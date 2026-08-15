# Forge Daemon -- launchd Service

macOS launchd service files for supervising the Forge daemon. Automatically restarts the daemon on crash and starts it at login.

## Install

```bash
# Copy plist to LaunchAgents
cp com.forgelabs.daemon.plist ~/Library/LaunchAgents/

# Substitute the project root placeholder
sed -i '' "s|__PROJECT_ROOT__|$(pwd)/../../../..|" ~/Library/LaunchAgents/com.forgelabs.daemon.plist

# Load the service
launchctl load ~/Library/LaunchAgents/com.forgelabs.daemon.plist
```

Or use the automated installer:

```bash
python3 .claude/hooks/company/forge_daemon.py install
```

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.forgelabs.daemon.plist
rm ~/Library/LaunchAgents/com.forgelabs.daemon.plist
```

## Status

```bash
launchctl list | grep forgelabs
```

## Logs

- stdout: `.company/logs/daemon-launchd-stdout.log`
- stderr: `.company/logs/daemon-launchd-stderr.log`

## Nightly Coverage Job (com.forgelabs.coverage)

One-shot LaunchAgent that runs the full test suite with coverage at 03:30
local time and atomically writes a trusted `coverage.json` for the G1
assessor. Install (same placeholder pattern as the daemon plist):

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
PROJECT_ID="$(basename "$PROJECT_ROOT")-$(echo -n "$PROJECT_ROOT" | shasum | cut -c1-6)"
PLIST=~/Library/LaunchAgents/com.forgelabs.coverage.$PROJECT_ID.plist
sed -e "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" \
    -e "s|__PROJECT_ID__|$PROJECT_ID|g" \
    -e "s|__UV_PATH__|$(which uv)|g" \
    -e "s|__USER_PATH__|$PATH|g" \
    com.forgelabs.coverage.plist > "$PLIST"
launchctl load "$PLIST"
```

Check `launchctl list | grep forgelabs.coverage` and the logs under
`.company/logs/coverage-nightly-*.log`. Exit codes: 0 = fresh coverage.json
written, 2 = lock held, 3 = pytest timeout, 4 = no valid report produced.
