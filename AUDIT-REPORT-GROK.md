# Wiki audit against the code that ships in 4.2

Each row is a claim that was wrong or not verifiable in the code. Evidence is a file path and a function or class name. Line numbers are omitted. Pages that were read and left unchanged are listed at the end.

## Bots-That-Talk

| Old claim | New claim | Evidence |
|---|---|---|
| `mesh_peers` lists at most 100 peers and cuts each summary to 200 characters, and never returns host, port or path. | On this computer the list is not capped and can include host, port and path. A connected web app sees a directory of at most 100 peers, each summary at most 200 characters, with no host, port or path. | `mcp/tools_mesh.py` `mesh_peers`; `mesh/broker.py` `MeshBroker.list_peers`; `mesh/broker_web.py` `list_peer_directory` |

## Compliance

| Old claim | New claim | Evidence |
|---|---|---|
| Agents below "the trust threshold" are blocked from write and delete, and trust is updated from outcome reports. The Trust tab was named without the Governance pane. | A new score starts at 0.5. A write is refused below 0.3 and a delete below 0.5 (`SLM_TRUST_WRITE_THRESHOLD`, `SLM_TRUST_DELETE_THRESHOLD`). Reads stay open unless `SLM_TRUST_READ_GATE=1`, and then the limit defaults to 0.1. The score moves on recorded signals (successful store, recall hit, confirmation, contradiction, access). An outcome report does not change it. Scores are under Governance, on the Trust tab. | `trust/gate.py` `TrustGate.check_write`, `check_delete`, `check_read`; `trust/scorer.py` `TrustScorer.record_signal`; `core/engine_wiring.py` `wire_hooks`; `mcp/tools_v28.py` `report_outcome`; `ui/js/od-shell.js` operations pane; `ui/js/od-operations.js` `buildSkeleton` |
| The page footer named a person. | The footer names Qualixar only. | No product behaviour. The name is not allowed on these pages. |

## GDPR-Compliance

| Old claim | New claim | Evidence |
|---|---|---|
| Article 15/20 export is `slm evidence export`, a checksummed JSONL bundle, from Governance → Data Privacy. | The export is `slm gdpr export --profile PROFILE`, plain JSON, embeddings omitted unless `--include-embeddings`. The dashboard path is Governance → Compliance → Data privacy & GDPR. `slm evidence export` is a different checksummed JSONL bundle. | `cli/gdpr_cmd.py` `_cmd_gdpr_export`; `compliance/gdpr.py` `export_profile_data`, `write_profile_export`; `cli/evidence_cmd.py` `cmd_evidence`; `ui/js/od-operations.js` `buildSkeleton` |
| Erasure has no profile command. Only `slm forget` and `slm delete` were listed, and the chain was called tamper-proof. | `slm gdpr erase --profile PROFILE` erases a profile (`--yes` runs it, `--dry-run` previews). `default` cannot be erased. There is no `slm profile delete`. `slm forget` and `slm delete` remove individual memories. The erasure event is written to the tamper-evident chain before deletion. | `cli/gdpr_cmd.py` `_cmd_gdpr_erase`; `compliance/gdpr.py` `forget_profile`; `compliance/audit.py` `AuditChain.log` |
| The audit trail records every store, recall, mutation and erasure, and `slm diagnostics export` shows it. | The chain records store, recall and delete, plus the erasure event written before a profile erase. Not every mutation is logged. `slm diagnostics export` is a content-free operational report and does not verify an erasure. | `core/engine_wiring.py` `wire_hooks`; `cli/diagnostics_cmd.py` `cmd_diagnostics` |
| `slm config set privacy.pii_redaction true` turns redaction on. | Redaction is off unless the enterprise deployment preset turns it on, or `SLM_PII_REDACTION` is set. `slm config set` has no key for it. | `cli/commands.py` `cmd_config`; `memory_core/save_path.py` `pii_redaction_enabled`; `core/config.py` `DeploymentConfig` |
| Erasure removes a fixed list of tables (memory, entity, graph, mesh, audit, session, backup, retention) and the chain is tamper-proof. | Erasure deletes rows from every memory-database table that has `profile_id`, except `profiles` and erasure receipts. It also clears the context cache and the graph and vector projections. The fact-expansion search index is erased with the profile's facts. Write receipts are erased on their own path because a trigger blocks an ordinary delete. In-database compliance-audit rows are deleted. The separate audit-chain file is written first and is not part of the sweep. | `compliance/gdpr.py` `forget_profile`, `_profile_scoped_tables`, `_erase_fact_keyed_tables`; `compliance/erasure_sidecars.py` `erase_profile_sidecars` |
| After erasure, verify with `slm diagnostics export` to a local file path. | Check the erasure receipt with `slm gdpr verify --receipt-id RECEIPT_ID`. Without a receipt id, `--profile` lists receipts. A verified receipt means that receipt's HMAC is intact, not that the whole chain was re-checked. | `cli/gdpr_cmd.py` `_cmd_gdpr_verify` |

