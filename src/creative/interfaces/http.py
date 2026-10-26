"""Shared HTTP access controls and disconnect cancellation for REST and MCP."""

import asyncio
import hmac
import ipaddress
from contextvars import ContextVar
from uuid import uuid4

from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from creative.core.config import Settings
from creative.core.engine import Engine
from creative.core.schemas import ErrorDetail, GenerateRequest, GenerateResponse

disconnected: ContextVar[asyncio.Event | None] = ContextVar("creative_disconnected", default=None)


async def run_connected(engine: Engine, request: GenerateRequest) -> GenerateResponse:
    event = disconnected.get()
    if event is None:
        return await engine.generate(request)
    generation = asyncio.create_task(engine.generate(request))
    watcher = asyncio.create_task(event.wait())
    try:
        done, _ = await asyncio.wait({generation, watcher}, return_when=asyncio.FIRST_COMPLETED)
        if watcher in done:
            raise asyncio.CancelledError
        return await generation
    finally:
        generation.cancel()
        watcher.cancel()
        await asyncio.gather(generation, watcher, return_exceptions=True)


class AccessMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)

        async def reject(status: int, code: str, message: str, **response_headers) -> None:
            detail = ErrorDetail(
                request_id=str(uuid4()),
                code=code,
                message=message,
                stage="access",
                retryable=False,
            )
            await JSONResponse(
                {"error": detail.model_dump()}, status_code=status, headers=response_headers
            )(scope, receive, send)

        if scope["path"] == "/healthz":
            await self.app(scope, receive, send)
            return
        origin = headers.get("origin")
        if origin is not None and origin not in self.settings.allowed_origins:
            await reject(403, "origin_forbidden", "Origin is not allowed")
            return
        preflight = scope["method"] == "OPTIONS" and origin is not None
        if not preflight:
            if self.settings.api_token:
                authorization = headers.get("authorization", "")
                scheme, _, token = authorization.partition(" ")
                if scheme.lower() != "bearer" or not hmac.compare_digest(
                    token.encode(), self.settings.api_token.encode()
                ):
                    await reject(
                        401,
                        "unauthorized",
                        "A valid bearer token is required",
                        **{"WWW-Authenticate": "Bearer"},
                    )
                    return
            else:
                client = scope.get("client")
                try:
                    local = bool(client) and ipaddress.ip_address(client[0]).is_loopback
                except ValueError:
                    local = False
                if not local:
                    await reject(403, "localhost_only", "Unauthenticated access is localhost only")
                    return

        if scope["path"] == "/mcp" and scope["method"] == "GET":
            # JSON-only stateless MCP has no server-initiated SSE stream.
            await reject(405, "method_not_allowed", "Use MCP POST requests", Allow="POST")
            return

        # Pump receive once for both transports; never race a disconnect poll against body reads.
        event = asyncio.Event()
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        token = disconnected.set(event)

        async def pump() -> None:
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    event.set()
                    await queue.put(message)
                    return
                await queue.put(message)

        pump_task = asyncio.create_task(pump())
        try:
            await self.app(scope, queue.get, send)
        finally:
            pump_task.cancel()
            await asyncio.gather(pump_task, return_exceptions=True)
            disconnected.reset(token)
