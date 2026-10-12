"""The power-user CLI uses the same actions as Memory health."""

from argparse import ArgumentParser, Namespace
from unittest.mock import Mock

import pytest

from superlocalmemory.cli.enrich_cmd import cmd_enrich, register_enrich_parser


@pytest.mark.parametrize('action', ['pause', 'resume', 'undo'])
def test_enrich_parser_and_actions(monkeypatch, action):
    parser = ArgumentParser()
    register_enrich_parser(parser.add_subparsers(dest='command'))
    args = parser.parse_args(['enrich', action, 'synthetic-run', '--json'])
    request = Mock(return_value={'status': action})
    monkeypatch.setattr('superlocalmemory.cli.enrich_cmd.daemon_request', request)
    cmd_enrich(args)
    request.assert_called_once_with(
        'POST', '/api/memory-health/action',
        {'action': action, 'run_id': 'synthetic-run'}, preserve_conflict=True)


def test_enrich_status_is_plain_language(monkeypatch, capsys):
    monkeypatch.setattr('superlocalmemory.cli.enrich_cmd.daemon_request',
                        lambda *a: {'summary': 'Improving your memories: 3 of 12',
                                    'enrichment': {'status': 'running'}})
    cmd_enrich(Namespace(enrich_action='status', json=False))
    assert 'Improving your memories: 3 of 12' in capsys.readouterr().out
