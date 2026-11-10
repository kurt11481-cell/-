#!/usr/bin/env python3
"""FM-2: self-improving (online-learning) density forecast, walk-forward scoring on a universe
that FM-1 never touched. Display/score only: no orders, no policy/state/core-input change.

Spec = forecast-model-fm2-prereg-2026-11-10.md (one level up). This file is the executable form of
that spec; its sha256 is fixed before the first run on real data. The four experts are the FM-1
definitions imported from fm1.py (hash-fixed 2026-11-10 08:54 KST), at 99 quantiles.

Self-improvement inside the model (all deterministic, fixed in advance):
  level 1  expert weights learned from matured forecasts (exponential weights on normalised CRPS)
  level 2  the learning speed itself is learned: 9 (eta, half-life) learners + 1 "do not learn"
           learner are combined by their own realised scores
  width    the 80% band is re-scaled so that past matured forecasts would have had 80% coverage
Nothing uses an outcome that was not known on an earlier calendar date.

Judged intervals are t intervals over q consecutive time groups (GROUPS_Q). The moving-block
bootstrap of FM-1 is kept as a reference only: boot_calib.py (synthetic data) shows it is too narrow.
80% bands use interpolated quantiles (wq), not fm1.wquant.

usage:
  python3 -I fm2.py selftest
  python3 -I fm2.py experts <inputs_dir> <rates_dir> <asof YYYY-MM-DD> <cache_dir> [--jobs N]
  python3 -I fm2.py learn <cache_dir> <out_json> [--boot N]
  python3 -I fm2.py current <result_json> <index_inputs_dir> <rates_dir> <asof> <out_json>
"""
import sys, os, json, math, datetime, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fm1
from statistics import NormalDist

QN = 99
fm1.QN = QN
fm1.QL = (np.arange(QN) + 0.5) / QN
ZQ = np.array([NormalDist().inv_cdf(float(p)) for p in fm1.QL])
Z10, Z90 = NormalDist().inv_cdf(0.1), NormalDist().inv_cdf(0.9)

# universe (file stem, class, rate lag in days: 1 = use the previous US close for non-US markets)
UNIVERSE = [('XLE', 'sector', 0), ('XLF', 'sector', 0), ('XLV', 'sector', 0), ('XLI', 'sector', 0),
            ('XLP', 'sector', 0), ('XLU', 'sector', 0), ('XLY', 'sector', 0), ('XLB', 'sector', 0),
            ('IWM', 'smallcap', 0),
            ('_N225', 'intl', 1), ('_GDAXI', 'intl', 1), ('_FTSE', 'intl', 1), ('_HSI', 'intl', 1), ('_KS11', 'intl', 1),
            ('MU', 'stock', 0), ('AMD', 'stock', 0), ('PWR', 'stock', 0), ('NVDA', 'stock', 0),
            ('MSFT', 'stock', 0), ('AMZN', 'stock', 0)]
HORIZONS = [20, 60, 250]
GRID_STEP = 5
LEARN_START = '2000-01-01'      # forecasts are issued from here (burn-in for the learner)
SCORE_START = '2005-01-01'      # judged forecasts start here (same as FM-1)
MIN_ROWS = 1260                 # an asset needs 5 years of history before its first forecast
EXPERTS = ['B1', 'B3', 'M1', 'M2']
K = len(EXPERTS)
BASES = ['B1', 'B2', 'B3', 'B3s']
ETAS = [0.5, 2.0, 8.0]
HALFS = [365.0, 1826.0, float('inf')]      # calendar days
ETA_TOP = 2.0
HC = 1826.0                     # calibration half-life (calendar days)
N0 = 10.0                       # calibration prior strength (independent periods at scale 1)
COVER = 0.80
RECENT_BAND = (0.70, 0.90)      # C2b: coverage of forecasts started 2020-01 or later must be inside
POOLED_BAND = (0.75, 0.85)      # C2c: coverage of all scored forecasts must be inside
GROUPS_Q = {20: 4, 60: 4, 250: 8}     # judged interval: t interval over q consecutive time groups (picked by boot_calib.py, synthetic only)
BLOCK_MULT = {20: 1, 60: 1, 250: 1}   # reference only: moving-block bootstrap, block = BLOCK_MULT[h] * h/5 weeks (as in FM-1)
NEIGHBOURS = [('eta_top1', dict(eta_top=1.0)), ('eta_top4', dict(eta_top=4.0)),
              ('hc912', dict(hc=912.0)), ('hc_inf', dict(hc=float('inf')))]
ERAS = fm1.ERAS
SEED = 20261111


def ordinal(day):
    return datetime.date.fromisoformat(day).toordinal()


def isoweek(o):
    y, w, _ = datetime.date.fromordinal(int(o)).isocalendar()
    return y * 100 + w


# ---------------- stage A: experts ----------------
def lag_fill(days, src_days, src_vals, lag):
    side = 'right' if lag == 0 else 'left'
    idx = np.searchsorted(np.array(src_days), np.array(days), side=side) - 1
    return np.where(idx >= 0, src_vals[np.clip(idx, 0, len(src_vals) - 1)], np.nan)


