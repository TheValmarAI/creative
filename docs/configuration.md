# Configuration and operations

All settings are read from environment variables and `.env`. Environment variables take
precedence. Copy [`.env.example`](../.env.example) for the full list. Restart the API server
after changing its configuration.

## Models and credentials

| Setting | Purpose |
| --- | --- |
| `AI_MODEL` | Default for every role; `gateway/openai-responses:gpt-6-luna` |
| `PLANNER_MODEL` | Optional override for framework generation and workflow planning |
| `GENERATOR_MODEL` | Optional override for node alternatives |
| `WRITER_MODEL` | Optional override for final composition |
| `PYDANTIC_AI_GATEWAY_API_KEY` | Gateway credential, loaded from `.env` |
| `PYDANTIC_AI_GATEWAY_BASE_URL` | Optional Gateway URL override; region is normally inferred |

The configured model must support structured output tools. OpenAI, Anthropic, and Google
provider support is included through Pydantic AI. Other providers may need an additional extra.

Gateway routes use your Gateway account's configured upstream providers. A separate
`OPENAI_API_KEY` is not required for those routes. For direct provider routes, export the
provider's native credentials in the shell; the app only reads its own declared settings
from `.env`. There is no automatic fallback to a different provider.

For an OpenAI Chat Completions-compatible endpoint, set `AI_BASE_URL` and `AI_API_KEY`.
Every active role must then use an explicit `openai-chat:` model string:

```dotenv
AI_MODEL=openai-chat:your-model
AI_BASE_URL=https://your-provider.example/v1
AI_API_KEY=your-key
```

GPT-6 Luna uses low reasoning effort on Responses and `none` on Chat Completions for tool
calling. Other models keep their native reasoning defaults.

## Candidates and execution

| Setting | Default | Meaning |
| --- | --- | --- |
| `CANDIDATE_COUNT` | 20 | Framework/candidate pool size, from 1 to 100 |
| `MAX_LLM_CALLS` | 8 | Concurrent provider requests per process |
| `MAX_GENERATIONS` | 4 | Admitted generations; excess requests receive a busy response |
| `CALL_TIMEOUT_SECONDS` | 180 | Deadline per provider attempt, after acquiring its slot |
| `GENERATION_TIMEOUT_SECONDS` | 600 | Entire generation, including slot waits and retries |
| `TRANSIENT_RETRIES` | 2 | Additional attempts for transient provider failures |

Per-request `candidate_count`, or CLI `--candidate-count`, overrides `CANDIDATE_COUNT`.
The resolved count is inserted into prompts and exact-length output schemas.

Each workflow is an ordered list. One node generates its pool and Python selects a candidate
before the next starts. Context isolation changes inputs, not execution order. Separate
requests share the provider-call limit while keeping their selections and prompts isolated.

A workflow with N decision nodes normally makes N+3 calls: frameworks, planning, N pools,
and final writing. With the maximum 23 decision nodes, that is 26 calls before corrections or
retries. Candidate count changes the output volume of each call, not the number of nodes.

One structured-output correction is allowed per agent stage, including framework-mapping
validation. Transient retries use jitter and respect `Retry-After`; SDK retries are disabled.
Backoff releases concurrency slots. Failure or cancellation stops the remaining chain.

## HTTP access

The launcher binds to `127.0.0.1:8000` by default. `HOST` and `PORT` override that address.
Set a bearer secret of at least 16 characters through `API_TOKEN` for private clients.
The same token protects REST, MCP, and documentation; `/healthz` stays available to probes.

Binding beyond localhost requires `API_TOKEN`. Configure explicit `ALLOWED_HOSTS` and, when
needed, `ALLOWED_ORIGINS` as JSON arrays; wildcard allowlists are rejected. The bundled launcher
does not trust forwarded headers. Unauthenticated requests must come from an actual loopback
peer. Use HTTPS at the reverse proxy when exposing the service.

The MCP endpoint uses the official Python SDK's stateless Streamable HTTP transport. The
parent FastAPI lifespan starts and stops its session manager. It supports JSON responses,
not a server-initiated event stream; `GET /mcp` returns 405. Authentication is a shared bearer
secret, not OAuth discovery for public MCP directories.

## Request and response

`POST /v1/generate` accepts:

