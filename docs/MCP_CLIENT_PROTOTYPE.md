# Jarvis MCP Client — isolated prototype

## Current scope

This is an opt-in prototype. It is **not** registered in Jarvis's default ToolRegistry and is not active in the running Jarvis service. The Telegram approval callback and MCP adapter have been tested together against an in-memory MCP server, but no external MCP endpoint is configured or called.

- Uses the official MCP Python SDK v2 client API: `from mcp import Client`.
- Supports MCP Streamable HTTP URLs.
- Requires HTTPS for remote servers. Plain HTTP is allowed only for loopback development.
- Rejects URLs containing embedded credentials, query strings, or fragments.
- Listing tools retrieves metadata only.
- Calling a tool requires an explicit tool-name allowlist and an approval decision.
- Does not add an MCP dependency to production requirements or change any existing runtime configuration.

## Approval security prerequisite

`core/approval.py` now provides one-use approval records bound to both the originating Telegram chat ID and the requesting Telegram user ID.

- Approval records expire after 5 minutes by default; callers may configure a shorter TTL, capped at 15 minutes.
- A different chat or user cannot consume the request.
- Expired and legacy records without an expiry timestamp fail closed.
- A request can be consumed only once, and only with status `approved` or `rejected`.
- The Telegram callback must come from the original approval message, the configured private chat, and the requesting Telegram user.
- A successful consume returns a signed, one-use grant bound to the exact tool name and exact parameters. The MCP adapter rejects a bare `approved=True`, altered parameters, expired grants, and replayed grants.
- The signing secret is process-local; a restart invalidates grants rather than allowing a persisted approval to be replayed.
- The approval-store tests use a temporary file and do not touch production approval data.

**Integration status:** `handlers/telegram.py` now registers an approval callback, pauses medium/high/explicitly approval-required tools, and only executes the exact stored tool and parameters after `consume(..., chat_id=..., user_id=..., message_id=...)` succeeds. The callback is bound to the original Telegram message. The MCP adapter additionally requires the signed one-use grant; a bare boolean is insufficient. The legacy `tools/integrate_approval.py` patcher is not used by the modular handler.

## Optional local installation

The project runtime is Python 3.13, which meets the SDK's Python 3.11+ requirement.

In an isolated development environment only:

```bash
python -m pip install "mcp"
```

Do not add this package to the production deployment until a local test and dependency review pass.

## Example

```python
import asyncio
from mcp_client import list_server_tools, call_server_tool

async def inspect():
    tools = await list_server_tools("http://127.0.0.1:8000/mcp")
    print(tools)  # metadata only

    # This call is for the in-memory test harness only.
    result = await call_server_tool(
        "http://127.0.0.1:8000/mcp",
        "read_status",
        {},
        allowed_tools={"read_status"},
        approved=True,
    )
    print(result)

asyncio.run(inspect())
```

## Verification

Run the approval-store tests:

```bash
python -m unittest tests.test_approval_security -v
```

Run the isolated MCP tests:

```bash
python -m unittest discover -s tests -p 'test_mcp_*.py' -v
```

The SDK integration test uses an in-memory MCP server. It does not connect to a remote endpoint or prove production connectivity.

## Verification status

- Telegram callback tests cover owner mismatch, wrong chat, wrong originating message, rejection, and the successful approval path.
- The end-to-end test sends a Telegram approval through the real ToolExecutor and MCP adapter to an in-memory read-only MCP server.
- Latest CI: 59 main tests passed (4 skipped), 19 isolated MCP tests passed, and compile passed.
- No remote MCP endpoint, production credentials, active workflow, or deployed service was used.

## Remaining work before a real connection

1. Review the identity and trust model for the specific external MCP provider.
2. Configure a remote endpoint and credentials only through a secure secret store, after separate explicit approval.
3. Map each remote tool to a risk level and allowlist it individually.
4. Keep the default registry and production service unchanged until the live connection has passed a separate review.

## References

- Official SDK: https://github.com/modelcontextprotocol/python-sdk
- Client documentation: https://py.sdk.modelcontextprotocol.io/client/

## Opt-in Jarvis adapter

`mcp_tool_adapter.py` exposes exactly one configured, allowlisted MCP tool through Jarvis's synchronous `BaseTool` contract.

- Adapter metadata is always `high` risk and requires approval.
- `ToolExecutor` requires an opaque signed one-use approval grant for approval-aware adapters; a caller-supplied `approved=True` alone is rejected. Existing tools retain their original `execute` call path.
- Calling the adapter's ordinary `execute` method directly is rejected.
- The adapter is not added to `build_default_registry()`; an operator must explicitly construct and register it in a separate/opt-in registry.
- The adapter uses a bounded async timeout and refuses to run inside an already active event loop. An async-native integration is required for event-loop handlers.
- Tests use an in-memory MCP server or mock calls; they do not connect to a remote server or change production configuration.
