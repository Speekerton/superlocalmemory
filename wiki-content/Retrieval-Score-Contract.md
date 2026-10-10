# Retrieval Score Contract

Every recall result carries several numbers, and they answer different questions. This page defines each field, explains why none of them is an answer probability, and lists the extra fields a recall response uses to say whether the answer check ran and whether SLM abstained. The contract is on version 2 (`score_contract_version` is `"2"`). If you build a client, read the explicit field names and ignore the legacy aliases. This page matches `docs/retrieval-score-contract.md` and the code.

## Result fields

Retrieval ordering is not answer confidence. A retrieval score answers "how relevant is this stored fact to this query?" It does not answer "how likely is a generated answer to be correct?"

| Field | Meaning | How to read it |
|---|---|---|
| `relevance_score` | Query-relative relevance after the configured retrieval and scoring pipeline | Bounded to 0.0 to 1.0; compare only within a compatible release and retrieval configuration |
| `ranking_score` | Internal ranking utility after optional adaptive or reranking adjustments | Diagnostic only; not a probability, and not guaranteed to be bounded or comparable across configurations |
| `memory_confidence` | Confidence stored with the underlying assertion | Memory metadata; it is neither query relevance nor answer correctness |
| `trust_score` | Trust signal attached to the stored evidence | An evidence-policy signal, not answer confidence |
| `rank_position` | One-based position in the returned list | The observable order after ranking |

For one compatibility release the legacy field `score` aliases `relevance_score` and the legacy field `confidence` aliases `memory_confidence`. The code sets both pairs to the same value when it finalises a response (`core/score_contract.py`). New integrations should use the explicit names.

## Response fields

Every canonical recall response declares the contract version and the state of the answer check. With nothing configured, the defaults look like this:

```json
{
  "score_contract_version": "2",
  "calibration_status": "uncalibrated",
  "calibration_id": null,
  "answer_confidence": null,
  "abstained": false,
  "abstention_reason": null,
  "answer_check_status": "off",
  "reranker_status": "not_configured",
  "local_reranker_status": ""
}
```

By default nothing judges whether the results answer the question, so `calibration_status` is `uncalibrated`, `calibration_id` is `null` and `answer_confidence` is `null`. Do not derive an answer probability by doubling, thresholding, averaging or otherwise transforming retrieval scores. Measured on a real store, the ranking score was the same for right answers, wrong answers and questions with no answer in memory, which is why the contract refuses to read it as confidence (comment in `core/score_contract.py`).

### Answer check status

`answer_check_status` says what became of the [Answer Check](Answer-Check) on this one recall. The six values below are the closed set in the code (`retrieval/answer_check_status.py`).

| Value | Meaning |
|---|---|
| `judged` | A verdict was applied to this recall |
| `off` | The check is not turned on, so no check runs |
| `skipped` | The check is on but was not asked: context loading, a system recall, no results, too little of the recall's time budget left, or the online option would have had to read another profile's memory |
| `busy` | The on-device check was already answering another recall |
| `warming` | The on-device check is still loading its model |
| `unavailable` | The check timed out, errored, has no key, or cannot run on this machine |

Skipping costs the verdict only. The memories, their order and their scores are the same either way. A verdict that is missing because the check was busy or warming is not the same as "nothing answers", which is why the status travels with the answer.

Alongside it, the response carries `answer_check_ran` (true only when the status is `judged`), `answer_check_reason` (a closed-set reason, or `reused` when an identical earlier check is repeated), and `answer_check_note`, a plain sentence for a person, empty when there is nothing to explain. Two further fields, `answerability` and `answerability_reason`, report supported, unsupported or unjudged and why; `abstained: false` never means "checked", and these fields do.

`reranker_status` names whichever step produced the final order. The value `jev_listwise` means the online answer check's optional reorder replaced what the local reranker had produced, and `local_reranker_status` then keeps the local status for that recall; it is empty when nothing replaced it.

### Abstention

When no result survives the evidence floor, `abstained` is `true` and `abstention_reason` is `evidence_floor`. When candidate generation returns nothing, the reason is `no_candidates`. Neither case involves judging results; there were none to judge. The code picks between the two by whether the response recorded a no-confident-match condition.

| `abstention_reason` | When |
|---|---|
| `evidence_floor` | Results were found but none cleared the evidence floor |
| `no_candidates` | Candidate generation returned nothing |
| `judged_insufficient` | The answer check ran, results were found and are still returned, and none were judged to answer the question |
| `null` | Not abstaining |

## Answer check

When the [Answer Check](Answer-Check) is turned on (off until an on-device install has passed its own check), a separate decision runs on the top results. It asks not "is this relevant" but "does this answer the question". Its verdict fills `calibration_status`, `calibration_id` and `answer_confidence` with real values instead of the uncalibrated defaults, and may set `abstention_reason` to `judged_insufficient`. `calibration_status` distinguishes a measured calibration from one that has not yet been measured for the current backend and settings, so treat an unmeasured verdict as a signal, not a guarantee. Results are never removed because of this verdict; it is reported next to them, and a caller that ignores it sees what it saw before.

The daemon's `GET /recall` accepts an `answer_check` query parameter with three values: `full` (the default, the complete check with the optional reorder when that is on), `no_reorder` (the verdict only, never the reorder, which is what the bounded-loop gate asks for) and `skip` (no check, for a recall that is not a question, such as context loading or a health probe). Any other value is refused with HTTP 400.

## How the ranking is built

The engine runs five candidate producers when their dependencies are healthy: dense semantic, BM25 lexical, temporal, Hopfield associative and spreading activation. Weighted reciprocal-rank fusion combines their output. Entity-graph information can raise a score after fusion, but it does not create a candidate of its own. Optional reranking and adaptive learning can change `ranking_score`; they do not turn it into a probability. A missing optional dependency can change the active channel set, so an application that needs a fixed retrieval topology should check health and trace metadata at startup. The channels that contributed to a result, and any channel abandoned at the hang guard (`incomplete_channels`), are in `channel_status` and in `slm trace`. See [How Recall Works](How-Recall-Works).

## Calibration release gate

Calibrated confidence needs a frozen release candidate, held-out relevance labels, a declared corpus and query distribution, a calibration identity, and reported calibration and selective-risk metrics. Until that evidence exists, the honest contract stays uncalibrated with `answer_confidence: null`. Runtime fields are not benchmark accuracy; the published LoCoMo figures and their protocols are on [Research Foundations](Research-Foundations).

Code: `core/score_contract.py` (`finalize_score_contract`), `server/recall_serializer.py`, `retrieval/answer_check_status.py`, `core/answer_check_stage.py`, `retrieval/answerability.py`, `mcp/_recall_metadata.py`; full developer contract in `docs/retrieval-score-contract.md`.
