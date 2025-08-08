# VSCode API Complete Exposure

**"The One CLI to Rule Them All"** - Complete VSCode API exposure with no restrictions, enabling unlimited automation and scripting of any VSCode functionality across multiple sessions.

## 🎯 Philosophy

If it exists in VSCode's API, it should be accessible via CLI. No gatekeeping, no limitations, just pure API exposure with dynamic JavaScript execution.

## 🏗️ Architecture

### Extension Bridge (`src/extension.ts`)
- **Auto-discovers** ALL available VSCode APIs
- **HTTP Server** on port 3637 (configurable) for CLI communication  
- **Mesh Networking** - automatically discovers other VSCode instances (ports 3637-3646)
- **Dynamic JavaScript Execution** - JIT compilation for unlimited flexibility
- **Session Management** - unique IDs with workspace tracking

### Universal CLI (`cli/vscode-api`)
- **Human-friendly** interface over HTTP API
- **Session targeting** by ID or workspace
- **Batch execution** and scripting support
- **Auto-discovery** of running VSCode instances

## 🚀 Quick Start

### 1. Install Extension Package

```bash
# Option A: Install from VSIX (recommended)
./install.sh

# Option B: Manual installation
code --install-extension vscode-api-expose-0.0.2.vsix --force

# Option C: Development mode (for testing)
# Press F5 in VSCode to run extension in new window
```

### 2. Check Status Bar

Look for the status indicator in VSCode's bottom status bar:
- **🟢 VSCode API (3637)** = Server running on port 3637
- **🔴 VSCode API** = Server stopped

Click the status bar item to toggle the server on/off.

### 3. Build & Test CLI

```bash
# Build CLI
cd cli && npm run build

# Test CLI (should show "no sessions" if extension not running)
node dist/cli.js sessions

# Install globally (optional)
npm run install-global

# Quick demo
./test-demo.sh
```

### 3. Use the CLI

```bash
# List all VSCode sessions
vscode-api sessions

# List all available APIs  
vscode-api apis

# Execute VSCode commands
vscode-api command "workbench.action.files.openFile" "/path/to/file"
vscode-api command "workbench.action.closeActiveEditor"

# Dynamic JavaScript execution (JIT Power!)
vscode-api exec "vscode.window.showInformationMessage('Hello from CLI!')"
vscode-api exec "vscode.window.activeTextEditor?.edit(edit => edit.insert(new vscode.Position(0,0), 'Inserted!'))"

# Target specific sessions
vscode-api --workspace="/my/project" command "workbench.action.files.save"
vscode-api --session="abc123..." exec "vscode.workspace.saveAll()"

# Batch execution
echo -e "exec \"vscode.window.showInformationMessage('Message 1')\"\\nexec \"vscode.window.showInformationMessage('Message 2')\"" > commands.txt
vscode-api batch commands.txt

# Show messages in VSCode
vscode-api message "Hello World!"
vscode-api message --type error "Something went wrong!"
```

## 🌐 Mesh Network Features

The extension automatically discovers other VSCode instances and forms a mesh network:

```bash
# View mesh network status
# Command Palette: "Show Mesh Network Status"

# Broadcast commands to all sessions
curl -X POST http://localhost:3637/mesh/broadcast/exec \\
  -H "Content-Type: application/json" \\
  -d '{"code": "vscode.window.showInformationMessage(\\"Broadcast!\\")"}'
```

## 📡 HTTP API Endpoints

Direct HTTP access for programmatic integration:

```bash
# Session info
curl http://localhost:3637/session

# List APIs
curl http://localhost:3637/apis

# Execute command
curl -X POST http://localhost:3637/command/workbench.action.files.openFile \\
  -H "Content-Type: application/json" \\
  -d '{"args": ["/path/to/file"]}'

# Dynamic JavaScript execution
curl -X POST http://localhost:3637/exec \\
  -H "Content-Type: text/plain" \\
  -d 'vscode.window.showInformationMessage("Direct HTTP!")'

# Mesh network peers
curl http://localhost:3637/mesh/peers
```

## 🎮 Available Commands

### Extension Commands (in VSCode)
- **Start API Exposure Server** - Manual server start
- **Stop API Exposure Server** - Manual server stop  
- **List All Available APIs** - View discovered APIs
- **Get Session Information** - View session details
- **Show Mesh Network Status** - View connected peers

### CLI Commands
```bash
vscode-api sessions              # List VSCode sessions
vscode-api apis                  # List all APIs
vscode-api command <cmd> [args]  # Execute VSCode command
vscode-api exec <code>           # Execute JavaScript
vscode-api message <text>        # Show message in VSCode
vscode-api batch <file>          # Execute batch commands
```

## ⚙️ Configuration

Extension settings in VSCode:

```json
{
  "vscode-api-expose.serverPort": 3637,
  "vscode-api-expose.autoStart": true
}
```

## 🔧 Development

### Project Structure
```
/src/extension.ts          # Main extension with API exposure
/cli/src/cli.ts           # CLI tool implementation  
/package.json             # Extension manifest
/cli/package.json         # CLI package
```

### Build Commands
```bash
npm run compile           # Build extension
npm run watch            # Watch mode for extension
cd cli && npm run build  # Build CLI
cd cli && npm run dev    # Watch mode for CLI
```

### Testing
```bash
./test-setup.sh          # Run complete test setup
```

## 🌟 Key Features

- ✅ **Complete API Surface** - Auto-discovers ALL VSCode APIs
- ✅ **Dynamic JavaScript Execution** - JIT compilation advantage  
- ✅ **Mesh Networking** - Multi-session coordination
- ✅ **Session Targeting** - Route commands to specific VSCode instances
- ✅ **CLI & HTTP Access** - Human and machine interfaces with clean output
- ✅ **Status Bar Integration** - 🟢/🔴 visual indicators with click-to-toggle
- ✅ **No Restrictions** - If VSCode can do it, CLI can script it
- ✅ **Batch Processing** - Automate complex workflows
- ✅ **Real-time Discovery** - Auto-find running VSCode sessions
- ✅ **Easy Installation** - One-click VSIX package
- ✅ **Clean Interface** - Professional output without verbose messages

## 🚨 Security Note

This extension exposes the complete VSCode API surface. Only run in trusted environments. The HTTP server binds to localhost only.

## 📝 Examples

### Automation Script
```bash
#!/bin/bash
# Auto-save all files in all VSCode sessions
vscode-api sessions --json | jq -r '.[].id' | while read session; do
  vscode-api --session="$session" exec "vscode.workspace.saveAll()"
done
```

### Productivity Workflow  
```bash
# Open project, show message, and focus editor
vscode-api command "workbench.action.files.openFolder" "/path/to/project"
vscode-api exec "vscode.window.showInformationMessage('Project loaded!')"
vscode-api command "workbench.action.focusActiveEditorGroup"
```

---

**Status**: CLI Complete ✅  
**Architecture**: Extension Bridge + Universal CLI + Mesh Network  
**Philosophy**: "One CLI to Rule Them All" - Zero restrictions on VSCode API access
