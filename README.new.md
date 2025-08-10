Dedicated to my God and Father for leading me through this project, to my Wife for her support and patience, and to you--the devs--who will do great things with this tool. I hope this tool serves you well in your VSCode adventures!

# capi: The Minimal VSCode Kernel CLI


## Keywords

- vscode api
- api exposure
- scripting
- automation
- session targeting
- extension
- mcp server
- copilot integration
- agent integration
- rapid prototyping
- developer tools
- code automation
- external control
- creativity

---

## Philosophy

capi is a minimal, scriptable kernel for VSCode automation. It exposes all VSCode APIs, commands, and session controls as raw, composable primitives—nothing more. There are no enforced workflows, no opinions, and no abstractions. The community and users define higher-level patterns, plugins, and conventions.


## What is capi?

capi (short for Code-API) is a VSCode extension and CLI that exposes the full VSCode API for external scripting and automation. It can target specific sessions, making it possible to control and automate any VSCode window from the outside. capi is designed for developers, agents, and anyone who wants to take VSCode to the next level—rapid prototyping, agent integration, and creative automation are all possible. The only limit is your creativity.

capi is also the foundation for the MCP (Model Context Protocol) server and tools, which use the official `vscodeAPI` as their reference. This means:
- Microsoft maintains the API surface and docs (via Copilot and `vscodeAPI`)
- MCP lets any agent, code assistant, or tool connect to VSCode, see everything Copilot can, and more
- The intent is to supercharge Copilot and allow any assistant to interact with VSCode via its APIs and code at runtime

---

## Key Principles

- **Expose Everything, Constrain Nothing:** All VSCode APIs, commands, and session controls are available as primitives.
- **No Forced Flows:** capi does not enforce any workflow or opinionated UX. Users compose and automate as they wish.
- **Transparent Output:** All results are output in a composable format (JSON by default).
- **Community-Driven Abstraction:** Higher-level patterns, plugins, and recipes are defined by users and the community—not by capi.
- **Official Discovery:** All API discovery, documentation, and evolution are handled by the official `vscodeAPI` (maintained by Microsoft and surfaced in GitHub Copilot).

## Core Commands

| Command                | Description                                      | Example Usage                                      |
|------------------------|--------------------------------------------------|----------------------------------------------------|
| `capi sessions`        | List all active VSCode sessions                  | `capi sessions`                                    |
| `capi apis`            | List all available VSCode APIs                   | `capi apis`                                        |
| `capi exec <js>`       | Execute arbitrary JS in VSCode extension host    | `capi exec "vscode.commands.executeCommand('...')"` |
| `capi command <id>`    | Run a VSCode command by ID                       | `capi command editor.action.selectAll`             |
| `capi message <text>`  | Show a message in VSCode                         | `capi message "Hello"`                             |
| `capi batch <file>`    | Run a batch of commands from a file              | `capi batch script.txt`                            |
| `capi --session <id>`  | Target a specific session for any command        | `capi apis --session <id>`                         |
| `capi --json`          | Output all results as JSON                       | `capi apis --json`                                 |

## Intent

- **capi is not a framework.** It is a kernel: a foundation for automation, scripting, and control.
- **Discovery and documentation** are delegated to the official `vscodeAPI` (GitHub Copilot, Microsoft-maintained).
- **Users are empowered** to build, share, and evolve their own workflows, plugins, and recipes.

## Example

```sh
# List all sessions
capi sessions

# List all APIs for a session
capi apis --session <session-id>

# Execute a VSCode command
capi exec "vscode.commands.executeCommand('editor.action.selectAll')" --session <session-id>
```

## Contributing

- Share your scripts, plugins, and recipes with the community.
- Use the official `vscodeAPI` for discovery and documentation.
- Help keep capi minimal, composable, and unconstrained.

---

*Let the community define the "how." capi just provides the "can."*
