import json,os,re,sys,glob,hashlib,datetime as dt
K=dt.timezone(dt.timedelta(hours=9));W='E:\\사업\\##금동한\\코덱스저장소\\';TEAMS=['운영관리','투자리서치','연구개발','법률']
def per(today):
    t=dt.date.fromisoformat(today);sat=t-dt.timedelta(days=(t.weekday()-5)%7);sun=sat-dt.timedelta(days=6)
    return t,sun,sat,[(sat-dt.timedelta(days=i)).isoformat() for i in range(4,-1,-1)]
def kd(s):
    try:return dt.datetime.fromisoformat(str(s).replace('Z','+00:00')).astimezone(K).date().isoformat()
    except Exception:return str(s or '')[:10]
def MK(s):return re.sub(r'\$\d+(?:\.\d+)?','…',re.sub(r'[$₩]?\d{1,3}(?:,\d{3})+(?:\.\d+)?','…',str(s)))
def NW(s):return ' '.join(str(s or '').split())
INFO=('F-LEG-1','F-LEG-3')
def SEV(c):return 'ℹ' if str(c).startswith(INFO) else '🟠'
def CLN(s,n=160):
    t=MK(NW(s));AW=r'(예수금|총자산|주문 ?가능|평단|잔고|매입가|평가액|평가 금액|계좌번호|보유 수량)'
    for _ in range(3):t=re.sub(AW+r'([^\d\n]{0,8}?)(?<![\w-])(?!\d{4}-\d{2}|\d{1,2}:\d{2})\d[\d,./]*',r'\1\2…',t)
    t=re.sub(r'(?<![\w-])\d[\d,.]*\s*(?:주(?![가-힣])|달러|USD|만 ?원|억 ?원|원(?![가-힣]))','…',t)
    t=re.sub(r'(?:USD|US\$)\s*\d[\d,.]*','USD …',t)
    return t.replace('|','/').replace('{{','{ ').replace('}}',' }').replace('-->','->')[:n]
def FM(tx):
    m=re.match(r'^﻿?---\r?\n(.*?)\r?\n---',tx or '',re.S);g=lambda k:(re.search(r'^'+k+r':\s*(.*)$',m.group(1),re.M) or [0,''])[1].strip() if m else ''
    s=g('summary') or g('title')
    if not s:
        L_=[l.strip() for l in (tx or '').split('\n')[:120]];L_=L_[L_.index('---',1)+1:] if m and '---' in L_[1:] else L_
        h=next((l.lstrip('# ') for l in L_ if l.startswith('#')),'');b=next((re.sub(r'^([-*>]|\d+\.)\s+','',l) for l in L_ if l and not l.startswith(('#','---','```','|','<!--'))),'')
        s=' — '.join(x for x in (h,b) if x)
    return {'status':g('status'),'type':g('type'),'tickers':g('tickers'),'valid':g('valid_until'),'sum':s.replace('**','')}
def WDOCS(m):
    m=m if isinstance(m,dict) else {}
    ok=[n for n in m if n.endswith('.md') and '/' not in n and not re.search(r'prompt|^ceo-weekly-report\.md$|^external-claims-ledger\.md$|^next-sandisk-scan-',n)]
    return sorted(ok,key=lambda n:(-(m.get(n) or 0),n))
def NSD(ns):
    v=sorted(n for n in (ns or []) if re.match(r'^next-sandisk-scan-\d{4}-\d{2}-\d{2}\.md$',str(n)))
    return v[-1] if v else None
def NSW(ns,a,b):
    v=sorted((n for n in (ns or []) if re.match(r'^\d{4}-\d{2}-\d{2}(-\d+)?\.md$',str(n)) and a.isoformat()<=n[:10]<=b.isoformat()),key=lambda n:(n[:10],len(n),n))
    return v[-1] if v else (f'{b.isoformat()}.md' if ns is None else None)
def PRE(ns,a,b):return sorted(n for n in (ns or []) if re.match(r'^\d{4}-\d{2}-\d{2}-.+\.md$',str(n)) and a.isoformat()<=n[:10]<=b.isoformat())
RT=[('연구개발',r'judge'),('법률',r'claude-md|agents-md|^artifact-design-rules|^review-stability|policy|constitution|authority|^company-org'),
    ('투자리서치',r'^(watch-card|watchlist|m6-|l2-|dram|buylow|buy-|cpi-|earnings|external-|next-sandisk|market-|scn27h1|event-strategy|card-|holding|thesis|candidate)'),
    ('운영관리',r'^(integrated-check|autocore|auto-core|host|board-|dev-dashboard|open-items|fx1009|ceo-weekly|dashboard-|pre-open|c1-host)'),
    ('연구개발',r'report|fix|replay|preregistration|builder|redesign|t2rc|evo-|merge|oracle|^c\d-|risk|rrec|runner|score|^t\d-|ust\d|pre-on|event-ctx|cmp-|^f-')]
def ROUTE(n,f):
    for t,p in RT:
        if re.search(p,n):return t
    tk=(f or {}).get('tickers') or ''
    return '투자리서치' if tk and 'ALL' not in tk and tk not in('[]','') else '운영관리'
def CRONPREV(expr,now):
    e=str(expr or '').strip();tz=dt.timezone.utc;m=re.match(r'CRON_TZ=(\S+)\s+(.*)',e)
    if m:
        try:
            from zoneinfo import ZoneInfo;tz=K if m.group(1)=='Asia/Seoul' else ZoneInfo(m.group(1))
        except Exception:return None
        e=m.group(2)
    f=e.split()
    if len(f)!=5:return None
    def S(x,lo,hi):
        o=set()
        for p in x.split(','):
            st=1
            if '/' in p:p,st=p.split('/');st=int(st)
            a,b=(lo,hi) if p=='*' else (tuple(map(int,p.split('-'))) if '-' in p else ((int(p),hi) if st>1 else (int(p),int(p))))
            o|=set(range(a,b+1,st))
        return o
    try:mi,hr,dm,mo,dw=S(f[0],0,59),S(f[1],0,23),S(f[2],1,31),S(f[3],1,12),{x%7 for x in S(f[4],0,7)}
    except Exception:return None
    loc=now.astimezone(tz)
    for i in range(40):
        d=(loc-dt.timedelta(days=i)).date();cw=(d.weekday()+1)%7
        if d.month not in mo:continue
        if not((d.day in dm or cw in dw) if f[2][0]!='*' and f[4][0]!='*' else (d.day in dm and cw in dw)):continue
        for h in sorted(hr,reverse=True):
            for mn in sorted(mi,reverse=True):
                c=dt.datetime.combine(d,dt.time(h,mn),tz)
                if c<=loc:return c
    return None
mode=sys.argv[1]
if mode=='period':
    t,sun,sat,days=per(sys.argv[2]);s=int(dt.datetime.combine(sun,dt.time(0,0),K).timestamp()*1000)
    print(json.dumps({'start':sun.isoformat(),'end':sat.isoformat(),'start_ms':s,'end_ms':s+7*86400000,'core_days':days}));sys.exit()
if mode=='plan':
    t,sun,sat,days=per(sys.argv[2]);I=json.load(open(sys.argv[3],encoding='utf-8'));H=I.get('have') or {}
    P=['workspace/outputs/auto-core/LATEST_DECISION.json','workspace/outputs/host-status/LATEST.json','workspace/outputs/dev-runs/LATEST.json','docs/claude/watchlist-registry.json','docs/claude/card-evidence-registry.json','docs/claude/event-calendar.json','CLAUDE.md','AGENTS.md']
    if H.get('weekly_latest'):P.append('workspace/outputs/journal-scores/WEEKLY_LATEST.json')
    if H.get('report'):P.append('docs/claude/ceo-weekly-report.md')
    for d in days:
        if d in (H.get('core_dirs') or []):P+=[f'workspace/outputs/auto-core/{d}/{f}' for f in('result.json','decision.json','t2rc-check.json')]
        if d in (H.get('rr_dirs') or []):P.append(f'workspace/outputs/research-records/{d}/research-record.json')
    P+=['docs/claude/'+n for n in (I.get('judge_files') or [])[:20]]
    P+=['docs/claude/external-claims-ledger.md','workspace/outputs/save-daily-offline-replay/LATEST_MARKET_ENV_MEMO.md']
    ns=NSD(I.get('nsd_files'))
    if ns:P.append('docs/claude/'+ns)
    nw_=NSW(I.get('nsdw_files'),sun,sat)
    if nw_:P.append('workspace/outputs/next-sandisk-weekly/'+nw_)
    P+=['workspace/outputs/pre-open/'+n for n in PRE(I.get('preopen'),sun,sat)][:10]
    P+=['docs/claude/'+n for n in WDOCS(I.get('week_docs'))[:60]]
    P=list(dict.fromkeys(P))
    print(json.dumps([[W+p.replace('/','\\') for p in P[i:i+45]] for i in range(0,len(P),45)],ensure_ascii=False));sys.exit()
