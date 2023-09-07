# API Toolkit Python FastAPI SDK

The API Toolkit FastAPI client is an sdk used to integrate FastAPI web services with APIToolkit.
It monitors incoming traffic, gathers the requests and sends the request to the apitoolkit servers.

## Design decisions:

- Use the gcp SDK to send real time traffic from REST APIs to the gcp topic

## How to Integrate:

First install the apitoolkit Go sdk:
`pip install apitoolkit-fastapi`

Then add apitoolkit to your app like so (Gin example):

```php
from fastapi import FastAPI
from apitoolkit import APIToolkit

app = FastAPI()

# Initialize apitoolkit
apitoolkit = APIToolkit()

@app.on_event('startup')
async def startup_event():
    await apitoolkit.initialize(
            api_key='<API_KEY goes here>',
        )

app.middleware('http')(apitoolkit.middleware)


@app.get("/")
def read_root():
    return {"Hello": "World"}
```

## Client Redacting fields

While it's possible to mark a field as redacted from the apitoolkit dashboard, this client also supports redacting at the client side.
Client side redacting means that those fields would never leave your servers at all. So you feel safer that your sensitive data only stays on your servers.

To mark fields that should be redacted, simply add them to the apitoolkit config struct.
Eg:

```python
from fastapi import FastAPI
from apitoolkit import APIToolkit

app = FastAPI()

# Initialize apitoolkit
apitoolkit = APIToolkit()

@app.on_event('startup')
async def startup_event():
    # A list of fields to redact from response body
    redact_res = ["$.api_key", "$.password"]
    # A list of fields to redact from request body
    redact_req = ["$.credit-card.cvv", "$.credit-card.name"]
    # A list of fields to redact from request and repsonse headers
    redact_headers = ["Authorization", "Cookie"]
    await apitoolkit.initialize(
            api_key="<API_KEY>", debug=True,redact_response_body=redact_res,
            redact_request_body=redact_req,redact_headers=redact_headers
        )

app.middleware('http')(apitoolkit.middleware)

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

It is important to note that while the `redact_headers` config field accepts a list of headers(case insensitive),
the `redact_request_body` and `redact_response_body` expect a list of JSONPath strings as arguments.

The choice of JSONPath was selected to allow you have great flexibility in descibing which fields within your responses are sensitive.
Also note that these list of items to be redacted will be aplied to all endpoint requests and responses on your server.
To learn more about jsonpath to help form your queries, please take a look at this cheatsheet:
[https://lzone.de/cheat-sheet/JSONPath](https://lzone.de/cheat-sheet/JSONPath)
