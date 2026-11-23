"""ic-record-gaps-1118 H1 desk test (copies only: no Kiwoom, web, push, dashboard, scheduled run, repo write).
python3 -I h1_test.py <old_rules> <old_loader> <research-records dir>   (run from docs/claude)"""
import copy, hashlib, json, os, re, subprocess, sys, tempfile
OLD_R, OLD_L, RR = sys.argv[1], sys.argv[2], sys.argv[3]
NEW_R = 'integrated-check-prompt-v3.12.16-2026-11-18.txt'
NEW_L = 'scheduled-prompts/pending-ic-earnlabel-1118/integrated-check-daily.txt'
if not os.path.exists(NEW_R): NEW_R = 'scheduled-prompts/pending-ic-earnlabel-1118/' + NEW_R
res = []
def ok(name, cond, note=''):
    res.append((name, bool(cond))); print(('PASS ' if cond else 'FAIL ') + name + (' — ' + note if note else ''))
o = open(OLD_R, encoding='utf-8').read().split('\n'); n = open(NEW_R, encoding='utf-8').read().split('\n')
changed = [i + 1 for i, (a, b) in enumerate(zip(o, n)) if a != b]
ok('T1 rules: same line count, only lines 1·133 change', len(o) == len(n) and changed == [1, 133], str(changed))
def subseq(a, b):
    it = iter(b); return all(ch in it for ch in a)
ok('T1b rules: both changed lines only insert text', all(subseq(o[i - 1], n[i - 1]) for i in changed) and n[132].startswith(o[132].split('미공지만으로는')[0]))
ol = open(OLD_L, encoding='utf-8').read(); nl = open(NEW_L, encoding='utf-8').read()
back = nl.split(' / ', 1)[1] if nl.startswith('v3.12.16-L+R2 (') else nl
back = back.replace('integrated-check-prompt-v3.12.16-2026-11-18.txt', 'integrated-check-prompt-v3.12.15-2026-11-12.txt')
back = re.sub(r"h=='[0-9a-f]{64}'", "h=='6d6191f06bf57844641d0df39e0e729cc2f4608d849803ab5f0ff69bfd2b1245'", back)
back = re.sub(r"\('finalize','fix1','(a6bcd6c6[0-9a-f]{56})'\),\('fix1','끝','[0-9a-f]{64}'\)", r"('finalize','끝','\1')", back)
back = back.replace('build·finalize·fix1 스크립트는 지시문 보관본의 build·finalize·fix1 구간을', 'build·finalize 스크립트는 지시문 보관본의 build·finalize 구간을')
back = back.replace('(build·finalize가 MISMATCH면 연구 기록을 쓰지 않고 push. fix1만 MISMATCH면 연구 기록은 그대로 쓰고 4단계 (6)만 하지 않는다)', '(MISMATCH면 연구 기록을 쓰지 않고 push)')
back = back.replace('· 4단계 연구 기록 · ① 칸 맞춤(4단계 (6)) · 알림.', '· 4단계 연구 기록 · 알림.')
back = re.sub(r'  \(6\) \(v3\.12\.16 ① 칸 맞춤.*?\n(?= 결과: "RR OK")', '', back, flags=re.S)
back = re.sub(r'\n----- fix1 -----\n.*?(?=\n----- 끝 -----)', '', back, flags=re.S)
ok('T2 loader: undoing the intended edits gives v3.12.15-L+R2 byte for byte', back == ol)
blocks = re.findall(r"python3 - <<'PY'\n(.*?)\nPY", nl, re.S)
home = tempfile.mkdtemp(); dc = os.path.join(home, 'mnt', '코덱스저장소', 'docs', 'claude'); os.makedirs(os.path.join(dc, 'scheduled-prompts'))
os.symlink(os.path.abspath(NEW_R), os.path.join(dc, 'integrated-check-prompt-v3.12.16-2026-11-18.txt'))
os.symlink(os.path.abspath(NEW_L), os.path.join(dc, 'scheduled-prompts', 'integrated-check-daily.txt'))
env = dict(os.environ, HOME=home)
r1 = subprocess.run([sys.executable, '-'], input=blocks[0], capture_output=True, text=True, env=env).stdout
ok('T3 loader step 1 rules hash check on the new rules file', 'MATCH' in r1 and 'MISMATCH' not in r1, r1.strip()[:110])
r2 = subprocess.run([sys.executable, '-'], input=blocks[1], capture_output=True, text=True, env=env).stdout
ok('T4 build·finalize·fix1 section hash check (3 MATCH)', r2.count('MATCH') == 3 and 'MISMATCH' not in r2, ' | '.join(l for l in r2.splitlines() if 'MATCH' in l))
def sec(t, a, b):
    x = '\n----- ' + a + ' -----\n'; y = '\n----- ' + b + ' -----'; i = t.rindex(x) + len(x); return t[i:t.index(y, i)]
