
from mcp.server.fastmcp.server import FastMCP
from app.tools import register_tools
from app.resources import register_resources
from app.prompts import register_prompts

server = FastMCP(name="VSCode Debug Toolkit")
register_tools(server)
register_resources(server)
register_prompts(server)

# Debug breakpoint candidates (place breakpoints on these lines in VS Code):
# 1: server = FastMCP(...)            -> inspect server construction and config
# 2: register_tools(server)           -> confirm tools registered
# 3: register_resources(server)       -> confirm resources registered
# 4: register_prompts(server)         -> confirm prompts registered

if __name__ == "__main__":
    # 5: server.run(...)                 -> starting the server; good spot to break
    server.run(transport="stdio")
