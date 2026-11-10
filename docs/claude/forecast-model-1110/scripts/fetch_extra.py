#!/usr/bin/env python3
"""Fetch extra Yahoo daily series for FM-2 layer-3 challengers (cloud only; reference-grade data).

Same source and file shape as fetch_weekly.py (it calls fetch_weekly.fetch). The stems are the values of
the EXTRAS tables of the registered challenger modules, e.g. _VIX _GSPC.

  <out_dir>/extra/<stem>.json
  <out_dir>/MANIFEST_EXTRA.json     rows, first and last day, last close, newest bars without a close, sha256

usage: python3 -I -B fetch_extra.py <out_dir> <stem> [<stem> ...]
"""
import sys, os, json, time, hashlib, datetime
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_weekly


def main():
    out = sys.argv[1]; stems = sys.argv[2:]
    os.makedirs(os.path.join(out, 'extra'), exist_ok=True)
    man = {'fetched_at': (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S KST'),
           'source': 'Yahoo chart API, daily (reference grade)', 'files': {}}
    bad = []
    day = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%d')
    for stem in stems:
        j = None
        for attempt in range(4):
            try:
                j = fetch_weekly.fetch(stem); break
            except Exception as e:                              # network errors: wait and retry
                err = '%s %s' % (type(e).__name__, e); time.sleep(2 ** (attempt + 1))
        if j is None:
            bad.append(stem); print('FAIL', stem, err); continue
        b = json.dumps(j, separators=(',', ':')).encode()
        open(os.path.join(out, 'extra', stem + '.json'), 'wb').write(b)
        res = j['chart']['result'][0]
        ts = res['timestamp']; cl = res['indicators']['quote'][0]['close']
        ok = [(t, c) for t, c in zip(ts, cl) if c is not None and c > 0]
        null = [day(t) for t, c in zip(ts[-10:], cl[-10:]) if c is None or not (c > 0)]
        man['files']['extra/' + stem + '.json'] = {'rows': len(ok), 'first': day(ok[0][0]), 'last': day(ok[-1][0]), 'last_close': ok[-1][1],
                                                   'recent_valid': [day(t) for t, _ in ok[-10:]], 'recent_null': null,
                                                   'sha256': hashlib.sha256(b).hexdigest()}
        print('OK', stem, len(ok), day(ok[0][0]), day(ok[-1][0]), ('| WARN no close yet on ' + ','.join(null)) if null else '')
        time.sleep(1)
    man['failed'] = bad
    json.dump(man, open(os.path.join(out, 'MANIFEST_EXTRA.json'), 'w'), indent=1)
    print('written', os.path.join(out, 'MANIFEST_EXTRA.json'), '| failed', bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
