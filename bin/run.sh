#!/bin/sh
# Launch run_inner.sh in KTerm (interactive terminal): $1 = reset | restore

EXT_DIR="/mnt/us/extensions/reset_books/bin"
KTERM_BIN="/mnt/us/extensions/kterm/bin/kterm.sh"
INNER_SCRIPT="$EXT_DIR/run_inner.sh"
MODE="${1:-reset}"

if [ ! -x "$KTERM_BIN" ]; then
    echo "KTerm not found or not executable: $KTERM_BIN"
    echo "Install KTerm in /mnt/us/extensions/kterm"
    read _
    exit 1
fi

if [ ! -f "$INNER_SCRIPT" ]; then
    echo "Inner script not found: $INNER_SCRIPT"
    read _
    exit 1
fi

exec "$KTERM_BIN" -c 0 -k 1 -e "sh $INNER_SCRIPT $MODE"