if mode=='run':
    today,root,inj,boardtxt,tdir=sys.argv[2:7]
    t,sun,sat,days=per(today);I=json.load(open(inj,encoding='utf-8'));PS=sun.isoformat();PE=sat.isoformat();C=I.get('complete') or {};HV=I.get('have') or {}
    def fp(p):return os.path.join(root,p)
    def L(p):
        try:return json.load(open(fp(p),encoding='utf-8-sig'))
        except Exception:return None
    def R(p):
        try:return open(fp(p),encoding='utf-8').read()
        except Exception:return None
    def H(p):
        try:return hashlib.sha256(open(fp(p),'rb').read()).hexdigest()
        except Exception:return None
    def Z(p):
        try:return os.path.getsize(fp(p))
        except Exception:return None
    def ab(m):print(json.dumps({'abort':m},ensure_ascii=False));sys.exit(3)
    inp=lambda d:PS<=(d or '')<=PE
    code=lambda s:MK(str(s).split(':')[0][:60])
    RP='docs/claude/ceo-weekly-report.md'
    try:pvb=open(fp(RP),'rb').read()
    except Exception:pvb=None
    if HV.get('report') and pvb is None:ab('보고 파일이 PC에 있는데 받지 못함 — 기록 중단(덮어쓰기 방지)')
    pv=(pvb or b'').decode('utf-8',errors='replace').replace('\r\n','\n')
    if f'<!-- id: ceo-{today} -->' in pv:ab(f'오늘(ceo-{today}) 보고가 이미 있음 — 같은 날 두 번 쓰지 않음')
    T={}
    for f in glob.glob(tdir+'/*.json'):
        x=json.load(open(f,encoding='utf-8'));T[os.path.basename(f)[:-5]]=x.get('data',x)
    F=[];red=False
    def fd(c,team,txt,sev=None):
        global red
        sev=sev or SEV(c);F.append({'id':c,'team':team,'text':MK(txt),'sev':sev});red=red or sev=='🔴'
    TM=os.path.dirname(os.path.abspath(inj));RN={}
    for f_ in glob.glob(TM+'/runs/**/*.json',recursive=True):
        try:x_=json.load(open(f_,encoding='utf-8-sig'))
        except Exception:continue
        x_=x_['data'] if isinstance(x_,dict) and isinstance(x_.get('data'),dict) and 'date' in x_['data'] else x_
        if isinstance(x_,dict) and str(x_.get('date') or '') in days:RN[str(x_['date'])]=x_
    IB=[];AL={};CDL=[];ncc=0;nmt=0;nal=0;noc=[];A=[];MDd=lambda d:f"{int(d[5:7])}/{int(d[8:10])}"
    VT_={'MATCH':'일치','MISMATCH':'불일치','ERROR':'오류','NOT_CHECKED':'대조 안 함'}
    def ib(sid,team,title,sm,items=()):IB.append({'id':sid,'team':team,'title':title,'sum':CLN(sm,260),'items':[CLN(x,170) for x in items if x][:26]})
    okc=0;ptot=0;touch=[];rrok=0;facts=0;tk=0;tv=[];cd=HV.get('core_dirs')
    if cd is None:fd('F-OPS-0','운영관리','코어 폴더 목록 읽기 실패 — 날짜별 코어 점검 확인 필요')
    for d in days:
        r=L(f'workspace/outputs/auto-core/{d}/result.json');x=L(f'workspace/outputs/auto-core/{d}/decision.json');c=L(f'workspace/outputs/auto-core/{d}/t2rc-check.json');rr=L(f'workspace/outputs/research-records/{d}/research-record.json')
        s1=(r or {}).get('status') or '없음';s2=(x or {}).get('status') or '없음';rs=(((x or {}).get('inputs') or {}).get('research_record') or {}).get('status') or '없음'
        v=(c or {}).get('verdict') if (c or {}).get('day_kst')==d else '결과 없음';md=d[5:].replace('-','')
        if s1=='OK' and s2=='OK':okc+=1
        elif cd is not None:
            if r is None and x is None:why='코어 결과 없음'
            else:why=' · '.join(z for z in [('daily '+code(((r or {}).get('reasons') or ['-'])[0])) if s1!='OK' and r is not None else '',('decide '+code(((x or {}).get('reasons') or ['-'])[0])) if s2!='OK' and x is not None else ''] if z) or '사유 없음'
            fd('F-OPS-1-'+md,'운영관리',f'{d} 코어 daily {s1} · decide {s2} — {why}','🔴' if '없음' in (s1,s2) or 'FAIL' in (s1,s2) else '🟠')
        if rs=='OK':rrok+=1
        elif x is not None and not x.get('no_new_session'):fd('F-RES-1-'+md,'투자리서치',f'{d} 연구 기록 {rs} — 그날 매수 막힘(매도는 안 막힘)')
        if v in('MISMATCH','ERROR'):fd('F-AUD-2-'+md,'감사실',f'{d} 독립 대조 {v}','🔴')
        ptot+=sum(1 for a in (x or {}).get('alerts') or [] if a.get('push'))
        tk+=len((x or {}).get('tickets') or [])
        for n in ((r or {}).get('next_action_for_user'),(x or {}).get('next_action_for_user')):
            if n and '키움 입력' not in str(n):touch.append(f'{d[5:]} {code(n)}')
        if isinstance((rr or {}).get('official_facts'),list):facts+=len(rr['official_facts'])
        tv.append(f"{d[5:]} {v}{'(C1 셈)' if (c or {}).get('counts_for_c1') else ''}")
        al=[a for a in (x or {}).get('alerts') or [] if isinstance(a,dict)];rd_=RN.get(d);cc=bool((rd_ or {}).get('core'));ncc+=cc;nmt+=v=='MATCH';nal+=len(al)
        for a in al:AL[str(a.get('code'))]=(d,str(a.get('line') or ''),a.get('push') is True or AL.get(str(a.get('code')),('','',False))[2])
        CDL.append(f"{MDd(d)} daily {s1}·decide {s2} · 알림 {len(al)}줄(푸시 {sum(1 for a in al if a.get('push') is True)}) · 대조 {VT_.get(v,v)} · 결과 알림 대시보드 옮김 {'예' if cc else ('아니오' if rd_ else '통합점검 기록 없음')}")
        if rd_ and x is not None and not cc:noc.append(MDd(d))
    if touch:fd('F-OPS-3','운영관리','코어가 사람에게 요청한 일(주문 입력 제외) '+str(len(touch))+'건: '+' / '.join(touch[:3]))
    h=L('workspace/outputs/host-status/LATEST.json')
    if not h:host='결과 없음';fd('F-OPS-2','운영관리','PC 상태 점검 결과 없음')
    else:
        hd=kd(h.get('generated_at'));host=f"{h.get('status')} ({hd})"
        A=[str(c.get('id'))+'('+str(c.get('state'))+')' for c in h.get('checks') or [] if isinstance(c,dict) and c.get('state')!='OK' and not(c.get('id')=='auto_logon' and c.get('state')=='WARN')]
        if hd<PE:fd('F-OPS-2','운영관리',f'PC 상태 점검 낡음({hd})')
        elif A:fd('F-OPS-2','운영관리','PC 상태 이상: '+', '.join(A[:3]))
    try:B=open(boardtxt,encoding='utf-8').read().strip() or '점검 불완전(스크립트 출력 없음)'
    except Exception:B='점검 불완전(스크립트 출력 없음)'
    if C.get('docs') is False:B=B+'\n(R2 미점검 — 문서 시각 읽기 실패: R2 줄은 세지 않음)'
    m=re.search(r'RESULT (\d+)건',B);bn=int(m.group(1)) if m else None
    if bn is not None and C.get('docs') is False:bn-=len(re.findall(r'^R2 ',B,re.M))
    miss=re.findall(r'^미점검 .*',B,re.M)+(['R2 미점검'] if C.get('docs') is False else [])+(['작업 일부만 읽음 — R2·R4·R5·R6 부분 점검'] if C.get('tasks') is False else [])
    if bn is None:fd('F-OPS-4','운영관리','관제판 점검 불완전')
    else:
        if bn>0:fd('F-OPS-4','운영관리',f'관제판 점검 발견 {bn}건(7절 원문)')
        if miss:fd('F-OPS-5','운영관리','관제판 점검 일부 미점검: '+' / '.join(x[:50] for x in miss))
    X=L('workspace/outputs/auto-core/LATEST_DECISION.json') or {};ex=X.get('exposure') or {};S7=ex.get('S7') or {};ac=((X.get('dashboard') or {}).get('runCore') or {}).get('account') or {}
    cu=ac.get('first_cushion_pct');cu=f'{cu*100:.1f}%' if isinstance(cu,(int,float)) else '확인 필요'
    pk=' · '.join(f"{p.get('symbol')} {p.get('state')}" for p in ex.get('peaks') or []) or '없음'
    E=S7.get('E');E=f'{E:.2f}' if isinstance(E,(int,float)) else '확인 필요'
    pa=', '.join({'new_buy':'신규 매수','add':'추가 매수'}.get(k,k) for k,v in (S7.get('pauses') or {}).items() if v) or '없음'
    wl=L('docs/claude/watchlist-registry.json') or {};wh=[f"{x.get('date')} {x.get('action')} {x.get('in') or ''}/{x.get('out') or ''}" for x in wl.get('history') or [] if inp(x.get('date'))]
    cr=(L('docs/claude/card-evidence-registry.json') or {}).get('symbols') or {};ca=[f"{k}({(v.get('accepted') or {}).get('date')})" for k,v in cr.items() if inp((v.get('accepted') or {}).get('date'))]
    roles={}
    for v in cr.values():roles[v.get('role')]=roles.get(v.get('role'),0)+1
    st={};auth=[];done=[];dec=[]
    for k,v in T.items():
        s=v.get('status');st[s]=st.get(s,0)+1
        if s=='active' and str(v.get('k') or '').startswith(('권한','K3')):auth.append(k)
        if s=='done' and inp(str(v.get('doneAt') or '')[:10]):done.append(k)
        if s=='decision':dec.append(f"{k}(기한 {v.get('deadline') or '없음'})")
    na=st.get('active',0)
    if C.get('tasks') is False:fd('F-RND-0','연구개발','관제판 작업 목록을 끝까지 못 읽음 — 연구개발 지표 확인 필요')
    if na>3:fd('F-RND-1','연구개발',f'진행 개발 {na}개 > 3')
    if len(auth)>1:fd('F-RND-2','연구개발','권한·한도 변경 동시 진행 '+','.join(auth))
    dv=L('workspace/outputs/dev-runs/LATEST.json') or {}
    dvs=f"{dv.get('id','없음')} {'MERGED '+kd(dv.get('merged_at')) if dv.get('merged_at') else dv.get('status','')}".strip()
    if dv and not dv.get('merged_at') and re.search(r'FAIL|STOP|ERROR',str(dv.get('status'))):fd('F-RND-4','연구개발','최근 개발 실행 '+dvs)
    wk=L('workspace/outputs/journal-scores/WEEKLY_LATEST.json');wd=kd((wk or {}).get('generated_at') or (wk or {}).get('written_at') or (wk or {}).get('finished_at'))
    if HV.get('weekly_latest') is None and not wk:sc='확인 필요(목록 읽기 실패)'
    elif not wk:sc='없음';fd('F-RND-3','연구개발','판단 성적 채점 주간 출력 없음')
    else:
        sc=f"{wk.get('status')} ({wd})"
        if wd<(sat+dt.timedelta(days=1)).isoformat():fd('F-RND-3','연구개발',f'채점 미실행·낡음({wd})')
        elif wk.get('status')!='OK':fd('F-RND-3','연구개발',f"채점 주간 출력 {wk.get('status')}")
    nx2=str((T.get('redesign-t2') or {}).get('next') or '');c1=re.search(r'(?<![A-Za-z-])C1\b[^·;\n]{0,100}?(?<![\d/])\d{1,2}/10(?![\d(])',nx2)
    c1=MK(c1.group()) if c1 else '관제판 redesign-t2 next에 "C1 … n/10" 문구 없음(확인 필요)'
    try:ms=re.findall(r'<!-- ceo-state (\{.*\}) -->',pv);PS0=json.loads(ms[-1]) if ms else {}
    except Exception:PS0={};fd('F-LEG-0-state','법률','지난 보고의 기준값(ceo-state) 읽기 실패 — 이번 주를 새 기준으로')
    NS={'claude_md':[Z('CLAUDE.md'),H('CLAUDE.md')],'agents_md':[Z('AGENTS.md'),H('AGENTS.md')]};lg=[]
    for k,lab in(('claude_md','CLAUDE.md'),('agents_md','AGENTS.md')):
        a=PS0.get(k);b=NS[k];fx=k.split('_')[0]
        if b[1] is None:lg.append(f'{lab} 읽기 실패');fd('F-LEG-0-'+fx,'법률',f'{lab} 읽기 실패');continue
        if not a:lg.append(f'{lab} {b[0]}바이트 기준값 기록(첫 실행)');continue
        if a[1]!=b[1]:lg.append(f'{lab} 바뀜({a[0]}→{b[0]}바이트)');fd('F-LEG-1-'+fx,'법률',f'{lab} 지난 보고 뒤 바뀜({a[0]}→{b[0]}바이트)')
        else:lg.append(f'{lab} 그대로 {b[0]}바이트')
    pc=I.get('policy_changes') or [];pcs='확인 필요(목록 읽기 실패)' if C.get('policy') is False else f'{len(pc)}건'
    if pc:fd('F-LEG-2','법률','정책 파일 수정(이름·시각만, 승인 정책 포함): '+', '.join(pc[:5]))
    tu=[x['name'] for x in I.get('trig') or [] if inp(kd(x.get('updated')))];tus='확인 필요(목록 끝까지 못 읽음)' if C.get('trig') is False else f'{len(tu)}건'
    if tu:fd('F-LEG-3','법률',f'예약 지시문·설정 수정 {len(tu)}건: '+', '.join(tu[:4]))
    jd=[];JV={}
    for n in (I.get('judge_files') or [])[:20]:
        tx=R('docs/claude/'+n);v=re.findall(r'^\s*VERDICT:\s*([A-Z_-]+)',tx or '',re.M);v=v[-1] if v else ('판정 줄 없음' if tx else '받지 못함')
        jd.append(f'{n} {v}');JV.setdefault(n.split('-judge')[0],[]).append(v)
    jm=[n for n in (I.get('judge_files') or [])[:20] if R('docs/claude/'+n) is None]
    if jm:fd('F-OPS-7-judge','운영관리',f'Judge 보고서 {len(jm)}개 받지 못함(판정 확인 못 함): '+', '.join(jm[:3]))
    try:sf=NW(open(os.path.dirname(os.path.abspath(inj))+'/stage_fail.txt',encoding='utf-8').read())
    except Exception:sf=''
    if sf:fd('F-OPS-7-stage','운영관리',f'자료 받기 일부 실패(묶음 {sf[:20]}) — 그 묶음 파일은 받은 결과에 "받지 못함"')
    for g,vs in JV.items():
        if 'FAIL' in vs and not any(x.startswith('PASS') for x in vs):fd('F-AUD-1-'+g,'감사실',f'Judge FAIL 뒤 PASS 없음: {g}')
    DL=[];dflt=set();cur=None;last=None;ids=[]
    for ln in pv.split('\n'):
        m=re.match(r'<!-- id: (ceo-[\d-]+) -->',ln)
        if m:cur=m.group(1);ids.append(cur);last=None;continue
        if ln.startswith('#'):last=None
        m=re.match(r'- (?:⚠ )?(D\d+) (.*)',ln)
        if m and cur:
            q=re.findall(r'· 기한 (\d{4}-\d{2}-\d{2}) · 답 양식',ln);last={'key':cur+' '+m.group(1),'sec':cur,'d':m.group(1),'dl':q[-1] if q else '','q':m.group(2).split(' · 권장')[0][:60],'ans':False};DL.append(last);continue
        if last and re.match(r'^\s*-?\s*답:',ln):last['ans']=True;continue
        for k in re.findall(r'기본값 기록: (ceo-[\d-]+ D\d+)',ln):dflt.add(k)
    pid=ids[-1] if ids else ''
    exp=[x for x in DL if not x['ans'] and x['key'] not in dflt and (not x['dl'] or x['dl']<today)]
    wait=[x for x in DL if not x['ans'] and x['key'] not in dflt and x not in exp]
    pl=[f"- 기본값 기록: {x['key']}(기한 {x['dl'] or '없음'}) — 답 없음 → 현행 유지(정책·상태·권한·주문은 바뀌지 않음)" for x in exp] or ['- 기본값으로 닫힌 결정 없음']
    wl4=[f"- 답 대기: {x['key']} {x['q']}(기한 {x['dl']}) — 답 양식 `결정 {x['sec']}: {x['d']} <선택>`" for x in wait]
    nx=[];te=(t+dt.timedelta(days=7)).isoformat();ti=t.isoformat()
    for e in (L('docs/claude/event-calendar.json') or {}).get('events') or []:
        if ti<=(e.get('event_date') or '')<=te:nx.append(f"{e['event_date'][5:]} {e.get('label')}")
    for k,v in (X.get('earnings_calendar') or {}).items():
        if v.get('status')=='VERIFIED' and ti<=(v.get('announcement_session') or '')<=te:nx.append(f"{v['announcement_session'][5:]} {k} 실적({v.get('timing','')})")
    for o in I.get('oneshots') or []:
        d=kd(o.get('next'))
        if ti<=d<=te:nx.append(f"{d[5:]} 일회성 예약: {o.get('name')}")
    # v1.4 새로/계속(관제판 결정 paperclip-1019 Q2 a, 2026-10-19): 지난 보고 절들을 최신부터 거슬러 같은 발견(날짜 꼬리 뺀 번호)·관제판 점검 줄(R번호+작업 id)이 몇 주 이어졌는지
    PH=[];SP_=set()
    for ch_ in reversed([c_ for c_ in re.split(r'(?m)^(?=## 주간 경영보고 )',pv) if c_.startswith('## 주간 경영보고 ')]):
        m_=re.match(r'^## 주간 경영보고 \S+ \(기간 (\d{4}-\d{2}-\d{2})~(\d{4}-\d{2}-\d{2})\)',ch_)
        if not m_ or m_.group(1) in SP_ or m_.group(1)>=PS:continue
        SP_.add(m_.group(1));s7_=ch_.split('### 7.',1)[1] if '### 7.' in ch_ else ''
        PH.append((m_.group(1),m_.group(2),{re.sub(r'-\d{4}$','',x_) for x_ in re.findall(r'^- (F-[A-Z]+-[\w-]+) \[',ch_,re.M)},set(re.findall(r'^(R\d \S+)',s7_,re.M)),bool(re.search(r'^RESULT \d+건',s7_,re.M))))
    PH.sort(key=lambda z:z[0],reverse=True)
    def STK(k,i):
        n_=1;ex_=(sun-dt.timedelta(days=1)).isoformat()
        for ps_,pe_,fs_,bs_,bo_ in PH:
            if pe_!=ex_:break
            ex_=(dt.date.fromisoformat(ps_)-dt.timedelta(days=1)).isoformat()
            if i==1 and not bo_:continue
            if k in (fs_ if i==0 else bs_):n_+=1
            else:break
        return n_
    SKL=lambda n_:'새로' if n_==1 else f'계속 {n_}주째'
    BK=[k for k in re.findall(r'^(R\d \S+)',B,re.M) if k!='R1 제외' and not (C.get('docs') is False and k.startswith('R2 '))];bnew=sum(1 for k in BK if STK(k,1)==1)
    # v1.3 받은 결과(팀별) — 자료마다 팀장이 확인 줄을 쓴다(finalize 검증). 자료가 안 왔거나 낡으면 운영관리 발견 F-OPS-6·F-OPS-7-*
    now=dt.datetime.fromisoformat(os.environ['CEO_NOW']) if os.environ.get('CEO_NOW') else dt.datetime.now(K)
    try:now=dt.datetime.fromisoformat(str(I.get('trig_at'))) if I.get('trig_at') else now
    except Exception:pass
    if now.tzinfo is None:now=now.replace(tzinfo=K)
    def PD(s):
        q=re.sub(r'(\.\d{6})\d+',r'\1',str(s or '').replace('Z','+00:00'))
        if not re.match(r'^\d{4}-\d{2}-\d{2}T',q):return None
        z=dt.datetime.fromisoformat(q);return z if z.tzinfo else z.replace(tzinfo=dt.timezone.utc)
    tl=I.get('trig') or [];late=[];fail=[];unk=[];okn=[];hasc=any('cron' in x for x in tl)
    for x in tl:
        if not x.get('enabled') or not x.get('recurring'):continue
        nm=CLN(x.get('name') or x.get('id'),40)
        if '주간 팀장회의' in str(x.get('name') or '') or x.get('id')=='trig_01XvqwKG2gt7EKLEVMHGYR6Y':okn.append(nm+'(이 회의 — 지금 실행 중)');continue
        ex=CRONPREV(x.get('cron'),now-dt.timedelta(minutes=20))
        try:lf=PD(x.get('last_fired'));cr_=PD(x.get('created'))
        except Exception:lf=cr_=None
        ls=re.sub(r'^ROUTINE_RUN_STATUS_','',str(x.get('last_status') or ''))
        if ex is None:unk.append(f'{nm}: 주기 읽기 못함');continue
        if cr_ and cr_>ex:okn.append(nm+'(첫 실행 전)');continue
        if lf is None:late.append(f'{nm}: 실행 기록 없음(예정 {ex.astimezone(K):%m/%d %H:%M})');continue
        if lf<ex-dt.timedelta(minutes=10):late.append(f'{nm}: 안 돎·늦음(예정 {ex.astimezone(K):%m/%d %H:%M}, 마지막 {lf.astimezone(K):%m/%d %H:%M})');continue
        if re.search(r'FAIL|ERROR|TIMEOUT|TIMED_OUT|CANCEL',ls):fail.append(f'{nm}: 마지막 실행 {ls}({lf.astimezone(K):%m/%d %H:%M})');continue
        if ls not in('SUCCEEDED','RUNNING'):unk.append(f'{nm}: 마지막 실행 상태 {ls or "없음"}({lf.astimezone(K):%m/%d %H:%M}) — 확인 필요');continue
        okn.append(nm)
    nrec=len(late)+len(fail)+len(unk)+len(okn)
    if not tl:ib('S-OPS-1','운영관리','예약 작업 출근부','예약 작업 목록을 읽지 못함 — 확인 필요')
    elif not hasc:ib('S-OPS-1','운영관리','예약 작업 출근부','예약 작업 실행 기록(주기·마지막 실행) 칸이 없음 — 확인 필요')
    else:ib('S-OPS-1','운영관리','예약 작업 출근부',f"켜진 반복 작업 {nrec}개 — 제때 {len(okn)} · 안 돎·늦음 {len(late)} · 실패 {len(fail)}"+(f" · 확인 필요 {len(unk)}" if unk else '')+(' (목록 끝까지 못 읽음 — 확인 필요)' if C.get('trig') is False else ''),late+fail+unk+(['제때: '+', '.join(okn)] if okn else []))
    if late or fail or unk:fd('F-OPS-6','운영관리',f'예약 작업 출근부: 안 돎·늦음 {len(late)}건 · 실패 {len(fail)}건'+(f' · 확인 필요 {len(unk)}건' if unk else '')+' — '+' / '.join((late+fail+unk)[:3]))
    ib('S-OPS-2','운영관리','자동 운영 코어·결과 알림',f"코어 정상 {okc}/{len(days)} · 알림 줄 {nal}건(푸시 대상 {ptot}) · 독립 대조 일치 {nmt}/{len(days)} · 결과 알림이 통합점검 대시보드에 옮김 {ncc}/{len(RN)}일",CDL)
    if noc:fd('F-OPS-7-alert','운영관리','코어 결과가 있는데 결과 알림이 통합점검 대시보드에 옮기지 않은 날: '+', '.join(noc))
    def stv(x,lab):
        for s in x.get('status') or []:
            if isinstance(s,dict) and s.get('label')==lab:return NW(s.get('value')),s.get('tone')
        return None,None
    CH=[];cbad=[];nfo=0;nst=0;nsv=0;DEC={};NEED={};hl=None;cf={};cl_={}
    for d in days:
        x=RN.get(d)
        if not x:CH.append(f'{MDd(d)} 기록 없음');cbad.append(MDd(d)+' 기록 없음');continue
        v_,tn=stv(x,'점검 상태');fl=x.get('filings') or {};mk=x.get('market') or {};stl=mk.get('stale') in(True,'True','true');sv=bool(x.get('saveticker'))
        nfo+=fl.get('status')=='OK';nst+=stl;nsv+=sv
        if tn!='ok':cbad.append(f'{MDd(d)} 점검 상태 {v_ or "확인 필요"}')
        CH.append(f"{MDd(d)} {str(x.get('runAt') or '')[11:16]} · 점검 상태 {v_ or '확인 필요'} · 공시 수집 {fl.get('status') or '확인 필요'}(새 {fl.get('newCount','?')}) · SAVE 메모 {mk.get('reportDate') or '없음'}{'(낡음)' if stl else ''} · saveticker {'수집' if sv else '미수집'}")
        if x.get('headline'):hl=(d,x['headline'])
        for z in x.get('decisions') or []:
            t_=NW((z or {}).get('title')) if isinstance(z,dict) else ''
            if t_ and t_ not in DEC:DEC[t_]=d
        for z in x.get('needs') or []:
            g=NW((z or {}).get('tag')) if isinstance(z,dict) else ''
            if g:NEED[g]=NEED.get(g,0)+1
        for z in x.get('claims') or []:
            if isinstance(z,dict) and str(z.get('id','')).startswith('EXT-'):cf.setdefault(z['id'],z.get('state'));cl_[z['id']]=z.get('state')
    rok=C.get('runs') is not False
    ib('S-OPS-3','운영관리','통합점검 실행 상태',(f"기록 {len(RN)}/{len(days)}일 · 점검 상태 정상 {len(RN)-len([z for z in cbad if '점검 상태' in z])} · 공시 수집 OK {nfo} · SAVE 메모 낡음 {nst}일 · saveticker 수집 {nsv}/{len(RN)}일") if rok else '통합점검 기록(대시보드 runs)을 읽지 못함 — 확인 필요',CH if rok else [])
    if not rok:fd('F-OPS-7-chk','운영관리','통합점검 기록 읽기 실패 — 이번 주 통합점검 결과를 팀에 전달 못 함')
    elif cbad:fd('F-OPS-7-chk','운영관리','통합점검: '+', '.join(cbad[:4]))
    ib('S-RES-1','투자리서치','통합점검 내용',(f"기록 {len(RN)}/{len(days)}일 · 최신({MDd(hl[0])}) {CLN(hl[1],110)} · 결정 요청 {len(DEC)}건(같은 제목 1번) · 확인 필요 주제 {len(NEED)}개" if hl else '이번 주 통합점검 기록 없음') if rok else '통합점검 기록을 읽지 못함 — 확인 필요',
       ([f'결정 요청 {MDd(d)}: {t_}' for t_,d in sorted(DEC.items(),key=lambda z:z[1])][-9:]+([f'결정 요청 앞선 {len(DEC)-9}건 생략(같은 주 앞날짜)'] if len(DEC)>9 else [])+(['확인 필요 주제(일수): '+' · '.join(f'{k} {v}' for k,v in sorted(NEED.items(),key=lambda z:-z[1]))] if NEED else [])
        +(['외부 주장 상태 변화(주간): '+' · '.join(f'{k} {cf[k]}→{cl_[k]}' for k in cl_ if cf.get(k)!=cl_[k])] if any(cf.get(k)!=cl_[k] for k in cl_) else [])) if rok else [])
    ib('S-RES-4','투자리서치','자동 운영 코어 알림 내용',f"이번 주 코어 알림 {len(AL)}종(같은 종목·조건은 마지막 날 1줄) · 푸시된 것 {sum(1 for v in AL.values() if v[2])}종",[f"{MDd(v[0])} {v[1]}"+(' (푸시)' if v[2] else '') for k,v in sorted(AL.items(),key=lambda z:(z[1][0],z[0]),reverse=True)][:14])
    sm=R('workspace/outputs/save-daily-offline-replay/LATEST_MARKET_ENV_MEMO.md')
    if sm is None:ib('S-RES-2','투자리서치','SAVE 시장환경 메모','메모를 받지 못함 — 확인 필요');fd('F-OPS-7-save','운영관리','SAVE 시장환경 메모를 받지 못함')
    else:
        sm=sm.replace('\r\n','\n');rd=re.search(r'리포트 날짜:\s*(\d{4}-\d{2}-\d{2})',sm);cr=re.search(r'메모 생성:\s*(\d{4}-\d{2}-\d{2})(?:\s+(\d{1,2}:\d{2}))?',sm)
        SC={}
        for ch in re.split(r'(?m)^## ',sm)[1:]:
            h_,_,b_=ch.partition('\n');SC[h_.strip()]=[NW(l[2:]) for l in b_.split('\n') if l.startswith('- ')]
        g_=lambda p:next((v for k,v in SC.items() if k.startswith(p)),[])
        ev,hd,li=g_('시장 관련 이벤트'),g_('보유'),g_('알려진 한계');crd=cr.group(1) if cr else ''
        ib('S-RES-2','투자리서치','SAVE 시장환경 메모(최신)',f"리포트 {rd.group(1) if rd else '확인 필요'} · 생성 {crd or '확인 필요'}{' '+cr.group(2) if cr and cr.group(2) else ''} · 시장 이벤트 {len(ev)}건 · 보유·산업 {len(hd)}줄 · 참고 자료(판단 규칙 아님)",['이벤트: '+z for z in ev[:5]]+['보유·산업: '+z for z in hd[:6]]+(['한계: '+li[0]] if li else []))
        if not crd or crd<(t-dt.timedelta(days=1)).isoformat():fd('F-OPS-7-save','운영관리',f'SAVE 시장환경 메모 낡음(생성 {crd or "확인 필요"})')
    lx=R('docs/claude/external-claims-ledger.md');EX={}
    for m_ in re.finditer(r'^### (EXT-(\d{8})-\d{2}) · (.*?) · 상태: (.*)$',(lx or '').replace('\r\n','\n'),re.M):EX[m_.group(1)]=(f'{m_.group(2)[:4]}-{m_.group(2)[4:6]}-{m_.group(2)[6:]}',NW(m_.group(3)),NW(m_.group(4)))
    if lx is None and isinstance(PS0.get('ext'),dict):NS['ext']=PS0['ext']
    if lx is None:ib('S-RES-3','투자리서치','외부 자료 원장','원장을 받지 못함 — 확인 필요');fd('F-OPS-7-ext','운영관리','외부 자료 원장을 받지 못함')
    else:
        pe_=PS0.get('ext') if isinstance(PS0.get('ext'),dict) else None
        NS['ext']={k:CLN(v[2],80) for k,v in EX.items() if not v[2].startswith('보관')}
        nw_=[k for k,v in EX.items() if PS<=v[0]<=PE];r0=[k for k in nw_ if EX[k][1].startswith('R0')];chg=[(k,pe_[k],EX[k][2]) for k in EX if pe_ and k in pe_ and pe_[k]!=CLN(EX[k][2],80)]
        ib('S-RES-3','투자리서치','외부 자료 PDF 원장',f"이번 주 새 {len(nw_)}건(기록만 R0 {len(r0)}) · 상태 바뀜 {len(chg) if pe_ is not None else '첫 기준(다음 주부터 비교)'} · 대기 {sum(1 for v in EX.values() if v[2].startswith('대기'))}건(표시 중 {sum(1 for v in EX.values() if '표시 중' in v[2])}) · 확정 {sum(1 for v in EX.values() if v[2].startswith('확정'))}건 · 전체 {len(EX)}건",
           [f'새 {k} {EX[k][1]} · {EX[k][2]}' for k in nw_ if k not in r0][:10]+[f'바뀜 {k} {a} → {b}' for k,a,b in chg][:6])
    wr=wl.get('weeklyRun') if isinstance(wl.get('weeklyRun'),dict) else {};wk_=wr.get('weakest') if isinstance(wr.get('weakest'),dict) else {}
    AC_={'candidates-add':'후보 추가','add':'편입','swap':'교체','remove':'제외','none':'변경 없음','hold':'보류'}
    ib('S-RES-5','투자리서치','관심 명단 주간 재채점',(f"{wr.get('date')} 재채점(기준 {wr.get('basis','?')}) — "+(CLN(wr.get('reason'),130) if str(wr.get('reason') or '').startswith(AC_.get(wr.get('action'),'@')) else f"{AC_.get(wr.get('action'),wr.get('action'))} · {CLN(wr.get('reason'),110)}") if wr else '재채점 기록(weeklyRun) 없음 — 확인 필요'),
       ([f"최약 {wk_.get('code')} {wk_.get('score')}점(기준선 {wk_.get('threshold')}, {wk_.get('ageDays')}일째)"] if wk_ else [])+[f"관심 명단 {len(wl.get('members') or [])}종목: {', '.join(str((m or {}).get('code')) for m in wl.get('members') or [] if isinstance(m,dict))} · 채점 후보 {len(wl.get('candidates') or [])}"]
       +([f"유지 보호: {', '.join(map(str,wr.get('protect')))}"] if wr.get('protect') else [])+([f"제외 대기: {', '.join(map(str,wr.get('pendingKill')))}"] if wr.get('pendingKill') else [])+[f'명단 기록 {z}' for z in wh][:6])
    if not inp(str(wr.get('date') or '')):fd('F-OPS-7-wl','운영관리',f"관심 명단 주간 재채점 이번 주 실행 기록 없음(마지막 {wr.get('date') or '없음'})")
    nsn=NSD(I.get('nsd_files'));fsat=[d for d in [(sun+dt.timedelta(days=i)) for i in range(7)] if d.weekday()==5 and d.day<=7]
    if I.get('nsd_files') is None:ib('S-RES-6','투자리서치','Next 샌디스크 발굴','발굴 파일 목록을 읽지 못함 — 확인 필요')
    elif not nsn:ib('S-RES-6','투자리서치','Next 샌디스크 발굴','발굴 파일 없음')
    else:
        nt_=R('docs/claude/'+nsn);nf=FM(nt_);nd_=nsn[18:28];n0=[]
        m_=re.search(r'(?ms)^## N-0[^\n]*\n(.*?)(?=^## )',(nt_ or '').replace('\r\n','\n'))
        if m_:n0=[NW(re.sub(r'^(-|\d+\.)\s+','',l)).replace('**','') for l in m_.group(1).split('\n') if re.match(r'^(-|\d+\.)\s',l)][:4]
        ib('S-RES-6','투자리서치','Next 샌디스크 발굴',f"최근 발굴 {nd_}({nf['status'] or '상태 확인 필요'}{', 다음 '+nf['valid'] if nf['valid'] else ''}) — {CLN(nf['sum'],130) if nt_ else '파일 받지 못함'} · 이번 주 새 발굴 {'있음' if inp(nd_) else '없음(월간 발굴 = 매월 첫 토요일)'}",['결론: '+z for z in n0])
    if fsat and (not nsn or nsn[18:28]<fsat[0].isoformat()) and I.get('nsd_files') is not None:fd('F-OPS-7-nsd','운영관리',f'Next 샌디스크 월간 발굴 파일 없음({fsat[0].isoformat()} 예정)')
    nwn=NSW(I.get('nsdw_files'),sun,sat);nwk=R('workspace/outputs/next-sandisk-weekly/'+nwn) if nwn else None;fsd=[d.isoformat() for d in fsat]
    for b_ in IB:
        if b_['id']!='S-RES-6':continue
        if nwk:
            f_=FM(nwk);mm_=re.search(r'(?ms)^## 결과\s*\n(.*?)(?=^## |\Z)',nwk.replace('\r\n','\n'))
            rs_=[NW(l[2:]) for l in (mm_.group(1).split('\n') if mm_ else []) if l.startswith('- ')]
            b_['sum']=CLN(f"주간 점검 {MDd(nwn[:10])}: {CLN(f_['sum'],110)} · "+b_['sum'],320);b_['items']=([CLN('주간: '+z,170) for z in rs_[:8]]+b_['items'])[:26]
        elif PE not in fsd:b_['sum']=CLN(f'주간 점검 {MDd(PE)} 결과 파일 없음 · '+b_['sum'],320)
    if not nwk and PE not in fsd:fd('F-OPS-7-nsdw','운영관리',f'Next 샌디스크 주간 점검 결과 파일 없음({PE}) — 주간 점검이 안 돌았거나 파일을 쓰지 못함')
    pr_=PRE(I.get('preopen'),sun,sat);PI=[]
    for n in pr_:
        tx_=R('workspace/outputs/pre-open/'+n);f_=FM(tx_);q=re.search(r'(?ms)^## 확인 필요\s*\n(.*?)(?=^## |\Z)',(tx_ or '').replace('\r\n','\n'));k_=len([l for l in (q.group(1).split('\n') if q else []) if l.startswith('- ')])
        PI.append(f"{n}: {CLN(f_['sum'],110) if tx_ else '받지 못함'}"+(f' · 확인 필요 {k_}줄' if k_ else ''))
    ib('S-RES-7','투자리서치','개장 전 점검 기록',f"이번 주 {len(pr_)}건" if I.get('preopen') is not None else '개장 전 점검 폴더 목록을 읽지 못함 — 확인 필요',PI)
    mon=(sun+dt.timedelta(days=1)).isoformat()
    if I.get('preopen') is not None and not any(n.startswith(mon+'-monday') for n in pr_):fd('F-OPS-7-pre','운영관리',f'월요일 개장 전 점검 기록 없음({mon})')
    ib('S-OPS-4','운영관리','개발 관제판 점검(R1~R6)',(f'관제판 점검 발견 {bn}건' if bn is not None else '관제판 점검 끝내지 못함')+(' · '+' · '.join(f'{k} {v}' for k,v in sorted({r_:len(re.findall("^"+r_+" ",B,re.M)) for r_ in ('R1','R2','R4','R5','R6')}.items()) if v) if bn else ''),[(SKL(STK(' '.join(l.split()[:2]),1))+' · '+l if re.match(r'^R\d ',l) and not l.startswith('R1 제외') else l) for l in B.split('\n') if re.match(r'^(R\d |미점검 )',l)][:8])
    ib('S-OPS-5','운영관리','PC 상태 점검',f'PC 상태 {host}',A[:5])
    STC={};
    for k,v in T.items():STC.setdefault(v.get('status'),[]).append(k)
    soon=[f"{k}(기한 {v.get('deadline')})" for k,v in T.items() if v.get('status') in('waiting','planned','paused') and ti<=str(v.get('deadline') or '')[:10]<=te]
    ib('S-RND-1','연구개발','개발 관제판 작업',f"진행 {len(STC.get('active',[]))} · 대기 {len(STC.get('waiting',[]))} · 계획 {len(STC.get('planned',[]))} · 멈춤 {len(STC.get('paused',[]))} · 결정함 {len(dec)} · 이번 주 끝냄 {len(done)}"+(' (일부만 읽음)' if C.get('tasks') is False else ''),
       (['진행: '+', '.join(f"{k}({CLN((T[k].get('plain') or T[k].get('title')),30)})" for k in STC.get('active',[]))] if STC.get('active') else [])+(['결정함: '+', '.join(dec)] if dec else [])+(['다음 7일 기한: '+', '.join(soon[:6])] if soon else [])+(['이번 주 끝냄 '+str(len(done))+'건: '+', '.join(sorted(done)[:10])+(f' 외 {len(done)-10}건' if len(done)>10 else '')] if done else []))
    ib('S-RND-2','연구개발','개발 자동 실행·판단 성적 채점',f'최근 개발 실행 {dvs} · 판단 성적 채점 주간 출력 {sc}')
    ib('S-LEG-1','법률','규칙·정책·예약 지시문 변경',f"{' · '.join(lg)} · 정책 파일 수정 {pcs} · 예약 지시문·설정 수정 {tus}",(['예약 작업 변경: '+', '.join(CLN(z,40) for z in tu[:8])] if tu else [])+(['정책 파일: '+', '.join(pc[:6])] if pc else []))
    WDm=I.get('week_docs')
    if not isinstance(WDm,dict):ib('S-OPS-D','운영관리','이번 주 점검·검토 문서','문서 목록을 읽지 못함 — 이번 주 검토 문서를 팀에 나누지 못함(확인 필요)')
    else:
        sel=WDOCS(WDm);GD={k:[] for k in TEAMS}
        for i,n in enumerate(sel):
            tx_=R('docs/claude/'+n) if i<60 else None;f_=FM(tx_) if tx_ else {}
            GD[ROUTE(n,f_)].append(f"{n}: {CLN(f_.get('sum'),120)}"+(f" ({f_['status']})" if f_.get('status') and f_.get('status')!='current' else '') if tx_ else n)
        for k,code_ in zip(TEAMS,('OPS','RES','RND','LEG')):
            if GD[k]:
                full=[z for z in GD[k] if ': ' in z];nm_=[z for z in GD[k] if ': ' not in z];sh=full[:24]
                ib(f'S-{code_}-D',k,'이번 주 새로·바뀐 점검·검토 문서',f'{len(GD[k])}건(문서 머리 요약 · 원문은 docs/claude)',sh+([f'요약 생략 {len(full)-len(sh)+len(nm_)}건: '+', '.join([z.split(":")[0] for z in full[24:]]+nm_)] if len(full)>24 or nm_ else []))
    for f_ in F:f_['weeks']=STK(re.sub(r'-\d{4}$','',f_['id']),0)
    SO={'운영관리':0,'투자리서치':1,'연구개발':2,'법률':3};IB.sort(key=lambda z:(SO[z['team']],z['id'].endswith('-D'),z['id']))
    col='🔴' if red else '🟠' if any(f['sev']=='🟠' for f in F) else '🟢'
    out={'id':'ceo-'+today,'period':[PS,PE],'color':col,'findings':F,'inbox':[f"{b_['id']} [{b_['team']}] {b_['title']} | {b_['sum'][:120]}" for b_ in IB],'prev':{'id':pid,'defaulted':[x['key'] for x in exp],'waiting':[x['key'] for x in wait]},'board_decisions':dec}
    S=[f"## 주간 경영보고 {today} (기간 {PS}~{PE}) — 회사 상태 {col} · {{{{N}}}}",f'<!-- id: ceo-{today} -->',
    f"### 1. 운용 (코어 파일 값 그대로, 기준 {X.get('run_day_kst','확인 필요')} · 모드 {X.get('decision_mode','확인 필요')})",
    f"- 노출 E {E} ({S7.get('band','확인 필요')}, 세션 {S7.get('session','확인 필요')}) · 멈춤: {pa} · 계좌 검토선 {ac.get('state','확인 필요')}(첫 쿠션 {cu})",
    f"- 종목 고점 검토: {pk}",f"- 이번 주 주문표 {tk}건 · 열린 주문표 {len(X.get('open_tickets') or [])}건 · 결과 기록 {len(X.get('outcomes') or [])}건",
    '### 2. 팀별',
    f"- 운영관리: 코어 정상 {okc}/{len(days)}(폴더 있는 날 {len([d for d in days if d in cd]) if cd is not None else '확인 필요'}) · 예외 알림 {ptot}건 · 코어가 요청한 사람 손(주문 입력 제외) {len(touch)}건 · PC 상태 {host} · 관제판 점검 발견 {bn if bn is not None else '불완전'}",
    f"- 투자리서치: 연구 기록 OK {rrok}/{len(days)} · 공식 사실 {facts}건 · 이번 주 카드 수락 {', '.join(ca) or '없음'} · 관심 명단 변경 {', '.join(wh) or '없음'} · 카드 {json.dumps(roles,ensure_ascii=False)}",
    f"- 연구개발: 진행 개발 {na}/3 · 권한·한도 변경 {len(auth)}/1 · 이번 주 완료 {len(done)}건 · 최근 개발 실행 {dvs} · 채점 주간 출력 {sc}",
    f"- 법률: {' · '.join(lg)} · 정책 파일 수정 {pcs} · 예약 지시문·설정 수정 {tus}",
    '받은 결과(팀장마다 자기 팀 줄을 모두 확인 — 확인: 특이 없음 / 제안 있음 / 확인 필요):',*[z for b_ in IB for z in [f"- 받음 [{b_['team']}] {b_['id']} {b_['title']} | {b_['sum']} | 확인: {{{{RV:{b_['id']}}}}}"]+[f'  - {y}' for y in b_['items']]],
    '팀장 제안:','{{PROPOSALS}}',
    '### 3. 감사실 (원문 그대로)',f"- Judge 보고서(이번 주 수정): {' / '.join(jd) or '없음'} · 파이프라인 최근 실행 {dvs}",f"- 독립 대조 일별: {' · '.join(tv)}",f'- C1 누계(관제판 redesign-t2 인용): "{c1}"',
    '### 4. 사장님 결정',f"- 관제판 결정함 대기 {len(dec)}건: {', '.join(dec) or '없음'}",*wl4,'{{DECISIONS}}',
    '### 5. 알림만',*pl,*[f"- {x['id']} [{x['team']}] {'(참고) ' if x['sev']=='ℹ' else ''}{x['text']} ⟨{SKL(x['weeks'])}⟩" for x in F],'{{QUEUE}}',
    '### 6. 다음 주',*([f'- {x}' for x in sorted(nx)] or ['- 일정 없음(일정표·실적 달력·일회성 예약 기준)']),
    '### 7. 관제판 점검 원문','```text',B,'```',
    '<!-- ceo-state '+json.dumps(NS,ensure_ascii=False)+' -->','']
    TM=os.path.dirname(os.path.abspath(inj));open(TM+'/section.md','w',encoding='utf-8',newline='\n').write('\n'.join(S))
    json.dump({**out,'bnew':bnew,'inbox':[{'id':b_['id'],'team':b_['team'],'title':b_['title']} for b_ in IB],'prev_D':len([x for x in DL if x['sec']==pid]) if pid else None,'waiting_n':len(wait),'prev_state':PS0,'state':NS,'board_n':bn,'prev_path':fp(RP) if pvb is not None else None,'today':today},open(TM+'/run.json','w',encoding='utf-8'),ensure_ascii=False)
    print(json.dumps(out,ensure_ascii=False));sys.exit()
