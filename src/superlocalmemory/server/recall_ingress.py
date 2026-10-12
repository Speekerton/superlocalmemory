# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""One absolute clock from HTTP ingress through middleware and serialization."""
import asyncio
from contextvars import ContextVar

_DEADLINE = ContextVar("slm_http_recall_deadline", default=None)
_RECALL_PATHS = frozenset({"/recall", "/api/v3/recall/trace", "/api/v3/views/run"})


def is_recall(scope):
    return scope.get("type") == "http" and scope.get("path", "").rstrip("/") in _RECALL_PATHS


def remaining_deadline(budget):
    deadline = asyncio.get_running_loop().time() + budget
    ingress = _DEADLINE.get()
    return min(deadline, ingress - 0.01) if ingress is not None else deadline


def fallback_deadline(public_deadline, floor_s):
    """When the keyword fallback must answer by: the public deadline, or later
    when that came sooner than the fallback's floor (a shortened budget), yet
    never past the HTTP request's own clock."""
    floor = asyncio.get_running_loop().time() + floor_s
    ingress = _DEADLINE.get()
    if ingress is not None:
        floor = min(floor, ingress - 0.01)
    return max(public_deadline, floor)


async def serve(app, state, scope, receive, send):
    from starlette.responses import JSONResponse

    from superlocalmemory.server.recall_core import RECALL_BUDGET_FLOOR_S, recall_budget_s

    # A budget shortened below the floor gives up on full recall sooner; the
    # keyword fallback that answers then still needs the floor (recall_core).
    deadline = remaining_deadline(max(recall_budget_s(), RECALL_BUDGET_FLOOR_S))
    token = _DEADLINE.set(deadline)
    messages = []

    async def buffered_send(message):
        messages.append(message)

    try:
        await asyncio.wait_for(app(scope, receive, buffered_send),
                               max(0, deadline - asyncio.get_running_loop().time()))
    except asyncio.TimeoutError:
        # Admission never completed: do not reveal a profile or touch its store.
        response = JSONResponse({
            "ok": False, "results": [], "count": 0, "result_count": 0,
            "degraded_reason": "recall_budget_exceeded", "answerability": "unjudged",
            "answer_check_status": "skipped", "answer_check_detail": "budget",
            "answer_check_note": ("Recall timed out before full results were available; "
                                  "it was not checked."),
        }, status_code=503)
        await response(scope, receive, send)
    else:
        for message in messages:
            await send(message)
    finally:
        _DEADLINE.reset(token)
