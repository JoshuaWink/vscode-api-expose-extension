#!/usr/bin/env node

import { Command } from 'commander';
import axios from 'axios';
import chalk from 'chalk';
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
}

interface VSCodeSession {
    port: number;
    info: SessionInfo;
    baseUrl: string;
}

class VSCodeAPIClient {
    async executeWithAction(code: string, onResult: string, target?: { sessionId?: string, workspace?: string }): Promise<any> {
        const session = await this.getTargetSession(target?.sessionId, target?.workspace);
        try {
            const response = await axios.post(
                `${session.baseUrl}/exec-with-action`,
                { code, onResult },
                { headers: { 'Content-Type': 'application/json' } }
            );
            return response.data;
        } catch (error: any) {
            throw new Error(`exec-with-action failed: ${error.response?.data?.error || error.message}`);
        }
    }
    private sessions: VSCodeSession[] = [];
    private defaultPorts = [3637, 3638, 3639, 3640, 3641]; // Default port range

    async discoverSessions(): Promise<VSCodeSession[]> {
        const sessions: VSCodeSession[] = [];
        
        for (const port of this.defaultPorts) {
            try {
                const baseUrl = `http://localhost:${port}`;
                const response = await axios.get(`${baseUrl}/session`, { timeout: 1000 });
                const info: SessionInfo = response.data;
                
                sessions.push({
                    port,
                    info,
                    baseUrl
                });
            } catch (error) {
                // Session not available on this port
            }
        }
        
        this.sessions = sessions;
        return sessions;
    }

    async getTargetSession(sessionId?: string, workspace?: string): Promise<VSCodeSession> {
        await this.discoverSessions();
        
        if (this.sessions.length === 0) {
            throw new Error('No VSCode sessions found. Make sure the VSCode API Exposure extension is running.');
        }

        // Target by session ID
        if (sessionId) {
            const session = this.sessions.find(s => s.info.id.startsWith(sessionId));
            if (!session) {
                throw new Error(`Session with ID ${sessionId} not found`);
            }
            return session;
        }

        // Target by workspace
        if (workspace) {
            const session = this.sessions.find(s => 
                s.info.workspaceUri && s.info.workspaceUri.includes(workspace)
            );
            if (!session) {
                throw new Error(`Session with workspace ${workspace} not found`);
            }
            return session;
        }

        // Default to first session
        return this.sessions[0];
    }

    async executeCommand(commandId: string, args: any[] = [], target?: { sessionId?: string, workspace?: string }): Promise<any> {
        const session = await this.getTargetSession(target?.sessionId, target?.workspace);
        
        try {
            const response = await axios.post(`${session.baseUrl}/command/${commandId}`, { args });
            return response.data;
        } catch (error: any) {
            throw new Error(`Command execution failed: ${error.response?.data?.error || error.message}`);
        }
    }

    async executeJavaScript(code: string, target?: { sessionId?: string, workspace?: string }): Promise<any> {
        const session = await this.getTargetSession(target?.sessionId, target?.workspace);
        
        try {
            const response = await axios.post(`${session.baseUrl}/exec`, code, {
                headers: { 'Content-Type': 'text/plain' }
            });
            return response.data;
        } catch (error: any) {
            throw new Error(`JavaScript execution failed: ${error.response?.data?.error || error.message}`);
        }
    }

    async getAPIs(target?: { sessionId?: string, workspace?: string }): Promise<any> {
        const session = await this.getTargetSession(target?.sessionId, target?.workspace);
        
        try {
            const response = await axios.get(`${session.baseUrl}/apis`);
            return response.data;
        } catch (error: any) {
            throw new Error(`Failed to get APIs: ${error.response?.data?.error || error.message}`);
        }
    }

    async showMessage(message: string, type: 'info' | 'warning' | 'error' = 'info', target?: { sessionId?: string, workspace?: string }): Promise<any> {
        const session = await this.getTargetSession(target?.sessionId, target?.workspace);
        
        try {
            const response = await axios.post(`${session.baseUrl}/window/showMessage`, { message, type });
            return response.data;
        } catch (error: any) {
            throw new Error(`Failed to show message: ${error.response?.data?.error || error.message}`);
        }
    }
}

const program = new Command();
const client = new VSCodeAPIClient();

program
    .name('vscode-api')
    .description('The One CLI to Rule Them All - Universal VSCode API access')
    .version('1.0.0');

// Global options
program
    .option('-s, --session <id>', 'Target specific VSCode session by ID')
    .option('-w, --workspace <path>', 'Target VSCode session by workspace path')
    .option('-j, --json', 'Output in JSON format')
    .option('-v, --verbose', 'Verbose output');

// List sessions command
program
    .command('sessions')
    .alias('ls')
    .description('List all available VSCode sessions')
    .action(async () => {
        try {
            const sessions = await client.discoverSessions();
            
            if (sessions.length === 0) {
                console.log(chalk.yellow('No VSCode sessions found.'));
                console.log(chalk.gray('Make sure VSCode is running with the API Exposure extension enabled.'));
                return;
            }

            console.log(chalk.green(`Found ${sessions.length} VSCode session(s):`));
            console.log();
            
            sessions.forEach((session, index) => {
                console.log(chalk.cyan(`Session ${index + 1}:`));
                console.log(`  ID: ${session.info.id}`);
                console.log(`  Port: ${session.port}`);
                console.log(`  PID: ${session.info.pid}`);
                console.log(`  Workspace: ${session.info.workspaceUri || 'None'}`);
                console.log(`  APIs: ${session.info.capabilities.length}`);
                console.log();
            });
        } catch (error: any) {
            console.error(chalk.red(`Error: ${error.message}`));
            process.exit(1);
        }
    });

