"""qqq-reg B H1 desk test (no Kiwoom, web, push, dashboard or scheduled run; copies only).
python3 -I h1_test.py <old_rules> <old_loader>   (run from this folder)"""
import hashlib, os, re, subprocess, sys, tempfile, json
OLD_R, OLD_L = sys.argv[1], sys.argv[2]
NEW_R = 'integrated-check-prompt-v3.12.15-2026-11-12.txt'
NEW_L = 'pending-qqq-b-1112/integrated-check-daily.txt'
res = []
def ok(name, cond, note=''):
    res.append((name, bool(cond))); print(('PASS ' if cond else 'FAIL ') + name + (' — ' + note if note else ''))
o = open(OLD_R, encoding='utf-8').read().split('\n'); n = open(NEW_R, encoding='utf-8').read().split('\n')
changed = [i + 1 for i, (a, b) in enumerate(zip(o, n)) if a != b]
ok('T1 rules: same line count, only lines 1·50·54·81·99·116·133·134·161·332 change', len(o) == len(n) and changed == [1, 50, 54, 81, 99, 116, 133, 134, 161, 332], str(changed))
def is_subseq(a, b):
    it = iter(b); return all(ch in it for ch in a)
GONE = '3배 비중이 10% 이하면 이 줄을 쓰지 않는다.'
ok('T1b rules: changed lines only insert text, except line 161 where the one sentence "'+GONE+'" is replaced and line 133 particle 은→는',
   all(is_subseq(o[i-1].replace(GONE, '') if i == 161 else o[i-1].replace('DRAM은 제외', 'DRAM 제외') if i == 133 else o[i-1], n[i-1]) for i in changed) and GONE not in n[160] and GONE in o[160])
ol = open(OLD_L, encoding='utf-8').read(); nl = open(NEW_L, encoding='utf-8').read()
back = nl.split(' / ', 1)[1] if nl.startswith('v3.12.15-L+R2 (') else nl
back = back.replace('integrated-check-prompt-v3.12.15-2026-11-12.txt', 'integrated-check-prompt-v3.12.13-2026-11-06.txt')
back = back.replace('지수 ETF SOXL·TQQQ·DRAM·QQQ 제외', '지수 ETF SOXL·TQQQ·DRAM 제외').replace("v3.12.15-L+R2'", "v3.12.14-L+R2'")
back = re.sub(r"h=='[0-9a-f]{64}'", "h=='3f87de2b831bfa98f28087af9b4f7c21bb4cb656d8b90b05b430bd736209907c'", back)
back = back.replace("('build','finalize','410027099cf987643ed358cc8b810a888216d7f6ab49a71c65c9ec6cea0264ec')", "('build','finalize','961984520462901dc337ac7cf5651e79096b2d5183028803bef908a767df4a9a')")
ok('T2 loader: undoing the 6 intended edits gives v3.12.14-L+R2 byte for byte', back == ol)
blocks = re.findall(r"python3 - <<'PY'\n(.*?)\nPY", nl, re.S)
home = tempfile.mkdtemp(); dc = os.path.join(home, 'mnt', '코덱스저장소', 'docs', 'claude'); os.makedirs(os.path.join(dc, 'scheduled-prompts'))
os.symlink(os.path.abspath(NEW_R), os.path.join(dc, NEW_R)); os.symlink(os.path.abspath(NEW_L), os.path.join(dc, 'scheduled-prompts', 'integrated-check-daily.txt'))
env = dict(os.environ, HOME=home)
r1 = subprocess.run([sys.executable, '-'], input=blocks[0], capture_output=True, text=True, env=env).stdout
ok('T3 loader step 1 rules hash check on the new rules file', 'MATCH' in r1 and 'MISMATCH' not in r1, r1.strip()[:120])
r2 = subprocess.run([sys.executable, '-'], input=blocks[1], capture_output=True, text=True, env=env).stdout
ok('T4 loader build/finalize section hash check', r2.count('MATCH') == 2 and 'MISMATCH' not in r2, ' | '.join(l for l in r2.splitlines() if 'MATCH' in l))
src = [l for l in n if "k not in ('MVLL','SOXL','TQQQ','DRAM','QQQ')" in l][0]
osrc = [l for l in o if "k not in ('MVLL','SOXL','TQQQ','DRAM')" in l][0]
def h_of(line, holdings):
    d = tempfile.mkdtemp() + '/'; os.makedirs(d + 'stock-strategy-system')
    json.dump({'holdings': holdings}, open(d + 'stock-strategy-system/portfolio_state.json', 'w'))
    g = {'json': json, 'R': d}; exec('def _h():\n' + line + '\n    except Exception: return set()', g); return g['_h']()
