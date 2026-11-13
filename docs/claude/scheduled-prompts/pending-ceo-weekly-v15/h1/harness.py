import json,os,re,subprocess,sys,shutil,datetime as dt,hashlib
REPO=os.path.expanduser('~/mnt/코덱스저장소');SNAP=os.path.expanduser('~/work/snap');WORK=os.path.expanduser('~/work');T=WORK+'/t'
SCR=sys.argv[1]  # script path
TAG=sys.argv[2]  # tag
MODE=sys.argv[3] # real | chain
OUT=f'{T}/{TAG}-{MODE}';shutil.rmtree(OUT,ignore_errors=True);os.makedirs(OUT)
# test copy: only output dir replaced
src=open(SCR,encoding='utf-8',newline='').read()
assert src.count('/mnt/user-data/outputs')>=1
open(OUT+'/ceo_test.py','w',encoding='utf-8',newline='').write(src.replace('/mnt/user-data/outputs',OUT+'/outputs'))
WEEKS=['2026-10-19','2026-10-25','2026-11-01','2026-11-08']
real=open(SNAP+'/docs/claude/ceo-weekly-report.md','rb').read()
def prefix(date):
    k=real.find(('## 주간 경영보고 '+date).encode('utf-8'))
    assert k>0,date
    return real[:k].rstrip(b'\n')+b'\n\n' if False else real[:k]
def board_txt(date):
    k=real.find(('## 주간 경영보고 '+date).encode('utf-8'));nk=real.find('## 주간 경영보고 '.encode('utf-8'),k+5)
    sec=real[k:nk if nk>0 else len(real)].decode('utf-8')
    m=re.search(r'### 7\. 관제판 점검 원문\n```text\n(.*?)\n```',sec,re.S)
    return m.group(1)
def ls(p):
    try:return sorted(os.listdir(SNAP+'/'+p))
    except Exception:return None
def per(today):
    t=dt.date.fromisoformat(today);sat=t-dt.timedelta(days=(t.weekday()-5)%7);sun=sat-dt.timedelta(days=6)
    return sun,sat,[(sat-dt.timedelta(days=i)).isoformat() for i in range(4,-1,-1)]
def mkroot(d,prev_bytes):
    r=d+'/root';os.makedirs(r+'/docs/claude',exist_ok=True)
    for n in ('workspace','CLAUDE.md','AGENTS.md'):os.symlink(SNAP+'/'+n,r+'/'+n)
    for n in os.listdir(SNAP+'/docs/claude'):
        if n=='ceo-weekly-report.md':continue
        os.symlink(SNAP+'/docs/claude/'+n,r+'/docs/claude/'+n)
    if prev_bytes is not None:open(r+'/docs/claude/ceo-weekly-report.md','wb').write(prev_bytes)
    return r
def trig(today):
    now=dt.datetime.fromisoformat(today+'T09:55:00+09:00');z=lambda h:(now.replace(hour=h,minute=0)-dt.timedelta(days=1)).isoformat()
    base=[('통합점검','CRON_TZ=Asia/Seoul 40 6 * * 2-6',True,'SUCCEEDED'),('비서 제안','CRON_TZ=Asia/Seoul 25 9 * * 1-6',True,'SUCCEEDED'),('사장실 결과 모음','CRON_TZ=Asia/Seoul 35 9 * * 1-6',True,'SUCCEEDED'),('시나리오 확률','CRON_TZ=Asia/Seoul 45 6,19,21,22 * * *',True,'SUCCEEDED'),('SAVE 메모','CRON_TZ=Asia/Seoul 15 6 * * *',True,'SUCCEEDED')]
    out=[]
    for i,(n,c,rec,st) in enumerate(base):
        lf=(now-dt.timedelta(minutes=15)).isoformat();bad=today in ('2026-10-25','2026-11-08')
        if bad and i==1:lf='2026-10-01T00:00:00+09:00'
        if bad and i==2:st='ROUTINE_RUN_STATUS_FAILED'
        out.append({'id':f'trig_T{i}','name':n,'updated':'2026-10-01T00:00:00Z','head':'v1','enabled':True,'recurring':True,'cron':c,'last_fired':lf,'last_status':st,'created':'2026-09-01T00:00:00Z'})
    return out
def runs(d,days,abnormal):
    os.makedirs(d+'/runs',exist_ok=True)
    for i,day in enumerate(days):
        if abnormal and i==3:continue  # missing record
        x={'date':day,'runAt':day+'T06:50:00+09:00','status':[{'label':'점검 상태','value':'정상' if not(abnormal and i==1) else '주의','tone':'ok' if not(abnormal and i==1) else 'warn'}],'filings':{'status':'OK','newCount':i},'market':{'stale':bool(abnormal and i==2),'reportDate':day},'saveticker':{'x':1} if i%2==0 else {}}
        if abnormal:x['saveticker']={'x':1}
        json.dump(x,open(f'{d}/runs/{day}.json','w',encoding='utf-8'),ensure_ascii=False)
