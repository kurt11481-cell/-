# -*- coding: utf-8 -*-
"""유동성 등급표 계산 (liquidity-1124, 사전 등록 liquidity-grade-prereg-2026-11-25.md 2판).

쓰는 법 (클라우드에서만, python3 -I -B):
  python3 -I -B liq_grade.py DATA_DIR --selftest        # 가격 수익을 계산하지 않는 검사 + 사건 목록 해시 출력
  python3 -I -B liq_grade.py DATA_DIR --events          # 가격 수익 없이 사건 날짜·달 분포·구성요소 몫만 출력
  python3 -I -B liq_grade.py DATA_DIR --run FREEZE OUT   # 고정 뒤 1회. OUT이 있으면 멈춘다

표준 라이브러리만 쓴다. 주문·키움·정책 파일과 무관하다.
사건 사슬·측정·등급·다시 뽑기 함수는 심리 등급표 psych_grade.py(sha256 990a6092…)의 것을 글자 그대로 옮겼다.
"""
import bisect, csv, datetime as dt, hashlib, json, os, platform, random, statistics, sys

# ---------------- 고정 값 (사전 등록 2·3절) ----------------
DATA_SHA256 = {
    "WALCL.csv": "9a42ddb135197ec68e31323adf54f348f17b9a1257047bde2c875c7977f3341a",
    "WDTGAL.csv": "83997772e901cec058528d2de70609d62764dd4092adf1f1d6b4f1f8fc2d942f",
    "RRPONTSYD.csv": "ca341e12c31d7b8d8119aa3b795b920446c598b64d917300f8ce58f8724fa629",
    "nasdaqcom.csv": "cdeaae283d51e56967d2af102bb8621fae0a43df95513991e892495050ba053f",
}
H = 60                    # 측정 창(세션) = 독립 사건 간격
TOP, BOT = 0.80, 0.20     # 상위·하위 20%
K_WEEKS = 4               # 변화 길이(주간 관측 수)
WIN = 156                 # 굴림 창(주간 변화 개수)
RRP_START = "2013-09-23"  # 역레포 일간 계열 시작 — 그 전 빈칸은 0 (수집기 collect.py v0.6과 같음)
RRP_BACK_DAYS = 7         # 수요일 역레포가 빈칸(휴일)이면 7일 안 직전 값
PERIODS = [("P1", "2009-01-01", "2017-12-31"), ("P2", "2018-01-01", "2099-12-31")]
DELTA = 0.05              # 크기(심리 등급표 3-5절 그대로)
N_MIN = 5                 # 시기마다 최소 독립 사건(같음)
BOOT_N, BOOT_SEED, CI = 10000, 20261123, 0.95   # 심리 등급표와 같은 값
# 보고만(등급에 쓰지 않음): 이웃 정의 · 수준 · TGA 단독
REPORT_ONLY = [
    # (이름, 계열, 변화 길이(0 = 수준), 문턱 하위, 문턱 상위)
    ("N2w", "nl", 2, 0.20, 0.80),
    ("N8w", "nl", 8, 0.20, 0.80),
    ("N10pct", "nl", 4, 0.10, 0.90),
    ("LEVEL", "nl", 0, 0.20, 0.80),
    ("TGA", "tga_neg", 4, 0.20, 0.80),   # TGA 변화의 부호를 뒤집은 것(TGA 증가 = 유동성 축소 쪽)
]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# ---------------- 자료 읽기 ----------------
def read_fred(path):
    out = []
    for r in csv.reader(open(path)):
        if r and r[0][:1].isdigit() and len(r) > 1 and r[1] not in ("", "."):
            out.append((r[0], float(r[1])))
    return out


def load(data_dir, check=True):
    if check:
        for f, h in DATA_SHA256.items():
            got = sha(os.path.join(data_dir, f))
            if got != h:
                raise SystemExit("자료 해시 불일치: %s %s" % (f, got))
    px = read_fred(os.path.join(data_dir, "nasdaqcom.csv"))
    walcl = read_fred(os.path.join(data_dir, "WALCL.csv"))
    wdtgal = read_fred(os.path.join(data_dir, "WDTGAL.csv"))
    rrp = read_fred(os.path.join(data_dir, "RRPONTSYD.csv"))
    return px, walcl, wdtgal, rrp


