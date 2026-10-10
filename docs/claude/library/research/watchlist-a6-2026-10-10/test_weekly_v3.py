"""Regression harness for the watchlist weekly python v3 (auto mode + protection rule 8).
Runs the exact heredoc python (new/py3.py) on fixtures built from the real 10/10 registry and real Kiwoom 10/9 candles."""
import json, os, sys, copy, shutil, subprocess, tempfile, re
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY_NEW = os.path.join(S, 'ext', 'py3.py'); PY_OLD = os.path.join(S, 'old', 'py3.py')
REG0 = json.load(open('/mnt/user-data/uploads/코덱스저장소/docs/claude/watchlist-registry.json', encoding='utf-8'))
CTX0 = json.load(open(os.path.join(S, 'wk', 'ctx.json'), encoding='utf-8'))
CAND = os.path.join(S, 'candles')
RESULTS = []

def run(reg, ctx, today='2026-10-17', fund=None, drop=(), synth=None, py=PY_NEW):
    W = tempfile.mkdtemp(dir=os.path.join(S, 'tmp'))
    for f in os.listdir(CAND):
        if f[:-5] not in drop: shutil.copy(os.path.join(CAND, f), W)
    for code, rows in (synth or {}).items():
        json.dump({'result': {'result_list': rows, 'return_code': 0}}, open(os.path.join(W, code + '.json'), 'w'))
    json.dump(ctx, open(os.path.join(W, 'ctx.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    if fund: json.dump(fund, open(os.path.join(W, 'fund.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    rp = os.path.join(W, 'reg_in.json'); json.dump(reg, open(rp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    od = os.path.join(W, 'out'); os.makedirs(od); op = os.path.join(od, 'watchlist-registry.json')
    p = subprocess.run([sys.executable, py, W, rp, op, today], capture_output=True, text=True)
    if p.returncode: raise RuntimeError(p.stderr[-3000:])
    lines = p.stdout.strip().split('\n'); j = json.loads(lines[0])
    out = json.load(open(op, encoding='utf-8')) if os.path.exists(op) else None
    return j, out, lines[1:], od

def check(name, cond, info=''):
    RESULTS.append((name, bool(cond), info)); print(('PASS' if cond else 'FAIL'), name, info if not cond else '')

def R(**kw):
    r = copy.deepcopy(REG0)
    for m in r['members']:
        if m['code'] in kw.get('since', {}): m['since'] = kw['since'][m['code']]
    for c in r['candidates']:
        if c['code'] in kw.get('streak', {}): c['aboveStreak'] = kw['streak'][c['code']]
        if c['code'] in kw.get('sector', {}): c['sector'] = kw['sector'][c['code']]
    for code, sc in kw.get('prevScore', {}).items(): r['weeklyRun']['memberData'][code]['score'] = sc
    if 'protect' in kw: r['weeklyRun']['protect'] = kw['protect']
    if 'members_drop' in kw: r['members'] = [m for m in r['members'] if m['code'] not in kw['members_drop']]; [r['weeklyRun']['memberData'].pop(c, None) for c in kw['members_drop']]
    return r

def C(**kw):
    c = copy.deepcopy(CTX0); c.update(kw); return c

CARD = lambda code: {code: {'kill': ['① 회사 공식 발표로 연간 가이던스 하향', '② 분기 핵심 부문 매출 YoY가 0% 미만(공식)', '③ 백로그·수주잔고가 직전 분기보다 감소(공식)'], 'src': ['https://example.com/ir/q2-release'], 'thesis': '테스트 테제(공식 수치)'}}

# ---- L1: real registry + real candles, old vs new python scoring identical ----
jn, on, ln, _ = run(R(), C())
jo, oo, lo, _ = run(R(), C(), py=PY_OLD)
check('L1 실제 명단 — 변경 없음', jn['action'][0] == 'none' and jn['action'][3] == '변경 없음 — 최약 MU 6점, 기준선 8', jn['action'])
check('L1 기록 통과·mode auto·members 불변', jn['written'] and on['mode'] == 'auto' and on['members'] == REG0['members'] and on['history'] == REG0['history'], jn['validation'])
sc_new = {e['code']: (e['score'], e['items'], e.get('aboveStreak')) for e in on['candidates']}; sc_new.update({k: (v['score'], v['items'], None) for k, v in on['weeklyRun']['memberData'].items()})
sc_old = {e['code']: (e['score'], e['items'], e.get('aboveStreak')) for e in oo['candidates']}; sc_old.update({k: (v['score'], v['items'], None) for k, v in oo['weeklyRun']['memberData'].items()})
check('L1 신·구 python 점수·항목·연속 횟수 동일(20종목)', sc_new == sc_old and len(sc_new) == 20)
md10 = REG0['weeklyRun']['memberData']
check('L1 10/10 기록 점수 재현(관심 5)', all(on['weeklyRun']['memberData'][c]['items'] == md10[c]['items'] for c in md10))
check('L1 10/10 기록 점수 재현(후보 15)', all(e['items'] == next(x for x in REG0['candidates'] if x['code'] == e['code'])['items'] for e in on['candidates']))
check('L1 ETN 분야 한도로 교체 불가·연속 2', next(e for e in on['candidates'] if e['code'] == 'ETN')['aboveStreak'] == 2 and jn['protect'] == {}, jn['protect'])
check('L1 push 없음', jn['push'] is False)

# ---- L2: swap (MU thesis weakened -> no protection) ----
r2 = R(since={'MU': '2026-09-01'}, streak={'AAOI': 1, 'AMD': 1, 'ALAB': 1, 'COHR': 1})
f2 = {'MU': {'s1': '약', 's1Basis': 'test basis'}}
j, o, _, _ = run(r2, C(), fund=f2)
x = j['needCard']
check('L2a 교체 결정 → 새 카드 요청(needCard), 기록은 판단 보류', bool(x) and j['action'][0] == 'hold' and o['members'] == r2['members'], j['action'])
j, o, lines, od = run(r2, C(card=CARD(x)), fund=f2)
check('L2b 카드 있으면 교체 적용', j['action'][:3] == ['swap', x, 'MU'] and j['written'], j['action'])
nm = next(m for m in o['members'] if m['code'] == x)
check('L2b 새 관심 칸: 같은 자리·카드 경로·미수락 초안·since', [m['code'] for m in o['members']] == [x if c == 'MU' else c for c in [m['code'] for m in REG0['members']]] and nm['card'] == f'docs/claude/watch-card-{x}-2026-10-17.md' and nm['cardStatus'].startswith('자동 작성 초안') and nm['since'] == '2026-10-17' and nm['triggerSet'] == x)
check('L2b MU는 후보로, 후보 목록 규칙', [c['code'] for c in o['candidates']] == [c['code'] for c in REG0['candidates'] if c['code'] != x] + ['MU'])
check('L2b history swap 1건(auto, weekly)', o['history'][:-1] == REG0['history'] and o['history'][-1]['action'] == 'swap' and o['history'][-1]['mode'] == 'auto' and o['history'][-1]['by'] == 'weekly')
check('L2b 보호 미적용(S1+S2 편입 때 미만)·push', j['protect'] == {} and j['push'] is True, j['protect'])
cf = os.path.join(od, f'watch-card-{x}-2026-10-17.md'); card = open(cf, encoding='utf-8').read() if os.path.exists(cf) else ''
# integrated check v3.12.2 loader readers (copied)
def secs(txt, pre):
    L = txt.split('\n'); H = [(i, l) for i, l in enumerate(L) if l.startswith('#')]; o_ = []
    for k, (i, l) in enumerate(H):
        t = l.lstrip('#').strip()
        if any(t.startswith(p) for p in pre):
            v = len(l) - len(l.lstrip('#')); jj = next((a for a, b in H[k + 1:] if len(b) - len(b.lstrip('#')) <= v), len(L)); o_ += L[i:jj]
    return '\n'.join(o_)
kl = [l for l in card.split('\n') if 'kill' in l.lower() or '철회 기준' in l]
s13 = secs(card, ['1.', '3.'])
check('L2b 카드 파일: 통합 점검 로더가 1절·3절·kill 줄을 읽음', card.startswith('---\nid: watch-card-') and '## 1.' in s13 and f'| {x}8 |' in s13 and any('①' in l and '②' in l and '③' in l for l in kl), (len(card), kl[:2]))
open(os.path.join(S, 'new', 'sample-card.md'), 'w', encoding='utf-8').write(card)

# ---- L3: 28 days not passed ----
j, o, _, _ = run(R(since={'MU': '2026-10-02'}, streak={'AAOI': 1, 'AMD': 1, 'ALAB': 1, 'COHR': 1}), C(card=CARD(x)), fund=f2)
check('L3 편입 28일 전 → 교체 평가 보류', j['action'][0] == 'none' and '28일 전' in j['action'][3] and j['written'], j['action'])
# ---- L4: first week above threshold ----
j, o, _, _ = run(R(since={'MU': '2026-09-01'}), C(card=CARD(x)), fund=f2)
check('L4 기준선 첫 주(연속 1) → 변경 없음', j['action'][0] == 'none' and j['written'], j['action'])
# ---- L5: idempotent next week after swap ----
j5, o5, _, _ = run(o2 := run(r2, C(card=CARD(x)), fund=f2)[1], C(), today='2026-10-24')
check('L5 교체 다음 주 재실행 → 추가 변경 없음(1건 한도·새 종목 28일 전)', j5['action'][0] == 'none' and o5['history'] == o2['history'] and j5['written'], j5['action'])
# ---- L6: hold dedup ----
j, o, _, _ = run(R(), C(), drop=('MU',))
check('L6a 관심 가격 실패 → 판단 보류 + push', j['action'][0] == 'hold' and j['push'] is True and j['written'] and o['members'] == REG0['members'], j['action'])
j, o, _, _ = run(o, C(), drop=('MU',), today='2026-10-24')
check('L6b 같은 판단 보류 반복 → push 없음', j['action'][0] == 'hold' and j['push'] is False, j['action'])
# ---- L7: kill ----
j, o, _, _ = run(R(), C(kill=['BE']))
check('L7 철회 기준 공식 확인 → 제외(remove), excluded 추가, 후보 아님', j['action'][:3] == ['remove', '', 'BE'] and 'BE' not in [m['code'] for m in o['members']] and o['excluded'][-1]['code'] == 'BE' and 'BE' not in [c['code'] for c in o['candidates']] and o['history'][-1]['action'] == 'remove' and j['push'], j['action'])
# ---- L8: held ----
j, o, _, _ = run(R(), C(held=['MVLL', 'SOXL', 'NBIS', 'PWR']))
check('L8 보유 전환 → 제외, excluded·후보 변화 없음', j['action'][:3] == ['remove', '', 'PWR'] and o['excluded'] == REG0['excluded'] and [c['code'] for c in o['candidates']] == [c['code'] for c in REG0['candidates']], j['action'])
# ---- L9: rule 6 fail ----
j, o, _, _ = run(r2, C(rule6Fail={x: '공식 자료에서 부문 매출 확인 불가'}), fund=f2)
check('L9 규칙 ⑥ 못 채움 → 판단 보류, 관심 불변', j['action'][0] == 'hold' and '못 채움' in j['action'][3] and o['members'] == r2['members'], j['action'])
# ---- L10: member cap breach ----
r10 = R(); next(m for m in r10['members'] if m['code'] == 'DELL')['inputs']['mcapUsd'] = 2e12
j, o, _, _ = run(r10, C())
check('L10 관심 종목 시총 상한 초과 → 판단 보류', j['action'][0] == 'hold' and '시총 상한' in j['action'][3], j['action'])
# ---- L11: card path missing ----
j, o, _, _ = run(R(), C(cardsMissing=['PWR']))
check('L11 카드 경로 없음 → 판단 보류', j['action'][0] == 'hold' and '카드 경로 없음 PWR' in j['action'][3], j['action'])
# ---- L12: integrated-check record unavailable ----
c12 = {'cardsMissing': [], 'killUnknown': True}
j, o, _, _ = run(R(), c12)
check('L12 통합 점검 기록 미접근 → flag 후 진행(held는 명단 파일 값)', j['action'][0] == 'none' and any('강제 제외 확인 불가' in f for f in j['flags']) and j['written'], j['flags'])
# ---- L13: validation failure ----
r13 = R(); next(c for c in r13['candidates'] if c['code'] == 'COHR')['items']['S3'] = 3
j, o, _, _ = run(r13, C(), drop=('COHR',))
check('L13 점수 형식 위반 → 기록 안 함(written false)', j['written'] is False and o is None and any('COHR' in v for v in j['validation']), j['validation'])
# ---- L14: benchmark ETF failure ----
j, o, _, _ = run(R(), C(), drop=('GRID',))
check('L14 기준 ETF 가격 실패 → 판단 보류', j['action'][0] == 'hold' and '기준 ETF' in j['action'][3], j['action'])
# ---- L15: fill empty slot ----
r15 = R(members_drop=['LITE'])
j, o, _, _ = run(r15, C())
y = j['needCard']
j, o, _, _ = run(r15, C(card=CARD(y)))
check('L15 빈 칸 채우기 → add(카드 필수), 분야 한도 지킴', j['action'][:2] == ['add', y] and y != 'ETN' and [m['code'] for m in o['members']][-1] == y and o['history'][-1]['action'] == 'add', j['action'])
# ---- L16: cycle sector candidate is incoming -> hold ----
r16 = R(members_drop=['LITE'], sector={y: 'B1 스토리지'})
j, o, _, _ = run(r16, C(card=CARD(y)))
check('L16 사이클 업종 의심 후보 편입 → 판단 보류 + flag', j['action'][0] == 'hold' and '사이클 업종' in j['action'][3] and any('사이클 업종 의심' in f for f in j['flags']), j['action'])

# ---- Protection ----
rp = R(since={'MU': '2026-09-01'}, sector={'ETN': 'A9 테스트'})
j, o, _, _ = run(rp, C(card=CARD('ETN')))
check('P1 보호 시작: MU 가격만 하락(S1+S2 유지) → 교체 대신 조정 중', j['action'][0] == 'none' and 'MU 조정 중' in j['action'][3] and j['protect'].get('MU', [None])[0] == 'active' and o['members'] == rp['members'], (j['action'], j['protect']))
check('P1 보호 기간 = 13주 상한 2027-01-16, S7 기준 반응일 기록', o['weeklyRun']['protect']['MU']['cap'] == '2027-01-16' and o['weeklyRun']['protect']['MU']['s7Base'] == '20261001' and o['weeklyRun']['protect']['MU']['entryS12'] == 4, o['weeklyRun']['protect'])
p1 = o
j, o, _, _ = run(p1, C(card=CARD('ETN')), today='2026-10-24')
check('P2 보호 유지(압력 지속) → 변경 없음, 보호 시작일 유지', j['action'][0] == 'none' and o['weeklyRun']['protect']['MU']['start'] == '2026-10-17' and o['weeklyRun']['protect']['MU']['status'] == 'active', (j['action'], j['protect']))
fP3 = {'BE': {'s1': '없음', 's1Basis': ''}}
rP3 = R(since={'MU': '2026-09-01', 'BE': '2026-09-01'}, sector={'ETN': 'A9 테스트'}, prevScore={'BE': 7})
j, o, _, _ = run(rP3, C(card=CARD('ETN')), fund=fP3)
check('P3 보호 중 종목 건너뛰고 다음 약한 종목(BE, 테제 약화) 교체 — 압력원(ETN)이 관심으로 들어가 MU 보호 상태는 정리', j['action'][:3] == ['swap', 'ETN', 'BE'] and '보호 중' in j['action'][3] and 'MU 조정 중' in j['action'][3] and 'MU' not in j['protect'], (j['action'], j['protect']))
rP3b = R(since={'MU': '2026-09-01', 'BE': '2026-09-01'}, sector={'ETN': 'A9 테스트'})
j, o, _, _ = run(rP3b, C(card=CARD('ETN')), fund=fP3)
check('P3b 다음 약한 종목은 2주 연속(+2) 따로 확인 — 지난주 미충족이면 교체 안 함', j['action'][0] == 'none' and j['protect']['MU'][0] == 'active', j['action'])
j, o, _, _ = run(p1, C(card=CARD('ETN')), today='2026-10-24', fund={'MU': {'newQuarter': True, 'reactDate': '20260924'}})
check('P4 S7 재측정(새 반응일·10세션 경과) → 보호 해제 → 교체', j['action'][:3] == ['swap', 'ETN', 'MU'] and 'MU' not in j['protect'], (j['action'], j['protect']))
p5 = copy.deepcopy(p1); p5['weeklyRun']['protect']['MU'].update(start='2026-07-01', cap='2026-09-30')
j, o, _, _ = run(p5, C(card=CARD('ETN')), today='2026-10-24')
check('P5 13주 상한 지남 → 보호 끝 → 교체(같은 압력 구간에서 재보호 없음)', j['action'][:3] == ['swap', 'ETN', 'MU'], (j['action'], j['protect']))
p5b = copy.deepcopy(p5); p5b['weeklyRun']['protect']['MU'].update(status='ended', endReason='13주 상한')
j, o, _, _ = run(p5b, C(card=CARD('ETN'), rule6Fail={'ETN': 'x'}), today='2026-10-24')
check('P5b 보호 끝난 뒤 판단 보류(규칙 ⑥)여도 상태는 이어짐(ended 유지)', j['action'][0] == 'hold' and o['weeklyRun']['protect']['MU']['status'] == 'ended', o['weeklyRun']['protect'] if o else None)
j, o, _, _ = run(p1, C(kill=['MU'], card=CARD('ETN')), today='2026-10-24')
check('P6 kill 우선 → 보호 중이어도 강제 제외', j['action'][:3] == ['remove', '', 'MU'] and 'MU' not in j['protect'], (j['action'], j['protect']))
p7 = copy.deepcopy(p1); p7['candidates'] = [c for c in p7['candidates'] if c['code'] != 'ETN']
j, o, _, _ = run(p7, C(), today='2026-10-24')
check('P7 압력 사라짐(MU+2 이상 후보 없음) → 보호 상태 삭제', j['action'][0] == 'none' and j['protect'] == {}, j['protect'])
p7b = copy.deepcopy(p1); [c.update(sector='A1') for c in p7b['candidates'] if c['code'] == 'ETN']
j, o, _, _ = run(p7b, C(), today='2026-10-24')
check('R7 분야 한도·입장 조건으로만 잠시 막힌 압력 → 보호 기록 유지(13주 상한 재시작 없음)', j['action'][0] == 'none' and j['protect'].get('MU', [None, None])[:2] == ['active', '2026-10-17'], j['protect'])
j, o, _, _ = run(p1, C(card=CARD('ETN')), today='2026-10-24', fund={'MU': {'s1': '약', 's1Basis': 'test'}})
check('P8 보호 중 S1+S2 하락 → 보호 해제 → 교체', j['action'][:3] == ['swap', 'ETN', 'MU'], (j['action'], j['protect']))
# P9 all protected: synthetic falling candles for all members, strong candidate ETN (A9)
mu = json.load(open(os.path.join(CAND, 'MU.json')))['result']['result_list']
dates = sorted(r['dt'] for r in mu)
def falling(p0):
    rows = []; p = p0
    for d in dates: rows.append({'dt': d, 'cur_prc': f'{p:.4f}'}); p *= 0.997
    return rows
rp9 = R(since={c: '2026-09-01' for c in ['MU', 'BE', 'DELL', 'PWR', 'LITE']}, sector={'ETN': 'A9 테스트'}, prevScore={c: 4 for c in ['MU', 'BE', 'DELL', 'PWR', 'LITE']})
syn = {c: falling(100.0) for c in ['MU', 'BE', 'DELL', 'PWR', 'LITE']}
j, o, ln9, _ = run(rp9, C(card=CARD('ETN')), synth=syn)
check('P9 전원 보호 → 변경 없음(전원 보호 중)', j['action'][0] == 'none' and '전원 보호' in j['action'][3] and len(j['protect']) == 5, (j['action'][3][:200], j['protect']))
# ---- reviewer findings ----
r1 = R(since={'MU': '2026-09-01'}, streak={'AAOI': 2, 'AMD': 1, 'ALAB': 1, 'COHR': 1})
j, o, _, _ = run(r1, C(card=CARD('AAOI')), fund=f2, drop=('AAOI',))
check('R1 들어올 종목 이번 주 일봉 없음 → 지난 값으로 편입하지 않음(판단 보류)', j['action'][0] == 'hold' and j['action'][1] == 'AAOI' and '일봉 없음' in j['action'][3] and o['members'] == r1['members'], j['action'])
j, o, _, _ = run(p1, C(card=CARD('ETN')), today='2026-10-24', fund={'MU': {'newQuarter': True, 'reactDate': '20261023'}})
check('R2 새 반응일 봉이 아직 없으면 보호 해제 안 함(S7 재측정 아님)', j['action'][0] == 'none' and j['protect'].get('MU', [None])[0] == 'active', (j['action'], j['protect']))
r2b = R(since={'MU': '2026-09-01'}, streak={'AAOI': 1, 'AMD': 1, 'ALAB': 1, 'COHR': 1})
j, o, _, _ = run(r2b, C(card=CARD('ETN')), fund={'MU': {'s1': '약', 's1Basis': 'test basis', 'newQuarter': True, 'reactDate': '20261023'}})
check('R2b 나갈 종목 S7 확인 필요(반응일 봉 없음) → 확인 안 된 0점으로 교체하지 않음', j['action'][0] == 'hold' and 'S7 확인 필요' in j['action'][3], j['action'])
j, o, _, _ = run(r2, C(card={x: {'kill': ['확인 필요'] * 3, 'src': ['http://x']}}), fund=f2)
check('R3 자리표시 카드(확인 필요·http) 거부 → needCard 판단 보류', j['action'][0] == 'hold' and j['needCard'] == x, j['action'])
j, o, _, _ = run(R(), C(kill=['BE', 'DELL']))
check('R4a 철회 2건 → 1건 제외 + 나머지 flag·pendingKill 기록', j['action'][2] == 'BE' and any('DELL' in f for f in j['flags']) and 'DELL' in o['weeklyRun']['pendingKill'], (j['action'], j['flags']))
j, o, _, _ = run(o, C(), today='2026-10-24')
check('R4b 다음 주 통합 점검 신호가 없어도 pendingKill로 제외', j['action'][:3] == ['remove', '', 'DELL'] and o['excluded'][-1]['code'] == 'DELL' and o['weeklyRun']['pendingKill'] == {}, j['action'])
j, o, lines, _ = run(r2, C(card=CARD(x)), fund=f2)
codes = [l.split()[0] for l in lines if l.strip()]
check('R5 교체 주 점수표: 들어온 종목 1줄(관심)·나간 종목 1줄(후보)·총 20줄', codes.count(x) == 1 and codes.count('MU') == 1 and len(codes) == 20 and any(l.startswith(x + ' 관심') for l in lines) and any(l.startswith('MU 후보') for l in lines), codes)
p6 = copy.deepcopy(p1); p6['weeklyRun']['protect']['MU'].pop('entryS12')
j, o, _, _ = run(p6, C(card=CARD('ETN')), today='2026-10-24')
check('R6 보호 기록 형식 오류 → 멈추지 않고 보호 끝(교체 규칙대로)', j['written'] and j['action'][:3] == ['swap', 'ETN', 'MU'], (j['action'], j['protect']))
print('\nSUMMARY', sum(r[1] for r in RESULTS), '/', len(RESULTS), 'passed')
json.dump([{'name': n, 'pass': p, 'info': str(i)[:300]} for n, p, i in RESULTS], open(os.path.join(S, 'new', 'regression-results.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
