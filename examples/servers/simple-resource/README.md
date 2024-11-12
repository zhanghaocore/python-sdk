# MCP Simple Resource

A simple MCP server that exposes sample text files as resources.

## Usage

Start the server using either stdio (default) or SSE transport:

```bash
# Using stdio transport (default)
mcp-simple-resource

# Using SSE transport on custom port
mcp-simple-resource --transport sse --port 8000
```

The server exposes some basic text file resources that can be read by clients.

## Example

Using the MCP client, you can read the resources like this:

```python
from mcp.client import ClientSession

async with ClientSession() as session:
    await session.initialize()

    # List available resources
    resources = await session.list_resources()
    print(resources)

    # Read a specific resource
    resource = await session.read_resource(resources[0].uri)
    print(resource)
```
