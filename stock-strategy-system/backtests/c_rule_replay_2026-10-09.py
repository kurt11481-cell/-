#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공통 규칙 C 기준값 리플레이 (사전 등록 고정본 구현).

사전 등록: docs/claude/c-rule-replay-preregistration-2026-10-09.md (raw sha256은 같은 이름 .sha256 파일).
권한: 과거 계산만. 주문 도구·정책·상태·규칙 파일·예약 작업을 읽거나 바꾸지 않는다.
모드: --self-test (합성 자료만) / --check-inputs (해시·적재 확인, 신호·수익 계산 없음) / --run (본 계산, 해시 대조 통과 시에만).

해석 I1~I8 (사전 등록 번호 기준, 문서에 없는 빈칸을 코드가 채운 곳은 결과 문서에 보고한다):
 I1  EMA 시드 = 첫 N개 종가 단순평균 (3절). RSI/ATR는 Wilder, 첫 14개 변화·TR 단순평균 시드 (3절).
 I2  RSI에서 평균 하락이 0이면 100, 평균 상승도 0이면 50 (문서에 없음 — 코드 보충).
 I3  신호 판정 t는 index >= 21부터 (C4/C5/C6/C3가 EMA20[t-2], 종가 t-21..t-2를 쓰므로). 그 앞은 미발생.
 I4  상태형 진입 = 거짓→참 (5절), 사건형 5세션 창 = 충족일 포함, 창 안 재충족은 창 재시작 (5절).
 I5  군집 첫 이벤트 = 직전 *원본* 이벤트와 20세션 이상 떨어진 이벤트 (8절 겹침 민감도).
 I6  임계값 제안에서 현행 값과 거리가 같은 후보가 둘 이상이면(동률) 문서에 규정이 없으므로 제안하지 않고 후보를 모두 기록한다.
 I7  거리는 격자 간격 단위(RSI 5, ATR 0.5)로 센다.
 I8  저장소 보조 표시의 C8 임계는 SOXX·NBIS·MVLL 10%, SOXL 20% (MVLL·NBIS 배수 확인 필요).
