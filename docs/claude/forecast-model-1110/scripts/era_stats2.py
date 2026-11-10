#!/usr/bin/env python3
"""Robustness checks for the era table (reference, Yahoo). Written after the independent re-review:
rows whose reading depended on one definition or on March 2020 are recomputed another way.
usage: python3 -I era_stats2.py inputs/yh 2026-11-06 <out_json>"""
import json, sys, os, datetime, math
import numpy as np
inp, asof, outp = sys.argv[1], sys.argv[2], sys.argv[3]
ERAS = [('1990s', '1990-01-01', '1999-12-31'), ('2000s', '2000-01-01', '2009-12-31'),
        ('2010s', '2010-01-01', '2019-12-31'), ('2020s', '2020-01-01', asof), ('2021-', '2021-01-01', asof)]


def load(sym, adj=False):
    d = json.load(open(os.path.join(inp, sym + '.json')))['chart']['result'][0]
    q = d['indicators']['quote'][0]; ac = d['indicators'].get('adjclose', [{}])[0].get('adjclose') if adj else None
    rows = []
    for k, t in enumerate(d['timestamp']):
        c = q['close'][k]; o = q['open'][k]
        if c is None or c <= 0: continue
        day = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%d')
        if day > asof: continue
        a = ac[k] if ac and ac[k] else float('nan')
        rows.append((day, o if o and o > 0 else float('nan'), c, a))
    return [r[0] for r in rows], np.array([r[1] for r in rows]), np.array([r[2] for r in rows]), np.array([r[3] for r in rows])


def mask(days, a, b): return np.array([a <= x <= b for x in days])
out = {}
def put(k, era, v): out.setdefault(k, {})[era] = v
S = {s: load(s, adj=True) for s in ['_GSPC', '_SOX', '_VIX', 'SPY', 'QQQ', 'SOXX', 'RSP', 'TLT', '_TNX']}
out['first_day'] = {s: S[s][0][0] for s in S}

# (a) SOX: share of days 20%+ below the trailing 252-day high
d, o, c, _ = S['_SOX']
hi = np.array([c[max(0, i - 251):i + 1].max() for i in range(len(c))])
below = c / hi - 1 <= -0.20
for en, a, b in ERAS:
    m = mask(d, a, b)
    if m.sum() > 250: put('_SOX share of days 20%+ below 1y high %', en, round(100 * float(below[m].mean()), 1))

# (b) lag-1 autocorrelation with and without the 2020 crash window; share of sign flips
for sym in ['_GSPC', '_SOX']:
    d, o, c, _ = S[sym]; dd = d[1:]; r = np.diff(np.log(c))
    for en, a, b in ERAS:
        m = mask(dd, a, b)
        if m.sum() < 500: continue
        x = r[m]
        put(sym + ' lag1 autocorr', en, round(float(np.corrcoef(x[1:], x[:-1])[0, 1]), 3))
        put(sym + ' share of days with sign flip %', en, round(100 * float(np.mean(np.sign(x[1:]) != np.sign(x[:-1]))), 1))
        put(sym + ' ann vol %', en, round(100 * float(x.std()) * math.sqrt(252), 1))
        put(sym + ' days |r|>4% share %', en, round(100 * float(np.mean(np.abs(x) > 0.04)), 2))
    m = mask(dd, '2020-01-01', asof); ex = m & ~mask(dd, '2020-02-20', '2020-04-30')
    idx = np.where(ex)[0]; pairs = [(r[i - 1], r[i]) for i in idx if ex[i - 1]]
    pa = np.array(pairs)
    put(sym + ' lag1 autocorr', '2020s excl 2020-02-20..04-30', round(float(np.corrcoef(pa[:, 0], pa[:, 1])[0, 1]), 3))

# (c) gap share of loss on days <= -3%
for sym in ['SPY', 'QQQ', 'SOXX']:
    d, o, c, _ = S[sym]
    on = np.log(o[1:] / c[:-1]); intr = np.log(c[1:] / o[1:]); dd = d[1:]
    for en, a, b in ERAS:
        m = mask(dd, a, b) & np.isfinite(on) & np.isfinite(intr)
        big = m & ((on + intr) <= -0.03)
        if big.sum() >= 5:
            put(sym + ' days<=-3%: gap share of loss % (n)', en, f"{round(100*on[big].sum()/(on[big]+intr[big]).sum())} ({int(big.sum())})")
    m = mask(dd, '2020-01-01', '2020-12-31') & np.isfinite(on) & np.isfinite(intr)
    put(sym + ' days<=-3%: n in 2020 alone', '2020', int((m & ((on + intr) <= -0.03)).sum()))

