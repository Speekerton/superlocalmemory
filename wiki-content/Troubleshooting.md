# Troubleshooting

Start with `slm doctor`. It checks dependencies, the embedding worker, whether the background service answers, and your configuration, and it prints the fix next to anything that is wrong. Add `--json` for a machine-readable result.

```bash
slm doctor            # the full check
slm doctor --quick    # dependencies and configuration only
slm doctor --deep     # also reads every database page (slow on a large store)
slm doctor --fix      # re-downloads missing models and installs sqlite-vec first, then reports
slm status --json     # mode, profile, database size, counts
```

## Install and connect

If `slm` is not found after `npm install -g superlocalmemory`, the npm global bin folder is not on your PATH. If the installer says the Python it found cannot work, install a supported 64-bit Python (3.12 to 3.14) and run `npm rebuild -g superlocalmemory`. See [[Installation]]. If an agent does not show SLM's tools, run `slm connect --list` to see what is configured, `slm connect <ide>` to configure one, and restart the agent. For hosts that were set up by an older SLM, `slm upgrade-hosts` previews what would be refreshed and changes nothing until you add `--apply`. See [[IDE Setup]] and [[Host Upgrades]].

## Saves and recall

A memory is searchable by its wording the moment `slm remember` returns, and by meaning shortly afterwards. Use `--sync` when the next step needs the full enrichment to be finished. If recall finds nothing you know is there, try a broader query and run `slm trace "your query"` to see how each channel scored. Recall can also say it has nothing: when no memory supports the question, it answers that nothing was found rather than guessing.

**Failed saves.** `slm doctor` has a **Failed saves** row. It warns when saves were given up on after repeated attempts, so those memories may lack entities or graph links, and fails at 50 or more. List them and decide:

```bash
slm ops status
slm ops list
slm ops resolve <operation_id> --action retry     # or --action cancel
```

**Memories that disappeared from recall.** If a memory was moved to the archive although it still scores high, `slm doctor --refile-hidden` lists them and changes nothing; add `--yes` to move exactly those back.

**Wrong people or projects in answers.** Before 4.1.25, entity names were matched loosely and could chain unrelated names together. `slm db repair-entities` previews the clean-up; `--apply --root <data folder>` makes a backup and applies it, and `--undo <run_id>` reverses it.

## The memory store

```bash
slm db integrity            # read-only; safe while SLM runs
slm db integrity --pages    # also reads every page
slm db repair --root ~/.superlocalmemory     # preview a repair
slm db repair --apply --root ~/.superlocalmemory
```

The dashboard's **Memory store** card under **Health** shows the same check, and **Repair now** saves a full backup copy before it changes anything. If the keyword index is reported damaged, the message names the exact repair command; your memories are kept. To go back to an earlier state, see [[Backup and Restore]].

## Pictures and documents

`slm media status` says what is on and how set-up is going. If turning the feature on is refused, the reason is the memory check (16 GB) or an unsupported system; see [[Pictures and Documents]]. A PDF marked as not finished shows why (password, too many pages, a page that took too long); **Try again** retries it. `slm media gc` reports leftovers and `slm media repair` makes pictures findable by what they show.

## Web access

Problems show on the dashboard's **Connected apps** page or as an error code in the app. Local SLM keeps working through all of them.

| What you see | What to do |
|---|---|
| The page says Connected apps are not available right now | The local service is not running. Run `slm status`, then `slm restart`. |
| Sign-in does not finish, or the link expired | Use **Continue sign-in** if your browser blocked the page, or **Restart sign-in**, which keeps your permissions. |
| `connector_asleep` or `connector_offline` | Your computer is asleep or offline. Wake it, check its network, and try again. |
| `DAILY_LIMIT_REACHED` | The free daily allowance is used; it resets at midnight UTC. |
| `relay_busy` or `relay_timeout` | Too many calls at once, or one took over 25 seconds. Make one call at a time. |
| `TOOL_DENIED` or `INSUFFICIENT_SCOPE` | The app was not given that permission. Remove the app and add it again with the box ticked. |
| `REVOKED` or `ENTITLEMENT_REQUIRED` | The app was removed or Web access ended. Turn it on again on the Connected apps page. |
| The app saves nothing | Saving is a separate permission; check the app's row for **Save**. |

See [[Connect Web Apps]].

## Company mode and sign-in

With login required, the install token or an API key alone no longer administers the workspace; use an admin account, or run `slm team status` and `slm team policy --require-login on|off` on the SLM computer. `slm token show` prints the key the dashboard asks for when `SLM_REQUIRE_CREDENTIALS=1`. See [RBAC and Teams](RBAC-Teams).

## Still stuck

Run `slm doctor --json` and `slm status --json`, look at `logs/daemon.log` in the data folder, and open an issue at [GitHub](https://github.com/qualixar/superlocalmemory/issues) with that output. `slm diagnostics export ./slm-diagnostics.json` writes a local, content-free summary you can inspect before sharing.
