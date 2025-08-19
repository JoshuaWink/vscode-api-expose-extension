# terminal-mcp-server

A small FastMCP server that exposes terminal (PTY) management APIs over MCP.

Features
- Create and manage local PTY-backed terminals from MCP clients.
- Non-blocking send/read of terminal output.
- Interrupt (Ctrl-C), clear, dispose terminals, and list active PTYs.

Available tools
- `terminal_create(name?)` -> creates a PTY and returns an id
- `terminal_send(terminalId, text)` -> sends text to PTY
- `terminal_read(terminalId, {strip_ansi:true, lines:N})` -> read buffered output
- `terminal_interrupt(terminalId)` -> send Ctrl-C
- `terminal_clear(terminalId)` -> clear buffer
- `terminal_dispose(terminalId)` -> terminate and clean up
- `terminal_list()` -> list known PTYs

Quickstart
1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install "mcp[cli]"
```

2. Run the server (from this folder):

```bash
python server.py
```

3. Use a FastMCP client or the MCP Inspector to call the tools above.

Examples
- Create a terminal:

```py
# using a simple FakeServer registration (for local testing):
from app.tools import register_tools

# See project examples for using the official FastMCP client.
```

Notes
- This server intentionally only exposes terminal-related tools so it can be included or deployed separately from a larger MCP server.
- Reads are non-destructive by default; call `terminal_clear` to empty a buffer.

Keywords: terminal, pty, mcp, fastmcp, shell, remote-shell, terminal-mcp
