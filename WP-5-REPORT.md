# WP-5 extraction fidelity

Branch: `wp/wp5-extraction-fidelity`. Baseline: `5bfa47c`.
Local commits only; no push, PR or merge.

## Findings and changes

| Defect | Verified root cause and fix | RED → GREEN evidence |
|---|---|---|
| L-01 / ENG-14 | Schema examples leaked Alice/Google; facts lacked assertion/attribution checks; an exact-prefix shortcut accepted `2004.` from `2004.6 ms`. Neutral prompts, grounded speakers/entities, token-boundary source spans, deterministic rejection/quarantine, 5-fact cap, and partial-duplicate collapse. Protected source projection survives consolidation. | `test_wp5_fidelity`, `test_source_fidelity_guard`, `test_saved_memory_keeps_its_own_fact`; real Ollama before/after corpus below. |
| N-09 / ENG-02 | Adjacent sentence pairing preceded speaker normalization and globally rewrote quotations. Turn boundaries, explicit alternating caller speakers, quotation-aware normalization including contractions/multiline quotes, and attribution checks now precede chunking. Assistant first person remains assistant attribution. | Exact Alex/Alexa and Priya fixtures fail on base; direct and canonical-write regressions pass. |
| ENG-15 | Shared daemon parser supplied the reference clock. Month/year was also parsed as a partial day, overlapping date patterns manufactured intervals, and source-year checks accepted changed years. Enrichment uses the memory date, rejects invalid anchors, recomputes relative fields on resave, preserves month precision/ranges, and parses overlapping calendar spans once. | `test_wp5_dates`, `test_wp5_enrichment`, `test_a_dated_fact_reaches_the_temporal_layer`. |
| ENG-11 / E-M1 | Fact dedup ignored source context; admission created orphan parents and counts recorded writes as retrieval access. Admission now reuses same content/scope/project/audience/speaker sources atomically, unions tags and preserves conflicting metadata/event dates in history. Fact writes stay source-bound; consolidation filters scope/project/audience, refuses differing values, and does not increment access counts. CCQ uses the same parent-reuse contract. | `test_wp5_dedup` includes concurrent fast saves and relative-date resaves; CCQ write-path and legacy-repair checks pass. |
| E-M4 | A large source was one embedding-worker request. Embedding calls are bounded to 4,000 characters and pooled into one normalized vector; extraction requests are bounded to 6,000 characters and at most five chunks. Full source remains on disk. | Canonical enrichment and warm fast-path request-size regressions fail before and pass after; cold/timeout adapter checks pass. |
| L-19 | gemma4:e2b was installed but uncatalogued; doctor matched family names instead of exact tags; noninteractive setup could silently replace an installed choice. Added explicit local recommendations, excluded cloud tags, kept configured installed choices, and added read-only doctor guidance. | `test_wp5_local_model`, wizard/model catalogue modules. No configuration/model changes made by the benchmark. |
| L-08 | Repeated entity JSON scans and reclassification consumed avoidable work. Enrichment uses the existing entity association index only when coverage is complete, retaining scan fallback and visibility checks. Duplicate type/model review calls are removed. Source comparison still files legitimate older-memory corrections. | Real 26k-fact canonical-pipeline profile below; indexed-query/visibility/correction regressions pass. |
| E-L1 | **Partly disputed:** the existing clamp already said “truncated.” It lacked a concrete pointer. Excerpts now contain the source memory ID and `/api/memories/<id>/detail`; full text is retained and the excerpt is mechanically verified before fidelity checks. | `test_wp5_truncation`; FTS-original and full-source storage checks. |

## 40-note fidelity measurement

Synthetic corpus: first person, direct quotations, two speakers, dates, measurements,
negations, ordered lists and code. Dataset and baseline labels are in
`tests/fixtures/wp5-extraction/`. Labels were reviewed against the source independently
of the production guard: a violation includes unsupported assertions, incorrect
attribution/date/value, or non-statement padding. This is source fidelity, not a claim
that every unsupported world fact is false in the outside world.

