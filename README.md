# Reset Kindle Books

An interactive KUAL extension that resets the reading progress of new downloaded books whose progress has automatically jumped between 0% and 1% without being opened, then restores their **NEW** badge. It can also restore a previous backup of `cc.db`.

The extension is designed to be launched from the Kindle menu through **KUAL** and runs in **KTerm**, keeping its output visible and writing an operation log.

## Features

- **Reset in-progress books**: targets books whose `p_percentFinished` value is strictly greater than 0 and strictly less than 1.
- **NEW badge**: sets `j_displaytags` back to `["NEW"]` after a reset.
- **Badge repair**: detects books that were already reset but are displayed at 0% without a NEW badge, then restores the badge.
- **SDR cleanup**: removes the `.sdr` folders associated with reset books to clear stored reading positions, unless `--skip-sdr` is used.
- **Automatic backup**: creates a timestamped copy of `cc.db` before making changes.
- **Restore**: lets you select and restore a previous `cc.db` backup.
- **Logging**: records output to `/mnt/us/documents/reset_books.log`.

## Warning

This project directly modifies the Kindle `cc.db` database and deletes `.sdr` folders. A database backup is created automatically, but **deleted `.sdr` folders cannot be restored** by the restore script.

Use it only on a Kindle you control and only if you understand the risks. Make a copy of `/mnt/us/documents` before first use.

## Requirements

- A jailbroken Kindle.
- **KUAL/KUALA/KUAL Next** installed.
- **KTerm** installed at `/mnt/us/extensions/kterm`.
- Kindle Python 3 available at `/mnt/us/python3/python/bin/python3`.

## Installation

1. Copy the extension folder to the Kindle:

   ```text
   /mnt/us/extensions/reset_books/
   ```

2. Ensure the folder contains at least:

   ```text
   /mnt/us/extensions/reset_books/
   ├── config.xml
   ├── menu.json
      /bin
      ├── run.sh
      ├── run_reset.sh
      ├── run_restore.sh
      ├── run_inner.sh
      ├── reset_kindle_books.py
      └── restore_cc_backup.py
   ```

3. Make the shell scripts executable:

   ```sh
   chmod +x run.sh run_reset.sh run_restore.sh run_inner.sh
   ```

4. Restart the Kindle or reload KUAL to refresh the menu.

## Usage

### From KUAL

Open **KUAL > Reset Kindle Books**:

- **Analyze and reset books**: runs `reset_kindle_books.py`.
- **Restore a cc.db backup**: runs `restore_cc_backup.py`.

### Reset books

The script first analyzes the database, lists the affected books, and asks for confirmation before making any changes.

```sh
/mnt/us/python3/python/bin/python3 reset_kindle_books.py
```

To keep the `.sdr` folders:

```sh
/mnt/us/python3/python/bin/python3 reset_kindle_books.py --skip-sdr
```

To use a specific database:

```sh
/mnt/us/python3/python/bin/python3 reset_kindle_books.py /path/to/cc.db
```

### Restore a backup

Without arguments, the script lists available backups in `/mnt/us/documents/ccdb_reset_backups`, newest first:

```sh
/mnt/us/python3/python/bin/python3 restore_cc_backup.py
```

To restore a specific backup:

```sh
/mnt/us/python3/python/bin/python3 restore_cc_backup.py /mnt/us/documents/ccdb_reset_backups/cc.db.backup-YYYYMMDD-HHMMSS.sqlite
```

Before restoring, the script creates a safety backup of the current `cc.db` state.

## Files

| File | Purpose |
|---|---|
| `config.xml` | KUAL extension metadata. |
| `menu.json` | KUAL menu entries. |
| `run.sh` | Entry point: opens KTerm and runs the requested mode. |
| `run_reset.sh` | Runs the `reset` mode. |
| `run_restore.sh` | Runs the `restore` mode. |
| `run_inner.sh` | Runs the Python script, displays output, and writes the log. |
| `reset_kindle_books.py` | Analyzes, backs up, resets, and repairs books. |
| `restore_cc_backup.py` | Lists, verifies, and restores a `cc.db` backup. |

## Important paths

| Item | Path |
|---|---|
| Kindle database | `/var/local/cc.db` |
| Kindle documents | `/mnt/us/documents` |
| Created backups | `/mnt/us/documents/ccdb_reset_backups` |
| Log file | `/mnt/us/documents/reset_books.log` |
| Extension folder | `/mnt/us/extensions/reset_books` |

## Technical behavior

- The main script creates a timestamped SQLite backup before modifying the database.
- `UPDATE` triggers on the `Entries` table are temporarily removed because they may call Kindle-specific functions unavailable from Python.
- Database changes run inside a SQLite transaction: if an error occurs, a `ROLLBACK` leaves `cc.db` unchanged.
- Triggers are recreated exactly as they were before `COMMIT`.
- After a successful reset, the script offers to reboot the Kindle so the catalog is reloaded.

## Troubleshooting

- **KTerm not found**: install KTerm at `/mnt/us/extensions/kterm`.
- **Inner script not found**: check that every file is present in `/mnt/us/extensions/reset_books`.
- **No backups available**: check the contents of `/mnt/us/documents/ccdb_reset_backups`.
- **Prompts are invisible**: use `run.sh` / KTerm; `run_inner.sh` keeps interactive output visible.
- **Check errors**: inspect `/mnt/us/documents/reset_books.log`.

## License

This project is licensed under the terms of the  
[GNU General Public License v3.0](./LICENSE).
