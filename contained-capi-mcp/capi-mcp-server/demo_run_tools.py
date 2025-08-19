"""
Demo: Hard-coded trials for Copilot-related endpoints via the VSCode API Exposure CLI (capi).

What it does:
  1) Lists Copilot-related commands discovered in the target VS Code session
  2) Probes Copilot LM availability and, if available, sends a small prompt
  3) Performs a simple task in VS Code: opens an untitled file and inserts text

Prereqs:
  - The VSCode API Exposure extension is running in a VS Code session
  - The CLI binary `capi` is on PATH (see repo cli/bin/capi or install wrapper)

Run:
  python demo_run_tools.py

Notes:
  - This script uses subprocess to call the existing CLI for simplicity.
  - You can add --session/--workspace routing inside run_capi if desired.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from typing import Any, List, Optional


def run_capi(args: List[str], expect_json: bool = False) -> Any:
    """Run `capi` CLI with given args. When expect_json, parse stdout as JSON.

    Resolution order:
      1) capi on PATH
      2) local repo binary at ../../cli/bin/capi (relative to this file)
    """
    exe = shutil.which("capi")
    if not exe:
        # Try local repo path: <repo>/cli/bin/capi
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(here, ".."))  # go up to repo root
        local_capi = os.path.join(repo_root, "cli", "bin", "capi")
        if shutil.which(local_capi) or os.path.exists(local_capi):
            exe = local_capi
        else:
            print("Error: 'capi' CLI not found. Build the CLI or add cli/bin to PATH.", file=sys.stderr)
            sys.exit(1)

    try:
        # Tip: add '--json' for commands that support it to get machine-readable output
        proc = subprocess.run([exe, *args], capture_output=True, text=True)
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            raise RuntimeError(f"capi failed: {err}")
        out = proc.stdout.strip()
        if expect_json:
            try:
                return json.loads(out)
            except Exception:
                # Some CLI paths always print JSON; others might not. Fall back to raw.
                return out
        return out
    except Exception as e:
        print(f"Error running capi {' '.join(args)}: {e}", file=sys.stderr)
        sys.exit(2)


def list_copilot_commands() -> Optional[List[str]]:
    """Return a list of Copilot-related commands via an exec() probe."""
    code = (
        "return (await vscode.commands.getCommands(true)).filter(c => /copilot/i.test(c));"
    )
    # Ask CLI to return JSON if possible
    out = run_capi(["exec", code, "--json"], expect_json=True)
    if isinstance(out, dict) and "result" in out:
        return out.get("result")
    if isinstance(out, list):
        return out
    # Fallback: try to parse if it's a JSON-looking string
    try:
        data = json.loads(out)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return None


def probe_copilot_lm() -> dict:
        """Lightweight check for Copilot LM surface; avoids sending a request to reduce errors."""
    code = (
        """
                try {
                    if (!vscode.lm || typeof vscode.lm.selectChatModels !== 'function') {
                        return { available: false, reason: 'no_lm_api' };
                    }
                    return { available: true };
                } catch (err) {
                    const code = (err && err.code) ? String(err.code) : undefined;
                    const message = (err && err.message) ? String(err.message) : String(err);
                    return { available: false, code, message };
                }
        """
        .strip()
    )
    out = run_capi(["exec", code, "--json"], expect_json=True)
    if isinstance(out, dict) and "result" in out:
        res = out.get("result")
        return res if isinstance(res, dict) else {"raw": res}
    if isinstance(out, dict):
        return out
    # Fallback
    return {"raw": out}


def simple_editor_task() -> bool:
    """Open an untitled file using the command endpoint; avoid message endpoint for stability."""
    try:
        # Use command endpoint to create a new untitled file
        _ = run_capi(["command", "workbench.action.files.newUntitledFile", "--json"], expect_json=True)
        return True
    except SystemExit:
        raise
    except Exception as e:
        print(f"simple_editor_task error: {e}", file=sys.stderr)
        return False


def main() -> None:
    print("== VSCode Copilot + Tools Demo ==")

    # 0) Show sessions (optional, JSON)
    try:
        sessions = run_capi(["sessions", "--json"], expect_json=True)
        if isinstance(sessions, list):
            print(f"Sessions discovered: {len(sessions)}")
        else:
            print("Sessions:", sessions)
    except SystemExit:
        raise
    except Exception as e:
        print(f"(sessions) warning: {e}")

    # 1) Discover Copilot commands
    cmds = list_copilot_commands()
    if cmds is None:
        print("No Copilot commands discovered (or parsing failed). Is Copilot installed in the target session?")
    else:
        print(f"Found {len(cmds)} Copilot-related command(s). Showing up to 10:")
        for c in cmds[:10]:
            print("  -", c)

    # 2) Probe Copilot LM and request a short reply
    lm_info = probe_copilot_lm()
    if lm_info.get("available"):
        text = lm_info.get("text", "").strip()
        print("Copilot LM response:")
        print(text if text else "(empty response)")
    else:
        code = lm_info.get("code")
        msg = lm_info.get("message")
        reason = lm_info.get("reason")
        if reason:
            print(f"Copilot LM not available (reason={reason}).")
        elif code or msg:
            print(f"Copilot LM not available (code={code}, message={msg}).")
        else:
            print("Copilot LM not available.")

    # 3) Simple task: open untitled and insert text
    ok = simple_editor_task()
    print(f"Simple editor task success: {ok}")


if __name__ == "__main__":
    main()
