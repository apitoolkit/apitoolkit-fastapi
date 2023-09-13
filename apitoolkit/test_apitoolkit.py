from fastapi import FastAPI
from fastapi.testclient import TestClient
from . import APIToolkit
import base64
import json

app = FastAPI()


redact_req = ["$.credit-card.cvv", "$.credit-card.name", "$.password"]
redact_headers = ["authorization", "content-type", "connection"]
exampleDataRedaction = [
    "$.status", "$.data.account_data.account_type",
    "$.data.account_data.possible_account_types",
    "$.data.account_data.possible_account_types2[*]",
    "$.non_existent",
]

apitoolkit = APIToolkit(
    api_key="<API_KEY>",
    root_url="http://localhost:8080",
    redact_headers=redact_headers,
    redact_request_body=redact_req,
    redact_response_body=exampleDataRedaction,
    debug=True
)


def publish_message(payload):
    payload_dict = payload.__dict__
    assert isinstance(payload_dict, dict)
    assert payload_dict['method'] == 'POST'
    assert payload_dict['response_headers']['content-type'] == "[CLIENT_REDACTED]"
    assert payload_dict['request_headers']['authorization'] == "[CLIENT_REDACTED]"
    assert payload_dict['request_headers']['x-val'] == "foo"
    assert payload_dict['query_params'] == {"foo": "bar"}
    assert payload_dict['path_params'] == {"name": "john"}
    assert payload_dict['url_path'] == '/hello/{name}'
    assert payload_dict['raw_url'] == '/hello/john?foo=bar'
    assert payload_dict['status_code'] == 200
    assert payload_dict['request_body'] == base64.b64encode(
        json.dumps(exampleRequestData).encode("utf-8")).decode("utf-8")
    assert payload_dict['response_body'] == base64.b64encode(
        json.dumps(exampleDataRedacted).encode("utf-8")).decode("utf-8")


apitoolkit.publish_message = publish_message

app.middleware('http')(apitoolkit.middleware)


@app.post("/hello/{name}")
async def read_main(name):
    return exampleResponseData

client = TestClient(app)


def test_read_main():
    response = client.post("/hello/john?foo=bar", json=exampleRequestData,
                           headers={"Authorization": "Bearer abc123", "X-Val": "foo"})
    assert response.status_code == 200
    assert response.json() == exampleResponseData


exampleResponseData = {
    "status": "success",
    "data": {
        "message": "hello world",
        "account_data": {
            "batch_number": 12345,
            "account_id": "123456789",
            "account_name": "test account",
            "account_type": "test",
            "account_status": "active",
            "account_balance": "100.00",
            "account_currency": "USD",
            "account_created_at": "2020-01-01T00:00:00Z",
            "account_updated_at": "2020-01-01T00:00:00Z",
            "account_deleted_at": "2020-01-01T00:00:00Z",
            "possible_account_types": ["test", "staging", "production"],
            "possible_account_types2": ["test", "staging", "production"],
        },
    },
}

exampleDataRedaction = [
    "$.status", "$.data.account_data.account_type",
    "$.data.account_data.possible_account_types",
    "$.data.account_data.possible_account_types2[*]",
    "$.non_existent",
]

exampleDataRedacted = {
    "status": "[CLIENT_REDACTED]",
    "data": {
        "message": "hello world",
        "account_data": {
            "batch_number": 12345,
            "account_id": "123456789",
            "account_name": "test account",
            "account_type": "[CLIENT_REDACTED]",
            "account_status": "active",
            "account_balance": "100.00",
            "account_currency": "USD",
            "account_created_at": "2020-01-01T00:00:00Z",
            "account_updated_at": "2020-01-01T00:00:00Z",
            "account_deleted_at": "2020-01-01T00:00:00Z",
            "possible_account_types": "[CLIENT_REDACTED]",
            "possible_account_types2": ["[CLIENT_REDACTED]", "[CLIENT_REDACTED]", "[CLIENT_REDACTED]"],
        },
    },
}

exampleRequestData = {
    "status": "request",
    "send": {
        "message": "hello world",
        "account_data": [{
            "batch_number": 12345,
            "account_id": "123456789",
            "account_name": "test account",
            "account_type": "test",
            "account_status": "active",
            "account_balance": "100.00",
            "account_currency": "USD",
            "account_created_at": "2020-01-01T00:00:00Z",
            "account_updated_at": "2020-01-01T00:00:00Z",
            "account_deleted_at": "2020-01-01T00:00:00Z",
            "possible_account_types": ["test", "staging", "production"],
        }],
    },
}
