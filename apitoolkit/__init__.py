from datetime import datetime
from fastapi import Request, Response 
from google.cloud import pubsub_v1
from starlette.concurrency import iterate_in_threadpool
from starlette.types import Message
from typing import Any
import base64
import httpx
import json
import time

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
    def __init__ (self):
        self.metadata = Any 
        self.publisher = Any
        self.topic_path = Any

    async def initialize(self, api_key: str, debug=False, root_url="https://app.apitoolkit.io"):
        url = root_url + "/api/client_metadata"
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
        self.debug = debug
        self.metadata = resp.json()
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(self.metadata['pubsub_project_id'], self.metadata['topic_id'])

    def publish_message(self, payload: Payload):
        data = json.dumps(payload.__dict__).encode('utf-8')
        
        if self.debug:
            print("APIToolkit: publish message")
            json_formatted_str = json.dumps(payload.__dict__, indent=2)
            print(json_formatted_str)

        future = self.publisher.publish(self.topic_path, data=data)
        return future.result()


    def build_payload(self, sdk_type: str, request: Request, response: Response, request_body: bytes, response_body: bytes, duration: float):
        route_pattern = request.scope["route"].path
        path = request.url.path  # "/items/1"
        query = request.url.query  # "q=abc"
        full_path = f"{path}"
        if query:
            full_path += f"?{query}"

        scheme = request.url.scheme  # "http"
        netloc = request.url.netloc  # "localhost:8000"
        base_url = f"{scheme}://{netloc}"

        payload = Payload(
            request_headers=dict(request.headers),
            query_params=dict(request.query_params),
            path_params=dict(request.path_params),
            response_headers=dict(response.headers),
            method=request.method,
            sdk_type=sdk_type,
            host=base_url,
            raw_url=full_path,
            referer=request.headers.get('referer', ""),
            project_id=self.metadata["project_id"] ,
            url_path=route_pattern,
            response_body=base64.b64encode(response_body).decode("utf-8"),
            request_body=base64.b64encode(request_body).decode("utf-8"),
            status_code=response.status_code,
            duration=duration,
        )
        return payload



    async def middleware(self, request: Request, call_next):
        start_time = time.perf_counter_ns()
        await set_body(request, await request.body())
        request_body = await get_body(request)

        response = await call_next(request)

        response_body = [chunk async for chunk in response.body_iterator]
        response.body_iterator = iterate_in_threadpool(iter(response_body))

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
