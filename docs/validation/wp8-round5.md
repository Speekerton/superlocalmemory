# WP-8 round 5 validation

Validated code: `9b42a746bc3cbfdec4bd804ee0ab7cddaf22b504`. Starting head: `c62419a7`. Release archive: `cb235fa1f22241f31c664c8eb3f3d8041429d030`.

Zero new failures. Six inherited failures are already fixed on verified open PR branches and remain unchanged under the owner's explicit exception. No pushes; the live data root and ports 8765/8767 were not used.

## Changes

- Keep feature-dependent media discovery while dispatching selected tools to their existing refusal handlers. Explicit host allowlists still block calls.
- Opt media behavior fixtures in through `enable_media(source="api", start_install=False)` under test-root isolation. Restore fixture-created profile import snapshots at teardown. Keep exact registration/discovery sets: default 62/57, core 18/18, whole 109/104 while images are off.
- Preserve synchronous standalone `MemoryEngine.store(require_complete=True)`. ANN/vector projections are optional when no embedder exists; model-present requirements remain intact. A new offline regression requires complete lexical materialization, not merely a queryable receipt.
- Align the public canonical-call test with synchronous completion. Seed the cold-recall test through real nonblocking canonical admission; all warming, loaded-once and latency assertions remain intact. No production change to `EmbeddingService.has_loaded_once`.

## Whole-directory results

Directories ran one at a time with the project's default marker exclusions. The final whole-MCP rerun follows the fixture-cache correction. UI ran with `node scripts/run-ui-tests.mjs`.

| Suite | Passed | Failed | Skipped | Deselected |
|---|---:|---:|---:|---:|
| `tests/test_mcp` | 658 | 0 | 0 | 0 |
| `tests/mcp` | 216 | 0 | 1 | 0 |
| `tests/test_modes` | 48 | 0 | 1 | 0 |
| `tests/test_core` | 2,628 | 1 | 0 | 1 |
| `tests/test_retrieval` | 1,873 | 0 | 0 | 5 |
| `tests/test_security` | 943 | 1 | 0 | 0 |
| `tests/test_server` | 1,211 | 0 | 0 | 0 |
| `tests/server` | 150 | 0 | 1 | 0 |
| `tests/test_integration` | 151 | 4 | 1 | 137 |
| `tests/test_ci_guards` | 163 | 0 | 9 | 0 |
| `UI` | 705 | 0 | 0 | 0 |

Totals: 8,746 passed, 6 inherited failures, 13 skipped, 143 deselected.

## Inherited failures and independent verification

| Failure | Release archive | Verified owner | Owning-fix archive |
|---|---|---|---|
| `report_outcome.report_id` classification | Same failure; original baseline 499 passed / 1 failed | [PR 244](https://github.com/qualixar/superlocalmemory/pull/244), included in open [batch PR 246](https://github.com/qualixar/superlocalmemory/pull/246); commit `33acbd985` | 450 remote-profile-binding tests pass on PR 253, which also contains this fix |
| Exact answer envelope omits `graph_lag_s` | 1 failed / 6 passed in the same file | Open [PR 253](https://github.com/qualixar/superlocalmemory/pull/253), head `97799ea18` | 7 passed |
| Four `TestModeBModelExtraction` source-fidelity tests | Same four failures | Open [PR 242](https://github.com/qualixar/superlocalmemory/pull/242), head `44cd3c47`; fix `156932bd6` also in batch PR 246 | 5 passed, including an added regression |

Open states and head SHAs were read through the GitHub connector. Branch ancestry was checked locally. All comparison archives used separate directories and the test isolation guard.

## Checks and evidence

- Original media/exposure reproduction: 85 failed / 11 passed. After repair: affected media, live discovery, exact exposure and prestage contracts 105 passed; final whole MCP 658 passed.
- Offline materialization regression first reproduced `incomplete derivation stages: ann, vector`; corrected focused set 46 passed, including standalone completion.
- Code and Python reviews approved each fix. Staged diff/secret checks and GitNexus change detection ran before local fix commits. Ruff comparison: 28 existing issues at both starting and final code, zero new issues.
- GitNexus round-only comparison: 13 files, 36 indexed symbols, zero indexed affected flows, low risk. Main comparison spans the older August branch: 3,096 files / 259 flows, critical aggregate scope; this was reported. FTS search extension download is unavailable (404); symbol impact/context still ran.

Full logs, isolated release/owner archives, work record and machine verification: `/private/tmp/slm-codex-impl/wp8-connectivity/round5`. `directory-results.json` contains final per-directory receipts; the failed preliminary MCP run is preserved separately as `tests-test_mcp-before-fixture-isolation.log`.

The live SuperLocalMemory store was not used for recall or persistence; this receipt and the isolated work record are the durable task handoff.
