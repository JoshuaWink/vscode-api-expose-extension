@server.tool(name="problems", description="Return basic diagnostics (problems) for workspace files.")
    def problems(payload: dict = None) -> str:
        code = (
            "const diags = [];"
            + "for (const [uri, ds] of vscode.languages.getDiagnostics()) {"
            + " diags.push({uri: uri.toString(), diagnostics: ds.map(d => ({message: d.message, severity: d.severity}))}); }"
            + "return diags;"
        )
        return capi_exec(code=code)

    @server.tool(name="changes", description="Return simple git change summary for workspace (if available).")
    def changes(payload: dict = None) -> str:
        # Best-effort: call git on workspace root. Fallback if no workspace.
        try:
            # ask the extension for workspace folders and return git status for first folder
            code = (
                "const ws = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];"
                "if (!ws) return 'No workspace';"
                "const p = ws.uri.fsPath;"
                "return p;"
            )
            workspace_path = capi_exec(code=code)
            # if we get a string path back, try local git status via python subprocess
            if workspace_path and 'No workspace' not in workspace_path:
                import shlex
                p = workspace_path.strip().strip('"')
                result = subprocess.run(['git', '-C', p, 'status', '--porcelain'], capture_output=True, text=True)
                return result.stdout if result.returncode == 0 else result.stderr
            return workspace_path
        except Exception as e:
            return f"Error: {e}"

    @server.tool(name="testFailure", description="Return last test failure info (best-effort).")
    def testFailure(payload: dict = None) -> str:
        # This is environment-dependent; try to read workspace/test output channels via exec
        code = "return (globalThis._lastTestFailure || null);"
        return capi_exec(code=code)

    @server.tool(name="terminalSelection", description="Return active terminal selection (name).")
    def terminalSelection(payload: dict = None) -> str:
        code = (
            "const t = vscode.window.activeTerminal; return t ? {name: t.name, processId: t.processId} : null;"
        )
        return capi_exec(code=code)

    @server.tool(name="terminalLastCommand", description="Return last command run in the active terminal (best-effort).")
    def terminalLastCommand(payload: dict = None) -> str:
        # Best-effort: the extension environment may not retain terminal history; return last selection if available.
        code = "return globalThis._lastTerminalCommand || null;"
        return capi_exec(code=code)

    @server.tool(name="openSimpleBrowser", description="Open a URL in the simple browser and return success.")
    def openSimpleBrowser(url: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            url = payload.get('url', url)
        if not url:
            return 'Error: missing url'
        code = f"await vscode.env.openExternal(vscode.Uri.parse({json.dumps(url)})); return true;"
        return capi_exec(code=code)

    @server.tool(name="fetch", description="Fetch a URL from the extension host (best-effort).")
    def fetch_url(url: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            url = payload.get('url', url)
        if not url:
            return 'Error: missing url'
        code = (
            "const r = await fetch(" + json.dumps(url) + ");"
            "const text = await r.text();"
            "return {status: r.status, body: text.slice(0, 10000)};"
        )
        return capi_exec(code=code)

    @server.tool(name="findTestFiles", description="Find files that look like tests in the workspace.")
    def findTestFiles(pattern: str = "**/*{test,spec}*.{js,ts,py}" , payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            pattern = payload.get('pattern', pattern)
        code = f"return (await vscode.workspace.findFiles('{pattern}')).map(u => u.fsPath);"
        return capi_exec(code=code)

    @server.tool(name="searchResults", description="Perform a simple text search across workspace files (returns matching paths).")
    def searchResults(query: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            query = payload.get('query', query)
        if not query:
            return 'Error: missing query'
        code = (
            "const q = " + json.dumps(query) + ";"
            + "const uris = await vscode.workspace.findFiles('**/*');"
            + "const out = [];"
            + "for (const u of uris) { const d = await vscode.workspace.openTextDocument(u); if (d.getText().includes(q)) out.push(u.fsPath); }"
            + "return out;"
        )
        return capi_exec(code=code)

    @server.tool(name="githubRepo", description="Return GitHub repo information if available via workspace/git remote.")
    def githubRepo(payload: dict = None) -> str:
        try:
            code = ("const ws = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];"
                    "if (!ws) return null; return ws.uri.fsPath;")
            ws = capi_exec(code=code)
            if not ws or 'No workspace' in ws:
                return ws
            p = ws.strip().strip('"')
            result = subprocess.run(['git', '-C', p, 'remote', '-v'], capture_output=True, text=True)
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return f"Error: {e}"

    @server.tool(name="extensions", description="List installed extensions (id and active state).")
    def extensions(payload: dict = None) -> str:
        code = "return vscode.extensions.all.map(e => ({id: e.id, isActive: e.isActive}));"
        return capi_exec(code=code)

    @server.tool(name="runTests", description="Run tests via a task or command (best-effort).")
    def runTests(taskName: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            taskName = payload.get('task', taskName)
        if not taskName:
            return capi(command='command', args=['workbench.action.tasks.test'])
        # try to run a named task
        return capi(command='command', args=[f'workbench.action.tasks.runTask', taskName])

    @server.tool(name="editFiles", description="Apply a simple edit to a file: path, position, text.")
    def editFiles(filePath: str = None, insertText: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            filePath = payload.get('filePath', filePath)
            insertText = payload.get('text', insertText)
        if not filePath or insertText is None:
            return 'Error: filePath and text required'
        code = (
            "const uri = vscode.Uri.file(" + json.dumps(filePath) + ");"
            "const doc = await vscode.workspace.openTextDocument(uri);"
            "const ed = await vscode.window.showTextDocument(doc);"
            "await ed.edit(e => e.insert(new vscode.Position(0,0), " + json.dumps(insertText) + "));"
            "return true;"
        )
        return capi_exec(code=code)

    @server.tool(name="runNotebooks", description="Run a notebook (best-effort placeholder).")
    def runNotebooks(payload: dict = None) -> str:
        return 'runNotebooks: not implemented in generic wrapper; please call a specific task or command.'

    @server.tool(name="search", description="Alias for searchResults")
    def search(query: str = None, payload: dict = None) -> str:
        return searchResults(query=query, payload=payload)

    @server.tool(name="new", description="Create a new untitled file (open new).")
    def new(payload: dict = None) -> str:
        return capi(command='command', args=['workbench.action.files.newUntitledFile'])
