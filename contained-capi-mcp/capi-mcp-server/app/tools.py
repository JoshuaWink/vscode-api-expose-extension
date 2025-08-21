"""
Tool definitions for code-mcp-server using FastMCP decorators.
"""

import subprocess
import os
import select
import threading
import uuid
import sys
import json
import re
import socket
import uuid
import os

# Note: prefer in-extension bridge for all VSCode operations. HTTP client removed.

# Local PTY manager: allow MCP server to spawn and manage real shell PTYs locally.
_local_ptys = {}
# Maximum total characters to retain per PTY buffer. If exceeded, oldest chars are trimmed.
_MAX_BUFFER_CHARS = 200000


def _discover_bridge_socket(explicit: str | None = None) -> str | None:
    """Return the first existing bridge socket path or None.
    Checks, in order: explicit, workspace .vscode socket from CWD, ancestor .vscode sockets,
    home fallback, /tmp fallback. This centralizes discovery logic so tools can reuse it.
    """
    try:
        candidates = []
        if explicit:
            candidates.append(explicit)
        # workspace-relative .vscode (from MCP cwd)
        try:
            candidates.append(os.path.join(os.getcwd(), '.vscode', 'vscode-api-expose.sock'))
        except Exception:
            pass
        # walk up from this file's directory to try to find the repository/workspace root
        start_dir = os.path.abspath(os.path.dirname(__file__))
        for i in range(0, 6):
            try:
                ancestor = os.path.abspath(os.path.join(start_dir, *(['..'] * i)))
                candidates.append(os.path.join(ancestor, '.vscode', 'vscode-api-expose.sock'))
            except Exception:
                continue
        candidates.append(os.path.expanduser('~/.vscode_api_expose.sock'))
        candidates.append('/tmp/vscode-api-expose.sock')

        for p in candidates:
            try:
                if p and os.path.exists(p):
                    return p
            except Exception:
                continue
    except Exception:
        return None
    return None
    return None

def _pty_reader(pty_id: str, master_fd: int, stop_event: threading.Event, buffer: list, lock: threading.Lock):
    try:
        while not stop_event.is_set():
            r, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd in r:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                text = data.decode(errors='replace')
                with lock:
                    buffer.append(text)
                    # Enforce a max buffer size by trimming oldest content if needed
                    try:
                        total = sum(len(s) for s in buffer)
                        if total > _MAX_BUFFER_CHARS:
                            # Join and keep only the last _MAX_BUFFER_CHARS characters
                            joined = ''.join(buffer)
                            kept = joined[-_MAX_BUFFER_CHARS:]
                            buffer.clear()
                            buffer.append(kept)
                    except Exception:
                        # best-effort trimming; ignore failures
                        pass
    except Exception:
        pass


