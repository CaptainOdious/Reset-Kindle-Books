#!/bin/sh
# Lance run_inner.sh dans KTerm (terminal interactif) : $1 = reset | restore

EXT_DIR="/mnt/us/extensions/reset_books"
KTERM_BIN="/mnt/us/extensions/kterm/bin/kterm.sh"
INNER_SCRIPT="$EXT_DIR/run_inner.sh"
MODE="${1:-reset}"

if [ ! -x "$KTERM_BIN" ]; then
    echo "KTerm introuvable ou non executable : $KTERM_BIN"
    echo "Installez KTerm dans /mnt/us/extensions/kterm"
    read _
    exit 1
fi

if [ ! -f "$INNER_SCRIPT" ]; then
    echo "Script interne introuvable : $INNER_SCRIPT"
    read _
    exit 1
fi

exec "$KTERM_BIN" -c 0 -k 1 -e "sh $INNER_SCRIPT $MODE"
