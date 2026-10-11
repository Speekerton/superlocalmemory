# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory | https://qualixar.com

"""The daemon's recall, after the request has been read and authorised.

Extracted from the ``GET /recall`` handler in ``server/unified_daemon.py``
(4.1.21) so that a saved view runs exactly the recall ``/recall`` runs — the
same thread-pool call, the same full-recall semaphore, the same budget and
keyword fallback when the budget is exceeded, the same serializer and the same
envelope. Two copies of this would drift; one is what makes "a view gives the
same answer as the question it stands for" true by construction.

What stays in the handler: reading and validating query parameters, the
permission check, the unknown-profile 404, the session id and the actor. What
lives here is everything from "the request is good" to "the response body".

``origin`` tags the recall for the Answer Check history (who asked:
a dashboard test, or a saved view run from the dashboard, the CLI or an agent).
It is entered on the executor thread, because a context variable set on the
event loop does not cross ``run_in_executor``.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("superlocalmemory.server.recall_core")

# v3.4.53: Limit concurrent full (non-fast) recalls. Without this, N parallel
# full recalls spawn N threads → Ollama serialises, the reranker lock queues,
# and total wall time is N × one recall. Three gives parallelism without
# oversaturation. Shared by every caller of :func:`run_recall`.
RECALL_SEMAPHORE = asyncio.Semaphore(3)


def recall_budget_s() -> float:
    """The public three-second ceiling; an environment override may only shorten it."""
    from superlocalmemory.retrieval.answer_check_status import RECALL_CEILING_S

    try:
        value = float(os.environ.get("SLM_SEARCH_RECALL_TIMEOUT_S", ""))
        return min(value, RECALL_CEILING_S) if value > 0 else RECALL_CEILING_S
    except (TypeError, ValueError):
        return RECALL_CEILING_S


#: A call budget is never allowed below this: the keyword fallback still has to run.
RECALL_BUDGET_FLOOR_S = 2.0


def parse_budget_s(raw: Any) -> float | None:
    """A caller's recall budget in seconds, or ``None`` when absent or unusable.

    Only a finite number above zero counts; anything else is ignored so a
    malformed value can never turn into an error or an unbounded wait.
    """
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0 else None


def sanitize_json_text(text: str) -> str:
    """Strip control characters that break JSON serialization.

    Facts ingested from agent conversations can contain raw control characters
    that survive database round-trips but fail JSON encoding of the response.
    They are replaced with spaces so the byte length is preserved and
    truncation stays predictable. Only the ASCII control range is touched.
    """
    if not text:
        return text
    if all(c >= " " or c in "\n\r\t" for c in text):
        return text
    return "".join(c if c >= " " or c in "\n\r\t" else " " for c in text)


@dataclass(frozen=True, slots=True)
class RecallCall:
    """One recall, fully resolved: every value already validated and normalised."""

    query: str
    limit: int
    session_id: str
    agent_id: str
    fast: bool
    profile_id: str = ""
    include_global: bool | None = None
    include_shared: bool | None = None
    window: str = ""
    as_of: str = ""
    known_as_of: str = ""
    valid_at: str = ""
    include_unknown: bool = False
    facets: Any = None
    skip_answer_check: bool = False
    no_reorder: bool = False
    full: bool = False
    include_source: bool = False
    include_marker: bool = False
    origin: str = ""
    #: A per-call budget in seconds. It can only SHORTEN ``recall_budget_s()``
    #: (see :func:`effective_budget_s`); ``None`` leaves the default untouched.
    budget_s: float | None = None
    #: How a remote caller came in (see ``retrieval/remote_view``); ``""`` is a local caller.
    caller_view: str = ""
    trace: bool = False


def effective_budget_s(call: RecallCall) -> float:
    """The seconds this call may wait before the keyword fallback is served.

    The call's own budget (a relayed call must answer before its relay gives
    up) can only shorten the default, and never below the floor the fallback
    query needs. Without one this is exactly ``recall_budget_s()``.
    """
    default = recall_budget_s()
    if call.budget_s is None:
        return default
    return min(default, max(call.budget_s, RECALL_BUDGET_FLOOR_S))


def _visibility_for(engine: Any, call: RecallCall) -> Any:
    """The caller's visibility context; local callers use the engine's scope."""
    if not call.caller_view:
        return nullcontext()
    from superlocalmemory.retrieval import remote_view, visibility

    ctx = remote_view.context_for(
        call.caller_view, engine._db, call.profile_id or engine.profile_id
    )
    return visibility.use(ctx) if ctx is not None else nullcontext()


def _engine_call(engine: Any, call: RecallCall) -> Any:
    """``engine.recall`` with the call's arguments, on the executor thread."""
    from superlocalmemory.core import answer_check_history as history
    from superlocalmemory.core.answer_check_scope import skip_answer_check

    with (
        skip_answer_check() if call.skip_answer_check else nullcontext(),
        history.origin(call.origin) if call.origin else nullcontext(),
        _visibility_for(engine, call),
    ):
        return engine.recall(
            call.query,
            limit=call.limit,
            session_id=call.session_id,
            agent_id=call.agent_id,
            fast=call.fast,
            profile_id=call.profile_id or None,
            include_global=call.include_global,
            include_shared=call.include_shared,
            window=call.window or None,
            as_of=call.as_of or None,
            known_as_of=call.known_as_of or None,
            valid_at=call.valid_at or None,
            include_unknown=call.include_unknown,
            # Only when given: an engine stand-in need not know these.
            **({"facets": call.facets} if call.facets is not None else {}),
            **({"answer_check": "no_reorder"} if call.no_reorder else {}),
        )


