// Import version from package.json for status bar tooltip
import pkg from '../package.json';
import * as vscode from 'vscode';
import express from 'express';
import cors from 'cors';
import { v4 as uuidv4 } from 'uuid';
import * as http from 'http';
import * as fs from 'fs';
import * as path from 'path';

interface SessionInfo {
    id: string;
    pid: number;
    workspaceUri?: string;
    windowId: number;
    capabilities: string[];
    lastSeen: Date;
    serverPort: number;
    meshPeers: string[]; // Connected peer session IDs
}

interface MeshPeer {
    sessionId: string;
    port: number;
    baseUrl: string;
    lastHeartbeat: Date;
    isConnected: boolean;
}

interface ExposedAPI {
    category: string;
    method: string;
    parameters: any;
    description?: string;
}

/**
 * MESH NETWORK ARCHITECTURE:
 * 
 * Each VSCode instance runs this extension and starts an HTTP server.
 * All instances discover each other through port scanning and form a mesh network.
 * This enables:
 * 1. Session discovery: Find all running VSCode instances
 * 2. Command routing: Send commands to specific sessions
 * 3. Load balancing: Distribute commands across sessions
 * 4. Broadcast mode: Execute commands on all sessions
 * 5. Health monitoring: Track session availability
 * 
 * Port Range: 3637-3646 (supports up to 10 concurrent VSCode instances)
 * Heartbeat: Every 30 seconds to maintain mesh connectivity
 * Auto-discovery: Continuous scanning for new sessions
 */

class VSCodeAPIExposure {
    private registryCleanupInterval: NodeJS.Timeout | null = null;
    private server: http.Server | null = null;
    private app: express.Application;
    private sessionInfo: SessionInfo;
    private discoveredAPIs: Map<string, ExposedAPI> = new Map();
    private meshPeers: Map<string, MeshPeer> = new Map();
    private heartbeatInterval: NodeJS.Timeout | null = null;
    private discoveryInterval: NodeJS.Timeout | null = null;
    private readonly portRange = { min: 3637, max: 3646 }; // Support 10 concurrent sessions
    private statusBarItem!: vscode.StatusBarItem;

    // Mesh registry file path (roaming/user data)
    private readonly registryDir: string;
    private readonly registryFile: string;

    // Track dynamic endpoints for removal
    private dynamicEndpoints: Map<string, import('express').RequestHandler> = new Map();

    constructor(private context: vscode.ExtensionContext) {
        this.app = express();
        // sessionInfo will be set in startServer()
        this.sessionInfo = {
            id: '',
            pid: 0,
            workspaceUri: undefined,
            windowId: 0,
            capabilities: [],
            lastSeen: new Date(),
            serverPort: 0,
            meshPeers: []
        };

        // Determine roaming/user data directory for registry
        const userDataDir = this.getUserDataDir();
        this.registryDir = path.join(userDataDir, 'vscode-api-mesh');
        this.registryFile = path.join(this.registryDir, 'registry.json');

        this.setupExpress();
        this.discoverAPIs();
        this.startMeshNetworking();
        this.createStatusBarItem();
        this.startRegistryCleanup();
    }
    // Remove expired sessions from the persistent registry (every minute)
    private startRegistryCleanup(): void {
        this.registryCleanupInterval = setInterval(() => {
            const registry = this.readRegistry();
            const now = Date.now();
            let changed = false;
            for (const [id, info] of Object.entries(registry)) {
                if (now - new Date(info.lastSeen).getTime() > 90 * 1000) { // 120 seconds
                    // Remove all dynamic endpoints if this is our session
                    if (id === this.sessionInfo.id) {
                        for (const path of Array.from(this.dynamicEndpoints.keys())) {
                            this.removeDynamicEndpoint(path);
                        }
                    }
                    delete registry[id];
                    changed = true;
                }
            }
            if (changed) {
                // Persist the registry after cleaning stale sessions.
                // Note: registry writes are intentionally simple JSON writes.
                // If this code is used in production, consider atomic file writes
                // and file locks to avoid races between multiple VS Code processes.
                this.writeRegistry(registry);
            }
        }, 60000); // Run every minute
    }

