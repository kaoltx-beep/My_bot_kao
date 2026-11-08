# Jarvis MCP Client — isolated prototype

## Current scope

This is a disconnected prototype. It is **not** registered in Jarvis's default ToolRegistry, is not called by Telegram/FastAPI handlers, and does not start any MCP server automatically.

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
- The approval-store tests use a temporary file and do not touch production approval data.

**Important integration status:** the current `handlers/telegram.py` only accepts messages from the configured private chat and does not register an approval callback handler. The approval store is a hardened primitive, not a complete Telegram approval workflow. Do not pass `approved=True` to MCP execution until a callback handler has been implemented and tested to call `consume(..., chat_id=..., user_id=...)` and then execute only the exact stored tool and parameters. The legacy `tools/integrate_approval.py` patcher is not the active modular Telegram handler.

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

## Next steps before integration

1. Implement a modular Telegram approval callback with chat/user binding and expiry checks.
2. Add handler tests for wrong user, wrong chat, expired requests, replay, and exact stored tool/arguments.
3. Add an approval-grant boundary so a plain boolean cannot be treated as proof of user consent.
4. Test the callback and MCP adapter together using only an in-memory read-only server.
5. Keep production deployment, credentials, workflows, and the default registry unchanged until a separate approval.

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
