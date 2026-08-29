#!/usr/bin/env bash
# 周报端到端验证（对齐原 send_and_poll_weekly_report.sh 三步）:
#   1) 读取 test_report_data.csv（或 pre 环境 pre_report_data.csv），调用 create_report_data 发报
#      - 发送人/接收人从 data.xlsx（test_data / pre_data sheet）登录
#      - 正文用「周报内容」列
#      - reportId 取自发报接口返回，立刻写回 CSV
#   2) 用接收人轮询 /reports/detail，等 aiTaskStatus == succeeded
#   3) 打印 aiSummary，并把「AI总结内容」写回 report_data.csv
#
# 用法:
#   ./send_and_poll_weekly_report.sh
#   ./send_and_poll_weekly_report.sh --types 周报
#   ./send_and_poll_weekly_report.sh --types 月报 --limit 1
#   ./send_and_poll_weekly_report.sh --force
#   DRY_RUN=1 ./send_and_poll_weekly_report.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

CSV="${REPORT_CSV:-test_report_data.csv}"
ENV_NAME="${REPORT_AGENT_ENV:-test}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONUNBUFFERED=1
export REPORT_AGENT_ENV="$ENV_NAME"

CMD=(
  "$PYTHON_BIN" -u create_report_data.py
  --env "$ENV_NAME"
  --from-csv "$CSV"
  --continue-on-error
)

if [[ -n "${TYPES:-}" ]]; then
  CMD+=(--types "$TYPES")
fi
if [[ -n "${LIMIT:-}" ]]; then
  CMD+=(--limit "$LIMIT")
fi
if [[ -n "${COMPANY_NAME:-}" ]]; then
  CMD+=(--company-name "$COMPANY_NAME")
fi
if [[ "${FORCE:-0}" == "1" ]]; then
  CMD+=(--force)
fi
if [[ -n "${POLL_INTERVAL:-}" ]]; then
  CMD+=(--poll-interval "$POLL_INTERVAL")
fi
if [[ -n "${MAX_POLLS:-}" ]]; then
  CMD+=(--max-polls "$MAX_POLLS")
fi

# 透传额外 CLI（如 --types 周报 --limit 1）
CMD+=("$@")

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "[DRY-RUN] ${CMD[*]}"
  exec "${CMD[@]}"
fi

echo "[RUN] [1/3] create_report_data 发报  [2/3] 接收人轮询 AI 摘要  [3/3] 回写 reportId + AI总结内容"
# CSV 执行模式默认就会轮询 AI；这里显式带上 --poll 表达意图
CMD+=(--execute --poll)
exec "${CMD[@]}"
