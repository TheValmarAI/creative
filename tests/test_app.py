import asyncio
import json

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import ValidationError

from creative.core.config import Settings
from creative.interfaces.api import create_app

AUTH = {"Authorization": "Bearer test-secret-123456789"}


@pytest.mark.parametrize("count", [None, 3, 31])
async def test_rest_and_mcp_end_to_end(scripted, settings, count):
    app = create_app(settings, scripted.llm())
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        app.state.engine.selector = lambda n: min(4, n - 1)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://localhost", headers=AUTH
        ) as client:
            arguments = {"prompt": "bear", "candidate_count": count}
            response = await client.post("/v1/generate", json=arguments)
            assert response.status_code == 200
            rest = response.json()
            async with streamable_http_client("http://localhost/mcp", http_client=client) as (
                read,
                write,
                _,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    assert [tool.name for tool in tools.tools] == ["generate_creative"]
                    result = await session.call_tool("generate_creative", arguments)
            assert not result.isError
            mcp = result.structuredContent
            for key in ("output", "candidate_count", "framework", "workflow", "selections"):
                assert mcp[key] == rest[key]
            assert len(rest["framework"]["candidates"]) == (count or 20)
            assert (await client.get("/healthz", headers={"Authorization": ""})).status_code == 200
            assert (await client.get("/openapi.json")).status_code == 200
            assert (await client.get("/mcp")).status_code == 405


async def test_authentication_validation_and_allowed_hosts(scripted, settings):
    app = create_app(settings, scripted.llm())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            for path in ("/v1/generate", "/mcp"):
                response = await client.post(path, json={"prompt": "bear"})
                assert response.status_code == 401
                assert response.headers["WWW-Authenticate"] == "Bearer"
            response = await client.post("/v1/generate", headers=AUTH, json={"prompt": " "})
            assert response.status_code == 422
            response = await client.post(
                "/v1/generate",
                headers={**AUTH, "Origin": "https://evil.example"},
                json={"prompt": "bear"},
            )
            assert response.status_code == 403
            response = await client.get("/healthz", headers={"Host": "evil.example"})
            assert response.status_code == 400
            assert not scripted.calls


async def test_invalid_override_is_rejected_by_both_transports(scripted, settings):
    app = create_app(settings, scripted.llm())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost", headers=AUTH
        ) as client:
            arguments = {"prompt": "bear", "candidate_count": 101}
            response = await client.post("/v1/generate", json=arguments)
            assert response.status_code == 422
            async with streamable_http_client("http://localhost/mcp", http_client=client) as (
                read,
                write,
                _,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    count_schema = tools.tools[0].inputSchema["properties"]["candidate_count"]
                    assert {"type": "integer", "minimum": 1, "maximum": 100} in count_schema[
                        "anyOf"
                    ]
                    result = await session.call_tool("generate_creative", arguments)
                    assert result.isError
            assert not scripted.calls


async def test_unauthed_access_is_only_for_actual_loopback(scripted, settings):
    settings.api_token = None
    app = create_app(settings, scripted.llm())
    async with app.router.lifespan_context(app):
        for host, expected in (("127.0.0.1", 200), ("203.0.113.1", 403)):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, client=(host, 1234)),
                base_url="http://localhost",
            ) as client:
                assert (await client.get("/openapi.json")).status_code == expected


async def test_structured_provider_errors_for_both_transports(scripted, settings):
    from pydantic_ai.exceptions import ModelHTTPError

    async def fail(role, payload):
        raise ModelHTTPError(400, "test", body="private data")

    scripted.hook = fail
    app = create_app(settings, scripted.llm())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost", headers=AUTH
        ) as client:
            rest = await client.post("/v1/generate", json={"prompt": "bear"})
            assert rest.status_code == 502
            async with streamable_http_client("http://localhost/mcp", http_client=client) as (
                read,
                write,
                _,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("generate_creative", {"prompt": "bear"})
            assert result.isError
            assert result.structuredContent["error"]["code"] == rest.json()["error"]["code"]
            assert "private data" not in result.model_dump_json()


@pytest.mark.parametrize("mcp", [False, True])
async def test_disconnect_cancels_generation_for_both_transports(scripted, settings, mcp):
    started = asyncio.Event()

    async def block(role, payload):
        started.set()
        await asyncio.Event().wait()

    scripted.hook = block
    app = create_app(settings, scripted.llm())
    body = (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "generate_creative", "arguments": {"prompt": "bear"}},
        }
        if mcp
        else {"prompt": "bear"}
    )
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/mcp" if mcp else "/v1/generate",
        "raw_path": b"/mcp" if mcp else b"/v1/generate",
        "query_string": b"",
        "root_path": "",
        "server": ("localhost", 80),
        "client": ("127.0.0.1", 1234),
        "headers": [
            (b"host", b"localhost"),
            (b"authorization", AUTH["Authorization"].encode()),
            (b"content-type", b"application/json"),
            (b"accept", b"application/json, text/event-stream"),
            (b"mcp-protocol-version", b"2025-03-26"),
        ],
    }
    messages = asyncio.Queue()
    await messages.put({"type": "http.request", "body": json.dumps(body).encode()})
    output = []

    async def send(message):
        output.append(message)

    async with app.router.lifespan_context(app):
        task = asyncio.create_task(app(scope, messages.get, send))
        try:
            await asyncio.wait_for(started.wait(), 2)
            await messages.put({"type": "http.disconnect"})
            await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), 2)
            # MCP may release the HTTP handler before its server task observes cancellation.
            for _ in range(20):
                if app.state.engine.active == 0:
                    break
                await asyncio.sleep(0.005)
            assert app.state.engine.active == 0
            assert scripted.cancelled == 1
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


def test_public_binding_requires_secret_and_explicit_compatible_transport():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, host="0.0.0.0")
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None, ai_model="openai-responses:example", ai_base_url="https://example.com"
        )
    with pytest.raises(ValidationError):
        Settings(_env_file=None, allowed_hosts=["*"])
