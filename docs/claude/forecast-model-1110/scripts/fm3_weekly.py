#!/usr/bin/env python3
"""FM-2 layer 3: the books of the challengers and the weekly shadow run (display/score only;
no orders, no policy/state/core-input change).

Rule = forecast-layer3-rule-2026-11-10.md (one level up). The maths is fm3_shadow.py. This file keeps:
  <layer3_dir>/LOG.jsonl       append-only event log, numbered 1..N. It is the record: the registry is what it tells
  <layer3_dir>/REGISTRY.json   findings, challengers and their status. Every command checks it against LOG.jsonl
                               (verify_books); a registry that differs (edited by hand, damaged) stops the command
                               until 'rebuild' has written it again from the log
One command at a time: there is no lock. A command that finds the books changed since it read them stops before it
writes (commit); two commands that overlap more closely than that can still leave books that 'verify' refuses.
  <layer3_dir>/REJECTED.md     one line per challenger horizon that ended without adoption (this model's own record)
  <layer3_dir>/challengers/    the registered copy of each challenger module, its pre-registration text, its admission
                               report and (<id>.issued/) the forecasts it issued, one file per run, never rewritten
  <layer3_dir>/menu/           MENU.json and the reviewed menu modules, in the order they are tried
  <layer3_dir>/runs/           weekly shadow results
  <layer3_dir>/checks/         the recorded check of the judgement interval (rule section 5)

Automatic here: registering the next menu challenger when a slot is free, shadow scoring, ending a challenger.
Never automatic: adoption. A horizon that passes is listed under "awaiting_judge" in every weekly result until a
person has decided (independent judge, then a decision card: rule section 6). There is no command here that
records an adoption; 'close' records a person's decision not to adopt (or to stop) and frees the slot.
A status only moves forward (shadow -> ended / candidate -> closed); a run with an asof older than the last run is
refused; the same asof can be run again: forecasts that were issued are read back and a look that was taken is not
taken again (it adds a 'run' line to the log).
Fixed at registration and written into the log: the module, T0, the judged horizons and the judged pair (the
version on display on that day). A later change of the display does not change the pair a challenger is judged on.
The judged scores use each challenger forecast as it was first issued (fm3_shadow.freeze): the run that first
sees a start day stores the challenger's forecast for it, computed from inputs that end at that start day, and
later runs read it back instead of recomputing it. No table of scores over the past is made (there is no replay),
and the share a history-backed challenger earned (the past score in another unit) is not shown in the weekly result.
No horizon is judged automatically unless every recorded check of the judgement interval on synthetic data passed
for it (interval-check; rule section 5). A judgement that is due without that is held: its numbers are recorded on
the day it is due and the horizon waits for a person; no later check releases it.
A challenger whose new forecasts differ between inputs cut at the start day and inputs cut at asof is ended.
Challenger code never runs in this process (admission: fresh interpreters; staging: child processes).

usage:
  python3 -I -B fm3_weekly.py selftest
  python3 -I -B fm3_weekly.py init <layer3_dir>
  python3 -I -B fm3_weekly.py next <layer3_dir>
  python3 -I -B fm3_weekly.py verify <layer3_dir>
  python3 -I -B fm3_weekly.py rebuild <layer3_dir>
  python3 -I -B fm3_weekly.py interval-check <layer3_dir> <report_json>
  python3 -I -B fm3_weekly.py register <layer3_dir> <menu_id> <pool_dir> <rates_dir> <extra_dir> <asof> <fm2_cache_dir> [--jobs N]
  python3 -I -B fm3_weekly.py run <layer3_dir> <pool_dir> <rates_dir> <extra_dir> <asof> <fm2_cache_dir> <ch_cache_root> <out_json> [--jobs N]
  python3 -I -B fm3_weekly.py close <layer3_dir> <challenger_id> "<who decided, when, why>"
"""
import sys, os, json, ast, shutil, hashlib, datetime
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fm1, fm2, fm2_weekly, fm3_shadow

RULE = 'forecast-layer3-rule-2026-11-10.md'
MAX_SHADOW = 3                    # challengers in shadow scoring (or waiting for a decision) at the same time
MAX_PER_FINDING = 2               # challenges per finding; after that a person decides
FIND_WEEKS = dict(fm3_shadow.MIN_WEEKS)   # scored weeks before the forward record of a horizon can open a finding (104 / 208)
TAIL_MAX = 0.20                   # a finding opens when one tail of the 80% band is breached more often (10% expected)
JUDGED = (20, 60)                 # horizons with a displayed FM-2 candidate; 250 is recorded only
KINDS = {'history': '과거 구간도 계산한다. 몫과 폭 배율은 기존 전문가와 같은 방식으로 과거에서도 배운다. 그 몫은 과거 성적과 같은 정보라 주간 결과에 싣지 않는다',
         'forward': 'T0부터만 계산한다. 몫은 1/5에서 시작한다'}
SKIP_REPORT = 4                   # runs in a row that skip a challenger before the run reports it (rule section 8)
SKIP_CLOSE = 12                   # runs in a row that skip a challenger before the run ends it and frees its slot
CI_COVER_MIN = 0.93               # the 95% judgement interval must hold the true gain at least this often in the check on
                                  # synthetic data before a horizon is judged (forward rule section 3)
FINDINGS0 = [                     # findings of the 2026-11-10 test (design doc sections 4 and 6); fixed by the rule
    {'id': 'D1', 'text': 'The four experts all read prices and rates; no outside information about the coming width',
     'source': 'forecast-model-design-2026-11-10.md 4 (reading 3), 6 (item 2)'},
    {'id': 'D2', 'text': 'Since 2020 the upper edge of the 80% band was breached too often (20 and 60 days)',
     'source': 'forecast-model-design-2026-11-10.md 4 (weak point 7)'},
    {'id': 'D3', 'text': 'No information about the centre (direction), needed most at 60 and 250 days',
     'source': 'forecast-model-design-2026-11-10.md 4 (direction), 6 (item 3)'},
    {'id': 'D4', 'text': 'Policy events that are not in the past sample',
     'source': 'forecast-model-design-2026-11-10.md 6 (item 8)'}]
REJECTED_HEAD = ('# 탈락 기록 — FM-2 3층 도전자 (이 모형 전용)\n\n'
                 '- 편입되지 않고 끝난 도전자를 구간마다 한 줄씩 적는다. scripts/fm3_weekly.py가 쓴다. 지난 줄은 고치지 않는다.\n'
                 '- "중간 점검" 줄은 최소 표본 전에 자리를 비운 기록이다. 해롭다는 최종 판정이 아니다.\n'
                 '- 회사의 Failure Museum(failure-museum.json)과는 다른 파일이다. 규칙: ' + RULE + '\n\n'
                 '| 도전자 | 발견 | 등록(KST) | 끝난 실행(asof) | 구간 | 채점 주 | 이득 (95% 구간) | 사유 |\n|---|---|---|---|---|---|---|---|\n')
WHY = {'drop_futility': '중간 점검: 구간 상한 < 0. 최소 표본 전에 자리를 비운 것이며 해롭다는 최종 판정이 아님',
       'end_harm': '해로움(구간 상한 < 0)', 'end_inconclusive': '구분 안 됨(구간이 0을 품음)',
       'end_coverage': '이득은 있으나 포함률이 70~90% 밖',
       'end_cut_mismatch': '시작일 대조 불일치(미래 자료 사용 또는 비결정)로 채점을 끝냄'}
STOPPED = ('books stopped: %s (two commands at the same time, or a file was edited). This command wrote nothing into '
           'LOG.jsonl, REGISTRY.json or REJECTED.md. One command at a time; run "verify", and "rebuild" if it says so')
STOPPED_SAVED = ('books stopped: %s (two commands at the same time, or a file was edited). This command had already saved '
                 'REGISTRY.json and could not complete LOG.jsonl. One command at a time; run "rebuild": it prints the lines '
                 'this command still owed, leaves them out and writes the registry again from the log')
PREREG = '''# 도전자 사전 등록 — {cid}

- 성격: 표시·채점 전용. 주문·정책·상태·자동 코어 입력·한도·권한 변경 0. 편입은 사장 카드로만 한다.
- 규칙: {rule} (판정·한도·기본 처분은 그 문서 그대로이고 여기서 바꾸지 않는다)
- 발견: {finding} — {finding_text}
- 이 발견의 도전 횟수: {attempt}번째 (한도 {max_per}회)
- 만든 길: {route} · 종류: {kind} ({kindtxt})
- 계산 파일: {module} (sha256 {msha})
- 추가 자료: {extras}
- 추가 자료를 읽는 시점: {lagtxt}
- 판정 구간: {judged}거래일 (나머지 구간은 기록만)
- 판정 쌍: {pair} (등록한 날 표시 중인 판. 뒤에 표시가 바뀌어도 이 쌍으로 판정한다)
- 등록 시각: {at} · 등록 때 자료 기준일: {asof}
- 그림자 채점 시작(T0): 시작일이 {t0} 이후인 예측만 판정에 쓴다.
- 등록 심사(기술 점검, 실제 결과와 대조하지 않음): {admission}

## 정의 (계산 파일 머리글 그대로)

```
{doc}
```

## 고정한 것

- 위 계산 파일은 등록 뒤 고치지 않는다. 고치면 새 도전으로 세고 새 T0부터 다시 잰다.
- T0 전 구간의 성적표는 만들지 않는다. 판정은 T0 이후에 낸 예측만으로 한다.
'''


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def kst_now():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S KST')


