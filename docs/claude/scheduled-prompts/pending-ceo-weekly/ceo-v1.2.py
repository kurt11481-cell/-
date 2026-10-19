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
    print(json.dumps([W+p.replace('/','\\') for p in P],ensure_ascii=False));sys.exit()
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
    col='🔴' if red else '🟠' if any(f['sev']=='🟠' for f in F) else '🟢'
    out={'id':'ceo-'+today,'period':[PS,PE],'color':col,'findings':F,'prev':{'id':pid,'defaulted':[x['key'] for x in exp],'waiting':[x['key'] for x in wait]},'board_decisions':dec}
    S=[f"## 주간 경영보고 {today} (기간 {PS}~{PE}) — 회사 상태 {col} · {{{{N}}}}",f'<!-- id: ceo-{today} -->',
    f"### 1. 운용 (코어 파일 값 그대로, 기준 {X.get('run_day_kst','확인 필요')} · 모드 {X.get('decision_mode','확인 필요')})",
    f"- 노출 E {E} ({S7.get('band','확인 필요')}, 세션 {S7.get('session','확인 필요')}) · 멈춤: {pa} · 계좌 검토선 {ac.get('state','확인 필요')}(첫 쿠션 {cu})",
    f"- 종목 고점 검토: {pk}",f"- 이번 주 주문표 {tk}건 · 열린 주문표 {len(X.get('open_tickets') or [])}건 · 결과 기록 {len(X.get('outcomes') or [])}건",
    '### 2. 팀별',
    f"- 운영관리: 코어 정상 {okc}/{len(days)}(폴더 있는 날 {len([d for d in days if d in cd]) if cd is not None else '확인 필요'}) · 예외 알림 {ptot}건 · 코어가 요청한 사람 손(주문 입력 제외) {len(touch)}건 · PC 상태 {host} · 관제판 점검 발견 {bn if bn is not None else '불완전'}",
    f"- 투자리서치: 연구 기록 OK {rrok}/{len(days)} · 공식 사실 {facts}건 · 이번 주 카드 수락 {', '.join(ca) or '없음'} · 관심 명단 변경 {', '.join(wh) or '없음'} · 카드 {json.dumps(roles,ensure_ascii=False)}",
    f"- 연구개발: 진행 개발 {na}/3 · 권한·한도 변경 {len(auth)}/1 · 이번 주 완료 {len(done)}건 · 최근 개발 실행 {dvs} · 채점 주간 출력 {sc}",
    f"- 법률: {' · '.join(lg)} · 정책 파일 수정 {pcs} · 예약 지시문·설정 수정 {tus}",
    '팀장 제안:','{{PROPOSALS}}',
    '### 3. 감사실 (원문 그대로)',f"- Judge 보고서(이번 주 수정): {' / '.join(jd) or '없음'} · 파이프라인 최근 실행 {dvs}",f"- 독립 대조 일별: {' · '.join(tv)}",f'- C1 누계(관제판 redesign-t2 인용): "{c1}"',
    '### 4. 사장님 결정',f"- 관제판 결정함 대기 {len(dec)}건: {', '.join(dec) or '없음'}",*wl4,'{{DECISIONS}}',
    '### 5. 알림만',*pl,*[f"- {x['id']} [{x['team']}] {'(참고) ' if x['sev']=='ℹ' else ''}{x['text']}" for x in F],'{{QUEUE}}',
    '### 6. 다음 주',*([f'- {x}' for x in sorted(nx)] or ['- 일정 없음(일정표·실적 달력·일회성 예약 기준)']),
    '### 7. 관제판 점검 원문','```text',B,'```',
    '<!-- ceo-state '+json.dumps(NS,ensure_ascii=False)+' -->','']
    TM=os.path.dirname(os.path.abspath(inj));open(TM+'/section.md','w',encoding='utf-8',newline='\n').write('\n'.join(S))
    json.dump({**out,'prev_D':len([x for x in DL if x['sec']==pid]) if pid else None,'waiting_n':len(wait),'prev_state':PS0,'state':NS,'board_n':bn,'prev_path':fp(RP) if pvb is not None else None,'today':today},open(TM+'/run.json','w',encoding='utf-8'),ensure_ascii=False)
    print(json.dumps(out,ensure_ascii=False));sys.exit()
