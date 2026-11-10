import urllib.request, sys, os, json, time
out = sys.argv[1]
syms = sys.argv[2:]
for s in syms:
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s) if False else s}?period1=-631152000&period2=1794268800&interval=1d&events=div%2Csplit'
    try:
        req = urllib.request.Request(url.replace('^','%5E'), headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as r: b = r.read()
        d = json.loads(b); t = d['chart']['result'][0]['timestamp']
        open(os.path.join(out, s.replace('^','_')+'.json'),'wb').write(b)
        print('OK', s, len(t), time.strftime('%Y-%m-%d', time.gmtime(t[0])), time.strftime('%Y-%m-%d', time.gmtime(t[-1])))
    except Exception as e:
        print('FAIL', s, type(e).__name__, e)
    time.sleep(1)
