#!/usr/bin/env python3
"""SNDK 리플레이 v3 — 주간 지시문 6) python(자동 모드 + 보호 규칙 ⑧)을 매주 그대로 실행해 SNDK 유지 여부를 본다 (D급).

사용법: python3 replay_sndk_v3.py <weekly-python.py> <sndk.csv> <soxx.csv> [<old-proposal-python.py>]
- 가정은 replay_sndk_r21.py(설계 16절)와 같다: 실적일·S1·S2 표, 관심 5 = SNDK + 고정 강세 4종목(10·10·9·9), 경쟁 후보 1개(9점 또는 10점).
- 차이: 점수·규칙은 지시문 python이 계산한다(S7 = 반응 세션 + 10세션, P0 = 발표일 종가, EMA50 시드 = 처음 50개 평균).
  SNDK 상장(2025-02-13) 전 구간은 첫 종가로 채운다(python의 253개 최소 조건 때문). 공식 실적 입력은 발표 다음 주 실행에 바로 들어간다고 가정.
- 경쟁 후보·고정 관심 4종목은 매일 +1% 합성 일봉(점수 고정용). 가격은 Yahoo 일봉(참고값, 키움 미대조). 매매 근거 아님.
"""
import csv, json, os, sys, copy, subprocess, tempfile, datetime as T
PY, SNDK, SOXX = sys.argv[1:4]; OLD = sys.argv[4] if len(sys.argv) > 4 else None
EARN = ["2025-05-07", "2025-08-14", "2025-11-06", "2026-01-29", "2026-04-30", "2026-08-05"]
S1 = {"2025-05-07": 0, "2025-08-14": 1, "2025-11-06": 2, "2026-01-29": 2, "2026-04-30": 2, "2026-08-05": 2}
S2 = {"2025-05-07": 1, "2025-08-14": 2, "2025-11-06": 2, "2026-01-29": 2, "2026-04-30": 2, "2026-08-05": 2}
ENTRY = "2025-08-29"
sn = [(r["date"], float(r["close"])) for r in csv.DictReader(open(SNDK))]
sx = {r["date"]: float(r["close"]) for r in csv.DictReader(open(SOXX))}
real = [d for d, _ in sn]
pad = []; d0 = T.date.fromisoformat(real[0])
while len(pad) < 160:
    d0 -= T.timedelta(days=1)
    if d0.weekday() < 5: pad.append(d0.isoformat())
DATES = sorted(pad) + real
SNC = {d: sn[0][1] for d in pad} | dict(sn)
SXC = {}; lastx = None
for d in DATES:
    lastx = sx.get(d, lastx if lastx is not None else min(sx.items())[1]); SXC[d] = lastx
k = lambda d: d.replace('-', '')
nxt = lambda d: DATES[DATES.index(d) + 1]
def rows(series, upto): return [{'dt': k(d), 'cur_prc': f'{series[d]:.6f}'} for d in DATES if d <= upto]
SYN = {}; p = 10.0
for d in DATES: SYN[d] = p; p *= 1.01
def member(code, sector, items, since):
    return {'code': code, 'sector': sector, 'since': since, 'card': f'docs/claude/watch-card-{code}-2025-01-01.md', 'triggerSet': code, 'capExempt': False,
            'cardStatus': '수락(리플레이)', 'score': sum(items.values()), 'items': items, 'inputs': {'mcapUsd': 5e10, 's1': '강', 'guideRaised': True}, 's1Basis': 'replay'}
def strong(code, sector, s4, s2g, since='2025-01-01'):
    m = member(code, sector, {'S1': 2, 'S2': 1 + int(s2g), 'S3': 2, 'S4': s4, 'S5': 1, 'S7': 2}, since)
    m['inputs']['guideRaised'] = s2g
    return m
REACT = k(DATES[60])
def init(comp_s4):
    sndk = member('SNDK', 'B9 낸드(리플레이)', {'S1': 1, 'S2': 2, 'S3': 0, 'S4': 0, 'S5': 0, 'S7': 0}, '2025-08-30')
    sndk['inputs'].update(s1='약', guideRaised=True)
    mem = [sndk, strong('M1', 'A1 리플레이', 1, True), strong('M2', 'A3 리플레이', 1, True), strong('M3', 'A4 리플레이', 1, False), strong('M4', 'A5 리플레이', 1, False)]
    comp = strong('COMP', 'A2 경쟁', comp_s4, True); [comp.pop(x) for x in ('since', 'card', 'triggerSet', 'capExempt', 'cardStatus')]; comp['aboveStreak'] = 0
    reg = {'schema': 'watchlist-registry/v1', 'mode': 'proposal', 'proposalRunsLeft': 0, 'slots': 5, 'capUsd': 1e12, 'capExempt': ['MU', 'AMD'], 'minMcapUsd': 5e9,
           'held': [], 'members': mem, 'candidates': [comp], 'excluded': [], 'history': []}
    md = {}
    for m in mem:
        dd = {'bm': 'SOXX', 'reactDate': REACT, 'yoy': 50, 'prevYoy': 40}
        if m['code'] != 'SNDK' and m['items']['S4']: dd['pe'] = 1e-6; dd['peBaseClose'] = 1.0
        md[m['code']] = {'score': m['score'], 'items': m['items'], 'detail': dd, 'inputs': {'s1': m['inputs']['s1'], 'guideRaised': m['inputs']['guideRaised']}, 's1Basis': 'replay'}
    cd = {'bm': 'SOXX', 'reactDate': REACT, 'yoy': 50, 'prevYoy': 40}
    if comp_s4: cd['pe'] = 1e-6; cd['peBaseClose'] = 1.0
    comp['detail'] = cd
    reg['weeklyRun'] = {'date': '2025-08-23', 'memberData': md}
    return reg
