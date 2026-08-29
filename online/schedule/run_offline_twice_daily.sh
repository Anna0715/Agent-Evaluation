#!/usr/bin/env bash
# Scheduled twice-daily quality run for the weekly-report Agent.
#
# Install with cron (09:00 and 21:00 local time):
#   0 9,21 * * * /path/to/Agent-Evaluation/packages/weekly_report_quality/schedule/run_twice_daily.sh
# or wire the same command into a Jenkins cron job.
#
# The run fails loudly: non-zero exit + alert line in the log file, so a
# missed or broken run is never silently skipped.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CASES_DIR="${WRQ_CASES_DIR:-$REPO_ROOT/fixtures/offline/cases}"
EVIDENCE_DIR="${WRQ_EVIDENCE_DIR:-$REPO_ROOT/fixtures/offline/evidence}"
RUNS_DIR="${WRQ_RUNS_DIR:-$REPO_ROOT/artifacts/offline-runs}"
LOG_DIR="${WRQ_LOG_DIR:-$RUNS_DIR/logs}"

mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%dT%H%M%S)"
LOG_FILE="$LOG_DIR/run-$STAMP.log"

if PYTHONPATH="$REPO_ROOT/packages" python3 -m weekly_report_quality daily \
    --cases "$CASES_DIR" \
    --evidence "$EVIDENCE_DIR" \
    --out "$RUNS_DIR" \
    >"$LOG_FILE" 2>&1; then
  echo "scheduled quality run OK: $LOG_FILE"
else
  status=$?
  echo "ALERT: scheduled weekly-report quality run FAILED (exit $status), see $LOG_FILE" | tee -a "$LOG_FILE" >&2
  exit "$status"
fi
