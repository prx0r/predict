#!/usr/bin/env bash
# Install the daily long-run loop (idempotent). Box needs: python3, cron.
# Usage: bash scripts/install_cron.sh [--uninstall]
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LINE="17 6 * * * cd $ROOT && /usr/bin/python3 -u scripts/oneclick.py >> $ROOT/data/oneclick-cron.log 2>&1"
if [ "${1:-}" = "--uninstall" ]; then
  crontab -l 2>/dev/null | grep -v "scripts/oneclick.py" | crontab -
  echo "oneclick cron removed"
  exit 0
fi
if crontab -l 2>/dev/null | grep -q "scripts/oneclick.py"; then
  echo "already installed:"
  crontab -l | grep "scripts/oneclick.py"
else
  (crontab -l 2>/dev/null; echo "$LINE") | crontab -
  echo "installed: $LINE"
fi
