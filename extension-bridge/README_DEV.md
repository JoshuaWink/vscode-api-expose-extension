Packaging & installing locally

Install `vsce` if you don't have it:

npm install -g vsce

Package:

vsce package

Install into VS Code:

code --install-extension vscode-api-expose-bridge-0.0.1.vsix

Then reload VS Code and run the command `Start VSCode API Socket Bridge` from the Command Palette.
