#!/bin/bash

# VSCode API Complete Exposure - Installation Script
# "The One CLI to Rule Them All"

echo "🚀 Installing VSCode API Complete Exposure..."

# Install the extension
if [ -f "vscode-api-expose-0.0.6.vsix" ]; then
    echo "📦 Installing extension from VSIX..."
    code --install-extension vscode-api-expose-0.0.6.vsix --force
    
    if [ $? -eq 0 ]; then
        echo "✅ Extension installed successfully!"
    else
        echo "❌ Extension installation failed!"
        exit 1
    fi
else
    echo "❌ VSIX file not found! Please run 'vsce package' first."
    exit 1
fi

# Build and install CLI globally
echo "🛠️  Building and installing CLI..."
cd cli
npm install
npm run build

if [ $? -eq 0 ]; then
    echo "📦 Installing CLI globally..."
    npm run install-global
    
    if [ $? -eq 0 ]; then
        echo "✅ CLI installed globally as 'vscode-api'!"
    else
        echo "❌ CLI global installation failed!"
        exit 1
    fi
else
    echo "❌ CLI build failed!"
    exit 1
fi

cd ..

echo ""
echo "🎉 Installation Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Restart VSCode to activate the extension"
echo "2. Look for the 🟢 VSCode API indicator in the status bar"
echo "3. Test the CLI: vscode-api --help"
echo ""
echo "🔥 Ready to rule them all with unlimited VSCode API access!"
