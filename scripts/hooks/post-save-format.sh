#!/bin/bash
# Auto-format files after Claude Code writes/edits them
FILEPATH="$1"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [ -z "$FILEPATH" ]; then
  exit 0
fi

case "$FILEPATH" in
  *.py)
    if command -v ruff &> /dev/null; then
      ruff format "$FILEPATH" 2>/dev/null
      ruff check --fix "$FILEPATH" 2>/dev/null
    fi
    ;;
  *.ts|*.tsx)
    if [ -f "$PROJECT_ROOT/frontend/node_modules/.bin/prettier" ]; then
      cd "$PROJECT_ROOT/frontend" && npx prettier --write "$FILEPATH" 2>/dev/null
    fi
    ;;
  *.json)
    python3 -c "import json; json.load(open('$FILEPATH'))" 2>/dev/null
    if [ $? -ne 0 ]; then
      echo "WARNING: Invalid JSON in $FILEPATH"
    fi
    ;;
esac
exit 0
