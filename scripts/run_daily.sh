#!/usr/bin/env bash
# Wrapper for cron: activates the virtualenv, runs the report, appends to a log.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

mkdir -p logs
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "=== $(date '+%Y-%m-%d %H:%M:%S') starting daily report ===" >> logs/daily_report.log
python main.py "$@" >> logs/daily_report.log 2>&1
