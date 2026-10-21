#!/usr/bin/env bash
# Install a systemd USER timer: every night at 03:10 the sloth plans (one file per minute, lowest CPU priority) and applies.
# Usage: scripts/install-timer.sh ~/Downloads /path/to/sloth.toml
set -euo pipefail
TARGET="$(realpath "$1")"; CONF="$(realpath "$2")"; HERE="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/sloth-sort.service <<UNIT
[Unit]
Description=Sloth tidies $TARGET
[Service]
Type=oneshot
WorkingDirectory=$HERE
ExecStartPre=/usr/bin/env bash -c 'curl -sf http://127.0.0.1:8187/health >/dev/null || (nohup $HERE/scripts/start-model.sh >/dev/null 2>&1 & sleep 40)'
ExecStart=$HERE/.venv/bin/sloth run "$TARGET" --config "$CONF" --pace 60 --nice 19
UNIT
cat > ~/.config/systemd/user/sloth-sort.timer <<UNIT
[Unit]
Description=Nightly sloth
[Timer]
OnCalendar=*-*-* 03:10:00
Persistent=true
[Install]
WantedBy=timers.target
UNIT
systemctl --user daemon-reload && systemctl --user enable --now sloth-sort.timer
echo "installed. Undo anything it did with: $HERE/.venv/bin/sloth undo \"$TARGET\""
