
# FastMCP Server Structure and Annotation Guide

This guide provides a detailed, step-by-step explanation of how the capi-mcp-server is structured, how it works, and how you can create or extend your own MCP servers with minimal friction. Every section is annotated for clarity and practical use.

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

## 1. Directory Structure (What Goes Where)

- `<lib>-mcp-server/`
  - `server.py`: **Entrypoint.** Instantiates the FastMCP server, registers all tools/resources/prompts, and starts the server. *Keep this file minimal and declarative.*
  - `app/`: **All business logic lives here.**
    - `tools.py`: **Define and register callable tools here.** Each tool is a Python function decorated and registered for agent/LLM use. Example: `capi_exec`, `capi`, `capi_help`.
    - `resources.py`: **(Optional)** Register shared resources (e.g., database connections, file handles) for use by tools.
    - `prompts.py`: **(Optional)** Register prompt templates or prompt logic for LLM/agent workflows.
  - `REFERENCE.md`: **Architecture reference.** Explains the modular, registry-driven pattern.
  - `README.md`: **Project overview, setup, and usage.**
  - `pyproject.toml`, `build/`, `<lib>_mcp_server.egg-info/`: **Packaging, planning, and build artifacts.**

---


## 2. Code Entities (What Does What)


### Tools (in `app/tools.py`)
- **What:** Python functions that expose automation, scripting, or API logic to agents/LLMs via MCP.
- **How:** Decorate each function with `@server.tool(...)` and register it in `register_tools(server)`.
- **Example:**
    ```python
    @server.tool(name="capi_exec", description="Run code via the capi CLI /exec endpoint.")
    def capi_exec(code: str = None, ...):
        # ...implementation...
    ```
- **Pattern:** Accept both direct parameters and a `payload` dict for flexible agent/LLM use.

### Server Entrypoint (`server.py`)
- **What:** The only script you run to start the server.
- **How:**
    1. Instantiate the FastMCP server: `server = FastMCP(name="...")`
    2. Register all tools/resources/prompts: `register_tools(server)` etc.
    3. Start the server: `server.run(transport="stdio")`
- **Keep this file minimal!** All logic should be in `app/` modules.


### Resources (in `app/resources.py`)
- **What:** Python objects or data (files, database connections, config, etc) that can be registered and exposed to agents/LLMs.
- **How:**
    1. Define a resource using `@server.resource` in `resources.py`.
    2. Register it in `register_resources(server)`.
    3. Resources are discoverable and readable by clients/agents.
- **Example:**
    ```python
    @server.resource(uri="file:///hello.txt", name="Hello File", description="A sample text file.")
    def hello_file():
        return open("hello.txt").read()
    # Register in register_resources(server)
    ```
- **Pattern:** Use absolute URIs for files/resources. Resources can be files, data, or even live objects.

### Prompts (in `app/prompts.py`)
- **What:** Prompt templates or prompt logic for LLM/agent workflows (e.g., reusable instructions, message templates).
- **How:**
    1. Define a prompt using `@server.prompt` in `prompts.py`.
    2. Register it in `register_prompts(server)`.
    3. Prompts are discoverable and renderable by clients/agents.
- **Example:**
    ```python
    @server.prompt(name="GreetUser", description="Say hello to a user.")
    def greet_user(user: str):
        return f"Hello, {user}!"
    # Register in register_prompts(server)
    ```
- **Pattern:** Prompts can be static templates or dynamic functions. Use clear names and descriptions for LLM UX.

---

---


## 3. Data Flow (How It Works)


- **Startup:** `server.py` runs, instantiates FastMCP, registers all tools/resources/prompts, and starts the server.
- **Tool Exposure:** Each tool registered with `@server.tool` becomes a callable endpoint via MCP (Model Context Protocol).
- **Agent/LLM Use:** Agents/clients can call these tools by name, passing parameters or payloads, and receive output (stdout, JSON, etc).
- **Registry Pattern:** All tools/resources/prompts are registered via functions, making discovery and extension trivial.

---


## 4. Extensibility (How to Add/Change Things)


### To Add a New Tool:
1. Open `app/tools.py`.
2. Define a new function and decorate it with `@server.tool(...)`.
3. Add it to the `register_tools(server)` function.
4. (Optional) Accept both direct params and a `payload` dict for agent/LLM flexibility.


