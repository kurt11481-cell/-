#!/usr/bin/env python3
"""FM-2 layer 3: end-to-end test of the books on a synthetic world (no real data, no network; its scores mean nothing).

The unit self-tests (fm3_shadow.py selftest, fm3_weekly.py selftest) cover the maths and the single commands.
This test covers what they cannot: the whole path  init -> register (the real admission, in its own interpreters,
with the full-grid run) -> weekly run -> judgement -> REJECTED.md / LOG.jsonl, with the sample limits shortened
(in memory only) so that judgements happen.
  - a challenger whose derive() uses the whole file is refused by the admission (look-ahead) and is not registered
  - no table of scores over the past exists anywhere; only forecasts that start on or after T0 are scored; the share
    a history-backed challenger earned (the past score in another unit) is not in the weekly result
  - a repeated run of the same week changes nothing
  - a changed challenger file, a stale extra input and a changed issued-forecast file are skipped; the skipped
    challenger is judged at its next scored run; one that stays skipped is ended and its slot freed
  - forecasts are scored as first issued: a later change of the inputs changes the recomputed forecasts, is
    counted and reported, and does not change the scored ones; a forecast that was not issued within
    ISSUE_MAX_DAYS of its start day counts as "no forecast"; new forecasts come from inputs cut at their start day
  - a judgement that is due while no check of the judgement interval allows it is held: its numbers are recorded
    that day and it waits for a person. A pass recorded after a failed check releases nothing
  - a challenger whose new forecasts differ between inputs cut at the start day and inputs cut at asof is ended at
    once, its held horizon too
  - one horizon can end while the other goes on; a challenger that passes becomes a candidate, keeps its slot
    and stays listed under awaiting_judge until a person closes it
  - a person's decision ('close') ends a challenger and frees its slot; the reason is in both records
  - a crash before the books are saved leaves nothing behind that the next run does not redo; a crash between
    saving the registry and appending the log is finished by the next run, each line once
  - a run with an older asof is refused
  - a status never moves back; every ended horizon has exactly one REJECTED line; LOG numbers are 1..N; the
    registry is what the log tells; every issued-forecast file is in the registry with its hash
Three branches that chance would decide (an interim drop, a pass, staying in shadow) are reached by overwriting
the interval of one row in memory (see `forced`); everything else is computed. That a truly better challenger
passes on its own numbers is tested in fm3_shadow.py selftest (3). The first run comes more than a year after the
registrations (the year in between stands in for a forward record), so ISSUE_MAX_DAYS is lifted for that one run.

Run it after any change of fm3_shadow.py or fm3_weekly.py.
usage: python3 -I -B fm3_itest.py [<work_dir>]        (a few minutes; ends with 'itest OK')
"""
import sys, os, json, math, datetime, tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fm2, fm2_weekly, fm3_shadow, fm3_weekly

STEMS = ['XLE', '_N225', 'NVDA']                   # the three assets with a synthetic history of their own and an fm2 cache
WIDE_SRC = '''"""itest challenger: the one-year normal range made 1.6 times wider."""
import math
ID = 'wide'


def quantiles(V, h):
    sd = float(V.s252[V.i]) * math.sqrt(h)
    if not (sd > 0):
        return None
    return 1.6 * V.ZQ * sd
'''
BAD_SRC = '''"""itest challenger: a biased range that is too narrow."""
import math
ID = 'badfwd'


def quantiles(V, h):
    sd = float(V.s252[V.i]) * math.sqrt(h)
    if not (sd > 0):
        return None
    return (1.5 + 0.6 * V.ZQ) * sd
'''
EXT_SRC = '''"""itest challenger: reads an extra series that (in the synthetic world only) holds the coming 20-day width."""
import math
import numpy as np
ID = 'ext'
EXTRAS = {'E': '_E'}
EXTRA_LAG = 1


def quantiles(V, h):
    e = V.x('E')[V.i]
    if not (np.isfinite(e) and e > 0):
        return None
    return V.ZQ * e * math.sqrt(h)
'''
PEEK_SRC = '''"""itest challenger with a look-ahead: derive() divides by the mean of the whole file."""
import math
import numpy as np
ID = 'peek'
EXTRAS = {'E': '_E'}


def derive(raw):
    d, v = raw['E']
    return {'E': (d, v / np.mean(v))}


def quantiles(V, h):
    e = V.x('E')[V.i]
    if not (np.isfinite(e) and e > 0):
        return None
    return V.ZQ * V.s252[V.i] * math.sqrt(h) * e
'''
RUNS = ['2008-03-21', '2008-03-28', '2008-04-04', '2008-04-11', '2008-07-04', '2008-07-11', '2008-07-18', '2008-07-25']
#       2008Q1        Q1            Q2            Q2            Q3            Q3            Q3            Q3