def tasks(d):
    os.makedirs(d+'/tasks',exist_ok=True)
    for k,v in {'a1':{'status':'active','plain':'작업1','updatedAt':'2026-11-02T00:00:00Z'},'w1':{'status':'waiting','plain':'대기','updatedAt':'2026-10-20T00:00:00Z'},'dc1':{'status':'decision','deadline':'2026-11-20'},'d1':{'status':'done','doneAt':'2026-11-03T01:00:00Z'},'redesign-t2':{'status':'active','next':'C1 10/20(화) 08:40 대조부터 0/10'}}.items():json.dump(v,open(f'{d}/tasks/{k}.json','w',encoding='utf-8'),ensure_ascii=False)
def sh(args,**k):
    return subprocess.run(args,capture_output=True,text=True,**k)
res={};prev=None;extra=os.environ.get('EXTRA','')
for wi,date in enumerate(WEEKS):
    d=f'{OUT}/{date}';os.makedirs(d)
    sun,sat,days=per(date)
    if MODE=='real':pv=prefix(date) if wi>0 else None
    else:pv=prev
    root=mkroot(d,pv)
    ab=(wi%2==1)
    runs(d,days,ab);tasks(d)
    have={'report':pv is not None,'weekly_latest':os.path.exists(SNAP+'/workspace/outputs/journal-scores/WEEKLY_LATEST.json'),'core_dirs':[x for x in (ls('workspace/outputs/auto-core') or []) if re.match(r'\d{4}-',x)],'rr_dirs':[x for x in (ls('workspace/outputs/research-records') or []) if re.match(r'\d{4}-',x)]}
    inj={'today':date,'trig':trig(date),'sch':[],'mtimes':{},'complete':{'trig':True,'sch':True,'docs':True,'policy':True,'tasks':True,'runs':True},'judge_files':[],'policy_changes':[],'oneshots':[],'trig_at':date+'T09:55:00+09:00','have':have,'week_docs':{},'nsd_files':[x for x in (ls('docs/claude') or []) if x.startswith('next-sandisk-scan-')],'preopen':ls('workspace/outputs/pre-open'),'nsdw_files':ls('workspace/outputs/next-sandisk-weekly'),'secretary':ls('workspace/outputs/secretary')}
    json.dump(inj,open(d+'/in.json','w',encoding='utf-8'),ensure_ascii=False)
    open(d+'/board.txt','w',encoding='utf-8').write(board_txt(date))
    env=dict(os.environ,CEO_NOW=date+'T09:55:00+09:00')
    p=sh(['python3','-I',OUT+'/ceo_test.py','plan',date,d+'/in.json'],env=env);assert p.returncode==0,p.stderr
    plan=json.loads(p.stdout);res[date+'_plan']=[x.split('\\')[-1] for b in plan for x in b if 'secretary' in x]
    r=sh(['python3','-I',OUT+'/ceo_test.py','run',date,root,d+'/in.json',d+'/board.txt',d+'/tasks'],env=env)
    if r.returncode!=0:res[date]={'run_rc':r.returncode,'out':r.stdout[:300],'err':r.stderr[-600:]};break
    j=json.loads(r.stdout.split('\n')[0]);inbox=[x.split(' ')[0] for x in j['inbox']]
    # fill
    use=inbox[1] if len(inbox)>1 else inbox[0]
    revs=[{'src':i,'read':'제안 있음' if i==use else '특이 없음','note':'시험 메모' if i==use else ''} for i in inbox]
    props=[{'team':t,'none':True} for t in ['운영관리','투자리서치','연구개발','법률']]
    dls={0:'2026-10-24',1:'2026-11-05',2:'2026-11-12',3:None}[wi]
    props[0]={'team':'운영관리','text':'시험 제안 하나를 처리하자','fids':[use],'rank':2,'decision':True,'with':['법률'],'ask':'법률이 확인'}
    dec=[{'question':'시험 결정 질문?','recommend':'예 — 시험','options':'a) 예 b) 아니오','fids':[use]}]
    if dls:dec[0]['deadline']=dls
    json.dump({'reviews':revs,'proposals':props,'decisions':dec},open(d+'/fill.json','w',encoding='utf-8'),ensure_ascii=False)
    f=sh(['python3','-I',OUT+'/ceo_test.py','finalize',d],env=env)
    if f.returncode!=0:res[date]={'fin_rc':f.returncode,'out':f.stdout[-300:],'err':f.stderr[-800:]};break
    fj=json.loads(f.stdout.strip().split('\n')[-1])
    body=open(OUT+'/outputs/ceo-weekly-report.md','rb').read()
    shutil.copy(OUT+'/outputs/ceo-weekly-report.md',d+'/report-after.md')
    ok_prefix=(pv is None) or body.startswith(pv)
    prev=body
    res[date]={'color':j['color'],'findings':[x['id'] for x in j['findings']],'valid':fj['validation'],'D':fj['D'],'prefix_kept':ok_prefix,'push':fj['push'],'prev':j['prev'],'inbox':inbox}
json.dump(res,open(OUT+'/result.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print(json.dumps(res,ensure_ascii=False,indent=1)[:6000])
