#!/usr/bin/env python3
"""FM-2 layer 3 (the expert list): shadow scoring of challenger experts.
Display/score only: no orders, no policy/state/core-input change.

Rule = forecast-layer3-rule-2026-11-10.md (one level up). fm1.py and fm2.py are hash-fixed; they are
imported here and never edited. Nothing in this file changes what fm2_weekly.py writes: the forecast
ledger and the pool-track scores do not depend on any challenger.

One challenger = one extra expert c (a Python module, see CHALLENGER API below). Its shadow pool is

    P+ = (1 - om) * P + om * c        (a mixture of the two distributions)

  P    the incumbent pool, with the expert weights W exactly as fm2.learn issued them
  om   the share of c. It is learned only from matured forecasts that c itself issued, by the fm2.py
       learner family on two losses (the pool P, the expert c): the same 9 (eta, half-life) learners
       + 1 "do not learn" learner, combined by their own realised scores (fm2.ETAS, HALFS, ETA_TOP).
       Prior share = 1 / (K + 1) (K = number of incumbent experts): the share an equal-weight pool gives.
  s+   width scale of P+: the fm2.py calibration procedure applied to the bands P+ itself issued.

Where c has no forecast (before its start, a missing input, an asset it does not cover) P+ is P.
With c absent everywhere, shadow_learn returns the fm2.learn numbers exactly (selftest 1).
Two pairs are scored: FM2+ against FM2 (learning on) and F0+ against F0 (equal weights 1/(K+1), no scale).
Nothing uses an outcome that was not known on an earlier calendar date (same rule as fm2.learn).
Only forecasts that start on or after a challenger's T0 are scored against the base pool (the judged window).
No table of a challenger's score over the past is made: the comparison (compare) covers the judged window only;
the finished historical data is not measured again with a new expert (rule section 4). A history-backed
challenger's share and width scale are learned over the past as well, exactly as the incumbents' weights are.
That share is the past score in another unit (the share of a learner that never forgets gives it back exactly),
so the weekly run does not show 'state' or 'om_mean' of a history-backed challenger (review R2-2).

CHALLENGER API (a module file; static_check() lists what it may contain):
  ID = 'name'                               lower-case letters, digits, underscore
  EXTRAS = {'NAME': '_STEM', ...}           optional: Yahoo-chart JSON files <extra_dir>/<_STEM>.json
  EXTRA_LAG = 1                             optional: every asset reads the extra series strictly before its
                                            start day (for a source whose daily value is fixed after the
                                            asset's own close). Default 0: only non-US assets do.
  def derive(raw)                           optional: raw[NAME] = (days, values) on the source's own calendar,
                                            cut at asof -> dict NAME -> (days, values). Must be causal.
  def quantiles(V, h)                       required: QN ascending quantiles (levels V.QL) of the h-day log
                                            return starting at V.day, or None for "no forecast"
A challenger reads no file itself: the harness loads the EXTRAS files and cuts them by date, which is what lets
the admission test catch a look-ahead. Per-asset extra files (option snapshots) are not part of this version.
V is a View: one asset, private copies of its data up to and including the start day only (see class View).
A forecast that enters the judged window is computed from inputs that end at its own start day (stage, cut_from):
the asset file and the extra files are cut there before derive() and the series are built (the extras one day
earlier for an asset that reads them strictly before its start day); the two rate files are aligned by date.
Every extra series is aligned to the asset's days: the value at (US-listed, EXTRA_LAG 0) or strictly before
(non-US, or EXTRA_LAG 1) each day, nan when it is older than MAX_GAP_DAYS calendar days. The day of a value
must be the day it became known (a series stamped by reference period needs its release lag built in).
Challenger code runs in other processes only (stage: fork children; admission: two fresh interpreters, then fork
children for the full-grid dry run), never in the process that scores or keeps the books. A fork child holds a
copy of its parent's memory: it cannot change what the parent scores or writes.

usage:
  python3 -I -B fm3_shadow.py selftest
  python3 -I -B fm3_shadow.py admit <challenger.py> <pool_inputs_dir> <rates_dir> <extra_dir> <asof> [<report_json>] [--cache <fm2_cache_dir>] [--jobs N]
  python3 -I -B fm3_shadow.py stage <challenger.py> <pool_inputs_dir> <rates_dir> <extra_dir> <asof> <fm2_cache_dir> <out_dir> [--from YYYY-MM-DD] [--cut-from YYYY-MM-DD] [--jobs N]
(admit-pass is the admission's own child command.)
"""
import sys, os, json, math, ast, time, re, hashlib, datetime, importlib.util, subprocess, tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fm1, fm2

