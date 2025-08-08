// Standalone test for port allocation and registry logic
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const portRange = { min: 3637, max: 3646 };
const userDataDir = path.join(process.env.HOME || '', 'Library', 'Application Support', 'Code', 'User');
const registryDir = path.join(userDataDir, 'vscode-api-mesh');
const registryFile = path.join(registryDir, 'registry.json');

function readRegistry() {
  try {
    if (fs.existsSync(registryFile)) {
      const raw = fs.readFileSync(registryFile, 'utf8');
      return JSON.parse(raw);
    }
  } catch (e) {
    console.error('Failed to read mesh registry:', e);
  }
  return {};
}

function writeRegistry(registry) {
  try {
    if (!fs.existsSync(registryDir)) {
      fs.mkdirSync(registryDir, { recursive: true });
    }
    fs.writeFileSync(registryFile, JSON.stringify(registry, null, 2), 'utf8');
  } catch (e) {
    console.error('Failed to write mesh registry:', e);
  }
}

function allocatePort() {
  let port = portRange.min;
  const usedPorts = new Set();
  const registry = readRegistry();
  for (const info of Object.values(registry)) {
    usedPorts.add(info.serverPort);
  }
  for (let p = portRange.min; p <= portRange.max; p++) {
    if (!usedPorts.has(p)) {
      port = p;
      break;
    }
  }
  return port;
}

function registerSession() {
  const registry = readRegistry();
  const port = allocatePort();
  const id = uuidv4();
  registry[id] = {
    id,
    pid: process.pid,
    workspaceUri: null,
    windowId: Math.floor(Math.random() * 1000000),
    capabilities: [],
    lastSeen: new Date(),
    serverPort: port,
    meshPeers: []
  };
  writeRegistry(registry);
  console.log(`Registered session ${id} on port ${port}`);
}

function clearRegistry() {
  writeRegistry({});
  console.log('Registry cleared.');
}

function printRegistry() {
  const registry = readRegistry();
  console.log(registry);
}

// CLI usage: node port-allocator-test.js [register|clear|print]
const cmd = process.argv[2];
if (cmd === 'register') {
  registerSession();
} else if (cmd === 'clear') {
  clearRegistry();
} else {
  printRegistry();
}