Ollama's installed **llama3.2-cpu** alias reports **llama3.2:latest** as its parent.
The plain tag suffered shared-load timeouts; that exploratory run is excluded from
this paired table. No models were pulled/deleted and no owner configuration changed.
Mode C's common guard/dispatch is tested with controlled responses; no cloud was called.

| Mode | False/unsupported extracted facts | Extracted facts/note | Searchable verbatim originals | Persisted facts/note |
|---|---:|---:|---:|---:|
| A before | 3/60 (5.0%) | 1.50 | 37/40 | 1.60 |
| A after | 0/50 (0%) | 1.25 | 40/40 | 1.78 |
| B before | 55/124 (44.4%) | 3.10 | 39/40 | 4.03 |
| B after | 0/54 (0%) | 1.35 | 40/40 | 2.00 |

Retention replays use the real canonical command, storage, consolidation, graph,
lineage and projection paths with deterministic 768-dimensional lexical embeddings.
They replay actual extracted model text without another generation call. The replay
completed all 40 writes in each mode/version. Full parent text stayed 40/40 throughout;
the searchable original fact is what the before versions sometimes removed.
Affected after-notes were rerun following discoveries from the first after run.
The zero rate is this labelled corpus result, not a universal entailment guarantee.

## Timing

Six serial notes, 26,000 seeded facts, 1,000 entities, 768-dimensional controlled
embeddings, actual canonical materialization. Entity-index coverage was complete
in both compared stores. Model inference was excluded from this store profile.

| Metric | Before | After |
|---|---:|---:|
| Enrichment median | 7.44 s | 0.76 s |
| Enrichment range | 6.76–8.92 s | 0.57–0.88 s |
| Embedding calls/note, warm | 14 | 4 |
| Real Ollama extraction median, separate | 23.30 s | 9.96 s |

The first baseline profile attributed 22.6 seconds over six notes to entity lookup
scans. No owner's store was accessed; its reported 31-second latency is not claimed
as a reproduced live measurement. CPU alias extraction timing includes source
chunking/review and shared scheduling; it is distinct from SQLite/graph overhead.

## Validation and boundaries

- Full **encoding module group: 877 passed**. Subsequent focused regressions pass.
- **342 direct importer test modules** were run module-wise: 317 outside encoding,
  25 encoding importers covered by the encoding run. Exact per-module paths and
  batch pass/skip counts are recorded in TMPDIR's importer manifests/logs.
- Ruff is compared against the exact base by path/code/message; no new diagnostics.
- Import architecture: **9 contracts kept, 0 broken**. Internal-leak guard: clean.
- GitNexus impact checks and change detection were run. Its caller extraction was
  incomplete for known Python call paths; direct caller inspection and importer
  tests provide the stronger scope evidence. Database initialization was HIGH risk.
- No files changed in the excluded entity, learning, compliance, vector-store,
  entity-channel, graph-cache or sufficiency areas. No live SLM store or live ports.
- A targeted pytest briefly overlapped the importer runner; it was stopped and
  remaining tests ran serially. Other engineers' processes were not stopped.
- New implementation modules are below 800 lines and functions below 50. The
  pre-existing oversized CLI, engine, ingestion, pipeline and database modules
  retain small integration changes; a wholesale split was not included. The
  optional size-scope question received no answer. This remains a strict size-gate
  exception, not an assertion that every legacy file/function meets the cap.
- Existing corrupted owner-store rows/backlog were not repaired because live-store
  access is expressly prohibited. New writes are guarded; legacy repair tests pass.

## Reproduction

`uv run --frozen env PYTHONPATH=src python scripts/benchmarks/wp5-fidelity.py --model llama3.2-cpu --output "$TMPDIR/fidelity.jsonl"`

The runner never opens an SLM store or daemon, uses installed local models serially,
and requires its artifact path under TMPDIR. Use an isolated base checkout via
PYTHONPATH for the before run. Store-profile/replay scripts, pstats, raw outputs,
label manifests and `WP-5-NOTES.md` are retained in the task's TMPDIR.