olt = ol.replace('\r\n', '\n')
ok('T4b build and finalize bodies identical to v3.12.15-L+R2', sec(nl, 'build', 'finalize') == sec(olt, 'build', 'finalize') and sec(nl, 'finalize', 'fix1') == sec(olt, 'finalize', '끝'))
FIX = sec(nl, 'fix1', '끝'); fp = os.path.join(tempfile.mkdtemp(), 'fix1.py'); open(fp, 'w', encoding='utf-8').write(FIX)
def run_fix(doc, rec, wrap=False, raw=None):
    d = tempfile.mkdtemp(); g = {'data': doc, 'version': 7, 'id': 'x'} if wrap else doc
    if raw is None: json.dump(g, open(d + '/g.json', 'w', encoding='utf-8'), ensure_ascii=False)
    else: open(d + '/g.json', 'w').write(raw)
    if isinstance(rec, str): open(d + '/r.json', 'w').write(rec)
    else: json.dump(rec, open(d + '/r.json', 'w', encoding='utf-8'), ensure_ascii=False)
    out = subprocess.run([sys.executable, '-I', fp, d + '/g.json', d + '/r.json', d + '/o.json'], capture_output=True, text=True).stdout
    m = re.search(r'FIX1 (\[.*\])', out)
    o = json.load(open(d + '/o.json', encoding='utf-8')) if os.path.exists(d + '/o.json') else None
    return (eval(m.group(1)) if m else out.strip()), o
EXPECT = {'2026-11-13': ['BE', 'LITE', 'MU', 'PLTR', 'PWR'], '2026-11-14': ['BE', 'LITE', 'PLTR'],
          '2026-11-17': ['BE', 'LITE', 'MU', 'PLTR'], '2026-11-18': ['BE', 'LITE', 'MU', 'PLTR', 'PWR']}  # = auto-core compare.json buyReq:*:1 P_EARN_R1_UNVERIFIED_IS_BLACKOUT
for day, exp in EXPECT.items():
    rec = json.load(open(os.path.join(RR, day, 'research-record.json'), encoding='utf-8'))
    doc = rec['integrated_check_run']; doc['core'] = {'meta': {'source': 'auto-core'}}
    for wrap in (True, False):
        fx, out = run_fix(copy.deepcopy(doc), rec, wrap=wrap)
        ok('T5 %s %s: FIX1 equals the core compare blackout set' % (day, 'data wrapper' if wrap else 'top level'), sorted(fx or []) == exp, str(fx))
    ok('T5b %s output holds only buyReq (update payload; core and other fields not sent)' % day, list(out) == ['buyReq'])
    a = copy.deepcopy(doc['buyReq']); b = copy.deepcopy(out['buyReq'])
    for r in a['rows']: r['c'][0] = None
    for r in b['rows']: r['c'][0] = None
    ok('T5c %s only ① cells differ inside buyReq' % day, a == b)
    rows = {r['code']: r['c'][0] for r in out['buyReq']['rows']}
    ok('T5d %s fixed cells read 막힘 and others untouched' % day, all(rows[k]['s'] == 'no' and rows[k]['t'].startswith('막힘 — 실적 일정') for k in exp)
       and all(rows[r['code']] == r['c'][0] for r in doc['buyReq']['rows'] if r['code'] not in exp))
    d2 = copy.deepcopy(doc); d2['buyReq'] = out['buyReq']; fx2, _ = run_fix(d2, rec)
    ok('T5e %s second run is a no-op (FIX1 [])' % day, fx2 == [])