"""
import argparse, collections, csv, datetime as dt, hashlib, json, math, os, random, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
INP = os.path.join(HERE, 'soxl_signal_inputs_2026-10-01')
DOC = os.path.join(ROOT, 'docs', 'claude', 'c-rule-replay-preregistration-2026-10-09.md')
DOCSHA = DOC[:-3] + '.sha256'
OUT_JSON = os.path.join(HERE, 'c_rule_replay_2026-10-09_results.json')
OUT_CSV = os.path.join(HERE, 'c_rule_replay_2026-10-09_events.csv')
EXPECT = {
    'SOXX': '00e8cdd030c38748eac563fc025222a16b2ada9e4cc09be3f6d7f28e224535f6',
    'QQQ': '644aabe79e8165bc382788f6fbe46b2e25898adc95cfe1cb224c13d03560df5e',
    'SOXL': '56e612b764a7c5df48b1f009efb300badba34dfc1d2cc262946a0d33a7502c24',
    'TQQQ': '816a9ac495fa2a31499e1e2fefb16342572609db5062ca0a6f5970ba5962c63b',
}
EVAL_START = '2011-01-03'
HALF = '2019-01-01'
MIN_HALF, MIN_ALL, THR = 25, 50, 0.30
KINDS = ['C1-', 'C1+', 'C2-', 'C2+', 'C3-', 'C3+', 'C4-', 'C4+', 'C5-', 'C5+', 'C6-', 'C6+', 'C8-', 'C8+']
JUDGED = [k for k in KINDS if not k.startswith('C8')]
STATE = ('C1', 'C3', 'C5')
ASSETS_J = ('SOXX', 'QQQ')
ASSETS_S = ('SOXL', 'TQQQ')
T_BY_ASSET = {'SOXX': 0.10, 'QQQ': 0.10, 'SOXL': 0.20, 'TQQQ': 0.20}
T_REPO = {'SOXX': 0.10, 'SOXL': 0.20, 'NBIS': 0.10, 'MVLL': 0.10}
P0 = dict(rsi_hi=70, rsi_lo=30, band_hi=2.0, band_lo=2.0, c2_hi=2.5, c2_lo=2.5)


def DIR(k):
    return -1 if k.endswith('-') else 1


def sha256_file(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


# ---------------- 지표 (3절) ----------------
def ema(c, N):
    n = len(c)
    e = [None] * n
    if n < N:
        return e
    e[N - 1] = sum(c[:N]) / N
    k = 2.0 / (N + 1)
    for i in range(N, n):
        e[i] = c[i] * k + e[i - 1] * (1 - k)
    return e


def wilder_rsi(c, N=14):
    n = len(c)
    r = [None] * n
    if n <= N:
        return r
    g = [max(c[i] - c[i - 1], 0.0) for i in range(1, n)]
    ls = [max(c[i - 1] - c[i], 0.0) for i in range(1, n)]
    ag = sum(g[:N]) / N
    al = sum(ls[:N]) / N

    def val(ag, al):
        if al == 0:
            return 100.0 if ag > 0 else 50.0
        return 100.0 - 100.0 / (1 + ag / al)
    r[N] = val(ag, al)
    for i in range(N + 1, n):
        ag = (ag * (N - 1) + g[i - 1]) / N
        al = (al * (N - 1) + ls[i - 1]) / N
        r[i] = val(ag, al)
    return r


def wilder_atr(h, l, c, N=14):
    n = len(c)
    a = [None] * n
    if n <= N:
        return a
    tr = [None] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, n)]
    a[N] = sum(tr[1:N + 1]) / N
    for i in range(N + 1, n):
        a[i] = (a[i - 1] * (N - 1) + tr[i]) / N
    return a


def sigma60(c):
    n = len(c)
    s = [None] * n
    ret = [None] + [c[i] / c[i - 1] - 1 for i in range(1, n)]
    for t in range(60, n):
        s[t] = st.stdev(ret[t - 59:t + 1])
    return s


def build(d, h, l, c, v, T, bad=()):
    n = len(c)
    A = dict(d=d, h=h, l=l, c=c, v=v, T=T, bad=set(bad), n=n)
    A['ema20'] = ema(c, 20)
    A['ema10'] = ema(c, 10)
    A['atr'] = wilder_atr(h, l, c, 14)
    A['rsi'] = wilder_rsi(c, 14)
    A['sig60'] = sigma60(c)
    A['v20'] = [None] * n
    for t in range(20, n):
        A['v20'][t] = sum(v[t - 20:t]) / 20.0
    return A


# ---------------- 신호 (4절) ----------------
def sig_at(t, A, P=P0, only=None):
    ks = only or KINDS
    if t < 21:
        return {k: False for k in ks}
    c, h, l, v = A['c'], A['h'], A['l'], A['v']
    e20, e10, atr, rsi, v20 = A['ema20'], A['ema10'], A['atr'], A['rsi'], A['v20']
    out = {}
    b, a = e20[t - 1], atr[t - 1]
    for k in ks:
        if k == 'C1-':
            x = rsi[t] >= P['rsi_hi'] or c[t] >= b + P['band_hi'] * a
        elif k == 'C1+':
            x = rsi[t] <= P['rsi_lo'] or c[t] <= b - P['band_lo'] * a
        elif k in ('C2-', 'C2+'):
            rng = h[t] - l[t]
            cp = 0.5 if rng == 0 else (c[t] - l[t]) / rng
            vok = (t not in A['bad']) and v[t] >= 1.2 * v20[t]
            if k == 'C2-':
                x = h[t] >= b + P['c2_hi'] * a and cp <= 0.35 and vok
            else:
                x = l[t] <= b - P['c2_lo'] * a and cp >= 0.65 and vok
        elif k == 'C3-':
            x = c[t] < e20[t] and c[t - 1] < e20[t - 1] and c[t - 2] >= e20[t - 2]
        elif k == 'C3+':
            x = c[t] > e20[t] and c[t - 1] > e20[t - 1] and c[t - 2] <= e20[t - 2]
        elif k in ('C4-', 'C4+', 'C5-', 'C5+'):
            win = c[t - 21:t - 1]  # t-21..t-2
            hi, lo = max(win), min(win)
            if k == 'C4-':
                x = c[t - 1] > hi and c[t] < hi
            elif k == 'C4+':
                x = c[t - 1] < lo and c[t] > lo
            elif k == 'C5-':
                x = c[t - 1] < lo and c[t - 1] < e10[t - 1] and c[t] < lo and c[t] < e10[t]
            else:
                x = c[t - 1] > hi and c[t - 1] > e10[t - 1] and c[t] > hi and c[t] > e10[t]
        elif k == 'C6-':
            x = (c[t - 2] < e20[t - 2] and c[t - 1] > c[t - 2] and e20[t - 1] * 0.985 <= c[t - 1] < e20[t - 1]
                 and c[t] < c[t - 1] and c[t] < e20[t])
        elif k == 'C6+':
            x = (c[t - 2] > e20[t - 2] and c[t - 1] < c[t - 2] and e20[t - 1] < c[t - 1] <= e20[t - 1] * 1.015
                 and c[t] > c[t - 1] and c[t] > e20[t])
        elif k == 'C8-':
            x = c[t] / c[t - 1] - 1 <= -A['T']
        elif k == 'C8+':
            x = c[t] / c[t - 1] - 1 >= A['T']
        else:
            raise KeyError(k)
        out[k] = bool(x)
    return out


def flags(A, P=P0, kinds=None):
    ks = kinds or KINDS
    fl = {k: [False] * A['n'] for k in ks}
    for t in range(A['n']):
        s = sig_at(t, A, P, ks)
        for k in ks:
            fl[k][t] = s[k]
    return fl


# ---------------- 이벤트 (5절) ----------------
def extract(kind, fl):
    out = []
    if kind[:2] in STATE:
        prev = False
        for t, x in enumerate(fl):
            if x and not prev:
                out.append(t)
            prev = x
    else:
        last = None
        for t, x in enumerate(fl):
            if x:
                if last is None or t - last >= 5:
                    out.append(t)
                last = t
    return out


def cluster_first(ev_all):
    return [e for i, e in enumerate(ev_all) if i == 0 or e - ev_all[i - 1] >= 20]


def active_mask(kind, fl, A):
    n = A['n']
    m = [False] * n
    if kind[:2] in ('C1', 'C5'):
        return list(fl)
    if kind[:2] == 'C3':
        ev = set(extract(kind, fl))
        for t in range(n):
            if t in ev:
                m[t] = True
            elif t > 0 and m[t - 1] and A['ema20'][t] is not None:
                m[t] = A['c'][t] < A['ema20'][t] if kind.endswith('-') else A['c'][t] > A['ema20'][t]
        return m
    last = None
    for t in range(n):
        if fl[t]:
            last = t
        m[t] = last is not None and t - last <= 4
    return m


# ---------------- 결과 측정 (6절) ----------------
def outcomes(A):
    n, c, l, d, sg = A['n'], A['c'], A['l'], A['d'], A['sig60']
    O = {'z': {}, 'r20': {}, 'r5': {}, 'mae': {}, 'zalt': {}}
    for t in range(n):
        if d[t] < EVAL_START or sg[t] is None or t + 21 >= n:
            continue
        p0 = c[t + 1]
        s = sg[t] * math.sqrt(20)
        r20 = c[t + 21] / p0 - 1
        O['r20'][t] = r20
        O['z'][t] = r20 / s
        O['r5'][t] = c[t + 6] / p0 - 1
        O['mae'][t] = min(l[t + 2:t + 22]) / p0 - 1
        O['zalt'][t] = (c[t + 20] / c[t] - 1) / s
    return O


def in_cell(date, cell):
    return cell == 'all' or (cell == 'H1' and date < HALF) or (cell == 'H2' and date >= HALF)


def cell_stats(A, O, evs, key='z'):
    res = {}
    for cell in ('all', 'H1', 'H2'):
        base = [O[key][t] for t in O[key] if in_cell(A['d'][t], cell)]
        ez = [O[key][t] for t in evs if t in O[key] and in_cell(A['d'][t], cell)]
        mb = st.median(base) if base else None
        me = st.median(ez) if ez else None
        res[cell] = {'N': len(ez), 'N_base': len(base), 'med_event': me, 'med_base': mb,
                     'dz': (me - mb) if (me is not None and mb is not None) else None}
    return res


def quant(a, p):
    if not a:
        return None
    s = sorted(a)
    pos = p * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def quants(a):
    return {'n': len(a), 'p25': quant(a, .25), 'p50': quant(a, .5), 'p75': quant(a, .75)}


# ---------------- 판정 (7절) ----------------
def verdict(cells, direction):
    """cells: [(kind 'all'|'half', N, dz)] 6칸. 순서: 보류 -> 지지 -> 반대 -> 미지지."""
    for kd, N, dz in cells:
        if N < (MIN_ALL if kd == 'all' else MIN_HALF):
            return '보류'
    if all(dz * direction > 0 for _, _, dz in cells) and all(dz * direction >= THR for kd, _, dz in cells if kd == 'all'):
        return '지지'
    if all(dz * direction < 0 for _, _, dz in cells) and all(-dz * direction >= THR for kd, _, dz in cells if kd == 'all'):
        return '반대'
    return '미지지'


def label(v, vc):
    if v in ('지지', '반대'):
        if vc == v:
            return v
        if vc == '보류':
            return v + '(군집 표본 부족)'
        return v + '(약)'
    return v


def eval_kind(kind, AS, OS, P=P0):
    dirn = DIR(kind)
    out = {'assets': {}}
    main_c, clu_c = [], []
    for s in ASSETS_J:
        A, O = AS[s], OS[s]
        fl = flags(A, P, [kind])[kind]
        ev_all = extract(kind, fl)
        ev = [t for t in ev_all if t in O['z']]
        evc = [t for t in cluster_first(ev_all) if t in O['z']]
        cs, cc = cell_stats(A, O, ev), cell_stats(A, O, evc)
        out['assets'][s] = {'cells': cs, 'cluster_cells': cc, 'events': ev, 'events_cluster': evc,
                            'cells_alt_p0': cell_stats(A, O, ev, 'zalt')}
        for cell in ('all', 'H1', 'H2'):
            kd = 'all' if cell == 'all' else 'half'
            main_c.append((kd, cs[cell]['N'], cs[cell]['dz']))
            clu_c.append((kd, cc[cell]['N'], cc[cell]['dz']))
    v, vc = verdict(main_c, dirn), verdict(clu_c, dirn)
    out.update(verdict=v, cluster_verdict=vc, label=label(v, vc))
    return out


def variants(kind):
    """(라벨, P, 축, 값, 현행값, 간격). 현행 값 자체도 포함(값==현행값)."""
    out = []
    if kind == 'C1-':
        for v in (65, 70, 75):
            out.append(('RSI>=%d' % v, dict(P0, rsi_hi=v), 'rsi', v, 70, 5))
        for b in (1.5, 2.0, 2.5):
            out.append(('밴드 %.1fATR' % b, dict(P0, band_hi=b), 'band', b, 2.0, 0.5))
    elif kind == 'C1+':
        for v in (25, 30, 35):
            out.append(('RSI<=%d' % v, dict(P0, rsi_lo=v), 'rsi', v, 30, 5))
        for b in (1.5, 2.0, 2.5):
            out.append(('밴드 %.1fATR' % b, dict(P0, band_lo=b), 'band', b, 2.0, 0.5))
    elif kind == 'C2-':
        for b in (2.0, 2.5, 3.0):
            out.append(('C2 밴드 %.1fATR' % b, dict(P0, c2_hi=b), 'c2band', b, 2.5, 0.5))
    elif kind == 'C2+':
        for b in (2.0, 2.5, 3.0):
            out.append(('C2 밴드 %.1fATR' % b, dict(P0, c2_lo=b), 'c2band', b, 2.5, 0.5))
    return out


def proposal(kind, cur, AS, OS):
    if cur['verdict'] not in ('미지지', '반대'):
        return {'status': '해당 없음(현행 판정 %s)' % cur['verdict']}
    vs = variants(kind)
    if not vs:
        return {'status': '격자 없음'}
    rows = []
    for lab, P, axis, val, curv, step in vs:
        if val == curv:
            continue
        r = eval_kind(kind, AS, OS, P)
        rows.append({'label': lab, 'axis': axis, 'value': val, 'steps': abs(val - curv) / step,
                     'verdict': r['verdict'], 'cluster_verdict': r['cluster_verdict'],
                     'ok': r['verdict'] == '지지' and r['cluster_verdict'] == '지지'})
    ok = [r for r in rows if r['ok']]
    if not ok:
        return {'status': '제안 없음', 'rows': rows}
    m = min(r['steps'] for r in ok)
    near = [r for r in ok if r['steps'] == m]
    if len(near) == 1:
        return {'status': '제안: ' + near[0]['label'], 'rows': rows}
    return {'status': '동률 — 문서에 동률 규정 없음, 제안 보류(I6)', 'candidates': [r['label'] for r in near], 'rows': rows}


# ---------------- 파이프라인 ----------------
def run_pipeline(datasets, aux=None):
    """datasets: sym -> dict(d,h,l,c,v,bad). 반환: results dict, events rows."""
    AS, OS, FL = {}, {}, {}
    for s, ds in datasets.items():
        AS[s] = build(ds['d'], ds['h'], ds['l'], ds['c'], ds['v'], T_BY_ASSET[s], ds.get('bad', ()))
        OS[s] = outcomes(AS[s])
        FL[s] = flags(AS[s])
    R = {'kinds': {}, 'assets': {}, 'c8': {}, 'activity': {}, 'cooccurrence': {}, 'baseline': {}}
    rows = []
    for s in datasets:
        A, O = AS[s], OS[s]
        R['baseline'][s] = {k: quants(list(O[k].values())) for k in ('z', 'r20', 'r5', 'mae')}
        R['assets'][s] = {'rows': A['n'], 'first': A['d'][0], 'last': A['d'][-1], 'eval_days': len(O['z'])}
    for kind in JUDGED:
        cur = eval_kind(kind, AS, OS)
        cur['proposal'] = proposal(kind, cur, AS, OS)
        cur['sensitivity_3x'] = {}
        for s in ASSETS_S:
            if s in AS:
                ev_all = extract(kind, FL[s][kind])
                ev = [t for t in ev_all if t in OS[s]['z']]
                cur['sensitivity_3x'][s] = {'cells': cell_stats(AS[s], OS[s], ev),
                                            'cells_alt_p0': cell_stats(AS[s], OS[s], ev, 'zalt'), 'N': len(ev)}
        cur['dist'] = {}
        for s in datasets:
            A, O = AS[s], OS[s]
            ev = [t for t in extract(kind, FL[s][kind]) if t in O['z']]
            cur['dist'][s] = {k: quants([O[k][t] for t in ev]) for k in ('z', 'r20', 'r5', 'mae')}
            by_year = collections.Counter(int(A['d'][t][:4]) for t in ev)
            m = active_mask(kind, FL[s][kind], A)
            days = [t for t in range(A['n']) if t in O['z']]
            runs, run = [], 0
            for t in days:
                if m[t]:
                    run += 1
                elif run:
                    runs.append(run)
                    run = 0
            if run:
                runs.append(run)
            R['activity'].setdefault(kind, {})[s] = {
                'events': len(ev), 'per100': 100.0 * len(ev) / max(1, len(days)),
                'active_ratio': sum(1 for t in days if m[t]) / max(1, len(days)),
                'median_run': st.median(runs) if runs else None, 'by_year': dict(sorted(by_year.items()))}
            for t in ev:
                rows.append([s, kind, A['d'][t], t, O['z'][t], O['r20'][t], O['r5'][t], O['mae'][t]])
        R['kinds'][kind] = cur
    for kind in ('C8-', 'C8+'):
        R['c8'][kind] = {}
        for s in datasets:
            A = AS[s]
            ev = [t for t in extract(kind, FL[s][kind]) if A['d'][t] >= EVAL_START]
            R['c8'][kind][s] = {'n': len(ev), 'dates': [A['d'][t] for t in ev]}
    for s in datasets:
        A, O = AS[s], OS[s]
        for sign in ('-', '+'):
            cnt = collections.defaultdict(set)
            for k in JUDGED:
                if k.endswith(sign):
                    for t in extract(k, FL[s][k]):
                        if t in O['z']:
                            cnt[t].add(k)
            multi = [t for t, ks in cnt.items() if len(ks) >= 2]
            R['cooccurrence'].setdefault(s, {})[sign] = {
                'days': len(multi), 'median_z20': st.median([O['z'][t] for t in multi]) if multi else None}
    if aux:
        R['aux_repo'] = aux(AS, FL)
    return R, rows


# ---------------- 적재 ----------------
def load_external(sym):
    path = os.path.join(INP, '%s_combined.csv' % sym)
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    d, h, l, c, v = [], [], [], [], []
    for r in rows:
        f = float(r['adjclose']) / float(r['close'])
        d.append(r['date'])
        h.append(float(r['high']) * f)
        l.append(float(r['low']) * f)
        c.append(float(r['close']) * f)
        v.append(float(r['volume']))
    src = json.load(open(os.path.join(INP, 'soxl_signal_inputs_sources.json'), encoding='utf-8'))
    bad = set()
    for sd in src['symbols'].get(sym, {}).get('splits', {}):
        if sd in d:
            i = d.index(sd)
            bad.update(range(i, min(len(d), i + 20)))
    return dict(d=d, h=h, l=l, c=c, v=v, bad=bad)


def load_repo(sym):
    base = os.path.join(ROOT, 'workspace', 'outputs', 'regular-session-closes')
    hist = json.load(open(os.path.join(base, 'history', '%s.close-history.json' % sym), encoding='utf-8'))
    sessions = [r['session_date'] for r in hist['sessions']]
    hclose = {r['session_date']: float(r['close']) for r in hist['sessions']}
    bars = {}
    pdir = os.path.join(base, 'pages', sym)
    for f in sorted(os.listdir(pdir)):
        for b in json.load(open(os.path.join(pdir, f), encoding='utf-8'))['result_list']:
            bars[b['cntr_tm']] = b
    by = collections.defaultdict(list)
    for t, b in bars.items():
        if '0930' <= t[8:12] <= '1530':
            by[t[:4] + '-' + t[4:6] + '-' + t[6:8]].append((t, b))
    d, h, l, c, v, mism = [], [], [], [], [], 0
    for s in sessions:
        bs = [b for _, b in sorted(by[s], key=lambda x: x[0])]
        d.append(s)
        h.append(max(float(b['high_pric']) for b in bs))
        l.append(min(float(b['low_pric']) for b in bs))
        c.append(float(bs[-1]['cur_prc']))
        v.append(float(sum(int(b['trde_qty']) for b in bs)))
        if abs(c[-1] - hclose[s]) > 1e-9:
            mism += 1
    bad = set()
    if sym == 'MVLL':
        ca = json.load(open(os.path.join(base, 'corporate-actions.json'), encoding='utf-8'))
        for a in ca['actions']:
            if a['symbol'] == 'MVLL' and a['action_type'] == 'SPLIT':
                ratio = a['new_shares'] / a['old_shares']
                i = d.index(a['effective_session'])
                for j in range(i):
                    h[j] /= ratio
                    l[j] /= ratio
                    c[j] /= ratio
                    v[j] *= ratio
                bad.update(range(i, min(len(d), i + 20)))
    return dict(d=d, h=h, l=l, c=c, v=v, bad=bad, close_mismatch=mism, bars=len(bars))


def aux_repo_from(rdata, AS, FL):
    """보조 표시(판정 아님): 저장소 종목의 같은 코드 이벤트와 이후 수익, 외부 일봉과의 일치율."""
    out = {}
    for sym, ds in rdata.items():
        A = build(ds['d'], ds['h'], ds['l'], ds['c'], ds['v'], T_REPO[sym], ds.get('bad', ()))
        fl = flags(A)
        o = {'sessions': A['n'], 'events': {}, 'agreement': {}}
        for k in KINDS:
            evs = []
            for t in extract(k, fl[k]):
                if t < 21:
                    continue
                evs.append({'date': A['d'][t],
                            'r5': (A['c'][t + 6] / A['c'][t + 1] - 1) if t + 6 < A['n'] else None,
                            'r20': (A['c'][t + 21] / A['c'][t + 1] - 1) if t + 21 < A['n'] else None})
            o['events'][k] = evs
        if sym in AS:
            idx = {d: i for i, d in enumerate(AS[sym]['d'])}
            for k in KINDS:
                nc = ag = both = ro = eo = 0
                for t in range(21, A['n']):
                    te = idx.get(A['d'][t])
                    if te is None:
                        continue
                    nc += 1
                    a, b = fl[k][t], FL[sym][k][te]
                    ag += (a == b)
                    both += (a and b)
                    ro += (a and not b)
                    eo += (b and not a)
                o['agreement'][k] = {'common_days': nc, 'agree': ag, 'both_true': both, 'repo_only': ro, 'ext_only': eo}
        out[sym] = o
    return out


def hash_checks():
    res = {'inputs': {}, 'doc': {}}
    ok = True
    for s, h in EXPECT.items():
        a = sha256_file(os.path.join(INP, '%s_combined.csv' % s))
        res['inputs'][s] = (a == h)
        ok = ok and a == h
    raw = open(DOC, 'rb').read()
    kv = dict(line.split('=', 1) for line in open(DOCSHA, encoding='utf-8').read().splitlines() if '=' in line and not line.startswith('fixed_at'))
    rawh = hashlib.sha256(raw).hexdigest()
    lfh = hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()
    res['doc'] = {'raw': rawh == kv.get('raw_bytes_sha256'), 'lf': lfh == kv.get('lf_normalized_sha256')}
    ok = ok and all(res['doc'].values())
    return ok, res


# ---------------- 자체 시험 (10절) ----------------
def _mk(n=40):
    c = [100.0] * n
    return dict(d=['2020-01-%02d' % (i + 1) if i < 28 else '2020-02-%02d' % (i - 27) for i in range(n)],
                h=[101.0] * n, l=[99.0] * n, c=c, v=[1e6] * n, T=0.10, bad=set(), n=n,
                ema20=[100.0] * n, ema10=[100.0] * n, atr=[1.0] * n, rsi=[50.0] * n, v20=[1e6] * n)


def _approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


def self_test():
    tests = []

    def T(f):
        tests.append(f)
        return f

    @T
    def ema_seed_recursion():
        c = [float(i) for i in range(1, 31)]
        e = ema(c, 20)
        assert e[18] is None and _approx(e[19], 10.5) and _approx(e[20], 11.5)

    @T
    def rsi_wilder():
        c = [10.0 + (i % 2) for i in range(30)]
        r = wilder_rsi(c)
        assert r[13] is None and _approx(r[14], 50.0)
        assert abs(r[15] - 53.571428571) < 1e-6
        assert _approx(wilder_rsi([float(i) for i in range(1, 30)])[14], 100.0)

    @T
    def atr_wilder_and_gap():
        n = 25
        c = [10.0] * n
        h = [11.0] * n
        l = [9.0] * n
        c[15], h[15], l[15] = 19.0, 20.0, 18.0
        a = wilder_atr(h, l, c)
        assert a[13] is None and _approx(a[14], 2.0)
        assert abs(a[15] - (2.0 * 13 + 10.0) / 14) < 1e-12

    @T
    def sigma_is_sample_std():
        c = [100.0]
        for i in range(1, 61):
            c.append(c[-1] * (1.01 if i % 2 else 0.99))
        s = sigma60(c)[60]
        rets = [c[i] / c[i - 1] - 1 for i in range(1, 61)]
        assert abs(s - st.stdev(rets)) < 1e-15
        assert abs(s / (0.01 * math.sqrt(60 / 59))) - 1 < 5e-3

    @T
    def band_uses_t_minus_1():
        A = _mk()
        t = 25
        A['ema20'][t - 1], A['atr'][t - 1] = 100.0, 5.0
        A['ema20'][t], A['atr'][t] = 130.0, 50.0   # 당일 값이 기준을 끌고 가면 안 된다
        A['c'][t] = 110.0
        assert sig_at(t, A)['C1-'] is True
        A['c'][t] = 109.9
        assert sig_at(t, A)['C1-'] is False
        A['c'][t] = 90.0
        assert sig_at(t, A)['C1+'] is True
        A['c'][t] = 100.0
        A['rsi'][t] = 70.0
        assert sig_at(t, A)['C1-'] is True
        A['rsi'][t] = 30.0
        assert sig_at(t, A)['C1+'] is True

    @T
    def c2_conditions_and_split():
        A = _mk()
        t = 25
        A['ema20'][t - 1], A['atr'][t - 1] = 100.0, 5.0
        A['h'][t], A['l'][t], A['c'][t] = 113.0, 100.0, 104.0
        A['v'][t], A['v20'][t] = 130.0, 100.0
        assert sig_at(t, A)['C2-'] is True
        A['v'][t] = 119.0
        assert sig_at(t, A)['C2-'] is False
        A['v'][t] = 130.0
        A['bad'] = {t}
        assert sig_at(t, A)['C2-'] is False       # 분할 20세션 보수 처리
        A['bad'] = set()
        A['c'][t] = 108.0                         # 종가 위치 0.615 > 0.35
        assert sig_at(t, A)['C2-'] is False
        A['h'][t], A['l'][t], A['c'][t] = 100.0, 87.0, 96.0   # +쪽: 저가 <= 100-12.5=87.5, 위치 0.69
        assert sig_at(t, A)['C2+'] is True

    @T
    def c3_equality_and_direction():
        A = _mk()
        t = 25
        A['c'][t - 2], A['c'][t - 1], A['c'][t] = 100.0, 99.0, 98.0   # 앞 종가 == EMA20 은 '위'(>=)로 인정
        assert sig_at(t, A)['C3-'] is True
        A['c'][t - 2] = 99.0
        assert sig_at(t, A)['C3-'] is False
        A['c'][t - 2], A['c'][t - 1], A['c'][t] = 100.0, 101.0, 102.0
        assert sig_at(t, A)['C3+'] is True
        A['c'][t - 2] = 101.0
        assert sig_at(t, A)['C3+'] is False

    @T
    def c4_c5_lines_and_second_day():
        A = _mk()
        t = 25
        A['c'][t - 1], A['c'][t] = 105.0, 99.0
        assert sig_at(t, A)['C4-'] is True
        A['c'][t - 1] = 100.0
        assert sig_at(t, A)['C4-'] is False
        A = _mk()
        A['c'][t - 1], A['c'][t] = 90.0, 89.0
        A['ema10'][t - 1], A['ema10'][t] = 95.0, 94.0
        assert sig_at(t, A)['C5-'] is True
        A['c'][t] = 101.0
        assert sig_at(t, A)['C5-'] is False
        A['c'][t] = 89.0
        A['c'][t - 2] = 80.0      # t-2는 선 창(t-21..t-2)에 포함 -> 선 80, c[t-1]=90은 선 위
        assert sig_at(t, A)['C5-'] is False
        A = _mk()
        A['c'][t - 1], A['c'][t] = 110.0, 111.0
        A['ema10'][t - 1], A['ema10'][t] = 105.0, 106.0
        assert sig_at(t, A)['C5+'] is True
        A['c'][t - 1] = 100.0   # 선 == 종가는 돌파 아님
        assert sig_at(t, A)['C5+'] is False

    @T
    def c6_bounce_and_pullback():
        A = _mk()
        t = 25
        A['c'][t - 2], A['c'][t - 1], A['c'][t] = 97.0, 98.6, 98.0
        assert sig_at(t, A)['C6-'] is True
        A['c'][t - 1] = 96.5          # 반등 아님
        assert sig_at(t, A)['C6-'] is False
        A['c'][t - 1] = 97.5          # 반등이지만 1.5% 밖
        assert sig_at(t, A)['C6-'] is False
        A = _mk()
        A['c'][t - 2], A['c'][t - 1], A['c'][t] = 103.0, 101.4, 102.0
        assert sig_at(t, A)['C6+'] is True
        A['c'][t - 1] = 103.5         # 눌림 아님
        assert sig_at(t, A)['C6+'] is False

    @T
    def c8_threshold():
        A = _mk()
        t = 25
        A['c'][t - 1], A['c'][t] = 100.0, 89.9
        assert sig_at(t, A)['C8-'] is True and sig_at(t, A)['C8+'] is False
        A['c'][t] = 110.1
        assert sig_at(t, A)['C8+'] is True

    @T
    def events_state_and_window():
        fl = [False, True, True, False, True]
        assert extract('C1-', fl) == [1, 4]
        fl = [False] * 15
        for t in (2, 4, 7, 12):
            fl[t] = True
        assert extract('C2-', fl) == [2, 12]      # 4는 창 안(재시작), 7은 4에서 3세션 -> 새 이벤트 아님, 12는 7에서 5세션 -> 새 이벤트

    @T
    def cluster_first_filter():
        assert cluster_first([0, 5, 10, 40, 45, 100]) == [0, 40, 100]

    @T
    def outcome_p0_and_end_exclusion():
        n = 100
        c = [100.0 * 1.01 ** i for i in range(n)]
        d = ['2012-%02d-%02d' % (1 + i // 28 % 12, 1 + i % 28) for i in range(n)]
        d = sorted(d)
        A = build(d, [x * 1.01 for x in c], [x * 0.99 for x in c], c, [1e6] * n, 0.10)
        O = outcomes(A)
        t = 70
        assert t in O['z'] and _approx(O['r20'][t], 1.01 ** 20 - 1, 1e-12)
        assert abs(O['mae'][t] - (1.01 * 0.99 - 1)) < 1e-12
        assert _approx(O['r5'][t], 1.01 ** 5 - 1, 1e-12)
        assert max(O['z']) == n - 22 and (n - 21) not in O['z']       # 창이 자료 끝을 넘는 표본 제외

    @T
    def no_lookahead():
        rnd = random.Random(7)
        n = 320
        c = [100.0]
        for _ in range(n - 1):
            c.append(c[-1] * (1 + rnd.gauss(0, 0.02)))
        h = [x * (1 + abs(rnd.gauss(0, .01))) for x in c]
        l = [x * (1 - abs(rnd.gauss(0, .01))) for x in c]
        v = [1e6 * (1 + rnd.random()) for _ in c]
        d = ['x%04d' % i for i in range(n)]
        full = build(d, h, l, c, v, 0.10)
        ff = {k: [sig_at(t, full)[k] for t in range(n)] for k in KINDS}
        for t in (80, 150, 233, 319):
            pre = build(d[:t + 1], h[:t + 1], l[:t + 1], c[:t + 1], v[:t + 1], 0.10)
            s = sig_at(t, pre)
            for k in KINDS:
                assert s[k] == ff[k][t], (k, t)
            for key in ('ema20', 'ema10', 'atr', 'rsi', 'sig60', 'v20'):
                assert pre[key][t] == full[key][t] or _approx(pre[key][t], full[key][t], 1e-12)

    @T
    def verdict_order_and_ties():
        good = [('all', 60, -0.4), ('half', 30, -0.1), ('half', 30, -0.2)] * 2
        assert verdict(good, -1) == '지지'
        assert verdict(good, +1) == '반대'
        short = list(good)
        short[1] = ('half', 24, -0.1)
        assert verdict(short, -1) == '보류'
        small = [('all', 60, -0.2), ('half', 30, -0.1), ('half', 30, -0.2)] * 2
        assert verdict(small, -1) == '미지지'          # 크기 미달
        zero = [('all', 60, -0.4), ('half', 30, 0.0), ('half', 30, -0.2)] * 2
        assert verdict(zero, -1) == '미지지'           # Δz=0은 어느 방향도 아님
        mixed = [('all', 60, -0.4), ('half', 30, 0.1), ('half', 30, -0.2)] * 2
        assert verdict(mixed, -1) == '미지지'
        assert label('지지', '지지') == '지지' and label('지지', '미지지') == '지지(약)' and label('지지', '보류') == '지지(군집 표본 부족)'
        assert label('반대', '반대') == '반대' and label('미지지', '지지') == '미지지'

    @T
    def cell_baselines_are_per_interval():
        n = 40
        A = dict(d=['2012-01-01'] * 20 + ['2020-01-01'] * 20, n=n)
        O = {'z': {i: (1.0 if i < 20 else 3.0) for i in range(n)}}
        cs = cell_stats(A, O, [0, 1, 30, 31])
        assert cs['H1']['med_base'] == 1.0 and cs['H2']['med_base'] == 3.0 and cs['all']['med_base'] == 2.0
        assert cs['H1']['dz'] == 0.0 and cs['H2']['dz'] == 0.0

    @T
    def activity_c3_run():
        A = _mk(30)
        for t in range(20, 30):
            A['c'][t] = 99.0
        A['c'][22] = 101.0
        fl = [False] * 30
        fl[21] = True
        m = active_mask('C3-', fl, A)
        assert m[21] and not m[22] and not m[25]

    @T
    def hash_and_quantile():
        import tempfile
        fd, p = tempfile.mkstemp(suffix='.bin')   # 저장소 밖 시스템 임시 폴더
        os.write(fd, b'abc')
        os.close(fd)
        try:
            assert sha256_file(p) == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
        finally:
            os.remove(p)
        assert quant([1, 2, 3, 4], .5) == 2.5 and quant([], .5) is None

    @T
    def pipeline_smoke_synthetic():
        rnd = random.Random(11)
        base = dt.date(2010, 1, 4)
        dates = []
        x = base
        while len(dates) < 2500:
            if x.weekday() < 5:
                dates.append(x.isoformat())
            x += dt.timedelta(days=1)
        ds = {}
        for i, s in enumerate(('SOXX', 'QQQ', 'SOXL', 'TQQQ')):
            c = [100.0]
            for _ in range(len(dates) - 1):
                c.append(c[-1] * (1 + rnd.gauss(0.0004, 0.015 * (1 + 2 * (i >= 2)))))
            h = [v * (1 + abs(rnd.gauss(0, .006))) for v in c]
            l = [v * (1 - abs(rnd.gauss(0, .006))) for v in c]
            ds[s] = dict(d=dates, h=h, l=l, c=c, v=[1e6 * (1 + rnd.random()) for _ in c], bad={400, 401})
        rd = {'SOXX': dict(d=dates[-60:], h=ds['SOXX']['h'][-60:], l=ds['SOXX']['l'][-60:], c=ds['SOXX']['c'][-60:], v=ds['SOXX']['v'][-60:], bad=set())}
        R, rows = run_pipeline(ds, aux=lambda AS, FL: aux_repo_from(rd, AS, FL))
        assert set(R['kinds']) == set(JUDGED) and rows
        for k, r in R['kinds'].items():
            assert r['verdict'] in ('보류', '지지', '반대', '미지지') and r['label'] and 'proposal' in r
        assert 'aux_repo' in R and 'SOXX' in R['aux_repo'] and R['aux_repo']['SOXX']['agreement']['C1-']['common_days'] > 0
        json.dumps(R, ensure_ascii=False, default=str)

    fails = 0
    for f in tests:
        try:
            f()
            print('PASS', f.__name__)
        except Exception as e:
            fails += 1
            import traceback
            print('FAIL', f.__name__, repr(e))
            traceback.print_exc()
    print('self-test: %d passed, %d failed' % (len(tests) - fails, fails))
    return fails == 0


def check_inputs():
    ok, res = hash_checks()
    print('입력 해시:', res['inputs'])
    print('문서 해시:', res['doc'])
    for s in EXPECT:
        ds = load_external(s)
        print('  외부', s, len(ds['d']), ds['d'][0], ds['d'][-1], '분할 보수 구간 세션', len(ds['bad']))
    for s in ('MVLL', 'NBIS', 'SOXL', 'SOXX'):
        r = load_repo(s)
        print('  저장소', s, len(r['d']), r['d'][0], r['d'][-1], '30분봉', r['bars'], '종가 불일치', r['close_mismatch'])
    print('ALL OK' if ok else 'HASH MISMATCH')
    return ok


def run():
    ok, res = hash_checks()
    if not ok:
        print('해시 대조 실패 — 계산 중단:', res)
        return False
    ds = {s: load_external(s) for s in EXPECT}
    rdata = {s: load_repo(s) for s in ('MVLL', 'NBIS', 'SOXL', 'SOXX')}
    R, rows = run_pipeline(ds, aux=lambda AS, FL: aux_repo_from(rdata, AS, FL))
    R['meta'] = {'run_at': dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec='seconds'),
                 'script_sha256': sha256_file(os.path.abspath(__file__)), 'hash_checks': res,
                 'doc_raw_sha256': hashlib.sha256(open(DOC, 'rb').read()).hexdigest()}
    json.dump(R, open(OUT_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['asset', 'kind', 'date', 'index', 'z20', 'r20', 'r5', 'mae20'])
        w.writerows(rows)
    print('완료:', OUT_JSON)
    for k in JUDGED:
        print(k, R['kinds'][k]['label'], '| 군집', R['kinds'][k]['cluster_verdict'], '|', R['kinds'][k]['proposal']['status'])
    return True


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--check-inputs', action='store_true')
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test() else 1)
    if a.check_inputs:
        sys.exit(0 if check_inputs() else 1)
    if a.run:
        sys.exit(0 if run() else 1)
    ap.print_help()
