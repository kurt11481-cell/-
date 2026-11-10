#!/usr/bin/env python3
"""Descriptive era comparison (reference, Yahoo). usage: python3 -I era_stats.py inputs/yh 2026-11-06"""
import json, sys, os, datetime, math
import numpy as np
inp, asof = sys.argv[1], sys.argv[2]
ERAS = [('1990s', '1990-01-01', '1999-12-31'), ('2000s', '2000-01-01', '2009-12-31'),
        ('2010s', '2010-01-01', '2019-12-31'), ('2020s', '2020-01-01', asof)]
def load(sym):
    d = json.load(open(os.path.join(inp, sym + '.json')))['chart']['result'][0]
    q = d['indicators']['quote'][0]; rows = []
    for k, t in enumerate(d['timestamp']):
        c = q['close'][k]; o = q['open'][k]
        if c is None or c <= 0: continue
        day = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%d')
        if day > asof: continue
        rows.append((day, o if o and o > 0 else float('nan'), c))
    return [r[0] for r in rows], np.array([r[1] for r in rows]), np.array([r[2] for r in rows])
def mask(days, a, b): return np.array([a <= x <= b for x in days])
out = {}
def put(k, era, v): out.setdefault(k, {})[era] = v
S = {s: load(s) for s in ['_GSPC', '_NDX', '_SOX', '_VIX', 'SPY', 'QQQ', 'SOXX', 'RSP', 'TLT', '_TNX']}
def rets(sym):
    d, o, c = S[sym]; return d[1:], np.diff(np.log(c))