# ---------------- 단서 값 ----------------
def rrp_at(rrp, d):
    """역레포(십억$) d일 값, 없으면(휴일) 7일 안 직전 값. 그것도 없고 계열 시작 전이면 0, 시작 뒤면 None."""
    keys = [x[0] for x in rrp]
    k = bisect.bisect_right(keys, d) - 1
    if k >= 0 and (dt.date.fromisoformat(d) - dt.date.fromisoformat(keys[k])).days <= RRP_BACK_DAYS:
        return rrp[k][1]
    if d < RRP_START:
        return 0.0
    return None


def components(walcl, wdtgal, rrp):
    """[(수요일, WALCL, WDTGAL, 역레포 백만$)] — 셋이 다 있는 주만."""
    tga = dict(wdtgal)
    out = []
    for d, v in walcl:
        if d not in tga:
            continue
        r = rrp_at(rrp, d)
        if r is None:
            continue
        out.append((d, v, tga[d], r * 1000.0))
    return out


def net_liquidity(comp):
    """주간 순유동성(백만$) = WALCL − WDTGAL − 역레포×1000, 같은 수요일."""
    return [(d, a - t - r) for d, a, t, r in comp]


def changes(series, k):
    """k관측 변화액. k = 0 이면 수준 그대로."""
    if k == 0:
        return list(series)
    return [(series[i][0], series[i][1] - series[i - k][1]) for i in range(k, len(series))]


def pct_rolling(series, win):
    out = {}
    for k in range(len(series)):
        if k + 1 < win:
            continue
        hist = [x for _, x in series[k + 1 - win: k + 1]]
        out[series[k][0]] = sum(1 for x in hist if x <= series[k][1]) / len(hist)
    return out


def first_on_or_after(sess, d):
    k = bisect.bisect_left(sess, d)
    return k if k < len(sess) else None


def usable(key):
    """기준일(수요일 수준) 값 → 기준일이 든 주의 다음 주 화요일(당일 또는 그 뒤 첫 세션)부터.
    H.4.1은 목요일 16:30 ET(장 마감 뒤), 연방 공휴일이면 다음 영업일 — 가장 늦은 경우(월요일 16:30)도 덮는다."""
    d = dt.date.fromisoformat(key)
    return (d + dt.timedelta(days=8 - d.weekday())).isoformat()


def states_from(sess, pmap, cond, usable_rule):
    """값 key는 usable(key) 당일 또는 그 뒤 첫 세션부터 다음 key가 쓰이기 전날까지. 계산 불가 = None."""
    st = [None] * len(sess)
    src = [None] * len(sess)
    keys = sorted(pmap)
    for n, key in enumerate(keys):
        a = first_on_or_after(sess, usable_rule(key))
        if a is None:
            continue
        if n + 1 < len(keys):
            b = first_on_or_after(sess, usable_rule(keys[n + 1]))
            b = len(sess) if b is None else b
        else:
            b = len(sess)
        for i in range(a, b):
            st[i] = cond(pmap[key])
            src[i] = key
    return st, src


def event_chain(sess, st, last_start, exclude=()):
    """단서마다 한 번에 만드는 사건 사슬. 반환 = [(세션 번호, 셈 여부)].
    사건 = 계산 가능한 꺼짐 바로 다음의 켜짐(계산 불가 뒤 첫 켜짐은 아님) 가운데
    바로 앞 사건(셈 여부와 상관없이)에서 H세션 이상 떨어진 것. 간격 미달 전환은 기준이 아니다.
    제외 구간에 시작한 사건은 세지 않지만 간격 기준은 된다."""
    out, prev_off, last_ev = [], False, -10 ** 9
    for i, s in enumerate(st):
        if s is None:
            prev_off = False
            continue
        if s and prev_off and i - last_ev >= H and i <= last_start:
            counted = not any(a <= sess[i] <= b for a, b in exclude)
            out.append((i, counted))
            last_ev = i
        prev_off = not s
    return out


