#!/usr/bin/env python3
"""
Launch the FastMCP server from this repository bound to a TCP transport on localhost.

Usage: run_mcp_tcp.py [port]
"""
import sys

if __name__ == "__main__":
    # allow running from extension by setting PYTHONPATH to repo root
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3743
    try:
        from mcp.server.fastmcp.server import FastMCP
        from app.tools import register_tools
        from app.resources import register_resources
        from app.prompts import register_prompts

        server = FastMCP(name="VSCode MCP Server")
        register_tools(server)
        register_resources(server)
        register_prompts(server)

        transport = f"tcp://127.0.0.1:{port}"
        print(f"[run_mcp_tcp] starting FastMCP on {transport}", flush=True)
        server.run(transport=transport)
    except Exception as e:
        print(f"[run_mcp_tcp] error starting server: {e}", flush=True)
        raise
