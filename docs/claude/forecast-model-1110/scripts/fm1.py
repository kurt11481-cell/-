#!/usr/bin/env python3
"""FM-1 walk-forward density-forecast scoring (pre-registered, display/score only).

Spec = forecast-model-prereg-2026-11-10.md (same folder, one level up). This file is the
executable form of that spec; its sha256 is fixed before the first run on real data.
No orders, no policy/state/core-input change. Reference data (Yahoo index closes).

usage:
  python3 -I fm1.py selftest
  python3 -I fm1.py run <inputs_dir> <asof YYYY-MM-DD> <out_json> [--boot N]
"""
import json, math, os, sys, datetime
import numpy as np

TARGETS = ['_SOX', '_NDX', '_GSPC']
HORIZONS = [20, 60, 250]
GRID_STEP = 5
GRID_START = '2005-01-01'
HIST_FLOOR = '1962-01-02'          # rates start; earlier target rows are not used
MIN_HIST = 260                      # first usable candidate index in a target series
B_WIN = 252                         # B1/B2 window (evolve-1029 11-3)
B3_WIN = 2520                       # B3 window (10y); B3s = 252 (h=20 only)
LAM = 0.94                          # M1 EWMA lambda
HALF = 60.0                         # M1 variance mean-reversion half-life (trading days)
KFRAC = 0.10                        # M2 neighbour fraction
KMIN = 60
QN = 199                            # quantile representation
QL = (np.arange(QN) + 0.5) / QN
ERAS = [('E1 2005-2012', '2005-01-01', '2012-12-31'),
        ('E2 2013-2019', '2013-01-01', '2019-12-31'),
        ('E3 2020-', '2020-01-01', '2099-12-31')]
NEIGHBOURS = [(0.90, 0.10), (0.97, 0.10), (0.94, 0.05), (0.94, 0.20)]
SEED = 20261110


# ---------- data ----------
def load_yahoo(path):
    d = json.load(open(path))['chart']['result'][0]
    ts = d['timestamp']; cl = d['indicators']['quote'][0]['close']
    out = {}
    for t, c in zip(ts, cl):
        if c is None or not (c > 0):
            continue
        day = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%d')
        out[day] = float(c)
    days = sorted(out)
    return days, np.array([out[x] for x in days])


def ffill_to(days, src_days, src_vals):
    """value of src at or before each day (nan if none)."""
    idx = np.searchsorted(np.array(src_days), np.array(days), side='right') - 1
    v = np.where(idx >= 0, src_vals[np.clip(idx, 0, len(src_vals) - 1)], np.nan)
    return v


# ---------- per-series precompute ----------
def ewma_var(r, lam):
    v = np.empty(len(r)); v[:] = np.nan
    if len(r) < 21:
        return v
    cur = float(np.mean(r[1:21] ** 2))
    for i in range(21, len(r)):
        cur = lam * cur + (1 - lam) * r[i] ** 2
        v[i] = cur
    return v


def expanding_var(r):
    v = np.empty(len(r)); v[:] = np.nan
    cs = np.cumsum(np.r_[0.0, r[1:]]); cs2 = np.cumsum(np.r_[0.0, r[1:] ** 2])
    n = np.arange(len(r)).astype(float)
    ok = n >= 250
    m = cs[ok] / n[ok]
    v[ok] = cs2[ok] / n[ok] - m ** 2
    return v


def roll_std_mean(r, w):
    s = np.empty(len(r)); s[:] = np.nan; m = s.copy()
    cs = np.cumsum(np.r_[0.0, r[1:]]); cs2 = np.cumsum(np.r_[0.0, r[1:] ** 2])
    i = np.arange(w, len(r))
    mm = (cs[i] - cs[i - w]) / w
    vv = (cs2[i] - cs2[i - w]) / w - mm ** 2
    m[i] = mm; s[i] = np.sqrt(np.maximum(vv, 1e-18) * w / (w - 1))
    return s, m


