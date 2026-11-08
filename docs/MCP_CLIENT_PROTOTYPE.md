# Jarvis MCP Client — isolated prototype

## Current scope

This is a disconnected prototype. It is **not** registered in Jarvis's default ToolRegistry, is not called by Telegram/FastAPI handlers, and does not start any MCP server automatically.

- Uses the official MCP Python SDK v2 client API: `from mcp import Client`.
- Supports MCP Streamable HTTP URLs.
- Requires HTTPS for remote servers. Plain HTTP is allowed only for loopback development.
- Rejects URLs containing embedded credentials, query strings, or fragments.
- Listing tools retrieves metadata only.
- Calling a tool requires both `approved=True` (to be supplied only after Jarvis's existing approval flow) and an explicit tool-name allowlist.
- Does not add an MCP dependency to production requirements or change any existing runtime configuration.

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

    # Only after the user approves this exact action:
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

Run the isolated safety tests without installing the MCP SDK:

```bash
python -m unittest discover -s tests -p 'test_mcp_client.py' -v
```

These tests cover URL restrictions, explicit approval, and the tool allowlist. They do not claim that a real MCP server connection has been tested.

## Next steps before integration

1. Run the unit tests in the repository's actual CI/runtime environment.
2. Install the SDK only in an isolated test environment and connect to a harmless local read-only MCP server.
3. Verify tool metadata, error handling, timeout behavior, and cancellation.
4. Add an adapter into Jarvis's ToolRegistry only after review. Map each remote tool to a risk level; never infer low risk from a tool name or description.
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
- Tests mock the MCP client call; they do not connect to a remote server or change production configuration.

Run adapter tests with:

```bash
python -m unittest tests.test_mcp_tool_adapter -v
```
