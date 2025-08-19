(async () => {
  // Minimal end-to-end test for debug helpers.
  // Run this inside the running extension host (for example via your `capi` CLI exec).
  const workspace = (vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0]);
  if (!workspace) return 'No workspace open';
  const targetFile = workspace.uri.fsPath + '/src/extension.ts';
  const lineOneBased = 11; // human-friendly line (will convert to 0-based)
  const outPath = workspace.uri.fsPath + '/.capi-debug-e2e.json';

  function serializeBreakpoint(b) {
    if ('location' in b) {
      return {
        ctor: b.constructor && b.constructor.name,
        type: 'source',
        enabled: b.enabled,
        condition: b.condition || null,
        hitCondition: b.hitCondition || null,
        logMessage: b.logMessage || null,
        location: {
          uri: b.location.uri.toString(),
          startLine: b.location.range.start.line,
          startCharacter: b.location.range.start.character,
          endLine: b.location.range.end.line,
          endCharacter: b.location.range.end.character
        }
      };
    }
    return { ctor: b.constructor && b.constructor.name, type: 'unknown' };
  }

  async function writeOut(obj) {
    const encoder = new TextEncoder();
    const uri = vscode.Uri.file(outPath);
    await vscode.workspace.fs.writeFile(uri, encoder.encode(JSON.stringify(obj, null, 2)));
    return uri.toString();
  }

  // Try to use extension exports if available
  const knownExtIds = [
    'yourPublisher.local-tool-expose-extension',
    'local-tool-expose-extension',
    'local-tool-debug' // common fallbacks
  ];

  let usedExport = false;
  for (const id of knownExtIds) {
    const ext = vscode.extensions.getExtension(id);
    if (ext) {
      try {
        await ext.activate();
        if (ext.exports && ext.exports.debug && typeof ext.exports.debug.setBreakpoint === 'function') {
          usedExport = true;
          const dbg = ext.exports.debug;
          await dbg.setBreakpoint(targetFile, lineOneBased);
          const list = await dbg.listBreakpoints();
          const out = { method: 'extension.exports.debug', extId: id, targetFile, lineOneBased, list };
          return await writeOut(out);
        }
      } catch (e) {
        // ignore and fallback
      }
    }
  }

  // Fallback: use vscode.debug directly
  const uri = vscode.Uri.file(targetFile);
  const zeroBasedLine = Math.max(0, lineOneBased - 1);
  const existing = vscode.debug.breakpoints || [];
  const existsAt = existing.filter(b => 'location' in b && b.location.uri.toString() === uri.toString() && b.location.range.start.line === zeroBasedLine);

  const before = existing.map(serializeBreakpoint);

  if (existsAt.length === 0) {
    const bp = new vscode.SourceBreakpoint(new vscode.Location(uri, new vscode.Position(zeroBasedLine, 0)), true);
    vscode.debug.addBreakpoints([bp]);
  }

  const after = (vscode.debug.breakpoints || []).map(serializeBreakpoint);

  const out = { method: 'direct-vscode.debug', targetFile, lineOneBased, before, after };
  return await writeOut(out);
})();