def roll_max(x, w):
    out = np.empty(len(x)); out[:] = np.nan
    from collections import deque
    dq = deque()
    for i, v in enumerate(x):
        while dq and x[dq[-1]] <= v:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - w:
            dq.popleft()
        if i >= w - 1:
            out[i] = x[dq[0]]
    return out


def w_h(h, half):
    k = np.arange(1, h + 1)
    return float(np.mean(0.5 ** (k / half)))


class Series:
    def __init__(self, days, close, tnx, irx):
        self.days = days; self.c = close; self.lc = np.log(close)
        self.r = np.r_[0.0, np.diff(self.lc)]
        self.s252, self.m252 = roll_std_mean(self.r, B_WIN)
        s20, _ = roll_std_mean(self.r, 20)
        self.exp_var = expanding_var(self.r)
        self.ew = {}
        n = len(close)
        f = np.full((6, n), np.nan)
        mx = roll_max(close, 252)
        f[0] = np.log(close / mx)
        f[1, 250:] = self.lc[250:] - self.lc[:-250]
        f[2, 60:] = self.lc[60:] - self.lc[:-60]
        f[3] = np.log(s20 / self.s252)
        f[4, 60:] = tnx[60:] - tnx[:-60]
        f[5] = tnx - irx
        self.f = f

    def vh(self, h, lam):
        if lam not in self.ew:
            self.ew[lam] = ewma_var(self.r, lam)
        w = w_h(h, HALF)
        return np.sqrt(w * self.ew[lam] + (1 - w) * self.exp_var)

    def y(self, h):
        out = np.full(len(self.c), np.nan)
        out[:-h] = self.lc[h:] - self.lc[:-h]
        return out


# ---------- scoring ----------
def crps_w(x, w, y):
    """CRPS of a weighted sample (weights sum to 1)."""
    o = np.argsort(x); x = x[o]; w = w[o]
    cw = np.cumsum(w)
    e1 = float(np.sum(w * np.abs(x - y)))
    e2 = float(2.0 * np.sum(w * x * (2 * cw - w - 1.0)))
    return e1 - 0.5 * e2


def crps_norm(mu, sd, y):
    z = (y - mu) / sd
    pdf = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return sd * (z * (2 * cdf - 1) + 2 * pdf - 1 / math.sqrt(math.pi))


def wquant(x, w, q):
    o = np.argsort(x); x = x[o]; cw = np.cumsum(w[o])
    return x[np.minimum(np.searchsorted(cw, q, side='left'), len(x) - 1)]


def to_q(sample):
    return np.quantile(sample, QL)


NORM_Q = None


def norm_q():
    global NORM_Q
    if NORM_Q is None:
        # inverse normal cdf by bisection (no scipy dependency)
        def inv(p):
            lo, hi = -10.0, 10.0
            for _ in range(80):
                mid = (lo + hi) / 2
                if 0.5 * (1 + math.erf(mid / math.sqrt(2))) < p:
                    lo = mid
                else:
                    hi = mid
            return (lo + hi) / 2
        NORM_Q = {0.1: inv(0.1), 0.9: inv(0.9)}
    return NORM_Q