if mode=='finalize':
    TM=sys.argv[2];U=json.load(open(TM+'/run.json',encoding='utf-8'));S=open(TM+'/section.md',encoding='utf-8').read();V=[];today=U['today'];td=dt.date.fromisoformat(today)
    NM=td+dt.timedelta(days=(6-td.weekday())%7 or 7);DEF=NM-dt.timedelta(days=1)
    try:G=json.load(open(TM+'/fill.json',encoding='utf-8'))
    except Exception:G={};V.append('fill.json 없음·깨짐')
    ids={f['id'] for f in U['findings']};PR=G.get('proposals') if isinstance(G.get('proposals'),list) else [];DS=G.get('decisions') if isinstance(G.get('decisions'),list) else []
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
    if '{{' in S:V.append('자리표시 남음')
    if V:S=S.replace('<!-- id: ','⚠ 형식 검증 실패: '+' / '.join(V[:4])+'\n<!-- id: ',1)
    st=U['state'];st['d_hist']=dh;S=re.sub(r'<!-- ceo-state \{.*\} -->','<!-- ceo-state '+json.dumps(st,ensure_ascii=False)+' -->',S)
    HD='---\nid: ceo-weekly-report\ntype: report\nstatus: current\nas_of: 각 주 절 머리(최신 = 맨 아래)\ntickers: [ALL]\nevidence: 코어·대조·채점·관제판 값은 결과 파일 그대로(등급은 원 파일 따름) / 팀장 제안·결정 문장 = 주간 팀장회의 LLM(근거 F-id) / 판정·매매 근거 아님\nconsumers: [사장(사용자) · 다음 주간 팀장회의(결정·답 줄) · Cowork(결정 ceo-<날짜> 처리) · 2단계 평가(docs/claude/company-org-plan-2026-10-19.md 7절) · redesign-t4(법률 정리 안건)]\nsummary: 투자_V2 주간 팀장회의 → 사장 보고. 매주 일요일 절을 덧붙인다(덧붙이기만). 조직·규칙 = docs/claude/company-org-plan-2026-10-19.md. 답 줄 형식 = 그 결정 줄 바로 아래 "  - 답: <원문>(<YYYY-MM-DD HH:MM KST>, Cowork)". 답이 없고 기한이 지난 결정은 다음 회의가 5절에 "기본값 기록"으로 닫는다.\n---\n\n# 주간 경영보고 (투자_V2)\n'
    pp=U.get('prev_path');pb=open(pp,'rb').read() if pp else b''
    sb=S.encode('utf-8');body=(pb+(b'' if pb.endswith(b'\n') else b'\n')+b'\n'+sb) if pb else (HD+'\n').encode('utf-8')+sb
    if not body.startswith(pb):V.append('덧붙이기 검사 실패')
    os.makedirs('/mnt/user-data/outputs',exist_ok=True);open('/mnt/user-data/outputs/ceo-weekly-report.md','wb').write(body)
    d8=today.replace('-','');open(f'/mnt/user-data/outputs/ceo-weekly-{d8}.txt','w',encoding='utf-8',newline='\n').write(f"docs(claude): ceo weekly report {today} (weekly team-lead meeting)\ndocs/claude/ceo-weekly-report.md\n")
    fi=sum(1 for f in U['findings'] if f.get('sev')=='ℹ');fc=len(U['findings'])-fi;bn=U.get('board_n');pre=f'⚠ 이번 주 답 필요 {hot}건 · ' if hot else ''
    push=f"{pre}주간 경영보고 {today[5:].replace('-','/')}: {U['color']} · 결정 {n}건(답 대기 {U.get('waiting_n',0)}) · 발견 {fc}건{f'(참고 {fi}건 별도)' if fi else ''} · 관제판 점검 {str(bn)+'건' if bn is not None else '불완전'}"+(' (형식 확인 필요)' if V else '')+" — 대시보드 '주간 팀장회의'"
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
            sec='';tm=None;fa=fi=0;props=[];decn=0;clo=0;dec=[];f_team={};kd=0;teams=[];boardn=None;q_last=None
            for ln in L[1:]:
                if ln.startswith('⚠ 형식 검증 실패'):add(w,'head','head:fmt',detail=ln[2:]);continue
                ms=re.match(r'^### (\d)\.',ln)
                if ms:sec=ms.group(1);mm=re.search(r'기준 (\S+) · 모드 (\S+)\)',ln) if sec=='1' else None;mm and add(w,'head','head:mode',title=mm.group(2),detail=f'기준 {mm.group(1)}',plain={'compare':'비교 모드 — 주문표는 비교용(입력 대상 아님)','apply':'기록 모드 — 주문표 입력 대상'}.get(mm.group(2),mm.group(2)));continue
                if sec=='1' and ln.startswith('- '):
                    items=[ln[2:]] if ln.startswith('- 종목 고점') else ln[2:].split(' · ')
                    for x in items:add(w,'ops',f'ops:{len(R)}',title=pm(x),detail=x)
                elif sec=='2':
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
                        fid,t_,txt=mf.groups();sv=sevf(fid,txt);fi+=sv=='ℹ';fa+=sv!='ℹ';o=f_team.get(t_,'ok');rk={'ok':0,'info':1,'warn':2,'bad':3}
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
            for t_ in teams+['감사실']:
                st=f_team.get(t_,'ok');add(w,'team',f'team:{TK[t_]}',team=t_,title=t_,state=st,label={'ok':'이상 없음','info':'참고만','warn':'주의','bad':'경고'}[st],n=sum(1 for r in R if r['week']==w and r['sec']=='find' and r['team']==t_))
            c=CL.get(col,(col,'',None));pd=sum(1 for r in R if r['week']==w and r['sec']=='prop' and r['kind'] in('알림만','결정 필요'))
            tk=(f"사장님이 결정할 일 {D}건"+(f"(급함 {hot}건)" if hot else '')+' — 기한 안에 답이 없으면 현행 유지됩니다.') if D else '이번 주 사장님이 결정할 일은 없습니다.'
            tk+=f" 알아 둘 것 {fa}건"+(f"(참고 {fi}건 별도)" if fi else '')+'.'+(f' 지난 결정 중 답 대기 {wt}건.' if wt else '')
            for k,v in [('head:color',dict(title=col,label=c[0],plain=c[1],state=c[2])),('head:period',dict(title=f'{MD(ps)}~{MD(pe)}',detail=f'{ps}~{pe}')),('head:takeaway',dict(plain=tk)),
                        ('head:dec',dict(n=D,label=f'급함 {hot}건' if hot else None)),('head:wait',dict(n=wt)),('head:find',dict(n=fa,label=f'참고 {fi}건 별도' if fi else None)),
                        ('head:board',dict(n=boardn,label=None if boardn is not None else '끝내지 못함')),('head:prev',dict(title=pv or None)),
                        ('flow:teams',dict(title='팀 보고',n=len(teams)+1,label=f'{len(teams)}팀 + 감사실')),('flow:find',dict(title='알아 둘 것',n=fa,label=f'참고 {fi}건 별도' if fi else None)),
                        ('flow:prop',dict(title='팀장 제안',n=pd,label=f'결정 필요 {kd}건')),('flow:dec',dict(title='사장님 결정',n=D,label=f'답 대기 {wt}건')),('flow:close',dict(title='기본값 마감',n=clo,label='답 없으면 현행 유지'))]:
                add(w,'flow' if k.startswith('flow') else 'head',k,**v)
        except Exception as e:
            bad.append(w);add(w,'head','head:fmt',detail=f'이 주 보고를 대시보드로 옮기지 못함({type(e).__name__}) — 원문 보고 파일을 보세요')
    WS=sorted({r['week'] for r in R})
    fam=lambda f:re.sub(r'-\d{4}$','',f.strip())
    for a_,b_ in zip(WS,WS[1:]):
        now={fam(r['title']) for r in R if r['week']==b_ and r['sec']=='find'}
        for r in [r for r in R if r['week']==a_ and r['sec']=='prop' and r['kind'] in('알림만','결정 필요')]:
            fs={fam(x) for x in (r['refs'] or '').split(',') if x.strip()}
            again=bool(fs&now)
            add(b_,'carry',f'carry:{len(R)}',team=r['team'],plain=r['plain'],refs=r['refs'],kind=r['kind'],label='이번 주에도 같은 발견' if again else '이번 주 발견에는 없음',state='warn' if again else 'ok',**{'with':r['with']})
    KW=set(WS[-26:]);R=[r for r in R if r['week'] in KW]
    for c in R:
        if c['n'] is not None:c['n']=int(c['n'])
    keys=[(r['week'],r['key']) for r in R];dup=len(keys)-len(set(keys))
    b=json.dumps({'rows':R},ensure_ascii=False,indent=0).encode('utf-8');open(out,'wb').write(b)
    print(json.dumps({'weeks':sorted({r['week'] for r in R}),'rows':len(R),'bytes':len(b),'bad_weeks':bad,'dup_keys':dup,'sha256':hashlib.sha256(b).hexdigest()},ensure_ascii=False));sys.exit(0 if not dup else 4)