row = lambda k, s='ok': {'code': k, 'name': k, 'c': [{'s': s, 't': 'x'}, {'s': 'no', 't': 'y'}]}
base = {'buyReq': {'rows': [row('SOXL'), row('QQQ'), row('TQQQ'), row('DRAM'), row('MVLL'), row('DELL'), row('CRWD'), row('NBIS', 'unk'), row('MU', 'no'), row('PWR'), row('BE')]}}
R = {'evaluation_session': '2026-11-17', 'earnings': {'DELL': {'status': 'VERIFIED', 'announcement_session': '2026-11-24'}, 'MVLL': {'status': 'NOT_ANNOUNCED'}, 'CRWD': {'status': 'verified'}, 'BE': {'status': 'VERIFIED', 'announcement_session': '2026-11-14'}}}
fx, out = run_fix(copy.deepcopy(base), R)
ok('T6 synthetic: index ETFs skipped, future VERIFIED/NOT_ANNOUNCED kept, lower-case/missing/stale VERIFIED → 막힘, unk/no untouched', fx == ['CRWD', 'PWR', 'BE'], str(fx))
ok('T6a stale VERIFIED reads 지남, missing reads 확인 못 함', [r['c'][0]['t'] for r in out['buyReq']['rows'] if r['code'] in ('BE', 'PWR')] == ['막힘 — 실적 일정 확인 못 함(코어와 같음, 매수만 막음)', '막힘 — 실적 일정 지남·금지 구간일 수 있음(코어와 같음, 매수만 막음)'])
fx, _ = run_fix(copy.deepcopy(base), {'evaluation_session': '2026-11-17', 'earnings': {}})
ok('T6b empty earnings: every ok non-index row → 막힘', fx == ['MVLL', 'DELL', 'CRWD', 'PWR', 'BE'], str(fx))
fx, _ = run_fix(copy.deepcopy(base), {'earnings': {'DELL': {'status': 'VERIFIED', 'announcement_session': '2026-11-24'}}})
ok('T6c no evaluation_session: VERIFIED cannot be dated → 막힘 (fail closed)', 'DELL' in fx, str(fx))
fx, _ = run_fix(copy.deepcopy(base), {'evaluation_session': '2026-11-17', 'earnings': []})
ok('T6d earnings not a dict: treated as empty', fx == ['MVLL', 'DELL', 'CRWD', 'PWR', 'BE'], str(fx))
for name, doc, raw in (('no buyReq', {'headline': 'x'}, None), ('rows not list', {'buyReq': {'rows': 'x'}}, None), ('data null', {'data': None, 'version': 3}, None),
                       ('meta only top level', {'version': 3, 'id': '2026-11-18'}, None), ('not json', None, '{oops')):
    fx, out = run_fix(doc, R, raw=raw)
    ok('T7 bad get file (%s): FIX1-NOROWS, no output file' % name, str(fx).startswith('FIX1-NOROWS') and out is None, str(fx))
fx, out = run_fix(copy.deepcopy(base), '{oops')
ok('T7b unreadable research record: FIX1-BADREC, no output file', str(fx).startswith('FIX1-BADREC') and out is None, str(fx))
fx, _ = run_fix({'buyReq': {'rows': [1, {'code': 'BE'}, {'code': 'BE', 'c': []}]}}, R)
ok('T7c malformed rows: no crash, nothing fixed', fx == [], str(fx))
ok('T8 fix1 has no network, device, write other than argv[3]', not re.search(r'urllib|requests|socket|subprocess|os\.|open\([^)]*\'w\'', FIX.replace("open(sys.argv[3],'w'", '')))
print('H1', sum(1 for _, v in res if v), '/', len(res), 'PASS' if all(v for _, v in res) else 'FAIL')
