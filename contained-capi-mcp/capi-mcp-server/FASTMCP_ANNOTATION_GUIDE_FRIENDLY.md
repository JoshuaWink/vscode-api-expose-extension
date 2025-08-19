# FastMCP Server: A Friendly Guide to Structure and Extension

*Welcome! If you're new to FastMCP or just want a clearer, more supportive explanation, you're in the right place. Let's walk through how the FastMCP server works, how you can extend it, and how to do so with confidence and ease.*

---

## 🌱 1. What Goes Where? (Directory Overview)

**Think of your FastMCP project as a well-organized home:**

- **`server.py`**: The front door. It starts the server and invites everything else in. *Keep it simple!*
- **`app/`**: The living space. All the real work happens here.
  - **`tools.py`**: Your toolkit. Define what your server can do ("tools").
  - **`resources.py`**: Shared supplies. Register things like files or database connections.
  - **`prompts.py`**: Conversation starters. Templates or logic for LLM/agent workflows.
- **Docs & Plans**: Files like `README.md`, `REFERENCE.md`, and `DEEPCOG_REFACTOR_PLAN.md` help you and others understand and plan.

*Example:*
```
capi-mcp-server/
  server.py
  app/
    tools.py
    resources.py
    prompts.py
  README.md
  ...
```

---

## 🛠️ 2. What Does What? (Key Code Entities)

### Tools (`app/tools.py`)
- **What?** Functions that let your server do things (run code, fetch data, etc.).
- **How?** Decorate with `@server.tool(...)` and register in `register_tools(server)`.
- **Pattern:** Accept both direct parameters and a `payload` dict for flexibility.

*Example:*
```python
@server.tool(name="capi_exec", description="Run code via the capi CLI /exec endpoint.")
def capi_exec(code: str = None, ...):
    # ...implementation...
```

### Resources (`app/resources.py`)
- **What?** Shared data or objects (files, configs, etc.).
- **How?** Decorate with `@server.resource(...)` and register in `register_resources(server)`.

*Example:*
```python
@server.resource(uri="file:///hello.txt", name="Hello File", description="A sample text file.")
def hello_file():
    return open("hello.txt").read()
```

### Prompts (`app/prompts.py`)
- **What?** Templates or logic for LLM/agent messages.
- **How?** Decorate with `@server.prompt(...)` and register in `register_prompts(server)`.

*Example:*
```python
@server.prompt(name="GreetUser", description="Say hello to a user.")
def greet_user(user: str):
    return f"Hello, {user}!"
```

---

## 🔄 3. How Does It Flow? (Data & Startup)

1. **Start the server** (`server.py`):
    - Instantiate FastMCP: `server = FastMCP(name="...")`
    - Register tools/resources/prompts.
    - Run: `server.run(transport="stdio")`
2. **Tools become callable endpoints** (via MCP).
3. **Agents/clients call tools** by name, passing parameters or payloads.
4. **Output is returned** (stdout, JSON, etc).

*Tip: All registration happens in one place for easy discovery and extension!*

---

## ✨ 4. How Do I Add or Change Things? (Extensibility)

### To Add a Tool:
1. Open `app/tools.py`.
2. Write a function, decorate with `@server.tool(...)`.
3. Add it to `register_tools(server)`.
4. (Optional) Accept both direct params and a `payload` dict.

### To Add a Resource:
1. Open `app/resources.py`.
2. Write a function, decorate with `@server.resource(...)`.
3. Add it to `register_resources(server)`.
4. Use an absolute URI for files/data.

### To Add a Prompt:
1. Open `app/prompts.py`.
2. Write a function, decorate with `@server.prompt(...)`.
3. Add it to `register_prompts(server)`.
4. Use clear names and descriptions.

*Encouragement: You only need to update the relevant `app/` file and register your new function. The entrypoint (`server.py`) stays clean and simple!*

---

## 🧩 5. Examples: Real-World Additions

- **Logging Tool:**
    ```python
    @server.tool(name="log_event", description="Log an event or annotation.")
    def log_event(event: str, payload: dict = None):
        with open("server.log", "a") as f:
            f.write(f"{event}: {json.dumps(payload)}\n")
        return "Logged."
    ```
- **Documentation Tool:**
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
    ```
- **Prompt Example:**
    ```python
    @server.prompt(name="Summarize", description="Summarize a block of text.")
    def summarize(text: str):
        return f"Summarize: {text}"
    ```

---

## 🚀 6. Quickstart: Your Own MCP Server

1. **Copy the structure:**
    - `server.py` (minimal entrypoint)
    - `app/` with `tools.py`, `resources.py`, `prompts.py`
2. **Install FastMCP:**
    ```sh
    pip install "fastmcp"
    ```
3. **Define your tools/resources/prompts in `app/` and register them in `server.py`.**
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
        server.run(transport="stdio") # or "http" or "sse"
    ```
4. **Run your server:**
    ```sh
    python server.py
    ```
5. **Call your tools via MCP Inspector, Python client, or any agent.**

---

## 📚 7. Want to Learn More?

- [MCP Python SDK Docs](https://modelcontextprotocol.io/docs/python-sdk/)
- [Inspector Tool](https://modelcontextprotocol.io/inspector/)
- [Official Spec](https://modelcontextprotocol.io/specification)
- See also: `mcp-cheatsheet.instructions.md` in your VSCode prompts for a quick reference.

---

## 💡 Final Encouragement

*Every step you take is progress. If you feel stuck, that's normal—just take it one section at a time. You're building something powerful, and this guide is here to support you. Happy coding!*