def quarter(day):
    return '%sQ%d' % (day[:4], (int(day[5:7]) - 1) // 3 + 1)


# ---------------- the books ----------------
def load_reg(d):
    return json.load(open(os.path.join(d, 'REGISTRY.json'), encoding='utf-8'))


def save_reg(d, reg):
    """Atomic: a crash leaves the old or the new registry, never a torn one."""
    p = os.path.join(d, 'REGISTRY.json'); tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp, p)


def _append(path, text):
    """Append whole lines. A torn last line (an earlier crash) is closed first, never repaired."""
    torn = False
    if os.path.exists(path) and os.path.getsize(path):
        with open(path, 'rb') as f:
            f.seek(-1, os.SEEK_END); torn = f.read(1) != b'\n'
    with open(path, 'a', encoding='utf-8') as f:
        f.write(('\n' if torn else '') + text)


def read_log(d):
    p = os.path.join(d, 'LOG.jsonl'); out = []
    for line in (open(p, encoding='utf-8').read().splitlines() if os.path.exists(p) else []):
        try:
            out.append(json.loads(line))
        except ValueError:                                      # a torn line: skipped
            pass
    return out


def ensure_rejected(d):
    """REJECTED.md with its head (the file is made after the first commit of the books, and again if it is lost).
    When it is made again for books that hold more than the init line, that is said: the lines the lost file held
    are not restored here (the judged and status events of LOG.jsonl still hold them; review R3-4)."""
    rp = os.path.join(d, 'REJECTED.md')
    if not os.path.exists(rp):
        if len(read_log(d)) > 1:
            print('NOTICE: REJECTED.md was missing and was made again with its head only. The lines it held are not '
                  'restored; the judged and status events of LOG.jsonl still hold them')
        with open(rp, 'w', encoding='utf-8') as f:
            f.write(REJECTED_HEAD)
    return rp


def flush(d, reg, saved=False):
    """Append what the registry still owes to LOG.jsonl and REJECTED.md (its outbox), then clear the outbox.
    A line that is already there (a crash between the append and the clearing) is not written twice.
    The owed lines must continue the log. If a line with an owed number is there with another content, or the owed
    numbers do not follow the last line, something else wrote in between: stop, write nothing (review R2-5).
    'saved' is set by commit, which has saved the registry by then: the message tells that (review R3-2)."""
    stop = STOPPED_SAVED if saved else STOPPED
    ob = reg.get('outbox') or {}
    if not (ob.get('log') or ob.get('rejected')):
        return
    canon = lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False)
    evs = read_log(d); have = {ev.get('seq'): ev for ev in evs}; owed = []
    for ev in ob.get('log', []):
        if ev['seq'] not in have:
            owed.append(ev)
        elif canon(have[ev['seq']]) != canon(ev):
            raise SystemExit(stop % ('line %d of LOG.jsonl is not the line the registry owes' % ev['seq']))
    if [ev['seq'] for ev in owed] != list(range(len(evs) + 1, len(evs) + 1 + len(owed))):
        raise SystemExit(stop % 'the lines the registry owes do not follow the last line of LOG.jsonl')
    for ev in owed:
        _append(os.path.join(d, 'LOG.jsonl'), json.dumps(ev, ensure_ascii=False) + '\n')
    rp = ensure_rejected(d); txt = open(rp, encoding='utf-8').read()
    for line in ob.get('rejected', []):
        if line not in txt:
            _append(rp, line)
    reg['outbox'] = {}
    save_reg(d, reg)


def books_from_log(evs):
    """The registry as LOG.jsonl tells it. REGISTRY.json must equal this (verify_books); 'rebuild' writes it."""
    reg = None
    for ev in json.loads(json.dumps(evs)):                      # a copy: nothing here shares an object with the events
        k = ev.get('event')
        if k == 'init':
            reg = {'version': 2, 'rule': ev['rule'], 'display': ev['display'], 'last_judgement_quarter': ev['quarter'],
                   'last_run_asof': '', 'interval_check': None, 'findings': [dict(f, challenges=[]) for f in ev['findings']],
                   'challengers': []}
            continue
        if reg is None:
            raise SystemExit('books refused: LOG.jsonl does not start with the init event')
        c = next((x for x in reg['challengers'] if x['id'] == ev.get('id')), None)
        if k == 'interval_check':
            reg['interval_check'] = ev['check']
        elif k == 'finding_opened':
            reg['findings'].append(dict(ev['finding'], challenges=[]))
        elif k == 'registered':
            reg['challengers'].append(ev['entry'])
            next(f for f in reg['findings'] if f['id'] == ev['entry']['finding'])['challenges'].append(ev['entry']['id'])
        elif k == 'issued':
            c['issued'].append({a: ev[a] for a in ('asof', 'file', 'sha256', 'rows')})
        elif k == 'held':
            c['held'][str(ev['h'])] = {'asof': ev['asof'], 'row': ev['row']}
        elif k == 'judged':
            c['h_status'][str(ev['h'])] = ev['status']
        elif k == 'status':
            c['status'] = ev['status']
        elif k == 'run':
            reg['last_run_asof'] = ev['asof']
            for x in reg['challengers']:
                if x['id'] in ev['judged_now']:
                    x['judged_quarter'] = ev['quarter']
            if ev['findings_run']:
                reg['last_judgement_quarter'] = ev['quarter']
    if reg is not None:
        reg['log_seq'] = len(evs)
    return reg


def verify_books(d, reg, written=False):
    """Stop unless REGISTRY.json is exactly what LOG.jsonl tells. Nothing is repaired here.
    written: the check after a commit (the command's lines are in the files by then)."""
    evs = read_log(d)
    if [ev.get('seq') for ev in evs] != list(range(1, len(evs) + 1)):
        raise SystemExit('books refused: the numbers in LOG.jsonl are not 1..N (a line is missing, repeated or damaged)')
    want = books_from_log(evs); have = {k: v for k, v in reg.items() if k != 'outbox'}
    canon = lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False)
    if want is None or canon(want) != canon(have):
        diff = sorted(k for k in set(want or {}) | set(have) if canon((want or {}).get(k)) != canon(have.get(k)))
        raise SystemExit('books refused: REGISTRY.json is not what LOG.jsonl tells (differs in: %s). %s '
                         'Do not edit either file; "rebuild" writes the registry again from the log'
                         % (', '.join(diff), 'This command has written its lines; another command wrote at the same time.'
                            if written else 'Nothing was changed.'))


def commit(d, reg, evs, rej=()):
    """One change of the books. The registry is saved together with the lines it owes (outbox); then they are
    appended and the outbox is cleared. A crash in between is finished by the next command (flush; 'rebuild' too).
    Before anything is written the books on disk must still be the ones this command read: LOG.jsonl has as many
    lines as the registry in memory counts, and the registry on disk counts the same and owes nothing. Otherwise
    another command wrote meanwhile and this one stops without writing (review R2-5)."""
    seq = reg.get('log_seq', 0); out = []
    rp = os.path.join(d, 'REGISTRY.json'); disk = load_reg(d) if os.path.exists(rp) else None
    if len(read_log(d)) != seq or (disk is None and seq) or (disk is not None and (disk.get('log_seq') != seq or disk.get('outbox'))):
        raise SystemExit(STOPPED % 'the books changed while this command was running')
    for ev in evs:
        seq += 1; out.append({'at': kst_now(), 'seq': seq, **ev})
    reg['log_seq'] = seq; reg['outbox'] = {'log': out, 'rejected': list(rej)}
    save_reg(d, reg)
    flush(d, reg, saved=True)
    verify_books(d, load_reg(d), written=True)


def open_books(d):
    """Every command starts here: finish what an earlier crash left, then check the registry against the log.
    A registry whose owed lines cannot be read (edited by hand, or damaged) is refused like any other edit."""
    reg = load_reg(d)
    try:
        flush(d, reg)
    except (KeyError, AttributeError, TypeError) as ex:
        raise SystemExit('books refused: the lines REGISTRY.json still owes cannot be read (%s). Run "rebuild"' % type(ex).__name__)
    verify_books(d, reg); ensure_rejected(d)
    return reg


