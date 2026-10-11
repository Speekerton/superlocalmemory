# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""Bound executor joins, including database-backed serialization and fallback."""

import asyncio


async def wait_until(future, deadline):
    try:
        return await asyncio.wait_for(
            asyncio.shield(future), max(0, deadline - asyncio.get_running_loop().time())
        )
    except asyncio.TimeoutError:
        future.add_done_callback(lambda f: f.cancelled() or f.exception())
        return None


def unjudged(payload):
    from superlocalmemory.retrieval.answer_check_status import answer_check_note

    return {
        **payload,
        "answerability": "unjudged",
        "answer_check_status": "skipped",
        "answer_check_detail": "budget",
        "answer_check_note": answer_check_note("skipped", "budget"),
        "no_confident_match": False,
    }


def timed_out(call, snapshot):
    from superlocalmemory.server.recall_fallback import abandoned_channel_metadata

    return unjudged(
        {
            "ok": True,
            "query": call.query,
            "query_type": "text_search",
            "profile": call.profile_id or snapshot.profile_id,
            "profile_generation": snapshot.generation,
            "results": [],
            "result_count": 0,
            "count": 0,
            "retrieval_mode": "degraded_lexical",
            "degraded_reason": "recall_budget_exceeded",
            **abandoned_channel_metadata(),
        }
    )


def submit(loop, hold, runtime, state, engine, fn, *args):
    from contextlib import nullcontext

    def guarded():
        lease = getattr(runtime, "operation_nowait", None)
        with lease() if lease else nullcontext(True) as admitted:
            if admitted is None or getattr(state, "engine", engine) is not engine:
                return None
            return fn(*args)

    return loop.run_in_executor(None, hold.run, guarded)
