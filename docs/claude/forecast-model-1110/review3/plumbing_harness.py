# Plumbing test of the fixed layer-3 code on real history with two throw-away dummy challengers.
# Pretend forward start 2022-01-03; one run stands in for about 250 weekly runs. Its scores mean nothing for vixr.
import sys, os, json, shutil
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, '..', 'l3fix', 'scripts')                 # the scratch fix set
I = '/mnt/project-files/forecast-model-1110/scripts/inputs'
sys.path.insert(0, S)
import fm2, fm2_weekly, fm3_shadow, fm3_weekly
fm3_shadow.FORWARD_START = '2022-01-03'            # plumbing test only: pretend the forward window began in 2022
fm3_shadow.ISSUE_MAX_DAYS = 10 ** 5                # plumbing test only: one run stands in for 250 weekly runs
d = os.path.join(HERE, 'L3'); pool = I + '/yh2'; rates = I + '/yh'; extra = I + '/yh'; asof = '2026-11-06'
cache = os.path.join(HERE, 'cache')                # links to the staged real cache + the hash of the inputs it was built from
if sys.argv[1] == 'setup':
    open(os.path.join(cache, 'INPUTS.sha256'), 'w').write(fm2_weekly.inputs_digest(pool, rates) + '\n')
    menu_src = {m: open(os.path.join(d, 'menu', m + '.py')).read() for m in ('m1dup', 'widefwd')}
    shutil.rmtree(d); os.makedirs(os.path.join(d, 'menu'))
    fm3_weekly.cmd_init(d, today='2021-12-30')
    for m, src in menu_src.items():
        open(os.path.join(d, 'menu', m + '.py'), 'w').write(src)
    json.dump({'method': 'plumbing test', 'coverage': {'20': 0.95, '60': 0.95}}, open(os.path.join(HERE, 'chk.json'), 'w'))
    fm3_weekly.cmd_interval_check(d, os.path.join(HERE, 'chk.json'))
    menu = [{'menu_id': 'm1dup', 'module': 'm1dup.py', 'finding': 'D1', 'kind': 'history', 'judged_horizons': [20, 60]},
            {'menu_id': 'widefwd', 'module': 'widefwd.py', 'finding': 'D2', 'kind': 'forward', 'judged_horizons': [20]}]
    for e in menu:
        e['module_sha256'] = fm3_weekly.sha(os.path.join(d, 'menu', e['module']))
    json.dump(menu, open(os.path.join(d, 'menu', 'MENU.json'), 'w'), indent=1)
    for mid in ('m1dup', 'widefwd'):
        c = fm3_weekly.cmd_register(d, mid, pool, rates, extra, asof, cache, today='2022-01-02', jobs=4)
        print('registered', c['id'], c['t0'], c['kind'], c['judged_horizons'], c['judged_pair'], flush=True)
else:
    fm3_weekly.cmd_run(d, pool, rates, extra, asof, cache, os.path.join(HERE, 'chcache'), os.path.join(HERE, 'shadow_test_%s.json' % sys.argv[1]), jobs=4)
    fm3_weekly.open_books(d); print('books OK')