def yj(path, days, vals):
    ts = [int(datetime.datetime.fromisoformat(x + 'T12:00:00+00:00').timestamp()) for x in days]
    json.dump({'chart': {'result': [{'timestamp': ts, 'indicators': {'quote': [{'close': [float(z) for z in vals]}]}}]}}, open(path, 'w'))


def build_world(work, rng):
    days = []; d = datetime.date(2000, 1, 3)
    while d <= datetime.date(2008, 12, 31):
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += datetime.timedelta(days=1)
    n = len(days); sig = np.empty(n); k = 0
    while k < n:                                      # one market-wide daily volatility that jumps between three levels
        ln = int(rng.integers(40, 121)); sig[k:k + ln] = rng.choice([0.006, 0.012, 0.024]); k += ln
    dirs = {k: os.path.join(work, k) for k in ('pool', 'rates', 'extra_ok', 'extra_stale')}
    for p in dirs.values():
        os.makedirs(p, exist_ok=True)
    series = {s: 100 * np.exp(np.cumsum(0.0002 + sig * rng.standard_normal(n))) for s in STEMS}
    for s, _, _ in fm2.UNIVERSE:                      # all 20 pool files exist; 17 are stand-ins without an fm2 cache
        yj(os.path.join(dirs['pool'], s + '.json'), days, series.get(s, series[STEMS[0]]))
    yj(os.path.join(dirs['rates'], '_TNX.json'), days, 5 + 0.3 * np.sin(np.arange(n) / 200.0))
    yj(os.path.join(dirs['rates'], '_IRX.json'), days, np.full(n, 3.0))
    cs = np.cumsum(np.r_[0.0, sig ** 2])              # e[t] = root mean square of sig over days t+2 .. t+21 (the oracle)
    e = np.array([math.sqrt((cs[min(t + 22, n)] - cs[min(t + 2, n)]) / max(min(t + 22, n) - min(t + 2, n), 1)) if t + 2 < n else sig[-1]
                  for t in range(n)])
    yj(os.path.join(dirs['extra_ok'], '_E.json'), days, e)
    cut = [k for k, x in enumerate(days) if x <= RUNS[1]]
    yj(os.path.join(dirs['extra_stale'], '_E.json'), [days[k] for k in cut], e[cut])
    return dirs, days, series


