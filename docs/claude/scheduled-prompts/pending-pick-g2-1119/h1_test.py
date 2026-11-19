"""pick-skill-1119 G2 (161행 재원 우선) H1 desk test — copies only: no Kiwoom, web, push, dashboard, scheduled run, repo write.
python3 -I h1_test.py <old_rules v3.12.16> <old_loader v3.12.16-L+R2> <research-records dir>   (run from docs/claude)
161행은 무인 실행 모델이 읽는 문장이라 코드로 돌릴 수 없다. 그래서 T5~T7은 옛·새 문장을 그대로 옮긴 참고 판정 함수로
관문 날 갈래를 재현한다(문장 해석 자체의 시험은 아님 — 제안서 4절 약점, 문장 읽기 책상 시험은 4절 별도)."""
import os, re, json, subprocess, sys, tempfile
OLD_R, OLD_L, RR = sys.argv[1], sys.argv[2], sys.argv[3]
P = 'scheduled-prompts/pending-pick-g2-1119/'
NEW_R = 'integrated-check-prompt-v3.12.17-2026-11-19.txt'
if not os.path.exists(NEW_R): NEW_R = P + NEW_R
NEW_L = P + 'integrated-check-daily.txt'
res = []
def ok(name, cond, note=''):
    res.append((name, bool(cond))); print(('PASS ' if cond else 'FAIL ') + name + (' — ' + note if note else ''))

# ---- T1: rules file — only lines 1 and 161 change, by insertion of the planned text ----
o = open(OLD_R, encoding='utf-8').read().split('\n'); n = open(NEW_R, encoding='utf-8').read().split('\n')
changed = [i + 1 for i, (a, b) in enumerate(zip(o, n)) if a != b]
ok('T1 rules: same line count, only lines 1·161 change', len(o) == len(n) and changed == [1, 161], str(changed))
ok('T1a rules line 1: old line kept whole after the new header', n[0].endswith(' / ' + o[0]) and n[0].startswith('v3.12.17 '))
A = ' 밖 행 가운데 ①③④⑤가 모두 통과인 행이 있으면 Q1·Q3 대신'
ok('T1b rules line 161: exactly one old phrase replaced, text before and after it identical',
   o[160].count(A) == 1 and n[160].startswith(o[160].split(A)[0]) and n[160].endswith(o[160].split(A)[1]) and A not in n[160])
mid = n[160][len(o[160].split(A)[0]):len(n[160]) - len(o[160].split(A)[1])]
for kw in ('①③④⑤가 모두 통과이면서 ②에 매수 가능 현금 부족 밖의 막힘 사유가 하나도 없는 행', '상품 승인 없음', 'S7 추가 매수 멈춤', '추가 매수 멈춤(S7 …)', '종목 상한', 'R5 추가 매수 멈춤', "'… 없음'은 사유가 아니고", '현금 액수를 적은 것만으로는 막힘 사유가 아니며', '막힘 사유 없이 ② 상태가 확인 필요인 행은 지금처럼 센다', '134행 재원 줄', 'Q1·Q3 대신'):
    ok('T1c new 161 text names: ' + kw, kw in mid)
ok('T1d 134행 ② 정의에 새 문구가 가리키는 사유가 다 있다(상품 승인 없음 · S7 add_recommendations 멈춤 · R5 추가 매수 멈춤 · 매수 가능 현금 — 글자는 실기록 표기에 맞춤)',
   all(k in o[133] for k in ('상품 승인 없음', 'add_recommendations 멈춤', 'R5 추가 매수 멈춤', '매수 가능 현금')))
ok('T1e 이미 정한 일 줄의 Q1~Q4 · 관문 ⓐⓑⓒ · 상한 w 문장은 그대로', all(s in n[160] for s in (
    "관문 = ⓐ QQQ가 ① 정책의 nominal_multipliers", '자리 r = min(1.55 − E − 0.03, 0.4 − QQQ 비중), 상한 w = min(c, r)', 'Q4 c < q면')))

