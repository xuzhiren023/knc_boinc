#!/usr/bin/env python3
"""Lead-only turn ledger lifecycle; see CARD_RUN.md. Dry runs never append."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

LEDGER = Path('C:/Users/xuzhi/Documents/card-coordination/jobs.jsonl')
PROJECT = 'knc-boinc'
PREFIX = 'claude-turn-knc-boinc-'


def rows_for(args):
    now = datetime.now(timezone.utc)
    if args.action == 'queue':
        purpose = args.purpose
    else:
        active = None
        # Include expired queues: they still need closing or explicit renewal.
        for line in args.ledger.read_text(encoding='utf8').splitlines():
            row = json.loads(line)
            if row.get('jobId') == args.job_id:
                active = row if row.get('event') == 'queued' else None
        if (active is None or active.get('project') != PROJECT
                or not args.job_id.startswith(PREFIX) or active.get('cores') != []
                or active.get('timingValid') is not True):
            raise ValueError('jobId must identify an unclosed knc-boinc turn queue')
        purpose = active['purpose']
    common = dict(agent='claude', project=PROJECT, cores=[], timingValid=True, purpose=purpose)
    rows = []
    if args.action != 'queue':
        rows.append(dict(common, jobId=args.job_id,
                         event='finish' if args.action == 'finish' else 'superseded',
                         endTime=now.isoformat(),
                         outcome=args.outcome if args.action == 'finish' else 'requeued'))
    if args.action != 'finish':
        rows.append(dict(common, event='queued', jobId=PREFIX + now.strftime('%Y%m%dT%H%M%S%fZ'),
                         queuedTime=now.isoformat()))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, default=LEDGER)
    parser.add_argument('--dry-run', action='store_true')
    actions = parser.add_subparsers(dest='action', required=True)
    queue = actions.add_parser('queue')
    queue.add_argument('--purpose', required=True)
    finish = actions.add_parser('finish')
    finish.add_argument('job_id')
    finish.add_argument('--outcome', required=True)
    requeue = actions.add_parser('requeue')
    requeue.add_argument('job_id')
    args = parser.parse_args()
    try:
        rows = rows_for(args)
        data = ''.join(json.dumps(row, sort_keys=True) + '\n' for row in rows)
        if not args.dry_run:
            # Like card_run: append only to an existing ledger, never repair it.
            # Requeue publishes its two rows together in one append syscall.
            fd = os.open(str(args.ledger), os.O_WRONLY | os.O_APPEND)
            try:
                encoded = data.encode('utf8')
                if os.write(fd, encoded) != len(encoded):
                    raise OSError('short ledger append')
            finally:
                os.close(fd)
        print(data, end='')
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('card turn: %s' % error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