```json
{
  "prompt": "Write an ad for a bottle of water.",
  "candidate_count": 5,
  "include_candidates": true
}
```

`prompt` is required and limited to 16,000 characters. Candidate count is optional;
`include_candidates` defaults to true. The MCP tool accepts the same fields.

A successful response contains the original `prompt`, `request_id`, resolved `candidate_count`,
finished `output`, selected `framework`, `workflow`, `selections`, per-stage `trace`, elapsed
time, and aggregate input/output tokens. Selection indices are zero-based. Setting
`include_candidates:false` omits pools from the response; it does not reduce model work.
Only selected values are passed to later nodes, regardless of this flag.

Each workflow node has `id`, `purpose`, `instructions`, `rationale`, `isolated_context`, and
`cue`. Normal nodes see the brief, framework, and every earlier selection. Isolated nodes
receive only their instructions and required neutral cue. Framework obligations map to node
IDs. Validation checks the ordered node identities, mapping, exact candidate count, nonempty
values, and string uniqueness. Semantic diversity and preservation remain model behaviors.

Errors use a structured `error` object with request ID, code, message, failed stage, and
retryability. Timeout failures also include attempt count and timing diagnostics.

| HTTP status | Meaning |
| --- | --- |
| 422 | Invalid request body |
| 429 | Generation capacity is full; retry later |
| 502 | Generation/provider failure |
| 504 | Overall generation deadline exceeded |

MCP returns equivalent error details with `isError:true`. It exposes successful responses
as structured content and a JSON text block. There is no successful partial result.

A client disconnect cancels the request. Closing a UI without closing its connection does
not signal cancellation. Retrying starts a fresh workflow and random path.

## Observability and prompt inspection

```dotenv
LOGFIRE_ENABLED=true
# Optional project write token, separate from the Gateway key:
LOGFIRE_TOKEN=your-logfire-write-token
LOGFIRE_INCLUDE_CONTENT=false
```

Native Pydantic AI agent/model spans sit under a generation span. Each provider attempt
records its stage, model, attempt number, and timeout. Without a token or configured Logfire
project, `--verbose` displays local console spans. A Gateway key does not authorize telemetry.

Prompt/output span capture is off by default. Set `LOGFIRE_INCLUDE_CONTENT=true` to opt in;
`LOGFIRE_ENABLED=false` disables the app's Logfire setup. Telemetry is flushed on CLI exit
and server shutdown. Python logs contain metrics and IDs rather than prompt/output content.

CLI `--visualize` separately captures model inputs for local inspection. The view shows the
model and one read-only prompt: instructions, examples, then the actual user input and prior
selections. It displays effective instructions once rather than duplicating mirrored SDK
fields. If correction occurred, the final request includes that conversation history.
The underlying JSON trace retains captured messages, schemas, and model settings at the
provider boundary, before provider-specific HTTP formatting. These inputs are not captured
by default for normal CLI, REST, or MCP runs.

The HTML file contains generated content and captured prompts. Its file permissions are
private; it persists in the system temporary directory until removed by you or the system.
Older results without a stored prompt show an unavailable-input message rather than guessing.

## Optional Docker usage

The repository is ready to run locally; no package registry or deployment is required.
The optional Dockerfile provides a non-root server image:

```sh
docker build -t creative .
docker run --rm -p 8000:8000 \
  -e PYDANTIC_AI_GATEWAY_API_KEY \
  -e API_TOKEN \
  -e 'ALLOWED_HOSTS=["localhost","127.0.0.1","creative.example.com"]' \
  creative
```

Export the Gateway key and a long random API token before running. The image binds to
`0.0.0.0`, so it requires a token. Retain `127.0.0.1` in the host allowlist for health probes.

Use one Uvicorn worker per container and scale containers for more capacity. Limits are per
process. Client, proxy, and ingress timeouts should exceed the generation deadline; 660
seconds accommodates the default 600-second deadline. Lower the deadline if your host imposes
a shorter limit. Provider latency, tokens, and rate limits dominate this I/O-heavy workflow.

There is no database, durable result storage, or request resume. Restarting interrupts active
requests. The launcher allows a 15-second graceful shutdown window before cancelling remaining
work. Choose infrastructure that permits long requests if you deploy it.
