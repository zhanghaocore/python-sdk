# MCP Simple Tool

A simple MCP server that exposes a website fetching tool.

## Usage

Start the server using either stdio (default) or SSE transport:

```bash
# Using stdio transport (default)
mcp-simple-tool

# Using SSE transport on custom port
mcp-simple-tool --transport sse --port 8000
```

The server exposes a tool named "fetch" that accepts one required argument:

- `url`: The URL of the website to fetch

## Example

Using the MCP client, you can use the tool like this:

```python
from mcp.client import ClientSession

async with ClientSession() as session:
    await session.initialize()

    # List available tools
    tools = await session.list_tools()
    print(tools)

    # Call the fetch tool
    result = await session.call_tool("fetch", {
        "url": "https://example.com"
    })
    print(result)
```