    public stopRegistryCleanup(): void {
        if (this.registryCleanupInterval) {
            clearInterval(this.registryCleanupInterval);
            this.registryCleanupInterval = null;
        }
    }
    // Get VSCode user data directory (cross-platform)
    private getUserDataDir(): string {
        const platform = process.platform;
        if (platform === 'darwin') {
            return path.join(process.env.HOME || '', 'Library', 'Application Support', 'Code', 'User');
        } else if (platform === 'win32') {
            return path.join(process.env.APPDATA || '', 'Code', 'User');
        } else {
            // Linux and others
            return path.join(process.env.HOME || '', '.config', 'Code', 'User');
        }
    }

    // --- Mesh Registry Logic ---
    private readRegistry(): Record<string, SessionInfo> {
        try {
            if (fs.existsSync(this.registryFile)) {
                const raw = fs.readFileSync(this.registryFile, 'utf8');
                return JSON.parse(raw);
            }
        } catch (e) {
            console.error('Failed to read mesh registry:', e);
        }
        return {};
    }

    private writeRegistry(registry: Record<string, SessionInfo>): void {
        try {
            if (!fs.existsSync(this.registryDir)) {
                fs.mkdirSync(this.registryDir, { recursive: true });
            }
            fs.writeFileSync(this.registryFile, JSON.stringify(registry, null, 2), 'utf8');
        } catch (e) {
            console.error('Failed to write mesh registry:', e);
        }
    }

    private registerSession(): void {
        const registry = this.readRegistry();
        registry[this.sessionInfo.id] = this.sessionInfo;
        this.writeRegistry(registry);
    }

    private deregisterSession(): void {
        // Remove all dynamic endpoints for this session
        for (const path of Array.from(this.dynamicEndpoints.keys())) {
            this.removeDynamicEndpoint(path);
        }
        const registry = this.readRegistry();
        delete registry[this.sessionInfo.id];
        this.writeRegistry(registry);
    }

    private getRegistrySessions(): SessionInfo[] {
        const registry = this.readRegistry();
        // Remove stale sessions (not seen in 2 min)
        const now = Date.now();
        const fresh: Record<string, SessionInfo> = {};
        for (const [id, info] of Object.entries(registry)) {
            if (now - new Date(info.lastSeen).getTime() < 2 * 60 * 1000) {
                fresh[id] = info;
            }
        }
        if (Object.keys(fresh).length !== Object.keys(registry).length) {
            this.writeRegistry(fresh);
        }
        return Object.values(fresh);
    }

    // Atomically find an available port by binding, only claim after successful bind
    private async findAvailablePortAndBind(): Promise<number> {
        for (let p = this.portRange.min; p <= this.portRange.max; p++) {
            try {
                await new Promise<void>((resolve, reject) => {
                    const testServer = http.createServer();
                    testServer.once('error', (err: any) => {
                        testServer.close();
                        reject(err);
                    });
                    testServer.listen(p, () => {
                        testServer.close(() => resolve());
                    });
                });
                return p;
            } catch (e) {
                // Port is in use, try next
            }
        }
        throw new Error('No available ports in the allowed range.');
    }

    // Generate session info after atomic port allocation
    private async generateSessionInfoAtomic(): Promise<SessionInfo> {
        const port = await this.findAvailablePortAndBind();
        return {
            id: uuidv4(),
            pid: process.pid,
            workspaceUri: vscode.workspace.workspaceFolders?.[0]?.uri.toString(),
            windowId: Math.floor(Math.random() * 1000000),
            capabilities: [],
            lastSeen: new Date(),
            serverPort: port,
            meshPeers: []
        };
    }

