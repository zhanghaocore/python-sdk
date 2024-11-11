# MCP Python SDK

Python implementation of the Model Context Protocol (MCP), providing both client and server capabilities for integrating with LLM surfaces.

## Overview

The Model Context Protocol allows applications to provide context for LLMs in a standardized way, separating the concerns of providing context from the actual LLM interaction. This Python SDK implements the full MCP specification, making it easy to:

- Build MCP clients that can connect to any MCP server
- Create MCP servers that expose resources, prompts and tools
- Use standard transports like stdio and SSE
- Handle all MCP protocol messages and lifecycle events

## Installation

```bash
uv add mcp
```

## Quick Start

### Creating a Client

```python
from mcp import ClientSession
from mcp.client.stdio import stdio_client

async with stdio_client(command="path/to/server") as (read, write):
    async with ClientSession(read, write) as session:
        # Initialize the connection
        await session.initialize()

        # List available resources
        resources = await session.list_resources()
```

### Creating a Server

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Create a server instance
server = Server("example-server")

# Add capabilities
@server.list_resources()
async def list_resources():
    return [
        {
            "uri": "file:///example.txt",
            "name": "Example Resource"
        }
    ]

# Run the server
async with stdio_server() as (read, write):
    await server.run(read, write, server.create_initialization_options())
```

## Documentation

- [MCP Specification](https://modelcontextprotocol.github.io)
- [Example Servers](https://github.com/modelcontextprotocol/example-servers)

## Contributing

Issues and pull requests are welcome on GitHub at https://github.com/modelcontextprotocol/python-sdk.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
