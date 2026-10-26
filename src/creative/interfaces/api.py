"""REST API and HTTP server composition, mounting the separate MCP adapter."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from creative.core.config import Settings
from creative.core.engine import Engine
from creative.core.errors import GenerationFailure
from creative.core.llm import LLM
from creative.core.observability import configure, flush
from creative.core.schemas import GenerateRequest, GenerateResponse
from creative.interfaces.http import AccessMiddleware, run_connected
from creative.interfaces.mcp import create_mcp


def create_app(settings: Settings | None = None, llm: LLM | None = None) -> FastAPI:
    settings = settings or Settings()
    configure(settings)

    async def generate(request: GenerateRequest) -> GenerateResponse:
        return await run_connected(app.state.engine, request)

    mcp = create_mcp(settings, generate)
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with llm or LLM(settings) as backend:
            engine = Engine(backend, settings)
            app.state.engine = engine
            async with mcp.session_manager.run():
                try:
                    yield
                finally:
                    await engine.close()
                    await asyncio.to_thread(flush)

    app = FastAPI(title="Creative API", version="0.1.0", lifespan=lifespan)
    app.state.mcp = mcp
    app.add_middleware(AccessMiddleware, settings=settings)
    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "MCP-Protocol-Version",
                "MCP-Session-Id",
            ],
            expose_headers=["MCP-Session-Id"],
        )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    @app.exception_handler(GenerationFailure)
    async def generation_error(_, error: GenerationFailure):
        return JSONResponse(
            error.payload,
            status_code=error.status_code,
            headers={"Retry-After": "5"} if error.status_code == 429 else None,
        )

    @app.get("/healthz")
    async def health():
        return {"status": "ok"}

    app.post("/v1/generate", response_model=GenerateResponse, response_model_exclude_none=True)(
        generate
    )
    # Mount last: the child owns /mcp, and the parent owns its lifespan above.
    app.mount("/", mcp_app)
    return app


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = Settings()
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        proxy_headers=False,
        timeout_graceful_shutdown=15,
    )


if __name__ == "__main__":
    main()