def events_in(sess, chain, lo, hi, counted_only=True):
    return [i for i, c in chain if lo <= sess[i] <= hi and (c or not counted_only)]


# ---------------- 측정 ----------------
def mae60(px, i):
    c0 = px[i][1]
    return min(c for _, c in px[i + 1: i + 1 + H]) / c0 - 1


def ret(px, i, n):
    return px[i + n][1] / px[i][1] - 1


def tstat(xs):
    if len(xs) < 2:
        return None
    s = statistics.stdev(xs)
    return None if s == 0 else statistics.mean(xs) / (s / len(xs) ** 0.5)


def grade(side, per, ci):
    """per = [(n, d), (n, d)] 두 시기. side '-' 는 d<=-DELTA 가 맞는 방향, '+' 는 d>=+DELTA."""
    sgn = -1 if side == "-" else 1
    if any(n < N_MIN for n, _ in per):
        return "판정 불가(표본 부족)"
    if all(sgn * d >= DELTA for _, d in per):
        return "1"
    if all(sgn * d <= -DELTA for _, d in per):
        return "2"
    if ci is not None and ci[0] > -DELTA and ci[1] < DELTA:
        return "3"
    return "판정 불가"


def boot_ci(ev_vals, base_med):
    rnd = random.Random(BOOT_SEED)
    n = len(ev_vals)
    ds = sorted(statistics.median([ev_vals[rnd.randrange(n)] for _ in range(n)]) - base_med for _ in range(BOOT_N))
    a = (1 - CI) / 2
    return ds[int(a * BOOT_N)], ds[int((1 - a) * BOOT_N) - 1]


# ---------------- 단서 정의 묶음 ----------------
def clue_pair(sess, series, k, bot, top, usable_rule=None):
    """한 계열에서 − 단서(하위)와 + 단서(상위) 상태를 만든다. 반환 {'-': (st, src), '+': (st, src)}."""
    u = usable_rule or usable
    pm = pct_rolling(changes(series, k), WIN)
    return {"-": states_from(sess, pm, lambda p: p <= bot, u),
            "+": states_from(sess, pm, lambda p: p >= top, u)}, pm


def build(px, walcl, wdtgal, rrp, usable_rule=None):
    sess = [d for d, _ in px]
    comp = components(walcl, wdtgal, rrp)
    nl = net_liquidity(comp)
    pair, pm = clue_pair(sess, nl, K_WEEKS, BOT, TOP, usable_rule)
    clues = {"LQ1-": ("-",) + pair["-"], "LQ1+": ("+",) + pair["+"]}
    return sess, clues, comp, nl, pm


def build_report_only(px, walcl, wdtgal, rrp):
    sess = [d for d, _ in px]
    comp = components(walcl, wdtgal, rrp)
    ser = {"nl": net_liquidity(comp), "tga_neg": [(d, -t) for d, _, t, _ in comp]}
    out = {}
    for name, key, k, bot, top in REPORT_ONLY:
        pair, _ = clue_pair(sess, ser[key], k, bot, top)
        out[name + "-"] = ("-",) + pair["-"]
        out[name + "+"] = ("+",) + pair["+"]
    return sess, out


def event_lists(px, walcl, wdtgal, rrp):
    sess, clues, _, _, _ = build(px, walcl, wdtgal, rrp)
    last_start = len(sess) - 1 - H
    out = {}
    for name, (side, st, src) in clues.items():
        ch = event_chain(sess, st, last_start)
        out[name + " chain(시기 밖 포함)"] = [sess[i] for i, _ in ch]
        for pname, lo_d, hi_d in PERIODS:
            out["%s %s" % (name, pname)] = [sess[i] for i in events_in(sess, ch, lo_d, hi_d)]
    return out


def events_hash(px, walcl, wdtgal, rrp):
    return hashlib.sha256(json.dumps(event_lists(px, walcl, wdtgal, rrp), sort_keys=True).encode()).hexdigest()


