#!/usr/bin/env bash
# 全量跑一周报追问 Agent 与单篇总结用例，并发布质检报告。
# 供 launchd / 手动调用：每天 09:00 或现在立刻跑一轮。

set -euo pipefail

if [[ -z "${CAFFEINATED:-}" ]] && command -v caffeinate >/dev/null 2>&1; then
  export CAFFEINATED=1
  exec caffeinate -dims -- "$0" "$@"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ONLINE_DIR="$REPO_ROOT/online"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/.run.pid"
ENV_FILE="$SCRIPT_DIR/.env"
STAMP="$(date +%Y%m%dT%H%M%S)"
DATE_TODAY="$(date +%Y-%m-%d)"
LOG_FILE="$LOG_DIR/run-$STAMP.log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin${PATH:+:$PATH}"
export PYTHONUNBUFFERED=1
export OTP_CODE="${OTP_CODE:-123456}"
export PHONE_AREA_CODE="${PHONE_AREA_CODE:-+81}"
export SEND_CODE_MAX_ATTEMPTS="${SEND_CODE_MAX_ATTEMPTS:-8}"
export SEND_CODE_RETRY_WAIT_SECONDS="${SEND_CODE_RETRY_WAIT_SECONDS:-60}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

PYTHON="${PYTHON:-/Users/barry/Desktop/autotest/.venv/bin/python}"
PAGES_REPO="${PAGES_REPO:-$HOME/Agent_report}"
PAGES_GIT_URL="${PAGES_GIT_URL:-git@github.com:Anna0715/Agent_report.git}"
ASKER_NAME="${ASKER_NAME:-智本_anrou}"
COMPANY_NAME="${COMPANY_NAME:-智本科技}"

if [[ ! -x "$PYTHON" ]]; then
  echo "[ERROR] python 不存在或不可执行：$PYTHON"
  exit 1
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${old_pid:-}" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "[SKIP] 已有评测在跑 pid=$old_pid log 见 $LOG_DIR"
    exit 0
  fi
fi
echo "$$" >"$PID_FILE"
NOTIFY_SENT=0
on_exit() {
  local code=$?
  rm -f "$PID_FILE"
  if [[ "$code" -ne 0 && "${NOTIFY_SENT}" != "1" ]]; then
    "$PYTHON" "$ONLINE_DIR/publish_quality_report.py" \
      --notify-failure \
      --batch-id "$STAMP" \
      --error "定时评测异常，exit=${code}，日志 ${LOG_FILE}" \
      || true
  fi
}
trap on_exit EXIT

echo "[START] $STAMP cwd=$ONLINE_DIR python=$PYTHON"
cd "$ONLINE_DIR"

if [[ ! -d "$PAGES_REPO/.git" ]]; then
  echo "[PAGES] clone $PAGES_GIT_URL -> $PAGES_REPO"
  git clone "$PAGES_GIT_URL" "$PAGES_REPO"
else
  git -C "$PAGES_REPO" pull --ff-only || true
fi

"$PYTHON" "$ONLINE_DIR/run_report_agent_cases.py" \
  --suite all \
  --asker-name "$ASKER_NAME" \
  --company-name "$COMPANY_NAME"

PUBLISH_ARGS=()
if [[ -f "$SCRIPT_DIR/.no_webhook" || "${NO_WEBHOOK:-}" == "1" ]]; then
  PUBLISH_ARGS+=(--no-webhook)
fi

echo "[PUBLISH] $DATE_TODAY -> $PAGES_REPO"
"$PYTHON" "$REPORT_DIR/publish_quality_report.py" \
  --date "$DATE_TODAY" \
  --pages-repo "$PAGES_REPO" \
  --batch-id "$STAMP" \
  "${PUBLISH_ARGS[@]}"
NOTIFY_SENT=1

echo "[DONE] $STAMP log=$LOG_FILE"