def cmd_init(d, today=None):
    have = [f for f in ('REGISTRY.json', 'LOG.jsonl', 'REJECTED.md') if os.path.exists(os.path.join(d, f))]
    if have:
        raise SystemExit('not initialised: %s already exist(s); init runs once and never overwrites the books' % ', '.join(have))
    for sub in ('challengers', 'menu', 'runs', 'checks'):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    today = today or kst_now()[:10]
    ev = {'event': 'init', 'rule': RULE,
          'display': {str(h): 'FM2' for h in JUDGED},        # the version on display per horizon: FM2 or F0 (forward rule 4)
          'quarter': quarter(today),                         # forward findings are looked at once per quarter, after this one
          'findings': [dict(f, opened=today, status='open') for f in FINDINGS0]}
    reg = books_from_log([ev]); reg['log_seq'] = 0
    commit(d, reg, [ev])                  # the registry first: a crash after it is finished by the next command
    ensure_rejected(d)
    return reg


def cmd_rebuild(d):
    """Write REGISTRY.json again from LOG.jsonl (a lost or damaged registry, or one that was edited by hand).
    First the lines an unfinished command still owes are appended, when the registry on disk can be read and its
    owed lines continue the log (flush); owed lines that do not are dropped and printed. Then the log decides."""
    try:
        old = load_reg(d)
    except (OSError, ValueError):
        old = None
    ob = old.get('outbox') if isinstance(old, dict) else None
    if ob:
        try:
            flush(d, old)
        except (SystemExit, Exception) as ex:                   # owed lines that do not continue the log, or cannot be read (R3-3)
            owed = [x if isinstance(x, list) else [] for x in ((ob.get('log'), ob.get('rejected')) if isinstance(ob, dict) else (0, 0))]
            why = str(ex).split(' (')[0] if isinstance(ex, SystemExit) else 'the owed lines cannot be read: %s' % type(ex).__name__
            print('rebuild: %d owed LOG line(s) and %d owed REJECTED line(s) of the old registry are dropped (%s)'
                  % (len(owed[0]), len(owed[1]), why))
            have = {json.dumps(ev, sort_keys=True, ensure_ascii=False) for ev in read_log(d)}
            for ev in owed[0]:
                there = json.dumps(ev, sort_keys=True, ensure_ascii=False, default=str) in have
                print('  %s:' % ('kept (it is in LOG.jsonl)' if there else 'dropped'), json.dumps(ev, ensure_ascii=False, default=str)[:300])
    evs = read_log(d)
    if [ev.get('seq') for ev in evs] != list(range(1, len(evs) + 1)):
        raise SystemExit('not rebuilt: the numbers in LOG.jsonl are not 1..N')
    reg = books_from_log(evs)
    if reg is None:
        raise SystemExit('not rebuilt: LOG.jsonl is empty')
    reg['outbox'] = {}
    save_reg(d, reg); verify_books(d, load_reg(d)); ensure_rejected(d)
    return reg


def ci_lengths():
    """The sample sizes (weeks) each judged horizon is judged at: the interim look, where there is one, and the
    minimum sample. The check of the judgement interval must report every one of them ({20: [65, 104], 60: [208]})."""
    S = fm3_shadow
    return {h: sorted({S.MIN_WEEKS[h]} | ({S.FUT_WEEKS[h]} if h in S.FUT_WEEKS else set())) for h in JUDGED}


def cmd_interval_check(d, report_json):
    """Record the check of the judgement interval on synthetic data (rule section 5, forward rule section 3).
    report_json: {"method": "...", "coverage": {"20": {"65": x, "104": y}, "60": {"208": z}}, ...} - how often the
    95% interval of the paired gain held the true gain, for every judged horizon at every sample size (weeks) the
    rule judges it at (ci_lengths). A report that leaves one out is not recorded. The file is copied into
    <layer3_dir>/checks/. A horizon passes when every one of its values is >= CI_COVER_MIN.
    'auto' (the run may judge the horizon without a person) needs every recorded check to have passed for it: a
    pass recorded after a failed check does not bring it back. A judgement that was held is never released by a
    check. Both are a person's decision (rule section 5; review R2-7)."""
    reg = open_books(d)
    rep = json.load(open(report_json, encoding='utf-8'))
    need = ci_lengths(); cov = {}
    try:
        for h in JUDGED:
            raw = {str(n): rep['coverage'][str(h)][str(n)] for n in need[h]}
            if any(isinstance(v, bool) for v in raw.values()):  # true/false is not a rate (review R3-6)
                raise ValueError('true/false')
            cov[str(h)] = {n: float(v) for n, v in raw.items()}
    except (KeyError, TypeError, ValueError):
        raise SystemExit('not recorded: the report needs "coverage" for every judged horizon at every sample size (weeks): %s'
                         % json.dumps({str(h): {str(n): '0..1' for n in v} for h, v in need.items()}))
    if not all(0.0 <= v <= 1.0 for c in cov.values() for v in c.values()):
        raise SystemExit('not recorded: every coverage value must be between 0 and 1')
    prev = reg.get('interval_check')
    ok = {h: all(v >= CI_COVER_MIN for v in c.values()) for h, c in cov.items()}
    auto = {h: bool(ok[h] and (prev is None or (prev.get('auto') or {}).get(h, False))) for h in ok}
    os.makedirs(os.path.join(d, 'checks'), exist_ok=True)
    n = sum(ev.get('event') == 'interval_check' for ev in read_log(d)) + 1
    rel = 'checks/interval_check_%03d.json' % n
    shutil.copyfile(report_json, os.path.join(d, rel))
    reg['interval_check'] = {'at': kst_now(), 'n': n, 'file': rel, 'sha256': sha(os.path.join(d, rel)), 'coverage': cov,
                             'need': CI_COVER_MIN, 'pass': ok, 'auto': auto}
    commit(d, reg, [{'event': 'interval_check', 'check': reg['interval_check']}])
    return reg['interval_check']


def slots_used(reg):
    return sum(c['status'] in ('shadow', 'candidate') for c in reg['challengers'])


def next_menu(reg, menu):
    """The next menu entry that may be registered now, or (None, reason)."""
    if slots_used(reg) >= MAX_SHADOW:
        return None, 'no free slot (%d of %d in use)' % (slots_used(reg), MAX_SHADOW)
    used = {c.get('menu_id') for c in reg['challengers']}
    fd = {f['id']: f for f in reg['findings']}
    for e in menu:
        f = fd.get(e['finding'])
        if e['menu_id'] in used or f is None or f['status'] != 'open' or len(f['challenges']) >= MAX_PER_FINDING:
            continue
        return e, 'ok'
    return None, 'no eligible menu entry (menu used up, or its findings are closed or at the challenge limit)'


def cache_note(cache, pool_dir, rates_dir, asof):
    """None when the fm2 expert cache is the one fm2_weekly.py built from these very input files at this asof."""
    ix = os.path.join(cache, 'INDEX.json'); dg = os.path.join(cache, 'INPUTS.sha256')
    if not (os.path.exists(ix) and os.path.exists(dg)):
        return 'the fm2 cache has no INDEX.json / INPUTS.sha256 (run fm2_weekly.py for this asof first)'
    if json.load(open(ix)).get('asof') != asof:
        return 'the fm2 cache asof is not %s' % asof
    if open(dg).read().strip() != fm2_weekly.inputs_digest(pool_dir, rates_dir):
        return 'the fm2 cache was not built from these input files'
    return None