### To Add a Resource:
1. Open `app/resources.py`.
2. Define a function and decorate it with `@server.resource(...)`.
3. Add it to the `register_resources(server)` function.
4. Use an absolute URI for files or data resources.

### To Add a Prompt:
1. Open `app/prompts.py`.
2. Define a function and decorate it with `@server.prompt(...)`.
3. Add it to the `register_prompts(server)` function.
4. Use clear names and descriptions for LLM/agent UX.


### To Extend/Refactor:
- Keep all business logic in `app/`.
- Only update `server.py` to register new modules or change server config.
- Use the MCP Inspector or client to discover all tools, resources, and prompts.

---



## 5. Example: Annotating or Extending FastMCP Servers (Tools, Resources, Prompts)


- **Annotation/Logging Tool Example:**
    ```python
    @server.tool(name="log_event", description="Log an event or annotation.")
    def log_event(event: str, payload: dict = None):
        with open("server.log", "a") as f:
            f.write(f"{event}: {json.dumps(payload)}\n")
        return "Logged."
    # Register in register_tools(server)
    ```
- **Documentation Tool Example:**
    ```python
    @server.tool(name="doc_tool", description="Return documentation for all registered tools.")
    def doc_tool():
        return str(server.list_tools())
    ```
- **Resource Example:**
    ```python
    @server.resource(uri="file:///config.json", name="Config File", description="Project config as JSON.")
    def config_file():
        import json
        return json.load(open("config.json"))
    # Register in register_resources(server)
    ```
- **Prompt Example:**
    ```python
    @server.prompt(name="Summarize", description="Summarize a block of text.")
    def summarize(text: str):
        return f"Summarize: {text}"
    # Register in register_prompts(server)
    ```
- **Pattern:** Any new tool, resource, or prompt can be added by following the above steps—no need to touch the entrypoint logic.

---


---

## 6. Quickstart: Creating Your Own MCP Server (Copy-Paste Template)

1. **Copy the directory structure:**
    - `server.py` (minimal entrypoint)
    - `app/` with `tools.py`, `resources.py`, `prompts.py`
2. **Install FastMCP and dependencies:**
    ```sh
    pip install "mcp[cli]"
    ```
3. **Define your tools/resources/prompts in `app/` and register them in `server.py`.**
4. **Run your server:**
    ```sh
    python server.py
    ```
5. **Call your tools via MCP Inspector, Python client, or any agent.**

---


---

## 7. References & Further Reading

- [MCP Python SDK Docs](https://modelcontextprotocol.io/docs/python-sdk/)
- [Inspector Tool](https://modelcontextprotocol.io/inspector/)
- [Official Spec](https://modelcontextprotocol.io/specification)
- See also: `mcp-cheatsheet.instructions.md` in your VSCode prompts for a quick reference to all decorators, commands, and usage patterns. FastMCP extends these patterns with a modular, registry-driven approach.

---

This guide is designed to make onboarding, extension, and new MCP server creation as clear and frictionless as possible. Copy, adapt, and extend with confidence!


## TL;DR + Refresher

- **Entrypoint:** `server.py` is minimal—just instantiates FastMCP, registers tools/resources/prompts, and runs the server.
- **Business Logic:** All tools, resources, and prompts live in `app/` (`tools.py`, `resources.py`, `prompts.py`).
- **Tools:** Python functions decorated with `@server.tool`, registered in `register_tools(server)`.
- **Resources:** Data or objects exposed with `@server.resource`, registered in `register_resources(server)`.
- **Prompts:** Templates or logic with `@server.prompt`, registered in `register_prompts(server)`.
- **Extending:** Add new tools/resources/prompts by defining and registering them—no need to change `server.py` logic.
- **Run:** `python server.py` starts the server. Use MCP Inspector or clients to call tools/resources/prompts.
- **Reference:** See [MCP Python SDK Docs](https://modelcontextprotocol.io/docs/python-sdk/) and the included cheatsheet for decorator and usage patterns.

**Remember:** Keep `server.py` declarative, put all logic in `app/`, and register everything for discoverability and easy extension. God willing, this pattern will keep your MCP servers clean, modular, and easy to grow.