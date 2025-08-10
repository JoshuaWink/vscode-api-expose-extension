"""
Tool definitions for capi-mcp-server using FastMCP decorators.
"""

import subprocess
import sys
import json

def register_tools(server):
    @server.tool(name="capi_exec", description="Run code via the capi CLI /exec endpoint and return its output. Accepts a JSON object: {code, args, shell, cwd}.")
    def capi_exec(
        code: str = None,
        args: list = None,
        shell: bool = False,
        cwd: str = None,
        payload: dict = None
    ) -> str:
        """
        Runs code using the capi CLI /exec endpoint and returns the output. Accepts a JSON object with keys: code, args, shell, cwd.
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
            cmd_list = ["capi", "exec", code]
            if args:
                if isinstance(args, str):
                    cmd_list += shlex.split(args)
                else:
                    cmd_list += list(args)
            result = subprocess.run(
                cmd_list if not shell else " ".join(shlex.quote(x) for x in cmd_list),
                capture_output=True,
                text=True,
                shell=shell,
                cwd=cwd
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            return str(output) if output is not None else ""
        except Exception as e:
            print(f"[capi_exec tool error] {e}", file=sys.stderr)
            return f"Error: {e}"

    @server.tool(name="capi", description="Run a capi — exposed vsCode API — command and return its output. Accepts a JSON object: {command, args, shell, cwd}.")
    def capi(
        command: str = None,
        args: list = None,
        shell: bool = False,
        cwd: str = None,
        payload: dict = None
    ) -> str:
        """
        Runs a capi CLI command and returns the output. Accepts a JSON object with keys: command, args, shell, cwd.
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
            cmd_list = ["capi", command]
            if args:
                if isinstance(args, str):
                    # If args is a string, split like shell
                    cmd_list += shlex.split(args)
                else:
                    cmd_list += list(args)
            result = subprocess.run(
                cmd_list if not shell else " ".join(shlex.quote(x) for x in cmd_list),
                capture_output=True,
                text=True,
                shell=shell,
                cwd=cwd
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            return str(output) if output is not None else ""
        except Exception as e:
            print(f"[capi tool error] {e}", file=sys.stderr)
            return f"Error: {e}"

    @server.tool(name="capi_help", description="Show help for the capi CLI, listing all available commands and options.")
    def capi_help() -> str:
        try:
            result = subprocess.run(
                ["capi", "--help"],
                capture_output=True,
                text=True
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            return str(output) if output is not None else ""
        except Exception as e:
            print(f"[capi_help tool error] {e}", file=sys.stderr)
            return f"Error: {e}"
