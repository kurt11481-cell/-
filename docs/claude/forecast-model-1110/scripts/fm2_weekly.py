#!/usr/bin/env python3
"""FM-2 weekly forward run, version 2 (display/score only; no orders, no policy/state/core-input change).

Orchestration around the hash-fixed fm2.py / fm1.py. There is no model code here.
Rules: forecast-forward-rule-2026-11-10.md. Two tracks:
  pool track  = the pre-registered forward test: the fixed learner on the 20 pool assets, starts >= FORWARD_START.
                Only this track can ever be judged, and only with enough scored weeks (MIN_WEEKS).
  index track = an additional display ledger for the three company indices (scored, never judged).

Steps:
  1. re-runs the fixed learner on the pool inputs (re-staged when asof or any input file changed)
  2. appends this week's range forecasts for the display targets to the forecast ledger.
     FM-2, the frozen pool F0 and the baseline B3 are each a weight vector W and a width scale s over the same
     four expert samples x, so a line can be re-scored from its own content with the fm2.py definitions.
  3. scores ledger lines whose horizon has passed, against the actual close
  4. reports the pool forward scores. No promotion or demotion is decided here (forward rule 3 and 4).

The ledger is append-only JSON lines: past lines are never rewritten. Lines written by version 1
(old/fm2_weekly_v1_99ff9668.py: no "v" field, a 99-quantile "logq" per model) are still scored the version-1 way.

usage:
  python3 -I -B fm2_weekly.py <pool_inputs_dir> <index_and_rates_dir> <asof YYYY-MM-DD> <cache_dir> <ledger_jsonl> <out_json> [--jobs N]
"""
import sys, os, json, math, datetime, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fm1, fm2

FORWARD_START = '2026-11-11'      # FM-2 prereg section 6: forward scoring uses starts after 2026-11-10
TARGETS = ['_SOX', '_NDX', '_GSPC']
CANDIDATE_H = [20, 60]            # horizons with a candidate verdict; 250 is recorded as baseline-only
REF_BASE = 'B3'                   # reference baseline, shown next to the pre-registered "best baseline" P1n
MIN_WEEKS = {20: 104, 60: 208}    # forward rule 3: scored weeks needed before any judgement
WARN_WEEKS = 52                   # forward rule 4: scored weeks needed before the coverage warning
FWD_Q = 4                         # forward rule 3: time groups of the t interval
COV_BAND = (0.70, 0.90)
EQ = np.full(fm2.QN, 1.0 / fm2.QN)
CUT = math.log(0.8)
K = len(fm2.EXPERTS)
FIXED_MODELS = {'F0': ([1.0 / K] * K, 1.0),
                'B3': ([1.0 if e == 'B3' else 0.0 for e in fm2.EXPERTS], 1.0)}    # FM2 comes from the learner state


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def kst_now():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S KST')


