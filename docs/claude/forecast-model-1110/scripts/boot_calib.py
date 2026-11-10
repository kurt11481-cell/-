#!/usr/bin/env python3
"""Synthetic check of the week-block bootstrap used by fm2.py. No real data is read.

Question: with block = m * h/5 weeks, how often does the nominal 95% interval hold the true value?
(Independent re-review of FM-1 found that m = 1 gives intervals that are too narrow.)

Data: 20 assets, 22 scored years, daily returns = common factor + own part, each GARCH(1,1) with
t(6) shocks. Forecasters are zero-mean normals (closed-form CRPS):
  base  = 252-day volatility            (like B1)
  model = EWMA(0.94) blended with long-run variance, 60-day half-life (like M1's width)
  twin  = same with EWMA(0.97)          (a close relative, so model-vs-twin mimics a small "gain")
Statistics, as in fm2.evaluate: P1 = 1 - sum(model)/sum(base), gain = 1 - sum(model)/sum(twin),
coverage of the model's 80% band. Truth = the same ratios on sums pooled over all replications.

Rule fixed before running: per horizon take the smallest m in MULTS whose interval holds the truth
in >= 93% of replications for both P1 and gain; if none does, take the m with the highest minimum.

Second method added after the first run showed that no block length reaches 93%: split the scored
weeks into q consecutive groups, compute the statistic inside each group, and use the t interval of
the q group values (Ibragimov-Mueller 2010). Rule fixed before running it: per horizon take the
largest q in QS with coverage >= 93% for both P1 and gain; if none, the q with the highest minimum.

usage: python3 -I boot_calib.py <out_json> [--reps N] [--jobs N]
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fm1, fm2

MULTS = [1, 2, 3, 4, 6]
QS = [4, 6, 8, 11]
HS = [20, 60, 250]
NA = 20; YEARS = 22; BURN = 1260; STEP = 5; NB = 1000
GA, GB = 0.08, 0.905
SD_F, SD_E = 0.010, 0.012
DF = 6
TARGET = 0.93


def erf(x):
    s = np.sign(x); x = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-x * x)
    return s * y


def crps_n(sd, y):
    z = y / sd
    pdf = np.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    cdf = 0.5 * (1 + erf(z / math.sqrt(2)))
    return sd * (z * (2 * cdf - 1) + 2 * pdf - 1 / math.sqrt(math.pi))


def one(seed):
    rng = np.random.default_rng(seed)
    T = BURN + YEARS * 252
    sc = math.sqrt((DF - 2) / DF)
    zf = rng.standard_t(DF, T) * sc; ze = rng.standard_t(DF, (T, NA)) * sc
    om_f = SD_F ** 2 * (1 - GA - GB); om_e = SD_E ** 2 * (1 - GA - GB)
    r = np.empty((T, NA)); hf = SD_F ** 2; he = np.full(NA, SD_E ** 2)
    e94 = np.empty((T, NA)); e97 = np.empty((T, NA)); c94 = np.full(NA, SD_F ** 2 + SD_E ** 2); c97 = c94.copy()
    for t in range(T):
        f = math.sqrt(hf) * zf[t]; e = np.sqrt(he) * ze[t]
        x = f + e; r[t] = x
        hf = om_f + GA * f * f + GB * hf; he = om_e + GA * e * e + GB * he
        c94 = 0.94 * c94 + 0.06 * x * x; c97 = 0.97 * c97 + 0.03 * x * x
        e94[t] = c94; e97[t] = c97
    cs = np.vstack([np.zeros((1, NA)), np.cumsum(r, axis=0)])            # cs[t] = sum r[0..t-1]
    cs2 = np.vstack([np.zeros((1, NA)), np.cumsum(r * r, axis=0)])
    n = np.arange(1, T + 1)[:, None]
    expv = cs2[1:] / n - (cs[1:] / n) ** 2                               # expanding variance up to t
    out = {}
    for h in HS:
        idx = np.arange(BURN, T - h, STEP)
        m252 = (cs[idx + 1] - cs[idx + 1 - 252]) / 252
        v252 = (cs2[idx + 1] - cs2[idx + 1 - 252]) / 252 - m252 ** 2
        sd_b = np.sqrt(v252 * 252 / 251 * h)
        w = fm1.w_h(h, 60.0)
        sd_m = np.sqrt((w * e94[idx] + (1 - w) * expv[idx]) * h)
        sd_g = np.sqrt((w * e97[idx] + (1 - w) * expv[idx]) * h)
        y = cs[idx + 1 + h] - cs[idx + 1]
        cols = {'m': (crps_n(sd_m, y) / sd_b).ravel(), 'b': (crps_n(sd_b, y) / sd_b).ravel(),
                'g': (crps_n(sd_g, y) / sd_b).ravel(),
                'hit': (np.abs(y) <= fm2.Z90 * sd_m).astype(float).ravel(), 'n': np.ones(y.size)}
        wk = np.repeat(np.arange(len(idx)), NA)
        res = {'sums': {k: float(v.sum()) for k, v in cols.items()}, 'ci': {}}
        for mlt in MULTS:
            bs, nw = fm2.week_boot(wk, cols, mlt * (h // STEP), NB, rng)
            res['ci'][mlt] = {'P1': fm2.ci(1 - bs['m'] / bs['b']), 'gain': fm2.ci(1 - bs['m'] / bs['g']),
                              'cov': fm2.ci(bs['hit'] / bs['n'])}
        nw = len(idx); wsum = {k: v.reshape(nw, NA).sum(1) for k, v in cols.items()}
        res['gt'] = {}
        for q in QS:
            g = (np.arange(nw) * q) // nw
            G = {k: np.bincount(g, weights=v, minlength=q) for k, v in wsum.items()}
            res['gt'][q] = {'P1': fm2.t_ci(1 - G['m'] / G['b']), 'gain': fm2.t_ci(1 - G['m'] / G['g']),
                            'cov': fm2.t_ci(G['hit'] / G['n'])}
        out[h] = res
    return out


if __name__ == '__main__':
    outp = sys.argv[1]
    reps = int(sys.argv[sys.argv.index('--reps') + 1]) if '--reps' in sys.argv else 400
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 1
    seeds = [50000 + k for k in range(reps)]
    if jobs > 1:
        import multiprocessing as mp
        with mp.Pool(jobs) as p:
            R = p.map(one, seeds, chunksize=4)
    else:
        R = [one(s) for s in seeds]
    summary = {'reps': reps, 'nboot': NB, 'rule': 'smallest m with coverage >= %.2f for P1 and gain, else best minimum' % TARGET,
               'horizons': {}}
    for h in HS:
        S = {k: sum(r[h]['sums'][k] for r in R) for k in ('m', 'b', 'g', 'hit', 'n')}
        truth = {'P1': 1 - S['m'] / S['b'], 'gain': 1 - S['m'] / S['g'], 'cov': S['hit'] / S['n']}
        tab = {}
        for mlt in MULTS:
            row = {}
            for st in ('P1', 'gain', 'cov'):
                lo = np.array([r[h]['ci'][mlt][st][0] for r in R]); hi = np.array([r[h]['ci'][mlt][st][1] for r in R])
                row[st] = round(float(np.mean((lo <= truth[st]) & (truth[st] <= hi))), 3)
                row[st + '_width'] = round(float(np.mean(hi - lo)), 5)
            tab[mlt] = row
        ok = [m for m in MULTS if min(tab[m]['P1'], tab[m]['gain']) >= TARGET]
        pick = ok[0] if ok else max(MULTS, key=lambda m: min(tab[m]['P1'], tab[m]['gain']))
        tabq = {}
        for q in QS:
            row = {}
            for st in ('P1', 'gain', 'cov'):
                lo = np.array([r[h]['gt'][q][st][0] for r in R]); hi = np.array([r[h]['gt'][q][st][1] for r in R])
                row[st] = round(float(np.mean((lo <= truth[st]) & (truth[st] <= hi))), 3)
                row[st + '_width'] = round(float(np.mean(hi - lo)), 5)
            tabq[q] = row
        okq = [q for q in QS if min(tabq[q]['P1'], tabq[q]['gain']) >= TARGET]
        pickq = max(okq) if okq else max(QS, key=lambda q: min(tabq[q]['P1'], tabq[q]['gain']))
        per = np.array([1 - r[h]['sums']['m'] / r[h]['sums']['b'] for r in R])
        summary['horizons'][h] = {'truth': {k: round(v, 5) for k, v in truth.items()}, 'sd_P1_across_reps': round(float(per.std()), 5),
                                  'coverage_by_mult': tab, 'pick': pick, 'target_met': bool(ok),
                                  'group_t_coverage_by_q': tabq, 'pick_q': pickq, 'target_met_q': bool(okq)}
        print(h, 'truth', summary['horizons'][h]['truth'], 'sd', summary['horizons'][h]['sd_P1_across_reps'],
              'pick m', pick, 'met', bool(ok), '| pick q', pickq, 'met', bool(okq))
        for mlt in MULTS:
            print('   m', mlt, tab[mlt])
        for q in QS:
            print('   q', q, tabq[q])
    json.dump(summary, open(outp, 'w'), indent=1)
    print('written', outp)
