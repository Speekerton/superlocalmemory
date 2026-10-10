# Upgrade Memory Engine

"Upgrade memory engine" is an opt-in preview that re-reads every memory with one model that understands both text and pictures, `google/embeddinggemma-2`, so text and pictures share one search space. It runs in the background inside the daemon. Recall and remember keep using your current engine the whole time, the switch happens in one step when the new vectors are complete, and you can roll back until you choose to free the old data. Nothing is deleted by the upgrade itself.

## Why it is optional

Vectors made by different models cannot be compared, so moving to a new model means re-embedding every memory. That costs memory, disk and time, and SLM does not do it behind your back. A new install starts on the default local model, `nomic-ai/nomic-embed-text-v1.5`. The first-run default that would put new users on the one-model engine is switched off in code (`ONE_MODEL_DEFAULT_ENABLED = False` in `runtimes/media_models.py`), and existing users never switch automatically. Turning on [Pictures and Documents](Pictures-and-Documents) does not change your existing text embeddings either: pictures and PDF pages are added next to them. The upgrade is a separate, deliberate step. It is also not related to [Modes](Modes-Explained): any of the three modes can run it.

## What you need

The upgrade is refused with a plain reason until the following are true. The plan checks the first four in this order; the memory check happens when you turn on images and documents.

| Requirement | Detail |
|---|---|
| Not already on the new engine | Otherwise it reports "Your memories already use the new engine." |
| No other embedding change running | Only one job runs at a time. Wait, or stop it with `slm embedder cancel`. |
| Pictures and documents turned on | `slm media enable`, or Settings. This downloads about 1.5 GiB of models and tools into SLM's own folder. |
| That environment finished installing | Check with `slm media status`. If it failed, `slm doctor` explains. On an unsupported computer, for example an Intel Mac, the card says so. |
| Enough memory | The images and documents feature needs 16 GB of RAM. Machines sold as 16 GB report slightly less, so the check passes from 15 GiB. `SLM_MEDIA_ALLOW_LOW_RAM=1` overrides it at your own risk. |

The card and `slm embedder upgrade` print the cost before you agree, from the same plan.

| Cost | How it is estimated |
|---|---|
| Memory (RAM) | 3000 MB while the model loads. The worker is stopped if it grows past 4500 MB. |
| Disk | The new vectors plus the kept previous ones: for each space, memories x dimensions x 4 bytes. When both are 768 dimensions (the default nomic model and EmbeddingGemma 2 are), that is about 3 KB per memory per space. |
| Time | 0.5 second per memory, shown as "about N minutes (a rough estimate)". |

These figures are marked provisional in the code. The time is not measured on your computer, and the RAM and disk numbers are to be confirmed by the Mac memory check. As an example, 10,000 memories would show roughly 30 MB for the new vectors and about 83 minutes. Treat that as the order of magnitude, not a promise.

## Running it

From the dashboard, open Settings, group "Embeddings & Retrieval", and use the Upgrade row. It shows the number of memories, the time estimate and the memory and disk needed, then asks you to confirm. From a terminal:

```bash
slm embedder upgrade          # prints the plan, then asks "Upgrade now? [y/N]"
slm embedder upgrade --yes    # no prompt; --no-wait returns as soon as it is queued
slm embedder status           # progress, the model in use, and whether a previous one is kept
slm embedder cancel           # stop a running job; the current engine stays
slm embedder rollback         # go back to the previous engine
slm embedder forget-previous  # free the previous engine's data
```

Off a terminal, or with `--json`, `upgrade` never starts unless you pass `--yes`. All the commands talk to the running daemon, so start it with `slm serve` if it is not running, and all take `--json`. `slm status` also prints one line while a switch is pending.

## What happens, and what stays usable

A job moves through the states `queued`, `running`, `catching_up`, `ready` and then `activated`; the other end states are `failed`, `rolled_back` and `cancelled`.

1. The daemon loads the new model under a RAM reservation. If another heavy job (a picture-model load, a document parse) holds the reservation, it waits up to 600 seconds, and fails with a plain message if memory is still short.
2. It asks the model one question to prove it is really loaded, then embeds every memory into a separate staging space, in batches of 32 with a short rest after each, so it takes about half of the daemon's interpreter time at most. Recall and remember keep using the old model and old vectors untouched.
3. It catches up with memories that were written or edited meanwhile, using a change log, so nothing saved during the upgrade is missed.
4. It waits for a quiet moment (up to 600 seconds), pauses background work, drains the requests already admitted and holds new ones for an instant. In that window one transaction makes the new space live, `config.json` is rewritten and an engine on the new model is published. Requests resume only after that, so no request can pair the new model with the old vectors.
5. A settle pass fixes up anything that changed during the swap.

If anything fails, the old space stays live. If publishing the new engine fails after the swap, the swap is reversed at once. A daemon restart resumes a running job at its cursor rather than starting over. A swap that finds new writes goes back to catching up, and one where requests do not drain in 30 seconds retries with a growing delay.

## Rolling back and freeing the old data

SLM keeps exactly one previous space. Roll back from the card ("Roll back"), or `slm embedder rollback`. A rollback is itself a background job: it first starts the previous model and checks it answers, and if that model is no longer available it refuses and tells you to make it available again, then retry. It re-uses the same swap, so recall keeps working while it runs.

"Free the old data", or `slm embedder forget-previous`, deletes the previous space and ends the option to roll back. The card says so before it acts. Until you do that, the old vectors stay on disk. The next model switch moves the then-live space into the "previous" slot and drops the older one, so "until you free it" holds only as long as you do not change engines again. You cannot free the previous space while a rollback is running.

## Switching to a different model instead

`slm embedder switch MODEL --dimension N [--provider P] [--endpoint URL]` uses the same background machinery for any model, including a custom OpenAI-compatible endpoint, and is how the Settings pane applies an embedding change. The upgrade is the same job with a fixed target and the checks above. The dimension must be 64 to 8192 and must be given for a new model. The tuning variables are `SLM_REINDEX_BATCH` (32), `SLM_REINDEX_PAUSE_S` (0.02) and `SLM_REINDEX_DUTY_REST` (1.0). See [Configuration](Configuration) and [Modes Explained](Modes-Explained).

The HTTP routes, for completeness, are under `/api/v3/embedding/reindex`: `GET` (status), `POST` (start a switch), `/upgrade` (`GET` for the plan, `POST` to start), `/rollback`, `/cancel` and `/forget-previous`. Changes need MANAGE permission.

Code: `core/engine_upgrade.py`, `core/embedding_reindex.py`, `core/embedding_reindex_steps.py`, `core/embedding_reindex_activate.py`, `storage/embedding_spaces.py`, `storage/embedding_space_swap.py`, `cli/embedder_cmd.py`, `server/routes/embedding_reindex.py`, `runtimes/media_models.py`, `core/one_model_default.py`, `ui/js/od-engine-upgrade.js`.
