VSCode API Expose Bridge

This extension starts a UNIX socket inside the extension host which accepts newline-delimited JSON requests of the form:

{ id, action: 'exec', code: '<js code>', payload: <object> }

It executes the JS in an async function with access to `vscode` and `payload`, and returns a newline-delimited JSON response.
