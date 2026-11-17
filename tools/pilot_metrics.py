#!/usr/bin/env python3
"""Regenerate the pilot ledger using only local evidence and the standard library."""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re

MAIN_REPO = Path('C:/Users/xuzhi/Documents/knc-boinc')
LEDGER = Path('C:/Users/xuzhi/Documents/card-coordination/jobs.jsonl')
TICKET = re.compile(r'\bS(\d+)-(\d+)\b', re.I)
STATUSES = ('ok', 'unsupported', 'missing_parameter', 'other')


def ticket_in(value):
    matches = list(TICKET.finditer(str(value)))
    return matches[-1].group().upper() if matches else None


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def timestamp(value):
    if isinstance(value, str):
        try:
            parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            pass
    return None


def load_json(path, warnings):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError, OSError, UnicodeError) as error:
        warnings.append('{}: {}'.format(path, error))
        return None


def json_lines(path, warnings):
    # Codex CLI logs may begin with a non-JSON startup line.
    if not path.exists():
        warnings.append('Missing source: {}'.format(path))
        return
    with path.open(encoding='utf-8-sig', errors='replace') as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except ValueError:
                warnings.append('{}:{}: non-JSON line skipped'.format(path, line_number))
                continue
            if isinstance(value, dict):
                yield value


def files_under(base):
    for directory, children, files in os.walk(str(base)):
        children[:] = sorted(c for c in children if c != '.git')
        for name in sorted(files):
            yield Path(directory) / name


def first_number(data, keys):
    for key in keys:
        value = number(data.get(key))
        if value is not None:
            return value
    return None


def score(row):
    result = dict(row)
    predicted, measured = number(row.get('predicted')), number(row.get('measured'))
    baseline = number(row.get('baseline'))
    bounds = row.get('predicted_range')
    ratio_range = None
    if bounds and len(bounds) == 2 and all(number(v) is not None and v > 0 for v in bounds) and measured is not None:
        ratio_range = sorted(measured / v for v in bounds)
    direction = None
    if predicted is not None and measured is not None and baseline is not None:
        sign = lambda n: (n > 0) - (n < 0)
        direction = sign(predicted - baseline) == sign(measured - baseline)
    elif row.get('predicted_winner') is not None and row.get('measured_winner') is not None:
        direction = row['predicted_winner'] == row['measured_winner']
    if row.get('status') == 'unsupported':
        usefulness = 'unsupported'
        direction = None
    elif direction is not None and row.get('method') in ('twin', 'model'):
        usefulness = 'decided' if direction else 'missed'
    else:
        usefulness = 'not-attempted'
    result.update(ratio_range=ratio_range, ratio=(measured / predicted if predicted not in (None, 0) and measured is not None else None),
                  direction_right=direction, usefulness=usefulness)
    # Only explicitly named, off-card-ranked variants count as avoided jobs.
    result['avoided_variants'] = sorted(set(row.get('ranked_variants', [])) -
                                        set(row.get('sent_variants', []))) if 'sent_variants' in row else []
    return result


def aggregate(rows):
    result = {key: sum(r[key] for r in rows) for key in
              ('sessions', 'card_jobs', 'card_minutes', 'sessions_timed', 'twin_host_runs')}
    for key in ('engineer_seconds', 'twin_host_seconds'):
        values = [r[key] for r in rows if r[key] is not None]
        result[key] = sum(values) if values else None
    result['twin_status'] = {s: sum(r['twin_status'][s] for r in rows) for s in STATUSES}
    result['model_tickets'] = sum(r['model_table'] for r in rows)
    return result


def report_outcome(report):
    for paragraph in re.split(r'\n\s*\n', report.strip()):
        if paragraph and not paragraph.lstrip().startswith(('#', '```', '|')):
            text = ' '.join(paragraph.split())
            return text[:177] + '...' if len(text) > 180 else text
    return 'No Engineer report in main checkout'


