#!/usr/bin/env bash
# Installs/updates the hourly live-collection launchd agent.
#
# IMPORTANT: macOS TCC blocks launchd-spawned processes from reading anything
# under ~/Desktop, so the runner CANNOT execute from this repo. This installer
# copies run_live_collection.sh to ~/Library/Application Support/prediction-desk/
# (unprotected) and points the agent there. The runner only talks to the local
# API on localhost:8000, so it needs nothing from the repo at runtime.
#
# Re-run this after editing run_live_collection.sh to deploy the new version.
set -euo pipefail

LABEL="com.predictiondesk.livecollection"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$HOME/Library/Application Support/prediction-desk"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

mkdir -p "$APP_DIR/scripts" "$APP_DIR/logs"
cp "$REPO_ROOT/scripts/run_live_collection.sh" "$APP_DIR/scripts/run_live_collection.sh"
chmod 755 "$APP_DIR/scripts/run_live_collection.sh"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${APP_DIR}/scripts/run_live_collection.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${APP_DIR}/logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>${APP_DIR}/logs/launchd_err.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart "gui/$(id -u)/${LABEL}"

echo "Installed + started: ${LABEL} (hourly)"
echo "Runner:  $APP_DIR/scripts/run_live_collection.sh"
echo "Logs:    $APP_DIR/logs/live_collection.log"
echo "Requires: docker compose up (API on localhost:8000)"