def cmd_register(d, menu_id, pool_dir, rates_dir, extra_dir, asof, cache, today=None, admit=fm3_shadow.admit, jobs=1):
    reg = open_books(d)
    menu = json.load(open(os.path.join(d, 'menu', 'MENU.json'), encoding='utf-8'))
    e, why = next_menu(reg, menu)
    if e is None or e['menu_id'] != menu_id:
        raise SystemExit('not registered: %s' % (why if e is None else 'the next eligible menu entry is %s' % e['menu_id']))
    src = os.path.join(d, 'menu', e['module'])
    if sha(src) != e['module_sha256']:
        raise SystemExit('not registered: menu module differs from the hash in MENU.json')
    judged = [h for h in e['judged_horizons'] if h in JUDGED]
    if not judged or e['kind'] not in KINDS:
        raise SystemExit('not registered: no judged horizon among %s, or kind is not one of %s' % (JUDGED, sorted(KINDS)))
    if today is None and int(kst_now()[11:13]) >= 23:           # T0 is tomorrow: the copy must reach today's docs commit (23:30 KST)
        raise SystemExit('not registered: after 23:00 KST the registration would miss today\'s docs commit; register tomorrow')
    note = cache_note(cache, pool_dir, rates_dir, asof)
    if note:
        raise SystemExit('not registered: ' + note)
    rep = admit(src, pool_dir, rates_dir, extra_dir, asof, cache, jobs)
    if not rep['pass'] or 'full_grid' not in rep['tests']:
        commit(d, reg, [{'event': 'admission_failed', 'menu_id': menu_id, 'module_sha256': e['module_sha256'], 'asof': asof,
                         'tests': {k: v['pass'] for k, v in rep['tests'].items()}}])
        raise SystemExit('not registered: admission failed %s' % json.dumps(rep['tests']))
    if today is None and int(kst_now()[11:13]) >= 23:           # the admission ran past 23:00: the same reason as above
        raise SystemExit('not registered: the admission ended after 23:00 KST; register tomorrow (nothing was written)')
    f = next(x for x in reg['findings'] if x['id'] == e['finding'])
    cid = 'c%02d_%s' % (len(reg['challengers']) + 1, menu_id)
    mod_rel = 'challengers/%s.py' % cid; pre_rel = 'challengers/%s.prereg.md' % cid; adm_rel = 'challengers/%s.admission.json' % cid
    shutil.copyfile(src, os.path.join(d, mod_rel))
    msha = sha(os.path.join(d, mod_rel))
    with open(os.path.join(d, adm_rel), 'w', encoding='utf-8') as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1)
    today = today or kst_now()[:10]; at = kst_now()
    t0 = max(fm3_shadow.FORWARD_START, (datetime.date.fromisoformat(today) + datetime.timedelta(days=1)).isoformat())
    xlag = int(rep['tests']['api'].get('extra_lag', 0))
    pair = {str(h): reg['display'][str(h)] for h in judged}     # fixed here: the version on display today
    adm = ', '.join('%s %s' % (k, 'ok' if v['pass'] else 'FAIL') for k, v in rep['tests'].items())
    doc = ast.get_docstring(ast.parse(open(src, encoding='utf-8').read())) or ''
    with open(os.path.join(d, pre_rel), 'w', encoding='utf-8') as fh:
        fh.write(PREREG.format(cid=cid, rule=RULE, finding=f['id'], finding_text=f['text'], attempt=len(f['challenges']) + 1,
                               max_per=MAX_PER_FINDING, route=e.get('route', 'menu'), kind=e['kind'], kindtxt=KINDS[e['kind']],
                               module=mod_rel, msha=msha, extras=json.dumps(rep['tests']['api'].get('extras', {})),
                               lagtxt='모든 종목이 시작일 전날까지의 값만 읽는다' if xlag else '미국 상장 종목은 시작일 당일 값까지, 그 밖의 종목은 전날 값까지 읽는다',
                               judged='·'.join(str(h) for h in judged),
                               pair=', '.join('%s일 = %s+ 대 %s' % (h, v, v) for h, v in pair.items()),
                               at=at, asof=asof, t0=t0, admission=adm, doc=doc))
    ch = {'id': cid, 'menu_id': menu_id, 'finding': f['id'], 'attempt': len(f['challenges']) + 1, 'route': e.get('route', 'menu'),
          'kind': e['kind'], 'judged_horizons': judged, 'judged_pair': pair, 'module': mod_rel, 'module_sha256': msha,
          'prereg': pre_rel, 'prereg_sha256': sha(os.path.join(d, pre_rel)), 'admission': adm_rel,
          'admission_sha256': sha(os.path.join(d, adm_rel)), 'extras': rep['tests']['api'].get('extras', {}), 'extra_lag': xlag,
          'registered_at': at, 'asof': asof, 't0': t0, 'status': 'shadow', 'h_status': {str(h): 'shadow' for h in judged},
          'judged_quarter': quarter(today), 'held': {}, 'issued': []}
    reg['challengers'].append(ch); f['challenges'].append(cid)
    commit(d, reg, [{'event': 'registered', 'id': cid, 'menu_sha256': sha(os.path.join(d, 'menu', 'MENU.json')), 'entry': ch}])
    return ch


def fmt_gain(row):
    if 'gain' not in row:
        return '채점 없음'
    ci = row.get('gain_ci95')
    return '%+.2f%%' % (100 * row['gain']) + (' (%+.2f ~ %+.2f%%)' % (100 * ci[0], 100 * ci[1]) if ci else ' (구간 없음)')


def reject_line(c, asof, h, row, why):
    return ('| %s | %s | %s | %s | %s일 | %s | %s | %s |\n'
            % (c['id'], c['finding'], c['registered_at'], asof, h, row.get('weeks', 0), fmt_gain(row), why.replace('|', '/').replace('\n', ' ')))


def set_status(c, status, asof, note):
    """Change a challenger's status in the registry object; returns the LOG event that tells it."""
    c['status'] = status
    return {'event': 'status', 'id': c['id'], 'status': status, 'asof': asof, 'note': note}


def end_if_done(c, asof, note=None):
    """When no judged horizon is left in shadow: candidate if one passed (it waits for a person), otherwise ended.
    A challenger that the start-day check ended is never a candidate, whatever another horizon read before: code
    that was found to look ahead (or not to be deterministic) does not go to a card (review R3-1)."""
    hs = list(c['h_status'].values())
    if c['status'] == 'shadow' and 'shadow' not in hs:
        cand = 'pass_to_judge' in hs and 'end_cut_mismatch' not in hs
        return [set_status(c, 'candidate' if cand else 'ended', asof, note or json.dumps(c['h_status']))]
    return []


def cmd_close(d, cid, reason):
    """Record a person's decision that ends a challenger: after a decision card on a candidate (not adopted), or an
    instruction to stop one that is still in shadow. Its slot is free afterwards. The weekly run never calls this."""
    reg = open_books(d)
    c = next((x for x in reg['challengers'] if x['id'] == cid), None)
    if c is None or c['status'] not in ('shadow', 'candidate'):
        raise SystemExit('not closed: %s is not a challenger in shadow or waiting for a decision' % cid)
    if len(reason.strip()) < 10:
        raise SystemExit('not closed: give the reason (who decided, when, why)')
    asof = reg['last_run_asof'] or '-'
    rej = [reject_line(c, asof, '·'.join(str(h) for h in c['judged_horizons']), {}, '사람이 닫음: ' + reason.strip())]
    commit(d, reg, [dict(set_status(c, 'closed', asof, reason.strip()), by='person')], rej)
    return c


def inputs_digest(c, d, pool_dir, rates_dir, extra_dir, asof, issued):
    """What a staged challenger depends on: its module, asof, t0, every input file and the issued-forecast files."""
    hh = hashlib.sha256(('%s|%s|%s|%s\n' % (c['module_sha256'], asof, c['t0'], ','.join(issued))).encode())
    for base, stems in ((pool_dir, [s for s, _, _ in fm2.UNIVERSE]), (rates_dir, ['_TNX', '_IRX']), (extra_dir, sorted(c['extras'].values()))):
        for stem in stems:
            hh.update(('%s:%s\n' % (stem, sha(os.path.join(base, stem + '.json')))).encode())
    return hh.hexdigest()


def skip_streak(d, cid, asof):
    """How many runs in a row before this one skipped this challenger. One per asof: the latest run of each asof
    counts, and an earlier run of this run's own asof does not."""
    n = 0; seen = {asof}
    for ev in reversed(read_log(d)):
        if ev.get('event') != 'run' or ev.get('asof') in seen:
            continue
        seen.add(ev.get('asof'))
        if cid not in ev.get('skipped', {}):
            break
        n += 1
    return n


def forward_check(F, R):
    """The forward record of the FM-2 pool that can open a finding: coverage and the two tail-breach rates."""
    mk = (F['start'] >= fm2.ordinal(fm3_shadow.FORWARD_START)) & (F['mat'] >= 0)
    if not mk.sum():
        return {'weeks': 0}
    miss = R['hit'][mk] == 0; up = F['y'][mk] > R['med'][mk]
    return {'weeks': len(set(F['week'][mk].tolist())), 'n': int(mk.sum()), 'cov80': float(R['hit'][mk].mean()),
            'above_q90': float((miss & up).mean()), 'below_q10': float((miss & ~up).mean())}


def open_findings(reg, h, chk, today):
    """Findings the forward record opens (rule section 2). Each id opens once. Returns the new finding records."""
    new = []
    if chk.get('weeks', 0) < FIND_WEEKS[h]:
        return new
    have = {f['id'] for f in reg['findings']}
    for fid, hit, text in (('F-upper-%d' % h, chk['above_q90'] > TAIL_MAX, 'Forward: the upper edge of the %d-day band is breached too often' % h),
                           ('F-lower-%d' % h, chk['below_q10'] > TAIL_MAX, 'Forward: the lower edge of the %d-day band is breached too often' % h),
                           ('F-width-%d' % h, not (fm3_shadow.COV_BAND[0] <= chk['cov80'] <= fm3_shadow.COV_BAND[1]),
                            'Forward: the %d-day 80%% band holds too few or too many outcomes' % h)):
        if hit and fid not in have:
            new.append({'id': fid, 'text': text, 'source': 'forward record: %s' % json.dumps(chk), 'opened': today, 'status': 'open'})
            reg['findings'].append(dict(new[-1], challenges=[]))
    return new


def extra_stale(f, asof):
    """True when an extra input file cannot be used at asof: missing, unreadable, empty, or its last day is before asof."""
    try:
        return fm1.load_yahoo(f)[0][-1] < asof
    except Exception:
        return True


