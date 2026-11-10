# How often does the fixed rule (interim look from 65 weeks at 20 days, none at 60 days) drop a dummy challenger before the
# minimum sample, and how often does a dummy pass? Real history, the reviewer's throw-away dummies (review3/work/dm, pk):
# the judged window is a rolling historical stretch, T0 every second Friday, looks = first weekly run of each quarter.
# About 10 independent windows only: the rates are rough. No menu challenger is involved.
import sys, os, json, pickle, datetime
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))
RV = os.path.join(HERE, '..', '..', 'review3', 'work')
import numpy as np
import fm2, fm3_shadow as S
LAST_T0 = {20: '2024-05-01', 60: '2022-04-01'}
def fridays(first, last):
    d = datetime.date.fromisoformat(first); d += datetime.timedelta(days=(4 - d.weekday()) % 7); out = []
    while d <= datetime.date.fromisoformat(last):
        out.append(d); d += datetime.timedelta(days=7)
    return out
looks = []; q = None
for d in fridays('2005-01-01', '2026-11-06'):
    k = (d.year, (d.month - 1) // 3)
    if k != q:
        if q is not None:
            looks.append(d.toordinal())
        q = k
looks = np.array(looks)
def run_rule(F, R, P, t0, h):
    base = (F['start'] >= t0) & (F['mat'] >= 0); n_look = 0
    for L in looks[looks >= t0]:
        win = base & (F['mat'] <= L)
        if not win.any():
            continue
        row = S.compare(F, R, P, win, S.FWD_Q, S.CI_WEEKS[h])
        if 'gain_ci95' in row and row['weeks'] < S.MIN_WEEKS[h]:
            n_look += 1
        st = S.judge(row, h)
        if st != 'shadow':
            return st, row['weeks'], n_look
    return 'shadow', None, n_look
names = sorted({f.rsplit('_', 1)[0] for f in os.listdir(os.path.join(RV, 'dm')) if f.endswith('.npz')})
out = {}
for h in (20, 60):
    o = pickle.load(open(os.path.join(RV, 'pk', 'F_%d.pkl' % h), 'rb')); F = o['F']
    t0s = [d.toordinal() - 2 for d in fridays('2005-01-05', LAST_T0[h])][::2]
    for pair in ('FM2', 'F0'):
        R = o['R'] if pair == 'FM2' else o['R0']
        for nm in names:
            Z = np.load(os.path.join(RV, 'dm', '%s_%d.npz' % (nm, h)))
            P = {'crps': Z['crps'] if pair == 'FM2' else Z['crps0'], 'hit': Z['hit'] if pair == 'FM2' else Z['hit0'], 'om': Z['om'],
                 'awake': np.ones(len(F['y']), dtype=bool)}
            c = {}; lk = []
            for t0 in t0s:
                st, w, nl = run_rule(F, R, P, t0, h); c[st] = c.get(st, 0) + 1; lk.append(nl)
            n = len(t0s); out['%s_%d_%s' % (nm, h, pair)] = {k: round(v / n, 3) for k, v in sorted(c.items())}
            print(h, pair, nm, 'T0s', n, out['%s_%d_%s' % (nm, h, pair)], 'interim looks max', max(lk), flush=True)
json.dump(out, open(os.path.join(HERE, 'sim_fut.json'), 'w'), indent=1)