def weeks():
    out = []
    for i, d in enumerate(real):
        n = real[i + 1] if i + 1 < len(real) else None
        if (n is None or T.date.fromisoformat(n).isocalendar()[1] != T.date.fromisoformat(d).isocalendar()[1]) and d >= ENTRY: out.append(d)
    return out
def run(py, reg, d, comp_has_card=True):
    W = tempfile.mkdtemp()
    for code, ser in (('SNDK', SNC), ('SOXX', SXC), ('GRID', SXC), ('M1', SYN), ('M2', SYN), ('M3', SYN), ('M4', SYN), ('COMP', SYN)):
        json.dump({'result': {'result_list': rows(ser, d), 'return_code': 0}}, open(f'{W}/{code}.json', 'w'))
    e = [x for x in EARN if x <= d][-1]
    fund = {'SNDK': {'newQuarter': True, 'yoy': 2 if S2[e] >= 1 else 0, 'prevYoy': 1, 'reactDate': k(nxt(e)), 'guideRaised': S2[e] == 2,
                     's1': {0: '없음', 1: '약', 2: '강'}[S1[e]], 's1Basis': 'replay' if S1[e] else ''}}
    ctx = {'cardsMissing': [], 'held': ['ZZZ'], 'kill': [], 'card': {'COMP': {'kill': ['① 리플레이 철회 기준 1', '② 리플레이 철회 기준 2', '③ 리플레이 철회 기준 3'], 'src': ['https://example.com/replay']}} if comp_has_card else {}}
    json.dump(fund, open(f'{W}/fund.json', 'w')); json.dump(ctx, open(f'{W}/ctx.json', 'w'))
    rp = f'{W}/reg.json'; json.dump(reg, open(rp, 'w'), ensure_ascii=False)
    os.makedirs(f'{W}/out'); op = f'{W}/out/watchlist-registry.json'
    today = (T.date.fromisoformat(d) + T.timedelta(days=1)).isoformat()
    pr = subprocess.run([sys.executable, py, W, rp, op, today], capture_output=True, text=True)
    if pr.returncode: raise RuntimeError(pr.stderr[-2000:])
    j = json.loads(pr.stdout.split('\n')[0]); o = json.load(open(op, encoding='utf-8')) if os.path.exists(op) else None
    sc = next(l for l in pr.stdout.split('\n')[1:] if l.startswith('SNDK '))
    return j, o, sc
PEAK = max(c for _, c in sn)
def replay(py, comp_s4, proposal=False):
    reg = init(comp_s4); log = []; prot_weeks = 0
    for d in weeks():
        j, o, sc = run(py, reg, d)
        if o is None: return f'기록 실패 {d}: {j["validation"]}', log, prot_weeks
        log.append((d, sc.split()[3], j['action'][0], (j.get('protect') or {}).get('SNDK', [''])[0]))
        if (j.get('protect') or {}).get('SNDK', [''])[0] == 'active': prot_weeks += 1
        out_ = j['action'][2] == 'SNDK' and j['action'][0] in ('swap', 'remove', 'propose')
        if out_:
            c = SNC[d]; return f"밀려남 {d} 종가 ${c:,.0f}(점수 {sc.split()[3]}), 그 뒤 최고가까지 {max(SNC[x] for x in real if x >= d) / c:.1f}배 / 보호 {prot_weeks}주", log, prot_weeks
        reg = o
    return f'끝까지 유지(마지막 평가 {weeks()[-1]}) / 보호 {prot_weeks}주', log, prot_weeks
if __name__ == '__main__':
    res = {}
    for comp_s4, name in ((0, '경쟁 후보 9점'), (1, '경쟁 후보 10점')):
        if OLD:
            r, _, _ = replay(OLD, comp_s4, proposal=True); print(f'{name} · 현행(보호 없음, 제안 모드 python): {r}')
        r, log, _ = replay(PY, comp_s4); print(f'{name} · v3(자동 모드 + 보호 ⑧): {r}'); res[name] = (r, log)
    for name, (r, log) in res.items():
        keep = {d: a for d, *_ , a in [(x[0], x[1], x[2], x[3]) for x in log]}
        print(name, '2025-11-28 상태:', next((f'{x[1]} {x[2]} 보호={x[3] or "-"}' for x in log if x[0] == '2025-11-28'), '명단 밖'), '| 2026-08-07 상태:', next((f'{x[1]} {x[2]} 보호={x[3] or "-"}' for x in log if x[0] == '2026-08-07'), '명단 밖'))
    json.dump({n: {'result': r, 'weeks': l} for n, (r, l) in res.items()}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'replay-sndk-v3-result.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
