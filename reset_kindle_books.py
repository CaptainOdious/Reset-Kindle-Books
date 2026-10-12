#!/mnt/us/python3/python/bin/python3
# -*- coding: utf-8 -*-
"""Reset Kindle books with 0 < p_percentFinished < 1 and restore their NEW badge.

Usage: python3 reset_kindle_books.py [cc.db_path] [--skip-sdr]
Default: /var/local/cc.db
"""
import glob
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime

DEFAULT_DB = "/var/local/cc.db"
DOCUMENTS_DIR = "/mnt/us/documents"
BACKUP_DIR = "/mnt/us/documents/ccdb_reset_backups"
NEW_TAGS = '["NEW"]'


def qi(name):
    return '"' + name.replace('"', '""') + '"'


def strictly_between_0_and_1(value):
    if value is None:
        return False
    try:
        return 0.0 < float(value) < 1.0
    except (TypeError, ValueError, OverflowError):
        return False


def find_sdr(location):
    if not location:
        return []
    location = str(location)
    if location.startswith("file://"):
        location = location[7:]
    stem = os.path.splitext(os.path.basename(location))[0]
    candidates = []
    parent = os.path.dirname(location)
    if parent:
        candidates.append(os.path.join(parent, stem + ".sdr"))
    if location.lower().endswith(".sdr"):
        candidates.append(location)
    candidates += glob.glob(os.path.join(DOCUMENTS_DIR, stem + ".sdr"))
    candidates += glob.glob(os.path.join(DOCUMENTS_DIR, "**", stem + ".sdr"), recursive=True)
    out, seen = [], set()
    for p in candidates:
        p = os.path.normpath(p)
        if p not in seen and os.path.isdir(p):
            out.append(p)
            seen.add(p)
    return out


def ask(question):
    try:
        return input(question).strip().lower() in ("o", "oui", "y", "yes")
    except EOFError:
        return False


