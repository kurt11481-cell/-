# st-1014 첫 짝 실행 확인(2026-10-15, 읽기 전용). 사용: python3 -I st1014-firstrun-check.py <DAY> <LATEST_TICKER_LEADS.json|-> <research-record.json|-> <대시보드 runs 문서 json|->
# 판정: FAIL(종료 1) = 적용된 규칙이 지켜지지 않음 / CHECK = 사람 확인 필요 / PASS. 파일을 쓰지 않는다. 근거: docs/claude/integrated-check-v3.12.4-change-2026-10-14.md
import json,re,sys
DAY,LP,RP,UP=sys.argv[1:5]
DENY=re.compile(r'(saveticker|reuters|bloomberg|yahoo|cnbc|stocktitan|marketbeat|seekingalpha|benzinga|investing\.com|fool\.com|zacks|tipranks|marketwatch|wsj\.com|ft\.com|barrons|thefly|finviz|nasdaq\.com/articles|google\.|naver|daum|hankyung|mk\.co\.kr|yna\.co\.kr|news1|fmkorea|//x\.com|twitter|reddit|stocktwits|futunn|tradingview|techcrunch|theverge|thenextweb|datacenterdynamics|investopedia|morningstar|msn\.com|apnews|axios|businessinsider|forbes|digitimes|trendforce|substack|medium\.com|pluang|rallies\.ai|lelezard|mlq\.ai|kucoin|cryptobriefing|investors\.com|gurufocus|simplywall|earningswhispers|public\.com|robinhood|webull|spheron|leaprate)',re.I)
WRITER='integrated-check 06:40 v3.12.4-L+R1'
RES={'OFFICIAL','COUNTERPARTY_OFFICIAL','NOT_FOUND','NOT_RELEVANT','SKIPPED_BUDGET'}
F=[];W=[];I=[]
def load(p):
    if p in('-',''):return None
    try:return json.load(open(p,encoding='utf-8'))
    except Exception as e:return {'__err__':type(e).__name__}
L=load(LP);R=load(RP);U=load(UP)
if isinstance(U,dict) and 'data' in U and 'date' not in U:U=U['data']
fresh=isinstance(L,dict) and '__err__' not in L and L.get('day')==DAY
if not isinstance(L,dict) or '__err__' in L:F.append('단서 파일 없음·읽기 실패')
else:
    if L.get('day')!=DAY:F.append(f"단서 파일 날짜 {L.get('day')} != {DAY}")
    if L.get('status') not in('OK','PARTIAL'):F.append(f"단서 상태 {L.get('status')}")
    tk=L.get('tickers') or {};gen=str(L.get('generated_at',''))
    I.append(f"단서 {L.get('status')} 생성 {gen[:16]} · "+' '.join(f"{c}={(v or {}).get('status')}" for c,v in sorted(tk.items())))
    nok=sum(1 for v in tk.values() if (v or {}).get('status')=='OK')
    if tk and nok<len(tk):W.append(f'단서 종목 일부 미수집 {nok}/{len(tk)}')
    if gen[:10]==DAY and gen[11:16]>'06:40':W.append(f'단서 파일 생성 {gen[11:16]} — 06:40 뒤(통합 점검이 못 봤을 수 있음)')
    win=[x for x in L.get('leads') or [] if isinstance(x,dict) and x.get('in_window')]
    I.append(f"단서 창 안 {len(win)} · must {sum(1 for x in win if x.get('must'))}"+''.join(f" | {','.join(x.get('must_codes') or [])}: {str(x.get('title',''))[:40]}" for x in win if x.get('must')))
run=None
if not isinstance(R,dict) or '__err__' in R:F.append('연구 기록 없음·읽기 실패')
else:
    if R.get('writer')!=WRITER:F.append(f"연구 기록 writer {R.get('writer')} != {WRITER}")
    if R.get('record_day_kst')!=DAY:F.append(f"연구 기록 날짜 {R.get('record_day_kst')} != {DAY}")
    run=R.get('integrated_check_run')
