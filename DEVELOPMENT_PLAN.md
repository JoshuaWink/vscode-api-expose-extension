# VSCode API Complete Exposure Extension - Development Plan

## Project Overview
**Goal**: Create "The One CLI to Rule Them All" - a single command-line interface that exposes the ENTIRE VSCode API surface with no restrictions, enabling complete automation and scripting of any VSCode functionality across multiple sessions.

**Philosophy**: If it exists in VSCode's API, it should be accessible via CLI. No gatekeeping, no limitations, just pure API exposure.

## Simplified Architecture

### 1. VSCode Extension Bridge (`src/extension.ts`)
- **Purpose**: Minimal bridge inside VSCode to expose ALL APIs
- **Responsibilities**:
  - Auto-discover and expose every available VSCode API
  - Start HTTP server for CLI communication
  - Handle session identification
  - Route API calls to appropriate VSCode instance

### 2. Universal CLI Tool (`cli/vscode-api`)
- **Purpose**: Single CLI that can call ANY VSCode API
- **Capabilities**:
  - Execute any command: `vscode-api command "workbench.action.files.openFile"`
  - Access any workspace API: `vscode-api workspace.openTextDocument "/path/to/file"`
  - Manipulate editor: `vscode-api editor.insertText "Hello World"`
  - Control windows: `vscode-api window.showInformationMessage "Alert"`
  - **Dynamic JavaScript Execution**: `vscode-api exec "vscode.window.showInformationMessage('JIT Power!')"`
  - Target sessions: `vscode-api --session=workspace1 [any-api-call]`
- **Output**: Direct API results, scriptable responses
- **JIT Advantage**: Runtime JavaScript string evaluation enables unlimited API flexibility

### 3. Session Discovery (`auto-magic`)
- **Purpose**: Automatically find and target VSCode sessions
- **Capabilities**:
  - Auto-detect running VSCode instances
  - Route commands to correct session by workspace/window
  - Handle multiple sessions seamlessly

## Development Phases

### Phase 1: Foundation ✅ COMPLETE
- [x] **Extension Bridge Setup**
  - [x] Initialize minimal VSCode extension
  - [x] Auto-discover ALL available VSCode APIs (commands, workspace, editor, window, etc.)
  - [x] Start HTTP server inside VSCode for CLI communication
  - [x] Generate session identifier for this VSCode instance
  - [x] **Implement JavaScript runtime evaluator** for dynamic string execution
  - [x] **MESH NETWORKING**: Auto-discovery and peer communication system

- [ ] **CLI Tool Creation**
  - [ ] Build Node.js CLI application (`vscode-api`)
  - [ ] Implement generic API caller (any VSCode API accessible)
  - [ ] **Add `exec` command for dynamic JavaScript string evaluation**
  - [ ] Add session discovery and targeting
  - [ ] Enable scriptable output formats (JSON, plain text)

### Phase 2: Complete API Exposure 🔄 Next
- [ ] **Universal API Access**
  - [ ] Map ALL VSCode namespace APIs automatically
  - [ ] Expose command palette (all registered commands)
  - [ ] Expose workspace manipulation (files, folders, settings)
  - [ ] Expose editor control (text, selections, cursors, decorations)
  - [ ] Expose window management (panels, tabs, notifications)
  - [ ] Expose extension management (install, enable, disable)

- [ ] **Multi-Session Support**
  - [ ] Auto-discover running VSCode instances
  - [ ] Route commands to specific sessions by workspace/window
  - [ ] Handle session conflicts and routing

### Phase 3: Scripting & Automation 🔄 Future
- [ ] **Advanced CLI Features**
  - [ ] Batch command execution from files
  - [ ] Watch mode for real-time API monitoring
  - [ ] Pipe support for command chaining
  - [ ] Shell completion for all available APIs

- [ ] **Documentation Generation**
  - [ ] Auto-generate CLI help from VSCode API discovery
  - [ ] Create examples for common automation tasks
  - [ ] Build reference documentation

## Technical Specifications

### Session Identification Strategy
```typescript
interface SessionInfo {
  id: string;          // Unique session identifier
  pid: number;         // Process ID
  workspaceUri?: string; // Current workspace
  windowId: number;    // Window identifier
  capabilities: string[]; // Available API capabilities
  lastSeen: Date;      // Last heartbeat
}
```

### CLI Command Examples - No Limits Approach

**Dynamic Code Execution**: Since JavaScript is JIT compiled, users can pass raw JavaScript strings that execute at runtime, similar to how GitHub Copilot interacts with the VSCode API. This enables unlimited flexibility and real-time code evaluation.

