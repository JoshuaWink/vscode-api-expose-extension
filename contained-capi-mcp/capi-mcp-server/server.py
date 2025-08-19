
from mcp.server.fastmcp.server import FastMCP
from app.tools import register_tools
from app.resources import register_resources
from app.prompts import register_prompts

server = FastMCP(name="VSCode CLI MCP Server")
register_tools(server)
register_resources(server)
register_prompts(server)

if __name__ == "__main__":
    server.run(transport="stdio")
