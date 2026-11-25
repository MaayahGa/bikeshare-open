#!/usr/bin/env bash
# Capture the evidence for one seeded fault: diff, red test output, hook stderr.
# Usage: bash .claude/skills/seed-fault/capture.sh <slug> [edited-file]
# Writes notes/faults/<slug>/{diff,tests,hook}.txt (notes/ is git-ignored).
set -uo pipefail
slug="${1:?usage: capture.sh <slug> [edited-file]}"
file="${2:-src/features.py}"
out="notes/faults/$slug"
mkdir -p "$out"

git --no-pager diff -- src/ tests/ data/raw/ > "$out/diff.txt"
python -m pytest tests/ -q 2>&1 | tail -25 > "$out/tests.txt"

# Replay the PostToolUse payload the hook would receive for an Edit of $file.
printf '{"tool_name":"Edit","tool_input":{"file_path":"%s/%s"}}' "$PWD" "$file" \
  | CLAUDE_PROJECT_DIR="$PWD" bash .claude/hooks/check_leakage.sh >/dev/null 2>"$out/hook.txt"
echo "hook exit code: $?" >> "$out/hook.txt"

echo "== $out/tests.txt";  tail -3 "$out/tests.txt"
echo "== $out/hook.txt";   tail -2 "$out/hook.txt"