def build_cache(dirs, asof, cache):
    """What fm2_weekly.py leaves behind for one asof: the expert cache of the three assets and the hash of its inputs."""
    os.makedirs(cache, exist_ok=True)
    meta = {s: (c, l) for s, c, l in fm2.UNIVERSE}
    args = [(s, meta[s][0], meta[s][1], dirs['pool'], dirs['rates'], asof, cache) for s in STEMS]
    import multiprocessing as mp
    with mp.get_context('fork').Pool(len(STEMS)) as p:
        infos = p.map(fm2._one, args, chunksize=1)
    json.dump({'asof': asof, 'assets': infos}, open(os.path.join(cache, 'INDEX.json'), 'w'), indent=1)
    open(os.path.join(cache, 'INPUTS.sha256'), 'w').write(fm2_weekly.inputs_digest(dirs['pool'], dirs['rates']) + '\n')


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix='fm3_itest_')
    os.makedirs(work, exist_ok=True)
    S, W = fm3_shadow, fm3_weekly
    S.FORWARD_START = '2006-07-03'; S.MIN_WEEKS = {20: 65, 60: 60}                                  # in memory only
    S.CI_WEEKS = {20: 20, 60: 20, 250: 10 ** 6}; S.FUT_WEEKS = {20: 20, 60: 20}; W.FIND_WEEKS = {20: 40, 60: 40}
    issue_days = S.ISSUE_MAX_DAYS
    forced = {}                                       # (challenger, horizon) -> fields overwritten in both pairs of its forward row
    real_score = S.score_horizon

    def score_with_forced(F, specs):                  # lets the test reach branches that chance would decide
        out, R, R0 = real_score(F, specs)
        assert all(set(v) == {'forward', 'state'} for v in out.values())          # nothing but the judged window is scored
        for (cid, h), patch in forced.items():
            if cid in out and h == F['h_val']:
                for pair in out[cid]['forward'].values():
                    pair.update(patch)
        return out, R, R0
    S.score_horizon = score_with_forced
    dirs, days, series = build_world(work, np.random.default_rng(7))
    L = os.path.join(work, 'layer3')
    os.makedirs(L)
    W.cmd_init(L, today='2006-12-29')
    chk = os.path.join(work, 'interval_check.json')    # the check of the judgement interval: at first passed for 20 days only

    def record_check(v20, v60):                        # one value per sample size the (shortened) rule judges at
        cov = {str(h): {str(n): v for n in W.ci_lengths()[h]} for h, v in ((20, v20), (60, v60))}
        json.dump({'method': 'itest', 'coverage': cov}, open(chk, 'w'))
        return W.cmd_interval_check(L, chk)
    assert W.ci_lengths() == {20: [20, 65], 60: [20, 60]}
    ic = record_check(0.95, 0.90)
    assert ic['pass'] == {'20': True, '60': False} == ic['auto']
    menu = []
    for mid, src, fnd, kind, jh in (('dup', S.GOOD_SRC.replace("ID = 'm1view'", "ID = 'dup'"), 'D1', 'history', [20, 60]),
                                    ('wide', WIDE_SRC, 'D1', 'history', [20]), ('ext', EXT_SRC, 'D2', 'forward', [20]),
                                    ('badfwd', BAD_SRC, 'D3', 'forward', [20]), ('peek', PEEK_SRC, 'D4', 'forward', [20])):
        p = os.path.join(L, 'menu', mid + '.py'); open(p, 'w').write(src)
        menu.append({'menu_id': mid, 'module': mid + '.py', 'module_sha256': W.sha(p), 'finding': fnd, 'kind': kind, 'judged_horizons': jh})
    json.dump(menu, open(os.path.join(L, 'menu', 'MENU.json'), 'w'), indent=1)

    def cache_of(asof, tag=''):
        cache = os.path.join(work, 'cache_' + asof + tag)
        if not os.path.exists(os.path.join(cache, 'INDEX.json')):
            build_cache(dirs, asof, cache)
        return cache
    register = lambda mid, asof, today: W.cmd_register(L, mid, dirs['pool'], dirs['rates'], dirs['extra_ok'], asof, cache_of(asof),
                                                       today=today, jobs=3)['id']
    dup, wide, ext = [register(mid, '2007-01-05', '2007-01-05') for mid in ('dup', 'wide', 'ext')]
    reg = W.load_reg(L)
    assert [c['t0'] for c in reg['challengers']] == ['2007-01-06'] * 3 and W.next_menu(reg, menu)[0] is None      # three slots in use
    assert reg['challengers'][2]['extra_lag'] == 1 and '전날' in open(os.path.join(L, reg['challengers'][2]['prereg']), encoding='utf-8').read()
    adm = json.load(open(os.path.join(L, reg['challengers'][0]['admission'])))                 # the real admission: all 20 assets, two processes
    assert set(adm['tests']) == {'static', 'api', 'valid_output', 'deterministic', 'no_lookahead', 'runtime', 'units', 'full_grid'}
    assert adm['tests']['valid_output']['calls'] == 20 * S.ADMIT_POINTS * 3 and adm['tests']['no_lookahead']['cut_points'] == 20 * 5 * 3
    assert adm['tests']['full_grid']['rows'] > 300 and adm['tests']['deterministic']['rows_that_differ_in_another_process'] == 0
    rej_lines = lambda: [l for l in open(os.path.join(L, 'REJECTED.md'), encoding='utf-8').read().splitlines() if l.startswith('| c')]
    get = lambda cid: next(c for c in W.load_reg(L)['challengers'] if c['id'] == cid)
    status = lambda: {c['id']: (c['status'], dict(c['h_status'])) for c in W.load_reg(L)['challengers']}
    n_events = lambda name: sum(ev.get('event') == name for ev in W.read_log(L))
    order = ['shadow', 'candidate', 'ended', 'closed']

    def run(asof, extra='extra_ok', tag='', ctag=''):
        before = status()
        res = W.cmd_run(L, dirs['pool'], dirs['rates'], dirs[extra], asof, cache_of(asof, ctag), os.path.join(work, 'ch'),
                        os.path.join(L, 'runs', 'shadow_%s%s.json' % (asof, tag)))
        after = status()
        for cid, (st, hs) in before.items():          # a status only moves forward
            assert order.index(after[cid][0]) >= order.index(st) and (st, after[cid][0]) != ('ended', 'closed'), (cid, st, after[cid])
            assert all(v == after[cid][1][h] or v == 'shadow' for h, v in hs.items()), (cid, hs, after[cid])
        for cid in res['judged_now']:                 # the recorded status is what judge() says about the pair fixed at registration
            c = get(cid)
            for h in c['judged_horizons']:
                if before[cid][1][str(h)] == 'shadow' and str(h) not in c['held']:
                    assert after[cid][1][str(h)] == S.judge(res['challengers'][cid][str(h)]['forward'][c['judged_pair'][str(h)]], h), (cid, h)
        for cid, c in res['challengers'].items():     # the counts of the issued forecasts add up; no score but the forward one exists
            z = c['issued']; assert z['rows'] == z['kept'] + z['new'] and z['changed'] <= z['kept'] and z['late'] <= z['new_no_forecast'] <= z['new'], z
            assert z['orphans'] == 0 and all(set(c[str(h)]) == {'forward', 'state'} for h in fm2.HORIZONS)
            for h in fm2.HORIZONS:                    # the share is shown for a forward-only challenger and never for a history-backed one
                if get(cid)['kind'] == 'history':
                    assert isinstance(c[str(h)]['state'], str) and '"om' not in json.dumps(c[str(h)]), (cid, h)
                else:
                    assert 0.0 <= c[str(h)]['state']['om'] <= 1.0 and len(c[str(h)]['state']['om_by_learner']) == 10, (cid, h)
        assert 'replay' not in json.dumps(res)
        return res

    # run 1: the first scored run after the registration quarter: every challenger is looked at; 'wide' is kept in shadow (forced)
    forced[(wide, 20)] = {'gain_ci95': [-0.01, 0.01]}
    S.ISSUE_MAX_DAYS = 10 ** 4                         # this run only: the year since the registrations stands in for a forward record
    r1 = run(RUNS[0])
    S.ISSUE_MAX_DAYS = issue_days
    del forced[(wide, 20)]
    assert r1['findings_run'] and sorted(r1['challengers']) == sorted([dup, wide, ext]) and sorted(r1['judged_now']) == sorted([dup, wide, ext])
    assert status()[wide] == ('shadow', {'20': 'shadow'}) and status()[dup][0] == 'shadow' and len(rej_lines()) == 0
    fw = r1['challengers'][ext]['20']['forward']['FM2']
    assert fw['first_start'] >= '2007-01-06' and fw['n_scored'] == fw['n_scored_by_challenger'] > 100
    assert r1['challengers'][dup]['20']['forward']['FM2']['first_start'] >= '2007-01-06'            # history-backed too: nothing before T0
    # every forecast of the judged window was issued in this run, from inputs cut at its own start day: one file per challenger
    z = r1['challengers'][ext]['issued']
    assert z['new'] == z['rows'] > 300 and z['kept'] == z['late'] == z['changed'] == 0 and n_events('issued') == 3
    for cid in (dup, wide, ext):
        (e,) = get(cid)['issued']
        assert e['asof'] == RUNS[0] and e['rows'] > 300 and W.sha(os.path.join(L, e['file'])) == e['sha256']
        ix = json.load(open(os.path.join(work, 'ch', cid, 'INDEX.json')))
        assert ix['cut_rows'] == e['rows'] and ix['cut_diff'] == 0 and ix['cut_from'] == '2007-01-06'
    # a person's decision ends 'wide': its slot goes to the next menu entry, which starts the day after its registration
    assert r1['next_menu'] is None
    W.cmd_close(L, wide, '사장 결정(시험) 2008-03-22: 그만 잰다')
    assert status()[wide][0] == 'closed' and len(rej_lines()) == 1 and '사람이 닫음' in rej_lines()[0] and W.next_menu(W.load_reg(L), menu)[0]['menu_id'] == 'badfwd'
    bad = register('badfwd', RUNS[0], '2008-03-22')
    assert get(bad)['t0'] == '2008-03-23' and get(bad)['judged_quarter'] == '2008Q1' and get(bad)['issued'] == [] and get(bad)['judged_pair'] == {'20': 'FM2'}
    # the same week again: no judgement, no new REJECTED line, nothing issued, one more 'run' line
    snap = (status(), rej_lines(), len(W.read_log(L)))
    r1b = run(RUNS[0], tag='_again')
    assert r1b['judged_now'] == [] and (status(), rej_lines(), len(W.read_log(L)) - 1) == snap and wide not in r1b['challengers']
    for key in ('forward', 'state'):
        assert json.dumps(r1b['challengers'][dup]['20'][key], sort_keys=True) == json.dumps(r1['challengers'][dup]['20'][key], sort_keys=True)
    assert r1b['challengers'][dup]['issued'] == r1['challengers'][dup]['issued']
    assert r1b['challengers'][bad]['20']['forward']['FM2']['n_scored'] == 0 and r1b['challengers'][bad]['issued']['rows'] == 0
    # run 2: a changed module file and a changed issued-forecast file are skipped, not repaired
    vp = os.path.join(L, get(dup)['module']); orig = open(vp, 'rb').read(); open(vp, 'ab').write(b'\n')
    ep = os.path.join(L, get(ext)['issued'][0]['file']); eorig = open(ep, 'rb').read(); open(ep, 'ab').write(b'x')
    # ... and a crash before the books are saved: the forecasts 'badfwd' issued are on disk but in no book; the next run redoes them
    real_commit = W.commit

    def boom_commit(*a, **k):
        raise RuntimeError('simulated crash before the books are saved')
    W.commit = boom_commit
    try:
        run(RUNS[1]); raise AssertionError('the simulated crash did not happen')
    except RuntimeError:
        pass
    finally:
        W.commit = real_commit
    left = os.path.join(L, 'challengers', bad + '.issued', RUNS[1] + '_001.npz')
    assert os.path.exists(left) and get(bad)['issued'] == [] and W.load_reg(L)['last_run_asof'] == RUNS[0] and n_events('issued') == 3
    r2 = run(RUNS[1])
    assert 'registered file' in r2['skipped'][dup] and dup not in r2['challengers'] and r2['judged_now'] == []
    assert 'issued-forecast file' in r2['skipped'][ext] and sorted(r2['challengers']) == [bad]
    (e,) = get(bad)['issued']
    z = r2['challengers'][bad]['issued']
    assert e['file'].endswith(RUNS[1] + '_001.npz') and W.sha(left) == e['sha256'] and e['rows'] == z['new'] == z['rows'] > 0 and z['late'] == 0
    assert n_events('issued') == 4
    open(vp, 'wb').write(orig); open(ep, 'wb').write(eorig)
    # run 3: a new quarter with a stale extra. 'ext' is skipped and not judged. The 60-day horizon of 'dup' is due for a
    # (forced) interim drop, but the judgement interval is not checked for 60 days: its numbers are recorded and it is held
    forced[(dup, 60)] = {'weeks': 30, 'gain_ci95': [-0.02, -0.001]}
    n_rej = len(rej_lines())
    r3 = run(RUNS[2], extra='extra_stale')
    del forced[(dup, 60)]
    assert 'older than asof' in r3['skipped'][ext] and r3['skip_streak'][ext] == 2 and r3['findings_run']
    assert sorted(r3['judged_now']) == sorted([dup, bad]) and get(ext)['judged_quarter'] == '2008Q1'
    held3 = [{'id': dup, 'h': 60, 'since': RUNS[2], 'numbers_read': 'drop_futility'}]
    assert r3['held'] == held3 and any('PERSON DECISION NEEDED' in x for x in r3['report']) and len(rej_lines()) == n_rej
    assert get(dup)['h_status'] == {'20': 'shadow', '60': 'shadow'} and get(dup)['status'] == 'shadow' and n_events('held') == 1
    assert get(dup)['held']['60']['asof'] == RUNS[2] and get(dup)['held']['60']['row']['weeks'] == 30
    assert r3['challengers'][bad]['issued']['kept'] == r2['challengers'][bad]['issued']['new'] and r3['challengers'][bad]['issued']['changed'] == 0
    ic = record_check(0.95, 0.94)                      # a second check, passed for both horizons: recorded, but a pass after a
    assert ic['pass'] == {'20': True, '60': True} and ic['auto'] == {'20': True, '60': False} and ic['file'].endswith('_002.json')   # failure allows nothing
    # run 4: the held judgement stays held (no check releases it; a person decides). The skipped challenger is judged at its
    # next scored run; nobody else is. What it did not issue in time is "no forecast"
    r4 = run(RUNS[3])
    assert r4['judged_now'] == [ext] and not r4['findings_run'] and get(ext)['h_status'] == {'20': 'shadow'} and r4['held'] == held3
    assert get(dup)['h_status'] == {'20': 'shadow', '60': 'shadow'} and get(dup)['status'] == 'shadow' and len(rej_lines()) == n_rej
    assert not [ev for ev in W.read_log(L) if ev.get('event') == 'judged' and ev['id'] == dup] and n_events('held') == 1
    assert any('PERSON DECISION NEEDED' in x for x in r4['report']) and r4['challengers'][dup]['60']['forward']['FM2']['weeks'] != 30
    z = r4['challengers'][ext]['issued']
    assert 0 < z['late'] < z['new'] and z['kept'] == r1['challengers'][ext]['issued']['new'] and any('not issued within' in x for x in r4['report'])
    late_keys = {(s, a, h) for s, rows in S.load_issued([os.path.join(L, get(ext)['issued'][-1]['file'])]).items()
                 for (a, h), q in rows.items() if not np.isfinite(q).all()}
    assert len(late_keys) == z['new_no_forecast'] == z['late'] and all(fm2.ordinal(RUNS[3]) - a > issue_days for _, a, _ in late_keys)
    # run 5: the minimum sample (the pass of 'ext' is forced; the 20-day horizon of 'dup' ends on its own numbers),
    # and a crash between saving the registry and appending the log
    real_append = W._append; n_before = len(W.read_log(L)); n_rej = len(rej_lines())
    forced[(ext, 20)] = {'gain_ci95': [0.01, 0.03], 'cov80_plus': 0.8}

    def boom(path, text):
        raise RuntimeError('simulated crash')
    W._append = boom
    try:
        run(RUNS[4]); raise AssertionError('the simulated crash did not happen')
    except RuntimeError:
        pass
    finally:
        W._append = real_append
    assert W.load_reg(L)['outbox']['log'] and len(W.read_log(L)) == n_before and len(rej_lines()) == n_rej
    r5 = run(RUNS[4], tag='_after_crash')              # finishes the owed lines first; then an ordinary repeated run
    log = W.read_log(L)
    assert W.load_reg(L)['outbox'] == {} and r5['judged_now'] == [] and r5['held'] == held3 and [ev['seq'] for ev in log] == list(range(1, len(log) + 1))
    judged5 = {ev['id']: ev for ev in log if ev.get('event') == 'judged' and ev['asof'] == RUNS[4] and ev['h'] == 20}
    assert sorted(judged5) == sorted([dup, ext]) and all(ev['row']['weeks'] >= 65 for ev in judged5.values())
    assert get(dup)['status'] == 'shadow' and get(dup)['h_status']['20'].startswith('end_') and get(dup)['h_status']['60'] == 'shadow'
    assert len(rej_lines()) == n_rej + 1               # the 20-day horizon ended; the 60-day one is held, so 'dup' keeps its slot
    # a challenger that passes becomes a candidate, keeps its slot, is no longer scored, and is listed until a person decides
    assert get(ext)['h_status'] == {'20': 'pass_to_judge'} and get(ext)['status'] == 'candidate', judged5[ext]['row']
    assert r5['awaiting_judge'] == [{'id': ext, 'h': 20}]
    del forced[(ext, 20)]
    # the same week once more: the staging of 'dup' finds new forecasts that differ between inputs cut at the start day and
    # inputs cut at asof (simulated). It is ended in that very run, its held horizon too; nobody else is touched
    os.remove(os.path.join(work, 'ch', dup, 'INPUTS.sha256')); real_stage = S.stage

    def stage_mismatch(path, *a, **k):
        if os.path.basename(path).startswith(dup):
            raise S.CutMismatch('2 of 40 new forecasts differ between inputs cut at the start day and inputs cut at asof (simulated)')
        return real_stage(path, *a, **k)
    S.stage = stage_mismatch
    try:
        r5c = run(RUNS[4], tag='_mismatch')
    finally:
        S.stage = real_stage
    assert 'start-day check failed' in r5c['skipped'][dup] and dup not in r5c['challengers'] and r5c['held'] == []
    assert get(dup)['status'] == 'ended' and get(dup)['h_status']['60'] == 'end_cut_mismatch' and get(dup)['h_status']['20'].startswith('end_')
    assert len(rej_lines()) == n_rej + 2 and '시작일 대조 불일치' in rej_lines()[-1] and any('was ended' in x for x in r5c['report'])
    assert get(ext)['status'] == 'candidate' and get(bad)['status'] == 'shadow'
    # run 6: a past close is corrected (a data revision). The recomputed forecasts change; the scored ones are those issued
    k = days.index('2008-03-03'); series[STEMS[0]][k] *= 1.03
    yj(os.path.join(dirs['pool'], STEMS[0] + '.json'), days, series[STEMS[0]])
    r6 = run(RUNS[5])
    assert r6['awaiting_judge'] == [{'id': ext, 'h': 20}] and sorted(r6['challengers']) == [bad] and get(bad)['status'] == 'shadow'
    assert r6['challengers'][bad]['20']['forward']['FM2']['first_start'] >= '2008-03-23'
    z = r6['challengers'][bad]['issued']
    assert z['changed'] > 0 and z['max_abs_diff'] > 0 and any('differ when recomputed' in x for x in r6['report'])
    arch = S.load_issued([os.path.join(L, e['file']) for e in get(bad)['issued']]); n_same = 0
    for s in STEMS:                                    # what the scores read (the staged rows) is the archive, row for row
        with np.load(os.path.join(work, 'ch', bad, s + '.npz')) as Z:
            for a, h, q in zip(Z['start'].tolist(), Z['h'].tolist(), Z['Qc']):
                if a >= fm2.ordinal(get(bad)['t0']):
                    assert np.array_equal(q, arch[s][(a, h)], equal_nan=True); n_same += 1
    assert n_same == z['rows'] == sum(len(v) for v in arch.values())
    n_iss6 = n_events('issued')
    r6b = run(RUNS[5], tag='_again')                   # the same week again: the same record, nothing issued twice
    assert json.dumps(r6b['challengers'][bad], sort_keys=True) == json.dumps(r6['challengers'][bad], sort_keys=True) and r6b['report'] == r6['report']
    # a weekly computation that fails for another reason is skipped and reported in that very run; the challenger stays
    os.remove(os.path.join(work, 'ch', bad, 'INPUTS.sha256'))

    def stage_fails(*a, **k):
        raise ValueError('start day 2008-05-02 is not in the input file (simulated)')
    S.stage = stage_fails
    try:
        r6c = run(RUNS[5], tag='_stagefail')
    finally:
        S.stage = real_stage
    assert r6c['skipped'][bad].startswith('stage error: ValueError') and r6c['skip_streak'][bad] == 1 and bad not in r6c['challengers']
    assert any('was not scored in this run' in x for x in r6c['report']) and get(bad)['status'] == 'shadow'
    r6d = run(RUNS[5], tag='_again2')                  # staged again from scratch: nothing is issued twice, the scores are the same
    z2 = r6d['challengers'][bad]['issued']
    assert z2['new'] == 0 and z2['kept'] == z2['rows'] == z['rows'] and z2['file'] is None and n_events('issued') == n_iss6
    assert json.dumps(r6d['challengers'][bad]['20']['forward'], sort_keys=True) == json.dumps(r6['challengers'][bad]['20']['forward'], sort_keys=True)
    # an older asof is refused and changes nothing
    snap = (status(), rej_lines(), len(W.read_log(L)))
    try:
        run(RUNS[1], tag='_old'); raise AssertionError('an older asof must be refused')
    except SystemExit as ex:
        assert 'older than the last run' in str(ex)
    assert (status(), rej_lines(), len(W.read_log(L))) == snap
    # an fm2 cache that was built from other input files is refused (here: the cache of this asof from before the revision)
    yj(os.path.join(dirs['pool'], STEMS[1] + '.json'), days, series[STEMS[1]] * 1.0001)
    try:
        run(RUNS[5], tag='_othercache'); raise AssertionError('a cache of other inputs must be refused')
    except SystemExit as ex:
        assert 'not built from these input files' in str(ex)
    yj(os.path.join(dirs['pool'], STEMS[1] + '.json'), days, series[STEMS[1]])
    # runs 7 and 8: a challenger that cannot be scored any more is ended after SKIP_CLOSE runs in a row and its slot is freed
    W.SKIP_CLOSE = 2
    bp = os.path.join(L, get(bad)['prereg']); open(bp, 'ab').write(b'\n')
    r7 = run(RUNS[6])
    assert 'registered file' in r7['skipped'][bad] and get(bad)['status'] == 'shadow' and r7['skip_streak'][bad] == 1
    n_rej = len(rej_lines())
    r8 = run(RUNS[7])
    assert get(bad)['status'] == 'ended' and get(bad)['h_status'] == {'20': 'end_unscored'} and r8['skip_streak'][bad] == 2
    assert len(rej_lines()) == n_rej + 1 and '채점하지 못해' in rej_lines()[-1] and r8['slots_used_after'] == 1 and r8['next_menu'] == 'peek'
    # the next menu entry looks ahead in derive(): the admission refuses it, nothing is registered, the refusal is logged
    try:
        register('peek', RUNS[7], '2008-07-26'); raise AssertionError('a challenger that looks ahead must not be registered')
    except SystemExit as ex:
        t = json.loads(str(ex).split('admission failed ', 1)[1])
        assert t['no_lookahead']['pass'] is False and t['no_lookahead']['rows_that_differ'] > 0 and t['deterministic']['pass'] and t['static']['pass']
    assert W.read_log(L)[-1]['event'] == 'admission_failed' and len(W.load_reg(L)['challengers']) == 4
    # the candidate waits until a person decides; the decision frees its slot
    assert W.slots_used(W.load_reg(L)) == 1
    W.cmd_close(L, ext, '사장 결정(시험) 2008-07-26: 편입 안 함')
    assert status()[ext] == ('closed', {'20': 'pass_to_judge'}) and W.slots_used(W.load_reg(L)) == 0
    # the books agree with each other, and the registry is what the log tells
    reg = W.open_books(L); log = W.read_log(L); n_iss = 0
    assert W.books_from_log(log) == {k: v for k, v in reg.items() if k != 'outbox'}
    for c in reg['challengers']:
        for e in c['issued']:
            assert W.sha(os.path.join(L, e['file'])) == e['sha256']; n_iss += 1
        assert sorted(os.listdir(os.path.join(L, 'challengers', c['id'] + '.issued'))) == sorted(os.path.basename(e['file']) for e in c['issued'])
    n_rej = sum(v not in ('shadow', 'pass_to_judge') for c in reg['challengers'] for v in c['h_status'].values()) + sum(c['status'] == 'closed' for c in reg['challengers'])
    assert len(rej_lines()) == n_rej == 5, (rej_lines(), n_rej)
    assert n_iss == n_events('issued') and [ev['seq'] for ev in log] == list(range(1, len(log) + 1))
    print('final status:', json.dumps(status(), ensure_ascii=False))
    print('rejected lines %d | log lines %d | issued files %d' % (len(rej_lines()), len(log), n_iss))
    print('work dir', work)
    print('itest OK')


if __name__ == '__main__':
    main()