def _envelope(engine: Any, call: RecallCall, response: Any, snapshot: Any) -> dict:
    if call.trace:
        from superlocalmemory.server.routes.recall_trace import envelope
        return envelope(engine, call, response)
    from superlocalmemory.server.recall_serializer import (
        recall_response_metadata,
        serialize_recall_response,
    )

    memory_ids = list(
        {r.fact.memory_id for r in response.results[: call.limit] if r.fact.memory_id}
    )
    memory_map = (
        engine._db.get_memory_content_batch(
            memory_ids,
            call.profile_id or engine.profile_id,
            include_global=True,
            include_shared=True,
        )
        if memory_ids
        else {}
    )
    retrieval = getattr(engine._config, "retrieval", None)
    from superlocalmemory.core.kind_query import engine_display_min_confidence
    from superlocalmemory.retrieval.media_channel import memory_sources

    results, no_confident_match = serialize_recall_response(
        response,
        limit=call.limit,
        memory_map={k: sanitize_json_text(v) for k, v in memory_map.items()},
        source_map=memory_sources(engine._db, memory_ids),
        per_fact_max=getattr(retrieval, "recall_per_fact_max_chars", 2400),
        total_max=getattr(retrieval, "recall_total_max_chars", 12000),
        # Markers only on session-bearing recalls: a marker can only buy a
        # learning signal when a pending outcome exists to settle.
        include_marker=call.include_marker,
        full=call.full,
        include_source=call.include_source,
        # One kind threshold for the filter and the labels on every surface.
        display_min_confidence=engine_display_min_confidence(engine),
    )
    for item in results:
        item["content"] = sanitize_json_text(item.get("content", ""))
    return {
        "ok": True,
        # The profile that actually served this recall: the routed profile when
        # one was named, else the active one. profile_generation describes the
        # global switch state, which per-request routing never moves.
        "profile": call.profile_id or snapshot.profile_id,
        "profile_generation": snapshot.generation,
        "query": call.query,
        "query_type": response.query_type,
        "result_count": len(results),
        "retrieval_time_ms": round(response.retrieval_time_ms, 1),
        "channel_weights": {k: round(v, 3) for k, v in (response.channel_weights or {}).items()},
        "total_candidates": getattr(response, "total_candidates", 0),
        "results": results,
        "count": len(results),
        "no_confident_match": no_confident_match,
        **recall_response_metadata(response),
    }