```bash
# Execute ANY VSCode command
vscode-api command "workbench.action.files.openFile" --args="/path/to/file"
vscode-api command "workbench.action.closeActiveEditor"
vscode-api command "workbench.action.toggleSidebarVisibility"

# Direct API access - workspace
vscode-api workspace.openTextDocument "/path/to/file.js"
vscode-api workspace.saveAll

# Direct API access - editor  
vscode-api editor.edit --insert "Hello World" --position="0,0"
vscode-api editor.selection --start="0,0" --end="0,5"

# Direct API access - window
vscode-api window.showInformationMessage "Task Complete!"
vscode-api window.createTerminal --name="test"

# Dynamic JavaScript execution (JIT advantage)
vscode-api exec "vscode.window.activeTextEditor.edit(edit => edit.insert(new vscode.Position(0,0), 'Dynamic!'))"
vscode-api exec "vscode.workspace.workspaceFolders[0].uri.fsPath"
vscode-api exec "await vscode.commands.executeCommand('workbench.action.files.save')"

# Complex dynamic operations
vscode-api exec "
  const editor = vscode.window.activeTextEditor;
  if (editor) {
    const selection = editor.selection;
    const text = editor.document.getText(selection);
    await vscode.window.showInformationMessage(\`Selected: \${text}\`);
  }
"

# Session targeting (auto-discovery by workspace)
vscode-api --workspace="/path/to/project" [any-command]
vscode-api --session="session-id" [any-command]

# Scripting support
vscode-api --batch commands.txt
vscode-api --watch workspace.onDidChangeTextDocument
echo "editor.insertText 'Hello'" | vscode-api --pipe

# Discovery
vscode-api list-apis                    # Show ALL available APIs
vscode-api list-commands               # Show all registered commands  
vscode-api list-sessions               # Show running VSCode instances
vscode-api help workspace              # Show workspace API methods
```

### API Exposure Pattern
```typescript
interface ExposedAPI {
  category: string;    // 'command' | 'workspace' | 'editor' | etc.
  method: string;      // API method name
  parameters: Schema;  // Parameter validation schema
  permissions: string[]; // Required permissions
  sessionRequired: boolean; // Whether session targeting required
}
```

## Success Metrics

### Phase 1 Success Criteria - "The Foundation"
- [ ] Extension auto-discovers 100% of available VSCode APIs
- [ ] CLI can execute any discovered API call
- [ ] Session identification working for multi-instance targeting
- [ ] Basic HTTP bridge functional between CLI and extension

### Phase 2 Success Criteria - "Complete Exposure"
- [ ] ALL VSCode namespaces accessible via CLI (workspace, editor, window, commands, etc.)
- [ ] Multi-session routing works automatically by workspace detection
- [ ] No API limitations - if VSCode can do it, CLI can do it
- [ ] Scriptable output formats for automation

### Phase 3 Success Criteria - "Automation Ready"
- [ ] Batch execution from files working
- [ ] Watch mode for real-time API monitoring
- [ ] Shell completion shows all available APIs dynamically
- [ ] Documentation auto-generated from API discovery

## Risk Mitigation

### Technical Risks
- **VSCode API Changes**: Use VSCode API compatibility checking
- **Performance Impact**: Implement lazy loading and caching
- **Security Concerns**: Add authentication and permission system
- **Session Conflicts**: Implement robust session isolation

### Implementation Risks
- **Scope Creep**: Focus on core APIs first, advanced features later
- **Testing Complexity**: Build comprehensive test suite from start
- **Documentation Debt**: Generate docs from code annotations

## Next Immediate Actions
1. **Create Extension Bridge**: Minimal VSCode extension that auto-discovers ALL APIs
2. **Build Universal CLI**: Single `vscode-api` command that can call anything
3. **Implement Session Discovery**: Auto-find and target VSCode instances
4. **Test Complete Access**: Verify NO API limitations exist

---

**Status**: Extension Bridge Complete ✅  
**Philosophy**: "One CLI to Rule Them All" - Complete VSCode API exposure without restrictions  
**Current Phase**: Extension bridge with mesh networking operational  
**Next**: Complete CLI tool development  
**Goal**: If VSCode can do it, `vscode-api` can script it

## Mesh Network Architecture Implemented

**Auto-Discovery**: Extension scans ports 3637-3646 to find peer VSCode instances  
**Heartbeat System**: 30-second health monitoring maintains mesh connectivity  
**Session Routing**: Commands can target specific sessions by ID or workspace  
**Broadcast Mode**: Execute commands across all connected VSCode instances  
**No Limits**: Complete API surface exposed with dynamic JavaScript execution
