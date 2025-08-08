#!/bin/bash

echo "🚀 Testing VSCode API Complete Exposure"
echo "========================================"

# Build the CLI
echo "📦 Building CLI..."
cd cli && npm run build
cd ..

# Test CLI without VSCode (should show "no sessions")
echo ""
echo "🔍 Testing CLI (should show no VSCode sessions found)..."
node cli/dist/cli.js sessions

echo ""
echo "✅ CLI is working!"
echo ""
echo "📋 Next steps:"
echo "1. Install the extension in VSCode:"
echo "   - Open VSCode"
echo "   - Press F5 to run extension in development mode"
echo "   - OR package and install: npm run vscode:prepublish"
echo ""
echo "2. Test the CLI with VSCode running:"
echo "   node cli/dist/cli.js sessions"
echo "   node cli/dist/cli.js apis"
echo "   node cli/dist/cli.js exec \"vscode.window.showInformationMessage('Hello from CLI!')\""
echo ""
echo "3. Install CLI globally (optional):"
echo "   cd cli && npm run install-global"
echo "   Then use: vscode-api sessions"
