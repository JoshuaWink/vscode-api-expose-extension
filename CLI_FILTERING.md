
## API CLI Filtering & Output Management

### apis [filter]
- You can pass an optional filter string or regex to the `apis` command.
- Example usage:
  - `vscode-api-cli apis workspace` (shows APIs with 'workspace' in category/method/description)
  - `vscode-api-cli apis 'show.*Message'` (regex match for showInformationMessage, showErrorMessage, etc)
- Filtering is case-insensitive and matches category, method, or description.

### Output to File
- Use `--out <file>` to save output to a specific file.
- If `--out` is omitted, output is saved to a temporary file in your OS temp directory (e.g., `/tmp`).
- The CLI prints the file path for easy access.

### Auto-Expiry of Temp Files
- Temporary files created by the CLI are automatically deleted if they are older than 24 hours (checked on each CLI run).
- You can also manually delete temp files (they start with `vscode-api-cli-` and end with `.json`).

### Example
```
vscode-api-cli apis workspace --out myapis.json
vscode-api-cli apis workspace
# Output saved to temp file: /tmp/vscode-api-cli-<timestamp>.json
```

---

See API.md for full endpoint details and more usage examples.