def build_series(days, close, tnx_d, tnx_v, irx_d, irx_v, lag):
    S = fm1.Series(days, close, lag_fill(days, tnx_d, tnx_v, lag), lag_fill(days, irx_d, irx_v, lag))
    S.idx = {x: k for k, x in enumerate(days)}
    return S


def expert_rows(S, learn_start=LEARN_START, min_rows=MIN_ROWS, horizons=HORIZONS):
    """All forecasts of one asset. Returns dict of arrays."""
    n = len(S.days)
    first = next((i for i in range(min_rows, n) if S.days[i] >= learn_start), None)
    out = {k: [] for k in ('start', 'mat', 'h', 'y', 'norm', 'Q', 'bc', 'bh')}
    if first is None:
        return None
    ords = [ordinal(d) for d in S.days]
    for i in range(first, n, GRID_STEP):
        for h in horizons:
            fc = fm1.forecasts(S, i, h, want=('B1', 'B2', 'B3', 'B3s', 'M1', 'M2'))
            sd = fc['B1'][2]
            if not (np.isfinite(sd) and sd > 0):
                continue
            Q = np.stack([sd * ZQ, fc['B3'][1], fc['M1'][1], fc['M2'][1]]).astype(np.float32)
            matured = i + h <= n - 1
            y = float(S.lc[i + h] - S.lc[i]) if matured else float('nan')
            bc = [float('nan')] * 4; bh = [float('nan')] * 4
            if matured:
                for b, name in enumerate(BASES):
                    if name in fc:
                        bc[b], bh[b] = score_fc(fc[name], y)
            out['start'].append(ords[i]); out['mat'].append(ords[i + h] if matured else -1)
            out['h'].append(h); out['y'].append(y); out['norm'].append(sd); out['Q'].append(Q)
            out['bc'].append(bc); out['bh'].append(bh)
    return {k: np.array(v) for k, v in out.items()}


def _one(args):
    stem, cls, lag, inputs, rates, asof, cache = args
    tnx_d, tnx_v = fm1.load_yahoo(os.path.join(rates, '_TNX.json'))
    irx_d, irx_v = fm1.load_yahoo(os.path.join(rates, '_IRX.json'))
    d, c = fm1.load_yahoo(os.path.join(inputs, stem + '.json'))
    keep = [k for k, x in enumerate(d) if fm1.HIST_FLOOR <= x <= asof]
    d = [d[k] for k in keep]; c = c[keep]
    S = build_series(d, c, tnx_d, tnx_v, irx_d, irx_v, lag)
    R = expert_rows(S)
    r = np.diff(np.log(c))
    info = {'stem': stem, 'class': cls, 'first': d[0], 'last': d[-1], 'rows': len(d),
            'n_forecasts': 0 if R is None else int(len(R['h'])), 'days_abs_ret_gt_30pct': int(np.sum(np.abs(r) > 0.3))}
    if R is not None:
        np.savez(os.path.join(cache, stem + '.npz'), **R)
    json.dump(info, open(os.path.join(cache, stem + '.json'), 'w'))
    return info


def stage_experts(inputs, rates, asof, cache, jobs):
    os.makedirs(cache, exist_ok=True)
    args = [(s, c, l, inputs, rates, asof, cache) for s, c, l in UNIVERSE]
    if jobs > 1:
        import multiprocessing as mp
        with mp.Pool(jobs) as p:
            infos = p.map(_one, args, chunksize=1)
    else:
        infos = [_one(a) for a in args]
    json.dump({'asof': asof, 'assets': infos}, open(os.path.join(cache, 'INDEX.json'), 'w'), indent=1)
    for i in infos:
        print(i)


# ---------------- stage B: learner ----------------
def pair_abs(Qa, Qb):
    """mean |a_i - b_j| over all pairs, row-wise. Qa, Qb: [n, q]."""
    out = np.empty(len(Qa))
    for s in range(0, len(Qa), 4000):
        a = Qa[s:s + 4000, :, None].astype(np.float64); b = Qb[s:s + 4000, None, :].astype(np.float64)
        out[s:s + 4000] = np.abs(a - b).mean(axis=(1, 2))
    return out


def prep(F):
    """F: dict with start, mat, y, norm, Q[n,K,q], asset, cls, bc, bh for ONE horizon. Adds A, D, u, week."""
    n = len(F['y']); Q = F['Q']
    o = np.argsort(F['start'], kind='stable')
    for k in list(F):
        if isinstance(F[k], np.ndarray) and len(F[k]) == n:
            F[k] = F[k][o]
    Q = F['Q']
    F['week'] = np.array([isoweek(x) for x in F['start']])
    wk, inv, cnt = np.unique(F['week'], return_inverse=True, return_counts=True)
    F['u'] = (GRID_STEP / F['h_val']) / cnt[inv]
    y = F['y'][:, None, None]
    with np.errstate(invalid='ignore'):
        F['A'] = np.abs(Q.astype(np.float64) - y).mean(axis=2) / F['norm'][:, None]      # nan when not matured
    D = np.empty((n, K, K))
    for a in range(K):
        for b in range(a, K):
            D[:, a, b] = D[:, b, a] = pair_abs(Q[:, a], Q[:, b]) / F['norm']
    F['D'] = D
    return F


