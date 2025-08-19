# Research: How the Python/Jupyter extensions expose tools (notes + repro)

Goal
- Understand how the Microsoft Python extension (and Jupyter) expose programmatic tools (like `configure Python environment`, `get Python executable`, `install package`, `jupyter` controls) so we can recreate the pattern in our extension.

What I ran (using local `capi` CLI against the active VS Code session)

1) Find sessions:

```
./cli/bin/capi sessions
```

2) Inspect `ms-python.python` exports and package contributions:

```
./cli/bin/capi -s <SESSION_ID> exec 'const e = vscode.extensions.getExtension("ms-python.python"); if(!e) return null; await e.activate(); return {id: e.id, exportsKeys: Object.keys(e.exports||{}), packageJSON: {name: e.packageJSON.name, contributes: e.packageJSON.contributes && Object.keys(e.packageJSON.contributes)}};'
```

Observed result (example from my environment)

- id: `ms-python.python`
- exportsKeys: [
  'ready',
  'jupyter',
  'tensorboard',
  'debug',
  'settings',
  'pylance',
  'environments',
  'environment'
]
- packageJSON.contributes includes keys like `commands`, `debuggers`, `configuration`, `breakpoints`, etc.

Interpretation
- The Python extension registers functionality by returning an `exports` object from its activation. That `exports` object contains sub-APIs (e.g., `jupyter`, `environments`, `debug`) each of which exposes helper methods.
- Extensions expose CLI-like tools by exporting functions/objects under `extension.exports` and by contributing `commands` in package.json so users (and other extensions) can invoke them.
- A consumer (other extension, or our `capi exec` JS) can:
  1. Get extension handle via `vscode.extensions.getExtension('publisher.id')`.
  2. `await ext.activate()` to ensure activation.
  3. Inspect `ext.exports` for available methods/objects.
  4. Call methods: `await ext.exports.someApi.someMethod(...)`.

How to probe exported sub-APIs (examples)

- List keys of a sub-API (safe introspection):

```
./cli/bin/capi -s <SESSION_ID> exec 'const e = vscode.extensions.getExtension("ms-python.python"); await e.activate(); return Object.keys(e.exports.jupyter || {});'
```

- List types of each property on a sub-API:

```
./cli/bin/capi -s <SESSION_ID> exec 'const e = vscode.extensions.getExtension("ms-python.python"); await e.activate(); const j=e.exports.jupyter||{}; const out={}; for(const k of Object.keys(j)){ out[k]=typeof j[k]; } return out;'
```

- Call a specific method (example placeholder; method names vary):

```
./cli/bin/capi -s <SESSION_ID> exec 'const e = vscode.extensions.getExtension("ms-python.python"); await e.activate(); return await (e.exports.environments && e.exports.environments.getActiveEnvironmentPath ? e.exports.environments.getActiveEnvironmentPath() : null);'
```

Recreating the pattern in our extension (step-by-step)

1) Design the API surface (list of tools)
   - Example tools: `configurePythonEnvironment`, `getPythonExecutable`, `installPackage`, `listPackages`, `jupyter.startKernel`, `jupyter.runCell`.

2) Implement and export the API in your extension
   - In `src/extension.ts` (TypeScript) implement the methods and return an API object from `activate`:

```ts
export async function activate(context: vscode.ExtensionContext) {
  const api = {
    async getPythonExecutable() { /* find env, return path */ },
    async configurePythonEnvironment(opts) { /* open UI, set settings */ },
    jupyter: {
      async startKernel(spec) { /* start kernel */ }
    }
  };

  // Option 1 (standard): return api so the extension's exports are available
  return api;
}
```

- Alternatively, setting `extension.exports` on your extension instance also works for dynamic cases.

3) Contribute commands (optional but recommended)
   - Add `contributes.commands` entries in `package.json` so users and CLI clients can call them via `vscode.commands.executeCommand('your.extension.command')`.

4) Make the API discoverable and safe
   - Provide a small `getCapabilities()` method that lists available methods and parameters.
   - Avoid returning internal objects that expose file system handles or raw child processes.

5) Optional: expose the methods over local IPC for non-extension clients
   - Our repo contains examples of two approaches:
     - The `capi` CLI calls `/exec` on the `vscode-api-expose` HTTP server which runs JS in the extension host (powerful but must be protected).
     - The `local-tool-expose-extension` (in this repo) shows both HTTP endpoints and internal exports — prefer internal exports for extension-to-extension use.

Security and UX notes
- Avoid exposing `exec`-style arbitrary JS over unsecured channels in production.
- Prefer explicit API methods (named functions) rather than a generic JS exec endpoint.
- Use optional authentication or approve-only endpoints if exposing to external processes.

Practical next steps / probes you can run now
- Enumerate every sub-API key for `ms-python.python`:

```
./cli/bin/capi -s <SESSION_ID> exec 'const e = vscode.extensions.getExtension("ms-python.python"); await e.activate(); return Object.entries(e.exports||{}).map(([k,v])=>[k, Object.keys(v||{})]);'
```

- For each sub-API, list function names and types:

```
./cli/bin/capi -s <SESSION_ID> exec 'const e=vscode.extensions.getExtension("ms-python.python"); await e.activate(); const out={}; for(const [k,v] of Object.entries(e.exports||{})){ out[k]=Object.fromEntries(Object.entries(v||{}).map(([kk,vv])=>[kk, typeof vv])); } return out;'
```

- Try calling the specific `environments` helper methods that look relevant (inspect names first, then call methods that are `function`):

## Live probe results (ms-python.python exports)

I ran targeted probes against the active VS Code session to list the exported member names and their JS types for three sub-APIs. Results are verbatim from the extension host.

