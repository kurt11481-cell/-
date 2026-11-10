"""vixr: market implied-volatility ratio expert (FM-2 layer 3 menu, finding D1). Display/score only.

Idea: VIX is the option market's price for the next 30 days of S&P 500 movement. Set against the
movement the S&P 500 actually delivered over the last year, it says whether the market expects more
or less than the last year gave. The asset's own one-year volatility is scaled by that ratio.
The four incumbent experts read prices and rates only; this one reads an option price.

Definition (every value is known before the start day's close):
  ratio_t = (VIX_t / 100) / (sd of the last 252 daily log returns of the S&P 500 up to t, times sqrt(252))
  R_k     = the last ratio_t with t strictly before day k (EXTRA_LAG = 1). A value up to 7 calendar days old is
            used as it is (weekends, holidays, a missing VIX day); when it is older there is no forecast.
            VIX's daily close is fixed 15 minutes after the US stock close, so the same-day value is not
            known at a US asset's close; every asset therefore reads the previous VIX day.
  w(h)    = mean over j = 1..h of 0.5 ** (j / 60)      (fm1 M1 weight of "now" against "long run")
  v_k     = s252_k * sqrt(w(h) * R_k ** 2 + 1 - w(h))                 (daily volatility for horizon h)
  z_k     = (h-day log return that started at k) / (v_k * sqrt(h))    for known outcomes, k = 260 .. i - h
  forecast = quantiles of z at the levels V.QL, times v_i * sqrt(h)
No forecast when R_i is missing or fewer than 250 z values exist.
Nothing was chosen by looking at scores: 252 and 60 are the fm1 constants B_WIN and HALF; 260 and the quantile
recipe are fm1 M1's; 250 (known outcomes needed, about one year) and 7 (calendar days after which a value is
stale, the harness default) were set by hand before any score of this expert was computed.
VIX is used as an input of a displayed range only, never as a trading or exposure rule.
"""
import math
import numpy as np

ID = 'vixr'
EXTRAS = {'VIX': '_VIX', 'SPX': '_GSPC'}
EXTRA_LAG = 1
WIN = 252
HALF = 60.0
FIRST = 260
MIN_Z = 250
MAX_GAP = 7


def derive(raw):
    sd, sc = raw['SPX']
    vd, vv = raw['VIX']
    n = len(sc)
    r = np.diff(np.log(sc))                                   # r[k] is the return of day k + 1
    cs = np.cumsum(np.r_[0.0, r])
    cs2 = np.cumsum(np.r_[0.0, r * r])
    rv = np.full(n, np.nan)                                   # annualised sd of the WIN returns ending at day t
    t = np.arange(WIN, n)
    m = (cs[t] - cs[t - WIN]) / WIN
    var = (cs2[t] - cs2[t - WIN]) / WIN - m * m
    rv[t] = np.sqrt(np.maximum(var, 1e-18) * WIN / (WIN - 1)) * math.sqrt(252.0)
    ratio = np.full(len(vd), np.nan)
    if n and len(vd):
        idx = np.searchsorted(np.array(sd), np.array(vd), side='right') - 1      # S&P 500 day at or before each VIX day
        ic = np.clip(idx, 0, n - 1)
        gap = (np.array(vd, dtype='datetime64[D]') - np.array(sd, dtype='datetime64[D]')[ic]).astype(np.int64)
        ok = (idx >= 0) & (gap <= MAX_GAP)
        ratio[ok] = (vv[ok] / 100.0) / rv[ic][ok]
    keep = np.isfinite(ratio) & (ratio > 0)
    return {'RATIO': ([d for d, k in zip(vd, keep) if k], ratio[keep])}


def quantiles(V, h):
    i = V.i
    last = i - h
    ratio = V.x('RATIO')
    if last < FIRST or not np.isfinite(ratio[i]):
        return None
    w = float(np.mean(0.5 ** (np.arange(1, h + 1) / HALF)))
    v = V.s252 * np.sqrt(w * ratio ** 2 + 1.0 - w)
    if not (np.isfinite(v[i]) and v[i] > 0):
        return None
    z = V.yh(h)[FIRST:last + 1] / (v[FIRST:last + 1] * math.sqrt(h))
    z = z[np.isfinite(z)]
    if len(z) < MIN_Z:
        return None
    return np.quantile(z, V.QL) * v[i] * math.sqrt(h)
