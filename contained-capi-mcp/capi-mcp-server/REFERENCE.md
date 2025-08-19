# capi-mcp-server Modular Refactor Reference

## Overview

This document summarizes the modular, registry-driven architecture applied to capi-mcp-server, inspired by fastmcp-template. The goal is maintainability, extensibility, and agent/LLM compatibility.

## Directory Structure

```
capi-mcp-server/
  app/
    __init__.py
    tools.py
    resources.py
    prompts.py
  server.py
  ...
```

## Key Patterns

### 1. Modular App Structure
- All business logic (tools, resources, prompts) is in `app/`.
- Each concern has its own module and registration function.

### 2. Registry Pattern
- Tools are defined as callables and registered via a list in `register_tools`.
- Resources and prompts follow the same pattern for future extensibility.

### 3. Declarative Entrypoint
- `server.py` is minimal: instantiate the server, call registration functions, and run.

```python
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
```

### 4. Extensibility
- Add new tools/resources/prompts by updating the respective list and registration function.

## Benefits
- **Separation of Concerns:** Logic is isolated from server setup.
- **Easy Extension:** Add new features by updating lists.
- **Declarative Entrypoint:** Main server file is minimal and readable.
- **Agent/LLM Friendly:** Registry pattern supports dynamic discovery and automation.

## Usage
- Use this structure for all new logic.
- Keep the entrypoint minimal and declarative.
- Add new tools/resources/prompts by updating the lists in `app/`.

---

This document is a living reference for the modular capi-mcp-server architecture.
