# capi (VSCode API CLI)

Universal CLI for VSCode API mesh automation and scripting.

## Install Globally

```sh
cd cli
npm run install-global
```

This makes `capi` and `code-api` available everywhere.

## Usage

```sh
capi [command] [options]
```

### Common Commands

- `capi sessions` — List all available VSCode sessions
- `capi apis` — List all available VSCode APIs
- `capi command <commandId> [args...]` — Execute a VSCode command
- `capi exec <js>` — Execute JavaScript in VSCode context
- `capi message <text>` — Show a message in VSCode
- `capi batch <file>` — Execute commands from a file

### Options

- `-s, --session <id>` — Target a specific session
- `-w, --workspace <path>` — Target by workspace path
- `-j, --json` — Output in JSON format
- `-v, --verbose` — Verbose output

## Examples

```sh
capi sessions
capi apis
capi command workbench.action.reloadWindow
capi exec "return vscode.env.appName"
capi message "Hello from capi!"
```

## Uninstall

```sh
cd cli
npm run uninstall-global
```

---

For more, see the main project: https://github.com/JoshuaWink/vscode-api-expose-extension
