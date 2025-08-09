# capi-cli API Observability & Automation

## ⚡ CLI Aliases and Usage

The CLI can be installed globally and used with the following commands:

- `code-api` (primary, clear and descriptive)
- `capi` (short, memorable, on-brand)

You can also create your own custom alias (e.g., `myapi`) using a shell alias or symlink if desired.

**Example usage:**
```sh
code-api exec "vscode.workspace.name"
capi sessions
capi apis --session <session-id>
capi exec "vscode.commands.executeCommand('editor.action.selectAll')" --session <session-id>
```

This makes it easy to access and automate the VSCode API mesh from anywhere on your system.

---

## 📚 API Surface Overview

### 1. Session & Workspace
- `capi sessions`: List all active VSCode sessions
- `capi apis`: List all available VSCode APIs for a session
- `capi --session <id>`: Target a specific session for any command

### 2. Command & Scripting
- `capi exec <js>`: Execute arbitrary JavaScript in the VSCode extension host
- `capi command <id>`: Run a VSCode command by ID
- `capi batch <file>`: Run a batch of commands from a file
- `capi --json`: Output all results as JSON

### 3. Messaging & UI
- `capi message <text>`: Show a message in VSCode
- UI pop-ups, panels, and other interactive elements can be triggered by executing commands programmatically (e.g., `vscode.commands.executeCommand('workbench.action.chat.openModePicker')`).

### 4. Integration & Extensibility
- capi is the foundation for the MCP (Model Context Protocol) server and tools, enabling any agent, code assistant, or tool to connect to VSCode and interact with its APIs at runtime.
- All API discovery, documentation, and evolution are handled by the official `vscodeAPI` (maintained by Microsoft and surfaced in GitHub Copilot).

---

## 🛠️ Real-Time Manipulation & Automation

- Dynamically manipulate VSCode configuration, settings, and UI in real time using JavaScript execution:
  - Change any workspace/user setting
  - Write to or modify any file in the workspace
  - Force extensions to interact or trigger commands
  - Run scripts on startup to automate workflows
  - Chain API calls to orchestrate complex behaviors

**Example: Change Theme in Real Time**
```typescript
await vscode.workspace.getConfiguration('workbench').update('colorTheme', 'Abyss', true);
```

**Example: Batch Setup on Startup**
```typescript
await vscode.workspace.getConfiguration('editor').update('fontSize', 18, true);
await vscode.commands.executeCommand('workbench.action.toggleSidebarVisibility');
// ...and more
```

---

## 🧠 What the Model/Agent Sees
- All sessions and APIs available in the mesh
- All commands, messages, and UI actions invoked
- All automation scripts and their results
- All agent/tool connections via MCP

---

## 📝 Notes
- For persistent or global logs, implement your own storage/export logic.
- For full observability, hook into all relevant events and log to a file or telemetry system.
- The public API does not expose global VSCode state outside the current session/target.

---

**This document is auto-generated for maximum transparency and observability of the capi-cli and VSCode API mesh.**

---

## 🧩 Troubleshooting: Shell Quoting & dquote>

If you see a `dquote>` prompt in your terminal, your shell (zsh) is waiting for a closing double quote (`"`). This usually happens if you have an unmatched or improperly escaped quote in your command.

**Example Problem:**
```sh
capi message "Hello from capi message!"
 --session 4c73041d-3209-4dd9-819b-074fa7f9496d
dquote>
```

**How to fix:**
- Write the command all on one line, with no line break:
  ```sh
  capi message "Hello from capi message!" --session 4c73041d-3209-4dd9-819b-074fa7f9496d
  ```
- Or, if you need to break lines, use a backslash (`\`) at the end of the first line:
  ```sh
  capi message "Hello from capi message!" \
    --session 4c73041d-3209-4dd9-819b-074fa7f9496d
  ```

**Summary:**
- The `dquote>` prompt means your shell is waiting for a closing quote.
- Avoid line breaks inside quoted strings, or use a backslash to escape the newline.
