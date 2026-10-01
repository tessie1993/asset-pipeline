#!/usr/bin/env bash
# install_flow_mcp.sh — install the Google Flow MCP server the image-to-assets pipeline uses for its
# reference drawings (TMSSS05/google-flow-browser-mcp, pinned), and register it with Claude Code
# as `google-flow`.
#
# Run it on the computer whose Google Chrome is signed in to your Google account: the server drives
# that Chrome ("Profile 3" under ~/.config/google-chrome; it copies the profile's cookies to a temp
# folder) and stops at login walls. It never asks for a password. A cloud container without that
# Chrome profile can install it but cannot use it.
#
# Usage: bash tools/flow/install_flow_mcp.sh
#
# Environment:
#   FLOW_MCP_DIR   where the server is cloned (default ~/.local/share/google-flow-browser-mcp)
#
# Afterwards: edit <FLOW_MCP_DIR>/config/flow.config.json (expectedAccount, chromeUserDataDir,
# chromeProfile, locale) and start a new Claude Code session so the server's tools load.

set -euo pipefail

readonly REPO_URL="https://github.com/TMSSS05/google-flow-browser-mcp"
readonly COMMIT="0c8e80ae4acb4475f8d7ba3b8c4e3b92c6b64b6a"
readonly DIR="${FLOW_MCP_DIR:-$HOME/.local/share/google-flow-browser-mcp}"

command -v node >/dev/null 2>&1 || { echo "Node.js 18 or newer is required" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required" >&2; exit 1; }

if [[ ! -d "$DIR/.git" ]]; then
  mkdir -p "$(dirname "$DIR")"
  git clone --quiet "$REPO_URL" "$DIR"
fi
git -C "$DIR" fetch --quiet origin "$COMMIT" 2>/dev/null || git -C "$DIR" fetch --quiet origin
git -C "$DIR" checkout --quiet "$COMMIT"
# Playwright is only used to talk to Chrome over its debugging port: no bundled browser download.
(cd "$DIR" && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci --no-audit --no-fund --silent)
[[ -f "$DIR/config/flow.config.json" ]] || cp "$DIR/config/flow.config.example.json" "$DIR/config/flow.config.json"

if command -v claude >/dev/null 2>&1; then
  if claude mcp get google-flow >/dev/null 2>&1; then
    echo "Claude Code already has an MCP server named google-flow"
  else
    claude mcp add --scope user google-flow -- node "$DIR/src/index.js"
  fi
else
  echo "Claude Code not found: register the server yourself: node $DIR/src/index.js (name it google-flow)"
fi

echo "Installed at $DIR (commit ${COMMIT:0:7})."
echo "Edit $DIR/config/flow.config.json: expectedAccount, chromeUserDataDir, chromeProfile."
