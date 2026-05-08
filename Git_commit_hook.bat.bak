#!/bin/sh
pattern="edge_all_open_tabs\|User's Edge browser tabs metadata"
files=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$files" ]; then
  exit 0
fi

bad=0
for f in $files; do
  if [ -f "$f" ]; then
    if grep -E -n "$pattern" "$f" >/dev/null 2>&1; then
      echo "ERROR: Commit enthält Edge browser metadata in $f"
      grep -n -E "$pattern" "$f" | sed 's/^/  /'
      bad=1
    fi
  fi
done

if [ $bad -ne 0 ]; then
  echo "Commit abgebrochen. Entferne die Metadaten und versuche erneut."
  exit 1
fi

exit 0
