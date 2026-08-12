#!/bin/bash
# Double-click on macOS Finder to start CryptoIntel (opens Terminal).
cd "$(dirname "$0")" || exit 1

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "CryptoIntel local start"
echo "Project: $(pwd)"
echo

if ! ./scripts/start.sh; then
  code=$?
  echo
  echo "Start failed (exit ${code})."
  echo "Tips:"
  echo "  1) Docker Desktop must be running (whale icon idle)."
  echo "  2) If macOS blocked this file: right-click Start.command → Open."
  echo "  3) Or in Terminal:  xattr -d com.apple.quarantine Start.command"
  echo "  4) Check logs: .api.log  .launcher.log"
  echo
  read -r -p "Press Enter to close…"
  exit "${code}"
fi

echo
read -r -p "Press Enter to close this window…"
