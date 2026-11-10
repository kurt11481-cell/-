# Re-run of the reviewer's bad challengers (review3/work/bad) through the fixed admission. Technical tests only: no outcome is read.
import sys, os, json, subprocess, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__))
BAD = os.path.join(HERE, '..', 'review3', 'work', 'bad')
P = '/mnt/project-files/forecast-model-1110/scripts/inputs/'
CACHE = os.path.join(HERE, '..', 'fm2_cache_real')
def one(fn):
    outp = os.path.join(HERE, 'bad_out', fn[:-3] + '.json')
    cmd = [sys.executable, '-I', '-B', os.path.join(HERE, 'scripts', 'fm3_shadow.py'), 'admit', os.path.join(BAD, fn), P + 'yh2', P + 'yh',
           os.path.join(HERE, '..', 'review3', 'work', 'bad_extra'), '2026-11-06', outp]
    if fn[:3] in GRID:
        cmd += ['--cache', CACHE, '--jobs', '2']
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3000)
    rep = json.load(open(outp)) if os.path.exists(outp) else None
    return fn, p.returncode, (p.stderr.strip().splitlines() or [''])[-1][:200], rep
GRID = set(sys.argv[1].split(',')) if len(sys.argv) > 1 else set()
files = sorted(f for f in os.listdir(BAD) if f.endswith('.py'))
with cf.ThreadPoolExecutor(2) as ex:
    for fn, rc, err, rep in ex.map(one, files):
        if rep is None:
            print('%-28s rc=%s NO REPORT %s' % (fn, rc, err), flush=True); continue
        T = rep['tests']
        fails = [k for k, v in T.items() if not v['pass']]
        detail = '; '.join(T['static']['refused'])[:110] if 'static' in fails else json.dumps({k: {a: b for a, b in T[k].items() if a != 'pass'} for k in fails})[:260]
        print('%-28s PASS=%-5s failed=%s %s' % (fn, rep['pass'], fails, detail), flush=True)