## Ingestion-Adapters

| Old claim | New claim | Evidence |
|---|---|---|
| The example `adapters.json` used a home-directory path for this machine. | The example uses a generic path placeholder. | No product path. A home-directory example is not allowed on these pages. |

## Knowledge-Graph-and-Entities

| Old claim | New claim | Evidence |
|---|---|---|
| A semantic edge is kept when cosine similarity is above 0.7. | The edge is kept when similarity is at least 0.7. | `encoding/graph_builder.py` `GraphBuilder` (`_SEMANTIC_THRESHOLD`) |
| Association edges and PageRank are computed during consolidation. | Association edges are written when a fact is stored. Unused ones decay during consolidation. PageRank is computed later, on the maintenance scheduler. | `encoding/auto_linker.py` `AutoLinker.link_new_fact`; `core/store_pipeline.py` (write path); `core/consolidation_engine.py` (decay); `core/graph_metrics.py` `compute_graph_metrics`; `core/maintenance_scheduler.py` `_initial_graph_metrics` |
| `auto` for the graph and vector backends auto-promotes at 100,000 edges. | `auto` uses CozoDB or LanceDB when that library is installed, and SQLite otherwise. A separate setting, on by default, promotes the scale engine once the graph has at least 100,000 edges. | `core/config.py` (`graph_backend`, `vector_backend`, `scale_auto_promote_min_edges`); `core/backend_orchestrator.py` `_auto_promote_if_at_scale` |

## MCP-Tools

| Old claim | New claim | Evidence |
|---|---|---|
| `host only` means no remote caller can ever run the tool, and `expand` was marked host only. | `host only` means one of the 45 tools classified as host-only. `expand` is `refused`: it is not on the read, write, mesh or media lists, and the denial is the generic one, not the host-only message. | `server/remote_tool_policy.py` `tool_allowed` |
| Of 109 tools, anything not listed is host-only, and a test fails if a registered tool is unclassified. | 110 tools are registered. The policy classifies 109: 31 read, 23 write-only, 5 mesh, 5 media, 45 host-only. `expand` is the one not in those sets. The classification test expects every registered name in exactly one set; `expand` is not in them. | `server/remote_tool_policy.py` `READ_TOOLS`, `WRITE_ONLY_TOOLS`, `MESH`, `MEDIA`, `HOST_ONLY`, `tool_allowed`; `tests/test_security/test_remote_tool_policy.py` `test_every_registered_tool_is_classified_exactly_once` |
| The host-only row said "everything else". | The host-only row is the 45 classified tools. `expand` is not in that set. | `server/remote_tool_policy.py` `HOST_ONLY` |
| Company mode with login required refuses remote keys. | Company mode refuses `slm remote` keys for an enterprise deployment or a workspace that requires sign-in. If the mode cannot be read, the keys are refused as well. | `server/remote_access.py` `company_mode_active`, `gate_remote_mcp`; `cli/remote_commands.py` (remote check) |

## Pictures-and-Documents

| Old claim | New claim | Evidence |
|---|---|---|
| OCR uses Apple Vision on a Mac, or RapidOCR elsewhere only when it is already installed, and SLM never downloads RapidOCR. | Turning images and documents on installs RapidOCR with the other picture packages. On a Mac, OCR tries Apple Vision first and RapidOCR when Vision is missing or finds no text. Elsewhere it uses RapidOCR and the models bundled in that package. If the package cannot be imported, or those models are missing, OCR is skipped and the picture is still saved. | `runtimes/media_models.py` `MEDIA_REQUIREMENTS`; `runtimes/media_image_ops.py` `ocr_image`, `_apple_vision`, `_rapidocr`, `_local_ocr_params` |

## Profiles

| Old claim | New claim | Evidence |
|---|---|---|
| A profile name may use letters, digits, underscore and hyphen only. | A name must start with a letter or digit, then only letters, digits, underscore and hyphen, up to 50 characters. | `core/profiles.py` `_validate_name` |
| Deleting a profile moves memories, facts, the graph and everything that makes them findable in one transaction, and a failure leaves the profile in place. Pictures move afterwards and finish at the next daemon start. Saved views, receipts, Answer Check history and learned ranking state are erased. | Memories, facts, the graph and the indexes that make them findable move into `default` in one transaction. Saved views, Answer Check history and learned state are cleared before that transaction. Pictures and documents move after the commit. If that move fails, the profile is still deleted, the move is recorded, and it finishes at the next daemon start or before the next profile is created. Pending memories move. Write receipts and erasure receipts stay labelled with the deleted profile, as do the markers that refuse a late write. Learned ranker, bandit and signals are removed so they do not retrain `default`. | `server/routes/profiles.py` `delete_profile`; `server/routes/helpers.py` `delete_profile_from_db`; `storage/profile_fold.py` (decision table); `storage/profile_fold_sidecars.py` `purge_learned_state` |
| `slm remote keys add` requires `--profile`, and an unbound key is simply refused. The key was described as created for Web access. | Omitting `--profile` binds the key to the profile active at that moment. `--profile` names a different one. A key that still has no profile is refused. Keys made before this binding are bound once, on daemon start or any `slm remote keys` command. A `profile_id` on a call that names a different profile is refused. The key is for `slm remote`, not for the cloud Web access connector. | `cli/remote_commands.py` (add-key parser); `server/remote_keys.py` `RemoteKeyStore.bind_unbound` |
| Many editors cap tools from all servers at 50 to 100. | Editors often cap how many tools they load. The 50-to-100 range is not in this product, so it is not stated. | Not in the product. The range was removed rather than repeated. |