async def run_recall(engine: Any, call: RecallCall, *, app_state: Any) -> dict:
    """One deadline covers queue admission, worker execution and response assembly."""
    from superlocalmemory.server.profile_runtime import get_profile_runtime
    from superlocalmemory.server.recall_admission import foreground_admission
    from superlocalmemory.server.recall_deadline import timed_out

    budget = effective_budget_s(call)
    from superlocalmemory.server.recall_ingress import remaining_deadline
    public_deadline = remaining_deadline(budget)
    worker_deadline = public_deadline - min(0.20, budget * 0.25)
    runtime = get_profile_runtime(app_state)
    snapshot = runtime.snapshot
    async with foreground_admission(runtime, worker_deadline) as admitted:
        if not admitted:
            return timed_out(call, snapshot)
        snapshot = runtime.snapshot
        return await _run_admitted(
            engine, call, app_state, runtime, snapshot, public_deadline, worker_deadline)


async def _run_admitted(engine, call, app_state, runtime, snapshot,
                        public_deadline, worker_deadline):
    from superlocalmemory.core.recall_gate import RecallHold
    from superlocalmemory.server.recall_deadline import submit, wait_until

    loop = asyncio.get_running_loop()
    hold, acquired = RecallHold(), False
    try:
        if not call.fast:
            try:
                await asyncio.wait_for(RECALL_SEMAPHORE.acquire(),
                                       max(0, worker_deadline - loop.time()))
                acquired = True
            except asyncio.TimeoutError:
                return await _bounded_fallback(
                    engine, call, app_state, public_deadline, snapshot, hold, runtime)
        future = submit(loop, hold, runtime, app_state, engine, _engine_call, engine, call)
        response = await wait_until(future, worker_deadline)
        if response is None:
            logger.warning("Recall deadline reached; trying unjudged keyword fallback")
            return await _bounded_fallback(
                    engine, call, app_state, public_deadline, snapshot, hold, runtime)
        minimal = _minimal_envelope(call, response, snapshot)
        envelope = submit(loop, hold, runtime, app_state, engine, _envelope,
                          engine, call, response, snapshot)
        assembled = await wait_until(envelope, public_deadline)
        from superlocalmemory.server.recall_deadline import unjudged
        return assembled if assembled is not None else unjudged(minimal)
    finally:
        if acquired:
            RECALL_SEMAPHORE.release()
        hold.leave()


def _minimal_envelope(call, response, snapshot):
    """Keep already-retrieved facts without any source hydration/database access."""
    results = [
        {"fact_id": result.fact.fact_id, "memory_id": result.fact.memory_id,
         "content": sanitize_json_text(result.fact.content[:2400]), "score": result.score}
        for result in (getattr(response, "results", ()) or ())[:call.limit]
    ]
    return {
        "ok": True, "query": call.query, "profile": call.profile_id or snapshot.profile_id,
        "profile_generation": snapshot.generation,
        "results": results, "count": len(results), "result_count": len(results),
        "channel_status": dict(getattr(response, "channel_status", {}) or {}),
        "retrieval_mode": "partial_context",
        "degraded_reason": "recall_assembly_budget_exceeded",
    }


async def _bounded_fallback(engine, call, app_state, deadline, snapshot, hold, runtime):
    from superlocalmemory.server.recall_deadline import submit, timed_out, unjudged, wait_until

    future = submit(asyncio.get_running_loop(), hold, runtime, app_state, engine,
                    _fallback, engine, call, app_state)
    result = await wait_until(future, deadline)
    return unjudged(result) if result is not None else timed_out(call, snapshot)


def _fallback(engine: Any, call: RecallCall, app_state: Any) -> dict:
    from superlocalmemory.server.profile_runtime import get_profile_runtime
    from superlocalmemory.server.recall_fallback import recall_keyword_fallback

    snapshot = get_profile_runtime(app_state).snapshot
    with _visibility_for(engine, call):
        return recall_keyword_fallback(
            engine,
            call.query,
            call.limit,
            profile_id=call.profile_id or None,
            profile=call.profile_id or snapshot.profile_id,
            profile_generation=snapshot.generation,
            facets=call.facets,
        )


__all__ = [
    "RECALL_BUDGET_FLOOR_S",
    "RECALL_SEMAPHORE",
    "RecallCall",
    "effective_budget_s",
    "parse_budget_s",
    "recall_budget_s",
    "run_recall",
    "sanitize_json_text",
]
