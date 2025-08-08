## ⚠️ LLM Limitations and Large File Editing

When using LLMs (Language Model Agents) to edit files in VSCode, file size can significantly impact reliability and accuracy:

- **Context Window Limits:** LLMs have a maximum context window (number of tokens/characters they can process at once). For files over 500–700 lines, the model may not "see" the entire file, leading to incomplete or imprecise edits.
- **Chunking Required:** For large files, edits may need to be performed in chunks (e.g., by section, function, or region) rather than as a single operation.
- **Risk of Overwriting:** Naive approaches that replace the entire file content can accidentally overwrite unrelated code or comments if the LLM misses context.
- **Diff and Patch Strategies:** Advanced agents use diff/patch or targeted range edits to minimize risk and improve reliability.
- **Performance:** Large file operations are slower and more resource-intensive, increasing the chance of timeouts or partial edits.
- **Best Practice:** For files over several hundred lines, prefer incremental, region-based, or semantic edits, and always validate the result.

**Note:** LLM capabilities are improving, but context and chunking remain critical for reliable automation in large files.


# VSCode Language Model (LM) & Chat API Observability

## � CLI Aliases and Usage

The CLI can be installed globally and used with the following commands:

- `code-api` (primary, clear and descriptive)
- `capi` (short, memorable, on-brand)

You can also create your own custom alias (e.g., `myapi`) using a shell alias or symlink if desired.

**Example usage:**
```sh
code-api exec "return vscode.workspace.name"
capi sessions
```

This makes it easy to access the VSCode API mesh from anywhere on your system.

---

## �📚 API Surface Overview

### 1. Chat History & Context
- **ChatContext.history**
  - Type: `ReadonlyArray<ChatRequestTurn | ChatResponseTurn>`
  - Description: All chat messages so far in the current chat session (for the current participant).

### 2. Chat Events
- **lm.onDidChangeChatModels**
  - Type: `Event<void>`
  - Description: Fired when the set of available chat models changes.

### 3. Chat Message Types
- **ChatRequestTurn**: User’s message/turn in chat history.
- **ChatResponseTurn**: Assistant/LLM’s response.
  - `response`: Array of content parts (Markdown, file tree, anchors, command buttons, etc.)
  - `result`: `ChatResult`
  - `participant`: Responder ID
  - `command?`: Command name (if any)

### 4. Chat Result
- **ChatResult**
  - `errorDetails?`: Error details if request failed
  - `metadata?`: Arbitrary JSON metadata

### 5. Chat Request Options
- **LanguageModelChatRequestOptions**
  - `tools?`: List of tools available to the LLM for this chat
  - Tool calls and results are handled by the extension

### 6. Chat Tooling
- **lm.tools**: Register tools for the LLM to use
- **lm.invokeTool**: Invoke a registered tool

### 7. Chat-Related Commands
- `workbench.action.chat.editRequests`
- `workbench.action.chat.addToChatAction`
- `workbench.action.chat.toggleDefaultVisibility`
- `chat.inlineResourceAnchor.addFileToChat`
- `chatEditing.*` (openFileInDiff, acceptFile, discardFile, etc.)
- `lmApiServer.toggleServer`

### 8. Chat File Storage
- `.chatmode.md` files: Persona, mode, and chat configuration (not actual chat transcripts)

**This document is auto-generated for maximum transparency and observability of the VSCode Language Model and chat system.**  

## 🪟 UI Interactions: Triggering Pop-ups and Panels Programmatically

You can trigger UI pop-ups, panels, and other interactive elements in VSCode by executing commands programmatically. This allows automation and scripting to interact with the user interface directly, not just settings or files.

### Example: Open the Chat Mode Picker
```typescript
await vscode.commands.executeCommand('workbench.action.chat.openModePicker');
```

This command opens the chat mode picker UI, demonstrating that extensions and automation can invoke visible UI elements on demand.


- You can access and log:
  - All chat history for the current session/participant
  - All chat events (e.g., model changes)
  - All chat requests, responses, and tool calls/results
  - All chat-related commands and their effects
  - All persona/mode definitions in `.chatmode.md` files

- You can add listeners for:
  - Chat model changes (`lm.onDidChangeChatModels`)
  - Chat session events (via custom chat provider)
  - Tool calls and results

- You can log:
  - Every message, response, and tool invocation
  - All configuration and persona changes
  - Any metadata or error details from chat results


## 🚦 Example: Observability Hooks (Pseudocode)

## 📝 How `vscode.workspace.applyEdit` Works

You can programmatically modify files in VSCode using the `vscode.WorkspaceEdit` class and the `vscode.workspace.applyEdit` method. This is the standard way to perform text replacements, insertions, or deletions in one or more files.