def shown(c, per_h):
    """What the weekly result shows of one scored challenger at one horizon. For a history-backed challenger the
    share it earned is left out ('state', 'om_mean'): the share of a learner that never forgets is the score over
    the past in another unit (review R2-2). The judged numbers of the day a judgement is due go to the log whole."""
    if c['kind'] != 'history':
        return per_h
    return {'forward': {k: {a: b for a, b in row.items() if a != 'om_mean'} for k, row in per_h['forward'].items()},
            'state': 'not shown for a history-backed challenger (rule section 4)'}


def cmd_run(d, pool_dir, rates_dir, extra_dir, asof, cache, ch_root, outp, jobs=1):
    reg = open_books(d)
    if asof < reg.get('last_run_asof', ''):
        raise SystemExit('not run: asof %s is older than the last run (%s)' % (asof, reg['last_run_asof']))
    note = cache_note(cache, pool_dir, rates_dir, asof)
    if note:
        raise SystemExit('not run: ' + note)
    here = os.path.dirname(os.path.abspath(__file__)); menu_path = os.path.join(d, 'menu', 'MENU.json')
    res = {'asof': asof, 'run_at': kst_now(), 'rule': RULE,
           'code': {k: sha(os.path.join(here, k + '.py'))[:16] for k in ('fm3_shadow', 'fm3_weekly', 'fm2', 'fm1')},
           'menu_sha256': sha(menu_path) if os.path.exists(menu_path) else None, 'display': reg['display'],
           'interval_check': reg['interval_check'], 'slots_used': slots_used(reg), 'skipped': {}, 'challengers': {},
           'forward_check': {}, 'events': [], 'held': []}
    ch_dirs = {}; specs = {}; frozen = {}; new_issue = {}; mismatch = {}
    evs = []; rej = []                    # LOG events and REJECTED lines: written with the registry (commit)
    for c in reg['challengers']:
        if c['status'] != 'shadow':
            continue
        path = os.path.join(d, c['module'])
        bad = [k for k in ('module', 'prereg', 'admission') if not os.path.exists(os.path.join(d, c[k])) or sha(os.path.join(d, c[k])) != c[k + '_sha256']]
        if bad:
            res['skipped'][c['id']] = 'registered file missing or changed: %s' % ','.join(bad); continue
        ex_files = {s: os.path.join(extra_dir, s + '.json') for s in sorted(c['extras'].values())}
        stale = [s for s, f in ex_files.items() if extra_stale(f, asof)]
        if stale:
            res['skipped'][c['id']] = 'extra input missing, unreadable or older than asof: %s' % ','.join(stale); continue
        iss = c['issued']                                       # the forecasts it issued so far: one file per run, never rewritten
        lost = [x['file'] for x in iss if not os.path.exists(os.path.join(d, x['file'])) or sha(os.path.join(d, x['file'])) != x['sha256']]
        if lost:
            res['skipped'][c['id']] = 'issued-forecast file missing or changed: %s' % ','.join(lost); continue
        out_dir = os.path.join(ch_root, c['id']); dg = os.path.join(out_dir, 'INPUTS.sha256'); fj = os.path.join(out_dir, 'ISSUED.json')
        shas = [x['sha256'] for x in iss]
        if os.path.exists(dg) and os.path.exists(fj) and open(dg).read().strip() == inputs_digest(c, d, pool_dir, rates_dir, extra_dir, asof, shas):
            frozen[c['id']] = json.load(open(fj))               # this asof was staged and frozen before, with the same inputs
        else:
            rel = 'challengers/%s.issued/%s_%03d.npz' % (c['id'], asof, len(iss) + 1)
            if os.path.exists(dg):                              # the staged files are about to change: the note that says
                os.remove(dg)                                   # "this folder is the frozen state of ..." goes first (R2-8)
            try:
                fm3_shadow.stage(path, pool_dir, rates_dir, extra_dir, asof, cache, out_dir,
                                 awake_from=None if c['kind'] == 'history' else c['t0'], jobs=jobs, cut_from=c['t0'])
                fz = fm3_shadow.freeze(out_dir, fm3_shadow.load_issued([os.path.join(d, x['file']) for x in iss]), c['t0'], asof, os.path.join(d, rel))
            except fm3_shadow.CutMismatch as ex:                # a look-ahead (or non-determinism): it is ended below (R2-4)
                mismatch[c['id']] = str(ex); res['skipped'][c['id']] = 'start-day check failed: %s' % ex; continue
            except Exception as ex:                             # a challenger that fails is skipped this week, never repaired here
                res['skipped'][c['id']] = 'stage error: %s: %s' % (type(ex).__name__, ex); continue
            if fz['file']:                                      # entered into the registry at the end of this run (commit)
                fz['file'] = rel; fz['sha256'] = sha(os.path.join(d, rel)); shas = shas + [fz['sha256']]
                new_issue[c['id']] = {'asof': asof, 'file': rel, 'sha256': fz['sha256'], 'rows': fz['new']}
            json.dump(fz, open(fj, 'w'))
            with open(dg, 'w') as f:                            # the digest of the state after this run's commit: a run that
                f.write(inputs_digest(c, d, pool_dir, rates_dir, extra_dir, asof, shas) + '\n')      # crashed before it is redone
            frozen[c['id']] = fz
        ch_dirs[c['id']] = out_dir; specs[c['id']] = {'t0': c['t0']}
    res['skip_streak'] = {cid: skip_streak(d, cid, asof) + 1 for cid in res['skipped']}
    res['report'] = ['%s was skipped %d runs in a row: %s' % (cid, k, res['skipped'][cid]) for cid, k in res['skip_streak'].items() if k >= SKIP_REPORT]
    res['report'] += ['%s was not scored in this run: %s' % (cid, why) for cid, why in res['skipped'].items()      # a failed computation
                      if why.startswith('stage error') and res['skip_streak'][cid] < SKIP_REPORT]                 # (a look-ahead too) is told at once
    res['report'] += ['%s: %d issued forecasts differ when recomputed (a data revision?); the scores use them as issued'
                      % (cid, fz['changed']) for cid, fz in frozen.items() if fz['changed']]
    res['report'] += ['%s: %d forecasts were not issued within %d days of their start day; they count as no forecast'
                      % (cid, fz['late'], fm3_shadow.ISSUE_MAX_DAYS) for cid, fz in frozen.items() if fz['late']]
    res['report'] += ['%s: %d issued forecasts have no row in today\'s grid (a past bar was added or removed); they are not scored'
                      % (cid, fz['orphans']) for cid, fz in frozen.items() if fz['orphans']]
    idx, data = fm3_shadow.load_shadow(cache, ch_dirs)
    q_now = quarter(asof)
    find_now = q_now > reg['last_judgement_quarter']                    # the first run after a quarter ended
    rows = {}
    for h in fm2.HORIZONS:
        F = fm2.prep(data[h])
        rows[h], R, R0 = fm3_shadow.score_horizon(F, specs)
        if h in JUDGED:
            chk = forward_check(F, R); res['forward_check'][str(h)] = chk
            if find_now:
                for fnd in open_findings(reg, h, chk, asof):
                    res['events'].append('finding opened: %s' % fnd['id']); evs.append({'event': 'finding_opened', 'id': fnd['id'], 'asof': asof, 'finding': fnd})
    judged_now = []
    ci_ok = (reg.get('interval_check') or {}).get('auto', {})      # horizons the run may judge: every recorded check passed
    first_look = ci_lengths()
    failed = sorted(h for h, v in ((reg.get('interval_check') or {}).get('auto') or {}).items() if not v and any(
        c['status'] == 'shadow' and c['h_status'].get(h) == 'shadow' for c in reg['challengers']))
    if failed:                                                      # a failed check is on record: told every week until a person decided
        res['report'].append('DECISION CARD NEEDED: the recorded check of the judgement interval does not allow an automatic judgement '
                             'for h=%s (a failed check is on record). Judgements of that horizon are held for a person (rule section 5)'
                             % ','.join(failed))

    def settle(c, h, st, row, note=None):                           # one horizon leaves the shadow
        c['h_status'][str(h)] = st
        res['events'].append('%s h=%d: %s' % (c['id'], h, st))
        evs.append({'event': 'judged', 'id': c['id'], 'h': h, 'status': st, 'asof': asof, 'row': row, **({'note': note} if note else {})})
        if st != 'pass_to_judge':
            rej.append(reject_line(c, asof, h, row, WHY.get(st, st) + (': ' + note if note else '')))
    for c in reg['challengers']:
        cid = c['id']
        if c['status'] != 'shadow':
            continue
        if cid in mismatch:                                         # it looked ahead (or is not deterministic): every horizon
            for h in c['judged_horizons']:                          # still in shadow ends, a held one too
                if c['h_status'][str(h)] == 'shadow':
                    settle(c, h, 'end_cut_mismatch', {}, mismatch[cid])
            res['report'].append('%s was ended: %s' % (cid, mismatch[cid]))
        elif cid in ch_dirs:
            res['challengers'][cid] = {str(h): shown(c, rows[h][cid]) for h in fm2.HORIZONS}
            res['challengers'][cid]['issued'] = frozen[cid]
            if cid in new_issue:
                c['issued'].append(new_issue[cid]); evs.append({'event': 'issued', 'id': cid, **new_issue[cid]})
            if q_now > c['judged_quarter']:                             # judged at its first scored run after a quarter ended
                c['judged_quarter'] = q_now; judged_now.append(cid)
                for h in c['judged_horizons']:
                    if c['h_status'][str(h)] != 'shadow' or str(h) in c['held']:
                        continue
                    row = rows[h][cid]['forward'][c['judged_pair'][str(h)]]
                    st = fm3_shadow.judge(row, h)
                    if st != 'shadow' and not ci_ok.get(str(h)):       # due, but the interval check does not allow it: the
                        c['held'][str(h)] = {'asof': asof, 'row': row}  # numbers are recorded now; a person decides (R2-7)
                        evs.append({'event': 'held', 'id': cid, 'h': h, 'asof': asof, 'row': row})
                    elif st != 'shadow':
                        settle(c, h, st, row)
            for h in c['judged_horizons']:                              # tell it early: the look is near and no check allows it
                w = rows[h][cid]['forward'][c['judged_pair'][str(h)]].get('weeks', 0)
                if c['h_status'][str(h)] == 'shadow' and str(h) not in c['held'] and not ci_ok.get(str(h)) and w >= first_look[h][0] - 26:
                    res['report'].append('%s h=%d: %d scored weeks, the first look is at %d. No check of the judgement interval allows an '
                                         'automatic judgement of this horizon yet: without it the judgement will be held for a person '
                                         '(rule section 5)' % (cid, h, w, first_look[h][0]))
        elif res['skip_streak'].get(cid, 0) >= SKIP_CLOSE:              # it cannot be scored any more: end it, free the slot
            for h in c['judged_horizons']:
                if c['h_status'][str(h)] == 'shadow':
                    c['h_status'][str(h)] = 'end_unscored'
                    evs.append({'event': 'judged', 'id': cid, 'h': h, 'status': 'end_unscored', 'asof': asof, 'row': {}})
                    rej.append(reject_line(c, asof, h, {}, '%d번 연속 채점하지 못해 끝냄: %s' % (res['skip_streak'][cid], res['skipped'][cid])))
            res['events'].append('%s ended: skipped %d runs in a row' % (cid, res['skip_streak'][cid]))
        evs += end_if_done(c, asof)
        for hk, held in c['held'].items():
            if c['h_status'][hk] == 'shadow':
                reads = fm3_shadow.judge(held['row'], int(hk))
                res['held'].append({'id': cid, 'h': int(hk), 'since': held['asof'], 'numbers_read': reads})
                res['report'].append('PERSON DECISION NEEDED: %s h=%s has a judgement held since %s (no check of the judgement interval '
                                     'allowed an automatic judgement on that day). The numbers of that day read "%s". No later check '
                                     'releases it (rule section 5); "close" records a person\'s decision to end the challenger'
                                     % (cid, hk, held['asof'], reads))
    if find_now:
        reg['last_judgement_quarter'] = q_now
    reg['last_run_asof'] = asof
    e, why = next_menu(reg, json.load(open(menu_path, encoding='utf-8')) if os.path.exists(menu_path) else [])
    res['findings_run'] = find_now; res['judged_now'] = judged_now; res['slots_used_after'] = slots_used(reg)
    res['awaiting_judge'] = [{'id': c['id'], 'h': int(h)} for c in reg['challengers'] if c['status'] in ('shadow', 'candidate')
                             for h, st in c['h_status'].items() if st == 'pass_to_judge']
    res['next_menu'] = e['menu_id'] if e else None; res['next_menu_note'] = why
    res['registry'] = [{k: c[k] for k in ('id', 'finding', 'status', 'h_status', 'judged_pair', 't0')} for c in reg['challengers']]
    evs.append({'event': 'run', 'asof': asof, 'quarter': q_now, 'findings_run': find_now, 'judged_now': judged_now,
                'scored': sorted(ch_dirs), 'skipped': res['skipped'], 'events': res['events'], 'held': res['held'],
                'code': res['code'], 'fm2_inputs_sha256': open(os.path.join(cache, 'INPUTS.sha256')).read().strip()})
    commit(d, reg, evs, rej)              # a crash before this line leaves the books as they were; after it, flush() finishes
    tmp = outp + '.tmp'                   # the appends. The result file comes after the books: a run that was refused or
    with open(tmp, 'w', encoding='utf-8') as f:      # crashed leaves no result that the books do not know (R2-9)
        json.dump(res, f, ensure_ascii=False, indent=1)
    os.replace(tmp, outp)
    print('asof', asof, '| scored', sorted(ch_dirs), '| skipped', res['skipped'], '| judged now', judged_now)
    for cid in sorted(ch_dirs):
        for h in fm2.HORIZONS:
            fw = rows[h][cid]['forward']['FM2']
            st = res['challengers'][cid][str(h)]['state']
            print(' %s h=%d forward weeks %s scored %s (by challenger %s) gain %s | share %s'
                  % (cid, h, fw.get('weeks', 0), fw['n_scored'], fw['n_scored_by_challenger'], fmt_gain(fw),
                     '%.3f' % st['om'] if isinstance(st, dict) else 'not shown'))
    print('events', res['events'], '| report', res['report'], '| awaiting judge', res['awaiting_judge'],
          '| next menu entry', res['next_menu'], '(%s)' % why)
    print('written', outp)
    return res


