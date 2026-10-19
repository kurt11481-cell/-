import json,glob,re,sys,datetime as dt
K=dt.timezone(dt.timedelta(hours=9))
mode,tdir=sys.argv[1],sys.argv[2]
T={}
for f in glob.glob(tdir+'/*.json'):
    d=json.load(open(f,encoding='utf-8')); T[f.replace('\\','/').split('/')[-1][:-5]]=d.get('data',d)
def iso(s): return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(K) if s else None
def nm(k): return T[k].get('plain') or T[k].get('title') or k
if mode=='docs':
    S=set()
    for k,t in T.items():
        if t.get('status')!='done':
            m=re.search(r'docs/claude/([^\s()]+)',t.get('doc') or '')
            if m: S.add(m.group(1))
    print(' '.join(sorted(S))); sys.exit()
I=json.load(open(sys.argv[3],encoding='utf-8'))
TODAY=dt.date.fromisoformat(I['today']); NOW=dt.datetime.combine(TODAY,dt.time(12,0),K)
F=[]
# R1 예약 작업 vs 관제판 기록 (v1.2: 이름 키워드 대신 관제판 문서의 trigs(예약 작업 id)로 짝짓는다)
VER=re.compile(r'v\d+(?:\.\d+)*')
C=I.get('complete',{}); N=[]; skipW=0; skipO=0
def isw(s): return 'Windows 작업' in s['name'] or 'GuardedPortfolio' in s['name']
def sver(s):
    m=VER.search(s['name'])
    if m: return m.group()
    m=re.search(r'지시문 (v\d+(?:\.\d+)*)',s.get('text',''))
    return m.group(1) if m else None
if C.get('trig') is False or C.get('sch') is False:
    N.append('R1 미점검(예약 작업 목록 또는 관제판 예약 기록을 끝까지 읽지 못함)')
else:
    tmap={}
    for s in I['sch']:
        for t in s.get('trigs') or []: tmap[t]=s
    ids={tr['id'] for tr in I['trig']}; seen=set()
    for tr in I['trig']:
        s=tmap.get(tr['id'])
        if not s:
            if tr.get('enabled') and (tr.get('recurring') or tr['name'].startswith('개장 전 이벤트')): F.append(('R1',f"관제판에 없는 예약 작업: {tr['name']} ({tr['id']})"))
            else: skipO+=1
            continue
        seen.add(s['id'])
        if iso(tr['updated'])>iso(s['updated'])+dt.timedelta(minutes=30):
            F.append(('R1',f"{tr['name']}: 예약 작업 수정 {iso(tr['updated']):%m/%d %H:%M} > 관제판 기록 {iso(s['updated']):%m/%d %H:%M} ({s['id']})"))
        a=VER.search(tr.get('head','')); b=sver(s)
        if a and b and a.group()!=b: F.append(('R1',f"{tr['name']}: 지시문 {a.group()} ≠ 관제판 표기 {b} ({s['id']})"))
    for s in I['sch']:
        if not s.get('trigs'):
            if isw(s): skipW+=1
            else: F.append(('R1',f"예약 작업 id(trigs)가 없는 관제판 항목: {s['name']} ({s['id']})"))
        elif s['id'] not in seen: F.append(('R1',f"관제판이 가리키는 예약 작업이 목록에 없음: {s['name']} ({s['id']})"))
# R2 문서가 작업보다 새로움(30분 초과)
for k,t in T.items():
    if t.get('status')=='done': continue
    m=re.search(r'docs/claude/([^\s()]+)',t.get('doc') or '')
    if not m: continue
    fn=m.group(1)
    if fn not in I['mtimes']: F.append(('R2',f"{k} {nm(k)}: 문서를 찾지 못함 {fn} (확인 필요)")); continue
    mt=dt.datetime.fromtimestamp(I['mtimes'][fn],K); u=iso(t.get('updatedAt'))
    if u and mt>u+dt.timedelta(minutes=30): F.append(('R2',f"{k} {nm(k)}: 문서 {fn} 수정 {mt:%m/%d %H:%M} > 작업 갱신 {u:%m/%d %H:%M}"))
# 상태 계산(관제판 화면과 같은 규칙)
def met(t):
    r=t.get('resume') or {}
    if r.get('type')=='date' and r.get('date'): return TODAY>=dt.date.fromisoformat(r['date'])
    if r.get('type')=='after' and r.get('after'): return all(T.get(i,{}).get('status')=='done' for i in r['after'])
    return False
def eff(t): return 'ready' if t.get('status')=='waiting' and met(t) else t.get('status')
def act(t):
    e=eff(t); r=t.get('resume') or {}
    return e in('ready','active','decision','blocked') or (e=='planned' and t.get('priority') is not None and not (r.get('type') and r['type']!='manual'))
# R4 재개 조건·마감
for k,t in T.items():
    s=t.get('status'); r=t.get('resume') or {}
    if s=='waiting':
        if not r.get('type'): F.append(('R4',f"{k} {nm(k)}: 기다리는 중인데 재개 조건 없음"))
        elif r['type']=='date' and r.get('date') and (TODAY-dt.date.fromisoformat(r['date'])).days>=3: F.append(('R4',f"{k} {nm(k)}: 재개일 {r['date']} 3일 이상 지났는데 아직 대기"))
    if s in('waiting','planned') and t.get('deadline'):
        d=(dt.date.fromisoformat(t['deadline'])-TODAY).days
        queued=r.get('type')=='date' and r.get('date') and dt.date.fromisoformat(r['date'])<=dt.date.fromisoformat(t['deadline'])
        if d<=3 and not queued: F.append(('R4',f"{k} {nm(k)}: 마감 {t['deadline']}까지 {d}일, 상태 {s}"))
# R5 지금 할 일 후보
rec=[(k,t) for k,t in T.items() if t.get('status')!='done' and act(t)]
if not rec: F.append(('R5','지금 할 수 있는 일이 없음'))
g={}
for k,t in rec: g.setdefault((eff(t) in('ready','active','blocked'),t.get('priority')),[]).append(k)
for (b,p),ks in g.items():
    if len(ks)>1 and p is not None: F.append(('R5',f"순서 숫자 {p} 동률: {', '.join(ks)}"))
# R6 진행 중 방치
for k,t in T.items():
    if t.get('status')=='active' and t.get('updatedAt') and (NOW-iso(t['updatedAt'])).days>=7: F.append(('R6',f"{k} {nm(k)}: 진행 중인데 7일 넘게 갱신 없음"))
print(f"RESULT {len(F)}건 | 검사한 작업 {len(T)}개 · 지금 할 수 있는 일 {len(rec)}개")
for r,x in F: print(r,x)
if not N: print(f"R1 제외: Windows 작업 {skipW}건 · 관제판에 올리지 않는 단발성/종료 예약 {skipO}건")
for x in N: print("미점검",x)
