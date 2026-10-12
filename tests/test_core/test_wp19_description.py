"""Canonical description works for preserved sources and local models."""

from types import SimpleNamespace
from unittest.mock import Mock

from superlocalmemory.core.enriched_fact import enrich
from superlocalmemory.core.kind_assignment import assign_kinds
from superlocalmemory.encoding.temporal_parser import TemporalParser
from superlocalmemory.storage.models import AtomicFact, MemoryRecord


def test_missing_entities_are_extracted_without_accepting_junk():
    text = 'Dr. Iyer uses PostgreSQL for the Zephyr project. PASS /api/v3/check 1234abcd.'
    resolver = Mock()
    resolver.resolve.side_effect = lambda names, profile: {n: 'entity-' + n for n in names}
    fact = enrich(AtomicFact(content=text), MemoryRecord(content=text), 'default',
                  embedder=None, entity_resolver=resolver, temporal_parser=TemporalParser(),
                  init_position=lambda **kw: [])
    assert 'PostgreSQL' in fact.entities
    assert 'Zephyr' in fact.entities
    assert fact.canonical_entities
    assert not any(n in fact.entities for n in ('PASS', '1234abcd', '/api/v3/check'))
    assert fact.observation_date


def test_prebuilt_caller_kind_survives_description_without_metadata():
    fact = AtomicFact(content='Zephyr is our project.', memory_kind='fact',
                      memory_kind_source='caller')
    db = SimpleNamespace(has_memory_kind_columns=lambda: True)
    described = assign_kinds([fact], metadata={}, source_type='python-api-prebuilt',
                             classifier=None, db=db)[0]
    assert described.memory_kind_source == 'caller'
    assert described.memory_kind == 'fact'


def test_local_kind_classifier_uses_a_bounded_local_call():
    from superlocalmemory.encoding.local_description_kinds import LocalDescriptionKinds
    llm = SimpleNamespace(provider='ollama', _ollama_host='http://localhost:11434', model='local')
    request = Mock(return_value={'kind': 'fact'})
    classifier = LocalDescriptionKinds(delegate=None, llm_supplier=lambda: llm, request=request)
    result = classifier.suggest([AtomicFact(content='Zephyr uses PostgreSQL.')], caller_kind=None)
    assert result[0].source.value == 'model:llm'
    assert request.call_args.kwargs['timeout'] <= 1.0


def test_hosted_kind_classifier_never_receives_memory_text():
    from superlocalmemory.encoding.local_description_kinds import LocalDescriptionKinds
    llm = SimpleNamespace(provider='ollama', _ollama_host='https://example.com', model='hosted')
    request = Mock()
    classifier = LocalDescriptionKinds(delegate=None, llm_supplier=lambda: llm, request=request)
    result = classifier.suggest([AtomicFact(content='Zephyr uses PostgreSQL.')], caller_kind=None)
    assert result[0].source.value == 'rules'
    request.assert_not_called()