def report_only_event_lists(px, walcl, wdtgal, rrp):
    sess, clues = build_report_only(px, walcl, wdtgal, rrp)
    last_start = len(sess) - 1 - H
    out = {}
    for name, (side, st, src) in clues.items():
        ch = event_chain(sess, st, last_start)
        for pname, lo_d, hi_d in PERIODS:
            out["%s %s" % (name, pname)] = [sess[i] for i in events_in(sess, ch, lo_d, hi_d)]
    return out


def report_only_hash(px, walcl, wdtgal, rrp):
    return hashlib.sha256(json.dumps(report_only_event_lists(px, walcl, wdtgal, rrp), sort_keys=True).encode()).hexdigest()


def event_details(px, walcl, wdtgal, rrp):
    """가격 수익 없이: 사건 세션 · 근거 수요일 · 백분위 · 4주 변화와 구성요소 몫(백만$) · 주도 요소."""
    sess, clues, comp, nl, pm = build(px, walcl, wdtgal, rrp)
    last_start = len(sess) - 1 - H
    idx = {d: n for n, (d, _, _, _) in enumerate(comp)}
    out = {}
    for name, (side, st, src) in clues.items():
        ch = event_chain(sess, st, last_start)
        rows = []
        for i, _ in ch:
            key = src[i]
            n = idx[key]
            a0, a1 = comp[n - K_WEEKS], comp[n]
            parts = {"연준 자산": a1[1] - a0[1], "TGA": -(a1[2] - a0[2]), "역레포": -(a1[3] - a0[3])}
            total = sum(parts.values())
            sgn = -1 if side == "-" else 1
            lead = max(parts, key=lambda p: sgn * parts[p])
            per = next((p for p, lo_d, hi_d in PERIODS if lo_d <= sess[i] <= hi_d), "시기 밖")
            rows.append({"session": sess[i], "obs_wed": key, "pct": round(pm[key], 4), "period": per,
                         "chg_musd": round(total), "parts_musd": {p: round(v) for p, v in parts.items()}, "lead": lead})
        out[name] = rows
    return out


def compute_one(px, sess, side, st, last_start):
    metric = (lambda i: mae60(px, i)) if side == "-" else (lambda i: ret(px, i, H))
    ch = event_chain(sess, st, last_start)
    per, pooled_ev, pooled_base, rows = [], [], [], []
    for pname, lo_d, hi_d in PERIODS:
        ev = events_in(sess, ch, lo_d, hi_d)
        base = [i for i in range(len(sess)) if st[i] is not None and i <= last_start and lo_d <= sess[i] <= hi_d]
        ev_m = [metric(i) for i in ev]
        base_m = [metric(i) for i in base]
        d = (statistics.median(ev_m) - statistics.median(base_m)) if ev_m and base_m else None
        per.append((len(ev), d if d is not None else 0.0))
        pooled_ev += ev_m
        pooled_base += base_m
        rows.append({
            "period": pname, "range": [lo_d, hi_d], "n_events": len(ev),
            "events": [sess[i] for i in ev],
            "n_base": len(base),
            "primary": "MAE60" if side == "-" else "R60",
            "event_median": statistics.median(ev_m) if ev_m else None,
            "base_median": statistics.median(base_m) if base_m else None,
            "diff": d,
            "report_only": {
                "R20_event_median": statistics.median([ret(px, i, 20) for i in ev]) if ev else None,
                "R20_base_median": statistics.median([ret(px, i, 20) for i in base]) if base else None,
                "R60_event_median": statistics.median([ret(px, i, H) for i in ev]) if ev else None,
                "R60_base_median": statistics.median([ret(px, i, H) for i in base]) if base else None,
                "MAE60_event_median": statistics.median([mae60(px, i) for i in ev]) if ev else None,
                "MAE60_base_median": statistics.median([mae60(px, i) for i in base]) if base else None,
                "primary_event_mean": statistics.mean(ev_m) if ev_m else None,
                "primary_t(겹침 없는 사건만)": tstat(ev_m),
            },
        })
    ci = None
    if all(n >= N_MIN for n, _ in per) and pooled_ev:
        ci = boot_ci(pooled_ev, statistics.median(pooled_base))
    return {"side": side, "periods": rows, "pooled_ci95": ci, "grade": grade(side, per, ci)}


