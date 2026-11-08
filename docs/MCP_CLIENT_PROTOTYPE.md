# Jarvis MCP Client — isolated prototype

## Current scope

This is a separately tested connection module. It is **not** registered in Jarvis's default ToolRegistry, is not called by Telegram/FastAPI handlers, and does not start an MCP server automatically.

- Uses the official MCP Python SDK v2 Streamable HTTP client.
- GitHub connects only to `https://api.githubcopilot.com/mcp/readonly`; non-read-only GitHub endpoint URLs are rejected before connecting.
- GitHub credentials are read from `GITHUB_PERSONAL_ACCESS_TOKEN`, or from the existing local `gh auth token` login. Tokens stay in memory and are not written to files or logs.
- Other remote servers require HTTPS. Plain HTTP is allowed only for loopback development.
- Rejects URLs containing embedded credentials, query strings, or fragments.
- Listing tools retrieves metadata only and reports the server's read-only annotation.
- Calling a tool requires an explicit tool-name allowlist and an approval decision.
- MCP resource content is preserved in tool results (not reduced to text-only blocks).
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

The SDK integration test uses an in-memory MCP server. A separate manual smoke test on the Termux device connected to the official GitHub read-only endpoint, listed 28 tools (all 28 marked read-only), and successfully called `get_me` and `get_file_contents`. This does not activate MCP in the running Jarvis service.

## Next steps before integration

1. Complete the isolated Telegram approval-flow tests and MCP adapter grant tests.
2. Run CI and review the complete callback-to-executor path.
3. Review the new remote connection code and its read-only URL guard.
4. Keep production deployment, Telegram handlers, workflows, credentials, and the default registry unchanged until a separate deployment approval.

## References

- Official SDK: https://github.com/modelcontextprotocol/python-sdk
- Client documentation: https://py.sdk.modelcontextprotocol.io/client/

## Opt-in Jarvis adapter

`mcp_tool_adapter.py` exposes exactly one configured, allowlisted MCP tool through Jarvis's synchronous `BaseTool` contract.

- Adapter metadata is always `high` risk and requires approval.
- `ToolExecutor` passes its explicit `approved` decision only to adapters that implement `execute_with_approval`; existing tools retain their original `execute` call path.
- Calling the adapter's ordinary `execute` method directly is rejected.
- The adapter is not added to `build_default_registry()`; an operator must explicitly construct and register it in a separate/opt-in registry.
- The adapter uses a bounded async timeout and refuses to run inside an already active event loop. An async-native integration is required for event-loop handlers.
- Tests use an in-memory MCP server or mock calls; they do not connect to a remote server or change production configuration.