// Execute command
program
    .command('command <commandId> [args...]')
    .alias('cmd')
    .description('Execute a VSCode command')
    .action(async (commandId: string, args: string[] = []) => {
        try {
            const opts = program.opts();
            const result = await client.executeCommand(commandId, args, {
                sessionId: opts.session,
                workspace: opts.workspace
            });
            
            // Always print the full JSON response (pretty-printed)
            console.log(JSON.stringify(result, null, 2));
        } catch (error: any) {
            console.error(chalk.red(`Error: ${error.message}`));
            process.exit(1);
        }
    });

// Execute JavaScript code
program
    .command('exec <code>')
    .description('Execute JavaScript code in VSCode context (JIT power!)')
    .action(async (code: string) => {
        try {
            const opts = program.opts();
            const result = await client.executeJavaScript(code, {
                sessionId: opts.session,
                workspace: opts.workspace
            });
            
            if (opts.json) {
                console.log(JSON.stringify(result, null, 2));
            } else {
                console.log(result.result !== undefined ? result.result : 'No return value');
            }
        } catch (error: any) {
            console.error(chalk.red(`Error: ${error.message}`));
            process.exit(1);
        }
    });

// Execute JavaScript code with a follow-up action
program
    .command('exec-with-action <code> <onResult>')
    .description('Execute JavaScript code in VSCode, then run a follow-up action with the result')
    .action(async (code: string, onResult: string) => {
        try {
            const opts = program.opts();
            const result = await client.executeWithAction(code, onResult, {
                sessionId: opts.session,
                workspace: opts.workspace
            });
            if (opts.json) {
                console.log(JSON.stringify(result, null, 2));
            } else {
                console.log('Result:', result.result !== undefined ? result.result : 'No return value');
                console.log('Action Result:', result.actionResult !== undefined ? result.actionResult : 'No action result');
            }
        } catch (error: any) {
            console.error(chalk.red(`Error: ${error.message}`));
            process.exit(1);
        }
    });

// List APIs command
program
    .command('apis')
    .description('List all available VSCode APIs')
    .action(async () => {
        try {
            const opts = program.opts();
            const apis = await client.getAPIs({
                sessionId: opts.session,
                workspace: opts.workspace
            });
            
            if (opts.json) {
                console.log(JSON.stringify(apis, null, 2));
            } else {
                console.log(chalk.green(`Found ${apis.length} available APIs:`));
                console.log();
                
                const grouped = apis.reduce((acc: any, api: any) => {
                    if (!acc[api.category]) acc[api.category] = [];
                    acc[api.category].push(api);
                    return acc;
                }, {});
                
                Object.entries(grouped).forEach(([category, categoryApis]: [string, any]) => {
                    console.log(chalk.cyan(`${category.toUpperCase()}:`));
                    categoryApis.forEach((api: any) => {
                        console.log(`  ${api.method}(${api.parameters.join(', ')})`);
                    });
                    console.log();
                });
            }
        } catch (error: any) {
            console.error(chalk.red(`Error: ${error.message}`));
            process.exit(1);
        }
    });

// Show message command
program
    .command('message <text>')
    .alias('msg')
    .description('Show a message in VSCode')
    .option('-t, --type <type>', 'Message type: info, warning, error', 'info')
    .action(async (text: string, options: any) => {
        try {
            const opts = program.opts();
            const result = await client.showMessage(text, options.type, {
                sessionId: opts.session,
                workspace: opts.workspace
            });
            
            console.log(chalk.green('Message sent successfully!'));
            if (opts.verbose) {
                console.log(result);
            }
        } catch (error: any) {
            console.error(chalk.red(`Error: ${error.message}`));
            process.exit(1);
        }
    });

// Batch execution from file
program
    .command('batch <file>')
    .description('Execute commands from a file (one per line)')
    .action(async (file: string) => {
        try {
            const filePath = path.resolve(file);
            if (!fs.existsSync(filePath)) {
                throw new Error(`File not found: ${filePath}`);
            }
            
            const content = fs.readFileSync(filePath, 'utf-8');
            const lines = content.split('\n').filter(line => line.trim() && !line.startsWith('#'));
            
            console.log(chalk.yellow(`Executing ${lines.length} commands from ${file}...`));
            console.log();
            
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                console.log(chalk.gray(`[${i + 1}/${lines.length}] ${line}`));
                
                try {
                    if (line.startsWith('exec ')) {
                        const code = line.substring(5);
                        await client.executeJavaScript(code);
                    } else {
                        const [command, ...args] = line.split(' ');
                        await client.executeCommand(command, args);
                    }
                    console.log(chalk.green('✓ Success'));
                } catch (error: any) {
                    console.log(chalk.red(`✗ Error: ${error.message}`));
                }
                console.log();
            }
            
            console.log(chalk.green('Batch execution completed!'));
        } catch (error: any) {
            console.error(chalk.red(`Error: ${error.message}`));
            process.exit(1);
        }
    });

// Parse arguments and run
program.parse();