### environments

```
{
  getEnvironmentVariables: 'function',
  onDidEnvironmentVariablesChange: 'function',
  getActiveEnvironmentPath: 'function',
  updateActiveEnvironmentPath: 'function',
  onDidChangeActiveEnvironmentPath: 'function',
  resolveEnvironment: 'function',
  known: 'object',
  refreshEnvironments: 'function',
  onDidChangeEnvironments: 'function',
  onWillCreateEnvironment: 'function',
  onDidCreateEnvironment: 'function',
  createEnvironment: 'function',
  registerCreateEnvironmentProvider: 'function'
}
```

Notes: there are many callable helpers here we can safely delegate to (for example: `getActiveEnvironmentPath`, `resolveEnvironment`, `createEnvironment`, `getEnvironmentVariables`).

### jupyter

```
{ registerHooks: 'function' }
```

Notes: the `jupyter` export surface is small in this session; `registerHooks` is available to integrate with Jupyter behaviours.

### debug

```
{
  getRemoteLauncherCommand: 'function',
  getDebuggerPackagePath: 'function'
}
```

Notes: the `debug` surface here exposes helper functions for debugger packaging/launch; it does not directly expose breakpoint placement helpers — use the VS Code `vscode.debug` API for breakpoint add/remove.

---

If you'd like, I can now wire the most relevant `environments` and `debug` calls into `local-tool-expose-extension/src/extension.ts` (mapping concrete method names), run the `scripts/validate_local_tool_api.sh` validation script, and then open a small follow-up PR that updates the extension wrappers. Which should I do next? (recommended: wire `getActiveEnvironmentPath`, `resolveEnvironment`, `getEnvironmentVariables`, then run validation)

```
./cli/bin/capi -s <SESSION_ID> exec 'const e=vscode.extensions.getExtension("ms-python.python"); await e.activate(); const env=e.exports.environments||{}; return Object.keys(env);'
```

Deliverable
- This file documents the commands to run, observed exports, and a clear reproduction plan to create an extension that exposes named tools via `extension.exports` and `contributes.commands`.

Appendix: Example `capi` calls used in this session

- `./cli/bin/capi sessions`
- `./cli/bin/capi -s <SESSION_ID> exec 'const e = vscode.extensions.getExtension("ms-python.python"); if(!e) return null; await e.activate(); return {id: e.id, exportsKeys: Object.keys(e.exports||{}), packageJSON: {name: e.packageJSON.name, contributes: e.packageJSON.contributes && Object.keys(e.packageJSON.contributes)}};'`

If you want, I can now run the targeted probing commands to enumerate the `jupyter`, `environments`, and `debug` sub-APIs and append the live output to this document. Which sub-APIs should I probe first? (recommended: `environments`, then `jupyter`, then `debug`)

## Perspectives & opinions (logged)

Below are the practical perspectives and opinions I formed from the probes, plus the concrete evidence that enforces each view. These are written as implementation-focused recommendations you can act on.

- Prefer explicit exported APIs over an open `exec` endpoint.
  - Rationale: `extension.exports` provides a stable, discoverable surface other extensions can call; `exec` is powerful but unsafe if exposed externally.
  - Evidence: `capi exec` was used only for discovery (`./cli/bin/capi -s <SESSION_ID> exec 'await ext.activate(); Object.keys(ext.exports||{})'`) and the research notes show exported sub-APIs (see `Live probe results`). The file documents the command used and its outputs.

- Use `extension.exports` + `contributes.commands` as the primary exposure pattern.
  - Rationale: This is the pattern used by `ms-python.python` and is idiomatic to VS Code (discoverable and consumable by other extensions and tooling).
  - Evidence: The probe returned `exportsKeys` (including `environments`, `jupyter`, `debug`) and `packageJSON.contributes` entries; see the top of this document and the session `capi` command results.

- Delegate environment-related work to `ms-python.python.environments` when available.
  - Rationale: The Python extension already implements complex environment resolution and lifecycle helpers — reuse instead of reimplementing.
  - Evidence: `environments` export contains functions like `getActiveEnvironmentPath`, `resolveEnvironment`, `getEnvironmentVariables`, `createEnvironment` (see `Live probe results — environments` block).

- Use the core `vscode.debug` API for breakpoint placement; do not rely on `ms-python.python` for that.
  - Rationale: The `debug` sub-API present in this session exposes packaging/launcher helpers, not breakpoint control. Breakpoint creation/removal is provided by the core `vscode.debug` API (`vscode.debug.addBreakpoints` / `removeBreakpoints`).
  - Evidence: `Live probe results — debug` shows `getRemoteLauncherCommand` and `getDebuggerPackagePath` only; the research file and VS Code docs show `vscode.debug` methods for breakpoints.

- Provide a `getCapabilities()` method on your exported API and keep the surface minimal and named.
  - Rationale: Makes discovery safe for agents and avoids exposing internals or arbitrary code execution.
  - Evidence: Best-practice recommendation in this doc and the successful pattern used by Python extension (well-scoped exported objects).

- Lock down any HTTP or IPC endpoints with an allowlist or token if you enable them for non-extension clients.
  - Rationale: The `capi exec` approach is useful for development but dangerous in production without auth.
  - Evidence: This repo includes `vscode-api-expose` with `/exec` used for discovery; the research doc cautions about securing `exec`-style endpoints.

---

If you want me to log these same perspectives into a new `notes/PERSPECTIVES.md` file or to immediately wire the recommended `environments` methods into `local-tool-expose-extension/src/extension.ts`, say which you'd prefer: `append-only` (new file) or `wire-and-validate` (implement + run validation). 
