#!/usr/bin/env bash
# 安装本机每天 09:00 的周报 Agent 全量评测（macOS launchd）。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LABEL="com.zelto.report-agent-eval"
PLIST_SRC="$SCRIPT_DIR/$LABEL.plist"
PLIST_DST="$HOME/Library/LaunchAgents/$LABEL.plist"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/env.example"
UID_NUM="$(id -u)"

chmod +x "$SCRIPT_DIR/run_daily.sh"

if [[ ! -f "$ENV_FILE" && -f "$ENV_EXAMPLE" ]]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "[ENV] 已生成 $ENV_FILE ，可按需改 OTP / Python / Pages 仓库路径"
fi

mkdir -p "$HOME/Library/LaunchAgents" "$SCRIPT_DIR/logs"

cat >"$PLIST_SRC" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$SCRIPT_DIR/run_daily.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$(cd "$SCRIPT_DIR/.." && pwd)</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>RunAtLoad</key>
  <false/>
  <key>StandardOutPath</key>
  <string>$SCRIPT_DIR/logs/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>$SCRIPT_DIR/logs/launchd.err.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>TZ</key>
    <string>Asia/Tokyo</string>
  </dict>
</dict>
</plist>
EOF

cp "$PLIST_SRC" "$PLIST_DST"

if launchctl bootout "gui/$UID_NUM/$LABEL" >/dev/null 2>&1; then
  echo "[LAUNCHD] 已卸载旧任务 $LABEL"
fi
if launchctl bootstrap "gui/$UID_NUM" "$PLIST_DST"; then
  echo "[LAUNCHD] 已加载 $PLIST_DST"
else
  launchctl unload "$PLIST_DST" >/dev/null 2>&1 || true
  launchctl load "$PLIST_DST"
  echo "[LAUNCHD] 已用 launchctl load 加载 $PLIST_DST"
fi

echo "[OK] 每天 09:00（Asia/Tokyo）执行 $SCRIPT_DIR/run_daily.sh"
echo "     查看：launchctl print gui/$UID_NUM/$LABEL | head"
echo "     卸装：launchctl bootout gui/$UID_NUM/$LABEL && rm -f $PLIST_DST"
echo "     电脑在 9 点处于睡眠时，唤醒后才会补跑；评测过程中脚本会 caffeinate 防止中途睡着。"
