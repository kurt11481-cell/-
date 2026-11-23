# -*- coding: utf-8 -*-
"""심리 등급표 계산 (psych-1123, 사전 등록 psych-grade-prereg-2026-11-23.md 2판).

쓰는 법 (클라우드에서만, python3 -I -B):
  python3 -I -B psych_grade.py DATA_DIR --selftest        # 가격 수익을 계산하지 않는 검사 + 사건 목록 해시 출력
  python3 -I -B psych_grade.py DATA_DIR --run FREEZE OUT   # 고정 뒤 1회. OUT이 있으면 멈춘다

표준 라이브러리만 쓴다. 주문·키움·정책 파일과 무관하다.
"""
import bisect, csv, datetime as dt, hashlib, json, os, platform, random, statistics, sys

# ---------------- 고정 값 (사전 등록 3절) ----------------
DATA_SHA256 = {
    "finra_rows.json": "8ac12590eeef9ae18a463581d45804d221fa5e3352078d674fcc39f2d12dc4e8",
    "cftc_nq.json": "7d16d0d1705c5bc02cbf3777a26f541e79ecf394a023c76da5c38e3c3a71c122",
    "nasdaqcom.csv": "cdeaae283d51e56967d2af102bb8621fae0a43df95513991e892495050ba053f",
}
H = 60                    # 측정 창(세션) = 독립 사건 간격
TOP, BOT = 0.80, 0.20     # 상위·하위 20%
S1_MIN_HIST = 60          # S1 누적 백분위 최소 이력(1년 변화율 개수)
S2_WIN = 156              # S2 굴림 창(보고 수)
CFTC_CODE = "209742"
# S2 사건 시작을 세지 않는 구간(간격 기준은 됨): 과거분 공개 전 + 셧다운 공개 지연(넓게)
S2_EXCLUDE = [("2010-01-01", "2010-12-05"), ("2013-10-01", "2013-11-30"),
              ("2018-12-22", "2019-03-31"), ("2025-10-01", "2026-01-31")]
PERIODS = {
    "S1": [("P1", "2003-01-01", "2009-12-31"), ("P2", "2010-01-01", "2099-12-31")],
    "S2": [("P1", "2010-01-01", "2017-12-31"), ("P2", "2018-01-01", "2099-12-31")],
}
DELTA = 0.05              # 크기(rule1028 사전 등록 6-3의 숫자를 옮겨 씀)
N_MIN = 5                 # 시기마다 최소 독립 사건(같은 선례에서 옮겨 씀)
BOOT_N, BOOT_SEED, CI = 10000, 20261123, 0.95


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# ---------------- 자료 읽기 ----------------
def load(data_dir, check=True):
    if check:
        for f, h in DATA_SHA256.items():
            got = sha(os.path.join(data_dir, f))
            if got != h:
                raise SystemExit("자료 해시 불일치: %s %s" % (f, got))
    px = []
    for r in csv.reader(open(os.path.join(data_dir, "nasdaqcom.csv"))):
        if r and r[0][:1].isdigit() and r[1] not in ("", "."):
            px.append((r[0], float(r[1])))
    rows = json.load(open(os.path.join(data_dir, "finra_rows.json")))[1:]
    finra = sorted((r[0], float(r[1])) for r in rows if r and r[0] and r[1])
    cf = json.load(open(os.path.join(data_dir, "cftc_nq.json")))
    cftc = sorted(
        (r["report_date_as_yyyy_mm_dd"][:10],
         (int(r["lev_money_positions_long"]) - int(r["lev_money_positions_short"])) / int(r["open_interest_all"]))
        for r in cf if r.get("cftc_contract_market_code") == CFTC_CODE)
    return px, finra, cftc


# ---------------- 단서 값 ----------------
def finra_yoy(finra):
    ym = [a for a, _ in finra]
    v = [b for _, b in finra]
    out = []
    for k in range(len(v)):
        y, m = int(ym[k][:4]), int(ym[k][5:7])
        prev = "%04d-%02d" % (y - 1, m)
        if prev in ym:
            out.append((ym[k], v[k] / v[ym.index(prev)] - 1))
    return out


