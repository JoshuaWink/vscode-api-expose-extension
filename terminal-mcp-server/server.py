from mcp.server.fastmcp.server import FastMCP
from app.tools import register_tools

server = FastMCP(name="Terminal MCP Server")
register_tools(server)

if __name__ == "__main__":
    server.run(transport="stdio")
