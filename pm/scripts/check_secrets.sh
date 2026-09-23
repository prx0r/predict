#!/bin/sh
# Pre-commit secret gate (seed0 Rule 0/5 pattern).
# Usage: bash scripts/check_secrets.sh; exit 1 + paths on hit.
set -u
cd "$(dirname "$0")/.." || exit 1
if grep -rEn "sk-live|AKIA[0-9A-Z]{16}|GOCSPX-|cfat_|get-x-api-|ghp_[A-Za-z0-9]{30,}|ya29\.|xox[bpas]-" \
  --include="*.py" --include="*.md" --include="*.json" --include="*.yaml" --include="*.toml" \
  bneck2/ collectors/ scripts/ tests/ experimentation/hypotheses/ 2>/dev/null | grep -v "check_secrets.sh"; then
  echo "SECRET GATE: live-looking secrets above. STOP, remove, use vault."
  exit 1
fi
echo "secret gate clean"