def collect(repo, ledger, predictions_path):
    warnings = []
    tickets = {}
    for path in sorted((repo / 'work/tickets').glob('S*.md')):
        tid = ticket_in(path.stem)
        if tid is None:
            continue
        try:
            text = path.read_text(encoding='utf-8-sig')
        except UnicodeError:
            text = path.read_text(encoding='cp1252')
            warnings.append('{}: decoded legacy cp1252 ticket'.format(path))
        title = next((line.lstrip('# ').strip() for line in text.splitlines() if line.startswith('# ')), tid)
        depth = re.search(r'Depth:\s*([\w-]+)', text, re.I)
        report = text.split('## Engineer report', 1)[1] if '## Engineer report' in text else ''
        # Instructions are not proof of use. Prefer the completed report, or evidence prose.
        evidence = report or ''
        model = bool(re.search(r'(?:used (?:a )?model table|\|\s*Term\s*\|.*Formula|knc-optimize|model-first)', evidence, re.I))
        if re.search(r'model table\s*(?:was used)?\s*[:=]?\s*(?:no|none|not used)', evidence, re.I):
            model = False
        tickets[tid] = dict(ticket=tid, sprint=int(TICKET.search(tid).group(1)), title=title,
                            depth=depth.group(1) if depth else None, source=str(path.relative_to(repo)),
                            text_evidence={'twin': bool(re.search('knc[-_]twin', evidence, re.I)),
                                           'card': bool(re.search(r'card (?:run|check|window)', evidence, re.I)),
                                           'engineer_report': bool(report)},
                            model_table=model, gcc_knc_variants=bool(re.search(
                                r'(?:GCC-KNC.*variant|variant.*GCC-KNC|\bV[0-9]\b|flags.*build)', evidence, re.I)),
                            sessions=0, sessions_timed=0, engineer_seconds=None, tokens={},
                            twin_status=dict.fromkeys(STATUSES, 0), twin_host_seconds=None,
                            twin_host_runs=0, card_jobs=0, card_minutes=0, card_windows=[],
                            outcome=report_outcome(report))
    sessions = []
    for path in sorted((repo / '.codex-logs').glob('S*-*.jsonl')):
        tid = ticket_in(path.name)
        events = list(json_lines(path, warnings))
        times = [timestamp(e.get('timestamp', e.get('timestamp_utc', e.get('time')))) for e in events]
        times = [t for t in times if t is not None]
        usage = collections.Counter()
        for event in events:
            # Turn usage is incremental in Codex CLI. Nested token_count events carry cumulative
            # totals; use only their final total when no turn.completed usage is available.
            if event.get('type') == 'turn.completed' or 'usage' in event:
                for key, value in event.get('usage', {}).items():
                    if number(value) is not None:
                        usage[key] += value
        if not usage:
            for event in events:
                info = event.get('payload', {}).get('info') or {}
                total = info.get('total_token_usage')
                if isinstance(total, dict):
                    usage = collections.Counter({k: v for k, v in total.items() if number(v) is not None})
        seconds = (times[-1] - times[0]).total_seconds() if len(times) >= 2 else None
        entry = dict(ticket=tid, source=str(path.relative_to(repo)), wall_seconds=seconds,
                     first_event=times[0].isoformat() if times else None,
                     last_event=times[-1].isoformat() if times else None, tokens=dict(usage))
        sessions.append(entry)
        if tid in tickets:
            t = tickets[tid]
            t['sessions'] += 1
            if seconds is not None:
                t['sessions_timed'] += 1
                t['engineer_seconds'] = (t['engineer_seconds'] or 0) + seconds
            t['tokens'] = dict(collections.Counter(t['tokens']) + usage)
    twins, receipts = {}, {}
    candidates = list(files_under(repo / 'twin')) + list(files_under(repo / 'runs'))
    candidates += list(files_under(repo / '.work'))
    for path in candidates:
        rel = path.relative_to(repo).as_posix()
        is_twin = path.name == 'result.json'
        is_card = path.suffix == '.json' and (rel.startswith('runs/') or '/runs/card/' in rel)
        if not (is_twin or is_card):
            continue
        data = load_json(path, warnings)
        if not isinstance(data, dict):
            continue
        if is_card and number(data.get('card_minutes')) is not None:
            key = data.get('job_id', data.get('jobId')) or hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
            if key not in receipts:
                receipts[key] = dict(job_id=key, ticket=ticket_in(rel), card_minutes=data['card_minutes'],
                                     window=data.get('window', data.get('window_id')), sources=[rel],
                                     exit_code=data.get('program_exit_code', data.get('exit_code')))
            else:
                receipts[key]['sources'].append(rel)
                receipts[key]['ticket'] = receipts[key]['ticket'] or ticket_in(rel)
        if is_twin and ('invocation' in data or str(data.get('schema', '')).startswith('knc-twin')):
            # Exact copies retain the original invocation identity.
            key = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
            if key in twins:
                twins[key]['sources'].append(rel)
                continue
            invocation = data.get('invocation') or {}
            artifacts = data.get('artifacts') or {}
            tid = (ticket_in(invocation.get('cwd', '')) or ticket_in(artifacts.get('result_json', '')) or ticket_in(rel))
            prediction = data.get('prediction') or {}
            raw_status = data.get('status')
            status = raw_status if raw_status in STATUSES else 'other'
            twins[key] = dict(ticket=tid, sources=[rel], command=invocation.get('command', data.get('command')),
                              argv=invocation.get('argv'), status=raw_status, status_bucket=status,
                              result_class=data.get('result_class', prediction.get('result_class')),
                              simulated_cycles=first_number(prediction, ('predicted_cycles', 'cycles', 'core_cycles', 'total_cycles')),
                              simulated_instructions=first_number(prediction, ('dynamic_instructions', 'instructions')),
                              host_seconds=first_number(data, ('python_execution_seconds', 'host_seconds', 'elapsed_seconds')),
                              timestamp=data.get('timestamp_utc'))
    # Allocation windows can contain other projects; never charge whole-window minutes.
    ledger_jobs = {}
    ledger_rows = list(json_lines(ledger, warnings))
    relevant_ids = {row.get('jobId', row.get('job_id')) for row in ledger_rows
                    if re.search(r'knc-boinc|milkyway', ' '.join(str(row.get(k, '')) for k in
                                 ('purpose', 'path', 'cwd', 'project', 'run_dir')), re.I)}
    for row in ledger_rows:
        searchable = ' '.join(str(row.get(k, '')) for k in ('purpose', 'path', 'cwd', 'project', 'run_dir'))
        if row.get('jobId', row.get('job_id')) not in relevant_ids:
            continue
        jid = row.get('jobId', row.get('job_id'))
        if jid is None:
            warnings.append('Shared ledger row has no job ID')
            continue
        job = ledger_jobs.setdefault(jid, dict(job_id=jid, ticket=ticket_in(searchable), events=[],
                                               purpose=row.get('purpose'), start=None, end=None, window=None))
        job['events'].append(row.get('event'))
        job['start'] = row.get('startTime', job['start'])
        job['end'] = row.get('endTime', job['end'])
        window = re.search(r'(?:window\s+|[-_]w)(\d+)', searchable + ' ' + jid, re.I)
        job['window'] = row.get('window', int(window.group(1)) if window else job['window'])
        job['ticket'] = job['ticket'] or ticket_in(searchable)
        if number(row.get('card_minutes')) is not None and jid not in receipts:
            receipts[jid] = dict(job_id=jid, ticket=job['ticket'], card_minutes=row['card_minutes'],
                                 window=job['window'], sources=[str(ledger)], exit_code=None)
    for run in twins.values():
        if run['ticket'] in tickets:
            t = tickets[run['ticket']]
            t['twin_status'][run['status_bucket']] += 1
            t['text_evidence']['twin'] = True
            if run['host_seconds'] is not None:
                t['twin_host_runs'] += 1
                t['twin_host_seconds'] = (t['twin_host_seconds'] or 0) + run['host_seconds']
    for receipt in receipts.values():
        job = ledger_jobs.get(receipt['job_id'], {})
        receipt['window'] = receipt['window'] or job.get('window')
        receipt['ticket'] = receipt['ticket'] or job.get('ticket')
        if receipt['ticket'] in tickets:
            t = tickets[receipt['ticket']]
            t['card_jobs'] += 1
            t['card_minutes'] += receipt['card_minutes']
            t['text_evidence']['card'] = True
            if receipt['window'] is not None:
                t['card_windows'] = sorted(set(t['card_windows'] + [receipt['window']]), key=str)
    predictions = load_json(predictions_path, warnings)
    if not isinstance(predictions, list):
        raise ValueError('predictions.json must contain a list of prediction rows')
    scores = [score(row) for row in predictions]
    for row in scores:
        for tid in row.get('tickets', []):
            if tid in tickets and row.get('method') == 'model':
                tickets[tid]['model_table'] = True
    rows = sorted(tickets.values(), key=lambda t: (t['sprint'], int(TICKET.search(t['ticket']).group(2))))
    sprints = [dict(sprint=s, tickets=sum(t['sprint'] == s for t in rows),
                    **aggregate([t for t in rows if t['sprint'] == s])) for s in sorted({t['sprint'] for t in rows})]
    totals = aggregate(rows)
    directions = [s['direction_right'] for s in scores if s['direction_right'] is not None]
    avoided = {(tuple(s.get('tickets', [])), v) for s in scores for v in s['avoided_variants']}
    totals.update(card_jobs=len(receipts), card_minutes=sum(r['card_minutes'] for r in receipts.values()),
                  card_runs_avoided=len(avoided), shared_allocation_jobs=len(ledger_jobs), direction_scored=len(directions),
                  direction_right=sum(directions), direction_hit_rate=sum(directions) / len(directions) if directions else None,
                  usefulness=dict(collections.Counter(s['usefulness'] for s in scores)),
                  unmapped_card_jobs=sum(r['ticket'] not in tickets for r in receipts.values()),
                  unmapped_twin_runs=sum(r['ticket'] not in tickets for r in twins.values()))
    return dict(schema='knc-boinc.pilot-metrics/1', source_repo=str(repo), predictions_source=str(predictions_path),
                tickets=rows, sprints=sprints, sessions=sessions, twin_runs=list(twins.values()),
                card_jobs=list(receipts.values()), shared_windows=list(ledger_jobs.values()),
                predictions=scores, totals=totals, warnings=warnings)


