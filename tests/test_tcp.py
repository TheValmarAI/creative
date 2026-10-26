"""Exercise the deployed ASGI stack over a real local TCP socket."""

import asyncio
import socket

import httpx
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from creative.interfaces.api import create_app


async def test_rest_and_mcp_over_tcp(scripted, settings):
    app = create_app(settings, scripted.llm())
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    url = f"http://127.0.0.1:{sock.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", lifespan="on"))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        async with asyncio.timeout(5):
            while not server.started:
                if task.done():
                    await task
                await asyncio.sleep(0.01)
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {settings.api_token}"}, timeout=5
        ) as client:
            response = await client.post(f"{url}/v1/generate", json={"prompt": "bear"})
            assert response.status_code == 200
            assert response.json()["output"] == "Finished: bear"
            async with streamable_http_client(f"{url}/mcp", http_client=client) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "generate_creative", {"prompt": "bear", "include_candidates": False}
                    )
                    assert not result.isError
                    assert result.structuredContent["output"] == "Finished: bear"
                    assert "candidates" not in result.structuredContent["framework"]
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, 5)
        sock.close()
