#!/usr/bin/env python3
"""FM-2 weekly forward run (display/score only; no orders, no policy/state/core-input change).

Orchestration around the hash-fixed fm2.py / fm1.py. There is no model code here.
  1. re-runs the fixed learner on freshly fetched pool inputs (20 assets)
  2. appends this week's range forecasts for the display targets to the forecast ledger
     (FM-2, the frozen pool F0, and the baseline B3 side by side)
  3. scores ledger rows whose horizon has passed, against the actual close
  4. reports forward scores (starts >= FORWARD_START) of FM-2 vs F0 on the pool

The ledger is append-only JSON lines: past lines are never rewritten.

usage:
  python3 -I fm2_weekly.py <pool_inputs_dir> <index_and_rates_dir> <asof YYYY-MM-DD> <cache_dir> <ledger_jsonl> <out_json> [--jobs N]
"""
import sys, os, json, math, datetime, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fm1, fm2

FORWARD_START = '2026-11-11'      # FM-2 prereg section 6: forward scoring uses starts after 2026-11-10
TARGETS = ['_SOX', '_NDX', '_GSPC']
CANDIDATE_H = [20, 60]            # horizons with a candidate verdict; 250 is recorded as baseline-only
FIXED_BASE = 'B3'                 # baseline for forward P1n, fixed in advance (best baseline in the prereg test)
EQ = np.full(fm2.QN, 1.0 / fm2.QN)
CUT = math.log(0.8)


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def kst_now():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S KST')