def softmin(x, eta):
    z = -eta * (x - np.min(x))
    e = np.exp(z)
    return e / e.sum()


def wq(x, w, qs):
    """Quantiles of a weighted sample whose points stand for cell mid-points
    (mid-cumulative weight, linear interpolation). fm1.wquant picks the next point up/down and
    makes an 80% band about 0.8 point too wide at 99 points; this does not."""
    o = np.argsort(x, kind='stable'); x = x[o]; w = w[o]
    mid = (np.cumsum(w) - 0.5 * w) / float(np.sum(w))
    return [float(v) for v in np.interp(qs, mid, x)]


def score_fc(fc, y):
    """CRPS and 80% hit of one fm1 forecast tuple."""
    if fc[0] == 'norm':
        _, mu, sd = fc
        return fm1.crps_norm(mu, sd, y), float(mu + sd * Z10 <= y <= mu + sd * Z90)
    _, x, w = fc
    lo, hi = wq(x, w, [0.1, 0.9])
    return fm1.crps_w(x, w, y), float(lo <= y <= hi)


def learn(F, eta_top=ETA_TOP, hc=HC, learn_w=True, learn_s=True, n0=N0):
    """Online learner for one horizon. Returns per-forecast arrays (normalised CRPS of the issued
    forecast, 80% hit, weights, scale)."""
    n = len(F['y']); start = F['start']; mat = F['mat']; y = F['y']; norm = F['norm']
    A = F['A']; D = F['D']; Q = F['Q'].astype(np.float64); u = F['u']
    metas = [(e, H) for e in ETAS for H in HALFS]            # + static learner at the end
    nm = len(metas) + 1
    L = np.zeros((len(metas), K))                            # discounted expert losses per learner
    Mloss = np.zeros(nm)                                     # undiscounted learner losses
    Wm = np.zeros((n, nm, K)); W = np.full((n, K), 1.0 / K); sc = np.ones(n)
    pool = np.zeros((n, 3))                                  # unscaled pool median, q10, q90 at issue
    crps = np.full(n, np.nan); hit = np.full(n, np.nan)
    order_mat = np.array([j for j in np.argsort(mat, kind='stable') if mat[j] >= 0], dtype=int)
    pm = 0
    cal_r = np.empty(n); cal_u = np.empty(n); cal_t = np.empty(n); nc = 0     # kept sorted by r
    uniq = np.unique(start)
    lo = 0; t_prev = None
    ew = np.repeat(1.0 / QN, QN)
    for t in uniq:
        if t_prev is not None:
            dt = float(t - t_prev)
            for m, (e, H) in enumerate(metas):
                if math.isfinite(H):
                    L[m] *= 0.5 ** (dt / H)
        # 1. absorb forecasts that matured on an earlier calendar date
        while pm < len(order_mat) and mat[order_mat[pm]] < t:
            j = order_mat[pm]; pm += 1
            e_k = A[j] - 0.5 * np.diag(D[j])
            for m, (e, H) in enumerate(metas):
                dec = 0.5 ** (float(t - mat[j]) / H) if math.isfinite(H) else 1.0
                L[m] += u[j] * dec * e_k
            Mloss += u[j] * (Wm[j] @ A[j] - 0.5 * np.einsum('mk,kl,ml->m', Wm[j], D[j], Wm[j]))
            med, q10, q90 = pool[j]
            r = (y[j] - med) / max(q90 - med, 1e-12) if y[j] >= med else (med - y[j]) / max(med - q10, 1e-12)
            pos = int(np.searchsorted(cal_r[:nc], r, side='right'))
            for arr, val in ((cal_r, r), (cal_u, u[j]), (cal_t, float(mat[j]))):
                arr[pos + 1:nc + 1] = arr[pos:nc]
                arr[pos] = val
            nc += 1
        # 2. weights
        wm = np.vstack([softmin(L[m], e) for m, (e, H) in enumerate(metas)] + [np.full(K, 1.0 / K)])
        v = softmin(Mloss, eta_top)
        Wt = v @ wm if learn_w else np.full(K, 1.0 / K)
        # 3. scale
        s = 1.0
        if learn_s and nc:
            c_ = cal_u[:nc] * 0.5 ** ((t - cal_t[:nc]) / hc) if math.isfinite(hc) else cal_u[:nc]
            cw = np.cumsum(c_); neff = float(cw[-1])
            s_hat = float(cal_r[min(int(np.searchsorted(cw, COVER * neff, side='left')), nc - 1)])
            s = (neff * s_hat + n0 * 1.0) / (neff + n0)
        # 4. issue today's forecasts
        hi = lo
        while hi < n and start[hi] == t:
            hi += 1
        for j in range(lo, hi):
            Wm[j] = wm; W[j] = Wt; sc[j] = s
            x = Q[j].ravel(); w = np.repeat(Wt / QN, QN)
            med, q10, q90 = wq(x, w, [0.5, 0.1, 0.9])
            pool[j] = (med, q10, q90)
            if mat[j] >= 0:
                xs = med + s * (x - med)
                crps[j] = (float(np.sum(w * np.abs(xs - y[j]))) / norm[j]) - 0.5 * s * float(Wt @ D[j] @ Wt)
                hit[j] = float(med + s * (q10 - med) <= y[j] <= med + s * (q90 - med))
        lo = hi; t_prev = t
    return {'crps': crps, 'hit': hit, 'W': W, 's': sc, 'med': pool[:, 0].copy(),
            'meta_v_last': softmin(Mloss, eta_top).tolist(),
            'state_last': {'date': str(datetime.date.fromordinal(int(t_prev))), 'W': [float(z) for z in Wt], 's': float(s)}}