### Example: Replace All Occurrences of a String in a File
```typescript
const uri = vscode.Uri.file('/path/to/file');
const doc = await vscode.workspace.openTextDocument(uri);
const edit = new vscode.WorkspaceEdit();
const text = doc.getText();
const newText = text.replace(/searchTerm/g, 'replacement');
// Replace the entire document content
edit.replace(uri, new vscode.Range(0, 0, doc.lineCount, 0), newText);
await vscode.workspace.applyEdit(edit);
await doc.save();
```

**Key Points:**
- `WorkspaceEdit` can batch changes across multiple files.
- You specify the file (URI), the range to replace, and the new text.
- `applyEdit` applies all changes atomically.
- You must save the document after applying the edit to persist changes to disk.

This approach is used by LLMs and automation agents to safely and efficiently modify files in the workspace.

import * as vscode from 'vscode';

// Listen for chat model changes
vscode.lm.onDidChangeChatModels(() => {
  log('Chat models changed!');
});

// Access chat history in a session
function logChatHistory(context: vscode.ChatContext) {
  context.history.forEach(turn => log(turn));
}

// Register a tool and log invocations
vscode.lm.tools.register({
  name: 'myTool',
  run: (args) => {
    log('Tool called', args);
    // ...
  }
});

// Log all chat results
function logChatResult(result: vscode.ChatResult) {
  if (result.errorDetails) log('Error:', result.errorDetails);
  if (result.metadata) log('Metadata:', result.metadata);
}
```

---

## 🛠️ Real-Time Manipulation & Automation

- You can dynamically manipulate VSCode configuration, settings, and even UI in real time using JavaScript execution:
  - Change any workspace/user setting (themes, colors, keybindings, etc.)
  - Write to or modify any file in the workspace
  - Force extensions to interact or trigger commands
  - Run scripts on startup to load entire setups or automate workflows
  - Chain API calls to orchestrate complex behaviors

### Example: Change Theme in Real Time
```typescript
await vscode.workspace.getConfiguration('workbench').update('colorTheme', 'Abyss', true);
```

### Example: Batch Setup on Startup
```typescript
// In a startup script, you could:
await vscode.workspace.getConfiguration('editor').update('fontSize', 18, true);
await vscode.commands.executeCommand('workbench.action.toggleSidebarVisibility');
// ...and more
```

- **You have full access to all Microsoft and extension APIs.**
- **You can orchestrate, automate, and observe any aspect of the VSCode environment.**

---

## 🧠 What the Model Sees
- All chat turns (user and assistant) in the current session
- All tool calls/results in the session
- All persona/mode configuration for the session
- All chat model changes/events
- All chat-related commands and their effects

---

## 📝 Notes
- For persistent or global chat logs, implement your own storage/export logic.
- For full observability, hook into all relevant events and log to a file or telemetry system.
- The public API does not expose global chat history or LLM memory outside the current session/participant.

---

**This document is auto-generated for maximum transparency and observability of the VSCode Language Model and chat system.**

---

## 🧩 Troubleshooting: Reliable Theme Change & Observed Behavior

### Reliable Theme Change (No Reload)
To reliably change the theme and confirm the result without triggering a reload (which cancels ongoing JavaScript execution), use the following approach:

```typescript
// List all available themes
const themes = vscode.extensions.all.flatMap(e => (e.packageJSON.contributes?.themes || []).map(t => t.label));
// Set the theme at the user (global) level
await vscode.workspace.getConfiguration('workbench').update('colorTheme', 'Quiet Light', vscode.ConfigurationTarget.Global);
// Confirm the active theme
const active = vscode.workspace.getConfiguration('workbench').get('colorTheme');
return { themes, active };
```

#### Example Output
```json
{
  "themes": [
    "Abyss", "Dark+", "Dark Modern", "Light+", "Light Modern", "Dark (Visual Studio)", "Light (Visual Studio)", "Dark High Contrast", "Light High Contrast", "Kimbie Dark", "Monokai", "Monokai Dimmed", "Quiet Light", "Red", "Solarized Dark", "Solarized Light", "Tomorrow Night Blue", "Tokyo Hack", "Horizon", "Horizon Italic", "Horizon Bold", "Horizon Bright", "Horizon Bright Italic", "Horizon Bright Bold", "Cyberpunk", "Sax Synth Color Theme", "Nighthawk", "NIGHT MAN", "Dark-Pastel", "One Dark Pro Rust winter sementic", "One Dark Pro Rust winter", "One Dark Pro Rust", "One Dark Pro Rust mix", "One Dark Pro Rust flat", "One Dark Pro Rust darker", "Visual Studio 2019 Dark", "Visual Studio 2019 Light", "theme-nickel", "Pastel Underwater Sun"
  ],
  "active": "Quiet Light"
}
```

### Observed Behavior
- Setting the theme at the user (global) level updates the configuration and is reflected in the API result.
- However, triggering a full window reload (`workbench.action.reloadWindow`) will cancel any ongoing JavaScript execution, so chaining these in automation is not reliable.
- The UI may not always update immediately; in some cases, a manual reload or user action is required for the change to visually take effect.
- Always confirm the available themes and the active theme programmatically to ensure the intended state.

---
