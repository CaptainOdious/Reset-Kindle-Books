#!/bin/sh
# Execute le script Python dans le terminal ET copie la sortie dans un journal.
# Important : la sortie doit rester visible, sinon les questions [o/N] sont invisibles.

MODE="${1:-reset}"
EXT_DIR="${EXT_DIR:-/mnt/us/extensions/reset_books}"
PYTHON_BIN="${PYTHON_BIN:-/mnt/us/python3/python/bin/python3}"
LOG_FILE="${LOG_FILE:-/mnt/us/documents/reset_books.log}"
STATUS_FILE="${STATUS_FILE:-/tmp/reset_books.status}"

case "$MODE" in
    reset)   SCRIPT="$EXT_DIR/reset_kindle_books.py" ;;
    restore) SCRIPT="$EXT_DIR/restore_cc_backup.py" ;;
    *) echo "Mode inconnu : $MODE (reset ou restore)"; read _; exit 2 ;;
esac

if [ ! -f "$SCRIPT" ]; then
    echo "Script introuvable : $SCRIPT"
    read _
    exit 1
fi

echo "=== $(date) | mode : $MODE ===" >> "$LOG_FILE"
rm -f "$STATUS_FILE"

if command -v tee >/dev/null 2>&1; then
    { "$PYTHON_BIN" -u "$SCRIPT" 2>&1; echo $? > "$STATUS_FILE"; } | tee -a "$LOG_FILE"
    status=$(cat "$STATUS_FILE" 2>/dev/null)
    [ -n "$status" ] || status=1
else
    "$PYTHON_BIN" -u "$SCRIPT"
    status=$?
fi

echo
echo "Code retour : $status"
echo "Fin : $(date)"
echo "Journal : $LOG_FILE"
echo "Appuyez sur Entree pour fermer."
read _
exit "$status"