## Research-Foundations

| Old claim | New claim | Evidence |
|---|---|---|
| The four papers were attributed to a named person, and the governed-memory title named two further authors. | The papers are listed newest first. The governed-memory title no longer names co-authors. | No product behaviour. Personal names are not allowed on these pages. The arXiv ids are unchanged. |
| The continuous Hopfield network was attributed to named authors. | The sentence cites arXiv 2008.02217 and does not name authors. | `math/hopfield.py`. The citation id was already on the page. |
| An ablation table gave per-conversation scores, 832 questions, an answer model, and a gain from 6.0 to 19.9 points. | The benchmark note publishes the six-conversation average: 71.7% with the information-geometric layers and 58.9% without them, a gain of 12.7 points. Per-conversation scores, a question count and the answer model are not in that note, so they are not repeated. | `docs/benchmarks.md` (the ablation paragraph). The per-conversation table is not in that note. |

## Retrieval-Score-Contract

| Old claim | New claim | Evidence |
|---|---|---|
| The example JSON is the default response when nothing is configured, including `tier: supported` and `answer_check_status: off`. | A response that never reached the pipeline starts with `tier` empty and `answer_check_status` `skipped`. A completed recall with no answer check sets `answer_check_status` to `off`. `tier` stays empty until the support check labels the recall. The example is that completed, supported case with the check off. | `storage/models.py` `RecallResponse`; `server/recall_serializer.py` `_score_metadata`, `_check_metadata`; `core/answer_check_stage.py` `run_answer_check`; `core/score_contract.py` `finalize_score_contract` |
| Empty results are always `evidence_floor` or `no_candidates`, chosen only by a no-confident-match flag. | `abstained` is true when the list is empty, when a judged verdict says the results do not answer, or when support is not `supported`. Support overrides the other two. The reason order is `judged_insufficient`, then `unsupported` when an unsupported check recorded probabilities, then `judged_insufficient` again if results remain, then `evidence_floor` if the floor removed every result, otherwise `no_candidates`. | `core/score_contract.py` `finalize_score_contract`, `_abstention_reason` |
| `GET /recall` accepts only `full`, `no_reorder` and `skip`, and any other value is HTTP 400. | Empty and `full` run the complete check. `no_reorder` skips the reorder. `skip` runs no check. `context` also skips the check and skips the answer-support gate. Any other value is HTTP 400. The error names `skip`, `no_reorder` and `full`; it does not name `context`, which is accepted before that check. | `server/unified_daemon.py` `recall`; `core/answer_check_scope.py` `wants_skip`, `wants_context` |

## Web-Access-and-Connected-Apps

| Old claim | New claim | Evidence |
|---|---|---|
| Web access cannot be used in company mode while login is required, because remote keys are refused there. | That sentence was removed from the Web access rules. Company mode refuses `slm remote` keys, not the cloud connector. The condition is an enterprise deployment or a workspace that requires sign-in, and an unreadable mode refuses the keys as well. | `server/remote_access.py` `company_mode_active`; `cli/remote_commands.py` (remote check). No company-mode check under `remote_connections/`. |
| The remote listener serves only `/mcp` and `GET /health`. | It serves `/mcp` and any path under it. A bare `/mcp` is served as `/mcp/`. `GET` and `HEAD /health` are served. Any other path is 404. | `server/remote_listener.py` `RemoteMCPListener._allowed` |

## Pages read and left unchanged

Memory-Kinds, Upgrade-Memory-Engine, Installation, Dashboard-Tour and CLI-Reference were checked against the same code. No claim on those pages was changed in this pass. CLI-Reference had already been corrected in the previous commit on this branch. The product was not started, so `slm --help` was not re-run.

## Not re-opened

Individual host-only tool rows in MCP-Tools, other than `expand`, were not signature-checked one by one. The score-contract sentence that names five candidate producers was left in place; the fusion weights include those channels, and a producer registry was not re-opened. Ingestion poll intervals (300 seconds and 20 messages for mail, 900 seconds and a 30-day lookback for calendar, body cuts of 3,000, 2,000 and 5,000 characters, batches of 50, and the 60-second hourly-limit wait) match the adapter code and were left.
