# Cloud Backup

SLM keeps three different kinds of copy, and they answer different questions. Local backups are scheduled snapshots of your databases in `backups/`. Cloud backup pushes the latest local snapshot to GitHub or Google Drive, encrypted on your computer first. Restore points are the verified copies SLM takes before an update that changes the store, and they are the only copies SLM can put back for you. Restore points are CLI and API only: there is no dashboard control for them.

## Local backups

A background job takes timestamped snapshots with SQLite's `sqlite3.backup()` API, which produces a consistent copy of each file even while the daemon is running. They go to `backups/` in the data folder.

| Setting | Default | Notes |
|---|---|---|
| Interval | 168 hours (weekly) | Minimum 1 hour. The Settings pane offers Daily (24 h) or Weekly. |
| Copies kept | 10 | Oldest are pruned. |

You can take one on demand from Settings, group "Backup", with "Backup Now", or `POST /api/backup/create`. Settings is also where you switch auto-backup off.

Which files are copied is a fixed list called `MANAGED_DATABASES`: `memory.db`, `learning.db`, `audit_chain.db`, `code_graph.db`, `pending.db`, `audit.db` and `media.db`. Only the ones that exist on your machine are copied. Each is snapshotted on its own, one after another, so a set is not a single atomic point in time across stores. For a consistent whole-folder copy, run `slm serve stop` and copy the data folder while the daemon is stopped.

Local copies of pictures and documents are included: `media.db` goes into `backups/` as `media-<timestamp>.db`, and one copy of every original picture and PDF is kept in `backups/media-originals/` (only new files are copied each time). They are never uploaded anywhere. Local backup files are plain SQLite and are not encrypted, so keep the data folder on an encrypted disk. Restoring a media copy puts back any original that is missing and never overwrites a file that is there.

No command or dashboard button restores a scheduled backup in place. To use one, stop the daemon, copy the file back as its canonical name (for example `memory.db`) into a clean data folder, and run `slm restart`.

## Cloud backup

When a cloud destination is connected, each scheduled backup is followed by a push of the latest set, and "Sync Now" pushes on demand. Both paths use `sync_all_destinations`. Pictures and documents are excluded by rule: any file whose name starts with `media-` is local only. That is a deliberate privacy choice, not a gap.

**GitHub.** Connect with a Personal Access Token with the `repo` scope, or sign in with GitHub in the dashboard. SLM creates a private repository named `slm-backup` (you can change the name) if it does not exist, and publishes each backup as a GitHub Release with the database files as assets. Only the last 5 releases are kept. If the repository already exists SLM reuses it without checking its visibility, so confirm an existing repository is private before connecting.

**Google Drive.** Google requires every app to register an OAuth client, so you supply your own client id and secret from Google Cloud Console and add the redirect URI `http://localhost:8765/api/backup/oauth/google/callback`. Files go into a `SLM-Backup` folder and are replaced in place, so there are no duplicates. Google Drive does not rotate old backups for you.

**Custom S3 or WebDAV.** The dashboard's Cloud Backup page lists a third row, "Custom S3 / WebDAV". It has no backend: there is no S3 or WebDAV route or module in the code, and its OAuth path does not exist. Treat it as not implemented.

Credentials go to your operating system's keychain (macOS Keychain, Windows Credential Locker, Linux Secret Service). Where no keychain exists, such as a headless server, they fall back to an owner-only file, `.credentials.json` in the data folder (mode 0600, directory 0700). That fallback file is not encrypted, so keep the data folder on an encrypted volume.

## Encryption

Every file is encrypted on your computer before upload, so GitHub and Google Drive only ever store ciphertext. A cloud backup carries the whole memory store, credentials included, which is why the encryption is not optional.

The format is AES-256-GCM over fixed-size chunks (the STREAM construction used by Tink and `age`). Each file gets its own key, derived with HKDF-SHA256 from your backup key and a random 96-bit nonce, and the header is authenticated, so reordering, splicing, truncation or appended data all fail to decrypt. Chunks are processed one at a time, so a multi-gigabyte database is never held in memory. Encrypted files end in `.slmenc`.

There is one 256-bit key per computer. It lives in the same credential store as your GitHub token, never beside the backup files, and SLM never replaces it silently. You see it as a recovery key that starts with `SLMBK1-`, base32 with a checksum so a typo is reported as a typo. If SLM has no key when a sync starts, it uploads nothing and says why.

