#!/usr/bin/env python3
"""Fetch daily closes for the FM-2 weekly run, up to now (cloud only; reference-grade Yahoo data).

fetch_long.py has a fixed end date (2026-11-10 UTC) and stays as the record of the pre-registered inputs.
This script is for the forward runs. It writes Yahoo-chart-shaped JSON holding only the two fields
fm1.load_yahoo reads (timestamp, close), and a manifest with row counts, last dates and hashes.

  <out_dir>/pool/<stem>.json   20 pool assets (fm2.UNIVERSE)
  <out_dir>/idx/<stem>.json    _TNX _IRX (rates) and _SOX _NDX _GSPC (display targets)
  <out_dir>/MANIFEST.json

Run it after the US close and pass fm2_weekly.py an asof that is the last finished US session,
so that a bar still being traded is cut off by asof.

usage: python3 -I -B fetch_weekly.py <out_dir>
"""
import sys, os, json, time, hashlib, datetime, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fm2

IDX = ['_TNX', '_IRX', '_SOX', '_NDX', '_GSPC']


def fetch(stem):
    sym = ('%5E' + stem[1:]) if stem.startswith('_') else stem
    url = ('https://query1.finance.yahoo.com/v8/finance/chart/%s?period1=-631152000&period2=%d&interval=1d'
           % (sym, int(time.time()) + 86400))
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())['chart']['result'][0]
    return {'chart': {'result': [{'meta': {'symbol': d['meta'].get('symbol'), 'currency': d['meta'].get('currency'),
                                           'exchangeTimezoneName': d['meta'].get('exchangeTimezoneName')},
                                  'timestamp': d['timestamp'],
                                  'indicators': {'quote': [{'close': d['indicators']['quote'][0]['close']}]}}]}}


def main():
    out = sys.argv[1]
    man = {'fetched_at': (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S KST'),
           'source': 'Yahoo chart API, daily, price basis (reference grade)', 'files': {}}
    bad = []
    for sub, stems in (('pool', [s for s, _, _ in fm2.UNIVERSE]), ('idx', IDX)):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
        for stem in stems:
            for attempt in range(4):
                try:
                    j = fetch(stem); break
                except Exception as e:                      # network errors: wait and retry
                    j = None; err = '%s %s' % (type(e).__name__, e); time.sleep(2 ** (attempt + 1))
            if j is None:
                bad.append(stem); print('FAIL', stem, err); continue
            b = json.dumps(j, separators=(',', ':')).encode()
            p = os.path.join(out, sub, stem + '.json')
            open(p, 'wb').write(b)
            res = j['chart']['result'][0]
            ts = res['timestamp']; cl = res['indicators']['quote'][0]['close']
            ok = [(t, c) for t, c in zip(ts, cl) if c is not None and c > 0]
            day = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%d')
            # Yahoo can leave the newest daily bars without a close for a while; such a day would silently drop out
            null = [day(t) for t, c in zip(ts[-10:], cl[-10:]) if c is None or not (c > 0)]
            man['files'][sub + '/' + stem + '.json'] = {'rows': len(ok), 'first': day(ok[0][0]), 'last': day(ok[-1][0]),
                                                        'last_close': ok[-1][1], 'recent_valid': [day(t) for t, _ in ok[-10:]],
                                                        'recent_null': null, 'sha256': hashlib.sha256(b).hexdigest()}
            print('OK', stem, len(ok), day(ok[0][0]), day(ok[-1][0]), ('| WARN no close yet on ' + ','.join(null)) if null else '')
            time.sleep(1)
    man['failed'] = bad
    # safe_asof: the latest day on which every US-listed file has a close and before which no file has an unfilled bar
    nulls = sorted({d for f in man['files'].values() for d in f['recent_null']})
    us = [k for k in man['files'] if k.startswith('idx/') or not os.path.basename(k).startswith('_')]
    cand = sorted(set.intersection(*[set(man['files'][k]['recent_valid']) for k in us])) if us and not bad else []
    cand = [d for d in cand if not nulls or d < nulls[0]]
    man['recent_null_days'] = nulls
    man['safe_asof'] = cand[-1] if cand else None
    json.dump(man, open(os.path.join(out, 'MANIFEST.json'), 'w'), indent=1)
    print('written', os.path.join(out, 'MANIFEST.json'), '| failed', bad, '| days without a close yet', nulls, '| safe_asof', man['safe_asof'])
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