# ---- T2~T4: loader — only header, rules path ×3 and hash change; step 1 / section hash checks pass ----
ol = open(OLD_L, encoding='utf-8').read(); nl = open(NEW_L, encoding='utf-8').read()
back = nl.split(' / ', 1)[1] if nl.startswith('v3.12.17-L+R2 (') else nl
back = back.replace('integrated-check-prompt-v3.12.17-2026-11-19.txt', 'integrated-check-prompt-v3.12.16-2026-11-18.txt')
back = re.sub(r"h=='[0-9a-f]{64}'", "h=='bcee847ac929aaadab01230f9e07500c22f58b4fd45366fd47926533d210f825'", back, count=1)
ok('T2 loader: undoing the intended edits gives v3.12.16-L+R2 byte for byte', back == ol)
blocks = re.findall(r"python3 - <<'PY'\n(.*?)\nPY", nl, re.S)
home = tempfile.mkdtemp(); dc = os.path.join(home, 'mnt', '코덱스저장소', 'docs', 'claude'); os.makedirs(os.path.join(dc, 'scheduled-prompts'))
os.symlink(os.path.abspath(NEW_R), os.path.join(dc, 'integrated-check-prompt-v3.12.17-2026-11-19.txt'))
os.symlink(os.path.abspath(NEW_L), os.path.join(dc, 'scheduled-prompts', 'integrated-check-daily.txt'))
env = dict(os.environ, HOME=home)
r1 = subprocess.run([sys.executable, '-'], input=blocks[0], capture_output=True, text=True, env=env).stdout
ok('T3 loader step 1 rules hash check on the new rules file', 'MATCH' in r1 and 'MISMATCH' not in r1, r1.strip()[:110])
r2 = subprocess.run([sys.executable, '-'], input=blocks[1], capture_output=True, text=True, env=env).stdout
ok('T4 build·finalize·fix1 section hash check (3 MATCH)', r2.count('MATCH') == 3 and 'MISMATCH' not in r2, ' | '.join(l for l in r2.splitlines() if 'MATCH' in l))
def sec(t, a, b):
    x = '\n----- ' + a + ' -----\n'; y = '\n----- ' + b + ' -----'; i = t.rindex(x) + len(x); return t[i:t.index(y, i)]
ok('T4b build·finalize·fix1 bodies identical to v3.12.16-L+R2', all(sec(nl, a, b) == sec(ol, a, b) for a, b in (('build', 'finalize'), ('finalize', 'fix1'), ('fix1', '끝'))))

# ---- T5: reference judgement of the 161 '이미 정한 일' QQQ line, old vs new sentence ----
CASH = '매수 가능 현금 부족'
def counts(row, qqq_held, ver):
    """row = {'code', 'c1','c3','c4','c5': 'ok'|'no'|'unk', 'r2': set of ② block reasons ('' set = 통과, {'확인 필요'} = 확인 필요)}"""
    if row['code'] in ('QQQ', 'SOXL', 'TQQQ'): return False
    if not all(row[k] == 'ok' for k in ('c1', 'c3', 'c4', 'c5')): return False
    if ver == 'old': return True
    if ver == 'new': return row['r2'] - {CASH, '확인 필요'} == set()   # 현금 밖 막힘 사유가 없으면 셈(② 확인 필요도 셈)
    if ver == 'design': return row['r2'] == set() or (row['r2'] == {CASH} and qqq_held)   # 설계 10-3 초안 문구(시험 비교용)
def line(rows, st, ver):  # 161 원문 순서: c·q 못 구함 → 판단 보류, Q4(c<q), Q2(관문 닫힘), 그다음 '재원 우선'이 Q1·Q3만 대신함
    if st.get('c') is None: return 'UNKNOWN'
    if st['c'] < st['q']: return 'Q4'
    if not st['gate']: return 'Q2'
    if any(counts(r, st['qqq_held'], ver) for r in rows): return 'HOLD'
    return 'Q1' if min(st['c'], st['r']) >= st['q'] else 'Q3'