def inputs_digest(pool_dir, idx_dir):
    """One hash over every input file the pool stage reads (20 pool files and the two rate files)."""
    hh = hashlib.sha256()
    for d, stems in ((pool_dir, [s for s, _, _ in fm2.UNIVERSE]), (idx_dir, ['_TNX', '_IRX'])):
        for stem in stems:
            hh.update(('%s:%s\n' % (stem, sha(os.path.join(d, stem + '.json')))).encode())
    return hh.hexdigest()


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
        row = {'n_matured': int(mk.sum()), 'n_issued': int((F['start'] >= f0).sum()),
               'status': 'candidate' if h in CANDIDATE_H else 'baseline_only',
               'judgement': 'insufficient_sample' if h in MIN_WEEKS else 'not_judged'}
        if h in MIN_WEEKS:
            row['weeks_needed'] = MIN_WEEKS[h]
        if mk.sum():
            bn = F['bc'] / F['norm'][:, None]
            sums = {b: float(bn[mk, i].sum()) for i, b in enumerate(fm2.BASES) if np.isfinite(bn[mk, i]).all()}
            best = min(sums, key=sums.get)                      # prereg definition: best baseline on the scored sample
            c = R['crps'][mk]; c0 = R0['crps'][mk]
            weeks = len(set(F['week'][mk].tolist()))
            row.update({'weeks': weeks, 'indep_periods': round(weeks / (h // fm2.GRID_STEP), 2), 'best_baseline': best,
                        'P1n_FM2': float(1 - c.sum() / sums[best]), 'P1n_F0': float(1 - c0.sum() / sums[best]),
                        'P1n_FM2_vs_' + REF_BASE: float(1 - c.sum() / sums[REF_BASE]),
                        'P1n_F0_vs_' + REF_BASE: float(1 - c0.sum() / sums[REF_BASE]),
                        'gain_vs_F0': float(1 - c.sum() / c0.sum()),
                        'cov80_FM2': float(R['hit'][mk].mean()), 'cov80_F0': float(R0['hit'][mk].mean()),
                        'cov80_' + REF_BASE: float(F['bh'][mk, fm2.BASES.index(REF_BASE)].mean())})
            if h in MIN_WEEKS:
                row['coverage_warning'] = bool(weeks >= WARN_WEEKS and not (COV_BAND[0] <= row['cov80_FM2'] <= COV_BAND[1]))
                if weeks >= MIN_WEEKS[h]:
                    cols = {'m': c, 'f0': c0, 'b': bn[mk, fm2.BASES.index(best)], 'hit': R['hit'][mk], 'n': np.ones(int(mk.sum()))}
                    G = fm2.group_sums(F['week'][mk], cols, FWD_Q)
                    row['ci95'] = {'P1n_FM2': fm2.t_ci(1 - G['m'] / G['b']), 'P1n_F0': fm2.t_ci(1 - G['f0'] / G['b']),
                                   'gain_vs_F0': fm2.t_ci(1 - G['m'] / G['f0']), 'cov80_FM2': fm2.t_ci(G['hit'] / G['n'])}
                    row['judgement'] = 'sample_reached_apply_forward_rule_3_and_4_by_hand'
        out[str(h)] = row
    return idx, out, states


def model_dist(Q, W, s):
    """Band, median and tail of the pool with expert weights W, scaled by s around its median (fm2.py definition).
    Q: [K, QN] expert samples. Returns the summary and the scaled weighted sample."""
    w = np.repeat(np.asarray(W, dtype=np.float64) / fm2.QN, fm2.QN)
    keep = w > 0
    x = np.asarray(Q, dtype=np.float64).ravel()[keep]; w = w[keep]
    med, q10, q90 = fm2.wq(x, w, [0.5, 0.1, 0.9])
    lo = med + s * (q10 - med); hi = med + s * (q90 - med)
    xs = med + s * (x - med)
    return ({'W': [float(v) for v in W], 's': float(s), 'log_lo': lo, 'log_med': med, 'log_hi': hi,
             'q10': math.exp(lo) - 1, 'q50': math.exp(med) - 1, 'q90': math.exp(hi) - 1,
             'p_below_minus20pct': float(np.sum(w[xs < CUT]))}, xs, w)


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
            Q = np.round(Q, 7)                                  # what is stored is what is scored
            st = states[h]
            models = {'FM2': model_dist(Q, st['W'], float(st['s']))[0]}
            for nm, (W, s) in FIXED_MODELS.items():
                models[nm] = model_dist(Q, W, s)[0]
            rows.append({'type': 'forecast', 'v': 2, 'id': '%s|%s|%d' % (d[i], stem, h), 'start_day': d[i], 'target': stem, 'h': h,
                         'start_close': float(c[i]), 'forward': bool(d[i] >= FORWARD_START),
                         'status': 'candidate_display_only' if h in CANDIDATE_H else 'baseline_only',
                         'state': st, 'experts': list(fm2.EXPERTS), 'x': [[float(v) for v in q] for q in Q], 'models': models,
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
            if 'logq' in m:                                     # version-1 line: 99-quantile reduction
                q = np.array(m['logq'])
                lo, hi = fm2.wq(q, EQ, [0.1, 0.9])
                sc['models'][name] = {'crps': float(fm1.crps_w(q, EQ, y)), 'hit80': bool(lo <= y <= hi)}
            else:                                               # version-2 line: the stored sample, fm2.py definition
                dm, xs, w = model_dist(np.array(r['x'], dtype=np.float64), m['W'], m['s'])
                sc['models'][name] = {'crps': float(fm1.crps_w(xs, w, y)), 'hit80': bool(dm['log_lo'] <= y <= dm['log_hi'])}
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
    dig = inputs_digest(pool_dir, idx_dir)
    ix = os.path.join(cache, 'INDEX.json'); dg = os.path.join(cache, 'INPUTS.sha256')
    fresh = (os.path.exists(ix) and json.load(open(ix)).get('asof') == asof
             and os.path.exists(dg) and open(dg).read().strip() == dig)
    if not fresh:
        fm2.stage_experts(pool_dir, idx_dir, asof, cache, jobs)
        with open(dg, 'w') as f:
            f.write(dig + '\n')
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
    latest = {}
    for r in allrows:
        if r['type'] == 'forecast':
            k = r['target'] + '|' + str(r['h'])
            if k not in latest or r['start_day'] >= latest[k]['start_day']:
                latest[k] = r
    keys = ('q10', 'q50', 'q90', 'p_below_minus20pct')
    res = {'asof': asof, 'run_at': kst_now(), 'forward_start': FORWARD_START, 'code': code, 'inputs_digest': dig,
           'rule': 'forecast-forward-rule-2026-11-10.md',
           'pool_forward': pool, 'states': {str(h): states[h] for h in states},
           'ledger': {'path': os.path.basename(ledger_path), 'forecast_lines': len([r for r in allrows if r['type'] == 'forecast']),
                      'score_lines': len(scores), 'new_forecasts': len(new_fc), 'new_scores': len(new_sc), 'forward_scored_by_h': led},
           'display': {k: {'start_day': r['start_day'], 'status': r['status'], 'forward': r['forward'],
                           **{nm: {kk: round(m[kk], 4) for kk in keys} for nm, m in r['models'].items()}}
                       for k, r in sorted(latest.items())}}
    json.dump(res, open(outp, 'w'), ensure_ascii=False, indent=1)
    print('asof', asof, '| new forecast lines', len(new_fc), '| new score lines', len(new_sc))
    for h in fm2.HORIZONS:
        print(' pool forward h=%d' % h, pool[str(h)])
    print('written', outp)


if __name__ == '__main__':
    main()