today = {'BE': 1, 'LITE': 1, 'MU': 1, 'PLTR': 1, 'SOXL': 1, 'MVLL': 1}
withq = dict(today, QQQ=1)
ok('T5 81행 _h(): today (no QQQ) old == new', h_of(src, today) == h_of(osrc, today), str(sorted(h_of(src, today))))
ok('T5b 81행 _h(): with QQQ held, new drops QQQ, old keeps it', 'QQQ' not in h_of(src, withq) and 'QQQ' in h_of(osrc, withq))
def line_a(t3, gates, E, c, q, qqq_w, rows=(), known=True):
    """Spec of 161행 'already decided' for 3x weight <= 10% (v3.12.15, fractions); returns the branch label."""
    if t3 > 0.10: return '3x-branch(v3.12.13, unchanged)'
    if not known: return 'hold(확인 필요)'
    r = min(1.55 - E - 0.03, 0.40 - qqq_w)
    if c < q: return 'Q4 none'
    if not all(gates): return 'Q2 wait'
    card_ready = any(ok and sym != 'QQQ' and mult != 3 for sym, mult, ok in rows)  # rows: (symbol, multiplier, cells 1345 all ok)
    if card_ready: return 'funding-first(QQQ 다시 사기 보류)'
    if r < q: return 'Q3 no-room'
    return 'Q1 buy max %.1f%%' % (100 * min(c, r))
cases = [((0.3665, (True, False, False), 2.004, 0.02, 0.01, 0), '3x-branch(v3.12.13, unchanged)'),
         ((0.10, (True, False, True), 1.35, 0.25, 0.01, 0), 'Q2 wait'),
         ((0.10, (True, True, False), 1.35, 0.25, 0.01, 0), 'Q2 wait'),
         ((0.10, (True, True, True), 1.35, 0.25, 0.01, 0), 'Q1 buy max 17.0%'),
         ((0.10, (True, True, True), 1.40, 0.05, 0.01, 0.20), 'Q1 buy max 5.0%'),
         ((0.10, (True, True, True), 1.515, 0.25, 0.01, 0), 'Q3 no-room'),
         ((0.10, (True, True, True), 1.30, 0.25, 0.01, 0.395), 'Q3 no-room'),
         ((0.10, (True, True, True), 1.40, 0.005, 0.01, 0.22), 'Q4 none'),
         ((0.10, (True, True, True), 1.30, 0.20, 0.01, 0.15, (('BE', 1, True),)), 'funding-first(QQQ 다시 사기 보류)'),
         ((0.10, (True, True, True), 1.30, 0.20, 0.01, 0.15, (('SOXL', 3, True), ('QQQ', 1, True))), 'Q1 buy max 20.0%')]
got = [line_a(*a) for a, _ in cases]
ok('T6 161행 branch spec on 10 states (today = 3x 36.65% → unchanged 3x line)', got == [e for _, e in cases], str(got))
ok('T7 size: rules +%d B, loader +%d B' % (os.path.getsize(NEW_R) - os.path.getsize(OLD_R), os.path.getsize(NEW_L) - os.path.getsize(OLD_L)), True)
print('H1', 'PASS' if all(v for _, v in res) else 'FAIL', sum(v for _, v in res), '/', len(res))
