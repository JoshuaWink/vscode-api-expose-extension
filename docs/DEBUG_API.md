# VS Code Debug API (live probe)

This document captures a live probe of the `vscode.debug` surface from the active extension host session and provides quick examples for the debugging wrapper.

## Probe results (live)

- Keys discovered on `vscode.debug`:

```
activeDebugConsole
activeDebugSession
activeStackItem
addBreakpoints
asDebugSourceUri
breakpoints
onDidChangeActiveDebugSession
onDidChangeActiveStackItem
onDidChangeBreakpoints
onDidReceiveDebugSessionCustomEvent
onDidStartDebugSession
onDidTerminateDebugSession
registerDebugAdapterDescriptorFactory
registerDebugAdapterTrackerFactory
registerDebugConfigurationProvider
registerDebugVisualizationProvider
registerDebugVisualizationTreeProvider
removeBreakpoints
startDebugging
stopDebugging
```

- Current breakpoints (sample):

```
[ { type: 'SourceBreakpoint', location: { uri: 'file:///.../src/extension.ts', line: 10 } } ]
```

- Active debug session: null (no active session in this probe)
- Sessions list: []

## Recommended wrapper API (what your extension should expose)

- setBreakpoint(filePath: string, lineOneBased: number, condition?: string)
- removeBreakpoint(filePath: string, lineOneBased: number)
- listBreakpoints(): Breakpoint[]
- startDebugging(folder: WorkspaceFolder | undefined, config: DebugConfiguration)
- stopDebugging(): Promise<boolean>
- sessionCustomRequest(method: string, args?: any): Promise<any>
- getStackTrace(threadId: number, startFrame?: number, levels?: number)
- evaluate(expression: string, frameId?: number)

## Quick usage examples (to run inside extension host)

- Add a source breakpoint (example):

```ts
const uri = vscode.Uri.file('/path/to/file.ts');
const bp = new vscode.SourceBreakpoint(new vscode.Location(uri, new vscode.Position(lineZeroBased, 0)));
vscode.debug.addBreakpoints([bp]);
```

- Remove a breakpoint (example):

```ts
// Assume `bp` is an existing breakpoint object
vscode.debug.removeBreakpoints([bp]);
```

- Start debugging (launch):

```ts
await vscode.debug.startDebugging(workspaceFolder, debugConfiguration);
```

- Send raw DAP request via active session (stepping, continue, evaluate, etc.):

```ts
const session = vscode.debug.activeDebugSession;
if (session) {
  // example: continue thread
  await session.customRequest('continue', { threadId });
  // example: evaluate
  const evalRes = await session.customRequest('evaluate', { expression: 'x + 1', frameId });
}
```

## Notes and caveats

- Not all debug adapters support every DAP request; always guard with try/catch and inspect adapter capabilities when available.
- Use `onDidChangeBreakpoints` and other events to maintain UI state.
- Prefer using `vscode.debug` helpers for breakpoints and `DebugSession.customRequest` for session-level DAP commands (step, continue, evaluate).

---

This file was generated from a live probe of the current extension host using the project's `capi` CLI.
