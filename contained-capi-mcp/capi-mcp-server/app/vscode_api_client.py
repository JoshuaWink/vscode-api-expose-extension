"""
Python port of VSCodeAPIClient from the CLI.
Utility class for calling the VSCode API Exposure endpoints directly via HTTP.
"""
import requests
import json
from typing import Any, Dict, List, Optional

class VSCodeAPIClient:
    def __init__(self, ports: Optional[List[int]] = None, timeout: int = 1, version: Optional[str] = None):
        # Default VSCode API Exposure ports
        self.ports = ports or [3637, 3638, 3639, 3640, 3641]
        self.timeout = timeout
        # API version prefix (e.g., 'v1', 'v2'); if provided, prefix endpoints with '/<version>'
        ver = str(version).strip('/') if version else ''
        self.version_prefix = f"/{ver}" if ver else ''
        self.sessions: List[Dict[str, Any]] = []

    def discover_sessions(self) -> List[Dict[str, Any]]:
        sessions = []
        for port in self.ports:
            try:
                base_url = f"http://localhost:{port}"
                # include version prefix if set
                resp = requests.get(f"{base_url}{self.version_prefix}/session", timeout=self.timeout)
                resp.raise_for_status()
                info = resp.json()
                sessions.append({"port": port, "info": info, "base_url": base_url})
            except Exception:
                continue
        self.sessions = sessions
        return sessions

    def get_target_session(self, session_id: Optional[str] = None, workspace: Optional[str] = None) -> Dict[str, Any]:
        if not self.sessions:
            self.discover_sessions()
        if not self.sessions:
            raise RuntimeError("No VSCode sessions found. Make sure the VSCode API Exposure extension is running.")
        if session_id:
            for s in self.sessions:
                if s['info']['id'].startswith(session_id):
                    return s
            raise RuntimeError(f"Session with ID {session_id} not found")
        if workspace:
            for s in self.sessions:
                if s['info'].get('workspaceUri', '').find(workspace) != -1:
                    return s
            raise RuntimeError(f"Session with workspace {workspace} not found")
        return self.sessions[0]

    def execute_command(self, command: str, args: Optional[List[Any]] = None, session_id: Optional[str] = None, workspace: Optional[str] = None) -> Any:
        sess = self.get_target_session(session_id, workspace)
        url = f"{sess['base_url']}{self.version_prefix}/command/{command}"
        payload = {"args": args or []}
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def execute_javascript(self, code: str, session_id: Optional[str] = None, workspace: Optional[str] = None) -> Any:
        sess = self.get_target_session(session_id, workspace)
        url = f"{sess['base_url']}{self.version_prefix}/exec"
        headers = {'Content-Type': 'text/plain'}
        resp = requests.post(url, data=code, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def execute_with_action(self, code: str, on_result: str, session_id: Optional[str] = None, workspace: Optional[str] = None) -> Any:
        sess = self.get_target_session(session_id, workspace)
        url = f"{sess['base_url']}{self.version_prefix}/exec-with-action"
        payload = {"code": code, "onResult": on_result}
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_apis(self, session_id: Optional[str] = None, workspace: Optional[str] = None) -> Any:
        sess = self.get_target_session(session_id, workspace)
        url = f"{sess['base_url']}{self.version_prefix}/apis"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def show_message(self, message: str, type: str = 'info', session_id: Optional[str] = None, workspace: Optional[str] = None) -> Any:
        sess = self.get_target_session(session_id, workspace)
        url = f"{sess['base_url']}{self.version_prefix}/window/showMessage"
        payload = {"message": message, "type": type}
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()
