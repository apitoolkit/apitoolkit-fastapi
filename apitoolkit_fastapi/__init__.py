from datetime import datetime
import uuid
from fastapi import Request, Response
from google.cloud import pubsub_v1
from google.oauth2 import service_account  # type: ignore
from starlette.concurrency import iterate_in_threadpool
from jsonpath_ng import parse  # type: ignore
from starlette.types import Message
from typing import Any
import base64
import httpx
import json
import time
import pytz  # type: ignore
from apitoolkit_python import observe_request, report_error


async def set_body(request: Request, body: bytes):
    async def receive() -> Message:
        return {"type": "http.request", "body": body}
    request._receive = receive


async def get_body(request: Request) -> bytes:
    body = await request.body()
    await set_body(request, body)
    return body


class Payload:
    def __init__(self, **kwargs):
        self.timestamp = datetime.now().isoformat()
        self.__dict__.update(kwargs)


class APIToolkit:
    def __init__(self, api_key, debug=False, root_url="https://app.apitoolkit.io",
                 redact_headers=['authorization', 'cookie'],
                 redact_request_body=[], redact_response_body=[], service_version=None, tags=[]):
        self.metadata = Any
        self.publisher = Any
        self.topic_path = Any
        self.redact_headers = ['authorization', 'cookie']
        self.redact_request_body = []
        self.redact_response_body = []
        self.service_version = service_version
        self.tags = tags
        self.debug = False
        if debug:
            print("APIToolkit: initialize")
        url = root_url + "/api/client_metadata"
        headers = {"Authorization": f"Bearer {api_key}"}
        client = httpx.Client()
        resp = client.get(url, headers=headers)
        self.debug = debug
        self.redact_headers = redact_headers
        self.redact_request_body = redact_request_body
        self.redact_response_body = redact_response_body
        self.metadata = resp.json()
        credentials = service_account.Credentials.from_service_account_info(
            self.metadata["pubsub_push_service_account"])
        self.publisher = pubsub_v1.PublisherClient(credentials=credentials)
        self.topic_path = 'projects/{project_id}/topics/{topic}'.format(
            project_id=self.metadata['pubsub_project_id'],
            topic=self.metadata['topic_id'],
        )

    def getInfo(self):
        return {"project_id": self.metadata["project_id"], "service_version": self.service_version, "tags": self.tags}

    def publish_message(self, payload):
        data = json.dumps(payload).encode('utf-8')
        if self.debug:
            print("APIToolkit: publish message")
            json_formatted_str = json.dumps(payload, indent=2)
            print(json_formatted_str)
        future = self.publisher.publish(self.topic_path, data=data)
        return future.result()

    def redact_headers_func(self, headers):
        redacted_headers = {}
        for header_name, value in headers.items():
            if header_name.lower() in self.redact_headers or header_name in self.redact_headers:
                redacted_headers[header_name] = "[CLIENT_REDACTED]"
            else:
                redacted_headers[header_name] = value
        return redacted_headers

    def redact_fields(self, body, paths):
        try:
            data = json.loads(body)
            for path in paths:
                expr = parse(path)
                expr.update(data, "[CLIENT_REDACTED]")
            return json.dumps(data).encode("utf-8")
        except Exception as e:
            print(e, body)
            if isinstance(body, str):
                return body.encode('utf-8')
            return body

    def build_payload(self, sdk_type: str, request: Request, response: Response, request_body: bytes, response_body: bytes, duration: float):
        if self.debug:
            print("APIToolkit: build_payload")

        route_pattern = request.scope["route"].path
        path = request.url.path  # "/items/1"
        query = request.url.query  # "q=abc"
        full_path = f"{path}"
        if query:
            full_path += f"?{query}"
        scheme = request.url.scheme  # "http"
        netloc = request.url.netloc  # "localhost:8000"
        base_url = f"{scheme}://{netloc}"
        request_headers = self.redact_headers_func(dict(request.headers))
        response_headers = self.redact_headers_func(dict(response.headers))
        request_body = self.redact_fields(
            request_body.decode("utf-8"), self.redact_request_body)
        response_body = self.redact_fields(
            response_body, self.redact_response_body)

        message_id = request.state.apitoolkit_message_id
        errors = request.state.apitoolkit_errors
        print(errors)
        timezone = pytz.timezone("UTC")
        timestamp = datetime.now(timezone).isoformat()
        payload = {
            "request_headers": request_headers,
            "query_params": dict(request.query_params),
            "path_params": dict(request.path_params),
            "response_headers": response_headers,
            "method": request.method,
            "sdk_type": sdk_type,
            "proto_major": 1,
            "proto_minor": 1,
            "host": base_url,
            "raw_url": full_path,
            "referer": request.headers.get('referer', ""),
            "project_id": self.metadata["project_id"],
            "url_path": route_pattern,
            "response_body": base64.b64encode(response_body).decode("utf-8"),
            "request_body": base64.b64encode(request_body).decode("utf-8"),
            "status_code": response.status_code,
            "duration": duration,
            "timestamp": timestamp,
            "service_version": self.service_version,
            "tags": self.tags,
            "msg_id": message_id,
            "errors": errors or [],
            "parent_id": None
        }
        return payload

    async def middleware(self, request: Request, call_next):
        if self.debug:
            print("APIToolkit: middleware")
            start_time = time.perf_counter_ns()
            request.state.apitoolkit_message_id = str(uuid.uuid4())
            request.state.apitoolkit_errors = []
            request.state.apitoolkit_client = self
            await set_body(request, await request.body())
            request_body = await get_body(request)

            response = await call_next(request)
            try:
                response_body = [chunk async for chunk in response.body_iterator]
                response.body_iterator = iterate_in_threadpool(
                    iter(response_body))

                end_time = time.perf_counter_ns()
                duration = (end_time - start_time)

                payload = self.build_payload(
                    sdk_type='PythonFastApi',
                    request=request,
                    response=response,
                    request_body=request_body,
                    response_body=b''.join(response_body),
                    duration=duration
                )
                self.publish_message(payload)
                return response
            except Exception as e:
                if self.debug:
                    print(e)
                return response
