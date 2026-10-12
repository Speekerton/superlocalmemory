# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Power-user control of the default automatic background improvements."""

from __future__ import annotations

import argparse
import json

from superlocalmemory.cli.daemon import daemon_request


def register_enrich_parser(sub):
    parser = sub.add_parser('enrich', help='Automatic memory improvements: status, pause, resume, undo')
    actions = parser.add_subparsers(dest='enrich_action', required=True)
    for action in ('status', 'pause', 'resume', 'undo'):
        command = actions.add_parser(action)
        if action != 'status':
            command.add_argument('run_id')
        command.add_argument('--json', action='store_true', default=argparse.SUPPRESS)


def cmd_enrich(args):
    action = args.enrich_action
    result = (daemon_request('GET', '/api/memory-health') if action == 'status' else
              daemon_request('POST', '/api/memory-health/action',
                             {'action': action, 'run_id': args.run_id}, preserve_conflict=True))
    if not isinstance(result, dict):
        raise RuntimeError('Your memory service did not answer.')
    if getattr(args, 'json', False):
        print(json.dumps(result))
    elif action == 'status':
        run = result['enrichment']
        print(result['summary'])
        print(f"Status: {run['status']}")
        if run.get('last_error'):
            print(f"Waiting after: {run['last_error']}")
    else:
        print(json.dumps(result))
