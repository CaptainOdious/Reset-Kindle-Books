#!/mnt/us/python3/python/bin/python3
# -*- coding: utf-8 -*-
"""Restore cc.db from a backup created by the reset scripts.

Usage:
  python3 restore_cc_backup.py                      # choose from the list
  python3 restore_cc_backup.py BACKUP_PATH    # specific backup
  python3 restore_cc_backup.py BACKUP_PATH CC_DB_PATH
Deleted .sdr folders CANNOT be restored by this script.
"""
import glob
import os
import sqlite3
import sys
from datetime import datetime

DEFAULT_DB = "/var/local/cc.db"
BACKUP_DIR = "/mnt/us/documents/ccdb_reset_backups"


def ask(question):
    try:
        return input(question).strip().lower() in ("o", "oui", "y", "yes")
    except EOFError:
        return False


def list_backups():
    files = glob.glob(os.path.join(BACKUP_DIR, "cc.db.*.sqlite"))
    return sorted(files, key=os.path.getmtime, reverse=True)


def describe(path):
    stamp = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
    return "{} ({:.1f} MB, {})".format(os.path.basename(path), os.path.getsize(path) / 1048576.0, stamp)


def summary(path):
    """Summary without integrity_check: it would require ICU collation."""
    conn = sqlite3.connect("file:{}?mode=ro".format(path), uri=True)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "Entries" not in tables:
            raise RuntimeError("Entries table missing: this is not a valid cc.db")
        entries = conn.execute("SELECT count(*) FROM Entries NOT INDEXED").fetchone()[0]
        objects = conn.execute("SELECT count(*) FROM sqlite_master").fetchone()[0]
        triggers = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
        return entries, objects, triggers
    finally:
        conn.close()


def choose_backup(args):
    if args:
        path = args[0]
        if not os.path.isfile(path):
            raise RuntimeError("backup not found: {}".format(path))
        return path
    backups = list_backups()
    if not backups:
        raise RuntimeError("no backups in {}".format(BACKUP_DIR))
    print("Available backups (newest first):")
    for i, p in enumerate(backups, 1):
        print("  {}. {}".format(i, describe(p)))
    try:
        raw = input("Backup number to restore [1 = newest]: ").strip() or "1"
        index = int(raw)
    except (EOFError, ValueError):
        raise RuntimeError("invalid selection")
    if not 1 <= index <= len(backups):
        raise RuntimeError("number out of range")
    return backups[index - 1]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    db_path = args[1] if len(args) > 1 else DEFAULT_DB
    try:
        backup = choose_backup(args[:1])
        if not os.path.isfile(db_path):
            raise RuntimeError("cc.db not found: {}".format(db_path))
        if os.path.abspath(backup) == os.path.abspath(db_path):
            raise RuntimeError("the backup and cc.db are the same file")

        b_entries, b_objects, b_triggers = summary(backup)
        c_entries, c_objects, c_triggers = summary(db_path)
        print("\nBackup: {}".format(describe(backup)))
        print("  Entries : {} | schema objects: {} | triggers : {}".format(b_entries, b_objects, b_triggers))
        print("Current cc.db: {}".format(db_path))
        print("  Entries : {} | schema objects: {} | triggers : {}".format(c_entries, c_objects, c_triggers))
        print("\nWARNING: the current contents of cc.db will be replaced.")
        print("Previously deleted .sdr folders will not be restored.")
        if not ask("Restore this backup? [y/N]: "):
            print("Cancelled.")
            return 0

        os.makedirs(BACKUP_DIR, exist_ok=True)
        safety = os.path.join(BACKUP_DIR, "cc.db.before-restore-{}.sqlite".format(
            datetime.now().strftime("%Y%m%d-%H%M%S")))
        src = sqlite3.connect(db_path, timeout=30)
        dst = sqlite3.connect(safety)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        print("Current state saved: {}".format(safety))

        # SQLite backup API: copies pages with proper locking.
        source = sqlite3.connect("file:{}?mode=ro".format(backup), uri=True)
        target = sqlite3.connect(db_path, timeout=30)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

        r_entries, r_objects, r_triggers = summary(db_path)
        if (r_entries, r_objects, r_triggers) != (b_entries, b_objects, b_triggers):
            raise RuntimeError("verification failed: {} / {} / {} instead of {} / {} / {}".format(
                r_entries, r_objects, r_triggers, b_entries, b_objects, b_triggers))
        print("Verification OK: Entries {} | objects {} | triggers {}".format(r_entries, r_objects, r_triggers))
        print("Restore complete. RESTART THE KINDLE now (command: reboot).")
        return 0
    except Exception as exc:
        print("\nERROR: {}".format(exc))
        print("This script made no further changes after this error.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
