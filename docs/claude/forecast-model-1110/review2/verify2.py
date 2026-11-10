#!/usr/bin/env python3
"""Author-side check of the numbers the second reviewer reported (reference only; no re-tuning, no verdict use).
usage: python3 -I -B verify2.py <cache_dir>"""
import sys, os, math, datetime
sys.path.insert(0, '/mnt/project-files/forecast-model-1110/scripts')
import numpy as np
import fm1, fm2

CACHE = sys.argv[1]
CUT = math.log(0.8)
T975 = {1: 12.7062, 2: 4.3027, **fm2.T975, 13: 2.1604, 14: 2.1448, 15: 2.1314, 16: 2.1199, 17: 2.1098, 18: 2.1009,
        19: 2.0930, 20: 2.0860, 21: 2.0796, 22: 2.0739}


def tci(v):
    v = np.asarray(v, float); q = len(v)
    half = T975[q - 1] * float(v.std(ddof=1)) / math.sqrt(q)
    return v.mean() - half, v.mean() + half


def f(x):
    return '%+.2f' % (100 * x)


idx, data = fm2.load_cache(CACHE)
stems = [a['stem'] for a in idx['assets']]
K = fm2.K; QN = fm2.QN
for h in fm2.HORIZONS:
    F = fm2.prep(data[h])
    R = fm2.learn(F); R0 = fm2.learn(F, learn_w=False, learn_s=False)
    score = (F['start'] >= fm2.ordinal(fm2.SCORE_START)) & (F['mat'] >= 0)
    bn = F['bc'] / F['norm'][:, None]
    bi = fm2.BASES.index('B3'); bbest = bn[:, bi]
    c = R['crps']; c0 = R0['crps']
    years = np.array([datetime.date.fromordinal(int(o)).year for o in F['start']])
    e3 = score & (F['start'] >= fm2.ordinal('2020-01-01'))
    wk = F['week'][score]
    print('===== h=%d n=%d  P1n %s  F0 P1n %s  gain %s  cov %.4f  F0 cov %.4f' % (
        h, score.sum(), f(1 - c[score].sum() / bbest[score].sum()), f(1 - c0[score].sum() / bbest[score].sum()),
        f(1 - c[score].sum() / c0[score].sum()), R['hit'][score].mean(), R0['hit'][score].mean()))
    cols = {'m': c[score], 'b': bbest[score], 'f0': c0[score], 'hit': R['hit'][score], 'hit0': R0['hit'][score],
            'n': np.ones(int(score.sum()))}
    # (1) grouping sensitivity
    for q in (3, 4, 5, 6, 8, 10, 11, 12):
        G = fm2.group_sums(wk, cols, q)
        p = tci(1 - G['m'] / G['b']); g = tci(1 - G['m'] / G['f0']); cv = tci(G['hit'] / G['n']); cv0 = tci(G['hit0'] / G['n'])
        print('  q=%2d P1n [%s, %s] | gain [%s, %s] | cov [%.4f, %.4f] | F0 cov [%.4f, %.4f] holds80=%s' % (
            q, f(p[0]), f(p[1]), f(g[0]), f(g[1]), cv[0], cv[1], cv0[0], cv0[1], cv0[0] <= 0.8 <= cv0[1]))
    # (2) calendar-year blocks
    ys = sorted(set(years[score].tolist()))
    S = {k: np.array([v[years[score] == yv].sum() for yv in ys]) for k, v in cols.items()}
    p = tci(1 - S['m'] / S['b']); g = tci(1 - S['m'] / S['f0']); cv0 = tci(S['hit0'] / S['n']); cv = tci(S['hit'] / S['n'])
    print('  year blocks n=%d: P1n [%s, %s] | gain [%s, %s] | cov [%.4f, %.4f] | F0 cov [%.4f, %.4f]' % (
        len(ys), f(p[0]), f(p[1]), f(g[0]), f(g[1]), cv[0], cv[1], cv0[0], cv0[1]))
    yp = 1 - S['m'] / S['b']; yc = S['hit'] / S['n']; yg = 1 - S['m'] / S['f0']
    print('  yearly P1n>0 in %d/%d; gain>0 in %d/%d; sd yearly P1n %.4f' % ((yp > 0).sum(), len(ys), (yg > 0).sum(), len(ys), yp.std(ddof=1)))
    print('  yearly cov: ' + ' '.join('%d:%.3f' % (yv, v) for yv, v in zip(ys, yc)))
    print('  yearly P1n: ' + ' '.join('%d:%s' % (yv, f(v)) for yv, v in zip(ys, yp)))
    # 2010+ subset with regrouped q
    sub = score & (F['start'] >= fm2.ordinal('2010-01-01'))
    cs = {'m': c[sub], 'b': bbest[sub], 'f0': c0[sub]}
    G = fm2.group_sums(F['week'][sub], cs, fm2.GROUPS_Q[h]); p = tci(1 - G['m'] / G['b'])
    print('  starts 2010+: n=%d P1n %s [%s, %s]' % (sub.sum(), f(1 - c[sub].sum() / bbest[sub].sum()), f(p[0]), f(p[1])))
    # (3) single expert alone
    ek = F['A'] - 0.5 * np.stack([F['D'][:, k, k] for k in range(K)], axis=1)
    print('  expert alone P1n: ' + ' '.join('%s %s' % (fm2.EXPERTS[k], f(1 - ek[score, k].sum() / bbest[score].sum())) for k in range(K))
          + ' | 2020+: ' + ' '.join('%s %s' % (fm2.EXPERTS[k], f(1 - ek[e3, k].sum() / bbest[e3].sum())) for k in range(K))
          + ' | FM2 2020+ %s F0 2020+ %s' % (f(1 - c[e3].sum() / bbest[e3].sum()), f(1 - c0[e3].sum() / bbest[e3].sum())))
    # (4) concentration of the gain
    d = c0 - c; tot = d[score].sum()
    print('  gain share by class: ' + ' '.join('%s %.0f%%' % (cl, 100 * d[score & (F['cls'] == cl)].sum() / tot) for cl in sorted(set(F['cls'].tolist()))))
    sh = sorted(((100 * d[score & (F['asset'] == a)].sum() / tot, stems[a]) for a in range(len(stems))), reverse=True)
    print('  gain share by asset: ' + ' '.join('%s %.0f%%' % (s, v) for v, s in sh))
    ns = score & (F['cls'] != 'stock')
    print('  gain without stocks %s | gain 2020+ %s | assets with gain>0: %d/%d' % (
        f(1 - c[ns].sum() / c0[ns].sum()), f(1 - c[e3].sum() / c0[e3].sum()), sum(v > 0 for v, s in sh), len(sh)))
    # (5) band sides and (7) P(<-20%) reliability, recomputed from the cache with the issued W and s
    ii = np.where(score)[0]
    Q = F['Q'].astype(np.float64); y = F['y']
    out = {}
    for nm, RR in (('FM2', R), ('F0', R0)):
        lo = np.empty(len(ii)); hi = np.empty(len(ii)); pb = np.empty(len(ii))
        for n_, j in enumerate(ii):
            x = Q[j].ravel(); w = np.repeat(RR['W'][j] / QN, QN); s = RR['s'][j]
            med, q10, q90 = fm2.wq(x, w, [0.5, 0.1, 0.9])
            lo[n_] = med + s * (q10 - med); hi[n_] = med + s * (q90 - med)
            xs = med + s * (x - med); pb[n_] = float(np.sum(w[xs < CUT]))
        yy = y[ii]; r20 = e3[ii]
        hit = ((lo <= yy) & (yy <= hi)).astype(float)
        print('  %s: hit recomputed == learn hit: %s | below 10%% edge %.4f (2020+ %.4f) | above 90%% edge %.4f (2020+ %.4f) | cov 2020+ %.4f' % (
            nm, bool((hit == RR['hit'][ii]).all()), (yy < lo).mean(), (yy < lo)[r20].mean(), (yy > hi).mean(), (yy > hi)[r20].mean(), hit[r20].mean()))
        real = (yy < CUT).astype(float)
        print('     P(<-20%%): mean predicted %.4f realised %.4f | 2020+: %.4f vs %.4f' % (pb.mean(), real.mean(), pb[r20].mean(), real[r20].mean()))
        edges = [0, 0.005, 0.02, 0.04, 0.07, 0.12, 0.20, 1.01]
        print('     bins: ' + ' | '.join('[%.3f,%.3f) n=%d pred %.3f real %.3f' % (a, b, ((pb >= a) & (pb < b)).sum(), pb[(pb >= a) & (pb < b)].mean(), real[(pb >= a) & (pb < b)].mean())
                                           for a, b in zip(edges[:-1], edges[1:]) if ((pb >= a) & (pb < b)).sum() > 0))
    sys.stdout.flush()