def pct_expanding(series, min_hist):
    out = {}
    for k in range(len(series)):
        if k + 1 < min_hist:
            continue
        hist = [x for _, x in series[: k + 1]]
        out[series[k][0]] = sum(1 for x in hist if x <= series[k][1]) / len(hist)
    return out


def pct_rolling(series, win):
    out = {}
    for k in range(len(series)):
        if k + 1 < win:
            continue
        hist = [x for _, x in series[k + 1 - win: k + 1]]
        out[series[k][0]] = sum(1 for x in hist if x <= series[k][1]) / len(hist)
    return out


def add_months(key, n):
    y, m = int(key[:4]), int(key[5:7]) + n
    while m > 12:
        m -= 12
        y += 1
    return "%04d-%02d-01" % (y, m)


def first_on_or_after(sess, d):
    k = bisect.bisect_left(sess, d)
    return k if k < len(sess) else None


def s1_usable(key):
    """M월 값 → M+2월 1일 당일 또는 그 뒤 첫 세션."""
    return add_months(key, 2)


def s2_usable(key):
    """보고 기준일이 든 주의 다음 주 화요일(당일 또는 그 뒤 첫 세션)."""
    d = dt.date.fromisoformat(key)
    return (d + dt.timedelta(days=8 - d.weekday())).isoformat()


def states_from(sess, pmap, cond, usable):
    """값 key는 usable(key) 당일 또는 그 뒤 첫 세션부터 다음 key가 쓰이기 전날까지. 계산 불가 = None."""
    st = [None] * len(sess)
    keys = sorted(pmap)
    for n, key in enumerate(keys):
        a = first_on_or_after(sess, usable(key))
        if a is None:
            continue
        if n + 1 < len(keys):
            b = first_on_or_after(sess, usable(keys[n + 1]))
            b = len(sess) if b is None else b
        else:
            b = len(sess)
        for i in range(a, b):
            st[i] = cond(pmap[key])
    return st


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
def build(px, finra, cftc, s2u=None):
    s2u = s2u or s2_usable
    sess = [d for d, _ in px]
    s1p = pct_expanding(finra_yoy(finra), S1_MIN_HIST)
    s2p = pct_rolling(cftc, S2_WIN)
    hi = lambda p: p >= TOP
    lo = lambda p: p <= BOT
    return sess, {
        "S1-": ("S1", "-", states_from(sess, s1p, hi, s1_usable), ()),
        "S1+": ("S1", "+", states_from(sess, s1p, lo, s1_usable), ()),
        "S2-": ("S2", "-", states_from(sess, s2p, hi, s2u), tuple(S2_EXCLUDE)),
        "S2+": ("S2", "+", states_from(sess, s2p, lo, s2u), tuple(S2_EXCLUDE)),
    }


def event_lists(px, finra, cftc):
    sess, clues = build(px, finra, cftc)
    last_start = len(sess) - 1 - H
    out = {}
    for name, (fam, side, st, excl) in clues.items():
        ch = event_chain(sess, st, last_start, excl)
        for pname, lo_d, hi_d in PERIODS[fam]:
            out["%s %s" % (name, pname)] = [sess[i] for i in events_in(sess, ch, lo_d, hi_d)]
    return out


def events_hash(px, finra, cftc):
    return hashlib.sha256(json.dumps(event_lists(px, finra, cftc), sort_keys=True).encode()).hexdigest()


def compute(px, finra, cftc):
    sess, clues = build(px, finra, cftc)
    last_start = len(sess) - 1 - H
    out = {}
    for name, (fam, side, st, excl) in clues.items():
        metric = (lambda i: mae60(px, i)) if side == "-" else (lambda i: ret(px, i, H))
        ch = event_chain(sess, st, last_start, excl)
        per, pooled_ev, pooled_base, rows = [], [], [], []
        for pname, lo_d, hi_d in PERIODS[fam]:
            ev = events_in(sess, ch, lo_d, hi_d)
            ev_all = events_in(sess, ch, lo_d, hi_d, counted_only=False)
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
                "events_incl_excluded(보고만)": [sess[i] for i in ev_all],
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
        out[name] = {"side": side, "periods": rows, "pooled_ci95": ci, "grade": grade(side, per, ci)}
    return out