# (d) VIX: distinct stress periods (first close above 30 until first close below 20), by start date
d, o, c, _ = S['_VIX']; per = []; i = 0; n = len(c)
while i < n:
    if c[i] > 30:
        j = i
        while j < n and c[j] >= 20: j += 1
        per.append((d[i], j - i, j < n)); i = j
    else: i += 1
for en, a, b in ERAS[:4]:
    e = [p for p in per if a <= p[0] <= b]
    if e: put('VIX distinct stress periods: n / median trading days until below 20', en, f"{len(e)} / {int(np.median([p[1] for p in e]))}")
out['VIX periods since 2010'] = [p for p in per if p[0] >= '2010']

# (e) SOX dip (5d <= -2 sigma): next-20d up counts
d, o, c, _ = S['_SOX']; lc = np.log(c); n = len(c)
r5 = lc[5:] - lc[:-5]; sd = np.array([np.std(np.diff(lc[max(0, i - 252):i + 1])) if i > 60 else np.nan for i in range(5, n)]) * math.sqrt(5)
f20 = np.full(n - 5, np.nan); f20[:n - 25] = lc[25:] - lc[5:n - 20]; dd5 = d[5:]
for en, a, b in ERAS[:4]:
    m = mask(dd5, a, b) & np.isfinite(f20) & np.isfinite(sd)
    hi_ = np.where(m & (r5 <= -2 * sd))[0]; keep = [hi_[k] for k in range(len(hi_)) if k == 0 or hi_[k] - hi_[k - 1] > 20]
    if len(keep) >= 5:
        put('_SOX dip: up 20 trading days later, k of n / median %', en, f"{int(np.sum(f20[keep] > 0))} of {len(keep)} / {round(100*float(np.median(f20[keep])),1)}")

# (f) beta, correlations from 2021
def align(a, b, adj=False):
    da, _, ca, aa = S[a]; db, _, cb, ab = S[b]
    xa = aa if adj else ca; xb = ab if adj else cb
    ia = {x: k for k, x in enumerate(da)}; ib = {x: k for k, x in enumerate(db)}
    common = [x for x in da if x in ib]
    pa = np.array([xa[ia[x]] for x in common]); pb = np.array([xb[ib[x]] for x in common])
    return common[1:], np.diff(np.log(pa)), np.diff(np.log(pb))
for a, b, adj in [('_SOX', '_GSPC', False), ('SPY', 'TLT', False), ('RSP', 'SPY', False), ('RSP', 'SPY', True)]:
    dd, ra, rb = align(a, b, adj)
    for en, s, e in ERAS:
        m = mask(dd, s, e) & np.isfinite(ra) & np.isfinite(rb)
        if m.sum() < 500: continue
        cc = float(np.corrcoef(ra[m], rb[m])[0, 1])
        put(f"{a} vs {b}{' (with dividends)' if adj else ''}: corr / beta / ann ret gap %p", en,
            f"{round(cc,2)} / {round(cc*ra[m].std()/rb[m].std(),2)} / {round(100*(ra[m].mean()-rb[m].mean())*252,1)}")

# (g) SOX: where it stands at asof
d, o, c, _ = S['_SOX']; m = mask(d, '2026-01-01', asof); idx = np.where(m)[0]
pk = idx[np.argmax(c[idx])]; tr = pk + int(np.argmin(c[pk:]))
out['_SOX 2026'] = {'peak': d[pk], 'trough': d[tr], 'trough_from_peak_%': round(100 * (c[tr] / c[pk] - 1), 1), 'trough_days': int(tr - pk),
                    'asof_from_peak_%': round(100 * (c[-1] / c[pk] - 1), 1), 'asof_days': int(len(c) - 1 - pk), 'asof_day': d[-1]}

# (i) S&P return vs 10y yield change: correlation and share of same-sign days
dt, _, ct, _ = S['_TNX']; dy = dict(zip(dt[1:], np.diff(ct)))
dg, _, cg, _ = S['_GSPC']; rg = np.diff(np.log(cg)); dgg = dg[1:]
k = [i for i, x in enumerate(dgg) if x in dy]; x = np.array([dy[dgg[i]] for i in k]); y = rg[k]; d2 = [dgg[i] for i in k]
for en, s, e in ERAS + [('2022-', '2022-01-01', asof)]:
    m = mask(d2, s, e) & (x != 0)
    if m.sum() < 400: continue
    put('_GSPC vs d10y: corr / same-sign days %', en, f"{round(float(np.corrcoef(x[m], y[m])[0,1]),2)} / {round(100*float(np.mean(np.sign(x[m]) == np.sign(y[m]))),1)}")
json.dump(out, open(outp, 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