def week_boot(wk_ids, cols, block, nboot, rng):
    """cols: dict name -> per-forecast array (nan-free). Aggregates by week, moving-block bootstrap over weeks.
    Returns function-ready arrays of bootstrap sums: dict name -> [nboot]."""
    wk, inv = np.unique(wk_ids, return_inverse=True)
    agg = {k: np.bincount(inv, weights=v, minlength=len(wk)) for k, v in cols.items()}
    nw = len(wk); block = min(block, nw); nb = int(math.ceil(nw / block))
    st = rng.integers(0, nw - block + 1, size=(nboot, nb))
    idx = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(nboot, -1)[:, :nw]
    return {k: v[idx].sum(1) for k, v in agg.items()}, nw


def ci(a):
    return [float(x) for x in np.percentile(a, [2.5, 97.5])]


T975 = {3: 3.1824, 4: 2.7764, 5: 2.5706, 6: 2.4469, 7: 2.3646, 8: 2.3060, 9: 2.2622, 10: 2.2281, 11: 2.2010, 12: 2.1788}


def t_ci(v):
    """95% t interval of the mean of q group values (q - 1 degrees of freedom)."""
    v = np.asarray(v, dtype=float); q = len(v)
    half = T975[q - 1] * float(v.std(ddof=1)) / math.sqrt(q)
    return [float(v.mean() - half), float(v.mean() + half)]


def group_sums(wk_ids, cols, q):
    """Sums of each column inside q consecutive groups of weeks (equal number of weeks per group)."""
    wk, inv = np.unique(wk_ids, return_inverse=True)
    g = (np.arange(len(wk)) * q) // len(wk)
    return {k: np.bincount(g[inv], weights=v, minlength=q) for k, v in cols.items()}


def c2_flags(m):
    """C2a: the 95% interval of the 80% coverage holds 80%. C2b: coverage of forecasts started 2020-01+ is
    inside RECENT_BAND. C2c: coverage of all scored forecasts is inside POOLED_BAND."""
    c2a = bool(m['cov80_ci95'][0] <= COVER <= m['cov80_ci95'][1])
    rc = m['by_era'].get('E3 2020-', {}).get('cov80', float('nan'))
    c2b = bool(RECENT_BAND[0] <= rc <= RECENT_BAND[1])
    c2c = bool(POOLED_BAND[0] <= m['cov80'] <= POOLED_BAND[1])
    return c2a, c2b, c2c


