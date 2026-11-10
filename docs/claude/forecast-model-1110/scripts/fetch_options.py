#!/usr/bin/env python3
"""Snapshot of option quotes near the money (cloud only; reference-grade Yahoo data; display/score use only).

Why: a future layer-3 challenger that reads option-implied volatility per asset has no history to learn
from. These snapshots are stored from 2026-11-10 on, before the outcomes they could help to forecast are
known. Nothing reads them yet; a challenger that does must first be registered under
forecast-layer3-rule-2026-11-10.md. No account, no order, no trading use.

Symbols: the US-listed pool assets (fm2.UNIVERSE) and four ETF proxies of the display targets.
Per symbol: the expirations that bracket 30, 91 and 365 calendar days, and every monthly (third Friday)
expiration within 400 days. Per expiration: up to 60 strikes within 20% of the last price, with
[strike, call bid, ask, last, last-trade time, volume, open interest, Yahoo IV, put bid, ask, last,
 last-trade time, volume, open interest, Yahoo IV].

  <out_dir>/<snap_day>.json.gz     snap_day = day (UTC) of the last regular trade of the underlyings
  <out_dir>/MANIFEST.jsonl         one line per snapshot: day, file, sha256, symbols, fetched_at

usage: python3 -I -B fetch_options.py <out_dir>
"""
import sys, os, json, gzip, time, hashlib, datetime, http.cookiejar, urllib.parse, urllib.request
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fm2

PROXIES = ['SPY', 'QQQ', 'SOXX', 'SMH']
TARGETS = (30, 91, 365)
MAX_DTE = 400
BAND = 0.20
MAX_STRIKES = 60
BASE = 'https://query2.finance.yahoo.com'


def opener():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [('User-Agent', 'Mozilla/5.0')]
    try:
        op.open('https://fc.yahoo.com', timeout=30).read()
    except Exception:                                   # this page answers 404 but sets the cookie the crumb needs
        pass
    crumb = op.open(BASE + '/v1/test/getcrumb', timeout=30).read().decode()
    if not crumb or '<' in crumb:
        raise RuntimeError('no crumb')
    return op, urllib.parse.quote(crumb)


def get(op, url):
    err = None
    for attempt in range(4):
        try:
            return json.loads(op.open(url, timeout=45).read())['optionChain']['result'][0]
        except Exception as e:                          # network errors: wait and retry
            err = '%s %s' % (type(e).__name__, e); time.sleep(2 ** (attempt + 1))
    raise RuntimeError(err)


def day(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%d')


def pick(exps, now):
    """Expirations to store: the ones that bracket each target and the monthly ones up to MAX_DTE."""
    dte = {e: (e - now) / 86400.0 for e in exps}
    keep = set()
    for tg in TARGETS:
        below = [e for e in exps if 0 < dte[e] <= tg]; above = [e for e in exps if dte[e] > tg]
        if below:
            keep.add(max(below))
        if above:
            keep.add(min(above))
    for e in exps:
        d = datetime.datetime.fromtimestamp(e, datetime.timezone.utc)
        if 0 < dte[e] <= MAX_DTE and d.weekday() == 4 and 15 <= d.day <= 21:
            keep.add(e)
    return sorted(keep)


def rows(o, S):
    calls = {c['strike']: c for c in o.get('calls', [])}; puts = {p['strike']: p for p in o.get('puts', [])}
    ks = sorted((k for k in set(calls) | set(puts) if abs(k / S - 1) <= BAND), key=lambda k: abs(k - S))[:MAX_STRIKES]
    f = lambda x: [x.get('bid'), x.get('ask'), x.get('lastPrice'), x.get('lastTradeDate'), x.get('volume'), x.get('openInterest'),
                   round(x['impliedVolatility'], 5) if x.get('impliedVolatility') is not None else None]
    return [[k] + f(calls.get(k, {})) + f(puts.get(k, {})) for k in sorted(ks)]


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    syms = [s for s, _, _ in fm2.UNIVERSE if not s.startswith('_')] + PROXIES
    op, crumb = opener()
    snap = {'fetched_at': (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S KST'),
            'source': 'Yahoo option chain (reference grade; quotes after the close can be stale or empty)',
            'columns': ['strike', 'c_bid', 'c_ask', 'c_last', 'c_last_time', 'c_volume', 'c_oi', 'c_iv',
                        'p_bid', 'p_ask', 'p_last', 'p_last_time', 'p_volume', 'p_oi', 'p_iv'],
            'symbols': {}, 'failed': []}
    for sym in syms:
        try:
            d = get(op, '%s/v7/finance/options/%s?crumb=%s' % (BASE, sym, crumb))
            q = d['quote']; S = float(q['regularMarketPrice']); now = int(q['regularMarketTime'])
            ent = {'S': S, 'mkt_time': now, 'mkt_day': day(now), 'state': q.get('marketState'), 'exp': {}}
            for e in pick(d['expirationDates'], now):
                o = get(op, '%s/v7/finance/options/%s?date=%d&crumb=%s' % (BASE, sym, e, crumb))['options']
                if o:
                    ent['exp'][day(e)] = rows(o[0], S)
                time.sleep(0.25)
            snap['symbols'][sym] = ent
            print('OK', sym, ent['mkt_day'], S, 'expirations', len(ent['exp']), 'rows', sum(len(v) for v in ent['exp'].values()))
        except Exception as e:
            snap['failed'].append(sym); print('FAIL', sym, type(e).__name__, e)
    days = [v['mkt_day'] for v in snap['symbols'].values()]
    if not days:
        print('no symbol fetched'); sys.exit(1)
    snap['snap_day'] = max(set(days), key=days.count)
    name = snap['snap_day'] + '.json.gz'
    if os.path.exists(os.path.join(out, name)):                       # never overwrite an earlier snapshot of the same day
        name = '%s_%s.json.gz' % (snap['snap_day'], snap['fetched_at'][11:16].replace(':', ''))
    b = gzip.compress(json.dumps(snap, separators=(',', ':')).encode(), mtime=0)
    open(os.path.join(out, name), 'wb').write(b)
    line = {'snap_day': snap['snap_day'], 'file': name, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b),
            'symbols': len(snap['symbols']), 'failed': snap['failed'], 'fetched_at': snap['fetched_at']}
    with open(os.path.join(out, 'MANIFEST.jsonl'), 'a', encoding='utf-8') as f:
        f.write(json.dumps(line) + '\n')
    print('written', os.path.join(out, name), line)
    sys.exit(1 if snap['failed'] else 0)


if __name__ == '__main__':
    main()