def forecasts(S, i, h, lam=LAM, kfrac=KFRAC, want=('B1', 'B2', 'B3', 'B3s', 'M1', 'M2', 'M3', 'M4')):
    """Forecasts for target series S at index i, horizon h, using only data <= i.
    Returns dict name -> ('norm', mu, sd) or ('samp', x, w)."""
    out = {}
    sd = S.s252[i] * math.sqrt(h)
    out['B1'] = ('norm', 0.0, sd)
    out['B2'] = ('norm', S.m252[i] * h, sd)
    yh = S.y(h)
    last = i - h                                   # last start whose outcome is known at i
    lo3 = max(MIN_HIST, i - B3_WIN)
    b3 = yh[lo3:last + 1]
    b3 = b3[np.isfinite(b3)]
    qb3 = to_q(b3)
    eq = np.full(QN, 1.0 / QN)
    out['B3'] = ('samp', qb3, eq)
    if h == 20:
        b3s = yh[max(MIN_HIST, i - B_WIN):last + 1]
        out['B3s'] = ('samp', to_q(b3s[np.isfinite(b3s)]), eq)
    cand = np.arange(MIN_HIST, last + 1)
    # M1
    v = S.vh(h, lam)
    z = yh[cand] / (v[cand] * math.sqrt(h))
    z = z[np.isfinite(z)]
    q1 = to_q(z) * v[i] * math.sqrt(h)
    out['M1'] = ('samp', q1, eq)
    # M2
    F = S.f[:, MIN_HIST:i + 1]                      # features known up to i
    ok = np.all(np.isfinite(F), axis=0)
    n_all = int(ok.sum())
    ranks = np.full(F.shape, np.nan)
    for k in range(F.shape[0]):
        col = F[k, ok]
        ranks[k, ok] = (np.argsort(np.argsort(col)) + 0.5) / n_all
    cur = ranks[:, -1]
    cr = ranks[:, :len(cand)]
    okc = np.all(np.isfinite(cr), axis=0) & np.isfinite(yh[cand])
    d = np.sqrt(np.sum((cr[:, okc] - cur[:, None]) ** 2, axis=0))
    k = max(KMIN, int(round(kfrac * int(okc.sum()))))
    k = min(k, int(okc.sum()))
    nb = np.argpartition(d, k - 1)[:k]
    q2 = to_q(yh[cand][okc][nb])
    out['M2'] = ('samp', q2, eq)
    out['M3'] = ('samp', np.r_[q2, qb3], np.r_[eq, eq] / 2)
    out['M4'] = ('samp', np.r_[q1, q2, qb3], np.r_[eq, eq, eq] / 3)
    return {k2: v2 for k2, v2 in out.items() if k2 in want}


def score(fc, y):
    if fc[0] == 'norm':
        _, mu, sd = fc
        nq = norm_q()
        lo, hi = mu + sd * nq[0.1], mu + sd * nq[0.9]
        return crps_norm(mu, sd, y), float(lo <= y <= hi)
    _, x, w = fc
    lo, hi = wquant(x, w, 0.1), wquant(x, w, 0.9)
    return crps_w(x, w, y), float(lo <= y <= hi)


