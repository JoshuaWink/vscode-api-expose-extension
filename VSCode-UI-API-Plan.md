# VSCode UI API Interaction Plan

## Goal
Explore and document all major VSCode UI APIs for automation and remote control, focusing on user-facing interactions.

## Core UI APIs to Explore

### 1. Message and Dialog APIs
- `window.showInformationMessage`
- `window.showWarningMessage`
- `window.showErrorMessage`
- `window.showInputBox`
- `window.showQuickPick`
- `window.showOpenDialog`, `window.showSaveDialog`
- `window.showWorkspaceFolderPick`

### 2. Editor and Document APIs
- `window.activeTextEditor`, `window.visibleTextEditors`
- `window.showTextDocument`
- `window.createTextEditorDecorationType`
- `window.setStatusBarMessage`
- `window.withProgress`

### 3. Status Bar and Progress
- `window.createStatusBarItem`
- `window.withProgress`

### 4. Panels, Webviews, and Custom UI
- `window.createWebviewPanel`
- `window.registerWebviewPanelSerializer`

### 5. Notifications and Output
- `window.showNotification` (not direct, but via showMessage)
- `window.createOutputChannel`

### 6. Window and Workspace Management
- `window.showWorkspaceFolderPick`
- `window.showWindowPicker` (if available)
- `window.onDidChangeActiveTextEditor`
- `window.onDidChangeVisibleTextEditors`

### 7. QuickInput API (Advanced)
- `window.createQuickPick`
- `window.createInputBox`
- `QuickInput.show()`, `QuickInput.busy`, `QuickInput.buttons`

## Usage Patterns and Scenarios
- Chaining UI prompts (e.g., input → quick pick → confirm)
- Conditional UI flows (e.g., show error if input invalid)
- Async UI updates (progress, busy indicators)
- Editor decorations and inline UI
- Status bar and notifications for background tasks
- Webview for custom UI/remote control

## Next Steps
1. Prototype each API via /exec or /command endpoint.
2. Document example payloads and expected results.
3. Note any limitations or special behaviors.
4. Build a UI automation script library for remote CLI.

---

## Checklist
- [ ] showInformationMessage
- [ ] showWarningMessage
- [ ] showErrorMessage
- [ ] showInputBox
- [ ] showQuickPick
- [ ] showOpenDialog
- [ ] showSaveDialog
- [ ] showWorkspaceFolderPick
- [ ] showTextDocument
- [ ] createTextEditorDecorationType
- [ ] setStatusBarMessage
- [ ] withProgress
- [ ] createStatusBarItem
- [ ] createWebviewPanel
- [ ] createOutputChannel
- [ ] createQuickPick
- [ ] createInputBox

---

Add notes and results as you test each API.