```bash
slm backup status                   # encryption status and any notices
slm backup recovery-key             # show this computer's recovery key
slm backup recovery-key --import    # put a key on a new computer (read from stdin)
slm backup decrypt FILE -o OUT.db   # turn a download into a plain .db file
```

A recovery key is read only from stdin or a hidden prompt, never from the command line, so it stays out of shell history. Store it somewhere safe: without it a backup cannot be restored on another machine. Backups made before encryption still restore, and you should delete old plain-text ones from Google Drive yourself.

### Restoring from the cloud

1. Run `slm serve stop` so the write-ahead log is flushed before you replace files.
2. Download every database file from one timestamped run. Do not mix timestamps, and reject an incomplete set.
3. Run `slm backup decrypt FILE -o OUT.db` on each (on a new computer, import the recovery key first).
4. Quarantine the stopped data folder as an offline copy and restore into a clean folder, renaming each file to its canonical name: `memory.db`, `learning.db`, `audit_chain.db`, `code_graph.db`, `pending.db`, `audit.db`.
5. Check the files are owner-only (0600, folder 0700), then run `slm restart`.

Restoring into a clean folder matters because a stale `-wal` or `-shm` file beside a replaced database would replay against it. The cloud path does not upload `lance/` or write-ahead files, only the canonical databases.

## Restore points and downgrades

Before any update that changes the memory store, SLM takes a verified copy with a manifest and checksum. Those are restore points, and copies from the last two updates are kept. Unlike a cloud backup, SLM can restore one for you.

```bash
slm db restore-points                       # id, time, reason, versions, size, memory count
slm db restore <point_id> [--yes] [--no-reimport]
slm db restore --cancel                     # withdraw a restore that has not run yet
slm db prepare-downgrade [--yes]            # get the data ready for the previous SLM version
slm db prepare-downgrade --cancel
```

`slm db restore` shows a preview first, in counts and plain sentences: memories in the copy and now, those added since, those deleted or erased since, confirmed kinds that will be applied again, and learning records or corrections that cannot be carried over. It then asks you to type `RESTORE` (or pass `--yes`). It stops SLM, records the request and starts SLM again; the restore itself runs at start, before migrations, because restoring under a live engine is unsafe. If SLM cannot be stopped, the restore waits for the next start. After the copy is back, memories written after it are added again exactly once (`--no-reimport` skips that), anything you or a privacy erasure deleted stays deleted, kinds you confirmed are kept and erased profiles stay erased. A copy made by a newer version is refused, and a restore works even when the live store is damaged. Once it has started it cannot be cancelled half-way.

`slm db prepare-downgrade` exists because an older SLM refuses to open a store stamped by a newer one. It names the version to go back to and prints the install command. Preparation is allowed only when every change since that version is one the older build can safely ignore, and it takes a verified copy first.

The same actions exist over the local HTTP API under `/api/upgrade/` (`status`, `restore-points`, `restore/preview`, `restore`, `restore/cancel`, `prepare-downgrade`, `prepare-downgrade/cancel`). Changes need the install credential, MANAGE permission and a typed confirmation word, `RESTORE` or `DOWNGRADE`. Nothing in the dashboard calls these routes, even though the route's own docstring describes a dashboard card. Use the CLI. A repair started from the Health pane's "Memory store" card takes its own full backup first; see [Health and Repair](Health-and-Repair).

## Export and erasure

The dashboard's download button creates a single gzipped `memory.db` snapshot (`POST /api/backup/export`). It is not a whole-folder export. When you erase data with `slm gdpr erase`, SLM records the backup copies that may still contain it as "backup residue obligations", because it cannot reach into copies you hold elsewhere. See [Security, Company Mode and Teams](Security-Company-Mode-and-Teams).

Code: `infra/backup.py` (`BackupManager`, `MANAGED_DATABASES`), `infra/backup_media.py`, `infra/cloud_backup.py`, `infra/cloud_backup_github.py`, `infra/cloud_backup_crypto.py`, `infra/backup_crypto.py`, `infra/backup_keys.py`, `cli/backup_cmd.py`, `storage/upgrade_restore.py`, `cli/upgrade_cmd.py`, `server/routes/backup.py`, `server/routes/backup_encryption.py`, `server/routes/upgrade_restore.py`.
