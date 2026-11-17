"""Only isolated ledgers under the test slot, never the shared ledger."""
import datetime as d
import json
from pathlib import Path
import sys
slot = Path(sys.argv[1]).resolve()
if sys.argv[2] == 'check':
    active = set()
    rows = [json.loads(line) for line in (slot/'jobs.jsonl').read_text().splitlines()]
    for r in rows:
        if r.get('project') != 'knc-boinc':
            continue
        assert r['agent'] == 'claude' and r['cores'] == [] and r['timingValid'] is True
        assert r['jobId'].startswith('claude-turn-knc-boinc-')
        if r['event'] == 'queued':
            assert d.datetime.fromisoformat(r['queuedTime']).tzinfo is not None
            active.add(r['jobId'])
        else:
            assert r['event'] in ('finish', 'superseded')
            assert d.datetime.fromisoformat(r['endTime']).tzinfo is not None
            active.discard(r['jobId'])
    assert not active, active
    print('PASS wrapper booking row shape and all task turns closed')
    sys.exit(0)
now = d.datetime.now(d.timezone.utc)
row = dict(agent='other', project='gcc-knc', cores=[], timingValid=True,
           purpose='isolated wrapper test')
rows = [dict(row, jobId='expired', event='queued', queuedTime=(now-d.timedelta(hours=4)).isoformat()),
        dict(row, jobId='closed', event='queued', queuedTime=(now-d.timedelta(minutes=5)).isoformat()),
        dict(row, jobId='closed', event='finish'),
        dict(row, jobId='future', event='queued', queuedTime=(now+d.timedelta(hours=1)).isoformat()),
        dict(row, jobId='invalid', event='queued', timingValid=False, queuedTime=now.isoformat())]
if sys.argv[2] == 'booking-requeue':
    job = 'claude-turn-knc-boinc-20000101T000000000000Z'
    old = (now-d.timedelta(hours=4)).isoformat()
    rows.append(dict(row, agent='claude', project='knc-boinc', jobId=job,
                     event='queued', queuedTime=old))
    (slot/'knc_turn').write_text(job+'\n')
else:
    rows.extend([dict(row, jobId='foreign-queue', event='queued', queuedTime=(now-d.timedelta(minutes=1)).isoformat()),
                 dict(row, jobId='foreign-running-' + chr(955), event='start')])
(slot/'jobs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
(slot/'dma-stop').touch()
cfg = slot/'knc_wrapper.cfg'
cfg.write_text(cfg.read_text().replace('card_booking=0', 'card_booking=1') +
               'booking_ledger='+(slot/'jobs.jsonl').as_posix()+chr(10)+
               'dma_stop_latch='+(slot/'dma-stop').as_posix()+chr(10)+
               'booking_suspend_timeout=1'+chr(10))