def register_tools(server):
    @server.tool(name="execute_vscode_arbitrary_js", description="Run code via the code CLI /exec endpoint and return its output. Accepts a JSON object: {code, args, shell, cwd}.")
    def code_execute(
        code: str = None,
        args: list = None,
        shell: bool = False,
        cwd: str = None,
        payload: dict = None
    ) -> str:
        """
        Runs code using the code CLI /exec endpoint and returns the output. Accepts a JSON object with keys: code, args, shell, cwd.
        """
        import shlex
        try:
            # Support both direct params and a single JSON payload
            if payload and isinstance(payload, dict):
                code = payload.get("code", code)
                args = payload.get("args", args)
                shell = payload.get("shell", shell)
                cwd = payload.get("cwd", cwd)
            if not code:
                return "Error: No code provided."
            # Prefer the in-extension unix socket bridge; no HTTP fallback.
            socket_path = None
            if payload and isinstance(payload, dict):
                socket_path = payload.get('socket_path') or payload.get('socketPath')
            discovered = _discover_bridge_socket(socket_path)
            if not discovered:
                return json.dumps({ 'ok': False, 'error': 'bridge-socket-not-found', 'attempted': socket_path })
            bridge_result = _bridge_exec(code, payload=payload or {}, socket_path=discovered)
            if bridge_result is not None:
                return bridge_result
            return json.dumps({ 'ok': False, 'error': 'bridge-exec-failed' })
        except Exception as e:
            print(f"[code_execute tool error] {e}", file=sys.stderr)
            return f"Error: {e}"

    @server.tool(name="execute_vscode_api_command", description="Run a code — exposed vsCode API — command and return its output. Accepts a JSON object: {command, args, shell, cwd}.")
    def code(
        command: str = None,
        args: list = None,
        shell: bool = False,
        cwd: str = None,
        payload: dict = None
    ) -> str:
        """
        Runs a code CLI command and returns the output. Accepts a JSON object with keys: command, args, shell, cwd.
        """
        import shlex
        try:
            # Support both direct params and a single JSON payload
            if payload and isinstance(payload, dict):
                command = payload.get("command", command)
                args = payload.get("args", args)
                shell = payload.get("shell", shell)
                cwd = payload.get("cwd", cwd)
            if not command:
                command = "--help"
            # Bridge-only command execution
            socket_path = None
            if payload and isinstance(payload, dict):
                socket_path = payload.get('socket_path') or payload.get('socketPath')
            discovered = _discover_bridge_socket(socket_path)
            if not discovered:
                return json.dumps({ 'ok': False, 'error': 'bridge-socket-not-found', 'attempted': socket_path })
            # Build JS that calls vscode.commands.executeCommand and let _bridge_exec wrap it
            js_args = []
            if args is None:
                js_args = []
            elif isinstance(args, str):
                js_args = [args]
            else:
                js_args = list(args)
            try:
                js_args_json = json.dumps(js_args)
            except Exception:
                js_args_json = json.dumps([str(a) for a in js_args])
            call_code = f"return await vscode.commands.executeCommand({json.dumps(command)}, ...{js_args_json});"
            bridge_result = _bridge_exec(call_code, payload=payload or {}, socket_path=discovered)
            if bridge_result is not None:
                return bridge_result
            return json.dumps({ 'ok': False, 'error': 'bridge-exec-failed' })
        except Exception as e:
            print(f"[code tool error] {e}", file=sys.stderr)
            return f"Error: {e}"

    @server.tool(name="help_code_cli", description="Show help for the code CLI, listing all available commands and options.")
    def vscode_execute_help(payload: dict = None) -> str:
        """Return a help-like listing of available VS Code commands/APIs.
        Replaces the old subprocess-based `vscode_execute --help` call by
        querying the injected HTTP client for available APIs.
        Accepts an optional `payload` dict with `sessionId` and `workspace`.
        """
        try:
            # Bridge-only: request commands via bridge
            socket_path = payload.get('socket_path') if payload and isinstance(payload, dict) else None
            discovered = _discover_bridge_socket(socket_path)
            if not discovered:
                return json.dumps({ 'ok': False, 'error': 'bridge-socket-not-found', 'attempted': socket_path })
            code = "return await vscode.commands.getCommands(true);"
            bridge_result = _bridge_exec(code, payload=payload or {}, socket_path=discovered)
            if bridge_result is not None:
                return bridge_result
            return json.dumps({ 'ok': False, 'error': 'bridge-exec-failed' })
        except Exception as e:
            print(f"[vscode_execute_help tool error] {e}", file=sys.stderr)
            return f"Error: {e}"

    # ------------------------------------------------------------------
    # High-level wrappers: expose common VS Code capabilities as MCP tools.
    # These call the existing `code_execute` or `code` helpers above so MCP
    # clients can request workspace/command operations via the code bridge.
    # Each tool accepts either direct params or a `payload` dict for
    # flexibility (string args or structured payloads).
    # ------------------------------------------------------------------

    @server.tool(name="get_vscode_apis", description="Return a list of available vscode commands (getCommands).")
    def vscodeAPI(payload: dict = None) -> str:
        # expose vscode.commands.getCommands(true)
        code = "return await vscode.commands.getCommands(true);"
        return code_execute(code=code)

    @server.tool(name="execute_vscode_bridge_js", description="Run JS inside the extension host using the in-extension socket bridge. Returns parsed JSON result.")
    def bridge_exec_js(code: str = None, payload: dict = None, socket_path: str = None, timeout: float = 5.0) -> str:
        """Execute JS via the unix-domain socket bridge started by the `extension-bridge` extension.
        Parameters:
          - code: JS string to execute (async function body)
          - payload: optional payload passed to the JS
          - socket_path: optional explicit socket path; defaults to workspace .vscode/vscode-api-expose.sock
        Returns:
          JSON string of the bridge response.
        """
        try:
            if payload and isinstance(payload, dict) and not code:
                code = payload.get('code')
            if not code:
                return 'Error: code required'

            # Build candidate socket paths to try. MCP server CWD may differ
            # from the workspace root, so try several likely locations.
            candidates = []
            explicit = socket_path or (payload.get('socket_path') if payload and isinstance(payload, dict) else None)
            if explicit:
                candidates.append(explicit)
            # workspace-relative .vscode (from MCP cwd)
            candidates.append(os.path.join(os.getcwd(), '.vscode', 'vscode-api-expose.sock'))
            # Walk up from this file's directory to try to find the repository/workspace root
            start_dir = os.path.abspath(os.path.dirname(__file__))
            for i in range(0, 6):
                try:
                    ancestor = os.path.abspath(os.path.join(start_dir, *(['..'] * i)))
                    candidates.append(os.path.join(ancestor, '.vscode', 'vscode-api-expose.sock'))
                except Exception:
                    continue
            # home and tmp fallbacks
            candidates.append(os.path.expanduser('~/.vscode_api_expose.sock'))
            candidates.append('/tmp/vscode-api-expose.sock')

            req = { 'id': str(uuid.uuid4()), 'action': 'exec', 'code': code, 'payload': payload }
            data = json.dumps(req) + '\n'

            last_err = None
            attempted = {}
            for path in candidates:
                try:
                    if not path:
                        attempted[path] = 'empty'
                        continue
                    # quick existence check
                    try:
                        exists = os.path.exists(path)
                    except Exception as ex:
                        exists = False
                        attempted[path] = f'existence-check-error:{ex}'
                    if not exists:
                        attempted[path] = 'missing'
                        continue
                    # try connect
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    sock.settimeout(float(timeout) if timeout is not None else 5.0)
                    try:
                        sock.connect(path)
                        sock.sendall(data.encode('utf8'))
                        buf = b''
                        while True:
                            ch = sock.recv(4096)
                            if not ch:
                                break
                            buf += ch
                            if b'\n' in buf:
                                line, _, rest = buf.partition(b'\n')
                                try:
                                    resp = json.loads(line.decode('utf8'))
                                    return json.dumps({ 'socket': path, 'response': resp })
                                except Exception:
                                    return json.dumps({ 'socket': path, 'response_raw': line.decode('utf8', errors='replace') })
                        if buf:
                            try:
                                return json.dumps({ 'socket': path, 'response': json.loads(buf.decode('utf8')) })
                            except Exception:
                                return json.dumps({ 'socket': path, 'response_raw': buf.decode('utf8', errors='replace') })
                        attempted[path] = 'no-response'
                    finally:
                        try: sock.close()
                        except: pass
                except Exception as e:
                    last_err = e
                    attempted[path] = f'error:{e}'

            # If we fall through, none of the candidates worked. Return diagnostics.
            return json.dumps({ 'id': req['id'], 'ok': False, 'error': 'socket-not-found-or-unresponsive', 'attempted': attempted, 'last_error': str(last_err) if last_err else None })
        except Exception as e:
            return f'Error: {e}'

    def _bridge_exec(code_body: str, payload: dict | None = None, socket_path: str | None = None, timeout: float = 5.0) -> str | None:
        """Wrap `code_body` in an async IIFE and execute it via the in-extension bridge if available.
        Returns the bridge response (string) or None if bridge not available or an error occurred.
        """
        try:
            wrapper = f"(async function(){{\n{code_body}\n}})();"
            discovered = _discover_bridge_socket(socket_path)
            if not discovered:
                return None
            try:
                return bridge_exec_js(code=wrapper, payload=payload or {}, socket_path=discovered, timeout=timeout)
            except Exception:
                return None
        except Exception:
            return None

    # Helper: build a small JS wrapper that iterates descriptors and runs a provided body snippet
    def _make_breakpoints_js(descriptors_json: str, body_snippet: str) -> str:
        """Return a JS IIFE that iterates `descriptors` and executes `body_snippet` for each descriptor.
        `body_snippet` should contain JS that references `d` and may push to `created`.
        """
        return (
            "(function(){ const descriptors = "
            + descriptors_json
            + "; const created = []; for (const d of descriptors) { try { "
            + body_snippet
            + " } catch(e) { /* ignore */ } } return created; })()"
        )

    
    @server.tool(name="debug_session_start", description="Start a debug session by configuration name or DebugConfiguration object.")
    def startDebugging(config: str = None, payload: dict = None) -> str:
        """Start a debug session. `config` may be a configuration name (string) or a DebugConfiguration object (dict).
        If `payload` is provided it may include `config` or `sessionId`/`workspace` routing keys.
        """
        if payload and isinstance(payload, dict):
            config = payload.get('config', config)
        if not config:
            return 'Error: config (name or DebugConfiguration) required'
        # If config is a dict, serialize to JSON; strings will be quoted correctly
        try:
            cfg_js = json.dumps(config)
        except Exception:
            cfg_js = json.dumps(str(config))
        code = f"return await vscode.debug.startDebugging(undefined, {cfg_js});"
        return code_execute(code=code, payload=payload)

    @server.tool(name="debug_session_stop", description="Stop the active debug session (if any).")
    def stopDebugging(payload: dict = None) -> str:
        """Stops the active debug session. Returns the result (true/false) or an error string."""
        code = "return await vscode.debug.stopDebugging();"
        return code_execute(code=code, payload=payload)

    @server.tool(name="debug_session_list", description="Return a list of active debug sessions (id, name, type).")
    def listDebugSessions(payload: dict = None) -> str:
        """Returns active debug sessions as an array of {id, name, type}."""
        code = "return vscode.debug.sessions.map(s => ({ id: s.id, name: s.name, type: s.type }));"
        return code_execute(code=code, payload=payload)

    # @server.tool(name="search_vscode_apis", description="Search available VS Code API commands and return matches.")
    # def vscodeAPI_search(query: str = None, payload: dict = None) -> str:
    #     """Search the API list (from `vscode_client.get_apis`) for the provided query string.
    #     Returns an array of matching API entries (strings or objects).
    #     """
    #     if payload and isinstance(payload, dict):
    #         query = payload.get('query', query)
    #     if not query:
    #         return 'Error: query required'
    #     try:
    #         apis = vscode_client.get_apis(
    #             session_id=payload.get('sessionId') if payload else None,
    #             workspace=payload.get('workspace') if payload else None
    #         )
    #         q = query.lower()
    #         matches = [a for a in apis if q in (a if isinstance(a, str) else json.dumps(a)).lower()]
    #         return json.dumps(matches)
    #     except Exception as e:
    #         print(f"[vscodeAPI_search tool error] {e}", file=sys.stderr)
    #         return f"Error: {e}"

    @server.tool(name="debug_breakpoints_add", description="Add breakpoints. Accepts array of breakpoint descriptors: {uri, line, column?, enabled?, condition?, hitCondition?, logMessage?}.")
    def addBreakpoints(breakpoints: list = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            breakpoints = payload.get('breakpoints', breakpoints)
        if not breakpoints:
            return 'Error: breakpoints required'
        try:
            # Serialize Python list to JSON for embedding into JS
            bps_json = json.dumps(breakpoints)
        except Exception:
            bps_json = json.dumps(str(breakpoints))
        # JS: convert descriptors into SourceBreakpoint instances where possible
        try:
            desc_json = json.dumps(breakpoints)
        except Exception:
            desc_json = json.dumps(str(breakpoints))
        body = (
            "if (d.uri) { const uri = vscode.Uri.parse(d.uri); const pos = new vscode.Position(d.line||0, d.column||0); "
            "const bp = new vscode.SourceBreakpoint(new vscode.Location(uri, new vscode.Range(pos, pos)), d.enabled!==false, d.condition, d.hitCondition, d.logMessage); vscode.debug.addBreakpoints([bp]); created.push({uri:d.uri,line:d.line,enabled:bp.enabled,condition:bp.condition||null,hitCondition:bp.hitCondition||null,logMessage:bp.logMessage||null}); }"
        )
        code = _make_breakpoints_js(desc_json, body)
        return code_execute(code=code, payload=payload)

    @server.tool(name="debug_breakpoints_remove", description="Remove breakpoints. Accepts array of descriptors {uri,line} to match existing breakpoints.")
    def removeBreakpoints(breakpoints: list = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            breakpoints = payload.get('breakpoints', breakpoints)
        if not breakpoints:
            return 'Error: breakpoints required'
        try:
            rb_json = json.dumps(breakpoints)
        except Exception:
            rb_json = json.dumps(str(breakpoints))
        code = (
            "(function(){ const toRemove = " + rb_json + "; const found = []; const existing = vscode.debug.breakpoints.slice(); for (const d of toRemove) { for (const b of existing) { try { const loc = b.location; if (loc && loc.uri && d.uri && loc.uri.toString() === d.uri && loc.range && d.line !== undefined && loc.range.start.line === d.line) { found.push(b); } } catch(e){} } } if (found.length) vscode.debug.removeBreakpoints(found); return found.map(b=>({ location: b.location?{uri:b.location.uri.toString(),line:b.location.range.start.line}:null, enabled: b.enabled })); })()"
        )
        return code_execute(code=code, payload=payload)

    @server.tool(name="debug_breakpoints_list", description="List current breakpoints.")
    def listBreakpoints(payload: dict = None) -> str:
        code = (
            "return vscode.debug.breakpoints.map(b => ({ enabled: b.enabled, condition: b.condition || null, hitCondition: b.hitCondition || null, logMessage: b.logMessage || null, location: b.location ? { uri: b.location.uri.toString(), line: b.location.range.start.line, character: b.location.range.start.character } : null }));"
        )
        return code_execute(code=code, payload=payload)

    # ------------------------------------------------------------------
    # Specialized breakpoint creators: source, function, conditional, logpoint, data
    # Each tool is a small wrapper that builds a single-descriptor payload and
    # delegates to the VS Code API via `code_execute`.
    # ------------------------------------------------------------------

    @server.tool(name="debug_breakpoint_add_source", description="Add a source breakpoint by uri and line (optional column).")
    def add_breakpoint_source(uri: str = None, line: int = None, column: int = 0, enabled: bool = True, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            uri = payload.get('uri', uri)
            line = payload.get('line', line)
            column = payload.get('column', column)
            enabled = payload.get('enabled', enabled)
        if not uri or line is None:
            return 'Error: uri and line required'
        desc = [{ 'uri': uri, 'line': int(line), 'column': int(column) if column is not None else 0, 'enabled': bool(enabled) }]
        try:
            try:
                desc_json = json.dumps(desc)
            except Exception:
                desc_json = json.dumps(str(desc))
            body = (
                "const uri = vscode.Uri.parse(d.uri); const pos = new vscode.Position(d.line||0, d.column||0); const bp = new vscode.SourceBreakpoint(new vscode.Location(uri, new vscode.Range(pos, pos)), d.enabled!==false); vscode.debug.addBreakpoints([bp]); created.push({uri:d.uri,line:d.line,enabled:bp.enabled});"
            )
            code = _make_breakpoints_js(desc_json, body)
            return code_execute(code=code, payload=payload)
        except Exception as e:
            return f"Error: {e}"

    @server.tool(name="debug_breakpoint_add_function", description="Add a function breakpoint by function name.")
    def add_breakpoint_function(function_name: str = None, enabled: bool = True, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            function_name = payload.get('function_name', function_name)
            enabled = payload.get('enabled', enabled)
        if not function_name:
            return 'Error: function_name required'
        desc = [{ 'name': function_name, 'enabled': bool(enabled) }]
        try:
            try:
                desc_json = json.dumps(desc)
            except Exception:
                desc_json = json.dumps(str(desc))
            body = (
                "const fb = new vscode.FunctionBreakpoint(d.name, d.enabled!==false); vscode.debug.addBreakpoints([fb]); created.push({name:d.name,enabled:fb.enabled});"
            )
            code = _make_breakpoints_js(desc_json, body)
            return code_execute(code=code, payload=payload)
        except Exception as e:
            return f"Error: {e}"

    @server.tool(name="debug_breakpoint_add_conditional", description="Add a conditional or hit-count breakpoint by uri and line with condition/hitCondition.")
    def add_breakpoint_conditional(uri: str = None, line: int = None, condition: str = None, hitCondition: str = None, enabled: bool = True, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            uri = payload.get('uri', uri)
            line = payload.get('line', line)
            condition = payload.get('condition', condition)
            hitCondition = payload.get('hitCondition', hitCondition)
            enabled = payload.get('enabled', enabled)
        if not uri or line is None:
            return 'Error: uri and line required'
        desc = [{ 'uri': uri, 'line': int(line), 'condition': condition, 'hitCondition': hitCondition, 'enabled': bool(enabled) }]
        try:
            try:
                desc_json = json.dumps(desc)
            except Exception:
                desc_json = json.dumps(str(desc))
            body = (
                "const uri = vscode.Uri.parse(d.uri); const pos = new vscode.Position(d.line||0, 0); const bp = new vscode.SourceBreakpoint(new vscode.Location(uri, new vscode.Range(pos, pos)), d.enabled!==false, d.condition||undefined, d.hitCondition||undefined); vscode.debug.addBreakpoints([bp]); created.push({uri:d.uri,line:d.line,enabled:bp.enabled,condition:bp.condition||null,hitCondition:bp.hitCondition||null});"
            )
            code = _make_breakpoints_js(desc_json, body)
            return code_execute(code=code, payload=payload)
        except Exception as e:
            return f"Error: {e}"

    @server.tool(name="debug_breakpoint_add_logpoint", description="Add a logpoint (source breakpoint with logMessage) by uri and line.")
    def add_breakpoint_logpoint(uri: str = None, line: int = None, logMessage: str = None, enabled: bool = True, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            uri = payload.get('uri', uri)
            line = payload.get('line', line)
            logMessage = payload.get('logMessage', logMessage)
            enabled = payload.get('enabled', enabled)
        if not uri or line is None or not logMessage:
            return 'Error: uri, line and logMessage required'
        desc = [{ 'uri': uri, 'line': int(line), 'logMessage': logMessage, 'enabled': bool(enabled) }]
        try:
            try:
                desc_json = json.dumps(desc)
            except Exception:
                desc_json = json.dumps(str(desc))
            body = (
                "const uri = vscode.Uri.parse(d.uri); const pos = new vscode.Position(d.line||0, 0); const bp = new vscode.SourceBreakpoint(new vscode.Location(uri, new vscode.Range(pos, pos)), d.enabled!==false, undefined, undefined, d.logMessage); vscode.debug.addBreakpoints([bp]); created.push({uri:d.uri,line:d.line,enabled:bp.enabled,logMessage:bp.logMessage||null});"
            )
            code = _make_breakpoints_js(desc_json, body)
            return code_execute(code=code, payload=payload)
        except Exception as e:
            return f"Error: {e}"

    @server.tool(name="debug_breakpoint_add_data", description="Attempt to add a data breakpoint. Adapter-dependent; may fail if unsupported.")
    def add_breakpoint_data(variable: str = None, accessType: str = 'write', description: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            variable = payload.get('variable', variable)
            accessType = payload.get('accessType', accessType)
            description = payload.get('description', description)
        if not variable:
            return 'Error: variable required'
        desc = [{ 'variable': variable, 'accessType': accessType, 'description': description }]
        try:
            try:
                desc_json = json.dumps(desc)
            except Exception:
                desc_json = json.dumps(str(desc))
            # DataBreakpoints are adapter-dependent; keep compatibility check inline
            body = (
                "if (typeof vscode.DataBreakpoint === 'undefined') { throw new Error('DataBreakpoint not supported'); } const db = new vscode.DataBreakpoint(d.variable, d.accessType||'write'); vscode.debug.addBreakpoints([db]); created.push({variable:d.variable,accessType:d.accessType});"
            )
            code = _make_breakpoints_js(desc_json, body)
            # Wrap to catch the unsupported case and return a structured object if needed
            wrapper = "(function(){ try{ const res = " + code + "; return { success: true, created: res }; } catch(e) { return { success:false, error:String(e) }; } })()"
            return code_execute(code=wrapper, payload=payload)
        except Exception as e:
            return f"Error: {e}"

    @server.tool(name="command_run_vscode", description="Run an arbitrary VS Code command via the code command endpoint.")
    def runCommands(commandId: str = None, args: list = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            commandId = payload.get('commandId', commandId)
            args = payload.get('args', args)
        if not commandId:
            return 'Error: commandId required'
        if args:
            return code(command='command', args=[commandId] + (list(args) if not isinstance(args, str) else [args]))
        return code(command='command', args=[commandId])

    # ------------------------------------------------------------------
    # Debug command convenience wrappers (call vscode commands via the HTTP client)
    # ------------------------------------------------------------------

    @server.tool(name="debug_step_over", description="Perform a debug step over (workbench.action.debug.stepOver).")
    def debug_stepOver(payload: dict = None) -> str:
        return code(command='workbench.action.debug.stepOver', payload=payload)

    @server.tool(name="debug_step_into", description="Perform a debug step into (workbench.action.debug.stepInto).")
    def debug_stepInto(payload: dict = None) -> str:
        return code(command='workbench.action.debug.stepInto', payload=payload)

    @server.tool(name="debug_step_out", description="Perform a debug step out (workbench.action.debug.stepOut).")
    def debug_stepOut(payload: dict = None) -> str:
        return code(command='workbench.action.debug.stepOut', payload=payload)

    @server.tool(name="debug_continue", description="Continue program execution (workbench.action.debug.continue).")
    def debug_continue(payload: dict = None) -> str:
        return code(command='workbench.action.debug.continue', payload=payload)

    @server.tool(name="debug_pause", description="Pause the debuggee (workbench.action.debug.pause).")
    def debug_pause(payload: dict = None) -> str:
        return code(command='workbench.action.debug.pause', payload=payload)

    @server.tool(name="debug_restart", description="Restart the debug session (workbench.action.debug.restart).")
    def debug_restart(payload: dict = None) -> str:
        return code(command='workbench.action.debug.restart', payload=payload)

    @server.tool(name="debug_stop", description="Stop the debug session (workbench.action.debug.stop).")
    def debug_stop(payload: dict = None) -> str:
        return code(command='workbench.action.debug.stop', payload=payload)

    @server.tool(name="debug_toggleBreakpoints", description="Toggle breakpoints activated state.")
    def debug_toggleBreakpoints(payload: dict = None) -> str:
        return code(command='workbench.debug.viewlet.action.toggleBreakpointsActivatedAction', payload=payload)

    @server.tool(name="debug_removeAllBreakpoints", description="Remove all breakpoints in the workspace.")
    def debug_removeAllBreakpoints(payload: dict = None) -> str:
        return code(command='workbench.debug.viewlet.action.removeAllBreakpoints', payload=payload)

    @server.tool(name="debug_enableAllBreakpoints", description="Enable all breakpoints in the workspace.")
    def debug_enableAllBreakpoints(payload: dict = None) -> str:
        return code(command='workbench.debug.viewlet.action.enableAllBreakpoints', payload=payload)

    @server.tool(name="debug_disableAllBreakpoints", description="Disable all breakpoints in the workspace.")
    def debug_disableAllBreakpoints(payload: dict = None) -> str:
        return code(command='workbench.debug.viewlet.action.disableAllBreakpoints', payload=payload)

    @server.tool(name="debug_inspector_list", description="Return inspector/debug-adapter info for active debug sessions (attempts to extract Node inspector ws URL from configurations).")
    def debug_inspector_list(payload: dict = None) -> str:
        """
        Returns an array of {id,name,type,configuration,inspectorUrl} for active debug sessions.
        Tries to extract common Node inspector hints (attach port or runtimeArgs containing --inspect).
        """
        # Defensive JS: only return primitives and a small subset of configuration
        code = (
            "return (function(){ try { return vscode.debug.sessions.map(s => { "
            "const src = s.configuration || {}; const cfg = {}; "
            "try { if (src.port) cfg.port = src.port; if (src.request) cfg.request = src.request; if (src.runtimeArgs && Array.isArray(src.runtimeArgs)) cfg.runtimeArgs = src.runtimeArgs.slice(0,10); } catch(e){} "
            "let inspector = null; try { if (cfg.request === 'attach' && cfg.port) inspector = 'ws://127.0.0.1:' + cfg.port + '/'; else if (cfg.runtimeArgs && cfg.runtimeArgs.find) { const p = cfg.runtimeArgs.find(a => /--inspect(?:-brk)?=/.test(String(a))); if (p) inspector = String(p); } } catch(e){} "
            "return { id: s.id, name: s.name || null, type: s.type || null, configuration: cfg, inspectorUrl: inspector }; }); } catch(err) { return { error: String(err && err.message ? err.message : err) }; } })();"
        )
        return code_execute(code=code, payload=payload)

    @server.tool(name="debug_probe_and_extract", description="Start a debug config (or use existing sessions) and defensively extract threads, stack frames and variables using the in-extension bridge.")
    def debug_probe_and_extract(config: object = None, socket_path: str = None, timeout: float = 10.0, payload: dict = None) -> str:
            """
            Attempts to programmatically start a debug session (if `config` provided) and then probes active sessions to extract threads, frames, scopes and some variables.
            Uses `bridge_exec_js` (the in-extension unix socket bridge) so it avoids the brittle HTTP endpoint.

            Parameters:
                - config: DebugConfiguration name (string) or DebugConfiguration object (dict). Optional: if omitted this will only probe existing sessions.
                - socket_path: optional explicit socket path for the bridge.
                - timeout: seconds to wait for sessions to appear and for probes to complete.
            Returns: JSON string with structure: { started?, sessions:[...], probes:[...] } or an error map.
            """
            try:
                    # Prefer payload values if present
                    if payload and isinstance(payload, dict):
                            config = payload.get('config', config)
                            socket_path = payload.get('socket_path', socket_path)
                            timeout = float(payload.get('timeout', timeout))

                    # Prepare serialized config for injection into JS
                    try:
                            cfg_js = json.dumps(config) if config is not None else 'null'
                    except Exception:
                            cfg_js = json.dumps(str(config))

                    timeout_ms = int(float(timeout) * 1000)

                    # First: run a lightweight session check to get quick diagnostics
                    simple_check = (
                        "try { const sessions = (vscode.debug.sessions || []).map(s=>({ id: s.id, name: s.name||null, type: s.type||null })); return { ok:true, sessions: sessions }; } "
                        "catch(e) { return { ok:false, error: String(e), stack: (e && e.stack) ? e.stack : null }; }"
                    )
                    try:
                        simple_resp_raw = _bridge_exec(simple_check, payload={'socket_path': socket_path} if socket_path else None)
                    except Exception as e:
                        simple_resp_raw = None

                    if simple_resp_raw:
                        try:
                            simple_parsed = json.loads(simple_resp_raw)
                            # If bridge_exec_js returns the {socket, response} wrapper, extract inner response
                            if isinstance(simple_parsed, dict) and 'response' in simple_parsed:
                                inner = simple_parsed.get('response')
                                # if inner contains 'result' (bridge's exec wrapper), pull that
                                if isinstance(inner, dict) and 'result' in inner:
                                    simple_inner = inner.get('result')
                                else:
                                    simple_inner = inner
                            else:
                                simple_inner = simple_parsed
                        except Exception:
                            simple_inner = None
                    else:
                        simple_inner = None

                    # If the simple check shows no sessions, return that diagnostic immediately.
                    try:
                        if simple_inner and isinstance(simple_inner, dict) and simple_inner.get('sessions') is not None and len(simple_inner.get('sessions')) == 0:
                            return json.dumps({ 'ok': True, 'socket': _discover_bridge_socket(socket_path), 'simple': simple_inner, 'probe': None })
                    except Exception:
                        pass

                    # Defensive JS: try to start debugging (if config provided), poll for sessions, and then
                    # use DebugSession.customRequest to call common DAP requests: threads, stackTrace, scopes, variables.
                    js = """
        (async function(){
            const cfg = @@CFG@@;
            const timeoutMs = @@TIMEOUTMS@@;
            const res = { started: null, sessions: [], probes: [], errors: [] };
            try {
                if (cfg) {
                    try {
                        const started = await vscode.debug.startDebugging(undefined, cfg);
                        res.started = !!started;
                    } catch (e) { res.started = false; res.errors.push('startDebugging:'+String(e)); }
                }

                const deadline = Date.now() + timeoutMs;
                let sessions = [];
                while (Date.now() < deadline) {
                    try { sessions = vscode.debug.sessions || []; } catch(e){ sessions = []; }
                    if (sessions.length) break;
                    await new Promise(r => setTimeout(r, 200));
                }
                res.sessions = sessions.map(s => ({ id: s.id, name: s.name || null, type: s.type || null }));

                if (sessions.length) {
                    const toProbe = sessions.slice(0,2);
                    for (const s of toProbe) {
                        const probe = { id: s.id, name: s.name||null, threads: null, stackFrames: [], errors: [] };
                        try {
                            let threadsRes = null;
                            try { threadsRes = await s.customRequest('threads'); } catch(e) { probe.errors.push('threads:'+String(e)); }
                            probe.threads = threadsRes || null;

                            const threadsList = (threadsRes && (threadsRes.body && threadsRes.body.threads)) || (threadsRes && threadsRes.threads) || [];
                            for (const t of (threadsList || []).slice(0,3)) {
                                try {
                                    let st = null;
                                    try { st = await s.customRequest('stackTrace', { threadId: t.id, startFrame: 0, levels: 1 }); } catch(e) { probe.errors.push('stackTrace:'+String(e)); }
                                    const frames = (st && (st.body && st.body.stackFrames)) || (st && st.stackFrames) || [];
                                    for (const f of frames) {
                                        const fid = f.id || f.frameId || null;
                                        const frameInfo = { name: f.name || null, id: fid, source: f.source ? (f.source.path||f.source.name||null) : null, scopes: null, variables: null, frameErrors: [] };
                                        try {
                                            let scopesRes = null;
                                            try { scopesRes = await s.customRequest('scopes', { frameId: fid }); } catch(e) { frameInfo.frameErrors.push('scopes:'+String(e)); }
                                            const scopes = (scopesRes && (scopesRes.body && scopesRes.body.scopes)) || (scopesRes && scopesRes.scopes) || [];
                                            frameInfo.scopes = scopes.map(sc => ({ name: sc.name, variablesReference: sc.variablesReference }));
                                            if (scopes && scopes.length) {
                                                try {
                                                    const firstRef = scopes[0].variablesReference;
                                                    let varsRes = null;
                                                    try { varsRes = await s.customRequest('variables', { variablesReference: firstRef }); } catch(e) { frameInfo.frameErrors.push('variables:'+String(e)); }
                                                    frameInfo.variables = (varsRes && (varsRes.body && varsRes.body.variables)) || (varsRes && varsRes.variables) || varsRes || null;
                                                } catch(e) { frameInfo.frameErrors.push('variables-fetch:'+String(e)); }
                                            }
                                        } catch(e) { frameInfo.frameErrors.push('probe-frame:'+String(e)); }
                                        probe.stackFrames.push(frameInfo);
                                    }
                                } catch(e) { probe.errors.push('probe-thread:'+String(e)); }
                            }
                        } catch(e) { probe.errors.push('probe-session:'+String(e)); }
                        res.probes.push(probe);
                    }
                }
                return res;
            } catch (err) { return { error: String(err) }; }
        })();
        """

                    js = js.replace('@@CFG@@', cfg_js).replace('@@TIMEOUTMS@@', str(timeout_ms))

                        # Call the bridge via helper and return combined diagnostics
                    try:
                        probe_raw = _bridge_exec(js, payload={'socket_path': socket_path} if socket_path else None, socket_path=socket_path, timeout=timeout)
                    except Exception as e:
                        probe_raw = None

                    result_obj = { 'ok': True, 'socket': _discover_bridge_socket(socket_path), 'simple': simple_inner, 'probe': None }
                    if probe_raw:
                        try:
                            parsed = json.loads(probe_raw)
                            # unwrap bridge wrapper if present
                            if isinstance(parsed, dict) and 'response' in parsed:
                                resp = parsed.get('response')
                                # if bridge wraps execution result under 'result'
                                if isinstance(resp, dict) and 'result' in resp:
                                    result_obj['probe'] = resp.get('result')
                                else:
                                    result_obj['probe'] = resp
                            else:
                                result_obj['probe'] = parsed
                        except Exception:
                            result_obj['probe_raw'] = probe_raw

                        return json.dumps(result_obj)
            except Exception as e:
                    return f"Error: {e}"