# ---------------- 검사 (실제 가격으로 수익을 계산하지 않음) ----------------
def selftest(px, finra, cftc):
    fails = []
    # 1) 등급 함수 손계산 사례
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
    if [i for i, _ in ch] != [8, 74]:  # 13은 8에서 5세션(간격 미달, 기준 아님), 76은 None 뒤라 전환 아님
        fails.append("chain case1 %s" % ch)
    ch2 = event_chain(fake, st, len(fake) - 1, (("2000-01-09", "2000-01-09"),))
    if events_in(fake, ch2, "1999-01-01", "2099-12-31") != [74]:  # 8(=01-09) 제외, 제외 사건도 간격 기준
        fails.append("chain case2 %s" % ch2)
    if events_in(fake, ch, "2000-01-14", "2099-12-31") != [74]:  # 시기 밖 사건 8도 간격 기준 → 13 아님
        fails.append("chain case3 period-start anchor")
    if events_in(fake, ch, "1999-01-01", fake[74]) != [8, 74]:  # 시기 끝 당일(fake[74]) 포함
        fails.append("chain case4 period-end inclusive %s" % fake[74])
    if events_in(fake, ch, "1999-01-01", fake[73]) != [8]:
        fails.append("chain case5 period-end exclusive")
    # 59/60 간격 경계
    st5 = [False] + [True] + [False] * 58 + [True] + [False] * 59
    st5 = (st5 + [False] * len(fake))[: len(fake)]
    if [i for i, _ in event_chain(fake, st5, len(fake) - 1, ())] != [1]:  # 59세션 뒤 → 아님
        fails.append("gap59")
    st6 = [False] + [True] + [False] * 59 + [True] + [False] * 58
    st6 = (st6 + [False] * len(fake))[: len(fake)]
    if [i for i, _ in event_chain(fake, st6, len(fake) - 1, ())] != [1, 61]:  # 60세션 뒤 → 사건
        fails.append("gap60")
    # last_start 경계
    if [i for i, _ in event_chain(fake, st6, 60, ())] != [1]:
        fails.append("last_start")
    # 3) 측정 함수 손계산(합성 가격)
    fpx = [("d%03d" % k, 100.0 + k) for k in range(70)]
    fpx[30] = ("d030", 50.0)
    if not (abs(mae60(fpx, 0) + 0.5) < 1e-12 and abs(ret(fpx, 0, H) - 0.6) < 1e-12):
        fails.append("measure basic")
    fpx[61] = ("d061", 1.0)  # 창 밖(t+61)
    if not abs(mae60(fpx, 0) + 0.5) < 1e-12:
        fails.append("measure window edge")
    fpx2 = [("e%03d" % k, 100.0 + k) for k in range(70)]
    if not abs(mae60(fpx2, 0) - 0.01) < 1e-12:  # 계속 오르면 양수
        fails.append("measure positive mae")
    # 4) 시점 규칙
    sess = [d for d, _ in px]
    stt = states_from(sess, {"2026-08": 0.9}, lambda p: p >= TOP, s1_usable)
    on_idx = [i for i, s in enumerate(stt) if s is not None]
    if not on_idx or sess[on_idx[0]] != sess[first_on_or_after(sess, "2026-10-01")]:
        fails.append("S1 lag")
    s2p = pct_rolling(cftc, S2_WIN)

    def s2_violations(usable_rule):
        src = states_from(sess, {k: k for k in s2p}, lambda k: k, usable_rule)
        return [sess[i] for i, k in enumerate(src) if k and sess[i] < s2_usable(k)]
    if s2_violations(s2_usable):
        fails.append("S2 lag")
    leaky = lambda k: (dt.date.fromisoformat(k) + dt.timedelta(days=3)).isoformat()  # 같은 주 금요일부터 씀
    if not s2_violations(leaky):
        fails.append("leak injection S2 not caught")
    # 5) 잘림 검사: 그날 알 수 있던 자료만 남겨 다시 계산한 상태 = 전체 계산 상태(그날까지)
    cuts = ["2004-06-15", "2008-09-15", "2011-03-01", "2013-10-15", "2016-01-04", "2018-10-01",
            "2020-03-16", "2022-06-15", "2024-08-01", "2026-06-01"]
    _, full = build(px, finra, cftc)

    def known_finra(cdate):
        return [x for x in finra if s1_usable(x[0]) <= cdate]

    def known_cftc(cdate):
        return [x for x in cftc if s2_usable(x[0]) <= cdate]
    for cdate in cuts:
        cpx = [x for x in px if x[0] <= cdate]
        _, part = build(cpx, known_finra(cdate), known_cftc(cdate))
        for k in full:
            a, b = full[k][2][: len(cpx)], part[k][2]
            if a != b:
                bad = [cpx[i][0] for i in range(len(b)) if a[i] != b[i]][:3]
                fails.append("truncation %s %s %s" % (cdate, k, bad))
    # 6) 일부러 넣은 누출(S1을 M+1월부터 씀)이 잘림 검사에서 잡히는지
    leak1 = lambda key: add_months(key, 1)
    s1p_full = pct_expanding(finra_yoy(finra), S1_MIN_HIST)
    caught = False
    for cdate in cuts:
        cpx = [x for x in px if x[0] <= cdate]
        ps = [d for d, _ in cpx]
        a = states_from(sess, s1p_full, lambda p: p >= TOP, leak1)[: len(cpx)]
        b = states_from(ps, pct_expanding(finra_yoy(known_finra(cdate)), S1_MIN_HIST), lambda p: p >= TOP, leak1)
        if a != b:
            caught = True
    if not caught:
        fails.append("leak injection S1 not caught")
    # 7) 백분위 누출(전체 표본 백분위)이 잘림 검사에서 잡히는지
    def pct_full(series):
        xs = [x for _, x in series]
        return {k: sum(1 for x in xs if x <= v) / len(xs) for k, v in series}
    caught = False
    for cdate in cuts:
        cpx = [x for x in px if x[0] <= cdate]
        ps = [d for d, _ in cpx]
        a = states_from(sess, pct_full(cftc), lambda p: p >= TOP, s2_usable)[: len(cpx)]
        b = states_from(ps, pct_full(known_cftc(cdate)), lambda p: p >= TOP, s2_usable)
        if a != b:
            caught = True
    if not caught:
        fails.append("leak injection pct not caught")
    return fails


def main():
    data_dir = sys.argv[1]
    mode = sys.argv[2]
    px, finra, cftc = load(data_dir)
    if mode == "--selftest":
        f = selftest(px, finra, cftc)
        print("SELFTEST", "PASS" if not f else "FAIL", f)
        print("EVENTS_SHA256", events_hash(px, finra, cftc))
        print("PYTHON", platform.python_version())
        sys.exit(1 if f else 0)
    if mode == "--run":
        freeze, out = sys.argv[3], sys.argv[4]
        if os.path.exists(out):
            raise SystemExit("이미 계산함(1회 규칙): %s" % out)
        fz = json.load(open(freeze))
        if fz["script_sha256"] != sha(__file__):
            raise SystemExit("계산 파일이 고정 뒤 바뀜")
        if fz["events_sha256"] != events_hash(px, finra, cftc):
            raise SystemExit("사건 목록이 고정 때와 다름")
        f = selftest(px, finra, cftc)
        if f:
            raise SystemExit("검사 실패 — 결과를 쓰지 않음: %s" % f)
        res = compute(px, finra, cftc)
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