def compute(px, walcl, wdtgal, rrp):
    sess, clues, _, _, _ = build(px, walcl, wdtgal, rrp)
    last_start = len(sess) - 1 - H
    out = {}
    for name, (side, st, src) in clues.items():
        out[name] = compute_one(px, sess, side, st, last_start)
    # 보고만 — 같은 함수로 재지만 등급·구간을 내지 않는다(사건 수·중앙값·차이만, 사전 등록 3-6)
    _, ro = build_report_only(px, walcl, wdtgal, rrp)
    out["_report_only(등급 아님)"] = {}
    for name, (side, st, src) in ro.items():
        r = compute_one(px, sess, side, st, last_start)
        r.pop("grade")
        r.pop("pooled_ci95")
        out["_report_only(등급 아님)"][name] = r
    return out


# ---------------- 검사 (실제 가격으로 수익을 계산하지 않음) ----------------
SEEN_D4 = ["2024-10-02", "2025-01-01", "2025-02-05", "2025-04-16", "2025-09-03", "2025-10-22",
           "2026-04-22", "2026-06-17", "2026-07-29"]   # 구현 스레드가 본 D4 켜짐 수요일(간격 조건 없음, 제안서 v0.6 3절)


def selftest(px, walcl, wdtgal, rrp):
    fails = []
    # 1) 등급 함수 손계산 사례(심리 등급표와 같은 8개)
    cases = [
        ("-", [(5, -0.06), (6, -0.05)], None, "1"),
        ("-", [(4, -0.20), (9, -0.20)], None, "판정 불가(표본 부족)"),
        ("-", [(5, 0.05), (5, 0.07)], None, "2"),
        ("+", [(5, 0.05), (7, 0.051)], None, "1"),
        ("+", [(5, -0.06), (7, -0.05)], None, "2"),
        ("+", [(5, 0.01), (7, -0.01)], (-0.049, 0.049), "3"),
        ("+", [(5, 0.01), (7, -0.01)], (-0.05, 0.03), "판정 불가"),
        ("-", [(5, -0.06), (7, -0.01)], (-0.04, 0.01), "3"),
    ]
    for side, per, ci, want in cases:
        got = grade(side, per, ci)
        if got != want:
            fails.append("grade %s %s %s -> %s (want %s)" % (side, per, ci, got, want))
    # 2) 사건 사슬 손계산 사례 (가상 세션 120개)
    fake = ["2000-01-%02d" % k for k in range(1, 32)] + ["2000-02-%02d" % k for k in range(1, 29)] + \
           ["2000-03-%02d" % k for k in range(1, 32)] + ["2000-04-%02d" % k for k in range(1, 31)]
    st = [None] * 3 + [False] * 5 + [True] * 3 + [False] * 2 + [True] + [False] * 60 + [True] + [None] + [True] + [False] * 45
    st = (st + [False] * len(fake))[: len(fake)]
    ch = event_chain(fake, st, len(fake) - 1, ())
    if [i for i, _ in ch] != [8, 74]:
        fails.append("chain case1 %s" % ch)
    ch2 = event_chain(fake, st, len(fake) - 1, (("2000-01-09", "2000-01-09"),))
    if events_in(fake, ch2, "1999-01-01", "2099-12-31") != [74]:
        fails.append("chain case2 %s" % ch2)
    if events_in(fake, ch, "2000-01-14", "2099-12-31") != [74]:
        fails.append("chain case3 period-start anchor")
    if events_in(fake, ch, "1999-01-01", fake[74]) != [8, 74]:
        fails.append("chain case4 period-end inclusive %s" % fake[74])
    if events_in(fake, ch, "1999-01-01", fake[73]) != [8]:
        fails.append("chain case5 period-end exclusive")
    st5 = [False] + [True] + [False] * 58 + [True] + [False] * 59
    st5 = (st5 + [False] * len(fake))[: len(fake)]
    if [i for i, _ in event_chain(fake, st5, len(fake) - 1, ())] != [1]:
        fails.append("gap59")
    st6 = [False] + [True] + [False] * 59 + [True] + [False] * 58
    st6 = (st6 + [False] * len(fake))[: len(fake)]
    if [i for i, _ in event_chain(fake, st6, len(fake) - 1, ())] != [1, 61]:
        fails.append("gap60")
    if [i for i, _ in event_chain(fake, st6, 60, ())] != [1]:
        fails.append("last_start")
    # 3) 측정 함수 손계산(합성 가격)
    fpx = [("d%03d" % k, 100.0 + k) for k in range(70)]
    fpx[30] = ("d030", 50.0)
    if not (abs(mae60(fpx, 0) + 0.5) < 1e-12 and abs(ret(fpx, 0, H) - 0.6) < 1e-12):
        fails.append("measure basic")
    fpx[61] = ("d061", 1.0)
    if not abs(mae60(fpx, 0) + 0.5) < 1e-12:
        fails.append("measure window edge")
    fpx2 = [("e%03d" % k, 100.0 + k) for k in range(70)]
    if not abs(mae60(fpx2, 0) - 0.01) < 1e-12:
        fails.append("measure positive mae")
    # 4) 순유동성 계산 손계산: 단위(역레포 ×1000) · 휴일 역레포 직전 값 · 계열 시작 전 0 · 시작 뒤 빈칸 주 빼기
    w = [("2013-01-02", 100.0), ("2020-01-01", 1000.0), ("2020-01-08", 1100.0), ("2020-02-05", 1200.0)]
    t = [("2013-01-02", 10.0), ("2020-01-01", 100.0), ("2020-01-08", 100.0), ("2020-02-05", 100.0)]
    r = [("2019-12-31", 0.2), ("2020-01-08", 0.3)]
    c = components(w, t, r)
    if [x[0] for x in c] != ["2013-01-02", "2020-01-01", "2020-01-08"]:
        fails.append("components weeks %s" % c)
    elif not (c[0][3] == 0.0 and c[1][3] == 200.0 and c[2][3] == 300.0 and net_liquidity(c)[1][1] == 700.0):
        fails.append("components values %s" % c)
    # 5) 실제 자료 값 대조(가격 아님): 2026-11-18 순유동성 = 6,741,452 − 892,310 − 331 = 5,848,811 (제안서 v0.6 3절)
    sess, clues, comp, nl, pm = build(px, walcl, wdtgal, rrp)
    if dict(nl).get("2026-11-18") is None or round(dict(nl)["2026-11-18"]) != 5848811:
        fails.append("nl 2026-11-18 %s" % dict(nl).get("2026-11-18"))
    # 6) 수집기 D4 정의(간격 없음, 전주 밖 → 이번 주 안)로 센 2024-08-21~2026-11-18 켜짐 수요일이 이미 본 9개와 같아야 한다
    ks = sorted(pm)
    d4 = [ks[n] for n in range(1, len(ks)) if pm[ks[n]] <= BOT and pm[ks[n - 1]] > BOT and "2024-08-21" <= ks[n] <= "2026-11-18"]
    if d4 != SEEN_D4:
        fails.append("seen D4 list differs %s" % d4)
    # 7) 시점 규칙: 어느 세션도 '다음 주 화요일' 앞에 그 수요일 값을 쓰지 않는다
    def violations(rule):
        _, src = states_from(sess, {k: 0.5 for k in pm}, lambda p: False, rule)
        return [sess[i] for i, k in enumerate(src) if k and sess[i] < usable(k)]
    if violations(usable):
        fails.append("usable lag")
    leaky = lambda k: (dt.date.fromisoformat(k) + dt.timedelta(days=1)).isoformat()  # 같은 주 목요일부터 씀
    if not violations(leaky):
        fails.append("leak injection (same-week Thursday) not caught")
    if usable("2026-11-18") != "2026-11-24" or usable("2025-01-01") != "2025-01-07":
        fails.append("usable date")
    # 8) 잘림 검사: 그날 알 수 있던 자료만 남겨 다시 계산한 상태 = 전체 계산 상태(그날까지)
    cuts = ["2006-06-15", "2008-09-15", "2011-03-01", "2013-10-15", "2016-01-04", "2018-10-01",
            "2020-03-16", "2022-06-15", "2024-08-01", "2026-06-01"]

    def known(series, cdate):
        return [x for x in series if usable(x[0]) <= cdate]

    def known_rrp(cdate):
        # 역레포는 일간(다음 날 공개)이지만, 수요일 값은 같은 수요일 H.4.1 값과 함께만 쓰이므로 그 수요일 이하만 남긴다
        ws = known(walcl, cdate)
        last = ws[-1][0] if ws else ""
        return [x for x in rrp if x[0] <= last]
    for cdate in cuts:
        cpx = [x for x in px if x[0] <= cdate]
        _, part, _, _, _ = build(cpx, known(walcl, cdate), known(wdtgal, cdate), known_rrp(cdate))
        for k in clues:
            a, b = clues[k][1][: len(cpx)], part[k][1]
            if a != b:
                bad = [cpx[i][0] for i in range(len(b)) if a[i] != b[i]][:3]
                fails.append("truncation %s %s %s" % (cdate, k, bad))
    # 9) 일부러 넣은 누출(전체 표본 백분위)이 잘림 검사에서 잡히는지
    def pct_full(series):
        xs = [x for _, x in series]
        return {k: sum(1 for x in xs if x <= v) / len(xs) for k, v in series}
    caught = False
    for cdate in cuts:
        cpx = [x for x in px if x[0] <= cdate]
        ps = [d for d, _ in cpx]
        full_ch = changes(nl, K_WEEKS)
        part_nl = net_liquidity(components(known(walcl, cdate), known(wdtgal, cdate), known_rrp(cdate)))
        a = states_from(sess, pct_full(full_ch), lambda p: p <= BOT, usable)[0][: len(cpx)]
        b = states_from(ps, pct_full(changes(part_nl, K_WEEKS)), lambda p: p <= BOT, usable)[0]
        if a != b:
            caught = True
    if not caught:
        fails.append("leak injection pct not caught")
    # 10) 주간 관측이 빠짐없이 7일 간격인지(4관측 = 4주가 맞는지)
    gaps = [(comp[n - 1][0], comp[n][0]) for n in range(1, len(comp))
            if (dt.date.fromisoformat(comp[n][0]) - dt.date.fromisoformat(comp[n - 1][0])).days != 7]
    if gaps:
        fails.append("weekly gaps %s" % gaps[:5])
    # 11) 계산 경로 시운전: 실제 가격 대신 합성 가격(날마다 +0.01, 실제 나스닥 값 아님)으로 compute 가 끝까지 돌고
    #     사건 수가 사건 목록과 같으며 보고 전용 줄에 등급·구간 칸이 없는지
    fake_px = [(d, 100.0 + 0.01 * n) for n, (d, _) in enumerate(px)]
    try:
        res = compute(fake_px, walcl, wdtgal, rrp)
        el = event_lists(px, walcl, wdtgal, rrp)
        for name in ("LQ1-", "LQ1+"):
            for row in res[name]["periods"]:
                if row["n_events"] != len(el["%s %s" % (name, row["period"])]):
                    fails.append("smoke n_events %s %s" % (name, row["period"]))
            if res[name]["grade"] not in ("1", "2", "3", "판정 불가", "판정 불가(표본 부족)"):
                fails.append("smoke grade %s" % name)
        ro = res["_report_only(등급 아님)"]
        if len(ro) != 2 * len(REPORT_ONLY) or any("grade" in v or "pooled_ci95" in v for v in ro.values()):
            fails.append("smoke report-only shape")
        json.dumps(res, ensure_ascii=False)
    except Exception as e:
        fails.append("smoke compute %s %s" % (type(e).__name__, e))
    return fails