def evaluate(F, h, nboot, rng, neighbours=True):
    score = (F['start'] >= ordinal(SCORE_START)) & (F['mat'] >= 0)
    bn = F['bc'] / F['norm'][:, None]
    base_names = [b for i, b in enumerate(BASES) if np.isfinite(bn[score, i]).all()]
    base_sum = {b: float(bn[score, BASES.index(b)].sum()) for b in base_names}
    best = min(base_sum, key=base_sum.get)
    bbest = bn[:, BASES.index(best)]
    runs = {'FM2': learn(F), 'F0_frozen': learn(F, learn_w=False, learn_s=False),
            'weights_only': learn(F, learn_s=False), 'width_only': learn(F, learn_w=False)}
    out = {'n_scored': int(score.sum()), 'best_baseline': best,
           'baseline_crps_n_sum': base_sum,
           'baseline_cov80': {b: float(F['bh'][score, BASES.index(b)].mean()) for b in base_names},
           'baseline_raw_sum': {b: float(F['bc'][score, BASES.index(b)].sum()) for b in base_names},
           'first_start': str(datetime.date.fromordinal(int(F['start'][score].min()))),
           'last_start': str(datetime.date.fromordinal(int(F['start'][score].max()))), 'models': {}}
    e3 = score & (F['start'] >= ordinal('2020-01-01'))
    out['baseline_cov80_2020on'] = {b: float(F['bh'][e3, BASES.index(b)].mean()) for b in base_names} if e3.sum() else {}
    wk = F['week'][score]; block = BLOCK_MULT[h] * (h // GRID_STEP)
    f0 = runs['F0_frozen']['crps']
    years = np.array([datetime.date.fromordinal(int(o)).year for o in F['start']])
    up = (F['y'] > 0).astype(float)
    for name, R in runs.items():
        c = R['crps']
        dh = ((R['med'] > 0) == (F['y'] > 0)).astype(float)          # reference only: sign of the median vs outcome
        cols = {'m': c[score], 'b': bbest[score], 'f0': f0[score], 'hit': R['hit'][score], 'n': np.ones(int(score.sum())),
                'dh': dh[score], 'up': up[score]}
        bs, nw = week_boot(wk, cols, block, nboot, rng)
        G = group_sums(wk, cols, GROUPS_Q[h])
        gP1 = 1 - G['m'] / G['b']; gcov = G['hit'] / G['n']; ggain = 1 - G['m'] / G['f0']
        m = {'P1n': float(1 - c[score].sum() / bbest[score].sum()), 'P1n_ci95': t_ci(gP1),
             'cov80': float(R['hit'][score].mean()), 'cov80_ci95': t_ci(gcov),
             'gain_vs_F0': float(1 - c[score].sum() / f0[score].sum()), 'gain_vs_F0_ci95': t_ci(ggain),
             'P1_raw': float(1 - (c[score] * F['norm'][score]).sum() / F['bc'][score, BASES.index(best)].sum()),
             'dir_hit': float(dh[score].mean()), 'always_up': float(up[score].mean()),
             'dir_edge': float(dh[score].mean() - up[score].mean()), 'dir_edge_ci95': t_ci((G['dh'] - G['up']) / G['n']),
             'groups': {'P1n': [round(float(z), 5) for z in gP1], 'cov80': [round(float(z), 4) for z in gcov],
                        'gain_vs_F0': [round(float(z), 5) for z in ggain]},
             'boot_ref': {'P1n_ci95': ci(1 - bs['m'] / bs['b']), 'cov80_ci95': ci(bs['hit'] / bs['n']),
                          'gain_vs_F0_ci95': ci(1 - bs['m'] / bs['f0'])},
             'by_era': {}, 'by_class': {}}
        for en, a, b in ERAS:
            mk = score & (F['start'] >= ordinal(a)) & (F['start'] <= ordinal(min(b, '2099-12-30')))
            if mk.sum() >= 200:
                m['by_era'][en] = {'P1n': float(1 - c[mk].sum() / bbest[mk].sum()), 'cov80': float(R['hit'][mk].mean()),
                                   'gain_vs_F0': float(1 - c[mk].sum() / f0[mk].sum()), 'n': int(mk.sum())}
        for cl in sorted(set(F['cls'].tolist())):
            mk = score & (F['cls'] == cl)
            m['by_class'][cl] = {'P1n': float(1 - c[mk].sum() / bbest[mk].sum()), 'cov80': float(R['hit'][mk].mean()),
                                 'gain_vs_F0': float(1 - c[mk].sum() / f0[mk].sum()), 'n': int(mk.sum())}
        m['pass_C2a'], m['pass_C2b'], m['pass_C2c'] = c2_flags(m)
        m['pass_C2'] = bool(m['pass_C2a'] and m['pass_C2b'] and m['pass_C2c'])
        if name == 'FM2':
            m['pass_C1'] = bool(m['P1n'] > 0 and m['P1n_ci95'][0] > 0)
            m['pass_C3'] = bool(m['by_era'].get('E3 2020-', {}).get('P1n', -1) > 0)
            m['pass_C4a'] = bool(m['gain_vs_F0'] > 0 and m['gain_vs_F0_ci95'][0] > 0)
            m['weights_by_year'] = {int(yv): [round(float(z), 3) for z in R['W'][score & (years == yv)].mean(0)]
                                    for yv in sorted(set(years[score].tolist()))}
            m['scale_by_year'] = {int(yv): round(float(R['s'][score & (years == yv)].mean()), 3)
                                  for yv in sorted(set(years[score].tolist()))}
            m['meta_v_last'] = [round(z, 3) for z in R['meta_v_last']]
            m['state_last'] = R['state_last']
        out['models'][name] = m
    out['groups_q'] = GROUPS_Q[h]; out['boot_block_weeks'] = int(block); out['indep_periods'] = round(nw / (h // GRID_STEP), 2)
    out['weeks'] = int(nw)
    fm = out['models']['FM2']
    fm['pass_C4b'] = bool(fm['pass_C2'] and not out['models']['F0_frozen']['pass_C2'])
    fm['pass_C4'] = bool(fm['pass_C4a'] or fm['pass_C4b'])
    if neighbours:
        nbr = {}
        for nm_, kw in NEIGHBOURS:
            R = learn(F, **kw)
            nbr[nm_] = {'P1n': float(1 - R['crps'][score].sum() / bbest[score].sum()), 'cov80': float(R['hit'][score].mean())}
        out['neighbours'] = nbr
        fm['pass_C5'] = bool(sum(v['P1n'] > 0 for v in nbr.values()) >= 3)
        core = bool(fm['pass_C1'] and fm['pass_C2'] and fm['pass_C3'] and fm['pass_C5'])
        fm['verdict'] = ('PASS_SELF_IMPROVING' if core and fm['pass_C4'] else
                         'PASS_MODEL_ONLY_LEARNING_GAIN_UNCONFIRMED' if core else 'FAIL_NO_CHANGE')
    return out


def load_cache(cache):
    idx = json.load(open(os.path.join(cache, 'INDEX.json')))
    cls_of = {s: c for s, c, _ in UNIVERSE}
    parts = {h: [] for h in HORIZONS}
    for a, info in enumerate(idx['assets']):
        p = os.path.join(cache, info['stem'] + '.npz')
        if not os.path.exists(p):
            continue
        Z = np.load(p)
        for h in HORIZONS:
            mk = Z['h'] == h
            parts[h].append({'start': Z['start'][mk], 'mat': Z['mat'][mk], 'y': Z['y'][mk], 'norm': Z['norm'][mk],
                             'Q': Z['Q'][mk], 'bc': Z['bc'][mk], 'bh': Z['bh'][mk],
                             'asset': np.full(int(mk.sum()), a), 'cls': np.array([cls_of[info['stem']]] * int(mk.sum()))})
    out = {}
    for h in HORIZONS:
        F = {k: np.concatenate([p[k] for p in parts[h]]) for k in parts[h][0]}
        F['h_val'] = h
        out[h] = F
    return idx, out


def stage_learn(cache, outp, nboot):
    idx, data = load_cache(cache)
    rng = np.random.default_rng(SEED)
    res = {'spec': 'FM-2 prereg 2026-11-10', 'asof': idx['asof'], 'nboot': nboot,
           'script_sha256': hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest(),
           'fm1_sha256': hashlib.sha256(open(fm1.__file__, 'rb').read()).hexdigest(),
           'assets': idx['assets'], 'horizons': {}}
    for h in HORIZONS:
        F = prep(data[h])
        res['horizons'][str(h)] = evaluate(F, h, nboot, rng)
        print('done', h, flush=True)
    json.dump(res, open(outp, 'w'), indent=1)
    print('written', outp)


# ---------------- current forecast (display only) ----------------
def stage_current(result_json, idx_dir, rates_dir, asof, outp, stems=('_SOX', '_NDX', '_GSPC')):
    """Apply the last learned weights and width scale to display targets. No scoring, no trading use."""
    res = json.load(open(result_json))
    tnx_d, tnx_v = fm1.load_yahoo(os.path.join(rates_dir, '_TNX.json'))
    irx_d, irx_v = fm1.load_yahoo(os.path.join(rates_dir, '_IRX.json'))
    eq = np.full(QN, 1.0 / QN); cut = math.log(0.8)
    out = {'asof': asof, 'note': 'display only; not a trading input', 'result_json': os.path.basename(result_json), 'targets': {}}
    for stem in stems:
        d, c = fm1.load_yahoo(os.path.join(idx_dir, stem + '.json'))
        keep = [k for k, x in enumerate(d) if fm1.HIST_FLOOR <= x <= asof]
        d = [d[k] for k in keep]; c = c[keep]
        S = build_series(d, c, tnx_d, tnx_v, irx_d, irx_v, 0)
        i = len(d) - 1
        tg = {'last_day': d[i], 'h': {}}
        for h in HORIZONS:
            fmres = res['horizons'][str(h)]['models']['FM2']
            st = fmres['state_last']
            fc = fm1.forecasts(S, i, h, want=('B1', 'B3', 'M1', 'M2'))
            sd = fc['B1'][2]
            Q = np.stack([sd * ZQ, fc['B3'][1], fc['M1'][1], fc['M2'][1]]).astype(np.float64)
            Wt = np.array(st['W']); sc_ = float(st['s'])
            x = Q.ravel(); w = np.repeat(Wt / QN, QN)
            med, q10, q90 = wq(x, w, [0.5, 0.1, 0.9])
            xs = med + sc_ * (x - med)
            b10, b50, b90 = wq(fc['B3'][1], eq, [0.1, 0.5, 0.9])
            tg['h'][str(h)] = {
                'verdict': fmres.get('verdict'), 'state_date': st['date'], 'W': st['W'], 's': sc_,
                'FM2': {'q10': math.exp(med + sc_ * (q10 - med)) - 1, 'q50': math.exp(med) - 1,
                        'q90': math.exp(med + sc_ * (q90 - med)) - 1, 'p_below_minus20pct': float(np.sum(w[xs < cut]))},
                'B3': {'q10': math.exp(b10) - 1, 'q50': math.exp(b50) - 1, 'q90': math.exp(b90) - 1,
                       'p_below_minus20pct': float(np.mean(fc['B3'][1] < cut))}}
        out['targets'][stem] = tg
    json.dump(out, open(outp, 'w'), indent=1)
    print('written', outp)


# ---------------- self test ----------------
def synth_F(rng, n_weeks=700, n_assets=6, h=20, shift_at=None):
    """Four synthetic experts: correct N(0,1), too wide N(0,2), biased N(0.5,1), too narrow N(0,0.5).
    If shift_at is set, the truth changes to N(0, 2^2) after that week (era change)."""
    base = ordinal('2000-01-03'); rows = []
    for w in range(n_weeks):
        for a in range(n_assets):
            st = base + 7 * w + (a % 3)
            sd_true = 2.0 if (shift_at is not None and w >= shift_at) else 1.0
            rows.append((st, st + int(h * 7 / 5) + 1, rng.standard_normal() * sd_true, a))
    start = np.array([r[0] for r in rows]); mat = np.array([r[1] for r in rows]); y = np.array([r[2] for r in rows])
    last = start.max()
    mat = np.where(mat <= last, mat, -1); y = np.where(mat >= 0, y, np.nan)
    Q = np.stack([np.stack([ZQ, 2 * ZQ, 0.5 + ZQ, 0.5 * ZQ])] * len(rows)).astype(np.float32)
    n = len(rows)
    return {'start': start, 'mat': mat, 'y': y, 'norm': np.ones(n), 'Q': Q, 'bc': np.zeros((n, 4)), 'bh': np.zeros((n, 4)),
            'asset': np.array([r[3] for r in rows]), 'cls': np.array(['x'] * n), 'h_val': h}


def selftest():
    rng = np.random.default_rng(7)
    # (1) pool CRPS identity: W.A - 0.5 W'DW equals direct weighted-sample CRPS
    F = prep(synth_F(rng, n_weeks=60))
    j = 10; Wt = np.array([0.1, 0.2, 0.3, 0.4])
    x = F['Q'][j].astype(np.float64).ravel(); w = np.repeat(Wt / QN, QN)
    direct = fm1.crps_w(x.copy(), w.copy(), F['y'][j])
    viaAD = float(Wt @ F['A'][j] - 0.5 * Wt @ F['D'][j] @ Wt)
    assert abs(direct - viaAD) < 1e-6, (direct, viaAD)
    sc_ = 0.8; med = wq(x, w, [0.5])[0]; xs = med + sc_ * (x - med)
    direct_s = fm1.crps_w(xs.copy(), w.copy(), F['y'][j])
    via_s = float(np.sum(w * np.abs(xs - F['y'][j]))) - 0.5 * sc_ * float(Wt @ F['D'][j] @ Wt)
    assert abs(direct_s - via_s) < 1e-6, (direct_s, via_s)
    # (1b) interpolated quantiles: a 99-point normal sample gives the exact 10%/90% levels (fm1.wquant does not)
    eq = np.full(QN, 1.0 / QN)
    q10, q50, q90 = wq(ZQ.copy(), eq, [0.1, 0.5, 0.9])
    assert abs(q10 - Z10) < 2e-3 and abs(q90 - Z90) < 2e-3 and abs(q50) < 1e-9, (q10, q90, q50)
    assert fm1.wquant(ZQ.copy(), eq, 0.9) > Z90 + 5e-3
    yy = rng.standard_normal(40000)
    hits = np.mean((yy >= q10) & (yy <= q90))
    assert abs(hits - 0.80) < 0.008, hits
    c1, h1 = score_fc(('norm', 0.0, 1.0), 0.3); c2, h2 = score_fc(('samp', ZQ.copy(), eq), 0.3)
    assert abs(c1 - c2) < 2e-3 and h1 == h2 == 1.0, (c1, c2)
    # (2) learning finds the correct expert and beats the frozen equal-weight pool
    F = prep(synth_F(rng))
    R = learn(F); R0 = learn(F, learn_w=False, learn_s=False)
    ok = np.isfinite(R['crps'])
    late = ok & (F['start'] > np.quantile(F['start'], 0.5))
    gain = 1 - R['crps'][late].sum() / R0['crps'][late].sum()
    print('weights late', R['W'][late].mean(0).round(3), 'gain', round(float(gain), 4),
          'cov FM2', round(float(R['hit'][late].mean()), 3), 'cov F0', round(float(R0['hit'][late].mean()), 3),
          'scale', round(float(R['s'][late].mean()), 3))
    assert R['W'][late].mean(0)[0] > 0.6 and gain > 0.01
    assert abs(R['hit'][late].mean() - 0.80) < 0.03
    # (3) width-only calibration fixes an over-wide frozen pool
    Rw = learn(F, learn_w=False)
    print('width-only cov', round(float(Rw['hit'][late].mean()), 3), 'scale', round(float(Rw['s'][late].mean()), 3))
    assert abs(Rw['hit'][late].mean() - 0.80) < 0.03 and Rw['s'][late].mean() < 1.0
    # (4) no look-ahead: changing outcomes that mature on/after t0 leaves everything issued up to t0 unchanged
    t0 = int(np.quantile(F['start'], 0.6))
    F2 = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in F.items()}
    chg = F2['mat'] >= t0
    F2['y'] = np.where(chg, F2['y'] * 3 + 1, F2['y'])
    y2 = F2['y'][:, None, None]
    with np.errstate(invalid='ignore'):
        F2['A'] = np.abs(F2['Q'].astype(np.float64) - y2).mean(axis=2) / F2['norm'][:, None]
    R2 = learn(F2)
    upto = F['start'] <= t0
    assert np.allclose(R['W'][upto], R2['W'][upto]) and np.allclose(R['s'][upto], R2['s'][upto])
    assert not np.allclose(R['W'][~upto], R2['W'][~upto])
    # (5) era change: after the truth doubles its width, the learner moves to the wide expert and re-calibrates
    F = prep(synth_F(rng, shift_at=350))
    R = learn(F); R0 = learn(F, learn_w=False, learn_s=False)
    ok = np.isfinite(R['crps']); st = F['start']; cut = ordinal('2000-01-03') + 7 * 350
    post = ok & (st > cut + 7 * 150)
    print('era shift: weights after', R['W'][post].mean(0).round(3), 'cov FM2', round(float(R['hit'][post].mean()), 3),
          'cov F0', round(float(R0['hit'][post].mean()), 3), 'gain', round(float(1 - R['crps'][post].sum() / R0['crps'][post].sum()), 4))
    assert R['W'][post].mean(0)[1] > 0.5
    # (6) expert stage: shapes and no look-ahead on a synthetic asset
    n = 3200
    days = [(datetime.date(1990, 1, 1) + datetime.timedelta(days=k)).isoformat() for k in range(n)]
    c = 100 * np.exp(np.cumsum(0.0003 + 0.012 * rng.standard_normal(n)))
    rd = days; rv = 4 + np.cumsum(rng.standard_normal(n)) * 0.02
    S = build_series(days, c, rd, rv, rd, rv * 0 + 3.0, 0)
    Ra = expert_rows(S, learn_start='1990-01-01', min_rows=1260, horizons=[20])
    c2 = c.copy(); cutix = 2000; c2[cutix + 1:] *= 1.3
    Sb = build_series(days, c2, rd, rv, rd, rv * 0 + 3.0, 0)
    Rb = expert_rows(Sb, learn_start='1990-01-01', min_rows=1260, horizons=[20])
    same = Ra['start'] <= ordinal(days[cutix])
    assert same.sum() > 50 and np.allclose(Ra['Q'][same], Rb['Q'][same]) and np.allclose(Ra['norm'][same], Rb['norm'][same])
    assert Ra['Q'].shape[1:] == (K, QN)
    # lagged rates never read the same-day value
    v = lag_fill(['2020-01-03'], ['2020-01-02', '2020-01-03'], np.array([1.0, 2.0]), 1)
    assert v[0] == 1.0 and lag_fill(['2020-01-03'], ['2020-01-02', '2020-01-03'], np.array([1.0, 2.0]), 0)[0] == 2.0
    # evaluate() runs end to end on synthetic data
    F = prep(synth_F(rng, n_weeks=400))
    F['bc'] = np.stack([F['A'][:, 0] - 0.5 * F['D'][:, 0, 0]] * 4, axis=1)       # baseline = correct expert
    F['bh'] = np.zeros((len(F['y']), 4))
    F['start'] = F['start'] + (ordinal('2006-01-02') - ordinal('2000-01-03'))
    F['mat'] = np.where(F['mat'] >= 0, F['mat'] + (ordinal('2006-01-02') - ordinal('2000-01-03')), -1)
    F['week'] = np.array([isoweek(x) for x in F['start']])
    ev = evaluate(F, 20, 300, np.random.default_rng(1))
    fmx = ev['models']['FM2']
    print('evaluate synthetic: P1n', round(fmx['P1n'], 4), 'gain', round(fmx['gain_vs_F0'], 4), 'verdict', fmx['verdict'],
          'C1,C2a,C2b,C2c,C3,C4a,C4b,C5', [fmx[k] for k in ('pass_C1', 'pass_C2a', 'pass_C2b', 'pass_C2c', 'pass_C3', 'pass_C4a', 'pass_C4b', 'pass_C5')],
          'dir_edge', round(fmx['dir_edge'], 4), 'state', fmx['state_last'])
    assert set(fmx['state_last']) == {'date', 'W', 's'} and abs(sum(fmx['state_last']['W']) - 1) < 1e-9
    print('selftest OK')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'selftest':
        selftest()
    elif cmd == 'experts':
        jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 1
        stage_experts(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], jobs)
    elif cmd == 'learn':
        nboot = int(sys.argv[sys.argv.index('--boot') + 1]) if '--boot' in sys.argv else 10000
        stage_learn(sys.argv[2], sys.argv[3], nboot)
    elif cmd == 'current':
        stage_current(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
