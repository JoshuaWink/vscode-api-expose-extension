const vscode = require('vscode');
const net = require('net');
const fs = require('fs');
const path = require('path');
const os = require('os');

let server = null;
let socketPath = null;

function defaultSocketPath() {
  try {
    const wf = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (wf && wf.uri && wf.uri.fsPath) {
      const dir = path.join(wf.uri.fsPath, '.vscode');
      try { fs.mkdirSync(dir, { recursive: true }); } catch(e){}
      return path.join(dir, 'vscode-api-expose.sock');
    }
  } catch(e) {}
  return path.join(os.tmpdir(), 'vscode-api-expose.sock');
}

function safeSerialize(obj) {
  const seen = new WeakSet();
  return JSON.parse(JSON.stringify(obj, function(k, v) {
    if (v === undefined) return null;
    if (typeof v === 'function') return `[Function:${v.name||'anonymous'}]`;
    if (v && typeof v === 'object') {
      if (seen.has(v)) return '[Circular]';
      seen.add(v);
    }
    return v;
  }));
}

function startBridge(pathOverride) {
  if (server) return { started: false, message: 'bridge already running' };
  socketPath = pathOverride || defaultSocketPath();
  // remove existing socket if present
  try { if (fs.existsSync(socketPath)) fs.unlinkSync(socketPath); } catch(e){}

  server = net.createServer((conn) => {
    let acc = '';
    conn.setEncoding('utf8');
    conn.on('data', (chunk) => {
      acc += chunk;
      let idx;
      while ((idx = acc.indexOf('\n')) !== -1) {
        const line = acc.slice(0, idx);
        acc = acc.slice(idx + 1);
        if (!line) continue;
        let req;
        try {
          req = JSON.parse(line);
        } catch (e) {
          conn.write(JSON.stringify({ id: null, ok: false, error: 'invalid-json' }) + '\n');
          continue;
        }
        (async () => {
          if (!req || !req.id) {
            conn.write(JSON.stringify({ id: null, ok: false, error: 'missing id' }) + '\n');
            return;
          }
          try {
            if (req.action === 'exec' && typeof req.code === 'string') {
              // eslint-disable-next-line no-new-func
              const fn = new Function('vscode', 'payload', `return (async function(){ ${req.code} })()`);
              let res = await Promise.resolve(fn(vscode, req.payload));
              try { res = safeSerialize(res); } catch(e) { res = String(res); }
              conn.write(JSON.stringify({ id: req.id, ok: true, result: res }) + '\n');
            } else {
              conn.write(JSON.stringify({ id: req.id, ok: false, error: 'unsupported action' }) + '\n');
            }
          } catch (err) {
            conn.write(JSON.stringify({ id: req.id, ok: false, error: String(err && err.message ? err.message : err) }) + '\n');
          }
        })();
      }
    });
    conn.on('error', ()=>{});
  });

  server.on('error', (e) => {
    console.error('socket server error', e);
  });

  server.listen(socketPath, () => {
    console.log('vscode-api-expose socket bridge listening on', socketPath);
    try {
      // write a small marker file with the socket path so external tools can discover it
      const markerDir = path.join(vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0].uri.fsPath || os.homedir(), '.vscode');
      try { fs.mkdirSync(markerDir, { recursive: true }); } catch(e){}
      const marker = path.join(markerDir, 'vscode-api-expose.sockpath');
      try { fs.writeFileSync(marker, socketPath, { encoding: 'utf8' }); } catch(e){}
    } catch(e) {}
  });

  return { started: true, socketPath };
}

function stopBridge() {
  if (!server) return { stopped: false, message: 'not running' };
  try {
    server.close();
  } catch(e){}
  try { if (fs.existsSync(socketPath)) fs.unlinkSync(socketPath); } catch(e){}
  try {
    const marker = path.join(vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0].uri.fsPath || os.homedir(), '.vscode', 'vscode-api-expose.sockpath');
    if (fs.existsSync(marker)) fs.unlinkSync(marker);
  } catch(e) {}
  server = null;
  socketPath = null;
  return { stopped: true };
}

function activate(context) {
  try {
    console.log('[vscode-api-expose] activate() node:', process.version, 'exec:', process.execPath);
  } catch(e) {}
  const startCmd = vscode.commands.registerCommand('vscode-api-expose.startSocketBridge', () => {
    const res = startBridge();
    vscode.window.showInformationMessage(`API Bridge: ${res.started ? 'started' : 'already running'} @ ${res.socketPath || ''}`);
    return res;
  });
  const stopCmd = vscode.commands.registerCommand('vscode-api-expose.stopSocketBridge', () => {
    const res = stopBridge();
    vscode.window.showInformationMessage(`API Bridge: ${res.stopped ? 'stopped' : res.message}`);
    return res;
  });
  context.subscriptions.push(startCmd, stopCmd);
}

function deactivate() {
  stopBridge();
}

module.exports = { activate, deactivate, startBridge, stopBridge };