def print_events(px, walcl, wdtgal, rrp):
    sess, clues, comp, nl, pm = build(px, walcl, wdtgal, rrp)
    last_start = len(sess) - 1 - H
    ks = sorted(pm)
    print("주간 관측", len(comp), comp[0][0], "~", comp[-1][0], "· 백분위 첫 주", ks[0], "· 마지막 시작 세션", sess[last_start])
    det = event_details(px, walcl, wdtgal, rrp)
    for name, (side, st, src) in clues.items():
        comp_sess = [i for i in range(len(sess)) if st[i] is not None]
        print("\n==", name, "계산 가능 첫 세션", sess[comp_sess[0]], "· 켜진 세션 비율(전체)",
              round(sum(1 for i in comp_sess if st[i]) / len(comp_sess), 3))
        for pname, lo_d, hi_d in PERIODS:
            base = [i for i in comp_sess if i <= last_start and lo_d <= sess[i] <= hi_d]
            rows = [r for r in det[name] if r["period"] == pname]
            months = {}
            leads = {}
            for r in rows:
                months[r["session"][5:7]] = months.get(r["session"][5:7], 0) + 1
                leads[r["lead"]] = leads.get(r["lead"], 0) + 1
            years = {}
            for r in rows:
                years[r["session"][:4]] = years.get(r["session"][:4], 0) + 1
            print(" ", pname, "사건", len(rows), "· 평소 세션", len(base),
                  "· 켜진 비율", round(sum(1 for i in base if st[i]) / len(base), 3) if base else None)
            print("    달 분포", dict(sorted(months.items())), "· 해 분포", dict(sorted(years.items())), "· 주도", leads)
        for r in det[name]:
            print("   ", r["period"], r["session"], "수요일", r["obs_wed"], "백분위", r["pct"], "4주 변화", r["chg_musd"],
                  r["parts_musd"], "주도", r["lead"])
    ro = report_only_event_lists(px, walcl, wdtgal, rrp)
    print("\n== 보고만(등급 아님) 사건 수")
    for k in sorted(ro):
        print("  ", k, len(ro[k]))
    # 지금 상태
    print("\n지금 상태:", {name: (sess[-1], st[-1], src[-1], round(pm[src[-1]], 3)) for name, (side, st, src) in clues.items()})


