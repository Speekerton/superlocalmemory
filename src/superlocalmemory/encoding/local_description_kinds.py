# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Bounded on-device kind suggestions; memory text never reaches a hosted URL."""

from __future__ import annotations

import ipaddress
import json
import logging
import time
from urllib.parse import urlsplit

from superlocalmemory.storage.memory_kinds import KindAssignment, KindSource, parse_kind

logger = logging.getLogger(__name__)
MODEL_BUDGET_SECONDS = 0.8


def loopback_host(host: str) -> bool:
    parsed = urlsplit(host)
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        return False
    if parsed.hostname == 'localhost':
        return True
    try:
        return ipaddress.ip_address(parsed.hostname or '').is_loopback
    except ValueError:
        return False


def _ollama_request(host, model, content, *, timeout):
    from superlocalmemory.core.background_process import run_in_child

    return run_in_child(_post, host, model, content, timeout, timeout=timeout)


def _post(host, model, content, timeout):
    import httpx

    from superlocalmemory.storage.memory_kinds import MemoryKind

    if not loopback_host(host):
        raise ValueError('kind classification requires an on-device model')
    choices = ', '.join(k.value for k in MemoryKind)
    payload = {'model': model, 'stream': False, 'format': 'json', 'think': False,
               'keep_alive': '5m', 'options': {'num_predict': 30, 'num_ctx': 2048},
               'messages': [{'role': 'system', 'content':
                             'Classify the memory. Return only {"kind": "choice"}. '
                             'Choices: ' + choices},
                            {'role': 'user', 'content': content[:4000]}]}
    with httpx.Client(timeout=timeout, trust_env=False, follow_redirects=False) as client:
        response = client.post(host.rstrip('/') + '/api/chat', json=payload)
        response.raise_for_status()
        return json.loads(response.json()['message']['content'])


class LocalDescriptionKinds:
    """Reuse existing suggestions; fill rules-only kinds from local Ollama."""

    def __init__(self, *, delegate, llm_supplier, request=None):
        self.delegate = delegate
        self.llm_supplier = llm_supplier
        self.request = request or _ollama_request

    def suggest(self, facts, *, caller_kind):
        from superlocalmemory.encoding.memory_kind_classifier import _rules_for

        if caller_kind is not None:
            return [KindAssignment(caller_kind, KindSource.CALLER, None, 'caller')] * len(facts)
        out = (self.delegate.suggest(facts, caller_kind=None) if self.delegate
               else [_rules_for(f) for f in facts])
        llm = self.llm_supplier()
        if getattr(llm, 'provider', None) != 'ollama':
            return out
        host = getattr(llm, '_ollama_host', '')
        if not loopback_host(host):
            return out
        deadline = time.monotonic() + MODEL_BUDGET_SECONDS
        for i, fact in enumerate(facts[:8]):
            if out[i] is None or out[i].source.value != 'rules':
                continue
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                raw = self.request(host, llm.model, fact.content, timeout=remaining)
                kind = parse_kind(raw.get('kind'))
                if kind is not None:
                    from superlocalmemory.encoding.memory_kind_classifier import decide
                    from superlocalmemory.encoding.memory_kind_rules import cue_kind

                    model = KindAssignment(kind, KindSource.MODEL_LLM, None, 'local-kind-v1')
                    out[i] = decide(model, out[i], cue_kind(fact.content)) or out[i]
            except Exception as exc:  # best-effort description must never fail a save
                logger.debug('Local memory description deferred (%s)', type(exc).__name__)
                break
        return out