if mode=='finalize':
    TM=sys.argv[2];U=json.load(open(TM+'/run.json',encoding='utf-8'));S=open(TM+'/section.md',encoding='utf-8').read();V=[];today=U['today'];td=dt.date.fromisoformat(today)
    NM=td+dt.timedelta(days=(6-td.weekday())%7 or 7);DEF=NM-dt.timedelta(days=1)
    try:G=json.load(open(TM+'/fill.json',encoding='utf-8'))
    except Exception:G={};V.append('fill.json 없음·깨짐')
    def SZ(o):return {k:SZ(v) for k,v in o.items()} if isinstance(o,dict) else [SZ(v) for v in o] if isinstance(o,list) else o.replace('{{','{ ').replace('}}',' }').replace('-->','->') if isinstance(o,str) else o
    G=SZ(G) if isinstance(G,dict) else {}
    sids={b['id'] for b in U.get('inbox') or []};ids={f['id'] for f in U['findings']}|sids;PR=G.get('proposals') if isinstance(G.get('proposals'),list) else [];DS=G.get('decisions') if isinstance(G.get('decisions'),list) else []
    if not isinstance(G.get('proposals'),list) or not isinstance(G.get('decisions'),list):V.append('proposals·decisions 목록 아님')
    used={};seen=set();byt={k:[] for k in TEAMS};need=set()
    for p in PR:
        if not isinstance(p,dict) or p.get('team') not in TEAMS:V.append('팀 이름 오류: '+NW(p)[:40]);continue
        seen.add(p['team'])
        if p.get('none'):continue
        fs=p.get('fids') if isinstance(p.get('fids'),list) else []
        if not fs or any(f not in ids for f in fs):V.append(f"{p['team']} 제안 근거 F-id 없음·모름: {fs}")
        for f in fs:
            if used.get(f,p['team'])!=p['team']:V.append(f'F-id 두 팀 사용: {f}')
            used[f]=p['team']
        if not isinstance(p.get('rank'),int) or isinstance(p.get('rank'),bool) or not 1<=p['rank']<=5:V.append(f"{p['team']} 순위 1~5 아님");p['rank']=9
        if not NW(p.get('text')):V.append(f"{p['team']} 제안 문장 없음")
        if p.get('decision') is True:need|=set(fs)
        wl=p.get('with') if isinstance(p.get('with'),list) else ([] if p.get('with') in (None,'') else None)
        if wl is None or any(x not in TEAMS or x==p['team'] for x in wl):V.append(f"{p['team']} 협조 팀 오류: {NW(p.get('with'))[:30]}");wl=[x for x in (wl or []) if x in TEAMS and x!=p['team']]
        p['with']=list(dict.fromkeys(wl))
        if p['with'] and not NW(p.get('ask')):V.append(f"{p['team']} 협조 부탁 문장 없음")
        byt[p['team']].append(p)
    for k in TEAMS:
        if k not in seen:V.append(f'{k} 팀장 줄 없음')
    RV=G.get('reviews') if isinstance(G.get('reviews'),list) else None
    if RV is None and sids:V.append('reviews 목록 없음')
    RM={};allf={f for t_ in byt.values() for p in t_ for f in p.get('fids') or []}
    for r in RV or []:
        s_=r.get('src') if isinstance(r,dict) else None
        if s_ not in sids:V.append(f'확인 줄의 받은 결과 번호 모름: {NW(s_)[:20]}');continue
        if s_ in RM:V.append(f'확인 줄 두 번: {s_}');continue
        rd=r.get('read');nt=CLN(r.get('note'),200)
        if rd not in('특이 없음','제안 있음','확인 필요'):V.append(f'{s_} 확인 값 오류: {NW(rd)[:12]}');rd='확인 필요'
        if rd!='특이 없음' and not nt:V.append(f'{s_} 확인 메모 없음')
        if rd=='제안 있음' and s_ not in allf:V.append(f'{s_} "제안 있음"인데 그 번호를 근거로 쓴 제안 없음')
        if rd=='특이 없음' and s_ in allf:V.append(f'{s_} 제안 근거인데 확인이 "특이 없음"')
        RM[s_]=(rd,nt)
    miss=sorted(sids-set(RM))
    if miss:V.append(f'팀장 확인 없는 받은 결과 {len(miss)}건: '+','.join(miss[:6]))
    dfs=set();DD=[]
    for i,d in enumerate(DS):
        fs=d.get('fids') if isinstance(d,dict) and isinstance(d.get('fids'),list) else []
        if not isinstance(d,dict) or not NW(d.get('question')) or not NW(d.get('recommend')):V.append(f'결정 {i+1} 질문·권장 없음');continue
        if not fs or any(f not in need for f in fs):V.append(f'결정 {i+1} 근거가 "결정 필요" 제안의 F-id가 아님: {fs}')
        dfs|=set(fs)
        try:dd=dt.date.fromisoformat(str(d.get('deadline') or DEF.isoformat()))
        except Exception:V.append(f'결정 {i+1} 기한 날짜 오류');dd=DEF
        if dd<=td:V.append(f'결정 {i+1} 기한이 오늘 이전');dd=DEF
        src=sorted([p for t_ in byt.values() for p in t_ if set(p.get('fids') or [])&set(fs)],key=lambda p:p['rank'])
        rk=src[0]['rank'] if src else 5;lead=src[0]['team'] if src else '';wth=sorted({w for p in src for w in p.get('with') or []}-{lead},key=TEAMS.index)
        DD.append((dd<DEF,dd,rk,i,d,lead,wth))
    if need-dfs:V.append('"결정 필요" 제안인데 결정 줄 없음: '+','.join(sorted(need-dfs)))
    DD.sort(key=lambda z:(not z[0],z[2],z[1],z[3]))
    Dl=[];hot=0
    for n,(h_,dd,rk,i,d,lead,wth) in enumerate(DD,1):
        hot+=h_;Dl.append(f"- {'⚠ ' if h_ else ''}D{n} {NW(d['question'])} · 권장 {NW(d['recommend'])}"+(f" · 선택지 {NW(d['options'])}" if NW(d.get('options')) else '')+((f" · 주관 {lead}"+(f"(협조 {','.join(wth)})" if wth else '')) if lead else '')+f" · 무응답 시 기본값 현행 유지 · 기한 {dd.isoformat()} · 답 양식 `결정 {U['id']}: D{n} <선택>`")
    Pl=[];Q=[]
    for k in TEAMS:
        ps=sorted(byt[k],key=lambda p:p['rank'])
        if not ps:Pl.append(f'- [{k}] 제안 없음')
        for j,p in enumerate(ps):
            ln=f"- [{k}] {NW(p.get('text'))} — 근거 {', '.join(p.get('fids') or [])} · 순위 {p['rank'] if p['rank']!=9 else '?'} · {'결정 필요' if p.get('decision') is True else '알림만'}"+(f" · 협조 {','.join(p['with'])}: {NW(p.get('ask'))}" if p.get('with') else '')
            (Pl if j<3 else Q).append(ln if j<3 else ln.replace('- [','- 대기열 [',1))
    n=len(Dl);dh=(U.get('prev_state') or {}).get('d_hist') or [];dh=(dh+[n])[-6:];pd=U.get('prev_D')
    LK={}
    for k in TEAMS:
        for p in byt[k]:
            for w in p.get('with') or []:LK[(k,w)]=LK.get((k,w),0)+1
    lks='- 팀 간 연계: '+(', '.join(f'{a}→{b} {c}건' for (a,b),c in sorted(LK.items(),key=lambda z:(TEAMS.index(z[0][0]),TEAMS.index(z[0][1])))) or '없음')
    S=S.replace('{{PROPOSALS}}','\n'.join(Pl)+'\n'+lks).replace('{{DECISIONS}}','\n'.join(Dl) or '- 이번 주 새 결정 없음').replace('{{QUEUE}}\n','\n'.join(Q)+('\n' if Q else '')).replace('{{N}}',f"사장님 결정 {n}건({'⚠ ' if hot else ''}급함 {hot}건 · 답 대기 {U.get('waiting_n',0)}건 · 지난 보고 {str(pd)+'건' if pd is not None else '없음'})")
    if len(dh)>=3 and dh[-3]<dh[-2]<dh[-1]:S=S.replace('### 6. 다음 주',f"- 결정 건수 3주 연속 증가({dh[-3]}→{dh[-2]}→{dh[-1]}) — 팀 제안 기준 점검 필요(법률팀·Cowork)\n### 6. 다음 주")
    for s_ in sids:S=S.replace('{{RV:'+s_+'}}',(RM[s_][0]+(' — '+RM[s_][1] if RM[s_][1] else '')) if s_ in RM else '없음(팀장 확인 누락)')
    if '{{' in S:V.append('자리표시 남음')
    if V:S=S.replace('<!-- id: ','⚠ 형식 검증 실패: '+' / '.join(V[:4])+'\n<!-- id: ',1)
    st=U['state'];st['d_hist']=dh;S=re.sub(r'<!-- ceo-state \{.*\} -->',lambda _:'<!-- ceo-state '+json.dumps(st,ensure_ascii=False)+' -->',S)
    HD='---\nid: ceo-weekly-report\ntype: report\nstatus: current\nas_of: 각 주 절 머리(최신 = 맨 아래)\ntickers: [ALL]\nevidence: 코어·대조·채점·관제판 값은 결과 파일 그대로(등급은 원 파일 따름) / 팀장 제안·결정 문장 = 주간 팀장회의 LLM(근거 F-id) / 판정·매매 근거 아님\nconsumers: [사장(사용자) · 다음 주간 팀장회의(결정·답 줄) · Cowork(결정 ceo-<날짜> 처리) · 2단계 평가(docs/claude/company-org-plan-2026-10-19.md 7절) · redesign-t4(법률 정리 안건)]\nsummary: 투자_V2 주간 팀장회의 → 사장 보고. 매주 일요일 절을 덧붙인다(덧붙이기만). 조직·규칙 = docs/claude/company-org-plan-2026-10-19.md. 답 줄 형식 = 그 결정 줄 바로 아래 "  - 답: <원문>(<YYYY-MM-DD HH:MM KST>, Cowork)". 답이 없고 기한이 지난 결정은 다음 회의가 5절에 "기본값 기록"으로 닫는다.\n---\n\n# 주간 경영보고 (투자_V2)\n'
    pp=U.get('prev_path');pb=open(pp,'rb').read() if pp else b''
    sb=S.encode('utf-8');body=(pb+(b'' if pb.endswith(b'\n') else b'\n')+b'\n'+sb) if pb else (HD+'\n').encode('utf-8')+sb
    if not body.startswith(pb):V.append('덧붙이기 검사 실패')
    os.makedirs('/mnt/user-data/outputs',exist_ok=True);open('/mnt/user-data/outputs/ceo-weekly-report.md','wb').write(body)
    d8=today.replace('-','');open(f'/mnt/user-data/outputs/ceo-weekly-{d8}.txt','w',encoding='utf-8',newline='\n').write(f"docs(claude): ceo weekly report {today} (weekly team-lead meeting)\ndocs/claude/ceo-weekly-report.md\n")
    fi=sum(1 for f in U['findings'] if f.get('sev')=='ℹ');fc=len(U['findings'])-fi;fn=sum(1 for f in U['findings'] if f.get('sev')!='ℹ' and f.get('weeks',1)==1);bn=U.get('board_n');bw=U.get('bnew');pre=f'⚠ 이번 주 답 필요 {hot}건 · ' if hot else ''
    push=f"{pre}주간 경영보고 {today[5:].replace('-','/')}: {U['color']} · 결정 {n}건(답 대기 {U.get('waiting_n',0)}) · 새 발견 {fn}건(계속 {fc-fn}건{f' · 참고 {fi}건 별도' if fi else ''}) · 관제판 점검 {(f'새로 {bw}건(전체 {bn}건)' if bw is not None else str(bn)+'건') if bn is not None else '불완전'}"+(f" · 받은 결과 {len(sids)}건(팀장 확인 {len(RM)})" if sids else '')+(' (형식 확인 필요)' if V else '')+" — 대시보드 '주간 팀장회의'"
    print(json.dumps({'validation':V or 'OK','D':n,'hot':hot,'push':push,'report':'/mnt/user-data/outputs/ceo-weekly-report.md','report_sha256':hashlib.sha256(body).hexdigest(),'pending':f'/mnt/user-data/outputs/ceo-weekly-{d8}.txt','pending_name':f'ceo-weekly-{d8}.txt'},ensure_ascii=False))