if not isinstance(run,dict):run=U if isinstance(U,dict) and U.get('date')==DAY else None
if run is None:F.append('오늘 통합 점검 기록(run) 없음')
else:
    st=run.get('stLeads') or {}
    if fresh:
        if st.get('day')!=DAY:F.append(f"run stLeads.day {st.get('day')} != {DAY}")
        fid={x.get('id') for x in L.get('leads') or [] if isinstance(x,dict) and x.get('in_window')}
        rid={x.get('id') for x in run.get('leads') or [] if isinstance(x,dict)}
        if fid!=rid:W.append(f'run leads {len(rid)}건 != 파일 창 안 {len(fid)}건(빠짐 {sorted(fid-rid)[:3]} 더함 {sorted(rid-fid)[:3]})')
    bad=[x.get('id') if isinstance(x,dict) else str(x)[:20] for x in run.get('leads') or [] if not isinstance(x,dict) or x.get('result') not in RES]
    if bad:F.append(f'lead result 형식 오류 {bad[:3]}')
    I.append('lead 결과 '+(', '.join(f"{','.join(x.get('codes') or [])}{'*' if x.get('must') else ''}={x.get('result')}" for x in run.get('leads') or [] if isinstance(x,dict)) or '없음'))
    rc=str((run.get('account') or {}).get('reconcile') or '');k=rc.find('fc_ord_alowa')
    if k>=0 and not re.search(r'(응답에 없|필드[^.]{0,12}없|미조회)',rc[max(0,k-40):k+60]):I.append('현금: reconcile에 fc_ord_alowa 있음 — '+rc[max(0,k-10):k+50])
    else:W.append('현금: reconcile에서 fc_ord_alowa 값 확인 안 됨 — '+rc[:100])
if isinstance(R,dict) and '__err__' not in R:
    E=R.get('earnings') or {};MF=set()
    for x in (run or {}).get('leads') or []:
        if isinstance(x,dict) and x.get('must') and x.get('result')!='OFFICIAL':MF|=set(x.get('must_codes') or [])
    if 'MRVL' in MF:MF.add('MVLL')
    for s,e in E.items():
        if DENY.search(str((e or {}).get('source_url',''))):F.append(f"실적 {s} 출처가 외부 도메인 {e.get('source_url')}")
        if (e or {}).get('status')=='NOT_ANNOUNCED' and s in MF:F.append(f'실적 {s} NOT_ANNOUNCED인데 must 단서 미확인')
    for f in R.get('official_facts') or []:
        if DENY.search(str((f or {}).get('source_url',''))):F.append(f"공식 사실 {f.get('fact_id')} 출처가 외부 도메인")
    p=E.get('PWR')
    if p is None:I.append('PWR 실적: 기록 없음(코어가 금지 구간으로 봄 — 매수만 막힘)')
    elif p.get('status')=='VERIFIED' and p.get('announcement_session')=='2026-10-29':I.append(f"PWR 실적: VERIFIED 10/29 {p.get('timing','')} — 정정됨")
    elif p.get('status')=='NOT_ANNOUNCED':F.append('PWR 실적 아직 NOT_ANNOUNCED — 회사 공지(10/13, 10/29 장 전)와 다름')
    else:W.append(f"PWR 실적 {p.get('status')} {p.get('announcement_session')}")
    I.append('실적 '+' '.join(f"{s}={(e or {}).get('status')}{('@'+e['announcement_session']) if (e or {}).get('announcement_session') else ''}" for s,e in sorted(E.items())))
v='FAIL' if F else('CHECK' if W else 'PASS')
print('ST1014_FIRSTRUN',v,DAY,f'fail {len(F)} check {len(W)}')
for x in F:print('FAIL',x)
for x in W:print('CHECK',x)
for x in I:print('INFO',x)
sys.exit(1 if F else 0)
