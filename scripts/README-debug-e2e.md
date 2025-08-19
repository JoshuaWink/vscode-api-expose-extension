Debug E2E test

Purpose: run this inside the running extension host to exercise `extension.exports.debug` if available, otherwise use `vscode.debug` directly.

How to run (example using the repo's `capi` CLI):

1. Find your extension host session id (used earlier). Example: `85b467f3-52b8-4834-a148-853b2a3fae94`.
2. Run:

```sh
./cli/bin/capi -s <SESSION_ID> exec "require('/workspace/scripts/debug_e2e_exec.js')"
```

Replace `<SESSION_ID>` with your session id. The script writes `.capi-debug-e2e.json` into the workspace root with the result.

Expected output file: `.capi-debug-e2e.json` containing an object with `method` (which path was used), `before`, and `after` arrays of serialized breakpoints.