for sym in ['_GSPC', '_NDX', '_SOX']:
    d, r = rets(sym); dd, o, c = S[sym]
    for en, a, b in ERAS:
        m = mask(d, a, b)
        if m.sum() < 500: continue
        x = r[m]
        put(sym + ' ann_ret%', en, round(100 * (math.exp(x.mean() * 252) - 1), 1))
        put(sym + ' ann_vol%', en, round(100 * x.std() * math.sqrt(252), 1))
        put(sym + ' days|r|>2%_share%', en, round(100 * np.mean(np.abs(x) > 0.02), 1))
        put(sym + ' days|r|>4%_share%', en, round(100 * np.mean(np.abs(x) > 0.04), 2))
        put(sym + ' lag1_autocorr', en, round(float(np.corrcoef(x[1:], x[:-1])[0, 1]), 3))
        w = np.add.reduceat(x[:len(x) // 5 * 5], np.arange(0, len(x) // 5 * 5, 5))
        put(sym + ' weekly_lag1_autocorr', en, round(float(np.corrcoef(w[1:], w[:-1])[0, 1]), 3))
# drawdown episodes
def episodes(days, c, thr):
    eps = []; peak = c[0]; pi = 0; i = 0; n = len(c)
    while i < n:
        if c[i] >= peak: peak = c[i]; pi = i; i += 1; continue
        if c[i] / peak - 1 <= -thr:
            j = i; ti = i
            while j < n and c[j] < peak:
                if c[j] < c[ti]: ti = j
                j += 1
            eps.append(dict(peak=days[pi], trough=days[ti], depth=c[ti] / peak - 1, down=ti - pi,
                            up=(j - ti) if j < n else None))
            if j >= n: break
            peak = c[j]; pi = j; i = j + 1
        else: i += 1
    return eps
for sym, thr in [('_GSPC', 0.10), ('_NDX', 0.10), ('_SOX', 0.20)]:
    d, o, c = S[sym]; eps = episodes(d, c, thr)
    for en, a, b in ERAS:
        e = [x for x in eps if a <= x['peak'] <= b]
        if not e: continue
        ups = [x['up'] for x in e if x['up'] is not None]
        put(f'{sym} dd>={int(thr*100)}% episodes: n / median days down / median days to recover / median depth%', en,
            f"{len(e)} / {int(np.median([x['down'] for x in e]))} / {int(np.median(ups)) if ups else 'NA'}{'' if len(ups)==len(e) else ' (open %d)'%(len(e)-len(ups))} / {round(100*float(np.median([x['depth'] for x in e])),1)}")
out['_SOX episodes list (peak,trough,depth%,down,up)'] = [(x['peak'], x['trough'], round(100 * x['depth'], 1), x['down'], x['up']) for x in episodes(S['_SOX'][0], S['_SOX'][2], 0.20) if x['peak'] >= '2010']
# speed: worst 20d decline -> how fast; share of dd>=10% reached within 20 days
# overnight vs intraday
for sym in ['SPY', 'QQQ', 'SOXX']:
    d, o, c = S[sym]
    on = np.log(o[1:] / c[:-1]); intr = np.log(c[1:] / o[1:]); dd = d[1:]
    for en, a, b in ERAS:
        m = mask(dd, a, b) & np.isfinite(on) & np.isfinite(intr)
        if m.sum() < 500: continue
        yrs = m.sum() / 252
        put(sym + ' overnight / intraday ann log-ret %', en, f"{round(100*on[m].sum()/yrs,1)} / {round(100*intr[m].sum()/yrs,1)}")
        put(sym + ' overnight share of abs move %', en, round(100 * np.abs(on[m]).sum() / (np.abs(on[m]).sum() + np.abs(intr[m]).sum()), 1))
        big = m & ((on + intr) <= -0.03)
        if big.sum() >= 5:
            put(sym + ' on days<=-3%: gap share of loss % (n)', en, f"{round(100*on[big].sum()/(on[big]+intr[big]).sum(),0)} ({int(big.sum())})")
# SOX vs GSPC
def align(a, b):
    da, ra = rets(a); db, rb = rets(b); ib = {x: k for k, x in enumerate(db)}
    k = [(i, ib[x]) for i, x in enumerate(da) if x in ib]
    return [da[i] for i, _ in k], ra[[i for i, _ in k]], rb[[j for _, j in k]]
for a, b in [('_SOX', '_GSPC'), ('_NDX', '_GSPC'), ('SPY', 'TLT'), ('RSP', 'SPY')]:
    d, ra, rb = align(a, b)
    for en, s, e in ERAS:
        m = mask(d, s, e)
        if m.sum() < 500: continue
        cc = float(np.corrcoef(ra[m], rb[m])[0, 1]); beta = cc * ra[m].std() / rb[m].std()
        put(f'{a} vs {b}: corr / beta / ann ret gap %p', en, f"{round(cc,2)} / {round(beta,2)} / {round(100*(ra[m].mean()-rb[m].mean())*252,1)}")
# stocks vs yield change
d, o, c = S['_TNX']; dy = dict(zip(d[1:], np.diff(c)))
dg, rg = rets('_GSPC'); dn, rn = rets('_NDX')
for nm, dd, rr in [('_GSPC', dg, rg), ('_NDX', dn, rn)]:
    k = [i for i, x in enumerate(dd) if x in dy]; x = np.array([dy[dd[i]] for i in k]); y = rr[k]; d2 = [dd[i] for i in k]
    for en, s, e in ERAS + [('2022-', '2022-01-01', asof)]:
        m = mask(d2, s, e)
        if m.sum() < 400: continue
        put(nm + ' corr(daily ret, d10y yield)', en, round(float(np.corrcoef(x[m], y[m])[0, 1]), 2))
# momentum / dip
for sym in ['_GSPC', '_NDX', '_SOX']:
    d, o, c = S[sym]; lc = np.log(c); n = len(c)
    idx = np.arange(250, n - 60, 20)
    past = lc[idx] - lc[idx - 250]; fut = lc[idx + 60] - lc[idx]; dd = [d[i] for i in idx]
    for en, s, e in ERAS:
        m = mask(dd, s, e)
        if m.sum() < 60: continue
        up = m & (past > 0); dn_ = m & (past <= 0)
        put(sym + ' trend: P(next60d up | past250d up) / P(up | past down) / n', en,
            f"{round(100*np.mean(fut[up]>0))}% / {round(100*np.mean(fut[dn_]>0)) if dn_.sum()>=8 else 'NA'}% / {int(up.sum())}+{int(dn_.sum())}")
    r5 = lc[5:] - lc[:-5]; sd = np.array([np.std(np.diff(lc[max(0, i - 252):i + 1])) if i > 60 else np.nan for i in range(5, n)]) * math.sqrt(5)
    f20 = np.full(n - 5, np.nan); f20[:n - 25] = lc[25:] - lc[5:n - 20]
    dd5 = d[5:]
    for en, s, e in ERAS:
        m = mask(dd5, s, e) & np.isfinite(f20) & np.isfinite(sd)
        hit = m & (r5 <= -2 * sd)
        # de-cluster: keep first of consecutive
        hi = np.where(hit)[0]; keep = [hi[k] for k in range(len(hi)) if k == 0 or hi[k] - hi[k - 1] > 20]
        if len(keep) >= 5:
            put(sym + ' dip(5d<=-2sig): next20d median % / P(up) / n ; all-days P(up)', en,
                f"{round(100*float(np.median(f20[keep])),1)} / {round(100*np.mean(f20[keep]>0))}% / {len(keep)} ; {round(100*np.mean(f20[m]>0))}%")
# VIX
d, o, c = S['_VIX']
for en, s, e in ERAS:
    m = mask(d, s, e); x = c[m]
    put('VIX mean / share days>30 %', en, f"{round(float(x.mean()),1)} / {round(100*np.mean(x>30),1)}")
    idx = np.where(m)[0]; sp = []; i = 0
    while i < len(idx):
        k = idx[i]
        if c[k] > 30 and (k == 0 or c[k - 1] <= 30):
            j = k
            while j < len(c) and c[j] > 20: j += 1
            sp.append(j - k); 
        i += 1
    if sp: put('VIX spike>30 -> back below 20: median days (n)', en, f"{int(np.median(sp))} ({len(sp)})")
print(json.dumps(out, ensure_ascii=False, indent=1))