def main():
    data_dir = sys.argv[1]
    mode = sys.argv[2]
    px, walcl, wdtgal, rrp = load(data_dir)
    if mode == "--selftest":
        f = selftest(px, walcl, wdtgal, rrp)
        print("SELFTEST", "PASS" if not f else "FAIL", f)
        print("EVENTS_SHA256", events_hash(px, walcl, wdtgal, rrp))
        print("REPORT_ONLY_EVENTS_SHA256", report_only_hash(px, walcl, wdtgal, rrp))
        print("PYTHON", platform.python_version())
        sys.exit(1 if f else 0)
    if mode == "--events":
        print_events(px, walcl, wdtgal, rrp)
        return
    if mode == "--run":
        freeze, out = sys.argv[3], sys.argv[4]
        if os.path.exists(out):
            raise SystemExit("이미 계산함(1회 규칙): %s" % out)
        fz = json.load(open(freeze))
        if fz["script_sha256"] != sha(__file__):
            raise SystemExit("계산 파일이 고정 뒤 바뀜")
        if fz["events_sha256"] != events_hash(px, walcl, wdtgal, rrp):
            raise SystemExit("사건 목록이 고정 때와 다름")
        if fz["report_only_events_sha256"] != report_only_hash(px, walcl, wdtgal, rrp):
            raise SystemExit("보고 전용 사건 목록이 고정 때와 다름")
        f = selftest(px, walcl, wdtgal, rrp)
        if f:
            raise SystemExit("검사 실패 — 결과를 쓰지 않음: %s" % f)
        res = compute(px, walcl, wdtgal, rrp)
        res["_event_details(가격 없음)"] = event_details(px, walcl, wdtgal, rrp)
        res["_meta"] = {"freeze": fz, "data_sha256": DATA_SHA256, "python": platform.python_version(),
                        "computed_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
        json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
        for k, v in res.items():
            if k.startswith("_"):
                continue
            print(k, v["grade"], [(r["period"], r["n_events"], r["diff"]) for r in v["periods"]], v["pooled_ci95"])
        return
    raise SystemExit("mode?")


if __name__ == "__main__":
    main()
