"""MCP tools and Streamable HTTP transport; workflow behavior stays in the core."""

import json
from collections.abc import Awaitable, Callable

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent

from creative.core.config import Settings
from creative.core.errors import GenerationFailure
from creative.core.schemas import CandidateCount, GenerateRequest, GenerateResponse, Prompt


def tool_result(data: dict, *, is_error: bool = False) -> CallToolResult:
    return CallToolResult(
        isError=is_error,
        content=[TextContent(type="text", text=json.dumps(data, ensure_ascii=False))],
        structuredContent=data,
    )


def create_mcp(
    settings: Settings, generate: Callable[[GenerateRequest], Awaitable[GenerateResponse]]
) -> FastMCP:
    server = FastMCP(
        "Creative",
        instructions="Generate framework-led creative outputs with independently random choices.",
        stateless_http=True,
        json_response=True,
        streamable_http_path="/mcp",
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[f"{host}:*" for host in settings.allowed_hosts] + settings.allowed_hosts,
            allowed_origins=settings.allowed_origins,
        ),
    )

    async def generate_tool_result(request: GenerateRequest) -> CallToolResult:
        result = await generate(request)
        return tool_result(result.model_dump(mode="json", exclude_none=True))

    @server.tool(structured_output=False)
    async def generate_creative(
        prompt: Prompt,
        include_candidates: bool = True,
        candidate_count: CandidateCount | None = None,
    ) -> CallToolResult:
        """Generate a creative deliverable with its framework and random-selection trace.

        prompt: Creative brief, including constraints, desired format and language.
        include_candidates: Include all candidates per node for review (default true).
        candidate_count: Candidates per node/frameworks (1–100; defaults to server config).
        """
        request = GenerateRequest(
            prompt=prompt, include_candidates=include_candidates, candidate_count=candidate_count
        )
        try:
            return await generate_tool_result(request)
        except GenerationFailure as error:
            return tool_result(error.payload, is_error=True)

    return server
