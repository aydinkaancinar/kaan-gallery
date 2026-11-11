# SQLite → Neon record transfer

The transfer script is [scripts/transfer_sqlite_to_neon.py](../scripts/transfer_sqlite_to_neon.py).
It requires an existing private SQLite snapshot, a Neon environment file with a
direct connection, and an explicit expected branch name. Default behavior is
preflight only; `--apply` imports into a destination without application records.
It permits migration-seeded categories only when their IDs/slugs match.

```bash
./.venv/bin/python scripts/transfer_sqlite_to_neon.py \
  --snapshot .backups/<snapshot-folder>/gallery.sqlite3 \
  --env-file .env.transfer --branch dev-data-transfer
```

Add `--apply` only for the intended destination after preflight. The script:

- Uses TLS and checks that all schema migrations are applied.
- Orders serialized models by Django's natural-key dependencies.
- Preserves full microsecond timestamp precision, primary keys, all serialized fields and relationships, password
  hashes, MFA devices/recovery tokens, admin history and Axes records.
- Uses a transaction and compares the imported records before committing;
  a verification failure rolls back the records. Many-to-many membership is
  compared without assuming database row order.
- Refuses to overwrite populated destinations. An already matching destination
  is a verified no-op, so it can be rechecked.
- Reuses generated permissions/content types via natural keys. It does not
  transfer sessions: destination login requires authentication and MFA again.
- Does not change SQLite, local image files, R2 objects or the app's selected DB.

## Sensitive backup files

Snapshots and fixture files under ignored `.backups/` contain account and MFA
secrets. Directory permissions are 700 and file permissions are 600. They are
not encrypted by the script; keep them on protected storage and do not share
or commit them. The fixture is created beside its SQLite snapshot.

An isolated `dev-data-transfer` branch is used for rehearsal before importing
into `main`. Its credentials are stored in ignored `.env.transfer`, separately
from `.env.local`; the workspace's main connection is preserved. That branch
will contain sensitive account data after a successful rehearsal and should
be removed once verification no longer needs it.

Keep admin edits paused between the snapshot and the final import. If local
records change, create a fresh snapshot and repeat verification before switching
the running app. Render deployment and production security remain separate work.

## Completed transfer — November 10, 2026

A SQLite backup passed `PRAGMA integrity_check`. Rehearsal on the isolated
`dev-data-transfer` branch passed before importing the same snapshot into `main`.
The verified transfer includes:

| Records | Count |
| --- | ---: |
| Artworks / image records | 10 / 31 |
| Artists / tags / categories | 2 / 5 / 7 |
| User | 1 |
| TOTP device / recovery device / recovery tokens | 1 / 1 / 10 |
| Admin history / Axes access log | 54 / 1 |

All serialized fields, IDs and relationships matched before commit. Full
microsecond timestamp precision was retained. Existing local sessions were not
copied. Generated permissions and content types were resolved by natural keys.
All 160 SQLite tests passed afterward; the 160 PostgreSQL test pass was already
verified on `dev-postgres-tests` before this transfer.

The running app remains on SQLite. This is a verified copy, not continuous
synchronization: changes after the snapshot must be reconciled before switching.
No production hosting was deployed by this step.

The temporary transfer branch and `.env.transfer` were removed after successful
main verification. The existing `dev-postgres-tests` branch was preserved.
Live checks on main passed for the artwork API and public/protected image
access. Private backup/fixture files remain available locally.

## Local application switch

After verifying that SQLite and Neon still matched the import snapshot, the
SQLite development server was stopped and restarted on port 8000 using
`./.venv/bin/python scripts/run_backend.py`. This selects
`config.settings_postgres`, reads the pooled connection from `.env.local`, and
retains the private R2 gateway. Plain `manage.py runserver` still defaults to
SQLite; use the explicit startup script for ongoing development.

The old SQLite database is now a rollback snapshot, not the active database.
Do not edit both databases. Reverting after PostgreSQL writes requires a
separate data reconciliation. The settings and server are still for local
development, not production deployment. Human password/MFA login confirmation
is the remaining manual check after this switch.

Live post-switch checks passed: artwork API and login page returned 200, six
card/detail/share responses matched retained local bytes, public originals
remained accessible, and protected originals returned 404 anonymously.
