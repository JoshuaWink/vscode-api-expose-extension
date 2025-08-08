#!/bin/bash

# VSCode API Complete Exposure - Quick Test Script

echo "🧪 Testing VSCode API Complete Exposure..."

# Check if CLI is available
if ! command -v vscode-api &> /dev/null; then
    echo "❌ CLI not found! Please run ./install.sh first."
    exit 1
fi

echo "🔍 Checking for VSCode sessions..."
vscode-api sessions

echo ""
echo "📡 Available APIs:"
vscode-api apis | head -10
echo "... (showing first 10, use 'vscode-api apis' for full list)"

echo ""
echo "💡 To test the extension:"
echo "1. Open VSCode (F5 for development mode)"
echo "2. Look for 🟢/🔴 indicator in status bar"
echo "3. Click status bar item to toggle server"
echo "4. Run: vscode-api sessions (should show your session)"
echo "5. Run: vscode-api message 'Hello from CLI!'"

echo ""
echo "🎯 Status Bar Indicators:"
echo "🟢 = Server running (green circle)"
echo "🔴 = Server stopped (red circle)"
echo "Click to toggle server state"