def selftest():
    import tempfile
    d = tempfile.mkdtemp(prefix='fm3w_selftest_')
    reg = cmd_init(d, today='2026-11-10')
    assert reg['last_judgement_quarter'] == '2026Q4' and quarter('2027-01-02') == '2027Q1' and len(reg['findings']) == 4
    assert FIND_WEEKS == {20: 104, 60: 208} and read_log(d)[0]['event'] == 'init' and load_reg(d)['display'] == {'20': 'FM2', '60': 'FM2'}
    src = '"""doc of %s"""\nID = \'%s\'\n\n\ndef quantiles(V, h):\n    return None\n'
    menu = []
    for k, (mid, fnd) in enumerate([('a', 'D1'), ('b', 'D1'), ('c', 'D1'), ('e', 'D2'), ('g', 'D3'), ('i', 'D4')]):
        p = os.path.join(d, 'menu', mid + '.py'); open(p, 'w').write(src % (mid, mid))
        menu.append({'menu_id': mid, 'module': mid + '.py', 'module_sha256': sha(p), 'finding': fnd, 'kind': 'history', 'judged_horizons': [20, 250]})
    json.dump(menu, open(os.path.join(d, 'menu', 'MENU.json'), 'w'))
    # stand-in input files and an fm2 cache that says it was built from them
    inp = os.path.join(d, '_inputs'); cache = os.path.join(d, '_cache'); os.makedirs(inp); os.makedirs(cache)
    for stem in [s for s, _, _ in fm2.UNIVERSE] + ['_TNX', '_IRX']:
        open(os.path.join(inp, stem + '.json'), 'w').write(stem)
    json.dump({'asof': '2026-11-13', 'assets': []}, open(os.path.join(cache, 'INDEX.json'), 'w'))
    assert 'INPUTS.sha256' in cache_note(cache, inp, inp, '2026-11-13')
    open(os.path.join(cache, 'INPUTS.sha256'), 'w').write(fm2_weekly.inputs_digest(inp, inp) + '\n')
    assert cache_note(cache, inp, inp, '2026-11-13') is None and 'asof' in cache_note(cache, inp, inp, '2026-11-20')
    ok = lambda *a: {'pass': True, 'tests': {'static': {'pass': True}, 'api': {'pass': True, 'extras': {}}, 'full_grid': {'pass': True}}}
    reg_ = lambda mid, **kw: cmd_register(d, mid, inp, inp, 'x', '2026-11-13', cache, today='2026-11-14', admit=ok, **kw)
    c1 = reg_('a')
    assert c1['id'] == 'c01_a' and c1['t0'] == '2026-11-15' and c1['judged_horizons'] == [20] and c1['attempt'] == 1
    assert c1['judged_pair'] == {'20': 'FM2'} and c1['held'] == {} and c1['issued'] == []
    pre = open(os.path.join(d, c1['prereg']), encoding='utf-8').read()
    assert sha(os.path.join(d, c1['module'])) == c1['module_sha256'] and 'doc of a' in pre and '20일 = FM2+ 대 FM2' in pre and '과거에서도 배운다' in pre
    for bad in ('a', 'e'):                                   # already used / not the next one in menu order
        try:
            reg_(bad); raise AssertionError('must be refused: ' + bad)
        except SystemExit:
            pass
    c2 = reg_('b'); assert c2['attempt'] == 2
    assert next_menu(load_reg(d), menu)[0]['menu_id'] == 'e'         # 'c' is skipped: finding D1 is at its limit of 2
    reg_('e')
    assert next_menu(load_reg(d), menu)[0] is None                    # three slots in use
    # a person closes one: its slot is free, the reason is in both records, and it cannot be closed twice
    n_rej0 = len(open(os.path.join(d, 'REJECTED.md'), encoding='utf-8').read().splitlines())
    for args in (('c01_a', 'short'), ('c09_x', 'decided by the owner on 2029-01-05: stop')):
        try:
            cmd_close(d, *args); raise AssertionError('must be refused')
        except SystemExit:
            pass
    cmd_close(d, 'c01_a', '사장 결정 2029-01-05: 편입 안 함 | 시험')
    last = open(os.path.join(d, 'REJECTED.md'), encoding='utf-8').read().splitlines()[-1]
    assert load_reg(d)['challengers'][0]['status'] == 'closed' and read_log(d)[-1]['by'] == 'person' and '사람이 닫음' in last and last.count('|') == 9
    assert len(open(os.path.join(d, 'REJECTED.md'), encoding='utf-8').read().splitlines()) == n_rej0 + 1
    try:
        cmd_close(d, 'c01_a', '사장 결정 2029-01-06: 다시 닫기'); raise AssertionError('must be refused')
    except SystemExit:
        pass
    assert next_menu(load_reg(d), menu)[0]['menu_id'] == 'g'          # a slot is free again
    try:                                                               # a changed menu module is refused
        open(os.path.join(d, 'menu', 'g.py'), 'a').write('\n'); reg_('g'); raise AssertionError('must be refused')
    except SystemExit:
        pass
    menu[4]['module_sha256'] = sha(os.path.join(d, 'menu', 'g.py')); json.dump(menu, open(os.path.join(d, 'menu', 'MENU.json'), 'w'))
    for bad_admit in (lambda *a: {'pass': False, 'tests': {'static': {'pass': False}}},          # a failed admission, and one without the
                      lambda *a: {'pass': True, 'tests': {'static': {'pass': True}}}):           # full-grid run, register nothing and are logged
        try:
            cmd_register(d, 'g', inp, inp, 'x', '2026-11-13', cache, today='2026-11-14', admit=bad_admit)
            raise AssertionError('must be refused')
        except SystemExit:
            pass
        assert read_log(d)[-1]['event'] == 'admission_failed'
    try:                                                               # an fm2 cache of other input files is refused
        open(os.path.join(inp, 'XLE.json'), 'a').write('x'); reg_('g'); raise AssertionError('must be refused')
    except SystemExit as ex:
        assert 'not built from these input files' in str(ex)
    open(os.path.join(inp, 'XLE.json'), 'w').write('XLE')
    assert len(load_reg(d)['challengers']) == 3 and [ev['seq'] for ev in read_log(d)] == list(range(1, len(read_log(d)) + 1))
    assert len(read_log(d)) >= 7 and load_reg(d)['outbox'] == {} and os.path.exists(os.path.join(d, 'challengers', 'c01_a.admission.json'))
    # findings opened by the forward record: after the minimum sample of the horizon
    r = load_reg(d)
    assert open_findings(r, 20, {'weeks': 60, 'cov80': 0.5, 'above_q90': 0.4, 'below_q10': 0.1}, '2027-12-31') == []
    assert open_findings(r, 60, {'weeks': 150, 'cov80': 0.5, 'above_q90': 0.4, 'below_q10': 0.1}, '2029-12-31') == []
    assert [f['id'] for f in open_findings(r, 20, {'weeks': 104, 'cov80': 0.74, 'above_q90': 0.21, 'below_q10': 0.05}, '2028-12-31')] == ['F-upper-20']
    assert [f['id'] for f in open_findings(r, 20, {'weeks': 110, 'cov80': 0.65, 'above_q90': 0.25, 'below_q10': 0.10}, '2029-03-31')] == ['F-width-20']
    assert fmt_gain({'gain': 0.0123, 'gain_ci95': [-0.001, 0.02]}) == '+1.23% (-0.10 ~ +2.00%)' and fmt_gain({}) == '채점 없음'
    r = load_reg(d)
    run_ev = lambda asof, sk: {'event': 'run', 'asof': asof, 'quarter': quarter(asof), 'findings_run': False, 'judged_now': [], 'skipped': sk}
    for k, sk in enumerate(({}, {'c02_b': 'x'}, {'c02_b': 'x'}, {'c02_b': 'x', 'c03_e': 'y'}, {'c02_b': 'x', 'c03_e': 'y'})):
        r['last_run_asof'] = '2030-01-%02d' % min(k + 1, 4); commit(d, r, [run_ev(r['last_run_asof'], sk)])     # the last asof is run twice
    assert skip_streak(d, 'c02_b', '2030-02-01') == 3 and skip_streak(d, 'c03_e', '2030-02-01') == 1 and skip_streak(d, 'c01_a', '2030-02-01') == 0
    assert skip_streak(d, 'c02_b', '2030-01-04') == 2                # an earlier run of the same asof does not count
    try:                                                               # init never overwrites existing books
        cmd_init(d); raise AssertionError('must be refused')
    except SystemExit:
        pass
    # the check of the judgement interval: recorded with a copy of the report; every judged horizon at every sample size it
    # is judged at; a horizon passes when all its values are CI_COVER_MIN or more
    assert load_reg(d)['interval_check'] is None and ci_lengths() == {20: [65, 104], 60: [208]}
    rp = os.path.join(d, 'chk.json'); json.dump({'method': 'test', 'coverage': {'20': {'65': 0.94, '104': 0.95}, '60': {'208': 0.92}}}, open(rp, 'w'))
    ic = cmd_interval_check(d, rp)
    assert ic['pass'] == {'20': True, '60': False} == ic['auto'] and sha(os.path.join(d, ic['file'])) == ic['sha256'] and read_log(d)[-1]['event'] == 'interval_check'
    for bad in ({'250': 0.99}, {'20': 0.99, '60': 0.99}, {'20': {'65': 0.99, '104': 0.99}}, {'20': {'65': 0.99}, '60': {'208': 0.99}},
                {'20': {'65': 0.99, '104': 1.2}, '60': {'208': 0.99}}, {'20': {'65': 0.99, '104': float('nan')}, '60': {'208': 0.99}},
                {'20': {'65': True, '104': True}, '60': {'208': True}}):
        json.dump({'coverage': bad}, open(rp, 'w'))                   # a horizon or a sample size left out, or not a rate: not recorded
        try:
            cmd_interval_check(d, rp); raise AssertionError('must be refused')
        except SystemExit:
            pass
    assert load_reg(d)['interval_check']['file'] == ic['file']
    # a pass recorded after a failed check does not bring automatic judgement back, and a later failure takes it away (R2-7)
    json.dump({'coverage': {'20': {'65': 0.94, '104': 0.92}, '60': {'208': 0.99}}}, open(rp, 'w')); ic = cmd_interval_check(d, rp)
    assert ic['pass'] == {'20': False, '60': True} and ic['auto'] == {'20': False, '60': False}
    json.dump({'coverage': {'20': {'65': 0.99, '104': 0.99}, '60': {'208': 0.99}}}, open(rp, 'w')); ic = cmd_interval_check(d, rp)
    assert ic['pass'] == {'20': True, '60': True} and ic['auto'] == {'20': False, '60': False} and ic['n'] == 3
    full = {'forward': {'FM2': {'weeks': 3, 'om_mean': 0.2}, 'F0': {'weeks': 3, 'om_mean': 0.2}}, 'state': {'om': 0.2, 'om_by_learner': [0.2]}}
    hid = shown({'kind': 'history'}, full)                           # the share of a history-backed challenger is not shown (R2-2)
    assert shown({'kind': 'forward'}, full) is full and 'om' not in json.dumps(hid) and hid['forward']['FM2'] == {'weeks': 3}
    assert extra_stale(os.path.join(d, 'none.json'), '2026-11-13') and extra_stale(os.path.join(inp, 'XLE.json'), '2026-11-13')
    # a crash between saving the registry and appending: the next flush writes each owed line once; a torn line is closed
    n_log = len(read_log(d)); n_rej = len(open(os.path.join(d, 'REJECTED.md'), encoding='utf-8').read().splitlines())
    r = load_reg(d); r['log_seq'] += 1; r['last_run_asof'] = '2030-01-05'
    r['outbox'] = {'log': [dict(run_ev('2030-01-05', {}), at='x', seq=r['log_seq'])], 'rejected': ['| crash | test |\n']}
    save_reg(d, r)
    with open(os.path.join(d, 'LOG.jsonl'), 'a', encoding='utf-8') as fh:
        fh.write('{"at": "torn')
    for _ in range(2):
        r = open_books(d)
    assert len(read_log(d)) == n_log + 1 and read_log(d)[-1]['asof'] == '2030-01-05' and load_reg(d)['outbox'] == {}
    assert len(open(os.path.join(d, 'REJECTED.md'), encoding='utf-8').read().splitlines()) == n_rej + 1
    r = load_reg(d); r['outbox'] = {'log': [read_log(d)[-1]], 'rejected': ['| crash | test |\n']}; save_reg(d, r); open_books(d)
    assert len(read_log(d)) == n_log + 1 and len(open(os.path.join(d, 'REJECTED.md'), encoding='utf-8').read().splitlines()) == n_rej + 1
    # two commands at once (R2-5): the one that read the books before the other wrote stops before it writes anything
    slow = open_books(d); other = open_books(d)
    other['last_run_asof'] = '2030-01-06'; commit(d, other, [run_ev('2030-01-06', {})])
    n_log = len(read_log(d)); slow['last_run_asof'] = '2030-01-07'
    try:
        commit(d, slow, [run_ev('2030-01-07', {})]); raise AssertionError('must stop')
    except SystemExit as ex:
        assert 'books stopped' in str(ex)
    assert len(read_log(d)) == n_log and load_reg(d)['last_run_asof'] == '2030-01-06' and open_books(d)['outbox'] == {}
    # an owed line whose number another line has taken stops every command; rebuild drops it (and prints it)
    r = load_reg(d); r['outbox'] = {'log': [dict(run_ev('2030-01-08', {}), at='x', seq=n_log)], 'rejected': []}; save_reg(d, r)
    try:
        open_books(d); raise AssertionError('must stop')
    except SystemExit as ex:
        assert 'books stopped' in str(ex)
    try:                                                       # the same stop inside a commit says that the registry was saved (R3-2)
        flush(d, load_reg(d), saved=True); raise AssertionError('must stop')
    except SystemExit as ex:
        assert 'books stopped' in str(ex) and 'already saved' in str(ex) and 'wrote nothing' not in str(ex)
    assert cmd_rebuild(d)['last_run_asof'] == '2030-01-06' and len(read_log(d)) == n_log and open_books(d)['outbox'] == {}
    # owed lines that cannot be read: every command is refused with a message, and rebuild leaves them out (R3-3)
    for bad_ob in ({'log': [{'event': 'run'}], 'rejected': []}, ['x'], {'log': 5}, {'log': [], 'rejected': 5}):
        r = load_reg(d); r['outbox'] = bad_ob; save_reg(d, r)
        try:
            open_books(d); raise AssertionError('must be refused')
        except SystemExit as ex:
            assert 'books refused' in str(ex), ex
        assert cmd_rebuild(d)['last_run_asof'] == '2030-01-06' and len(read_log(d)) == n_log and open_books(d)['outbox'] == {}
    # a challenger that the start-day check ended is never a candidate, whatever another horizon read before (R3-1)
    cx = {'id': 'x', 'status': 'shadow', 'h_status': {'20': 'pass_to_judge', '60': 'end_cut_mismatch'}}
    assert end_if_done(cx, '2030-01-06')[0]['status'] == 'ended' == cx['status']
    cx = {'id': 'x', 'status': 'shadow', 'h_status': {'20': 'pass_to_judge', '60': 'end_inconclusive'}}
    assert end_if_done(cx, '2030-01-06')[0]['status'] == 'candidate' == cx['status']
    cx = {'id': 'x', 'status': 'shadow', 'h_status': {'20': 'pass_to_judge', '60': 'shadow'}}
    assert end_if_done(cx, '2030-01-06') == [] and cx['status'] == 'shadow'
    # rebuild after a crash in the middle of a commit: the owed lines are appended first, not lost (R2-9)
    r = load_reg(d); r['log_seq'] += 1; r['last_run_asof'] = '2030-01-09'
    r['outbox'] = {'log': [dict(run_ev('2030-01-09', {}), at='x', seq=r['log_seq'])], 'rejected': ['| crash 2 | test |\n']}; save_reg(d, r)
    assert cmd_rebuild(d)['last_run_asof'] == '2030-01-09' and len(read_log(d)) == n_log + 1
    assert '| crash 2 | test |' in open(os.path.join(d, 'REJECTED.md'), encoding='utf-8').read()
    # init that crashes after it saved the registry is finished by the next command; one that crashes before leaves nothing
    d2 = tempfile.mkdtemp(prefix='fm3w_selftest_'); g = globals(); real = g['_append']

    def boom(path, text):
        raise RuntimeError('simulated crash')
    g['_append'] = boom
    try:
        cmd_init(d2, today='2026-11-10'); raise AssertionError('must crash')
    except RuntimeError:
        pass
    g['_append'] = real
    assert not os.path.exists(os.path.join(d2, 'REJECTED.md')) and not os.path.exists(os.path.join(d2, 'LOG.jsonl'))
    assert open_books(d2)['log_seq'] == 1 and read_log(d2)[0]['event'] == 'init'
    assert open(os.path.join(d2, 'REJECTED.md'), encoding='utf-8').read() == REJECTED_HEAD
    try:
        cmd_init(d2); raise AssertionError('must be refused')
    except SystemExit:
        pass
    shutil.rmtree(d2)
    # the registry is what the log tells: a registry edited by hand stops every command, and rebuild restores it
    good = load_reg(d)
    for edit in (lambda r: r['challengers'][1].update(t0='2026-11-01'), lambda r: r['challengers'][1].update(status='ended'),
                 lambda r: r['challengers'][1]['judged_pair'].update({'20': 'F0'}), lambda r: r['display'].update({'20': 'F0'}),
                 lambda r: r['findings'][0]['challenges'].pop(), lambda r: r.update(last_run_asof='2029-01-01'),
                 lambda r: r['challengers'][0].update(status='shadow'), lambda r: r['interval_check']['auto'].update({'60': True}),
                 lambda r: r['challengers'][2].update(judged_quarter='2020Q1')):
        r = load_reg(d); edit(r); save_reg(d, r)
        for cmd in (lambda: open_books(d), lambda: reg_('g'), lambda: cmd_close(d, 'c02_b', 'decided by the owner: stop it')):
            try:
                cmd(); raise AssertionError('an edited registry must be refused')
            except SystemExit as ex:
                assert 'books refused' in str(ex), ex
        assert cmd_rebuild(d) == good == load_reg(d)
    lp = os.path.join(d, 'LOG.jsonl'); lines = open(lp, encoding='utf-8').read().splitlines(True)
    open(lp, 'w', encoding='utf-8').write(''.join(lines[:3] + lines[4:]))                          # a log with a missing line is refused too
    for cmd in (lambda: open_books(d), lambda: cmd_rebuild(d)):
        try:
            cmd(); raise AssertionError('a damaged log must be refused')
        except SystemExit:
            pass
    open(lp, 'w', encoding='utf-8').write(''.join(lines)); open_books(d)
    # an entry without a judged horizon is refused
    json.dump([dict(menu[4], judged_horizons=[250])], open(os.path.join(d, 'menu', 'MENU.json'), 'w'))
    try:
        reg_('g'); raise AssertionError('must be refused')
    except SystemExit as ex:
        assert 'no judged horizon' in str(ex)
    assert len(load_reg(d)['challengers']) == 3
    # a lost REJECTED.md is made again with its head, and that is said (R3-4)
    os.remove(os.path.join(d, 'REJECTED.md')); open_books(d)
    assert open(os.path.join(d, 'REJECTED.md'), encoding='utf-8').read() == REJECTED_HEAD
    shutil.rmtree(d)
    print('selftest OK')


