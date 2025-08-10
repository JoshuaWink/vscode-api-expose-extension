# capi-mcp-server

A minimal Model Context Protocol (MCP) server exposing the `capi` CLI as a tool for agent-driven VS Code automation.

## Overview
This server allows agents to invoke `capi` CLI commands via MCP, enabling automation and observability with minimal human intervention.

## Files
- `server.py`: Main MCP server exposing the `run_capi` tool.

## How to Run

1. Install the MCP Python SDK:
   ```sh
   pip install "mcp[cli]"
   ```
2. Ensure the `capi` CLI is available in your PATH.
3. Start the server:
   ```sh
   python server.py
   ```

## Example Tool

- `run_capi(command: str) -> str`: Runs a `capi` CLI command and returns its output.

## Next Steps
- Add more tools for other CLI commands or workflows.
- Test with the MCP Inspector or a Python client.
- Extend with async tools, resources, or prompts as needed.
- Add authentication, logging, or error handling as required.

## References
- [MCP Python SDK Docs](https://modelcontextprotocol.io/docs/python-sdk/)
- [Inspector Tool](https://modelcontextprotocol.io/inspector/)
- [Official Spec](https://modelcontextprotocol.io/specification)