def fmt(value, digits=3):
    if value is None:
        return 'unknown'
    return ('{:.%df}' % digits).format(value)


def cell(value):
    return str(value).replace('|', '\|').replace('\n', ' ')


def table(headers, rows):
    return '\n'.join('| ' + ' | '.join(map(cell, row)) + ' |' for row in
                     [headers, ['---'] * len(headers)] + rows)


def render(data):
    lines = ['# Pilot-study ledger', '',
             'Generated by `tools/pilot_metrics.py` from the main checkout (read-only), its worktrees, '
             'CLI logs, receipts, shared ledger, and `predictions.json`. No network or card access.', '',
             'Rerun from the S8-06 worktree: `python tools/pilot_metrics.py`. '
             'Optional: `--repo PATH --ledger PATH --predictions PATH --output PATH`.', '',
             'Hours are first-to-last timestamped event per session, summed across sessions; overlapping '
             'sessions are not de-overlapped. Unknown means absent evidence, never zero effort. '
             'Timestamp-free CLI logs still count as sessions; filesystem timestamps are not duration evidence. '
             'Tokens are retained by category in metrics.json; cached input is part of input, not added again.', '',
             'Twin counts include all commands, not just simulations. Exact JSON copies across worktrees count '
             'once; original invocation cwd/artifact path determines ownership before the copy path. '
             'Host seconds use the overall Python execution field, not a sum of nested timing fields. '
             'Receipts count once per job ID; receipt ownership follows its ticket path. '
             'Ledger allocation windows are separate from application jobs and do not add whole-window minutes. '
             'Receipt minutes include staging and are not application wall times. Missing window IDs stay unknown.', '',
             'Model and variant flags use Engineer-report evidence and explicit model prediction rows; ticket '
             'instructions alone do not establish use. Outcome quotes the first report paragraph, truncated at 180 characters. '
             'No means no positive recorded evidence.', '', '## Per ticket', '']
    lines.append(table(['Sprint', 'Ticket', 'Sessions', 'Engineer h', 'Twin ok/unsupported', 'Twin host s',
                        'Model table', 'Card jobs', 'Card min', 'Outcome'], [
        [t['sprint'], t['ticket'], t['sessions'], fmt(t['engineer_seconds'] / 3600 if t['engineer_seconds'] is not None else None),
         '{ok}/{unsupported}'.format(**t['twin_status']), fmt(t['twin_host_seconds']),
         'yes' if t['model_table'] else 'no', t['card_jobs'], fmt(t['card_minutes']), t['outcome']] for t in data['tickets']]))
    lines += ['', '## Per sprint', '', table(
        ['Sprint', 'Tickets', 'Sessions', 'Engineer h', 'Twin ok/unsupported/missing/other', 'Twin host s', 'Model tickets', 'Card jobs', 'Card min'], [
            [s['sprint'], s['tickets'], s['sessions'], fmt(s['engineer_seconds'] / 3600 if s['engineer_seconds'] is not None else None),
             '/'.join(str(s['twin_status'][k]) for k in STATUSES), fmt(s['twin_host_seconds']),
             s['model_tickets'], s['card_jobs'], fmt(s['card_minutes'])] for s in data['sprints']]), '', '## Scoring', '',
        'Ratio = measured / predicted, only for the same numeric unit and scope. Direction compares '
        'the sign of change against a common baseline, or explicit winner names. Range ratios show the endpoint interval without inventing a '
        'midpoint. `decided`/`missed` require a comparable card direction; `unsupported` records a refusal; '
        '`not-attempted` includes predictions whose card comparison has not been attempted or cannot be scored. '
        'Functional host checks and whole-run timings cannot validate force-only cycle predictions.', '',
        table(['Prediction', 'Tickets', 'Predicted', 'Measured card', 'Ratio', 'Direction right', 'Usefulness', 'Evidence / limits'], [
            [s['id'], ', '.join(s.get('tickets', [])), s.get('predicted_text', str(s.get('predicted', 'unknown'))),
             s.get('measured_text', str(s.get('measured', 'unknown'))), (' to '.join(fmt(v) for v in s['ratio_range']) if s['ratio_range'] else fmt(s['ratio'])),
             'unknown' if s['direction_right'] is None else ('yes' if s['direction_right'] else 'no'),
             s['usefulness'], s.get('notes', '') + ' Sources: ' + ', '.join(s.get('sources', []))] for s in data['predictions']])]
    t = data['totals']
    lines += ['', '## Totals and coverage', '',
              table(['Metric', 'Value'], [
                  ['Card minutes (unique receipts / explicit ledger minutes)', fmt(t['card_minutes'])],
                  ['Card jobs', t['card_jobs']], ['Shared allocation jobs (separate)', t['shared_allocation_jobs']],
                  ['Unmapped card jobs', t['unmapped_card_jobs']],
                  ['Unmapped twin runs', t['unmapped_twin_runs']],
                  ['Card runs avoided by explicit off-card variant ranking', t['card_runs_avoided']],
                  ['Direction-right hit rate', '{} / {} ({})'.format(t['direction_right'], t['direction_scored'], fmt(t['direction_hit_rate']))],
                  ['Sessions with usable event timestamps', '{} / {}'.format(t['sessions_timed'], t['sessions'])],
                  ['Twin runs with host timing', t['twin_host_runs']]]), '',
              'Avoided runs require named ranked variants and an explicit list sent to the card; '
              'absence of a receipt alone is not proof that a run was avoided. Counts are a recorded lower bound. '
              'Per-sprint totals exclude unattributed jobs; global totals include them. '
              'All raw evidence paths, status buckets, token categories and missing-source warnings are in metrics.json.', '',
              '## Shared allocation windows', '', table(
                  ['Job', 'Window', 'Ticket', 'Start', 'End', 'Events'], [
                      [j['job_id'], j['window'] or 'unknown', j['ticket'] or 'unmapped', j['start'] or 'unknown',
                       j['end'] or 'unknown', ', '.join(str(e) for e in j['events'])] for j in data['shared_windows']]), '',
              '{} source warnings (including non-JSON CLI preambles); see metrics.json.'.format(len(data['warnings'])), '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=MAIN_REPO)
    parser.add_argument('--ledger', type=Path, default=LEDGER)
    parser.add_argument('--predictions', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/pilot-study')
    args = parser.parse_args()
    predictions = args.predictions or Path(__file__).resolve().parents[1] / 'docs/pilot-study/predictions.json'
    data = collect(args.repo.resolve(), args.ledger, predictions)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'metrics.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (args.output / 'README.md').write_text(render(data), encoding='utf-8')
    print('{} tickets, {} unique twin results, {} card jobs'.format(len(data['tickets']), len(data['twin_runs']), len(data['card_jobs'])))


if __name__ == '__main__':
    main()
