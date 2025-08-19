(async function() {
  // Reusable script to add a SourceBreakpoint to src/extension.ts (line 11, 1-based)
  // Run this using the repo's capi CLI: 
  // /cli/bin/capi -s <SESSION_ID> exec "$(cat scripts/set_breakpoint_exec.js)"

  const fsTarget = '/Users/joshuawink/Documents/github/vscode-api-expose/src/extension.ts';
  // Use a 1-based line number interface for humans/CLI. Change this value to set a different line.
  const lineOneBased = 11; // 1-based line number to set breakpoint (human-friendly)
  const lineZeroBased = Math.max(0, lineOneBased - 1);

  const uri = vscode.Uri.file(fsTarget);
  const bp = new vscode.SourceBreakpoint(new vscode.Location(uri, new vscode.Position(lineZeroBased, 0)));

  try {
    vscode.debug.addBreakpoints([bp]);
  } catch (e) {
    return { success: false, error: String(e) };
  }

  // Return current breakpoints for verification
  return (vscode.debug.breakpoints || []).map(b => ({
    type: b.constructor && b.constructor.name,
    location: b.location && { uri: b.location.uri.toString(), line: b.location.range.start.line }
  }));
})();