def pool_scores(cache):
    """Forward (start >= FORWARD_START) scores on the 20-asset pool, and the latest learner state per horizon."""
    idx, data = fm2.load_cache(cache)
    out = {}; states = {}
    f0 = fm2.ordinal(FORWARD_START)
    for h in fm2.HORIZONS:
        F = fm2.prep(data[h])
        R = fm2.learn(F); R0 = fm2.learn(F, learn_w=False, learn_s=False)
        states[h] = R['state_last']
        mk = (F['start'] >= f0) & (F['mat'] >= 0)
        row = {'n_matured': int(mk.sum()), 'n_issued': int((F['start'] >= f0).sum())}
        if mk.sum():
            b = (F['bc'][:, fm2.BASES.index(FIXED_BASE)] / F['norm'])[mk]
            weeks = len(set(F['week'][mk].tolist()))
            row.update({'weeks': weeks, 'indep_periods': round(weeks / (h // fm2.GRID_STEP), 2),
                        'P1n_FM2': float(1 - R['crps'][mk].sum() / b.sum()), 'P1n_F0': float(1 - R0['crps'][mk].sum() / b.sum()),
                        'gain_vs_F0': float(1 - R['crps'][mk].sum() / R0['crps'][mk].sum()),
                        'cov80_FM2': float(R['hit'][mk].mean()), 'cov80_F0': float(R0['hit'][mk].mean()),
                        'cov80_' + FIXED_BASE: float(F['bh'][mk, fm2.BASES.index(FIXED_BASE)].mean())})
        out[str(h)] = row
    return idx, out, states


def dist(x, w, s):
    """99 quantiles and summary of a pooled distribution scaled by s around its median."""
    med, = fm2.wq(x, w, [0.5])
    xs = med + s * (x - med)
    q = np.array(fm2.wq(xs, w, list(fm1.QL)))
    q10, q50, q90 = fm2.wq(q, EQ, [0.1, 0.5, 0.9])
    return {'q10': math.exp(q10) - 1, 'q50': math.exp(q50) - 1, 'q90': math.exp(q90) - 1,
            'p_below_minus20pct': float(np.sum(w[xs < CUT])), 'logq': [round(float(v), 6) for v in q]}


def issue(idx_dir, asof, states, code):
    """Forecast lines for the display targets at the last close <= asof."""
    tnx_d, tnx_v = fm1.load_yahoo(os.path.join(idx_dir, '_TNX.json'))
    irx_d, irx_v = fm1.load_yahoo(os.path.join(idx_dir, '_IRX.json'))
    rows = []
    for stem in TARGETS:
        d, c = fm1.load_yahoo(os.path.join(idx_dir, stem + '.json'))
        keep = [k for k, x in enumerate(d) if fm1.HIST_FLOOR <= x <= asof]
        d = [d[k] for k in keep]; c = c[keep]
        S = fm2.build_series(d, c, tnx_d, tnx_v, irx_d, irx_v, 0)
        i = len(d) - 1
        for h in fm2.HORIZONS:
            fc = fm1.forecasts(S, i, h, want=('B1', 'B3', 'M1', 'M2'))
            Q = np.stack([fc['B1'][2] * fm2.ZQ, fc['B3'][1], fc['M1'][1], fc['M2'][1]]).astype(np.float64)
            x = Q.ravel(); st = states[h]
            w = np.repeat(np.array(st['W']) / fm2.QN, fm2.QN); w0 = np.repeat(np.full(fm2.K, 1.0 / fm2.K) / fm2.QN, fm2.QN)
            rows.append({'type': 'forecast', 'id': '%s|%s|%d' % (d[i], stem, h), 'start_day': d[i], 'target': stem, 'h': h,
                         'start_close': float(c[i]), 'forward': bool(d[i] >= FORWARD_START),
                         'status': 'candidate_display_only' if h in CANDIDATE_H else 'baseline_only',
                         'state': st, 'models': {'FM2': dist(x, w, float(st['s'])), 'F0': dist(x, w0, 1.0),
                                                 'B3': dist(fc['B3'][1].astype(np.float64), EQ, 1.0)},
                         'code': code, 'written_at': kst_now()})
    return rows


def score_matured(ledger, idx_dir, asof):
    """Score lines for forecast lines whose h trading days have passed. Uses the target's own calendar."""
    done = {r['ref'] for r in ledger if r['type'] == 'score'}
    series = {}
    out = []
    for r in ledger:
        if r['type'] != 'forecast' or r['id'] in done:
            continue
        if r['target'] not in series:
            d, c = fm1.load_yahoo(os.path.join(idx_dir, r['target'] + '.json'))
            keep = [k for k, x in enumerate(d) if x <= asof]
            series[r['target']] = ([d[k] for k in keep], c[keep])
        d, c = series[r['target']]
        if r['start_day'] not in d:
            continue
        i = d.index(r['start_day'])
        if i + r['h'] > len(d) - 1:
            continue
        y = math.log(c[i + r['h']] / c[i])
        sc = {'type': 'score', 'ref': r['id'], 'due_day': d[i + r['h']], 'y': y, 'ret': math.exp(y) - 1,
              'start_close_revised': bool(abs(c[i] / r['start_close'] - 1) > 1e-6), 'models': {}, 'written_at': kst_now()}
        for name, m in r['models'].items():
            q = np.array(m['logq'])
            lo, hi = fm2.wq(q, EQ, [0.1, 0.9])
            sc['models'][name] = {'crps': float(fm1.crps_w(q, EQ, y)), 'hit80': bool(lo <= y <= hi)}
        out.append(sc)
    return out


def main():
    global FORWARD_START
    pool_dir, idx_dir, asof, cache, ledger_path, outp = sys.argv[1:7]
    if '--forward-start' in sys.argv:           # for tests on synthetic data only
        FORWARD_START = sys.argv[sys.argv.index('--forward-start') + 1]
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 1
    here = os.path.dirname(os.path.abspath(__file__))
    code = {'fm2': sha(os.path.join(here, 'fm2.py'))[:16], 'fm1': sha(os.path.join(here, 'fm1.py'))[:16],
            'weekly': sha(os.path.abspath(__file__))[:16]}
    ix = os.path.join(cache, 'INDEX.json')
    if not (os.path.exists(ix) and json.load(open(ix)).get('asof') == asof):
        fm2.stage_experts(pool_dir, idx_dir, asof, cache, jobs)
    idx, pool, states = pool_scores(cache)
    ledger = [json.loads(l) for l in open(ledger_path, encoding='utf-8')] if os.path.exists(ledger_path) else []
    have = {r['id'] for r in ledger if r['type'] == 'forecast'}
    new_fc = [r for r in issue(idx_dir, asof, states, code) if r['id'] not in have]
    new_sc = score_matured(ledger + new_fc, idx_dir, asof)
    with open(ledger_path, 'a', encoding='utf-8') as f:
        for r in new_fc + new_sc:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    allrows = ledger + new_fc + new_sc
    scores = [r for r in allrows if r['type'] == 'score']
    fwd_ids = {r['id'] for r in allrows if r['type'] == 'forecast' and r['forward']}
    led = {}
    for h in fm2.HORIZONS:
        ss = [s for s in scores if s['ref'] in fwd_ids and s['ref'].endswith('|%d' % h)]
        if ss:
            led[str(h)] = {'n': len(ss), **{nm: {'crps_sum': sum(s['models'][nm]['crps'] for s in ss),
                                                 'hit80': sum(s['models'][nm]['hit80'] for s in ss)} for nm in ('FM2', 'F0', 'B3')}}
    res = {'asof': asof, 'run_at': kst_now(), 'forward_start': FORWARD_START, 'code': code,
           'pool_forward': pool, 'states': {str(h): states[h] for h in states},
           'ledger': {'path': os.path.basename(ledger_path), 'forecast_lines': len([r for r in allrows if r['type'] == 'forecast']),
                      'score_lines': len(scores), 'new_forecasts': len(new_fc), 'new_scores': len(new_sc), 'forward_scored_by_h': led},
           'display': {r['target'] + '|' + str(r['h']): {'status': r['status'], 'forward': r['forward'],
                                                        **{nm: {k: round(v, 4) for k, v in m.items() if k != 'logq'} for nm, m in r['models'].items()}}
                       for r in new_fc}}
    json.dump(res, open(outp, 'w'), ensure_ascii=False, indent=1)
    print('asof', asof, '| new forecast lines', len(new_fc), '| new score lines', len(new_sc))
    for h in fm2.HORIZONS:
        print(' pool forward h=%d' % h, pool[str(h)])
    print('written', outp)


if __name__ == '__main__':
    main()
