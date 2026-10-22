import json,os,sys
x=json.load(open(sys.argv[1],encoding='utf-8'));W=sys.argv[2];os.makedirs(W+'/orders',exist_ok=True)
try:k=json.load(open(sys.argv[3],encoding='utf-8')) if len(sys.argv)>3 and sys.argv[3]!='-' else None
except Exception:k=None
c3=(k or {}).get('c3') if (k or {}).get('day_kst')==x.get('run_day_kst') and ((k or {}).get('decision') or {}).get('generated_at')==x.get('generated_at') else None
def allow(t):
    c=(c3 or {}).get(t.get('side')) or {}
    return bool(c.get('confirmed_before')) or t.get('ticket_id') in (c.get('matched') or [])
b=x.get('dashboard') or {}
E=[{'ticket_id':t.get('ticket_id'),'side':t.get('side'),'ticker':t.get('ticker')} for t in x.get('tickets') or []]
I={e['ticket_id'] for e in E}
E+=[{'ticket_id':o.get('id'),'side':o.get('side'),'ticker':o.get('ticker')} for o in b.get('orders') or [] if o.get('id') not in I]
S={str(t.get('ticker'))+'|'+str(t.get('side')) for t in E if allow(t)}
Hd=[str(t.get('ticker'))+'|'+str(t.get('side')) for t in E if not allow(t)]
c=x.get('compare') or {};r=(x.get('inputs') or {}).get('research_record') or {}
core={**(b.get('runCore') or {}),'meta':{'source':'auto-core','status':x.get('status'),'mode':x.get('decision_mode'),'generatedAt':x.get('generated_at'),'session':x.get('evaluation_session'),'noNewSession':x.get('no_new_session'),'reasons':(x.get('reasons') or [])[:3],'research':r.get('status'),'compare':{'status':c.get('status'),'streak':c.get('streak'),'required':c.get('required'),'unexplained':len(c.get('unexplained') or [])}}}
if x.get('decision_mode')=='apply' and Hd:
    core['meta']['ticketHold']=[h+' 주문표 확인 대기 — 입력 금지' for h in Hd]
    for t in core.get('tickets') or []:
        if isinstance(t,dict) and str(t.get('ticker'))+'|'+str(t.get('side')) in Hd:t['hold']='주문표 확인 대기 — 입력 금지'
json.dump({'core':core},open(W+'/core.json','w',encoding='utf-8'),ensure_ascii=False)
n=0
if x.get('decision_mode')=='apply' and x.get('status')!='FAIL':
    for o in b.get('orders') or []:
        if o.get('id') and str(o.get('ticker'))+'|'+str(o.get('side')) in S:json.dump(o,open(W+'/orders/'+o['id']+'.json','w',encoding='utf-8'),ensure_ascii=False);n+=1
print('CORE_READY',x.get('run_day_kst'),'orders',n,'bytes',os.path.getsize(W+'/core.json'))
