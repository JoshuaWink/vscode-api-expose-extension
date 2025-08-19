#!/usr/bin/env bash
# Validate local-tool-expose-extension exports via the local `capi` CLI.
set -euo pipefail
CAPI="./cli/bin/capi"
if [ ! -x "$CAPI" ]; then
  echo "capi CLI not found or not executable at $CAPI"
  exit 1
fi

# Find a session ID that looks like this workspace; fallback to first session
SESSION_ID=$("$CAPI" -j sessions | node -e '
const s = JSON.parse(require("fs").readFileSync(0, "utf8") || "[]");
let sel = s.find(x => x.info && x.info.workspace && x.info.workspace.includes(process.cwd().split("/").slice(-1)[0]));
if (!sel && s.length) sel = s[0];
if (!sel) { console.error("No sessions found"); process.exit(2); }
console.log(sel.info.id);
')

echo "Using VS Code session: $SESSION_ID"

echo "== Test: listFiles via extension API =="
"$CAPI" -s "$SESSION_ID" exec 'const ext=vscode.extensions.getExtension("yourname.local-tool-expose-extension"); if(!ext) return {error:"extension not found"}; await ext.activate(); const api=ext.exports; try { const files = await api.listFiles("**/*.md"); return {ok:true, files: files.slice(0,20)}; } catch(e) { return {ok:false, error: String(e)} }'

echo "== Test: exec via extension API =="
"$CAPI" -s "$SESSION_ID" exec 'const ext=vscode.extensions.getExtension("yourname.local-tool-expose-extension"); if(!ext) return {error:"extension not found"}; await ext.activate(); const api=ext.exports; try { const r = await api.exec("return 42;"); return {ok:true, result: r}; } catch(e) { return {ok:false, error: String(e)} }'


echo "Done. If you saw results above, the extension exports are callable via capi exec."