def R(code, r2=(), c1='ok', c3='ok', c4='ok', c5='ok'): return dict(code=code, r2=set(r2), c1=c1, c3=c3, c4=c4, c5=c5)
G = dict(c=0.20, q=0.004, r=0.15, gate=True, qqq_held=False)
cases = [  # name, rows, state overrides, expected old, expected new
    ('1 PLTR ② 상품 승인 없음(살 수 없음)', [R('PLTR', ['상품 승인 없음'])], {}, 'HOLD', 'Q1'),
    ('2 LITE(추가) ② R5 추가 매수 멈춤', [R('LITE', ['R5 추가 매수 멈춤'])], {}, 'HOLD', 'Q1'),
    ('2b BE(추가) ② S7 추가 매수 멈춤', [R('BE', ['S7 추가 매수 멈춤'])], {}, 'HOLD', 'Q1'),
    ('2c MU ② 종목 상한', [R('MU', ['종목 상한'])], {}, 'HOLD', 'Q1'),
    ('3 MU ② 통과(살 수 있음)', [R('MU')], {}, 'HOLD', 'HOLD'),
    ('4 MU ② 현금 부족만 · QQQ 보유(134 재원 줄과 같은 날)', [R('MU', [CASH])], dict(qqq_held=True), 'HOLD', 'HOLD'),
    ('5 MU ② 현금 부족만 · QQQ 없음', [R('MU', [CASH])], dict(c=0.01, q=0.004), 'HOLD', 'HOLD'),
    ('6 MU ② 확인 필요(막힘 사유 없음) — 모르면 바꾸지 않음', [R('MU', ['확인 필요'])], {}, 'HOLD', 'HOLD'),
    ('6b MU ② 확인 필요 + 상품 승인 없음', [R('MU', ['확인 필요', '상품 승인 없음'])], {}, 'HOLD', 'Q1'),
    ('7 MU ② 현금 부족 + 상품 승인 없음', [R('MU', [CASH, '상품 승인 없음'])], {}, 'HOLD', 'Q1'),
    ('8 ①③④⑤ 통과 행 없음', [R('MU', c1='no'), R('DELL', c5='unk')], {}, 'Q1', 'Q1'),
    ('9 Q3 상태(자리 < 1주) + PLTR', [R('PLTR', ['상품 승인 없음'])], dict(r=0.002), 'HOLD', 'Q3'),
    ('10 관문 닫힘 + PLTR — 지금도 Q2', [R('PLTR', ['상품 승인 없음'])], dict(gate=False), 'Q2', 'Q2'),
    ('10b 통과 행 + c < q — 지금도 Q4', [R('MU')], dict(c=0.002), 'Q4', 'Q4'),
    ('10c c를 못 구함 — 판단 보류', [R('MU')], dict(c=None), 'UNKNOWN', 'UNKNOWN'),
    ('10d ① 막힘 + ② 현금 부족만(오독 잡기)', [R('MU', [CASH], c1='no')], dict(qqq_held=True), 'Q1', 'Q1'),
    ('10e PLTR(못 삼) + MU(현금 부족만·QQQ 보유)', [R('PLTR', ['상품 승인 없음']), R('MU', [CASH])], dict(qqq_held=True), 'HOLD', 'HOLD'),
    ('11 SOXL·QQQ 행은 어느 판에서도 세지 않음', [R('SOXL'), R('QQQ')], {}, 'Q1', 'Q1'),
    ('12 PLTR(못 삼) + MU(삼)', [R('PLTR', ['상품 승인 없음']), R('MU')], {}, 'HOLD', 'HOLD'),
]
for name, rows, ov, eo, en in cases:
    st = dict(G, **ov); go, gn = line(rows, st, 'old'), line(rows, st, 'new')
    ok('T5 ' + name, (go, gn) == (eo, en), 'old %s → new %s' % (go, gn))

# ---- T6: no buy-today/sell-tomorrow loop (리뷰 지적 ⓐ) — 3-day walk, MU 1주 > 현금 ≥ QQQ 1주 ----
def walk(ver, days=4):
    st = dict(G, c=0.008, q=0.004, qqq_held=False); out = []
    mu_px = 0.009  # MU 1주 = 계좌의 0.9%, 현금 0.8%
    for _ in range(days):
        cash_short = st['c'] < mu_px
        rows = [R('MU', [CASH] if cash_short else [])]
        ln = line(rows, st, ver)
        sell = st['qqq_held'] and cash_short  # 134행 재원 줄: ② 현금 부족 하나 + ①③④⑤ 통과 + QQQ 보유 → 오늘 QQQ 매도
        out.append(('SELL_QQQ' if sell else '') + ln)
        if sell: st.update(c=st['c'] + 0.004, qqq_held=False)
        elif ln == 'Q1': st.update(c=st['c'] - 0.004, qqq_held=True)
        if not cash_short and ln == 'HOLD': break
    return out
wn, wd = walk('new'), walk('design')
ok('T6 new: no QQQ buy→sell alternation while MU 1주를 못 삼', not any(x == 'Q1' for x in wn), str(wn))
ok('T6b (비교) 설계 초안 문구는 사고팔기가 되풀이됨 — 그래서 QQQ 보유 조건을 뺐다', wd.count('Q1') >= 2 and any(x.startswith('SELL_QQQ') for x in wd), str(wd))

def walk_flip(ver, days=6):  # LITE(추가) R5 멈춤이 하루씩 걸렸다 풀림, 현금은 LITE 1주보다 적음
    st = dict(G, c=0.008, q=0.004, qqq_held=False); out = []
    for d in range(days):
        r5 = d % 2 == 0; cash_short = st['c'] < 0.009
        r2 = set(['R5 추가 매수 멈춤'] if r5 else []) | ({CASH} if cash_short else set())
        ln = line([R('LITE', r2)], st, ver)
        sell = st['qqq_held'] and r2 == {CASH}
        out.append(('SELL_QQQ+' if sell else '') + ln)
        if sell: st.update(c=st['c'] + 0.004, qqq_held=False)
        elif ln == 'Q1': st.update(c=st['c'] - 0.004, qqq_held=True)
    return out