if __name__ == '__main__':
    cmd = sys.argv[1]
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 1
    if cmd == 'selftest':
        selftest()
    elif cmd == 'init':
        cmd_init(sys.argv[2]); print('created', os.path.join(sys.argv[2], 'REGISTRY.json'))
    elif cmd == 'verify':
        open_books(sys.argv[2]); print('books OK: REGISTRY.json is what LOG.jsonl tells (%d events)' % len(read_log(sys.argv[2])))
    elif cmd == 'rebuild':
        cmd_rebuild(sys.argv[2]); print('rebuilt', os.path.join(sys.argv[2], 'REGISTRY.json'), 'from', len(read_log(sys.argv[2])), 'events')
    elif cmd == 'interval-check':
        print(json.dumps(cmd_interval_check(sys.argv[2], sys.argv[3]), ensure_ascii=False))
    elif cmd == 'next':
        e, why = next_menu(open_books(sys.argv[2]), json.load(open(os.path.join(sys.argv[2], 'menu', 'MENU.json'), encoding='utf-8')))
        print(json.dumps({'next_menu': e['menu_id'] if e else None, 'note': why}))
    elif cmd == 'register':
        c = cmd_register(*sys.argv[2:9], jobs=jobs)
        print(json.dumps({k: c[k] for k in ('id', 'finding', 'attempt', 'module_sha256', 'prereg_sha256', 't0', 'judged_pair', 'status')}, ensure_ascii=False))
    elif cmd == 'run':
        cmd_run(*sys.argv[2:10], jobs=jobs)
    elif cmd == 'close':
        c = cmd_close(sys.argv[2], sys.argv[3], sys.argv[4]); print(json.dumps({k: c[k] for k in ('id', 'status')}))