if mode=='dash':
    src,out=sys.argv[2:4];tx=open(src,encoding='utf-8',errors='replace').read().replace('\r\n','\n')
    COLS=['week','sec','key','ord','team','title','plain','detail','state','label','n','kind','due','answer','reply','refs','rank','with','ask'];R=[]
    TK={'운영관리':'ops','투자리서치':'res','연구개발':'rnd','법률':'leg','감사실':'aud'}
    def add(w,sec,key,**k):
        r={c:None for c in COLS};r.update(week=w,sec=sec,key=key,ord=len(R))
        for a,b in k.items():r[a]=NW(b) if isinstance(b,str) else b
        R.append(r);return r
    MD=lambda d:f"{int(d[5:7])}/{int(d[8:10])}"
    OKW={'OK':'정상','HOLD':'보류','FAIL':'실패','없음':'결과 없음'}
    CL={'🟢':('정상','알릴 문제 없음','ok'),'🟠':('주의','확인할 것이 있음 — 급한 문제는 아님','warn'),'🔴':('경고','자동 운영 또는 독립 대조에 문제가 있음','bad')}
    VT={'MATCH':'일치','MISMATCH':'불일치','ERROR':'오류','NOT_CHECKED':'대조 안 함'}
    JV={'PASS':'통과','FAIL':'불합격','PASS-WITH-CONDITIONS':'조건부 통과','PASS_WITH_CONDITIONS':'조건부 통과'}
    RL={'R1':'예약 작업과 관제판 기록이 다름','R2':'문서와 일 기록이 어긋남','R4':'기다리는 일의 재개 조건·마감','R5':'지금 할 일 순서','R6':'오래 멈춘 진행 중 일'}
    ACT={'candidates-add':'후보 추가','add':'편입','swap':'교체','remove':'제외','none':'변경 없음','hold':'보류'}
    MR=[(r'^코어 정상 (\d+)/(\d+)\(.*\)$',r'자동 운영 정상 \1/\2일'),(r'^코어가 요청한 사람 손\(주문 입력 제외\) (\d+)건$',r'사람 손 요청 \1건(주문 입력 제외)'),
     (r'^PC 상태 OK \((.*)\)$',r'PC 상태 정상(\1)'),(r'^PC 상태 WARN \((.*)\)$',r'PC 상태 주의(\1)'),(r'^관제판 점검 발견 (\d+)$',r'관제판 점검 \1건'),(r'^관제판 점검 발견 불완전$','관제판 점검 끝내지 못함'),
     (r'^연구 기록 OK (\d+)/(\d+)$',r'연구 기록 정상 \1/\2일'),(r'^공식 사실 (\d+)건$',r'회사 공식 발표 \1건'),(r'^이번 주 카드 수락 (.*)$',r'카드 수락: \1'),
     (r'^진행 개발 (\d+)/3$',r'진행 중 개발 \1/3개'),(r'^권한·한도 변경 (\d+)/1$',r'권한·한도 변경 \1/1개'),(r'^이번 주 완료 (\d+)건$',r'이번 주 끝낸 일 \1건'),
     (r'^최근 개발 실행 (\S+) MERGED (\S+)$',r'최근 개발 자동 실행 \1 — 병합됨(\2)'),(r'^채점 주간 출력 (.*)$',r'판단 성적 채점: \1'),
     (r'^(CLAUDE\.md|AGENTS\.md) \d+바이트 기준값 기록\(첫 실행\)$',r'\1 기준값 처음 기록'),(r'^(CLAUDE\.md|AGENTS\.md) 그대로 \d+바이트$',r'\1 바뀐 것 없음'),
     (r'^정책 파일 수정 (.*)$',r'승인 정책 파일 수정 \1'),(r'^예약 지시문·설정 수정 (.*)$',r'예약 작업 변경 \1'),
     (r'^노출 E (\S+) \(WITHIN_BAND, 세션 (\S+)\)$',r'위험 노출 \1 — 허용 범위 안(세션 \2)'),(r'^노출 E (\S+) \((\S+), 세션 (\S+)\)$',r'위험 노출 \1 — \2(세션 \3)'),
     (r'^멈춤: 없음$','멈춘 것 없음'),(r'^멈춤: (.*)$',r'지금 멈춘 것: \1'),(r'^계좌 검토선 (.*)$',r'계좌 점검선 \1'),(r'^종목 고점 검토: (.*)$',r'종목별 고점 점검: \1'),
     (r'^열린 주문표 (\d+)건$',r'아직 열린 주문표 \1건')]
    def pm(x):
        x=NW(x)
        if x.startswith('카드 {'):
            try:j=json.loads(x[3:]);return '카드: '+' · '.join(f"{ {'holding':'보유','watch':'관심'}.get(k,k)} {v}" for k,v in j.items())
            except Exception:return x
        if x.startswith('관심 명단 변경 '):
            v=x[8:]
            if v=='없음':return '관심 명단 변경 없음'
            return '관심 명단 변경: '+', '.join(f"{MD(a)} {ACT.get(b,b)} {c}"+(f" → 나감 {d}" if d else '') for a,b,c,d in re.findall(r'(\d{4}-\d{2}-\d{2}) (\S+) ([^/\s]*)/([^,\s]*(?:,[^,\s/]+)*)',v)) if re.search(r'\d{4}-\d{2}-\d{2}',v) else '관심 명단 변경: '+v
        for a,b in MR:
            if re.match(a,x):return re.sub(a,b,x)
        return x
    def pf(fid,t):
        q=re.match(r'(\d{4}-\d{2}-\d{2}) 코어 daily (\S+) · decide (\S+)',t)
        if fid.startswith('F-OPS-1-') and q:return f"{MD(q.group(1))} 자동 운영이 정상으로 끝나지 않았습니다(아침 점검 daily {OKW.get(q.group(2),q.group(2))} · 판정 decide {OKW.get(q.group(3),q.group(3))})."
        q=re.match(r'(\d{4}-\d{2}-\d{2})',t);d=MD(q.group(1))+' ' if q else ''
        if fid.startswith('F-RES-1-'):return d+'연구 기록이 정상이 아니어서 그날 매수가 막혔습니다(매도는 안 막힘).'
        if fid.startswith('F-AUD-2-'):return d+'독립 대조가 자동 운영 결과와 맞지 않거나 오류가 났습니다.'
        if fid.startswith('F-AUD-1-'):return f'독립 검사(Judge)가 불합격을 낸 뒤 아직 통과가 없습니다: {fid[8:]}.'
        if fid.startswith('F-LEG-0-'):return '법률팀 기준값(규칙 문서 크기·지문)을 읽지 못했습니다.'
        if fid.startswith('F-LEG-1-'):return f"운영 규칙 문서({'CLAUDE.md' if 'claude' in fid else 'AGENTS.md'})가 지난 보고 뒤 바뀌었습니다(기록용)."
        n=re.search(r'(\d+)건',t);n=n.group(1) if n else ''
        T={'F-OPS-0':'자동 운영 기록 폴더 목록을 읽지 못해 날짜별 확인을 못 했습니다.','F-OPS-2':'PC 상태 점검 결과가 없거나 오래됐거나 이상이 있습니다.',
           'F-OPS-3':'자동 운영이 사람 손을 요청했습니다(주문 입력 제외).','F-OPS-4':('개발 관제판 자동 점검을 끝내지 못했습니다.' if '불완전' in t else f"개발 관제판 자동 점검에서 고칠 곳 {n}건이 나왔습니다(아래 '관제판 점검')."),
           'F-OPS-5':'개발 관제판 점검 일부를 확인하지 못했습니다.','F-RND-0':'개발 일 목록을 끝까지 읽지 못했습니다.','F-RND-1':'동시에 진행 중인 개발이 한도(3개)를 넘었습니다.',
           'F-RND-2':'권한·한도 변경이 동시에 2개 이상 진행 중입니다(한 번에 1개).','F-RND-3':'판단 성적 채점(주간) 결과가 없거나 오래됐거나 정상이 아닙니다.',
           'F-RND-4':'최근 개발 자동 실행이 실패하거나 멈췄습니다.','F-LEG-2':'승인된 정책 파일이 이번 주에 수정됐습니다 — 승인 기록과 맞는지 확인 대상입니다.',
           'F-LEG-3':f'예약 작업의 지시문·설정이 {n}건 바뀌었습니다(기록용).'}
        return T.get(fid,t)
    def sevf(fid,t):
        q=re.match(r'\d{4}-\d{2}-\d{2} 코어 daily (\S+) · decide (\S+)',t)
        if fid.startswith('F-AUD-2-') or (fid.startswith('F-OPS-1-') and q and ({'없음','FAIL'}&{q.group(1),q.group(2)})):return '🔴'
        return SEV(fid)
    chunks=re.split(r'(?m)^(?=## 주간 경영보고 )',tx);bad=[]
    for ch in chunks:
        if not ch.startswith('## 주간 경영보고 '):continue
        L=ch.split('\n');m=re.search(r'<!-- id: ceo-(\d{4}-\d{2}-\d{2}) -->',ch);w=m.group(1) if m else re.findall(r'\d{4}-\d{2}-\d{2}',L[0])[0]
        try:
            h=re.match(r'^## 주간 경영보고 \S+ \(기간 (\S+)~(\S+)\) — 회사 상태 (\S+) · 사장님 결정 (\d+)건\((.*)\)\s*$',L[0])
            ps,pe,col,D,inner=h.groups();D=int(D)
            hot=int((re.search(r'(?:⚠ 이번 주|급함) (\d+)건',inner) or [0,0])[1]);wt=int((re.search(r'답 대기 (\d+)건',inner) or [0,0])[1]);pv=(re.search(r'지난 보고 ([^·)]+)$',inner) or [0,''])[1].strip()
            sec='';tm=None;fa=fi=0;props=[];decn=0;clo=0;dec=[];f_team={};kd=0;teams=[];boardn=None;q_last=None;ib_last=None;ii=0
            for ln in L[1:]:
                if ln.startswith('⚠ 형식 검증 실패'):add(w,'head','head:fmt',detail=ln[2:]);continue
                ms=re.match(r'^### (\d)\.',ln)
                if ms:sec=ms.group(1);mm=re.search(r'기준 (\S+) · 모드 (\S+)\)',ln) if sec=='1' else None;mm and add(w,'head','head:mode',title=mm.group(2),detail=f'기준 {mm.group(1)}',plain={'compare':'비교 모드 — 주문표는 비교용(입력 대상 아님)','apply':'기록 모드 — 주문표 입력 대상'}.get(mm.group(2),mm.group(2)));continue
                if sec=='1' and ln.startswith('- '):
                    items=[ln[2:]] if ln.startswith('- 종목 고점') else ln[2:].split(' · ')
                    for x in items:add(w,'ops',f'ops:{len(R)}',title=pm(x),detail=x)
                elif sec=='2':
                    mi_=re.match(r'^- 받음 \[(\S+)\] (S-[A-Z]+-\w+) (.*?) \| (.*?) \| 확인: (.*)$',ln)
                    if mi_:
                        t_,sid,ttl,sm_,rv=mi_.groups();rd_,_,nt_=rv.partition(' — ');st_={'특이 없음':'ok','제안 있음':'warn','확인 필요':'info'}.get(rd_,'bad')
                        ib_last=add(w,'inbox',f'inbox:{sid}',team=t_,title=ttl,plain=sm_,label=rd_ if st_!='bad' else '팀장 확인 없음',detail=nt_ or None,state=st_,refs=sid);ii=0;continue
                    mj_=re.match(r'^  - (.*)$',ln)
                    if mj_ and ib_last is not None:add(w,'inboxitem',f"ii:{ib_last['refs']}:{ii}",team=ib_last['team'],title=ib_last['refs'],plain=mj_.group(1));ii+=1;continue
                    ib_last=None
                    mt=re.match(r'^- (운영관리|투자리서치|연구개발|법률): (.*)$',ln)
                    if mt:
                        teams.append(mt.group(1))
                        for i,x in enumerate(mt.group(2).split(' · ')):
                            add(w,'metric',f'm:{TK[mt.group(1)]}:{i}',team=mt.group(1),title=pm(x),detail=x)
                            bm=re.match(r'관제판 점검 발견 (\d+)$',NW(x));boardn=int(bm.group(1)) if bm else boardn
                        continue
                    if ln.startswith('- 팀 간 연계: '):add(w,'head','head:links',detail=ln[2:]);continue
                    mp=re.match(r'^- \[(\S+)\] (.*) — 근거 (.*?) · 순위 (\S+) · (알림만|결정 필요)(?: · 협조 ([^:]+): (.*))?$',ln)
                    if mp:
                        t_,txt,refs,rk,kn,wi,ak=mp.groups();kd+=kn=='결정 필요';props.append(1)
                        add(w,'prop',f'prop:{TK.get(t_,t_)}:{len(R)}',team=t_,plain=txt,refs=refs,rank=int(rk) if rk.isdigit() else None,kind=kn,**({'with':wi,'ask':ak} if wi else {}));continue
                    mn=re.match(r'^- \[(\S+)\] 제안 없음$',ln)
                    if mn:add(w,'prop',f'prop:{TK.get(mn.group(1),mn.group(1))}:none',team=mn.group(1),plain='제안 없음',kind='없음')
                elif sec=='3' and ln.startswith('- '):
                    if ln.startswith('- Judge 보고서'):
                        body=ln.split(': ',1)[1].split(' · 파이프라인 최근 실행 ')
                        for i,x in enumerate([y for y in body[0].split(' / ') if y.strip() and y.strip()!='없음']):
                            nmv=x.strip().split(' ',1);v=nmv[1] if len(nmv)>1 else ''
                            add(w,'judge',f'judge:{i}',team='감사실',title=nmv[0],detail=v,label=JV.get(v,v),state='ok' if v.startswith('PASS') else 'bad' if v=='FAIL' else 'info')
                        if len(body)>1:add(w,'judge',f'judge:pipe',team='감사실',title='개발 자동 실행(최근)',detail=body[1],label=body[1])
                    elif ln.startswith('- 독립 대조 일별'):
                        for i,x in enumerate(ln.split(': ',1)[1].split(' · ')):
                            d_,v=(x.strip().split(' ',1)+[''])[:2];c1='(C1 셈)' in v;v0=v.replace('(C1 셈)','').strip()
                            add(w,'t2rc',f't2rc:{i}',team='감사실',title=d_,detail=v,label=VT.get(v0,v0)+(' · C1에 셈' if c1 else ''),state='ok' if v0=='MATCH' else 'bad' if v0 in('MISMATCH','ERROR') else 'info')
                    elif ln.startswith('- C1 누계'):
                        qq=re.search(r'"(.*)"',ln);add(w,'c1','c1',team='감사실',detail=qq.group(1) if qq else ln[2:],plain='판정 모드를 켜기 전 조건 중 하나 — 독립 대조가 연속 10세션 일치해야 함')
                elif sec=='4':
                    mb=re.match(r'^- 관제판 결정함 대기 (\d+)건: (.*)$',ln)
                    if mb:add(w,'boarddec','boarddec',n=int(mb.group(1)),detail=mb.group(2));continue
                    mw=re.match(r'^- 답 대기: (ceo-\S+ D\d+) (.*)\(기한 (\S+)\) — 답 양식 `(.*)`$',ln)
                    if mw:add(w,'wait',f'wait:{len(R)}',title=mw.group(1),plain=mw.group(2),due=mw.group(3),answer=mw.group(4));continue
                    md=re.match(r'^- (⚠ )?(D\d+) (.*?) · 권장 (.*?)(?: · 선택지 (.*?))?(?: · 주관 ([^(·]+?)(?:\(협조 ([^)]*)\))?)? · 무응답 시 기본값 현행 유지 · 기한 (\d{4}-\d{2}-\d{2}) · 답 양식 `(.*)`$',ln)
                    if md:q_last=add(w,'dec',f'dec:{md.group(2)}',title=md.group(2),plain=md.group(3),detail=md.group(4),label=md.group(5),team=md.group(6),**{'with':md.group(7)},due=md.group(8),answer=md.group(9),kind='급함' if md.group(1) else None,state='warn' if md.group(1) else 'info');continue
                    ma=re.match(r'^\s*-?\s*답:\s*(.*)$',ln)
                    if ma and q_last is not None:q_last['reply']=NW(ma.group(1));q_last['state']='ok';continue
                elif sec=='5':
                    mc=re.match(r'^- 기본값 기록: (ceo-\S+ D\d+)\(기한 (\S+)\) — (.*)$',ln)
                    if mc:clo+=1;add(w,'closed',f'closed:{len(R)}',title=mc.group(1),due=mc.group(2),plain='답이 없어 현행 유지로 닫음',detail=mc.group(3));continue
                    mf=re.match(r'^- (F-[A-Z]+-[\w-]+) \[(\S+)\] (?:\(참고\) )?(.*)$',ln)
                    if mf:
                        fid,t_,txt=mf.groups();txt=re.sub(r' ⟨(?:새로|계속 \d+주째)⟩$','',txt);sv=sevf(fid,txt);fi+=sv=='ℹ';fa+=sv!='ℹ';o=f_team.get(t_,'ok');rk={'ok':0,'info':1,'warn':2,'bad':3}
                        st={'🔴':'bad','🟠':'warn','ℹ':'info'}[sv];f_team[t_]=st if rk[st]>rk[o] else o
                        add(w,'find',f'find:{fid}',team=t_,title=fid,plain=pf(fid,txt),detail=txt,state=st,label={'bad':'경고','warn':'주의','info':'참고'}[st]);continue
                    mq=re.match(r'^- 대기열 \[(\S+)\] (.*) — 근거 (.*?) · 순위 (\S+) · (알림만|결정 필요)(?: · 협조 ([^:]+): (.*))?$',ln)
                    if mq:t_,txt,refs,rk_,kn,wi,ak=mq.groups();kd+=kn=='결정 필요';props.append(1);add(w,'prop',f'prop:{TK.get(t_,t_)}:{len(R)}',team=t_,plain=txt,refs=refs,rank=int(rk_) if rk_.isdigit() else None,kind=kn,label='대기열',**({'with':wi,'ask':ak} if wi else {}));continue
                    if ln.startswith('- 결정 건수 3주 연속 증가'):add(w,'head','head:trend',detail=ln[2:])
                elif sec=='6' and ln.startswith('- '):
                    mx=re.match(r'^- (\d{2}-\d{2}) (.*)$',ln)
                    if mx:add(w,'next',f'next:{len(R)}',title=mx.group(1),plain=mx.group(2))
                elif sec=='7':
                    mr=re.match(r'^RESULT (\d+)건 \| (.*)$',ln)
                    if mr:add(w,'boardhead','board:head',n=int(mr.group(1)),detail=mr.group(2));continue
                    mr=re.match(r'^(R\d) (.*)$',ln)
                    if mr and not ln.startswith('R1 제외'):add(w,'board',f'board:{len(R)}',title=mr.group(1),label='문서를 찾지 못함' if '문서를 찾지 못함' in ln else RL.get(mr.group(1),mr.group(1)),detail=mr.group(2),state='warn');continue
                    if ln.startswith('미점검 '):add(w,'board',f'board:{len(R)}',title='미점검',label='확인 못 한 점검',detail=ln[4:],state='info');continue
                    if ln.startswith('R1 제외') or ln.startswith('(R2 미점검'):add(w,'boardnote',f'boardnote:{len(R)}',detail=ln)
            WR=[r for r in R if r['week']==w]
            LKC={}
            for r in WR:
                if r['sec']=='prop' and r['with']:
                    for b_ in [x.strip() for x in r['with'].split(',') if x.strip()]:LKC.setdefault((r['team'],b_),[]).append(r['ask'] or '')
            for (a_,b_),asks in LKC.items():add(w,'link',f'link:{TK.get(a_,a_)}:{TK.get(b_,b_)}',team=a_,title=b_,n=len(asks),detail=' / '.join(asks))
            for r in WR:
                if r['key']=='boarddec' and (r['n'] or 0)>0:add(w,'act','act:boarddec',title='개발 관제판 결정함',plain='개발 관제판에 사장님 답을 기다리는 결정이 있습니다.',detail=r['detail'],n=r['n'],kind='결정')
                if r['key']=='find:F-OPS-3':add(w,'act','act:touch',title='자동 운영의 사람 손 요청',plain=r['plain'],detail=r['detail'],kind='확인')
            pr=sorted([r for r in WR if r['sec']=='prop' and r['kind'] in('알림만','결정 필요')],key=lambda r:(r['rank'] if r['rank'] is not None else 9,r['ord']))
            bf=[r for r in WR if r['sec']=='find' and r['state']=='bad']
            why=(bf[0]['plain'] if bf else (f"[{pr[0]['team']}] {pr[0]['plain']}" if pr else '이번 주 팀장 제안 없음'))
            add(w,'head','head:why',plain=why,title='가장 먼저 볼 것' if not bf else '경고 원인')
            ntodo=sum(1 for r in R if r['week']==w and r['sec'] in('dec','wait','act') and not r.get('reply'))
            add(w,'head','head:todo',n=ntodo,plain='이번 주 사장님이 할 일은 없습니다. 그대로 두셔도 됩니다.' if not ntodo else f'사장님이 할 일 {ntodo}건 — 아래 순서대로 보세요.')
            JG={}
            for r in R:
                if r['week']==w and r['sec']=='judge' and r['key']!='judge:pipe':JG.setdefault(r['title'].split('-judge')[0],[]).append(r)
            for g,rs in JG.items():
                if any((r['detail'] or '').startswith('PASS') for r in rs):
                    for r in rs:
                        if r['detail']=='FAIL':r['label']='불합격 → 이후 통과';r['state']='info'
            IBW=[r for r in R if r['week']==w and r['sec']=='inbox']
            for t_ in teams+['감사실']:
                st=f_team.get(t_,'ok');it_=[r for r in IBW if r['team']==t_]
                add(w,'team',f'team:{TK[t_]}',team=t_,title=t_,state=st,label={'ok':'이상 없음','info':'참고만','warn':'주의','bad':'경고'}[st],n=sum(1 for r in R if r['week']==w and r['sec']=='find' and r['team']==t_),detail=f"받은 결과 {len(it_)}건 · 팀장 확인 {sum(1 for r in it_ if r['state']!='bad')}건" if it_ else None)
            nib=len(IBW);nrv=sum(1 for r in IBW if r['state']!='bad');PRW=[r for r in R if r['week']==w and r['sec']=='prop' and r['kind'] in('알림만','결정 필요')]
            nlink=len({x.strip() for r in PRW for x in (r['refs'] or '').split(',') if x.strip().startswith('S-')})
            if nib:add(w,'head','head:inbox',n=nib,label=f'팀장 확인 {nrv}/{nib}',detail=f'제안 근거로 쓰인 받은 결과 {nlink}건',state='ok' if nrv==nib else 'bad')
            c=CL.get(col,(col,'',None));pd=sum(1 for r in R if r['week']==w and r['sec']=='prop' and r['kind'] in('알림만','결정 필요'))
            tk=(f"사장님이 결정할 일 {D}건"+(f"(급함 {hot}건)" if hot else '')+' — 기한 안에 답이 없으면 현행 유지됩니다.') if D else '이번 주 사장님이 결정할 일은 없습니다.'
            tk+=f" 알아 둘 것 {fa}건"+(f"(참고 {fi}건 별도)" if fi else '')+'.'+(f' 지난 결정 중 답 대기 {wt}건.' if wt else '')
            for k,v in [('head:color',dict(title=col,label=c[0],plain=c[1],state=c[2])),('head:period',dict(title=f'{MD(ps)}~{MD(pe)}',detail=f'{ps}~{pe}')),('head:takeaway',dict(plain=tk)),
                        ('head:dec',dict(n=D,label=f'급함 {hot}건' if hot else None)),('head:wait',dict(n=wt)),('head:find',dict(n=fa,label=f'참고 {fi}건 별도' if fi else None)),
                        ('head:board',dict(n=boardn,label=None if boardn is not None else '끝내지 못함')),('head:prev',dict(title=pv or None)),
                        *([('flow:inbox',dict(title='받은 결과',n=nib,label=f'팀장 확인 {nrv}/{nib}'))] if nib else []),
                        ('flow:teams',dict(title='팀 보고',n=len(teams)+1,label=f'{len(teams)}팀 + 감사실')),('flow:find',dict(title='알아 둘 것',n=fa,label=f'참고 {fi}건 별도' if fi else None)),
                        ('flow:prop',dict(title='팀장 제안',n=pd,label=f'결정 필요 {kd}건')),('flow:dec',dict(title='사장님 결정',n=D,label=f'답 대기 {wt}건')),('flow:close',dict(title='기본값 마감',n=clo,label='답 없으면 현행 유지'))]:
                add(w,'flow' if k.startswith('flow') else 'head',k,**v)
        except Exception as e:
            bad.append(w);add(w,'head','head:fmt',detail=f'이 주 보고를 대시보드로 옮기지 못함({type(e).__name__}) — 원문 보고 파일을 보세요')
    WS=sorted({r['week'] for r in R})
    fam=lambda f:re.sub(r'-\d{4}$','',f.strip())
    bkey=lambda r:(r['title'] or '')+' '+((r['detail'] or '').split(' ')[0])
    PER={r['week']:tuple(r['detail'].split('~')) for r in R if r['key']=='head:period' and '~' in str(r['detail'] or '')}
    REP={}
    for w_ in WS:
        if w_ in PER and PER[w_][0] not in REP or (w_ in PER and w_>REP.get(PER[w_][0],'')):REP[PER[w_][0]]=w_
    FS={w_:{fam(r['title']) for r in R if r['week']==w_ and r['sec']=='find'} for w_ in WS}
    BS={w_:{bkey(r) for r in R if r['week']==w_ and r['sec']=='board' and r['title']!='미점검'} for w_ in WS}
    BO={w_:any(r['week']==w_ and r['key']=='board:head' for r in R) for w_ in WS}
    def DST(w_,k,i):
        n_=1;ps_=PER[w_][0];ex_=(dt.date.fromisoformat(ps_)-dt.timedelta(days=1)).isoformat()
        for p_ in sorted([p for p in REP if p<ps_],reverse=True):
            wk_=REP[p_]
            if PER[wk_][1]!=ex_:break
            ex_=(dt.date.fromisoformat(p_)-dt.timedelta(days=1)).isoformat()
            if i==1 and not BO[wk_]:continue
            if k in (FS if i==0 else BS)[wk_]:n_+=1
            else:break
        return n_
    for r in R:
        if r['week'] not in PER:continue
        if r['sec']=='find':n_=DST(r['week'],fam(r['title']),0);r['kind']='새로' if n_==1 else f'계속 {n_}주째'
        if r['sec']=='board' and r['title']!='미점검':n_=DST(r['week'],bkey(r),1);r['kind']='새로' if n_==1 else f'계속 {n_}주째'
    for w_ in WS:
        for r in R:
            if r['week']==w_ and r['key']=='head:find':
                nn_=sum(1 for x in R if x['week']==w_ and x['sec']=='find' and x['state']!='info' and x['kind']=='새로');r['detail']=f"새로 {nn_}건 · 계속 {(r['n'] or 0)-nn_}건"
    for a_,b_ in zip(WS,WS[1:]):
        now={fam(r['title']) for r in R if r['week']==b_ and r['sec']=='find'}
        for r in [r for r in R if r['week']==a_ and r['sec']=='prop' and r['kind'] in('알림만','결정 필요')]:
            fs={fam(x) for x in (r['refs'] or '').split(',') if x.strip().startswith('F-')}
            again=bool(fs&now)
            add(b_,'carry',f'carry:{len(R)}',team=r['team'],plain=r['plain'],refs=r['refs'],kind=r['kind'],label=('이번 주에도 같은 발견' if again else '이번 주 발견에는 없음') if fs else '받은 결과 근거(발견 아님) — 진행 확인',state=('warn' if again else 'ok') if fs else 'info',**{'with':r['with']})
    KW=set(WS[-26:]);K8=set(WS[-8:]);R=[r for r in R if r['week'] in KW and (r['sec']!='inboxitem' or r['week'] in K8)]
    for c in R:
        if c['n'] is not None:c['n']=int(c['n'])
    keys=[(r['week'],r['key']) for r in R];dup=len(keys)-len(set(keys))
    b=json.dumps({'rows':R},ensure_ascii=False,indent=0).encode('utf-8');open(out,'wb').write(b)
    print(json.dumps({'weeks':sorted({r['week'] for r in R}),'rows':len(R),'bytes':len(b),'bad_weeks':bad,'dup_keys':dup,'sha256':hashlib.sha256(b).hexdigest()},ensure_ascii=False));sys.exit(0 if not dup else 4)