K = len(fm2.EXPERTS)
PRIOR = 1.0 / (K + 1)             # prior share of a challenger
FORWARD_START = '2026-11-11'      # same as fm2_weekly.py: no forward score before this start day
MIN_WEEKS = {20: 104, 60: 208}    # scored weeks at which a challenger is judged (forward rule section 3)
FWD_Q = 4                         # time groups of the forward t interval (forward rule section 3)
CI_WEEKS = {h: 4 * FWD_Q * h // fm2.GRID_STEP + 1 for h in fm2.HORIZONS}
                                  # scored weeks from which every time group holds more than 4 independent h-day periods
                                  # (the basis of forward rule section 3): 65 / 193 / 801. No interval before that.
FUT_WEEKS = {20: CI_WEEKS[20]}    # interim look (upper bound of the interval < 0) from this many weeks on.
                                  # None at 60 days: its interval is usable only 15 weeks before the judgement itself.
COV_BAND = (0.70, 0.90)           # a shadow pool that passes must have its forward 80% coverage inside
MAX_GAP_DAYS = 7                  # an extra value older than this (calendar days) is "missing"
RUNTIME_LIMIT = 0.01              # admission: mean seconds per quantiles() call (about 12 CPU minutes per weekly stage)
WIDTH_BAND = (0.1, 10.0)          # admission: challenger 80% width / B1 80% width at every test point (gross unit errors)
WIDTH_MED_BAND = (0.5, 2.0)       # admission: the median of that ratio over the test points (a constant-factor unit error)
MED_MAX = 3.0                     # admission: |challenger median| / (B1 sd for the horizon) at every test point
ADMIT_POINTS = 12                 # admission: start days per asset (all 20 assets), spread over its history
ADMIT_TIMEOUT = 1800              # admission: seconds allowed for each of the two passes
ISSUE_MAX_DAYS = 10               # a judged forecast must be first computed within this many calendar days of its start day
ISSUE_TOL = (1e-4, 1e-7)          # (rtol, atol): a recomputed forecast further than this from the issued one counts as "changed"
CUT_TOL = (1e-6, 1e-9)            # (rtol, atol): cut at the start day against cut at asof; further apart = look-ahead

ALLOWED_IMPORTS = {'math', 'numpy'}
BAD_NAMES = {'open', 'exec', 'eval', 'compile', '__import__', 'input', 'globals', 'locals', 'vars', 'getattr', 'setattr',
             'delattr', 'breakpoint', 'memoryview', 'exit', 'quit', 'help', 'type', 'super', 'object', 'classmethod',
             'staticmethod', 'property', 'print', 'hash', 'id',
             'str', 'repr', 'ascii', 'dir'}             # the text of an object carries its memory address
BAD_ATTRS = {'load', 'save', 'savez', 'savez_compressed', 'loadtxt', 'savetxt', 'genfromtxt', 'fromfile', 'tofile',
             'memmap', 'random', 'ctypeslib', 'lib', 'testing', 'f2py', 'distutils', 'DataSource', 'fromregex',
             'frombuffer', 'dump', 'dumps', 'setflags', 'flags', 'ctypes', 'base', 'data', 'seterr', 'seterrcall',
             # every public sub-module of numpy (they lead to builtins, inspect, operator, ...; selftest 9 walks them)
             'char', 'core', 'dtypes', 'emath', 'exceptions', 'fft', 'linalg', 'ma', 'polynomial', 'rec', 'strings',
             'typing', 'matrixlib', 'version', 'compat', 'test', 'os', 'sys',
             'format', 'format_map',                    # str.format reads attributes through its field names
             'mro',                                     # leads to object, and from there to every class
             'setbufsize', 'getbufsize', 'set_printoptions', 'get_printoptions', 'printoptions',
             'geterr', 'geterrcall'}                    # numpy settings that last between calls (a state)
BAD_PREFIX = ('gi_', 'cr_', 'ag_', 'f_', 'co_', 'tb_')  # generator / frame / code / traceback objects (they lead to builtins)
MUTATORS = {'append', 'extend', 'insert', 'remove', 'pop', 'popitem', 'clear', 'update', 'setdefault', 'add', 'discard',
            'sort', 'reverse', 'fill', 'put', 'itemset', 'resize', 'partition', 'byteswap'}
CLOCK_WORDS = {'now', 'today'}                          # numpy reads the clock from these date strings
TOP_NODES = (ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef, ast.Expr)
BAD_NODES = (ast.ClassDef, ast.Global, ast.Nonlocal, ast.AsyncFunctionDef, ast.With, ast.AsyncWith, ast.Yield,
             ast.YieldFrom, ast.Await, ast.Try, ast.Raise, ast.Delete,
             ast.Match,                                 # a class pattern reads any attribute by name (review R2-6)
             ast.JoinedStr)                             # an f-string is str() of its values


class CutMismatch(ValueError):
    """A new forecast computed from inputs that end at its start day differs from the same forecast computed from
    inputs cut at asof: the challenger looks ahead, or it is not deterministic."""


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


# ---------------- challenger modules ----------------
def _root(node):
    """The name an attribute / subscript / call chain starts from, or None."""
    while isinstance(node, (ast.Attribute, ast.Subscript, ast.Call, ast.Starred)):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node.id if isinstance(node, ast.Name) else None


def _const(node):
    """A module-level value that cannot be changed later: a constant, or a tuple / arithmetic of constants."""
    if isinstance(node, ast.Tuple):
        return all(_const(e) for e in node.elts)
    if isinstance(node, ast.UnaryOp):
        return _const(node.operand)
    if isinstance(node, ast.BinOp):
        return _const(node.left) and _const(node.right)
    return isinstance(node, ast.Constant)


def static_check(src):
    """Reasons why a challenger source is refused (empty list = accepted).
    This is not a sandbox. It keeps honest code inside the API (no files, no network, no randomness, no state,
    no clock) and can be bypassed by code written to bypass it (a clock word put together from pieces, the address
    of an object through '%s' % V); the code is also read by an independent judge before it is registered (rule
    section 3).
    Module level: imports of math / numpy, constants, EXTRAS (a dict of strings, read by the harness only) and
    functions. Inside functions: no private or introspection attribute, no attribute assignment, the imported
    modules only as "np.name" / "math.name"."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return ['syntax error: %s' % e]
    bad = []
    assigned = set(); imported = set(); extras_def = set()       # module-level names
    for node in tree.body:
        if not isinstance(node, TOP_NODES):
            bad.append('top-level %s' % type(node).__name__)
        elif isinstance(node, ast.Expr) and not (isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            bad.append('top-level expression')
        elif isinstance(node, ast.Assign):
            names = {n.id for t in node.targets for n in ast.walk(t) if isinstance(n, ast.Name)}
            assigned |= names
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'EXTRAS':
                extras_def.add(id(node.targets[0]))
                if not (isinstance(node.value, ast.Dict) and all(isinstance(x, ast.Constant) and isinstance(x.value, str)
                                                                 for x in node.value.keys + node.value.values)):
                    bad.append('EXTRAS is not a dict of string constants')
            elif 'EXTRAS' in names or not _const(node.value):
                bad.append('module-level value of %s is not a constant' % ', '.join(sorted(names)))
        elif isinstance(node, ast.Import):
            imported |= {(a.asname or a.name).split('.')[0] for a in node.names}
    attr_base = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            bad += ['import %s' % a.name for a in node.names if a.name not in ALLOWED_IMPORTS]
        elif isinstance(node, ast.ImportFrom):
            bad.append('from %s import' % node.module)          # only "import math" / "import numpy as np"
        elif isinstance(node, ast.Name) and (node.id in BAD_NAMES or node.id.startswith('_')):
            bad.append('name %s' % node.id)
        elif isinstance(node, ast.Name) and node.id in imported and id(node) not in attr_base:
            bad.append('module %s used as a value' % node.id)
        elif isinstance(node, ast.Name) and node.id == 'EXTRAS' and id(node) not in extras_def:
            bad.append('EXTRAS used inside the module')
        elif isinstance(node, ast.Attribute) and (node.attr.startswith('_') or node.attr in BAD_ATTRS or node.attr.startswith(BAD_PREFIX)):
            bad.append('attribute .%s' % node.attr)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bad.append('attribute assignment .%s' % node.attr)
        elif isinstance(node, BAD_NODES):
            bad.append('statement %s' % type(node).__name__)
        elif isinstance(node, ast.FunctionDef) and node.decorator_list:
            bad.append('decorator on %s' % node.name)
        elif isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)) and \
                (node.value.decode('latin-1') if isinstance(node.value, bytes) else node.value).strip().lower() in CLOCK_WORDS:
            bad.append('clock string %r' % node.value)
        # no state: nothing may be written into a module-level object, and defaults must be constants
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                for el in ast.walk(t):
                    if isinstance(el, (ast.Subscript, ast.Attribute)) and _root(el) in assigned | imported:
                        bad.append('write into module-level %s' % _root(el))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in MUTATORS \
                and _root(node.func.value) in assigned:
            bad.append('call .%s on module-level %s' % (node.func.attr, _root(node.func.value)))
        elif isinstance(node, (ast.FunctionDef, ast.Lambda)):
            if any(d is not None and not isinstance(d, ast.Constant) for d in node.args.defaults + node.args.kw_defaults):
                bad.append('non-constant default argument')
    return sorted(set(bad))


def load_challenger(path):
    """Import a challenger module after the static check. Raises ValueError when it is refused."""
    src = open(path, encoding='utf-8').read()
    bad = static_check(src)
    if bad:
        raise ValueError('challenger refused: ' + '; '.join(bad))
    spec = importlib.util.spec_from_file_location('challenger_' + hashlib.sha256(src.encode()).hexdigest()[:12], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not (isinstance(getattr(mod, 'ID', None), str) and re.fullmatch(r'[a-z0-9_]+', mod.ID)):
        raise ValueError('challenger refused: ID missing or not [a-z0-9_]+')
    if not callable(getattr(mod, 'quantiles', None)):
        raise ValueError('challenger refused: quantiles(V, h) missing')
    ex = getattr(mod, 'EXTRAS', {})
    if not (isinstance(ex, dict) and all(isinstance(k, str) and isinstance(v, str) and re.fullmatch(r'[A-Za-z0-9_]+', v)
                                         for k, v in ex.items())):
        raise ValueError('challenger refused: EXTRAS must map names to file stems')
    if type(getattr(mod, 'EXTRA_LAG', 0)) is not int or getattr(mod, 'EXTRA_LAG', 0) not in (0, 1):
        raise ValueError('challenger refused: EXTRA_LAG must be 0 or 1')
    if hasattr(mod, 'asset_extras'):
        raise ValueError('challenger refused: asset_extras (per-asset extra files) is not part of this version')
    return mod


def _cut(a, n):
    b = np.array(a[..., :n]); b.flags.writeable = False
    return b


class View:
    """All a challenger may read for one forecast: one asset, data up to and including index i (the start day).
    Every array is a private read-only copy that ends at i: nothing later than the start day exists in a View,
    and nothing in it leads back to the harness.
      i, day            index and date 'YYYY-MM-DD' of the start day
      QN, QL, ZQ        number of quantiles, their levels (mid-points), standard normal quantiles at QL
      c, lc, r          closes, log closes, daily log returns (r[0] = 0)
      s252, m252        252-day sd and mean of r (s252 is the fm1 B1 width per day)
      f                 the six fm1 features, shape (6, i + 1)
      vh(h), yh(h), x(name)"""

    def __init__(self, A, i):
        """A: the arrays of one asset (asset_context). The harness keeps A; the View keeps cut copies only."""
        n = int(i) + 1
        self.i = int(i); self.day = A['days'][self.i]; self.QN = fm2.QN
        self.QL = _cut(fm1.QL, fm2.QN); self.ZQ = _cut(fm2.ZQ, fm2.QN)
        self.c = _cut(A['c'], n); self.lc = _cut(A['lc'], n); self.r = _cut(A['r'], n)
        self.s252 = _cut(A['s252'], n); self.m252 = _cut(A['m252'], n); self.f = _cut(A['f'], n)
        self._ev = _cut(A['exp_var'], n); self._ew = _cut(A['ew'], n)
        self._x = {k: _cut(v, n) for k, v in A['x'].items()}

    def vh(self, h, lam=fm1.LAM):
        """fm1 M1 daily volatility for horizon h (EWMA blended with the long-run level), as fm1.Series.vh."""
        w = fm1.w_h(h, fm1.HALF)
        return np.sqrt(w * (self._ew if lam == fm1.LAM else fm1.ewma_var(self.r, lam)) + (1 - w) * self._ev)

    def yh(self, h):
        """Known h-day log returns: element k is lc[k + h] - lc[k], for starts k = 0 .. i - h."""
        return self.lc[h:] - self.lc[:max(self.i + 1 - h, 0)]

    def x(self, name):
        """An extra series aligned to this asset's days."""
        return self._x[name]


def load_series(path, asof):
    d, v = fm1.load_yahoo(path)
    keep = [k for k, x in enumerate(d) if x <= asof]
    return [d[k] for k in keep], v[keep]


def extras_for(mod, extra_dir, asof):
    """Common extra series of a challenger, each on its own calendar: dict NAME -> (days, values)."""
    raw = {name: load_series(os.path.join(extra_dir, stem + '.json'), asof) for name, stem in getattr(mod, 'EXTRAS', {}).items()}
    return mod.derive(raw) if hasattr(mod, 'derive') else raw


def align(days, src_days, src_vals, lag, max_gap=MAX_GAP_DAYS):
    """Source value at (lag 0) or strictly before (lag 1) each day, as fm2.lag_fill; nan when there is none
    or when it is older than max_gap calendar days."""
    out = np.full(len(days), np.nan)
    if len(src_days) == 0 or len(days) == 0:
        return out
    idx = np.searchsorted(np.array(src_days), np.array(days), side='right' if lag == 0 else 'left') - 1
    ic = np.clip(idx, 0, len(src_days) - 1)
    gap = (np.array(days, dtype='datetime64[D]') - np.array(src_days, dtype='datetime64[D]')[ic]).astype(np.int64)
    ok = (idx >= 0) & (gap <= max_gap)
    out[ok] = np.asarray(src_vals, dtype=np.float64)[ic][ok]
    return out


def arrays_of(S, X):
    """The arrays a View is cut from: an fm1 series and the extra series aligned to its days."""
    return {'days': S.days, 'c': S.c, 'lc': S.lc, 'r': S.r, 's252': S.s252, 'm252': S.m252, 'f': S.f, 'exp_var': S.exp_var,
            'ew': fm1.ewma_var(S.r, fm1.LAM), 'x': X}


def asset_context(mod, stem, lag, pool_dir, rates_dir, extra_dir, asof, common=None, cut_test=False):
    """The arrays of one asset for View: its fm1 series and the challenger's extra series aligned to it. The asset
    file and the extra files are cut at asof before anything is computed from them (the two rate files are not cut:
    fm2.build_series aligns them day by day).
    cut_test: when this asset reads the extras strictly before the start day (xlag 1), the extra files end the
    calendar day before asof. Honest code reads the same values; a derive() that moves a value to an earlier day
    does not (review R2-3)."""
    tnx_d, tnx_v = fm1.load_yahoo(os.path.join(rates_dir, '_TNX.json'))
    irx_d, irx_v = fm1.load_yahoo(os.path.join(rates_dir, '_IRX.json'))
    d, c = fm1.load_yahoo(os.path.join(pool_dir, stem + '.json'))
    keep = [k for k, x in enumerate(d) if fm1.HIST_FLOOR <= x <= asof]
    d = [d[k] for k in keep]; c = c[keep]
    S = fm2.build_series(d, c, tnx_d, tnx_v, irx_d, irx_v, lag)
    xlag = max(int(lag), int(getattr(mod, 'EXTRA_LAG', 0)))       # strictly before the start day when either says so
    if common is None:
        end = asof
        if cut_test and xlag:
            end = (datetime.date.fromisoformat(asof) - datetime.timedelta(days=1)).isoformat()
        common = extras_for(mod, extra_dir, end)
    return arrays_of(S, {name: align(d, sd, sv, xlag) for name, (sd, sv) in common.items()})


def check_q(q):
    q = np.asarray(q, dtype=np.float64)
    if q.shape != (fm2.QN,) or not np.isfinite(q).all() or np.any(np.diff(q) < 0):
        raise ValueError('challenger returned invalid quantiles (need %d finite ascending values)' % fm2.QN)
    return q


def challenger_rows(mod, A, starts, hs, awake_from=None):
    """Challenger quantiles for forecast rows of one asset (start ordinals, horizons). A nan row = no forecast."""
    pos = {fm2.ordinal(d): k for k, d in enumerate(A['days'])}
    out = np.full((len(starts), fm2.QN), np.nan, dtype=np.float32)
    a0 = fm2.ordinal(awake_from) if awake_from else None
    st_l = [int(z) for z in np.asarray(starts).tolist()]; h_l = [int(z) for z in np.asarray(hs).tolist()]
    V = None
    for r in sorted(range(len(st_l)), key=lambda k: st_l[k]):          # one View per start day
        if a0 is not None and st_l[r] < a0:
            continue
        if V is None or V.i != pos[st_l[r]]:
            V = View(A, pos[st_l[r]])
        q = mod.quantiles(V, h_l[r])
        if q is not None:
            out[r] = check_q(q)
    return out


def same_rows(a, b, tol):
    """Number of rows of two quantile arrays that differ: one has a forecast and the other has none, or the values
    are further apart than tol = (rtol, atol)."""
    fa = np.isfinite(a).all(axis=1); fb = np.isfinite(b).all(axis=1)
    both = fa & fb
    far = np.zeros(len(a), dtype=bool)
    if both.any():
        far[both] = ~np.isclose(a[both].astype(np.float64), b[both].astype(np.float64), rtol=tol[0], atol=tol[1]).all(axis=1)
    return int((fa != fb).sum() + far.sum())


def _stage_one(args):
    path, stem, lag, pool_dir, rates_dir, extra_dir, asof, cache, out_dir, awake_from, cut_from = args
    p = os.path.join(cache, stem + '.npz')
    if not os.path.exists(p):
        return {'stem': stem, 'rows': 0, 'awake': 0, 'cut_rows': 0, 'cut_diff': 0}
    with np.load(p) as Z:
        start = Z['start']; hh = Z['h']
    cut = []                              # first the rows that can be issued in this run, each from inputs that end at its start day
    if cut_from:
        sel = np.flatnonzero((start >= fm2.ordinal(cut_from)) & (fm2.ordinal(asof) - start <= ISSUE_MAX_DAYS))
        modc = load_challenger(path)      # a module object of its own
        for st in sorted(set(start[sel].tolist())):
            rows = sel[start[sel] == st]
            Ac = asset_context(modc, stem, lag, pool_dir, rates_dir, extra_dir, str(datetime.date.fromordinal(int(st))), cut_test=True)
            if fm2.ordinal(Ac['days'][-1]) != st:
                raise ValueError('%s: start day %s is not in the input file' % (stem, datetime.date.fromordinal(int(st))))
            cut.append((rows, challenger_rows(modc, Ac, start[rows], hh[rows])))
    mod = load_challenger(path)
    Qc = challenger_rows(mod, asset_context(mod, stem, lag, pool_dir, rates_dir, extra_dir, asof), start, hh, awake_from)
    n_cut = 0; n_diff = 0
    for rows, Qn in cut:                  # the cut values stand; a difference from the values computed at asof is a look-ahead
        n_diff += same_rows(Qn, Qc[rows], CUT_TOL); n_cut += len(rows)
        Qc[rows] = Qn
    np.savez(os.path.join(out_dir, stem + '.npz'), start=start, h=hh, Qc=Qc)
    return {'id': mod.ID, 'stem': stem, 'rows': int(len(Qc)), 'awake': int(np.isfinite(Qc[:, 0]).sum()), 'cut_rows': n_cut, 'cut_diff': n_diff}


def stage(path, pool_dir, rates_dir, extra_dir, asof, cache, out_dir, awake_from=None, jobs=1, cut_from=None):
    """Challenger quantiles for every row of the fm2 expert cache (same assets, start days and horizons).
    cut_from (a day; the weekly run gives the challenger's T0): rows that start on or after it and within
    ISSUE_MAX_DAYS of asof are computed from inputs that end at their own start day. If such a row differs from the
    same row computed with the inputs cut at asof, the challenger looks ahead (or is not deterministic): CutMismatch.
    (For an asset that reads the extras strictly before the start day, the cut extras end the day before it.)
    The challenger module is loaded and run in child processes only."""
    idx = json.load(open(os.path.join(cache, 'INDEX.json')))
    if idx['asof'] != asof:
        raise ValueError('fm2 cache asof %s is not %s' % (idx['asof'], asof))
    bad = static_check(open(path, encoding='utf-8').read())
    if bad:
        raise ValueError('challenger refused: ' + '; '.join(bad))
    os.makedirs(out_dir, exist_ok=True)
    cf = max(cut_from, FORWARD_START) if cut_from else None
    args = [(path, s, l, pool_dir, rates_dir, extra_dir, asof, cache, out_dir, awake_from, cf) for s, _, l in fm2.UNIVERSE]
    import multiprocessing as mp
    t = time.time()
    with mp.get_context('fork').Pool(max(int(jobs), 1)) as p:
        infos = p.map(_stage_one, args, chunksize=1)
    cid = next((a['id'] for a in infos if 'id' in a), None)
    infos = [{k: v for k, v in a.items() if k != 'id'} for a in infos]
    info = {'id': cid, 'module_sha256': sha(path), 'asof': asof, 'awake_from': awake_from, 'cut_from': cf,
            'rows': sum(a['rows'] for a in infos), 'awake': sum(a['awake'] for a in infos),
            'cut_rows': sum(a['cut_rows'] for a in infos), 'cut_diff': sum(a['cut_diff'] for a in infos),
            'seconds': round(time.time() - t, 1), 'assets': infos}
    json.dump(info, open(os.path.join(out_dir, 'INDEX.json'), 'w'), indent=1)
    if info['cut_diff']:
        raise CutMismatch('%d of %d new forecasts differ between inputs cut at the start day and inputs cut at asof '
                          '(look-ahead or non-determinism)' % (info['cut_diff'], info['cut_rows']))
    return info


def load_shadow(cache, ch_dirs):
    """The fm2 cache plus challenger quantiles (F['Qc_<id>']), per horizon, ready for fm2.prep.
    ch_dirs: dict id -> staged dir. Row order is the fm2.load_cache order; fm2.prep then sorts every array."""
    idx, data = fm2.load_cache(cache)
    for cid, d in ch_dirs.items():
        parts = {h: [] for h in fm2.HORIZONS}
        for info in idx['assets']:
            p = os.path.join(cache, info['stem'] + '.npz')
            if not os.path.exists(p):
                continue
            Z = np.load(p); C = np.load(os.path.join(d, info['stem'] + '.npz'))
            if not (np.array_equal(Z['start'], C['start']) and np.array_equal(Z['h'], C['h'])):
                raise ValueError('challenger rows differ from the fm2 cache: %s %s' % (cid, info['stem']))
            for h in fm2.HORIZONS:
                parts[h].append(C['Qc'][Z['h'] == h])
        for h in fm2.HORIZONS:
            data[h]['Qc_' + cid] = np.concatenate(parts[h])
    return idx, data


def load_issued(files):
    """The forecasts a challenger issued, from its run files (oldest first): dict stem -> {(start, h): float32[QN]}.
    A nan row = the challenger issued nothing for that row. The first record of a row stands."""
    out = {}
    for p in files:
        with np.load(p) as Z:
            for stem, st, h, q in zip(Z['stem'].tolist(), Z['start'].tolist(), Z['h'].tolist(), Z['Qc']):
                out.setdefault(stem, {}).setdefault((int(st), int(h)), q)
    return out


def freeze(out_dir, issued, t0, asof, new_path):
    """Make the judged rows of a staged challenger the forecasts as first issued (rule section 5).
    Judged rows = start day >= max(t0, FORWARD_START). A row that an earlier run issued keeps the issued value,
    whatever today's recomputation says (a difference is counted, never used). A row seen for the first time is
    issued now: the staged value if asof is within ISSUE_MAX_DAYS calendar days of its start day, otherwise
    "no forecast" (it was not issued in time, so the base pool stands there).
    The new rows are written to new_path (.npz) when there are any. Returns the counts:
    rows (judged rows staged), kept (issued earlier), changed (kept rows that carry a forecast and whose
    recomputation differs), none_kept (kept rows issued as "no forecast" that today's inputs could compute: they
    stay "no forecast"; this is no data revision and is not reported as one),
    new (issued now), new_no_forecast (of the new rows: no forecast, late ones included), late (not issued in time),
    orphans (issued rows that have no row in today's grid: a past bar was added or removed and the grid moved)."""
    f0 = max(fm2.ordinal(t0), fm2.ordinal(FORWARD_START)); a0 = fm2.ordinal(asof)
    new = {'stem': [], 'start': [], 'h': [], 'Qc': []}
    st = {'rows': 0, 'kept': 0, 'changed': 0, 'none_kept': 0, 'max_abs_diff': 0.0, 'new': 0, 'new_no_forecast': 0, 'late': 0,
          'orphans': 0, 'file': None}
    for stem, _, _ in fm2.UNIVERSE:
        p = os.path.join(out_dir, stem + '.npz')
        if not os.path.exists(p):
            continue
        with np.load(p) as Z:
            start = Z['start']; hh = Z['h']; Qc = Z['Qc'].copy()
        have = issued.get(stem, {})
        judged = np.flatnonzero(start >= f0).tolist()
        st['orphans'] += len(set(have) - {(int(start[j]), int(hh[j])) for j in judged})
        for j in judged:
            key = (int(start[j]), int(hh[j])); st['rows'] += 1
            if key in have:
                old = have[key]; a = bool(np.isfinite(old).all()); b = bool(np.isfinite(Qc[j]).all())
                if b and not a:
                    st['none_kept'] += 1
                elif a != b or (a and not np.allclose(Qc[j], old, rtol=ISSUE_TOL[0], atol=ISSUE_TOL[1])):
                    st['changed'] += 1
                    if a and b:
                        st['max_abs_diff'] = max(st['max_abs_diff'], float(np.abs(Qc[j].astype(np.float64) - old).max()))
                Qc[j] = old; st['kept'] += 1
            else:
                if a0 - key[0] > ISSUE_MAX_DAYS:
                    Qc[j] = np.nan; st['late'] += 1
                st['new'] += 1; st['new_no_forecast'] += int(not np.isfinite(Qc[j]).all())
                for k, v in zip(('stem', 'start', 'h', 'Qc'), (stem, key[0], key[1], Qc[j].copy())):
                    new[k].append(v)
        np.savez(p, start=start, h=hh, Qc=Qc)
    if st['new']:
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        tmp = new_path[:-4] + '.tmp.npz'
        np.savez(tmp, stem=np.array(new['stem']), start=np.array(new['start'], dtype=np.int64), h=np.array(new['h'], dtype=np.int64),
                 Qc=np.stack(new['Qc']).astype(np.float32), asof=np.array(asof))
        os.replace(tmp, new_path); st['file'] = new_path
    return st


# ---------------- shadow learner ----------------
def terms(F, W, Qc):
    """Per-forecast pieces of the mixture CRPS identity for the pair (pool P with weights W, expert c):
    awake, a_c = E|c - y|, d_cc = E|c - c'|, d_Pc = E|P - c|, a_P = E|P - y|, d_PP = E|P - P'|  (all / norm)."""
    n = len(F['y']); norm = F['norm']; y = F['y']; Q = F['Q']
    aw = np.isfinite(Qc).all(axis=1)
    ix = np.flatnonzero(aw)
    Ac = np.full(n, np.nan); Dcc = np.zeros(n); dPc = np.zeros(n)
    if len(ix):
        qc = Qc[ix].astype(np.float64)
        with np.errstate(invalid='ignore'):
            Ac[ix] = np.abs(qc - y[ix, None]).mean(axis=1) / norm[ix]          # nan when not matured
        Dcc[ix] = fm2.pair_abs(qc, qc) / norm[ix]
        for k in range(Q.shape[1]):
            dPc[ix] += W[ix, k] * fm2.pair_abs(Q[ix, k], qc) / norm[ix]
    with np.errstate(invalid='ignore'):
        aP = np.einsum('nk,nk->n', W, F['A'])                                  # nan when not matured
    dPP = np.einsum('nk,nkl,nl->n', W, F['D'], W)
    return aw, Ac, Dcc, dPc, aP, dPP


def shadow_learn(F, R, Qc, prior=PRIOR, eta_top=fm2.ETA_TOP, hc=fm2.HC, n0=fm2.N0, learn_w=True, learn_s=True):
    """Shadow pool P+ for one horizon. F: fm2.prep output. R: fm2.learn(F, ...) run with the same learn_w /
    learn_s (the base pool P). Qc: [n, QN] challenger quantiles, nan rows where c has no forecast.
    Returns per-forecast arrays (normalised CRPS and 80% hit of the issued P+ forecast, om, s+)."""
    n = len(F['y']); start = F['start']; mat = F['mat']; y = F['y']; norm = F['norm']; u = F['u']
    D = F['D']; Q = F['Q'].astype(np.float64); W = R['W']; QN = fm2.QN
    aw, Ac, Dcc, dPc, aP, dPP = terms(F, W, Qc)
    Qc = Qc.astype(np.float64)
    lP = aP - 0.5 * dPP; lc = Ac - 0.5 * Dcc                  # normalised CRPS of the pool P and of the expert c
    metas = [(e, H) for e in fm2.ETAS for H in fm2.HALFS]     # + static learner at the end
    nm = len(metas) + 1
    L2 = np.zeros((len(metas), 2))                            # discounted losses of (P, c) per learner
    Mloss = np.zeros(nm)                                      # undiscounted learner losses
    OMm = np.zeros((n, nm)); OM = np.zeros(n); sc = np.ones(n)
    pool = np.zeros((n, 3))                                   # unscaled P+ median, q10, q90 at issue
    crps = np.full(n, np.nan); hit = np.full(n, np.nan)
    order_mat = np.array([j for j in np.argsort(mat, kind='stable') if mat[j] >= 0], dtype=int)
    pm = 0
    cal_r = np.empty(n); cal_u = np.empty(n); cal_t = np.empty(n); nc = 0     # kept sorted by r
    uniq = np.unique(start)
    lo = 0; t_prev = None; odds = (1.0 - prior) / prior
    om_t = prior; om_m = np.full(nm, prior); s = 1.0
    for t in uniq:
        if t_prev is not None:
            dt = float(t - t_prev)
            for m, (e, H) in enumerate(metas):
                if math.isfinite(H):
                    L2[m] *= 0.5 ** (dt / H)
        # 1. absorb forecasts that matured on an earlier calendar date
        while pm < len(order_mat) and mat[order_mat[pm]] < t:
            j = order_mat[pm]; pm += 1
            if aw[j]:                                         # c issued this one: it carries evidence about om
                for m, (e, H) in enumerate(metas):
                    dec = 0.5 ** (float(t - mat[j]) / H) if math.isfinite(H) else 1.0
                    L2[m, 0] += u[j] * dec * lP[j]; L2[m, 1] += u[j] * dec * lc[j]
                o = OMm[j]
                Mloss += u[j] * ((1 - o) * aP[j] + o * Ac[j]
                                 - 0.5 * ((1 - o) ** 2 * dPP[j] + 2 * o * (1 - o) * dPc[j] + o ** 2 * Dcc[j]))
            med, q10, q90 = pool[j]
            r = (y[j] - med) / max(q90 - med, 1e-12) if y[j] >= med else (med - y[j]) / max(med - q10, 1e-12)
            pos = int(np.searchsorted(cal_r[:nc], r, side='right'))
            for arr, val in ((cal_r, r), (cal_u, u[j]), (cal_t, float(mat[j]))):
                arr[pos + 1:nc + 1] = arr[pos:nc]
                arr[pos] = val
            nc += 1
        # 2. share of the challenger: learner m gives prior * exp(-eta * L_c) against (1 - prior) * exp(-eta * L_P)
        om_m = np.array([1.0 / (1.0 + odds * math.exp(min(700.0, max(-700.0, -e * (L2[m, 0] - L2[m, 1])))))
                         for m, (e, H) in enumerate(metas)] + [prior])
        v = fm2.softmin(Mloss, eta_top)
        om_t = float(v @ om_m) if learn_w else prior
        # 3. scale (fm2.learn step 3, on the bands P+ issued)
        s = 1.0
        if learn_s and nc:
            c_ = cal_u[:nc] * 0.5 ** ((t - cal_t[:nc]) / hc) if math.isfinite(hc) else cal_u[:nc]
            cw = np.cumsum(c_); neff = float(cw[-1])
            s_hat = float(cal_r[min(int(np.searchsorted(cw, fm2.COVER * neff, side='left')), nc - 1)])
            s = (neff * s_hat + n0 * 1.0) / (neff + n0)
        # 4. issue today's forecasts
        hi = lo
        while hi < n and start[hi] == t:
            hi += 1
        for j in range(lo, hi):
            OMm[j] = om_m; sc[j] = s
            if aw[j]:
                OM[j] = om_t
                x = np.concatenate([Q[j].ravel(), Qc[j]])
                w = np.concatenate([np.repeat((1.0 - om_t) * W[j] / QN, QN), np.full(QN, om_t / QN)])
                quad = (1 - om_t) ** 2 * dPP[j] + 2 * om_t * (1 - om_t) * dPc[j] + om_t ** 2 * Dcc[j]
            else:                                             # no challenger forecast: P+ is P
                x = Q[j].ravel(); w = np.repeat(W[j] / QN, QN)
                quad = float(W[j] @ D[j] @ W[j])
            med, q10, q90 = fm2.wq(x, w, [0.5, 0.1, 0.9])
            pool[j] = (med, q10, q90)
            if mat[j] >= 0:
                xs = med + s * (x - med)
                crps[j] = (float(np.sum(w * np.abs(xs - y[j]))) / norm[j]) - 0.5 * s * quad
                hit[j] = float(med + s * (q10 - med) <= y[j] <= med + s * (q90 - med))
        lo = hi; t_prev = t
    return {'crps': crps, 'hit': hit, 'om': OM, 's': sc, 'awake': aw, 'med': pool[:, 0].copy(),
            'state_last': {'date': str(datetime.date.fromordinal(int(t_prev))), 'om': float(om_t), 's': float(s),
                           'om_by_learner': [float(z) for z in om_m],
                           'learner_weights': [float(z) for z in fm2.softmin(Mloss, eta_top)]}}


# ---------------- paired score and status ----------------
def compare(F, R, P, win, q, min_ci_weeks):
    """Paired score of a shadow pool P against its base R over every matured forecast in the boolean window
    win, all assets. Where the challenger issued nothing the two pools differ only by the width scale; that
    difference is part of what adoption would change, so those forecasts are scored too.
    Interval: t interval over q consecutive time groups."""
    aw = P['awake']; mk = win & (F['mat'] >= 0); ma = mk & aw
    row = {'n_issued': int(win.sum()), 'n_issued_by_challenger': int((win & aw).sum()), 'n_scored': int(mk.sum()),
           'n_scored_by_challenger': int(ma.sum()), 'weeks': 0}
    if mk.sum():
        c = P['crps'][mk]; b = R['crps'][mk]
        weeks = len(set(F['week'][mk].tolist()))
        row.update({'weeks': weeks, 'indep_periods': round(weeks / (F['h_val'] // fm2.GRID_STEP), 2),
                    'gain': float(1 - c.sum() / b.sum()), 'cov80_plus': float(P['hit'][mk].mean()),
                    'cov80_base': float(R['hit'][mk].mean()),
                    'gain_where_issued': float(1 - P['crps'][ma].sum() / R['crps'][ma].sum()) if ma.sum() else None,
                    'om_mean': float(P['om'][ma].mean()) if ma.sum() else None,
                    'first_start': str(datetime.date.fromordinal(int(F['start'][mk].min()))),
                    'last_start': str(datetime.date.fromordinal(int(F['start'][mk].max())))})
        if weeks >= max(min_ci_weeks, q):
            G = fm2.group_sums(F['week'][mk], {'p': c, 'b': b}, q)
            g = 1 - G['p'] / G['b']
            row['gain_ci95'] = fm2.t_ci(g); row['gain_groups'] = [round(float(z), 5) for z in g]
    return row


def judge(row, h):
    """Status of one judged horizon from its paired forward row (rule section 5). Deterministic.
    shadow: keep scoring. pass_to_judge: at the minimum sample the paired gain is above zero -> independent judge,
    then a decision card (never automatic). end_*: finished at the minimum sample without adoption.
    drop_futility: at an interim look before the minimum sample the upper bound of the interval was below zero
    (20 days only). It frees the slot; it is not a final verdict of harm (rule section 12)."""
    w = row.get('weeks', 0); ci = row.get('gain_ci95')
    if ci is None:
        return 'shadow'
    lo, hi = ci
    if w < MIN_WEEKS[h]:
        return 'drop_futility' if (h in FUT_WEEKS and w >= FUT_WEEKS[h] and hi < 0) else 'shadow'
    if lo > 0:
        return 'pass_to_judge' if COV_BAND[0] <= row['cov80_plus'] <= COV_BAND[1] else 'end_coverage'
    return 'end_harm' if hi < 0 else 'end_inconclusive'


def score_horizon(F, specs):
    """All pairs of one horizon. F: fm2.prep output holding F['Qc_<id>']. specs: dict id -> {'t0': first judged
    start day}. Returns (rows per challenger, FM2 run, F0 run). 'forward' is the judged window: starts >=
    max(t0, FORWARD_START). Nothing is scored before it."""
    h = F['h_val']
    R = fm2.learn(F); R0 = fm2.learn(F, learn_w=False, learn_s=False)
    f0 = fm2.ordinal(FORWARD_START); out = {}
    for cid, sp in specs.items():
        Qc = F['Qc_' + cid]; t0 = max(f0, fm2.ordinal(sp['t0']))
        P = shadow_learn(F, R, Qc); P0 = shadow_learn(F, R0, Qc, learn_w=False, learn_s=False)
        fwd = F['start'] >= t0
        out[cid] = {'forward': {'FM2': compare(F, R, P, fwd, FWD_Q, CI_WEEKS[h]), 'F0': compare(F, R0, P0, fwd, FWD_Q, CI_WEEKS[h])},
                    'state': P['state_last']}
    return out, R, R0


# ---------------- admission ----------------
def admit_points(n):
    """Test points of one asset with n days: start-day indices spread over its history, and those also computed cut."""
    pts = sorted({int(z) for z in np.linspace(fm2.MIN_ROWS, n - 1, ADMIT_POINTS)}) if n > fm2.MIN_ROWS else []
    return pts, sorted(set(pts[::3] + pts[-1:]))


def admit_pass(path, pool_dir, rates_dir, extra_dir, asof, mode, outp):
    """One pass of the admission; each pass runs in an interpreter of its own (see admit).
    mode 'full': every test point with the inputs cut at asof, twice (the second time in another call order).
    mode 'cut':  first the cut points, each from inputs that end at its own day, then the 'full' values once more.
    Writes <outp> (.npz) and <outp>.json. No outcome is read."""
    lag_of = {s: l for s, _, l in fm2.UNIVERSE}
    keys = []; Q = []; ckeys = []; CQ = []; ratios = []; meds = []; secs = 0.0; n_call = 0; same = True

    def calls(m, A, stem_k, pts, order, timed):
        nonlocal secs, n_call
        out = {}
        for i in order(pts):
            V = View(A, i)
            for h in order(fm2.HORIZONS):
                t = time.perf_counter(); q = m.quantiles(V, h)
                if timed:
                    secs += time.perf_counter() - t; n_call += 1
                out[(stem_k, i, h)] = np.full(fm2.QN, np.nan) if q is None else check_q(q).copy()
        return out
    fwd = lambda z: list(z); rev = lambda z: list(reversed(z))
    if mode == 'cut':
        modc = load_challenger(path)
        for k, (stem, _, _) in enumerate(fm2.UNIVERSE):
            days = [d for d in fm1.load_yahoo(os.path.join(pool_dir, stem + '.json'))[0] if fm1.HIST_FLOOR <= d <= asof]
            for i in admit_points(len(days))[1]:
                Ac = asset_context(modc, stem, lag_of[stem], pool_dir, rates_dir, extra_dir, days[i], cut_test=True)
                assert len(Ac['days']) == i + 1
                for key, q in calls(modc, Ac, k, [i], fwd, False).items():
                    ckeys.append(key); CQ.append(q)
    mod = load_challenger(path)
    for k, (stem, _, _) in enumerate(fm2.UNIVERSE):
        A = asset_context(mod, stem, lag_of[stem], pool_dir, rates_dir, extra_dir, asof)
        pts = admit_points(len(A['days']))[0]
        first = calls(mod, A, k, pts, fwd, True)
        if mode == 'full':
            again = calls(mod, A, k, pts, rev, False)
            same &= all(np.array_equal(first[key], again[key], equal_nan=True) for key in first)
        for (kk, i, h), q in first.items():
            keys.append((kk, i, h)); Q.append(q)
            if np.isfinite(q).all():
                sd = float(A['s252'][i]) * math.sqrt(h)
                lo, md, hi = fm2.wq(q, np.full(fm2.QN, 1.0 / fm2.QN), [0.1, 0.5, 0.9])
                ratios.append((hi - lo) / ((fm2.Z90 - fm2.Z10) * sd)); meds.append(abs(md) / sd)
    np.savez(outp, keys=np.array(keys, dtype=np.int64).reshape(-1, 3), Q=np.array(Q, dtype=np.float64).reshape(-1, fm2.QN),
             ckeys=np.array(ckeys, dtype=np.int64).reshape(-1, 3), CQ=np.array(CQ, dtype=np.float64).reshape(-1, fm2.QN),
             ratios=np.array(ratios), meds=np.array(meds))
    json.dump({'id': mod.ID, 'extras': getattr(mod, 'EXTRAS', {}), 'extra_lag': int(getattr(mod, 'EXTRA_LAG', 0)),
               'seconds': secs, 'calls': n_call, 'same_order': bool(same)}, open(outp + '.json', 'w'))


def admit(path, pool_dir, rates_dir, extra_dir, asof, cache=None, jobs=1):
    """Technical admission tests of a challenger module on real inputs. No outcome is scored or read.
    The challenger never runs in this process: two fresh interpreters compute the test points (all 20 assets,
    ADMIT_POINTS start days each, every horizon), and their outputs are compared here:
      deterministic   same values in another call order and in another process
      no_lookahead    inputs that end at the test day give the same values as inputs cut at asof
      runtime, units  speed; width and centre against the one-year normal range (gross and constant-factor errors)
      full_grid       (with an fm2 cache) every row of the weekly grid is staged once: no error, no invalid output
    Returns a report dict; report['pass'] is the verdict."""
    rep = {'module': os.path.basename(path), 'module_sha256': sha(path), 'asof': asof, 'tests': {}}
    T = rep['tests']
    bad = static_check(open(path, encoding='utf-8').read())
    T['static'] = {'pass': not bad, 'refused': bad}
    if bad:
        rep['pass'] = False
        return rep
    with tempfile.TemporaryDirectory(prefix='fm3_admit_') as tmp:
        outs = {m: os.path.join(tmp, m + '.npz') for m in ('full', 'cut')}
        procs = {m: subprocess.Popen([sys.executable, '-I', '-B', os.path.abspath(__file__), 'admit-pass', path, pool_dir, rates_dir,
                                      extra_dir, asof, m, o], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                 for m, o in outs.items()}
        err = None
        for m, pr in procs.items():
            try:
                e = pr.communicate(timeout=ADMIT_TIMEOUT)[1]
            except subprocess.TimeoutExpired:
                pr.kill(); e = pr.communicate()[1] + '\ntimeout after %d s' % ADMIT_TIMEOUT
            if pr.returncode != 0 or not os.path.exists(outs[m] + '.json'):
                err = err or '%s pass: %s' % (m, (e.strip().splitlines() or ['no output'])[-1][:300])
        if err is None:
            R = {m: (dict(np.load(o)), json.load(open(o + '.json'))) for m, o in outs.items()}
    if err is not None:
        api_err = 'challenger refused' in err
        T['api' if api_err else 'valid_output'] = {'pass': False, 'error': err}; rep['pass'] = False
        return rep
    (Zf, Jf), (Zc, Jc) = R['full'], R['cut']
    T['api'] = {'pass': True, 'id': Jf['id'], 'extras': Jf['extras'], 'extra_lag': Jf['extra_lag']}
    n_aw = int(np.isfinite(Zf['Q']).all(axis=1).sum())
    T['valid_output'] = {'pass': True, 'calls': int(len(Zf['Q'])), 'forecasts': n_aw, 'error': None}
    same_keys = np.array_equal(Zf['keys'], Zc['keys'])
    T['deterministic'] = {'pass': bool(Jf['same_order'] and same_keys and np.array_equal(Zf['Q'], Zc['Q'], equal_nan=True)),
                          'same_in_another_call_order': bool(Jf['same_order']),
                          'rows_that_differ_in_another_process': same_rows(Zf['Q'], Zc['Q'], (0.0, 0.0)) if same_keys else None}
    at = {tuple(k): j for j, k in enumerate(Zf['keys'].tolist())}
    pick = [at.get(tuple(k), -1) for k in Zc['ckeys'].tolist()]
    n_la = same_rows(Zc['CQ'], Zf['Q'][pick], (1e-9, 1e-12)) if len(pick) and min(pick) >= 0 else None
    T['no_lookahead'] = {'pass': n_la == 0, 'cut_points': len(pick), 'rows_that_differ': n_la}
    mean_s = Jf['seconds'] / max(Jf['calls'], 1)
    T['runtime'] = {'pass': bool(mean_s <= RUNTIME_LIMIT), 'mean_seconds': round(mean_s, 5), 'limit': RUNTIME_LIMIT}
    ra = Zf['ratios']; me = Zf['meds']
    okw = bool(n_aw > 0 and WIDTH_BAND[0] <= ra.min() and ra.max() <= WIDTH_BAND[1]
               and WIDTH_MED_BAND[0] <= float(np.median(ra)) <= WIDTH_MED_BAND[1] and me.max() <= MED_MAX)
    T['units'] = {'pass': okw, 'width_ratio_min_max': [round(float(ra.min()), 3), round(float(ra.max()), 3)] if n_aw else None,
                  'width_ratio_median': round(float(np.median(ra)), 3) if n_aw else None,
                  'abs_median_over_sd_max': round(float(me.max()), 3) if n_aw else None,
                  'band': list(WIDTH_BAND), 'median_band': list(WIDTH_MED_BAND), 'median_over_sd_limit': MED_MAX}
    if cache is not None:
        with tempfile.TemporaryDirectory(prefix='fm3_admit_grid_') as tmp:
            try:
                info = stage(path, pool_dir, rates_dir, extra_dir, asof, cache, tmp, jobs=jobs)
                T['full_grid'] = {'pass': True, 'rows': info['rows'], 'forecasts': info['awake'], 'seconds': info['seconds']}
            except Exception as e:
                T['full_grid'] = {'pass': False, 'error': '%s: %s' % (type(e).__name__, str(e)[:300])}
    rep['pass'] = all(t['pass'] for t in T.values())
    return rep


# ---------------- self test ----------------
def synth(rng, n_weeks=420, n_assets=6, h=20, kind='good', wake_week=0, base_day='2027-01-04'):
    """Synthetic pool: the four fm2.selftest experts (N(0,1), N(0,2), N(0.5,1), N(0,0.5)); the true width
    switches between 0.6 and 1.8 every 26 weeks. Challenger: 'good' knows the true width, 'bad' is N(1, 0.3)."""
    base = fm2.ordinal(base_day); rows = []
    for w in range(n_weeks):
        sd = 0.6 if (w // 26) % 2 == 0 else 1.8
        for a in range(n_assets):
            st = base + 7 * w + (a % 3)
            rows.append((st, st + int(h * 7 / 5) + 1, rng.standard_normal() * sd, a, sd, w))
    start = np.array([r[0] for r in rows]); mat = np.array([r[1] for r in rows]); y = np.array([r[2] for r in rows])
    last = start.max()
    mat = np.where(mat <= last, mat, -1); y = np.where(mat >= 0, y, np.nan)
    n = len(rows); Z = fm2.ZQ
    Q = np.stack([np.stack([Z, 2 * Z, 0.5 + Z, 0.5 * Z])] * n).astype(np.float32)
    sd = np.array([r[4] for r in rows]); wk = np.array([r[5] for r in rows])
    Qc = (sd[:, None] * Z[None, :] if kind == 'good' else 1.0 + 0.3 * Z[None, :] + 0 * sd[:, None]).astype(np.float32)
    Qc[wk < wake_week] = np.nan
    return {'start': start, 'mat': mat, 'y': y, 'norm': np.ones(n), 'Q': Q, 'bc': np.zeros((n, 4)), 'bh': np.zeros((n, 4)),
            'asset': np.array([r[3] for r in rows]), 'cls': np.array(['x'] * n), 'h_val': h, 'Qc': Qc}


GOOD_SRC = '''"""selftest challenger: fm1 M1 rebuilt through the View."""
import math
import numpy as np
ID = 'm1view'


def quantiles(V, h):
    i = V.i; last = i - h
    if last < 260:
        return None
    v = V.vh(h); yh = V.yh(h)
    z = yh[260:last + 1] / (v[260:last + 1] * math.sqrt(h))
    return np.quantile(z[np.isfinite(z)], V.QL) * v[i] * math.sqrt(h)
'''


def selftest():
    import tempfile
    rng = np.random.default_rng(11)
    eq = lambda a, b: np.array_equal(a, b, equal_nan=True)
    # (1) challenger absent everywhere: the fm2.learn numbers, exactly (both pairs)
    F = fm2.prep(fm2.synth_F(rng, n_weeks=300))
    none = np.full((len(F['y']), fm2.QN), np.nan, dtype=np.float32)
    for kw in (dict(), dict(learn_w=False, learn_s=False)):
        R = fm2.learn(F, **kw); P = shadow_learn(F, R, none, **kw)
        assert eq(P['crps'], R['crps']) and eq(P['hit'], R['hit']) and eq(P['s'], R['s']) and not P['om'].any()
    # (2) mixture identity: the formula equals the direct CRPS of the 5-component weighted sample (unscaled and scaled)
    F = fm2.prep(synth(rng, n_weeks=80)); R = fm2.learn(F)
    aw, Ac, Dcc, dPc, aP, dPP = terms(F, R['W'], F['Qc'])
    j = int(np.flatnonzero(F['mat'] >= 0)[40]); om = 0.37; QN = fm2.QN
    x = np.concatenate([F['Q'][j].astype(np.float64).ravel(), F['Qc'][j].astype(np.float64)])
    w = np.concatenate([np.repeat((1 - om) * R['W'][j] / QN, QN), np.full(QN, om / QN)])
    quad = (1 - om) ** 2 * dPP[j] + 2 * om * (1 - om) * dPc[j] + om ** 2 * Dcc[j]
    direct = fm1.crps_w(x.copy(), w.copy(), F['y'][j])
    assert abs(direct - ((1 - om) * aP[j] + om * Ac[j] - 0.5 * quad)) < 1e-6, direct
    med = fm2.wq(x, w, [0.5])[0]; xs = med + 0.8 * (x - med)
    assert abs(fm1.crps_w(xs.copy(), w.copy(), F['y'][j]) - (float(np.sum(w * np.abs(xs - F['y'][j]))) - 0.5 * 0.8 * quad)) < 1e-6
    # (3) a challenger that knows the width: its share grows, the shadow pool wins, the status is pass_to_judge
    F = fm2.prep(synth(rng)); R = fm2.learn(F); P = shadow_learn(F, R, F['Qc'])
    win = F['start'] >= fm2.ordinal('2027-01-04')
    row = compare(F, R, P, win, FWD_Q, CI_WEEKS[20])
    print('good challenger:', {k: row[k] for k in ('weeks', 'gain', 'gain_ci95', 'cov80_plus', 'cov80_base', 'om_mean')}, 'om last', round(P['state_last']['om'], 3))
    assert row['gain'] > 0.02 and row['gain_ci95'][0] > 0 and P['state_last']['om'] > 0.5 and judge(row, 20) == 'pass_to_judge'
    R0 = fm2.learn(F, learn_w=False, learn_s=False); P0 = shadow_learn(F, R0, F['Qc'], learn_w=False, learn_s=False)
    assert np.allclose(P0['om'][P0['awake']], PRIOR) and (P0['s'] == 1).all() and compare(F, R0, P0, win, FWD_Q, CI_WEEKS[20])['gain'] > 0
    # (4) a bad challenger: its share falls to almost nothing and the shadow pool is protected
    F = fm2.prep(synth(rng, kind='bad')); R = fm2.learn(F); P = shadow_learn(F, R, F['Qc'])
    row = compare(F, R, P, F['start'] >= 0, FWD_Q, CI_WEEKS[20])
    print('bad challenger:', {k: row[k] for k in ('weeks', 'gain', 'gain_ci95', 'om_mean')}, 'om last', round(P['state_last']['om'], 4))
    assert P['state_last']['om'] < 0.02 and -0.05 < row['gain'] < 0 and judge(row, 20) in ('end_harm', 'end_inconclusive')
    early = compare(F, R, P, F['start'] < F['start'].min() + 7 * 60, FWD_Q, CI_WEEKS[20])
    assert 'gain_ci95' not in early and judge(early, 20) == 'shadow' and judge({'weeks': 30}, 20) == 'shadow'
    assert CI_WEEKS == {20: 65, 60: 193, 250: 801} and FUT_WEEKS == {20: 65}
    assert all(CI_WEEKS[h] / FWD_Q * fm2.GRID_STEP / h > 4 >= (CI_WEEKS[h] - 1) / FWD_Q * fm2.GRID_STEP / h and MIN_WEEKS[h] >= CI_WEEKS[h] for h in MIN_WEEKS)
    assert 'gain_ci95' in compare(F, R, P, F['start'] < F['start'].min() + 7 * 65, FWD_Q, CI_WEEKS[20])
    assert judge({'weeks': 64, 'gain_ci95': [-0.02, -0.001]}, 20) == 'shadow'            # no interim look before 65 weeks
    assert judge({'weeks': 65, 'gain_ci95': [-0.02, -0.001]}, 20) == 'drop_futility'
    assert judge({'weeks': 200, 'gain_ci95': [-0.02, -0.001]}, 60) == 'shadow'           # and none at all at 60 days
    assert judge({'weeks': 208, 'gain_ci95': [-0.02, -0.001], 'cov80_plus': 0.8}, 60) == 'end_harm'
    assert judge({'weeks': 70, 'gain_ci95': [0.001, 0.02], 'cov80_plus': 0.8}, 20) == 'shadow'
    assert judge({'weeks': 104}, 20) == 'shadow'                                          # never judged without an interval
    assert judge({'weeks': 104, 'gain_ci95': [0.001, 0.02], 'cov80_plus': 0.8}, 20) == 'pass_to_judge'
    assert judge({'weeks': 104, 'gain_ci95': [0.001, 0.02], 'cov80_plus': 0.65}, 20) == 'end_coverage'
    assert judge({'weeks': 104, 'gain_ci95': [-0.01, 0.02], 'cov80_plus': 0.8}, 20) == 'end_inconclusive'
    assert judge({'weeks': 150, 'gain_ci95': [0.001, 0.02], 'cov80_plus': 0.8}, 60) == 'shadow'
    # (5) a challenger that starts later: everything issued before its first forecast is the base pool, exactly
    F = fm2.prep(synth(rng, wake_week=200)); R = fm2.learn(F); P = shadow_learn(F, R, F['Qc'])
    t_wake = F['start'][P['awake']].min(); before = F['start'] < t_wake
    assert before.sum() > 500 and eq(P['crps'][before], R['crps'][before]) and eq(P['s'][before], R['s'][before])
    assert np.allclose(P['om'][F['start'] == t_wake], PRIOR) and not eq(P['crps'][~before], R['crps'][~before])
    # (6) no look-ahead: changing outcomes that mature on/after t0 leaves every share and scale issued up to t0 unchanged
    t0 = int(np.quantile(F['start'], 0.75))
    F2 = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in F.items()}
    F2['y'] = np.where(F2['mat'] >= t0, F2['y'] * 3 + 1, F2['y'])
    with np.errstate(invalid='ignore'):
        F2['A'] = np.abs(F2['Q'].astype(np.float64) - F2['y'][:, None, None]).mean(axis=2) / F2['norm'][:, None]
    R2 = fm2.learn(F2); P2 = shadow_learn(F2, R2, F2['Qc'])
    upto = F['start'] <= t0
    assert np.allclose(P['om'][upto], P2['om'][upto]) and np.allclose(P['s'][upto], P2['s'][upto])
    assert not np.allclose(P['om'][~upto], P2['om'][~upto])
    # (7) static check
    assert static_check(GOOD_SRC) == []
    for bad in ('import os\n', 'from numpy import random\nimport numpy as np\nx = np.random\n', 'def quantiles(V, h):\n    return V._S\n',
                'def quantiles(V, h):\n    return open("x")\n', 'class A:\n    pass\n', 'x = 1\nx += 1\n',
                'import numpy as np\ndef f(a):\n    a.flags.writeable = True\n', 'def f():\n    global z\n',
                'def f():\n    return __builtins__\n', 'def f():\n    return __loader__.get_data("x")\n',
                'import numpy as np\ndef f():\n    return np.ma.core\n', 'import numpy as np\ndef f():\n    return np.polynomial\n',
                'C = {}\ndef f(k):\n    C[k] = 1\n', 'C = []\ndef f(k):\n    C.append(k)\n', 'def f(k, c=[]):\n    return c\n',
                'import numpy as np\ndef f():\n    np.x = 1\n', 'def f(x):\n    return hash(x)\n', 'f = lambda k, c={}: c\n',
                'import numpy as np\ndef f():\n    m = np\n    return m.zeros(1)\n', 'def f(x):\n    x.shape = (1,)\n',
                'C = [1, 2]\n', 'import numpy as np\nC = np.zeros(3)\n', "EXTRAS = {'E': '_E'}\ndef f():\n    return EXTRAS\n",
                "EXTRAS = {'E': 5}\n", "def f(x):\n    return '{0.base}'.format(x)\n",
                'def f():\n    g = (x for x in ())\n    return g.gi_frame\n', 'def f(g):\n    return g.f_builtins\n',
                "import numpy as np\ndef f():\n    return np.datetime64('today')\n", "import numpy as np\ndef f():\n    return np.array(' NOW ', dtype='M8[s]')\n",
                'def f(V):\n    V.i = 3\n', 'def f(V):\n    return V._x\n'):
        assert static_check(bad), bad
    assert static_check("import numpy as np\n\n\ndef f(d):\n    return np.array(d, dtype='datetime64[D]')\n") == []
    assert static_check("ID = 'a'\nEXTRAS = {'E': '_E'}\nT = (1, 2.5, 'x')\nH = 60.0 * 2\nN = -1\n\n\ndef quantiles(V, h):\n    return None\n") == []
    assert static_check('import numpy as np\nW = 5\n\n\ndef f(a, k=3):\n    b = np.zeros(3)\n    b[0] = W\n    b.sort()\n    return b\n') == []
    # (8) View and staging on a synthetic asset: M1 rebuilt through the View equals fm1's M1; nothing after i is reachable
    tmp = tempfile.mkdtemp(prefix='fm3_selftest_')
    path = os.path.join(tmp, 'm1view.py'); open(path, 'w').write(GOOD_SRC)
    mod = load_challenger(path)
    n = 3200
    days = [(datetime.date(1990, 1, 1) + datetime.timedelta(days=k)).isoformat() for k in range(n)]
    c = 100 * np.exp(np.cumsum(0.0003 + 0.012 * rng.standard_normal(n)))
    rv = 4 + np.cumsum(rng.standard_normal(n)) * 0.02
    S = fm2.build_series(days, c, days, rv, days, rv * 0 + 3.0, 0)
    Ra = fm2.expert_rows(S, learn_start='1990-01-01', min_rows=1260, horizons=[20, 60])
    A = arrays_of(S, {'E': align(days, days[::7], np.arange(len(days[::7]), dtype=float), 0)})
    Qc = challenger_rows(mod, A, Ra['start'], Ra['h'])
    assert np.isfinite(Qc).all() and np.allclose(Qc, Ra['Q'][:, 2], rtol=1e-6, atol=1e-9)        # expert index 2 = M1
    Qw = challenger_rows(mod, A, Ra['start'], Ra['h'], awake_from=days[2500])
    assert np.isnan(Qw[Ra['start'] < fm2.ordinal(days[2500])]).all() and eq(Qw[Ra['start'] >= fm2.ordinal(days[2500])], Qc[Ra['start'] >= fm2.ordinal(days[2500])])
    V = View(A, 2000)
    assert len(V.lc) == len(V.c) == len(V.r) == len(V.s252) == len(V.x('E')) == 2001 and V.f.shape == (6, 2001) and V.day == days[2000]
    assert len(V.yh(20)) == 1981 and abs(V.yh(20)[-1] - (S.lc[2000] - S.lc[1980])) < 1e-12 and len(V.vh(20)) == 2001
    assert eq(V.vh(60), S.vh(60, fm1.LAM)[:2001]) and eq(V.vh(20, 0.9), S.vh(20, 0.9)[:2001]) and eq(V.f, S.f[:, :2001])
    # a View holds private copies cut at the start day: no array reaches the full series, none can be written
    held = [v for v in vars(V).values() if isinstance(v, np.ndarray)] + list(V.x.__self__._x.values())
    assert len(held) == 11 and all(a.base is None and not a.flags.writeable and a.shape[-1] in (2001, fm2.QN) for a in held)
    assert not any(isinstance(v, (fm1.Series, dict)) and v is not V._x for v in vars(V).values())
    try:
        V.lc[0] = 1.0; raise AssertionError('View arrays must be read-only')
    except ValueError:
        pass
    # align: lag 0 takes the same day, lag 1 never does, an old value is missing
    a0 = align(['2020-01-03', '2020-01-20'], ['2020-01-02', '2020-01-03'], np.array([1.0, 2.0]), 0)
    a1 = align(['2020-01-03', '2020-01-20'], ['2020-01-02', '2020-01-03'], np.array([1.0, 2.0]), 1)
    assert a0[0] == 2.0 and a1[0] == 1.0 and np.isnan(a0[1]) and np.isnan(a1[1])
    assert eq(align(days, days[::7], np.arange(len(days[::7]), dtype=float), 0), fm2.lag_fill(days, days[::7], np.arange(len(days[::7]), dtype=float), 0))
    try:
        check_q(np.r_[1.0, np.zeros(fm2.QN - 1)]); raise AssertionError('descending quantiles must be refused')
    except ValueError:
        pass
    # EXTRA_LAG: 0 reads the same day (US-listed asset), 1 reads strictly before; a non-US asset is always strictly before
    def yj(path, dd, vv):
        ts = [int(datetime.datetime.fromisoformat(x + 'T12:00:00+00:00').timestamp()) for x in dd]
        json.dump({'chart': {'result': [{'timestamp': ts, 'indicators': {'quote': [{'close': [float(z) for z in vv]}]}}]}}, open(path, 'w'))
    dirs = [os.path.join(tmp, sub) for sub in ('pool', 'rates', 'extra')]
    for dd in dirs:
        os.makedirs(dd)
    yj(os.path.join(dirs[0], 'AAA.json'), days, c); yj(os.path.join(dirs[1], '_TNX.json'), days, rv)
    yj(os.path.join(dirs[1], '_IRX.json'), days, rv * 0 + 3.0); yj(os.path.join(dirs[2], '_E.json'), days, np.arange(n) + 1.0)
    for xl in (0, 1, 2):
        pth = os.path.join(tmp, 'lag%d.py' % xl)
        open(pth, 'w').write("ID = 'lag%d'\nEXTRAS = {'E': '_E'}\nEXTRA_LAG = %d\n\n\ndef quantiles(V, h):\n    return None\n" % (xl, xl))
        if xl == 2:
            try:
                load_challenger(pth); raise AssertionError('EXTRA_LAG 2 must be refused')
            except ValueError:
                pass
            open(pth, 'w').write("ID = 'ax'\n\n\ndef asset_extras(stem, load_json):\n    return {}\n\n\ndef quantiles(V, h):\n    return None\n")
            try:
                load_challenger(pth); raise AssertionError('asset_extras must be refused')
            except ValueError:
                continue
        ml = load_challenger(pth)
        Al = asset_context(ml, 'AAA', 0, dirs[0], dirs[1], dirs[2], days[-1])
        assert Al['x']['E'][2000] == 2001.0 - xl and View(Al, 2000).x('E')[-1] == 2001.0 - xl
        assert asset_context(ml, 'AAA', 1, dirs[0], dirs[1], dirs[2], days[-1])['x']['E'][2000] == 2000.0
    # staging: the rows that can be issued are computed from inputs that end at their own start day. A causal challenger
    # gives the same values either way; one whose derive() uses the whole file (here: its mean) is caught.
    cache = os.path.join(tmp, 'cache'); os.makedirs(cache)
    np.savez(os.path.join(cache, 'AAA.npz'), start=Ra['start'], h=Ra['h'])
    for name, body, n_bad in (('causal', '    return raw\n', 0), ('ahead', "    d, v = raw['E']\n    return {'E': (d, v / np.mean(v))}\n", 1)):
        pth = os.path.join(tmp, name + '.py')
        open(pth, 'w').write("import math\nimport numpy as np\nID = '%s'\nEXTRAS = {'E': '_E'}\n\n\ndef derive(raw):\n%s\n\ndef quantiles(V, h):\n"
                             "    return V.ZQ * V.s252[V.i] * math.sqrt(h) * (1.0 + V.x('E')[V.i])\n" % (name, body))
        out = os.path.join(tmp, 'out_' + name); os.makedirs(out)
        cut_from = days[n - 40]
        info = _stage_one((pth, 'AAA', 0, dirs[0], dirs[1], dirs[2], days[-1], cache, out, None, cut_from))
        n_rows = int(((Ra['start'] >= fm2.ordinal(cut_from)) & (fm2.ordinal(days[-1]) - Ra['start'] <= ISSUE_MAX_DAYS)).sum())
        assert info['cut_rows'] == n_rows > 0 and (info['cut_diff'] > 0) == bool(n_bad), info
        if not n_bad:
            assert eq(np.load(os.path.join(out, 'AAA.npz'))['Qc'], challenger_rows(load_challenger(pth), asset_context(load_challenger(pth), 'AAA', 0, dirs[0], dirs[1], dirs[2], days[-1]), Ra['start'], Ra['h']))
    assert same_rows(np.array([[1.0, 2.0], [np.nan, np.nan], [1.0, 2.0]]), np.array([[1.0, 2.0], [1.0, 2.0], [1.0, 2.1]]), (1e-9, 0.0)) == 2
    # the issued forecasts: rows that are in the books but not in today's grid are counted as orphans
    fz_dir = os.path.join(tmp, 'fz'); os.makedirs(fz_dir)
    st0 = fm2.ordinal(FORWARD_START) + 7 * np.arange(4); stem0 = fm2.UNIVERSE[0][0]
    np.savez(os.path.join(fz_dir, stem0 + '.npz'), start=st0, h=np.full(4, 20), Qc=np.tile(fm2.ZQ, (4, 1)).astype(np.float32))
    old_rows = {stem0: {(int(st0[0]), 20): fm2.ZQ.astype(np.float32) * 2, (int(st0[0]) - 1, 20): fm2.ZQ.astype(np.float32)}}
    fz = freeze(fz_dir, old_rows, FORWARD_START, str(datetime.date.fromordinal(int(st0[-1]))), os.path.join(tmp, 'iss', 'a_001.npz'))
    assert (fz['rows'], fz['kept'], fz['changed'], fz['new'], fz['late'], fz['orphans']) == (4, 1, 1, 3, 1, 1), fz
    got = np.load(os.path.join(fz_dir, stem0 + '.npz'))['Qc']
    assert eq(got[0], fm2.ZQ.astype(np.float32) * 2) and np.isnan(got[1]).all() and eq(got[3], fm2.ZQ.astype(np.float32))
    # the same grid staged again: the late row was issued as "no forecast" and stays so; that is not a changed forecast
    np.savez(os.path.join(fz_dir, stem0 + '.npz'), start=st0, h=np.full(4, 20), Qc=np.tile(fm2.ZQ, (4, 1)).astype(np.float32))
    fz2 = freeze(fz_dir, load_issued([fz['file']]), FORWARD_START, str(datetime.date.fromordinal(int(st0[-1]))), os.path.join(tmp, 'iss', 'a_002.npz'))
    assert (fz2['rows'], fz2['kept'], fz2['changed'], fz2['none_kept'], fz2['new'], fz2['file']) == (4, 3, 0, 1, 1, os.path.join(tmp, 'iss', 'a_002.npz')), fz2
    assert np.isnan(np.load(os.path.join(fz_dir, stem0 + '.npz'))['Qc'][1]).all()
    # (9) the static check leaves no way from numpy or math to another module (two attribute steps deep)
    import types, warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        for top in (np, math):
            for a in dir(top):
                if a.startswith('_') or a in BAD_ATTRS:
                    continue
                v = getattr(top, a)
                assert not isinstance(v, types.ModuleType), 'module reachable: %s.%s' % (top.__name__, a)
                for b in dir(v):
                    if b.startswith('_') or b in BAD_ATTRS:
                        continue
                    try:
                        w = getattr(v, b)
                    except Exception:
                        continue
                    assert not isinstance(w, types.ModuleType), 'module reachable: %s.%s.%s' % (top.__name__, a, b)
    print('selftest OK')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'selftest':
        selftest()
    elif cmd == 'admit':
        opt = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
        pos = [a for k, a in enumerate(sys.argv[2:]) if not a.startswith('--') and not sys.argv[k + 1].startswith('--')]
        rep = admit(*pos[:5], cache=opt('--cache'), jobs=int(opt('--jobs') or 1))
        if len(pos) > 5:
            json.dump(rep, open(pos[5], 'w'), indent=1)
        print(json.dumps(rep, indent=1))
        sys.exit(0 if rep['pass'] else 1)
    elif cmd == 'admit-pass':
        admit_pass(*sys.argv[2:9])
    elif cmd == 'stage':
        opt = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
        print(json.dumps(stage(*sys.argv[2:9], awake_from=opt('--from'), jobs=int(opt('--jobs') or 1), cut_from=opt('--cut-from')), indent=1))
