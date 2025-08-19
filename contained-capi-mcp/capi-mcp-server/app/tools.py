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
from .vscode_api_client import VSCodeAPIClient

# Instantiate shared HTTP-based client for VSCode API Exposure
vscode_client = VSCodeAPIClient()

# Local PTY manager: allow MCP server to spawn and manage real shell PTYs locally.
_local_ptys = {}
# Maximum total characters to retain per PTY buffer. If exceeded, oldest chars are trimmed.
_MAX_BUFFER_CHARS = 200000

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
    @server.tool(name="vscode_execute_arbitrary_js", description="Run code via the code CLI /exec endpoint and return its output. Accepts a JSON object: {code, args, shell, cwd}.")
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
            # Use HTTP client to execute JS in VSCode context
            try:
                response = vscode_client.execute_javascript(
                    code,
                    session_id=payload.get('sessionId', None) if payload else None,
                    workspace=payload.get('workspace', None) if payload else None
                )
                return json.dumps(response)
            except Exception as err:
                return f"Error: {err}"
        except Exception as e:
            print(f"[code_execute tool error] {e}", file=sys.stderr)
            return f"Error: {e}"

    @server.tool(name="vscode_execute_api_command", description="Run a code — exposed vsCode API — command and return its output. Accepts a JSON object: {command, args, shell, cwd}.")
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
            # Use HTTP client to execute VSCode command
            try:
                response = vscode_client.execute_command(
                    command,
                    args=list(shlex.split(args)) if isinstance(args, str) else args,
                    session_id=payload.get('sessionId', None) if payload else None,
                    workspace=payload.get('workspace', None) if payload else None
                )
                return json.dumps(response)
            except Exception as err:
                return f"Error: {err}"
        except Exception as e:
            print(f"[code tool error] {e}", file=sys.stderr)
            return f"Error: {e}"

    @server.tool(name="vscode_execute_help", description="Show help for the code CLI, listing all available commands and options.")
    def vscode_execute_help(payload: dict = None) -> str:
        """Return a help-like listing of available VS Code commands/APIs.
        Replaces the old subprocess-based `vscode_execute --help` call by
        querying the injected HTTP client for available APIs.
        Accepts an optional `payload` dict with `sessionId` and `workspace`.
        """
        try:
            try:
                response = vscode_client.get_apis(
                    session_id=payload.get('sessionId') if payload else None,
                    workspace=payload.get('workspace') if payload else None
                )
                return json.dumps(response)
            except Exception as err:
                return f"Error: {err}"
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

    @server.tool(name="codebase", description="List workspace files (globbing pattern).")
    def codebase(pattern: str = "**/*", payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            pattern = payload.get("pattern", pattern)
        code = f"return (await vscode.workspace.findFiles(\"{pattern}\")).map(f => f.fsPath);"
        return code_execute(code=code)

    @server.tool(name="usages", description="Find usages (simple filename search).")
    def usages(query: str = None, pattern: str = "**/*", payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            query = payload.get("query", query)
            pattern = payload.get("pattern", pattern)
        if not query:
            return "Error: missing query"
        # simple heuristic: search files for the query string and return matches
        code = (
            "const q = " + json.dumps(query) + ";"
            + "const uris = await vscode.workspace.findFiles(" + json.dumps(pattern) + ");"
            + "const results = [];"
            + "for (const u of uris) { const doc = await vscode.workspace.openTextDocument(u);"
            + " if (doc.getText().includes(q)) results.push(u.fsPath); }"
            + "return results;"
        )
        return code_execute(code=code)

    @server.tool(name="vscodeAPI", description="Return a list of available vscode commands (getCommands).")
    def vscodeAPI(payload: dict = None) -> str:
        # expose vscode.commands.getCommands(true)
        code = "return await vscode.commands.getCommands(true);"
        return code_execute(code=code)

    
    @server.tool(name="startDebugging", description="Start a debug session by configuration name or DebugConfiguration object.")
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

    @server.tool(name="stopDebugging", description="Stop the active debug session (if any).")
    def stopDebugging(payload: dict = None) -> str:
        """Stops the active debug session. Returns the result (true/false) or an error string."""
        code = "return await vscode.debug.stopDebugging();"
        return code_execute(code=code, payload=payload)

    @server.tool(name="listDebugSessions", description="Return a list of active debug sessions (id, name, type).")
    def listDebugSessions(payload: dict = None) -> str:
        """Returns active debug sessions as an array of {id, name, type}."""
        code = "return vscode.debug.sessions.map(s => ({ id: s.id, name: s.name, type: s.type }));"
        return code_execute(code=code, payload=payload)

    @server.tool(name="vscodeAPI_search", description="Search available VS Code API commands and return matches.")
    def vscodeAPI_search(query: str = None, payload: dict = None) -> str:
        """Search the API list (from `vscode_client.get_apis`) for the provided query string.
        Returns an array of matching API entries (strings or objects).
        """
        if payload and isinstance(payload, dict):
            query = payload.get('query', query)
        if not query:
            return 'Error: query required'
        try:
            apis = vscode_client.get_apis(
                session_id=payload.get('sessionId') if payload else None,
                workspace=payload.get('workspace') if payload else None
            )
            q = query.lower()
            matches = [a for a in apis if q in (a if isinstance(a, str) else json.dumps(a)).lower()]
            return json.dumps(matches)
        except Exception as e:
            print(f"[vscodeAPI_search tool error] {e}", file=sys.stderr)
            return f"Error: {e}"

    @server.tool(name="addBreakpoints", description="Add breakpoints. Accepts array of breakpoint descriptors: {uri, line, column?, enabled?, condition?, hitCondition?, logMessage?}.")
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
        code = (
            "(function(){ const descriptors = " + json.dumps(breakpoints) + "; const created = []; "
            + "for (const d of descriptors) { try { if (d.uri) { const uri = vscode.Uri.parse(d.uri); const pos = new vscode.Position(d.line||0, d.column||0); "
            + "const bp = new vscode.SourceBreakpoint(new vscode.Location(uri, new vscode.Range(pos, pos)), d.enabled!==false, d.condition, d.hitCondition, d.logMessage); vscode.debug.addBreakpoints([bp]); created.push({uri:d.uri,line:d.line,enabled:bp.enabled,condition:bp.condition||null,hitCondition:bp.hitCondition||null,logMessage:bp.logMessage||null}); } } catch(e) { /* ignore */ } } return created; })()"
        )
        return code_execute(code=code, payload=payload)

    @server.tool(name="removeBreakpoints", description="Remove breakpoints. Accepts array of descriptors {uri,line} to match existing breakpoints.")
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

    @server.tool(name="listBreakpoints", description="List current breakpoints.")
    def listBreakpoints(payload: dict = None) -> str:
        code = (
            "return vscode.debug.breakpoints.map(b => ({ enabled: b.enabled, condition: b.condition || null, hitCondition: b.hitCondition || null, logMessage: b.logMessage || null, location: b.location ? { uri: b.location.uri.toString(), line: b.location.range.start.line, character: b.location.range.start.character } : null }));"
        )
        return code_execute(code=code, payload=payload)

    @server.tool(name="runCommands", description="Run an arbitrary VS Code command via the code command endpoint.")
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

    @server.tool(name="debug_stepOver", description="Perform a debug step over (workbench.action.debug.stepOver).")
    def debug_stepOver(payload: dict = None) -> str:
        return code(command='workbench.action.debug.stepOver', payload=payload)

    @server.tool(name="debug_stepInto", description="Perform a debug step into (workbench.action.debug.stepInto).")
    def debug_stepInto(payload: dict = None) -> str:
        return code(command='workbench.action.debug.stepInto', payload=payload)

    @server.tool(name="debug_stepOut", description="Perform a debug step out (workbench.action.debug.stepOut).")
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

    # ------------------------------------------------------------------
    # Terminal utilities: create shell or pseudoterminal, send text, read buffer, dispose
    # Note: reading output is only supported for pseudoterminal instances created by these tools.
    # ------------------------------------------------------------------

    # Removed legacy shell terminal creation. Only PTY-backed terminal_create remains.

    @server.tool(name="terminal_create", description="Create a terminal (pty-backed). Returns terminal id.")
    def terminal_create(name: str = None, payload: dict = None) -> str:
        # Always create a local PTY and return its id.
        if payload and isinstance(payload, dict):
            name = payload.get('name', name)
        term_name = name or f"mcp-terminal-{int(__import__('time').time())}"
        try:
            master_fd, slave_fd = os.openpty()
            shell = os.environ.get('SHELL', '/bin/sh') if os.name != 'nt' else (os.environ.get('ComSpec', 'cmd.exe'))
            proc = subprocess.Popen([shell], stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, close_fds=True)
            os.close(slave_fd)
            lid = term_name if term_name else f"local-pty-{uuid.uuid4().hex[:8]}"
            buf = []
            lock = threading.Lock()
            stop_ev = threading.Event()
            th = threading.Thread(target=_pty_reader, args=(lid, master_fd, stop_ev, buf, lock), daemon=True)
            th.start()
            _local_ptys[lid] = {
                'master_fd': master_fd,
                'proc': proc,
                'buffer': buf,
                'lock': lock,
                'stop': stop_ev,
                'thread': th
            }
            return lid
        except Exception:
            return term_name

    @server.tool(name="terminal_send", description="Send text to a terminal (shell or pty). Non-blocking.")
    def terminal_send(terminalId: str = None, text: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            terminalId = payload.get('terminalId', terminalId)
            text = payload.get('text', text)
        if not terminalId or text is None:
            return 'Error: terminalId and text required'
        # For local PTYs, write and return an empty string (terminal output comes from terminal_read).
        if terminalId in _local_ptys:
            try:
                m = _local_ptys[terminalId]
                # Ensure newline for shell commands if not present
                to_write = text if text.endswith('\n') else text + '\n'
                os.write(m['master_fd'], to_write.encode())
                return ''
            except Exception as e:
                return str(e)
        return ''

    @server.tool(name="terminal_interrupt", description="Send an interrupt (Ctrl-C) to a terminal created by these tools.")
    def terminal_interrupt(terminalId: str = None, payload: dict = None) -> str:
        """Send an ASCII ETX (Ctrl-C) to the pty master fd for a local PTY.

        Returns empty string on success to match other terminal helpers, or an
        error string when terminalId is missing or the terminal is not found.
        """
        if payload and isinstance(payload, dict):
            terminalId = payload.get('terminalId', terminalId)
        if not terminalId:
            return 'Error: terminalId required'

        # For local PTYs, write the ETX (0x03) character.
        if terminalId in _local_ptys:
            try:
                m = _local_ptys[terminalId]
                try:
                    os.write(m['master_fd'], b'\x03')
                    return ''
                except Exception as e:
                    return str(e)
            except Exception:
                return ''
        return 'Error: terminal not found'

    @server.tool(name="terminal_read", description="Read and consume buffered output from a pseudoterminal created by terminal_create.")
    def terminal_read(terminalId: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            terminalId = payload.get('terminalId', terminalId)
        if not terminalId:
            return 'Error: terminalId required'
        js = (
            "(function(){"
            "globalThis.__mcp_terminals = globalThis.__mcp_terminals || {};"
            f"const id = {json.dumps(terminalId)};"
            "const rec = globalThis.__mcp_terminals[id];"
            "if (!rec) return { success:false, error: 'terminal not found', id: id, output: '' };"
            "if (rec.type !== 'pty') return { success:false, error: 'read supported only for pty terminals', id: id, output: '' };"
            "try { const out = rec.buffer.join(''); rec.buffer.length = 0; return { success:true, id:id, output: out }; } catch(e) { return { success:false, error: String(e), id:id, output: '' }; }"
            "})()"
        )
        # If this is a local PTY managed by MCP, return buffered output as raw string
        if terminalId in _local_ptys:
            try:
                m = _local_ptys[terminalId]
                # Parse payload options early. We removed the 'consume' option;
                # reads are always non-destructive. ``terminal_clear`` must be
                # called explicitly to empty a terminal buffer.
                strip_ansi = True
                lines = None
                if payload and isinstance(payload, dict):
                    if 'strip_ansi' in payload:
                        strip_ansi = bool(payload.get('strip_ansi'))
                    if 'lines' in payload:
                        try:
                            lines = int(payload.get('lines'))
                        except Exception:
                            lines = None

                # Snapshot the raw buffer under lock. Do NOT mutate stored buffer.
                with m['lock']:
                    raw = ''.join(m['buffer'])
                    if lines is not None:
                        parts = raw.splitlines(True)
                        if lines <= 0:
                            consumed_raw = ''
                        else:
                            if lines >= len(parts):
                                consumed_raw = ''.join(parts)
                            else:
                                consumed_raw = ''.join(parts[-lines:])
                    else:
                        consumed_raw = raw
                out = consumed_raw

                if strip_ansi and out:
                    # Remove ANSI CSI sequences (e.g. \x1b[31m), OSC sequences, and other escapes
                    # CSI/OSC regexes combined for common terminal sequences
                    # Remove CSI and other ESC [ ... sequences (more permissive)
                    ansi_csi_re = re.compile(r"\x1b\[[0-9;?=><]*[A-Za-z]")
                    out = ansi_csi_re.sub('', out)
                    # Also remove common bracketed sequences like ESC[?2004h / ESC[?2004l
                    out = re.sub(r"\x1b\[\?[0-9;]*[hl]", '', out)
                    # Remove OSC (Operating System Command) sequences: ESC ] ... BEL
                    osc_re = re.compile(r"\x1b\][^\x07]*\x07")
                    out = osc_re.sub('', out)
                    # Remove any remaining ESC character markers
                    out = out.replace('\x1b', '')
                    # Normalize CRLF and stray carriage returns
                    out = out.replace('\r\n', '\n').replace('\r', '\n')
                    # Strip other control characters except tab(\t) and newline(\n)
                    out = ''.join(ch for ch in out if ch == '\n' or ch == '\t' or ord(ch) >= 32)
                # If lines requested, return only last N lines (after cleaning).
                if lines is not None:
                    split_lines = out.splitlines(True)
                    if lines <= 0:
                        return ''
                    return ''.join(split_lines[-lines:])

                # Default: return full cleaned output
                return out
            except Exception:
                return ''

        resp = code_execute(code=js, payload=payload)
        # code_execute generally returns a JSON-serializable Python object encoded as a string.
        # Attempt to parse nested JSON and return the explicit output when present.
        try:
            parsed = None
            if isinstance(resp, str):
                parsed = json.loads(resp)
            elif isinstance(resp, dict):
                parsed = resp
        except Exception:
            parsed = None

        if parsed and isinstance(parsed, dict) and 'output' in parsed:
            return json.dumps(parsed)

        # Fallback: query the registry directly for the buffer content
        fallback_js = (
            "(function(){"
            f"const id = {json.dumps(terminalId)};"
            "globalThis.__mcp_terminals = globalThis.__mcp_terminals || {};"
            "const rec = globalThis.__mcp_terminals[id];"
            "if (!rec) return { success:false, id:id, output: '' };"
            "if (rec.type !== 'pty') return { success:false, id:id, output: '' };"
            "try { const out = rec.buffer.join(''); rec.buffer.length = 0; return { success:true, id:id, output: out }; } catch(e) { return { success:false, id:id, output: '' }; }"
            "})()"
        )
        fresp = code_execute(code=fallback_js, payload=payload)
        try:
            if isinstance(fresp, str):
                fparsed = json.loads(fresp)
            else:
                fparsed = fresp
            return json.dumps(fparsed)
        except Exception:
            return json.dumps({"success": False, "error": "could not parse terminal read response", "raw": str(resp)})

    @server.tool(name="terminal_dispose", description="Dispose a terminal created by these tools.")
    def terminal_dispose(terminalId: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            terminalId = payload.get('terminalId', terminalId)
        if not terminalId:
            return 'Error: terminalId required'
        # If this is a local PTY, stop reader and terminate proc and return empty string
        if terminalId in _local_ptys:
            try:
                m = _local_ptys[terminalId]
                m['stop'].set()
                try:
                    os.close(m['master_fd'])
                except Exception:
                    pass
                try:
                    m['proc'].terminate()
                except Exception:
                    pass
                try:
                    m['thread'].join(timeout=1.0)
                except Exception:
                    pass
                del _local_ptys[terminalId]
                return ''
            except Exception:
                return ''
        return ''

    @server.tool(name="terminal_clear", description="Clear the buffered output for a terminal created by terminal_create.")
    def terminal_clear(terminalId: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            terminalId = payload.get('terminalId', terminalId)
        if not terminalId:
            return 'Error: terminalId required'
        if terminalId in _local_ptys:
            try:
                m = _local_ptys[terminalId]
                with m['lock']:
                    m['buffer'].clear()
                return ''
            except Exception:
                return ''
        return 'Error: terminal not found'

    @server.tool(name="terminal_list", description="List terminals created or registered (returns JSON array).")
    def terminal_list(payload: dict = None) -> str:
        """Return a JSON array of known terminals. For local PTYs this includes pid and buffer size.
        Accepts optional payload { include_remote: bool } defaulting to true to also query the global registry.
        """
        include_remote = True
        if payload and isinstance(payload, dict):
            if 'include_remote' in payload:
                try:
                    include_remote = bool(payload.get('include_remote'))
                except Exception:
                    include_remote = True
        results = []
        try:
            # Local PTYs
            for tid, m in _local_ptys.items():
                try:
                    pid = getattr(m.get('proc', None), 'pid', None)
                except Exception:
                    pid = None
                buf_len = None
                try:
                    with m['lock']:
                        buf_len = sum(len(s) for s in m.get('buffer', []))
                except Exception:
                    buf_len = None
                results.append({'id': tid, 'type': 'pty', 'pid': pid, 'buffer_chars': buf_len})

            # Optionally include registry-backed terminals (e.g. those exposed via the JS registry)
            if include_remote:
                js = (
                    "(function(){ globalThis.__mcp_terminals = globalThis.__mcp_terminals || {}; "
                    "return Object.keys(globalThis.__mcp_terminals).map(k=>({ id:k, type: (globalThis.__mcp_terminals[k] && globalThis.__mcp_terminals[k].type) || null })); })()"
                )
                try:
                    resp = code_execute(code=js, payload=payload)
                    parsed = None
                    if isinstance(resp, str):
                        try:
                            parsed = json.loads(resp)
                        except Exception:
                            # some code_execute responses are raw JS-returned objects
                            parsed = resp
                    else:
                        parsed = resp

                    if isinstance(parsed, list):
                        for item in parsed:
                            if isinstance(item, dict) and 'id' in item:
                                if not any(r.get('id') == item.get('id') for r in results):
                                    results.append(item)
                except Exception:
                    # Ignore remote listing failures; return local results
                    pass

            return json.dumps(results)
        except Exception as e:
            print(f"[terminal_list tool error] {e}", file=sys.stderr)
            return f"Error: {e}"