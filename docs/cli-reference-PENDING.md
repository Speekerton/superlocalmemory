# CLI reference: commands not yet in a release

These commands are on branches that have not been merged into the 4.1.25
release branch. They are documented here so the text is ready when the branch
merges. Until then, nothing on this page exists in the released `slm`. When a
branch merges, move its section into `docs/cli-reference.md` and the wiki's
CLI Reference, and delete it here. When every section has moved, delete this file.

Branch state when this page was written (2026-10-11): `wp/wp9-governance` at
a9609604. That branch was local to the builder's worktree. Its snapshot on
GitHub is `wip/wp9-governance`; there is no PR yet. The help text below came
from running `--help` on that commit's code in an isolated data folder. The
other open branches add no CLI commands or flags. They were checked by
comparing the full parser tree with the release branch:
`wp/wp8-connectivity` 8aaffe3a, `wp/wp11-brain-batch2` 71b9afdc,
`batch/242-244` b9cac78f, `wp/wp13-hygiene` e5cb6892,
`wp/wp6-answer-check-embeddings` 34a251fb, `wp/wp10-dashboard` fd296c13 and
`wp/wp4b-recall-latency` bfe05f01.

## From `wp/wp9-governance`

### `slm ops repair-saves [--apply] [--json]`

Before 4.1.25, fact deduplication matched on content alone, so some saves were
folded onto another memory's fact. Their memory never got its own fact, and `slm ops status` counts
them as failed saves. This command re-files those saves. Without `--apply`, it
opens `memory.db` read-only and prints what it would do. The output lists the
saves to re-file, the saves left alone for review (each with its reason), the
agent names that can be backfilled from the save record, and the memories whose
agent is known nowhere. Nothing is changed.

```bash
slm ops repair-saves            # dry run
slm ops repair-saves --apply    # back up memory.db, then repair
slm ops repair-saves --json
```

`--apply` backs up `memory.db` first and then re-files the saves. A save operation that
changed since the plan was made (retried or cancelled) is skipped, never overwritten. The command prints how many saves it
re-filed, how many it skipped, how many agent names it backfilled, and where the
backup is. The running service enriches the re-filed saves on its next pass. The
command reads and writes the data folder's `memory.db` directly, like
`slm doctor`, so it also works with the service stopped. In a workspace that
requires sign-in it is the computer owner's tool: it needs file access to the
data folder, nothing else.

### `slm team admin <username> [--profile NAME]`

This makes an account an administrator of a workspace. Without `--profile` it uses
the active workspace. It is the way back in when every administrator is locked out.

### `slm team reset-password <username> [--password-stdin]`

This sets a new password for an account. The account's old sessions are signed
out. By default the command asks for the password twice without echoing it.
`--password-stdin` reads it from standard input, for scripts. A password shorter
than 8 characters, or two entries that differ, change nothing.

Both `team` commands talk to the running SLM. They send the daemon capability,
a private file that only the user running SLM can read, rather than the
dashboard's install token. They therefore work even when the workspace requires
login and no administrator can sign in. Run them as the same user that runs SLM;
otherwise the daemon refuses. If SLM is not running, they say so and change
nothing.