wf, wfo = walk_flip('new'), walk_flip('old')
ok('T6c (공개) ②의 현금 밖 사유가 풀렸다 걸렸다 하면 새 문구는 QQQ 왕복이 생김 — 옛 문구는 내내 보류', wf.count('Q1') >= 2 and all(x == 'HOLD' for x in wfo), 'new %s / old %s' % (wf, wfo))

# ---- T7: real 11/11~11/19 records, gate-day what-if (② 노출·현금 사유와 ⑤를 관문 열림으로 바꿔 봄) ----
GATE_GONE = (r'S7 \d+/\d+ E [\d.]+ ≥ 1\.9 절대 상한\(신규 매수 전부 막힘\)', r'E [\d.]+ ≥ 1\.9 절대 상한', r'S7 신규 매수 멈춤(\(L4·L5\))?',
             r'S7 오래됨\([^)]*\)', r'N [\d.]+', r'R-REC1 열림', r'L4·L5 검토 열림')   # 관문 날엔 모두 풀림(관문 ⓑ·E < 1.52)
NOT_REASON = (r'S7 추가 매수 멈춤 없음', r'(주문 가능 )?현금 \$[\d.]+(\(주문 가능액\))?')   # 부정문 · 현금 액수(관문 날 판 몫 현금은 충분하다고 봄)
BLOCKS = ((r'R5 추가 매수 멈춤(\([^)]*\))?', 'R5 추가 매수 멈춤'), (r'추가 매수 멈춤\(S7 [^)]*\)', 'S7 추가 매수 멈춤'),
          (r'S7 추가 매수 멈춤', 'S7 추가 매수 멈춤'), (r'상품 승인 없음(\(사용자 승인 필요\))?', '상품 승인 없음'))
def reasons(t):
    t = t.split('—', 1)[1] if '—' in t else t; out = set()
    for pat in GATE_GONE + NOT_REASON: t = re.sub(pat, ' ', t)
    for pat, name in BLOCKS:
        if re.search(pat, t): out.add(name); t = re.sub(pat, ' ', t)
    if re.sub(r'[\s·,]', '', t): out.add('UNKNOWN:' + t.strip())
    return out
EXPECT_NEW = {'2026-11-11': [], '2026-11-12': ['MU', 'DELL', 'PWR'], '2026-11-13': ['MU', 'DELL', 'PWR'], '2026-11-14': ['MU', 'DELL', 'PWR'],
              '2026-11-17': ['MU', 'DELL', 'PWR'], '2026-11-18': ['MU', 'DELL', 'PWR'], '2026-11-19': ['DELL']}
summary = []
for day in sorted(EXPECT_NEW):  # v3.12.15(QQQ 줄) 첫 실행 무렵부터 — 그 전 판(10/13~11/07)은 ② 칸 표기가 달라 이 분류기 범위 밖(제안서 4절)
    f = os.path.join(RR, day, 'research-record.json')
    if not os.path.exists(f): ok('T7 %s record exists' % day, False); continue
    rows0 = json.load(open(f, encoding='utf-8'))['integrated_check_run']['buyReq']['rows']
    rows = []
    for r in rows0:
        c = r['c']; s = lambda i: c[i]['s'] if c[i]['s'] in ('ok', 'no') else 'unk'
        code = r['code']
        rows.append(R(code, reasons(c[1]['t']), s(0), s(2), s(3), 'ok'))
    held = [x['code'] for x in rows if counts(x, False, 'old')]
    heldn = [x['code'] for x in rows if counts(x, False, 'new')]
    unknown = [x['code'] + str(x['r2']) for x in rows if any(str(y).startswith('UNKNOWN') for y in x['r2'])]
    summary.append('%s old:%s new:%s' % (day, ','.join(held) or '-', ','.join(heldn) or '-'))
    ok('T7 %s what-if: ② 칸 글자를 모두 분류함(모르는 사유 0)' % day, not unknown, str(unknown))
    ok('T7b %s what-if: 새 문구가 보류시키는 행 = 기대 목록' % day, sorted(heldn) == sorted(EXPECT_NEW.get(day, ['?'])), 'old 보류 행 %s → new %s' % (held or '-', heldn or '-'))
print('T7 summary', ' | '.join(summary))
print('H1', sum(1 for _, v in res if v), '/', len(res), 'PASS' if all(v for _, v in res) else 'FAIL')
