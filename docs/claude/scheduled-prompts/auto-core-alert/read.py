import json,os,sys,datetime as T
K=T.timezone(T.timedelta(hours=9));today=sys.argv[1];lp=sys.argv[2];dp=sys.argv[3];tp=sys.argv[4];rr=sys.argv[5:]
now=T.datetime.now(K).date().isoformat()
print('TODAY',today,'OK' if today==now else 'MISMATCH '+now)
def load(p):
    if p=='-':return None
    try:return json.load(open(p,encoding='utf-8'))
    except Exception:return None
d=load(lp)
if d is None:print('T1 NO_FILE')
else:
    g=d.get('generated_at') or ''
    try:t=T.datetime.fromisoformat(g.replace('Z','+00:00')).astimezone(K)
    except Exception:t=None
    c=d.get('compare') or {}
    print('T1','FRESH' if t and t.date().isoformat()==today else 'STALE',t.isoformat() if t else g)
    print('T1 STATUS',d.get('status'),'MODE',d.get('mode'),'APPLIED',bool(d.get('applied')),'STREAK',c.get('streak'))
    print('T1 REASONS',' | '.join(str(x) for x in (d.get('reasons') or [])[:2]))
    print('T1 WARNINGS',' | '.join(str(x) for x in (d.get('warnings') or [])[:2]))
    print('T1 NEXT',d.get('next_action_for_user') or '')
x=load(dp)
if x is None or x.get('run_day_kst')!=today:print('D NO_FILE' if x is None else 'D STALE '+str(x.get('run_day_kst')))
else:
    r=(x.get('inputs') or {}).get('research_record') or {};c=x.get('compare') or {}
    print('D FRESH STATUS',x.get('status'),'MODE',x.get('decision_mode'),'NO_NEW_SESSION',x.get('no_new_session'),'SESSION',x.get('evaluation_session'))
    print('D REASONS',' | '.join(str(y) for y in (x.get('reasons') or [])[:2]))
    print('D RESEARCH',r.get('status'),' | '.join(str(y) for y in (r.get('reasons') or [])[:1]))
    print('D COMPARE',c.get('status'),'STREAK',c.get('streak'),'/',c.get('required'),'UNEXPLAINED',len(c.get('unexplained') or []))
    print('D TICKETS',len(x.get('tickets') or []),'ORDERS',len((x.get('dashboard') or {}).get('orders') or []))
    P=[a.get('line') for a in (x.get('alerts') or []) if a.get('push')]
    k=load(tp);c3=(k or {}).get('c3') if (k or {}).get('day_kst')==today and ((k or {}).get('decision') or {}).get('generated_at')==x.get('generated_at') else None
    def allow(t):
        c=(c3 or {}).get(t.get('side')) or {}
        return bool(c.get('confirmed_before')) or t.get('ticket_id') in (c.get('matched') or [])
    E=[{'ticket_id':t.get('ticket_id'),'side':t.get('side'),'ticker':t.get('ticker')} for t in x.get('tickets') or []]
    I={e['ticket_id'] for e in E}
    E+=[{'ticket_id':o.get('id'),'side':o.get('side'),'ticker':o.get('ticker')} for o in (x.get('dashboard') or {}).get('orders') or [] if o.get('id') not in I]
    H={}
    if x.get('decision_mode')=='apply':
        for t in E:
            if not allow(t):H.setdefault(str(t.get('side')),[]).append(str(t.get('ticker')))
    B=[c for v in H.values() for c in v]
    P=[l for l in P if not any(c in str(l) for c in B)]
    for l in P[:3]:print('D PUSH',l)
    if len(P)>3:print('D PUSH 외',len(P)-3,'건')
    for s,v in sorted(H.items()):print('D HOLD',{'buy':'매수','sell':'매도'}.get(s,s),','.join(v))
    n=x.get('next_action_for_user') or ''
    if B and n:
        m=len(E)-len(B)
        n='주문표 %d건 — 저녁 키움 입력 (확인 대기 %d건은 입력 금지)'%(m,len(B)) if m>0 else ''
    print('D NEXT_USER',n)
    print('D NEXT_COWORK',x.get('next_action_for_cowork') or '')
k=load(tp)
if k is None:print('R NO_FILE')
elif k.get('day_kst')!=today:print('R STALE',k.get('day_kst'))
else:
    c=k.get('c1') or {}
    print('R FRESH VERDICT',k.get('verdict'),'REASON',k.get('reason') or '-','C1',c.get('match'),'MISSING',len(c.get('missing_in_core') or []),'EXTRA',len(c.get('extra_in_core') or []),'LEAKS',len(k.get('ticket_leaks') or []),'TICKETS_MATCH',sum(1 for t in k.get('tickets') or [] if t.get('match')),'/',len(k.get('tickets') or []))
for p in sorted(rr):
    for a in [a for a in ((load(p) or {}).get('alerts') or []) if a.get('push')][:1]:print('D RERUN',os.path.basename(p),a.get('line'))
