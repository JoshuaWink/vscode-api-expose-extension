# VSCode API Complete Exposure Extension

## Overview
This extension exposes the full VSCode API surface over HTTP, supporting mesh networking, dynamic endpoint registration/removal, and robust session management.

## API Endpoints

### Core Endpoints
- `GET /session` — Get current session info
- `GET /apis` — List all discovered APIs
- `POST /command/:commandId` — Execute a VSCode command
- `POST /exec` — Execute arbitrary JavaScript in the VSCode context
- `GET /workspace/folders` — List workspace folders
- `GET /editor/active` — Get info about the active editor
- `POST /window/showMessage` — Show a message in VSCode
- `GET /health` — Health check
- `GET /mesh/peers` — List mesh peers
- `POST /mesh/broadcast/:endpoint` — Broadcast to mesh peers

### Dynamic Endpoints
- `POST /add-endpoint`
  - Register a new GET endpoint at runtime.
  - Body: `{ "path": "/custom", "response": { ... } }`
  - Example:
    ```sh
    curl -X POST http://localhost:3637/add-endpoint -H 'Content-Type: application/json' -d '{"path": "/custom-hello", "response": {"message": "Hello!"}}'
    ```
- `POST /remove-endpoint`
  - Remove a previously registered dynamic endpoint.
  - Body: `{ "path": "/custom" }`
  - Example:
    ```sh
    curl -X POST http://localhost:3637/remove-endpoint -H 'Content-Type: application/json' -d '{"path": "/custom-hello"}'
    ```
- Dynamic endpoints are removed automatically when the session expires or is deregistered.

### RESTful Best Practices
- All information-only queries (no side effects) use `GET`.
- Mutating or command endpoints use `POST`.


## CLI Usage Examples
- Get session info:
  ```sh
  vscode-api-cli session --out session.json
  # or just: vscode-api-cli session
  # Output saved to temp file: /tmp/vscode-api-cli-<timestamp>.json
  ```
- List APIs:
  ```sh
  vscode-api-cli apis workspace --out myapis.json
  vscode-api-cli apis workspace
  # Output saved to temp file: /tmp/vscode-api-cli-<timestamp>.json
  ```
- Register a dynamic endpoint:
  ```sh
  curl -X POST http://localhost:3637/add-endpoint -H 'Content-Type: application/json' -d '{"path": "/custom-hello", "response": {"message": "Hello!"}}'
  ```
- Remove a dynamic endpoint:
  ```sh
  curl -X POST http://localhost:3637/remove-endpoint -H 'Content-Type: application/json' -d '{"path": "/custom-hello"}'
  ```

### Output Management
- Use `--out <file>` to save CLI output to a file.
- If omitted, output is saved to a temp file (auto-deleted after 24h).
- Temp files are cleaned up on each CLI run.

## Mesh and Session Management
- Only the session that successfully binds to a port is kept alive in the registry.
- Stale sessions and their dynamic endpoints are cleaned up automatically.

## Next Steps
1. Update OpenAPI/JSON schema to reflect new endpoints and RESTful conventions.
2. Ensure CLI tools and scripts match the documented API.
3. Implement and test across the project.

---

For more, see the repository: https://github.com/JoshuaWink/vscode-api-expose-extension
