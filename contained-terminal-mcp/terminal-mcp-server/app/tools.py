"""
Minimal terminal-only tools for a dedicated Terminal MCP server.
Expose a small subset of the original terminal utilities: create, send, read,
interrupt, clear, dispose, list.
"""

import os
import select
import threading
import uuid
import subprocess
import json
import re

_local_ptys = {}
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
                    try:
                        total = sum(len(s) for s in buffer)
                        if total > _MAX_BUFFER_CHARS:
                            joined = ''.join(buffer)
                            kept = joined[-_MAX_BUFFER_CHARS:]
                            buffer.clear()
                            buffer.append(kept)
                    except Exception:
                        pass
    except Exception:
        pass


def register_tools(server):
    @server.tool(name="terminal_create", description="Create a terminal (pty-backed). Returns terminal id.")
    def terminal_create(name: str = None, payload: dict = None) -> str:
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
        if terminalId in _local_ptys:
            try:
                m = _local_ptys[terminalId]
                to_write = text if text.endswith('\n') else text + '\n'
                os.write(m['master_fd'], to_write.encode())
                return ''
            except Exception as e:
                return str(e)
        return ''

    @server.tool(name="terminal_read", description="Read buffered output from a pseudoterminal created by terminal_create.")
    def terminal_read(terminalId: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            terminalId = payload.get('terminalId', terminalId)
        if not terminalId:
            return 'Error: terminalId required'
        if terminalId in _local_ptys:
            try:
                m = _local_ptys[terminalId]
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
                    ansi_csi_re = re.compile(r"\x1b\[[0-9;?=><]*[A-Za-z]")
                    out = ansi_csi_re.sub('', out)
                    out = re.sub(r"\x1b\[\?[0-9;]*[hl]", '', out)
                    osc_re = re.compile(r"\x1b\][^\x07]*\x07")
                    out = osc_re.sub('', out)
                    out = out.replace('\x1b', '')
                    out = out.replace('\r\n', '\n').replace('\r', '\n')
                    out = ''.join(ch for ch in out if ch == '\n' or ch == '\t' or ord(ch) >= 32)
                if lines is not None:
                    split_lines = out.splitlines(True)
                    if lines <= 0:
                        return ''
                    return ''.join(split_lines[-lines:])
                return out
            except Exception:
                return ''
        return 'Error: terminal not found'

    @server.tool(name="terminal_interrupt", description="Send an interrupt (Ctrl-C) to a terminal created by these tools.")
    def terminal_interrupt(terminalId: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            terminalId = payload.get('terminalId', terminalId)
        if not terminalId:
            return 'Error: terminalId required'
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

    @server.tool(name="terminal_dispose", description="Dispose a terminal created by these tools.")
    def terminal_dispose(terminalId: str = None, payload: dict = None) -> str:
        if payload and isinstance(payload, dict):
            terminalId = payload.get('terminalId', terminalId)
        if not terminalId:
            return 'Error: terminalId required'
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
        return 'Error: terminal not found'

    @server.tool(name="terminal_list", description="List terminals created or registered (returns JSON array).")
    def terminal_list(payload: dict = None) -> str:
        include_remote = False
        if payload and isinstance(payload, dict):
            if 'include_remote' in payload:
                try:
                    include_remote = bool(payload.get('include_remote'))
                except Exception:
                    include_remote = False
        results = []
        try:
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
            return json.dumps(results)
        except Exception:
            return '[]'