def block_boot(num, den, cov, block, nboot, rng):
    """num/den: arrays [n_starts] of summed CRPS (model / best baseline); cov [n_starts] mean coverage.
    moving-block bootstrap over starts."""
    n = len(num); nb = int(math.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(nboot, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(nboot, -1)[:, :n]
    p1 = 1 - num[idx].sum(1) / den[idx].sum(1)
    cv = cov[idx].mean(1)
    return (np.percentile(p1, [2.5, 97.5]).tolist(), np.percentile(cv, [2.5, 97.5]).tolist())


def evaluate(series, grid_days, asof_idx, nboot=10000, lam=LAM, kfrac=KFRAC, models=None, boot=True):
    """series: dict target -> Series; grid_days: list of start dates (common calendar)."""
    rng = np.random.default_rng(SEED)
    res = {}
    for h in HORIZONS:
        names = ['B1', 'B2', 'B3'] + (['B3s'] if h == 20 else []) + ['M1', 'M2', 'M3', 'M4']
        if models:
            names = [n for n in names if n[0] == 'B' or n in models]
        rows = []                                  # per start: date, {name: [crps per target]}, cov
        for day in grid_days:
            cr = {n: [] for n in names}; cv = {n: [] for n in names}; good = True
            for t in TARGETS:
                S = series[t]
                i = S.idx[day]
                if i + h > asof_idx[t]:
                    good = False; break
                y = S.y(h)[i]
                fc = forecasts(S, i, h, lam, kfrac, want=names)
                for n in names:
                    c, k = score(fc[n], y)
                    cr[n].append(c); cv[n].append(k)
            if good:
                rows.append((day, cr, cv))
        days = [r[0] for r in rows]
        C = {n: np.array([r[1][n] for r in rows]) for n in names}       # [starts, targets]
        K = {n: np.array([r[2][n] for r in rows]) for n in names}
        base = [n for n in names if n[0] == 'B']
        best = min(base, key=lambda n: C[n].sum())
        block = h // GRID_STEP
        hr = {'n_starts': len(days), 'first': days[0], 'last': days[-1], 'block': block,
              'indep_blocks': round(len(days) / block, 2), 'best_baseline': best,
              'crps_sum': {n: float(C[n].sum()) for n in names}, 'models': {}}
        for n in names:
            if n[0] == 'B':
                continue
            num = C[n].sum(1); den = C[best].sum(1); cov = K[n].mean(1)
            m = {'P1': float(1 - num.sum() / den.sum()), 'P2_cov80': float(cov.mean()),
                 'P1_vs': {b: float(1 - C[n].sum() / C[b].sum()) for b in base},
                 'P1_by_target': {t: float(1 - C[n][:, j].sum() / C[best][:, j].sum()) for j, t in enumerate(TARGETS)},
                 'P1_by_era': {}}
            for en, a, b in ERAS:
                mk = np.array([(a <= d <= b) for d in days])
                if mk.sum() >= block:
                    m['P1_by_era'][en] = {'P1': float(1 - num[mk].sum() / den[mk].sum()), 'n': int(mk.sum()),
                                          'cov80': float(cov[mk].mean())}
            if boot:
                ci1, ci2 = block_boot(num, den, cov, block, nboot, rng)
                m['P1_ci95'] = ci1; m['P2_ci95'] = ci2
                m['pass_P1'] = bool(m['P1'] > 0 and ci1[0] > 0)
                m['pass_P2'] = bool(ci2[0] <= 0.80 <= ci2[1])
            hr['models'][n] = m
        hr['baseline_cov80'] = {b: float(K[b].mean()) for b in base}
        res[str(h)] = hr
    return res


def build(inputs, asof):
    tnx_d, tnx_v = load_yahoo(os.path.join(inputs, '_TNX.json'))
    irx_d, irx_v = load_yahoo(os.path.join(inputs, '_IRX.json'))
    series = {}; asof_idx = {}
    for t in TARGETS:
        d, c = load_yahoo(os.path.join(inputs, t + '.json'))
        keep = [k for k, x in enumerate(d) if HIST_FLOOR <= x <= asof]
        d = [d[k] for k in keep]; c = c[keep]
        S = Series(d, c, ffill_to(d, tnx_d, tnx_v), ffill_to(d, irx_d, irx_v))
        S.idx = {x: k for k, x in enumerate(d)}
        series[t] = S; asof_idx[t] = len(d) - 1
    common = sorted(set.intersection(*[set(series[t].days) for t in TARGETS]))
    common = [x for x in common if x >= GRID_START]
    grid = common[::GRID_STEP]
    return series, asof_idx, grid, common


def current(series, common):
    day = common[-1]; out = {'asof': day, 'targets': {}}
    for t in TARGETS:
        S = series[t]; i = S.idx[day]; out['targets'][t] = {}
        for h in HORIZONS:
            fc = forecasts(S, i, h)
            row = {}
            for n in ('B3', 'M1', 'M2', 'M4'):
                _, x, w = fc[n]
                qs = {str(q): float(math.exp(wquant(x, w, q)) - 1) for q in (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)}
                qs['p_up'] = float(np.sum(w[x > 0]))
                qs['p_below_-20%'] = float(np.sum(w[x < math.log(0.8)]))
                row[n] = qs
            out['targets'][t][str(h)] = row
    return out


def selftest():
    rng = np.random.default_rng(1)
    # crps check: weighted sample from N(0,1) vs closed form
    x = np.sort(rng.standard_normal(200000)); q = np.quantile(x, QL)
    a = crps_w(q, np.full(QN, 1 / QN), 0.3); b = crps_norm(0, 1, 0.3)
    assert abs(a - b) < 5e-3, (a, b)
    assert abs(wquant(q, np.full(QN, 1 / QN), 0.5)) < 0.02
    # synthetic series: (a) iid normal, (b) vol clustering. M1 should be ~0 on (a), > 0 on (b)
    n = 9000
    days = [(datetime.date(1990, 1, 1) + datetime.timedelta(days=k)).isoformat() for k in range(n)]
    out = {}
    for name in ('iid', 'garch'):
        ser = {}
        for j, t in enumerate(TARGETS):
            e = rng.standard_normal(n)
            if name == 'iid':
                r = 0.0003 + 0.012 * e
            else:
                v = np.empty(n); v[0] = 0.012 ** 2; r = np.empty(n)
                for k in range(n):
                    if k:
                        v[k] = 2e-6 + 0.09 * r[k - 1] ** 2 + 0.90 * v[k - 1]
                    r[k] = 0.0003 + math.sqrt(v[k]) * e[k]
            c = 100 * np.exp(np.cumsum(r))
            S = Series(days, c, 4 + np.cumsum(rng.standard_normal(n)) * 0.02, np.full(n, 3.0))
            S.idx = {x: k for k, x in enumerate(days)}
            ser[t] = S
        grid = [d for d in days if d >= '2000-01-01'][::GRID_STEP * 4]
        global HORIZONS
        keep = HORIZONS; HORIZONS = [20]
        r = evaluate(ser, grid, {t: n - 1 for t in TARGETS}, nboot=500)
        HORIZONS = keep
        out[name] = {m: round(v['P1'], 4) for m, v in r['20']['models'].items()}
        out[name]['best'] = r['20']['best_baseline']
        out[name]['cov'] = {m: round(v['P2_cov80'], 3) for m, v in r['20']['models'].items()}
    print(json.dumps(out, indent=1))
    assert out['garch']['M1'] > 0.0, out
    assert abs(out['iid']['M1']) < 0.03, out
    # no-lookahead check: changing future prices must not change a forecast
    S = ser['_SOX']; i = 5000
    f1 = forecasts(S, i, 20)
    c2 = S.c.copy(); c2[i + 1:] *= 1.5
    S2 = Series(days, c2, S.f[4] * 0 + 4.0, np.full(n, 3.0)); S3 = Series(days, S.c, S.f[4] * 0 + 4.0, np.full(n, 3.0))
    a = forecasts(S2, i, 20); b = forecasts(S3, i, 20)
    for k in a:
        assert np.allclose(a[k][1], b[k][1]), k
    print('selftest OK')


if __name__ == '__main__':
    if sys.argv[1] == 'selftest':
        selftest(); sys.exit(0)
    inputs, asof, outp = sys.argv[2], sys.argv[3], sys.argv[4]
    nboot = int(sys.argv[sys.argv.index('--boot') + 1]) if '--boot' in sys.argv else 10000
    series, asof_idx, grid, common = build(inputs, asof)
    main = evaluate(series, grid, asof_idx, nboot=nboot)
    nb = {}
    for lam, kf in NEIGHBOURS:
        r = evaluate(series, grid, asof_idx, lam=lam, kfrac=kf, models=['M4'], boot=False)
        nb[f'lam{lam}_k{kf}'] = {h: r[h]['models']['M4']['P1'] for h in r}
    res = {'spec': 'FM-1 prereg 2026-11-10', 'asof': asof, 'grid_n': len(grid), 'nboot': nboot,
           'script_sha256': __import__('hashlib').sha256(open(__file__, 'rb').read()).hexdigest(),
           'series': {t: {'first': series[t].days[0], 'last': series[t].days[-1], 'n': len(series[t].days)} for t in TARGETS},
           'main': main, 'neighbours_M4_P1': nb, 'current': current(series, common)}
    json.dump(res, open(outp, 'w'), indent=1)
    print('written', outp)