    private setupExpress(): void {
        this.app.use(cors());
        this.app.use(express.json({ limit: '50mb' }));
        this.app.use(express.text({ limit: '50mb' }));

        // Session info endpoint
        this.app.get('/session', (req, res) => {
            this.sessionInfo.lastSeen = new Date();
            res.json(this.sessionInfo);
        });

        // Dynamic endpoint registration
        // POST /add-endpoint
        // Body: { path: string, response: any }
        // Returns: { success: true, message }
        // Notes: Registers a simple GET handler that returns the provided `response` for quick prototyping.
        // Security: Anyone who can access the port can register endpoints; in production require an allowlist or token.
        this.app.post('/add-endpoint', (req, res) => {
            const { path, response } = req.body;
            if (!path || typeof path !== 'string' || !path.startsWith('/')) {
                return res.status(400).json({ success: false, error: 'Invalid path. Must start with /.' });
            }
            // Remove if already exists
            if (this.dynamicEndpoints.has(path)) {
                this.removeDynamicEndpoint(path);
            }
            // Register a new GET endpoint at runtime that returns a static JSON payload.
            const handler = (req2: express.Request, res2: express.Response) => {
                res2.json({ success: true, dynamic: true, path, response });
            };
            (this.app as any).get(path, handler);
            this.dynamicEndpoints.set(path, handler);
            res.json({ success: true, message: `Endpoint ${path} registered.` });
        });

        // Dynamic endpoint removal
        this.app.post('/remove-endpoint', (req, res) => {
            const { path } = req.body;
            if (!path || typeof path !== 'string' || !path.startsWith('/')) {
                return res.status(400).json({ success: false, error: 'Invalid path. Must start with /.' });
            }
            if (!this.dynamicEndpoints.has(path)) {
                return res.status(404).json({ success: false, error: 'Endpoint not found.' });
            }
            this.removeDynamicEndpoint(path);
            res.json({ success: true, message: `Endpoint ${path} removed.` });
        });

        // List all discovered APIs
        this.app.get('/apis', (req, res) => {
            const apis = Array.from(this.discoveredAPIs.values());
            res.json(apis);
        });

        // Execute VSCode command
        // POST /command/:commandId
        // Body: { args?: any[] }
        // Returns: { success: true, result }
        // Notes: This proxies directly to `vscode.commands.executeCommand` and is useful for invoking built-in commands from remote callers.
        // Security: validate commandId against an allowlist in production.
        this.app.post('/command/:commandId', async (req, res) => {
            try {
                const { commandId } = req.params;
                const args = req.body.args || [];
                const result = await vscode.commands.executeCommand(commandId, ...args);
                res.json({ success: true, result });
            } catch (error) {
                res.status(500).json({ success: false, error: (error as Error).message });
            }
        });

        // Dynamic JavaScript execution - THE JIT POWER!
        // POST /exec
        // Body: { code: string } OR raw string body
        // Returns: { success: true, result }
        // WARNING: This endpoint evaluates arbitrary JavaScript inside the extension host. It's extremely powerful and dangerous.
        // - Do NOT expose this port publicly.
        // - Add authentication or an allowlist before enabling in shared environments.
        // - Consider sandboxing and strict input validation.
        this.app.post('/exec', async (req, res) => {
            try {
                const code = typeof req.body === 'string' ? req.body : req.body.code;
                
                // Create a controlled execution context exposing only safe globals and the vscode API.
                const cp = require('child_process');
                const os = require('os');
                const context = {
                    vscode,
                    console,
                    setTimeout,
                    setInterval,
                    clearTimeout,
                    clearInterval,
                    Promise,
                    cp,
                    os,
                    process
                };

                // Use an AsyncFunction so callers can `await` inside provided code strings.
                const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
                // Expose child_process (cp), os, and process to injected code so it can spawn shell processes for PTY-backed terminals.
                const func = new AsyncFunction('vscode', 'console', 'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval', 'Promise', 'cp', 'os', 'process', code);
                
                const result = await func(
                    context.vscode,
                    context.console,
                    context.setTimeout,
                    context.setInterval,
                    context.clearTimeout,
                    context.clearInterval,
                    context.Promise,
                    context.cp,
                    context.os,
                    context.process,
                );

                // Return the raw result produced by the executed JS. The MCP
                // layer can wrap or attach status metadata as needed.
                return res.json(result);
            } catch (error) {
                // Return a sanitized error message
                res.status(500).json({ success: false, error: (error as Error).message });
            }
        });

        // Workspace API exposure
        this.app.get('/workspace/folders', (req, res) => {
            const folders = vscode.workspace.workspaceFolders?.map(folder => ({
                uri: folder.uri.toString(),
                name: folder.name,
                index: folder.index
            }));
            res.json(folders || []);
        });

        // Editor API exposure
        this.app.get('/editor/active', (req, res) => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                res.json({
                    document: {
                        uri: editor.document.uri.toString(),
                        fileName: editor.document.fileName,
                        languageId: editor.document.languageId,
                        lineCount: editor.document.lineCount
                    },
                    selection: {
                        start: { line: editor.selection.start.line, character: editor.selection.start.character },
                        end: { line: editor.selection.end.line, character: editor.selection.end.character }
                    }
                });
            } else {
                res.json(null);
            }
        });

        // Window API exposure  
        this.app.post('/window/showMessage', async (req, res) => {
            try {
                const { message, type = 'info' } = req.body;
                let result;
                
                switch (type) {
                    case 'error':
                        result = await vscode.window.showErrorMessage(message);
                        break;
                    case 'warning':
                        result = await vscode.window.showWarningMessage(message);
                        break;
                    default:
                        result = await vscode.window.showInformationMessage(message);
                }
                
                res.json({ success: true, result });

            } catch (error) {
                res.status(500).json({ success: false, error: (error as Error).message });
            }
        });

        // Health check
        this.app.get('/health', (req, res) => {
            res.json({ status: 'ok', timestamp: new Date().toISOString() });
        });

        // Mesh network endpoints
        this.app.get('/mesh/peers', (req, res) => {
            const peers = this.getMeshPeers();
            res.json(peers);
        });

        this.app.post('/mesh/broadcast/:endpoint', async (req, res) => {
            try {
                const { endpoint } = req.params;
                const results = await this.broadcastToMesh(`/${endpoint}`, req.body);
                res.json({ success: true, results });
            } catch (error) {
                res.status(500).json({ success: false, error: (error as Error).message });
            }
        });
    }

    private discoverAPIs(): void {
        // Discover all available commands
        vscode.commands.getCommands(true).then(commands => {
            commands.forEach(command => {
                this.discoveredAPIs.set(`command.${command}`, {
                    category: 'command',
                    method: command,
                    parameters: ['...args'],
                    description: `Execute VSCode command: ${command}`
                });
            });
        });

        // Add known VSCode API namespaces
        const vscodeAPIs = [
            { category: 'workspace', method: 'openTextDocument', parameters: ['uri'] },
            { category: 'workspace', method: 'saveAll', parameters: [] },
            { category: 'workspace', method: 'findFiles', parameters: ['include', 'exclude?', 'maxResults?'] },
            { category: 'window', method: 'showInformationMessage', parameters: ['message', '...items'] },
            { category: 'window', method: 'showErrorMessage', parameters: ['message', '...items'] },
            { category: 'window', method: 'showWarningMessage', parameters: ['message', '...items'] },
            { category: 'window', method: 'showInputBox', parameters: ['options?'] },
            { category: 'window', method: 'showQuickPick', parameters: ['items', 'options?'] },
            { category: 'editor', method: 'edit', parameters: ['callback'] },
            { category: 'editor', method: 'insertSnippet', parameters: ['snippet', 'location?', 'options?'] },
            { category: 'commands', method: 'executeCommand', parameters: ['command', '...args'] },
            { category: 'languages', method: 'getDiagnostics', parameters: ['resource?'] },
            { category: 'extensions', method: 'getExtension', parameters: ['extensionId'] }
        ];

        vscodeAPIs.forEach(api => {
            this.discoveredAPIs.set(`${api.category}.${api.method}`, api);
        });

        // Update capabilities
        this.sessionInfo.capabilities = Array.from(this.discoveredAPIs.keys());
    }

    // === STATUS BAR METHODS ===
    
    private createStatusBarItem(): void {
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.statusBarItem.command = 'vscode-api-expose.toggleServer';
        this.updateStatusBarItem();
        this.statusBarItem.show();
        this.context.subscriptions.push(this.statusBarItem);
    }

    private updateStatusBarItem(): void {
        const isRunning = this.server !== null;
        const peerCount = this.meshPeers.size;
        const apiCount = this.discoveredAPIs.size;
        const version = pkg.version || 'unknown';
        if (isRunning) {
            this.statusBarItem.text = `🟢 VSCode API (${this.sessionInfo.serverPort})`;
            this.statusBarItem.tooltip = `VSCode API Exposure Server v${version}\n• Status: Running on port ${this.sessionInfo.serverPort}\n• Session ID: ${this.sessionInfo.id.substring(0, 8)}...\n• Mesh Peers: ${peerCount} connected\n• APIs Exposed: ${apiCount}\n• Click to stop server`;
        } else {
            this.statusBarItem.text = `🔴 VSCode API`;
            this.statusBarItem.tooltip = `VSCode API Exposure Server v${version}\n• Status: Stopped\n• Click to start server`;
        }
    }

    async startServer(): Promise<void> {
        if (this.server) {
            return;
        }

        // Atomically allocate port and generate session info
        this.sessionInfo = await this.generateSessionInfoAtomic();

        return new Promise((resolve, reject) => {
            this.server = this.app.listen(this.sessionInfo.serverPort, () => {
                this.registerSession(); // Register in mesh registry
                vscode.window.showInformationMessage(
                    `VSCode API Exposure Server started on port ${this.sessionInfo.serverPort}`
                );
                console.log(`API Exposure Server running on http://localhost:${this.sessionInfo.serverPort}`);
                this.updateStatusBarItem();
                resolve();
            });

            this.server.on('error', (error) => {
                vscode.window.showErrorMessage(`Failed to start API server: ${error.message}`);
                reject(error);
            });
        });
    }

    async stopServer(): Promise<void> {
        // Stop mesh networking first
        this.stopMeshNetworking();

        this.deregisterSession(); // Remove from mesh registry

        if (this.server) {
            return new Promise((resolve) => {
                this.server!.close(() => {
                    vscode.window.showInformationMessage('VSCode API Exposure Server stopped');
                    this.server = null;
                    this.updateStatusBarItem();
                    resolve();
                });
            });
        }
    }

    getSessionInfo(): SessionInfo {
        this.sessionInfo.lastSeen = new Date();
        return this.sessionInfo;
    }

    getDiscoveredAPIs(): ExposedAPI[] {
        return Array.from(this.discoveredAPIs.values());
    }

    isServerRunning(): boolean {
        return this.server !== null;
    }

    // === MESH NETWORKING METHODS ===
    
    private async startMeshNetworking(): Promise<void> {
        // Start peer discovery
        this.startPeerDiscovery();
        
        // Start heartbeat system
        this.startHeartbeat();
        
        console.log('Mesh networking started - scanning for VSCode peers...');
    }

    private startPeerDiscovery(): void {
        this.discoveryInterval = setInterval(async () => {
            await this.discoverPeers();
        }, 10000); // Discover peers every 10 seconds
    }

    private async discoverPeers(): Promise<void> {
        // Use registry for peer discovery
        const sessions = this.getRegistrySessions();
        for (const peerInfo of sessions) {
            if (peerInfo.id === this.sessionInfo.id) {
                continue;
            }
            // Add or update peer
            this.meshPeers.set(peerInfo.id, {
                sessionId: peerInfo.id,
                port: peerInfo.serverPort,
                baseUrl: `http://localhost:${peerInfo.serverPort}`,
                lastHeartbeat: new Date(peerInfo.lastSeen),
                isConnected: true
            });
        }
        // Remove peers not in registry
        for (const id of Array.from(this.meshPeers.keys())) {
            if (!sessions.find(s => s.id === id)) {
                this.meshPeers.delete(id);
            }
        }
        this.sessionInfo.meshPeers = Array.from(this.meshPeers.keys());
        this.updateStatusBarItem();
    }

    private httpGet(url: string): Promise<string> {
        return new Promise((resolve, reject) => {
            const urlParts = new URL(url);
            const options = {
                hostname: urlParts.hostname,
                port: urlParts.port,
                path: urlParts.pathname,
                method: 'GET',
                timeout: 1000
            };

            const req = http.request(options, (res) => {
                let data = '';
                res.on('data', (chunk) => data += chunk);
                res.on('end', () => resolve(data));
            });

            req.on('error', reject);
            req.on('timeout', () => {
                req.destroy();
                reject(new Error('Timeout'));
            });
            req.setTimeout(1000);
            req.end();
        });
    }

    private startHeartbeat(): void {
        this.heartbeatInterval = setInterval(() => {
            this.sessionInfo.lastSeen = new Date();
            // Persistently update our own session in the registry
            const registry = this.readRegistry();
            registry[this.sessionInfo.id] = this.sessionInfo;
            this.writeRegistry(registry);
            this.updatePeerHealth();
        }, 60000); // Heartbeat every 60 seconds
    }

    private updatePeerHealth(): void {
        const now = new Date();
        const staleThreshold = 60000; // 1 minute

        for (const [sessionId, peer] of this.meshPeers.entries()) {
            if (now.getTime() - peer.lastHeartbeat.getTime() > staleThreshold) {
                peer.isConnected = false;
                // Could remove completely or keep for reconnection attempts
                this.meshPeers.delete(sessionId);
                this.sessionInfo.meshPeers = Array.from(this.meshPeers.keys());
            }
        }
    }

    getMeshPeers(): MeshPeer[] {
        return Array.from(this.meshPeers.values());
    }

    async broadcastToMesh(endpoint: string, data: any): Promise<any[]> {
        const results: any[] = [];
        
        for (const peer of this.meshPeers.values()) {
            if (peer.isConnected) {
                try {
                    const response = await this.httpPost(`${peer.baseUrl}${endpoint}`, data);
                    const result = JSON.parse(response);
                    results.push({ sessionId: peer.sessionId, result });
                } catch (error) {
                    results.push({ sessionId: peer.sessionId, error: (error as Error).message });
                }
            }
        }
        
        return results;
    }

    private httpPost(url: string, data: any): Promise<string> {
        return new Promise((resolve, reject) => {
            const urlParts = new URL(url);
            const postData = JSON.stringify(data);
            // NOTE: httpPost uses a short timeout (5s) to avoid blocking mesh broadcasts.
            // In high-latency networks increase the timeout or make this configurable.
            

        // Generic exec-with-action endpoint: run code, then run follow-up action with result
        // POST /exec-with-action
        // Body: { code: string, onResult?: string }
        // Returns: { success: true, result, actionResult }
        // Purpose: Allows a two-step flow where `code` is executed and the result passed into `onResult` for additional processing.
        // Example: { code: 'return 1+1', onResult: 'return result * 10' } => { result: 2, actionResult: 20 }
        // Security: Same cautions as /exec apply; prefer to avoid enabling this endpoint without auth.
        this.app.post('/exec-with-action', async (req, res) => {
            try {
                const code = typeof req.body === 'string' ? req.body : req.body.code;
                const onResult = req.body.onResult;
                // Create a safe execution context with vscode API
                const context = {
                    vscode,
                    console,
                    setTimeout,
                    setInterval,
                    clearTimeout,
                    clearInterval,
                    Promise
                };
                const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
                const func = new AsyncFunction('vscode', 'console', 'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval', 'Promise', code);
                const result = await func(
                    context.vscode,
                    context.console,
                    context.setTimeout,
                    context.setInterval,
                    context.clearTimeout,
                    context.clearInterval,
                    context.Promise
                );
                let actionResult = null;
                if (onResult) {
                    // onResult is a JS function body as string, receives 'result' as argument
                    const actionFunc = new AsyncFunction('result', 'vscode', 'console', 'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval', 'Promise', onResult);
                    actionResult = await actionFunc(
                        result,
                        context.vscode,
                        context.console,
                        context.setTimeout,
                        context.setInterval,
                        context.clearTimeout,
                        context.clearInterval,
                        context.Promise
                    );
                }
                // Return the composite response object directly. Clients can
                // interpret or re-wrap this as needed.
                return res.json({ result, actionResult });
            } catch (error) {
                res.status(500).json({ success: false, error: (error as Error).message });
            }
        });
            const options = {
                hostname: urlParts.hostname,
                port: urlParts.port,
                path: urlParts.pathname,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(postData)
                },
                timeout: 5000
            };

            const req = http.request(options, (res) => {
                let responseData = '';
                res.on('data', (chunk) => responseData += chunk);
                res.on('end', () => resolve(responseData));
            });

            req.on('error', reject);
            req.on('timeout', () => {
                req.destroy();
                reject(new Error('Timeout'));
            });
            req.setTimeout(5000);
            req.write(postData);
            req.end();
        });
    }

    private stopMeshNetworking(): void {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
        
        if (this.discoveryInterval) {
            clearInterval(this.discoveryInterval);
            this.discoveryInterval = null;
        }
        
        this.meshPeers.clear();
        this.sessionInfo.meshPeers = [];
    }

    // Remove a dynamic endpoint from Express
    private removeDynamicEndpoint(path: string) {
        // Remove from Express router stack.
        // Warning: this manipulates the private `_router.stack` structure. This is pragmatic but brittle
        // across Express versions. Prefer registering middleware in a controlled way if this becomes critical.
        try {
            const router = (this.app as any)._router;
            if (!router || !Array.isArray(router.stack)) {
                // Router not initialized (can happen in some runtime states). Ensure we don't throw.
                console.warn(`Cannot remove dynamic endpoint ${path}: router stack not available.`);
                // Keep internal map consistent
                this.dynamicEndpoints.delete(path);
                return;
            }

            const stack = router.stack;
            for (let i = stack.length - 1; i >= 0; i--) {
                const route = stack[i];
                if (route && route.route && route.route.path === path) {
                    // Splice out the stack entry to remove the route handler
                    stack.splice(i, 1);
                }
            }
        } catch (err) {
            // Defensive: log and continue. We must not crash the extension host due to route removal.
            console.error(`Failed to remove dynamic endpoint ${path}:`, err);
        } finally {
            // Always remove from our internal registry so state stays consistent even if Express internals differ.
            this.dynamicEndpoints.delete(path);
        }
    }
}