def update_trigger_rows(conn, table):
    """UPDATE triggers for the table: they call Kindle-specific functions
    unavailable in Python, so they are removed temporarily during the update."""
    rows = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='trigger' "
        "AND lower(tbl_name)=lower(?) AND sql IS NOT NULL", (table,)).fetchall()
    result = []
    for name, sql in rows:
        header = re.split(r"\bBEGIN\b", sql, maxsplit=1, flags=re.I)[0]
        if re.search(r"\bUPDATE\b", header, flags=re.I):
            result.append((name, sql))
    return result


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    skip_sdr = "--skip-sdr" in sys.argv[1:]
    db_path = args[0] if args else DEFAULT_DB
    if not os.path.isfile(db_path):
        print("ERROR: database not found: {}".format(db_path))
        return 1
    print("Database: {}".format(db_path))

    conn = None
    backup_path = None
    in_tx = False
    try:
        conn = sqlite3.connect(db_path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")

        os.makedirs(BACKUP_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, "cc.db.backup-{}.sqlite".format(stamp))
        bconn = sqlite3.connect(backup_path)
        try:
            conn.backup(bconn)
        finally:
            bconn.close()
        print("Backup: {}".format(backup_path))

        table = next((r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'") if r[0].lower() == "entries"), None)
        if not table:
            raise RuntimeError("Entries table not found")
        columns = [r[1] for r in conn.execute("PRAGMA table_info({})".format(qi(table)))]
        cmap = {c.lower(): c for c in columns}
        uuid_col = cmap.get("p_uuid")
        pct_col = cmap.get("p_percentfinished")
        if not uuid_col or not pct_col:
            raise RuntimeError("p_uuid / p_percentFinished columns not found")
        loc_col = cmap.get("p_location")
        type_col = cmap.get("p_type")
        title_col = cmap.get("p_titles_0_nominal")
        state_col = cmap.get("p_readstate")
        pos_col = cmap.get("p_lastaccessedposition")
        tags_col = cmap.get("j_displaytags")
        arch_col = cmap.get("p_isarchived")
        vis_col = cmap.get("p_isvisibleinhome")

        sql = "SELECT {} FROM {}".format(", ".join(qi(c) for c in columns), qi(table))
        params = []
        if type_col:
            sql += " WHERE lower({}) = ?".format(qi(type_col))
            params.append("entry:item")
        all_rows = conn.execute(sql, params).fetchall()

        def title_of(r):
            location = r[loc_col] if loc_col else None
            return (r[title_col] if title_col else None) or (
                os.path.basename(str(location)) if location else str(r[uuid_col]))

        # Group 1: books with progress strictly between 0 and 1 -> full reset.
        reset_rows = [r for r in all_rows if strictly_between_0_and_1(r[pct_col])]

        # Group 2: previously reset books without a NEW badge (shown as 0%).
        repair_rows = []
        if tags_col and state_col:
            for r in all_rows:
                if r[pct_col] is None and r[state_col] is None and r[tags_col] == "[]":
                    if arch_col and r[arch_col] != 0:
                        continue
                    if vis_col and r[vis_col] != 1:
                        continue
                    repair_rows.append(r)

        print("\n=== Books with 0 < progress < 1: {} ===".format(len(reset_rows)))
        sdr_by_uuid = {}
        for i, r in enumerate(reset_rows, 1):
            found = [] if skip_sdr else find_sdr(r[loc_col] if loc_col else None)
            sdr_by_uuid[r[uuid_col]] = found
            print("{:>3}. {} | progress {} | SDR : {}".format(
                i, title_of(r), r[pct_col], len(found)))

        if repair_rows:
            print("\n=== Previously reset books without a NEW badge (shown as 0%): {} ===".format(len(repair_rows)))
            for i, r in enumerate(repair_rows, 1):
                print("{:>3}. {}".format(i, title_of(r)))

        do_reset = bool(reset_rows) and ask(
            "\nReset the {} book(s) with 0 < progress < 1? [y/N]: ".format(len(reset_rows)))
        do_repair = bool(repair_rows) and ask(
            "Restore the NEW badge on the {} previously reset book(s)? [y/N]: ".format(len(repair_rows)))
        if not do_reset and not do_repair:
            print("No changes requested.")
            return 0

        reset_uuids = [r[uuid_col] for r in reset_rows] if do_reset else []
        repair_uuids = [r[uuid_col] for r in repair_rows] if do_repair else []

        # Delete SDR folders BEFORE editing cc.db.
        if do_reset and not skip_sdr:
            paths = sorted({p for u in reset_uuids for p in sdr_by_uuid.get(u, [])})
            deleted = 0
            for p in paths:
                try:
                    shutil.rmtree(p)
                    deleted += 1
                    print("SDR folder deleted: {}".format(p))
                except FileNotFoundError:
                    pass
                except Exception as exc:
                    print("FAILED to delete SDR folder {} : {}".format(p, exc))
            print("SDR folders deleted: {}".format(deleted))

        triggers = update_trigger_rows(conn, table)
        print("UPDATE triggers temporarily removed: {}".format(
            ", ".join(n for n, _ in triggers) or "none"))

        reset_sets = ["{}=NULL".format(qi(pct_col))]
        reset_sets += ["{}=NULL".format(qi(c)) for c in (state_col, pos_col) if c]
        if tags_col:
            reset_sets.append("{}='{}'".format(qi(tags_col), NEW_TAGS))
        reset_sql = "UPDATE {} SET {} WHERE {}=?".format(
            qi(table), ", ".join(reset_sets), qi(uuid_col))
        repair_sql = None
        if tags_col:
            repair_sql = "UPDATE {} SET {}='{}' WHERE {}=? AND {}='[]'".format(
                qi(table), qi(tags_col), NEW_TAGS, qi(uuid_col), qi(tags_col))

        # ONE transaction: on error, ROLLBACK also undoes the
        # removal/recreation of triggers (SQLite DDL is transactional).
        conn.execute("BEGIN IMMEDIATE")
        in_tx = True
        for name, _ in triggers:
            conn.execute("DROP TRIGGER {}".format(qi(name)))
        reset_done = repair_done = 0
        for uid in reset_uuids:
            reset_done += conn.execute(reset_sql, (uid,)).rowcount
        if repair_sql:
            for uid in repair_uuids:
                repair_done += conn.execute(repair_sql, (uid,)).rowcount
        for _, trigger_sql in triggers:
            conn.execute(trigger_sql)
        if reset_done != len(reset_uuids) or repair_done != len(repair_uuids):
            raise RuntimeError("Unexpected number of updated rows ({}/{} et {}/{})".format(
                reset_done, len(reset_uuids), repair_done, len(repair_uuids)))
        if {n for n, _ in update_trigger_rows(conn, table)} != {n for n, _ in triggers}:
            raise RuntimeError("The triggers were not restored correctly")
        conn.execute("COMMIT")
        in_tx = False
        print("\nBooks reset: {}".format(reset_done))
        print("NEW badges restored (previously reset): {}".format(repair_done))
        print("Triggers restored: {}".format(len(triggers)))
        print("Completed without errors.")
        success = True
    except Exception as exc:
        if conn is not None and in_tx:
            try:
                conn.execute("ROLLBACK")
                print("ROLLBACK completed: cc.db is unchanged.")
            except Exception as rb:
                print("ROLLBACK ERROR: {}".format(rb))
        print("\nERROR: {}".format(exc))
        if backup_path:
            print("Backup: {}".format(backup_path))
        return 1
    finally:
        if conn is not None:
            conn.close()

    if success and db_path == DEFAULT_DB:
        if ask("\nRestart the Kindle now? [y/N]: "):
            print("Restarting...")
            sys.stdout.flush()
            subprocess.call(["reboot"])
        else:
            print("Remember to restart the Kindle to reload the catalog.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
