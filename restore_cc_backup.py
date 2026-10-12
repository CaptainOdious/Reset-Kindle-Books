#!/mnt/us/python3/python/bin/python3
# -*- coding: utf-8 -*-
"""Restaure cc.db depuis une sauvegarde créée par les scripts de réinitialisation.

Usage :
  python3 restore_cc_backup.py                      # choix dans la liste
  python3 restore_cc_backup.py CHEMIN_SAUVEGARDE    # sauvegarde précise
  python3 restore_cc_backup.py CHEMIN_SAUVEGARDE CHEMIN_CC_DB
Les dossiers .sdr supprimés ne peuvent PAS être restaurés par ce script.
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
    return "{} ({:.1f} Mo, {})".format(os.path.basename(path), os.path.getsize(path) / 1048576.0, stamp)


def summary(path):
    """Résumé sans integrity_check : il aurait besoin de la collation ICU."""
    conn = sqlite3.connect("file:{}?mode=ro".format(path), uri=True)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "Entries" not in tables:
            raise RuntimeError("table Entries absente : ce n'est pas un cc.db valide")
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
            raise RuntimeError("sauvegarde introuvable : {}".format(path))
        return path
    backups = list_backups()
    if not backups:
        raise RuntimeError("aucune sauvegarde dans {}".format(BACKUP_DIR))
    print("Sauvegardes disponibles (la plus récente d'abord) :")
    for i, p in enumerate(backups, 1):
        print("  {}. {}".format(i, describe(p)))
    try:
        raw = input("Numéro à restaurer [1 = la plus récente] : ").strip() or "1"
        index = int(raw)
    except (EOFError, ValueError):
        raise RuntimeError("choix invalide")
    if not 1 <= index <= len(backups):
        raise RuntimeError("numéro hors de la liste")
    return backups[index - 1]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    db_path = args[1] if len(args) > 1 else DEFAULT_DB
    try:
        backup = choose_backup(args[:1])
        if not os.path.isfile(db_path):
            raise RuntimeError("cc.db introuvable : {}".format(db_path))
        if os.path.abspath(backup) == os.path.abspath(db_path):
            raise RuntimeError("la sauvegarde et cc.db sont le même fichier")

        b_entries, b_objects, b_triggers = summary(backup)
        c_entries, c_objects, c_triggers = summary(db_path)
        print("\nSauvegarde : {}".format(describe(backup)))
        print("  Entries : {} | objets de schéma : {} | triggers : {}".format(b_entries, b_objects, b_triggers))
        print("cc.db actuel : {}".format(db_path))
        print("  Entries : {} | objets de schéma : {} | triggers : {}".format(c_entries, c_objects, c_triggers))
        print("\nATTENTION : le contenu actuel de cc.db sera remplacé.")
        print("Les dossiers .sdr déjà supprimés ne seront pas restaurés.")
        if not ask("Restaurer cette sauvegarde ? [o/N] : "):
            print("Annulé.")
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
        print("État actuel conservé : {}".format(safety))

        # API de sauvegarde SQLite : copie les pages avec verrouillage correct.
        source = sqlite3.connect("file:{}?mode=ro".format(backup), uri=True)
        target = sqlite3.connect(db_path, timeout=30)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

        r_entries, r_objects, r_triggers = summary(db_path)
        if (r_entries, r_objects, r_triggers) != (b_entries, b_objects, b_triggers):
            raise RuntimeError("vérification échouée : {} / {} / {} au lieu de {} / {} / {}".format(
                r_entries, r_objects, r_triggers, b_entries, b_objects, b_triggers))
        print("Vérification OK : Entries {} | objets {} | triggers {}".format(r_entries, r_objects, r_triggers))
        print("Restauration terminée. REDÉMARREZ LE KINDLE maintenant (commande : reboot).")
        return 0
    except Exception as exc:
        print("\nERREUR : {}".format(exc))
        print("Aucune autre modification n'a été faite par ce script après cette erreur.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