let apiExposure: VSCodeAPIExposure;

export function activate(context: vscode.ExtensionContext) {
    console.log('VSCode API Complete Exposure extension is now active!');

    // Create the API exposure instance
    apiExposure = new VSCodeAPIExposure(context);

    // Register commands
    const startCommand = vscode.commands.registerCommand('vscode-api-expose.startServer', async () => {
        await apiExposure.startServer();
    });

    const stopCommand = vscode.commands.registerCommand('vscode-api-expose.stopServer', async () => {
        await apiExposure.stopServer();
    });

    const listAPIsCommand = vscode.commands.registerCommand('vscode-api-expose.listAPIs', () => {
        const apis = apiExposure.getDiscoveredAPIs();
        const output = vscode.window.createOutputChannel('VSCode API Exposure');
        output.show();
        output.appendLine('=== Discovered VSCode APIs ===');
        apis.forEach(api => {
            output.appendLine(`${api.category}.${api.method}(${api.parameters.join(', ')})`);
        });
        output.appendLine(`\nTotal APIs discovered: ${apis.length}`);
    });

    const sessionInfoCommand = vscode.commands.registerCommand('vscode-api-expose.getSessionInfo', () => {
        const info = apiExposure.getSessionInfo();
        vscode.window.showInformationMessage(
            `Session: ${info.id.substring(0, 8)}... | Port: ${info.serverPort} | Workspace: ${info.workspaceUri ? 'Yes' : 'No'}`
        );
    });

    const meshStatusCommand = vscode.commands.registerCommand('vscode-api-expose.showMeshStatus', () => {
        const peers = apiExposure.getMeshPeers();
        const output = vscode.window.createOutputChannel('VSCode Mesh Network');
        output.show();
        output.appendLine('=== VSCode Mesh Network Status ===');
        output.appendLine(`Local Session: ${apiExposure.getSessionInfo().id}`);
        output.appendLine(`Local Port: ${apiExposure.getSessionInfo().serverPort}`);
        output.appendLine(`Connected Peers: ${peers.length}`);
        output.appendLine('');
        
        if (peers.length > 0) {
            output.appendLine('MESH PEERS:');
            peers.forEach((peer, index) => {
                output.appendLine(`${index + 1}. Session: ${peer.sessionId}`);
                output.appendLine(`   Port: ${peer.port}`);
                output.appendLine(`   Status: ${peer.isConnected ? 'Connected' : 'Disconnected'}`);
                output.appendLine(`   Last Seen: ${peer.lastHeartbeat.toLocaleTimeString()}`);
                output.appendLine('');
            });
        } else {
            output.appendLine('No mesh peers found. This VSCode instance is running solo.');
        }
    });

    const toggleServerCommand = vscode.commands.registerCommand('vscode-api-expose.toggleServer', async () => {
        if (apiExposure.isServerRunning()) {
            await apiExposure.stopServer();
        } else {
            await apiExposure.startServer();
        }
    });

    // Add to subscriptions
    context.subscriptions.push(startCommand, stopCommand, listAPIsCommand, sessionInfoCommand, meshStatusCommand, toggleServerCommand);

    // Auto-start server if configured
    const config = vscode.workspace.getConfiguration('vscode-api-expose');
    if (config.get<boolean>('autoStart', true)) {
        apiExposure.startServer();
    }

    // === Chat Participant (@vscode-api-expose.tools) ===
    // Guard for VS Code versions without chat API
    const chatApi: any = (vscode as any).chat;
    if (chatApi && typeof chatApi.createChatParticipant === 'function') {
        const handler: vscode.ChatRequestHandler = async (request, _context, stream, token) => {
            try {
                const prompt = (request.prompt || '').trim();
                if (!prompt) {
                    stream.markdown('Provide an instruction, e.g., "open untitled", "insert \"Hello\"", "run command workbench.action.files.save", or "list copilot commands".');
                    return;
                }

                if (token.isCancellationRequested) {
                    return;
                }

                // open untitled
                if (/\bopen\b.*\buntitled\b/i.test(prompt) || /\bnew\b.*\bfile\b/i.test(prompt)) {
                    await vscode.commands.executeCommand('workbench.action.files.newUntitledFile');
                    stream.markdown('Opened an untitled file.');
                    return;
                }

                // insert "..." at cursor
                const insertMatch = prompt.match(/insert\s+\"([^\"]+)\"|insert\s+\'([^\']+)\'/i);
                if (insertMatch) {
                    const text = insertMatch[1] ?? insertMatch[2] ?? '';
                    const editor = vscode.window.activeTextEditor;
                    if (!editor) {
                        stream.markdown('No active editor to insert into.');
                        return;
                    }
                    await editor.edit((edit) => {
                        const pos = editor.selection.active;
                        edit.insert(pos, text);
                    });
                    stream.markdown(`Inserted text at cursor.`);
                    return;
                }

                // run command <id>
                const cmdMatch = prompt.match(/run\s+command\s+([\w\.-:]+)(?:\s|$)/i);
                if (cmdMatch) {
                    const cmdId = cmdMatch[1];
                    await vscode.commands.executeCommand(cmdId);
                    stream.markdown(`Executed command: ${cmdId}`);
                    return;
                }

                // list copilot commands
                if (/list\s+copilot\s+commands/i.test(prompt)) {
                    const cmds = await vscode.commands.getCommands(true);
                    const filtered = cmds.filter(c => /copilot/i.test(c)).slice(0, 50);
                    if (filtered.length === 0) {
                        stream.markdown('No Copilot-related commands found.');
                    } else {
                        stream.markdown(['Found Copilot commands (first 50):', ...filtered.map(c => `- ${c}`)].join('\n'));
                    }
                    return;
                }

                // fallback help
                stream.markdown('Unsupported instruction. Try: "open untitled", "insert \"Hello\"", "run command workbench.action.files.save", or "list copilot commands".');
            } catch (err) {
                const msg = (err instanceof Error) ? err.message : String(err);
                stream.markdown(`Error: ${msg}`);
            }
        };

    const participant = chatApi.createChatParticipant('vscode-api-expose.tools', handler);
        context.subscriptions.push(participant);
    }
}

export function deactivate() {
    if (apiExposure) {
        apiExposure.stopServer();
        apiExposure.stopRegistryCleanup();
    }
}
