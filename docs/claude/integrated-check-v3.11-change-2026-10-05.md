---
id: integrated-check-v3.11-change
type: change-draft
status: applied (2026-10-05 사용자 "v3.11 적용", 10/6 06:40 첫 실행 확인 대기)
as_of: 2026-10-05
tickers: [MRVL, NBIS, MU, BE, DELL, PWR, LITE]
evidence: 공식 사실 = SEC 공식 API 수집 결과(로컬 파일, 출처 SEC) / 이 문서의 판단 = Cowork 초안(K1)
consumers: 통합 점검(화~토 06:40) 2-2), Cowork(적용·5회 실행 뒤 K0 비교), 관제판 e-filing-k1
summary: SEC 공시 수집기 산출물을 통합 점검이 읽는 단계(2-2)를 추가하는 변경안. 새 공시 표시·신선도 24시간·현행 검색과 대조(검색은 줄이지 않음). 판정·알림 조건 불변.
---

# 통합 점검 v3.11 변경안 — SEC 공시 피드 읽기 (e-filing-k1, 2026-10-05)

- 사용자 결정(2026-10-05, 추천안): ① 이번 버전은 검색을 줄이지 않고 표시·대조만, 생략은 5회 대조 뒤 v3.12 ② 신선도 24시간.
- 등급 K1(출력 행동 + 읽기 단계 추가). 판정 기준·알림 ①~⑧ 조건·쓰기 범위·점검 상태 조건은 그대로. order_authority=false.
- 근거: `e-filing-feed-review-2026-10-05.md` §4·§5(3단계), `e-filing-feed-k2-builder-report-2026-10-05.md`, 같은 문서 진행 기록(22:16 재가동 첫 실행 PASS).
- **번호 정정**: 검토서 §5의 "v3.10"은 오늘 먼저 적용된 "개장 전 기록 읽기" 변경(`integrated-check-v3.10-change-2026-10-05.md`)과 이름이 겹친다. 이 변경은 **v3.11**로 부른다. 검토서·관제판 문구의 "v3.10"은 적용 때 함께 고친다.
- **기준 문서**: 적용된 v3.10 전체본이 저장소에 없어, 사용자가 붙여 준 라이브 지시문과 대조해 복원했다 — v3.9 초안 + v3.10 차이분 = `integrated-check-prompt-v3.10-reconstructed-2026-10-05.txt`(26,224자, 변경 노트의 적용 당시 길이와 일치, 붙여 준 글을 글자 단위로 대조하지는 못함). v3.11 초안은 이 파일에 아래 A~F를 삽입한 `integrated-check-prompt-v3.11-draft-2026-10-05.txt`(31,152자)이고, v3.10과의 차이는 7곳(이름 2줄, 머리 이력, 2-2) 새 단계, 3) 끝 문장, (g), 점검 상태 끝, 대시보드 기록 끝)뿐이다.

## 1. 바뀌는 것 (6곳)

| 위치 | 내용 |
|---|---|
| 맨 위 두 줄·머리 변경 이력 | 이름 v3.11, 이력 한 문장(A) |
| **새 단계 2-2)** (2-1)과 3) 사이) | 공시 피드 읽기: 최신 `scheduled-dashboard.json`·`normalized-events.json`·`run-manifest.json`을 python으로 요약, 새 공시 표시, 신선도 규칙(B) |
| 3) "공식 발표·공시의 확인" 끝 | 검색은 현행 그대로 하고, 검색으로 찾은 공시를 피드와 대조해 놓침 건수를 기록(C) |
| 출력 (g) 뉴스 | "공시 피드(SEC, 공식·로컬 수집)" 한 줄(D) |
| 점검 상태 | 피드 실패는 ㉠~㉥에 넣지 않는다는 구절(E) |
| 대시보드 기록 | 문서에 `filings{}` 필드 추가(표시 전용, 값은 보고에 쓴 것만)(F) |

## 2. 삽입문 원문

### A. 머리 변경 이력 끝에 덧붙일 문장
v3.11 변경(2026-10-05 사용자 승인, 근거 docs/claude/e-filing-feed-review-2026-10-05.md §4·§5): 2-2) 공시 피드 읽기를 추가한다(표시·대조용, 3)·5)의 검색은 줄이지 않는다). 판정 기준·알림 조건·점검 상태·대시보드 기존 필드는 그대로다.

### B. 새 단계 2-2) (2-1) 바로 뒤)
2-2) 공시 피드 읽기(v3.11, 읽기만 — 사용자 PC의 Windows 작업이 월~금 22:00·화~토 12:30(한국 시간)에 SEC 공식 API로 모은 파일): 아래 python을 device_bash에서 그대로 한 번 실행하고(heredoc, 파일을 만들지 않는다) 출력만 읽는다. SINCE에는 0)의 직전 기록 runAt을 UTC ISO로 넣고(예 2026-10-03T21:40:00Z), 직전 기록이 없으면 ""로 둔다(최근 72시간 기준).
SINCE="<값>" python3 - <<'PY'
import json,glob,os,datetime as dt
R=os.path.expanduser('~/mnt/코덱스저장소/')
now=dt.datetime.now(dt.timezone.utc)
P=lambda s:dt.datetime.fromisoformat(s.replace('Z','+00:00'))
S=os.environ.get('SINCE','').strip()
cut=P(S) if S else now-dt.timedelta(hours=72)
runs=sorted(glob.glob(R+'workspace/outputs/official-event-intake/sec/*/sec-scheduled-*/scheduled-dashboard.json'),key=lambda p:os.path.basename(os.path.dirname(p)))
if not runs: print('FEED MISSING 산출물 없음'); raise SystemExit
D=os.path.dirname(runs[-1]);ld=lambda f:json.load(open(D+'/'+f,encoding='utf-8'))
d=ld('scheduled-dashboard.json');m=ld('run-manifest.json');ev=ld('normalized-events.json')['events']
age=(now-P(d['run_finished_at'])).total_seconds()/3600;pr=[]
if age>24:pr.append(f'오래됨 {age:.0f}h')
if d.get('schedule_status')!='PASS' or d.get('pipeline_status')!='PASS':pr.append('실행 상태 '+str(d.get('schedule_status'))+'/'+str(d.get('pipeline_status')))
if d.get('freshness_status')!='CURRENT_RUN':pr.append('freshness '+str(d.get('freshness_status')))
bad=[k for k,v in (m.get('company_source_status') or {}).items() if v!='PASS']
if bad:pr.append('회사 조회 실패 '+','.join(bad))
reg=json.load(open(R+'docs/claude/watchlist-registry.json',encoding='utf-8'))
exp={'MRVL','NBIS'}|{x['code'] for x in reg['members']};got={x if isinstance(x,str) else x.get('ticker') for x in d['watchlist']}
print('FEED',os.path.basename(D),'finished',d['run_finished_at'][:16]+'Z',f'age {age:.1f}h','STATUS','OK' if not pr else 'STALE_OR_FAILED: '+'; '.join(pr))
print('WATCHLIST','일치' if exp==got else f'불일치 피드에만 {sorted(got-exp)} / 피드에 없음 {sorted(exp-got)}','| 창',d['lookback_days'],'일 총',len(ev),'건, HIGH',sum(e['materiality']=='HIGH' for e in ev))
def url(e):
    return f"https://www.sec.gov/Archives/edgar/data/{int(e['cik'])}/{e['accession_number'].replace('-','')}/{e['primary_document']}" if e.get('primary_document') else 'URL 없음'
new=[e for e in ev if P(e['accepted_at'])>cut]
IO=lambda e:e.get('event_type')=='INSIDER_OWNERSHIP' or e['form'] in ('3','4','5','144','3/A','4/A','5/A','144/A')
own=[e for e in new if IO(e)];oth=[e for e in new if not IO(e)]
gap=cut<now-dt.timedelta(days=d['lookback_days'])
if gap:print('주의: SINCE가 피드 조회 창('+str(d['lookback_days'])+'일)보다 오래됨 — 창 밖 공시는 이 출력에 없음, 그 구간은 3)·5) WebSearch로 확인')
print('NEW since',cut.strftime('%Y-%m-%dT%H:%MZ'),'총',len(new),'건 = 내부자 지분(Form 3/4/5·144 류) '+str(len(own))+'건('+', '.join(f'{k} {sum(e["ticker"]==k for e in own)}' for k in sorted({e["ticker"] for e in own}))+') + 그 밖 '+str(len(oth))+'건(HIGH 먼저, 최대 20줄)')
for e in sorted(oth,key=lambda e:(e['materiality']!='HIGH',e['accepted_at']))[:20]:
    print(e['ticker'],e['form'],e['filing_date'],e['accepted_at'][:16]+'Z',e.get('items_if_available') or '',e['materiality'],e['decision_impact'],url(e))
PY
 규칙 ① STATUS가 OK이면 보고 (g)에 "공시 피드(SEC, 공식·로컬 수집)" 줄을 쓴다: 피드 실행 시각, 새 공시 중 HIGH와 8-K·6-K·S-3·424B류(종목·종류·항목 번호·제출 시각·문서 URL), 내부자 지분 공시는 종목별 건수만. 새 공시가 없으면 "피드 기준 새 공시 없음(실행 <시각>)". ② 피드는 "새 공시가 있다"는 사실까지만이다. 호재·악재·트리거 충족은 출력의 문서 URL을 WebFetch로 열어 본문을 확인한 뒤 기존 기준 (a)와 카드 규칙대로 3)에서 판정한다(본문 확인은 공시마다 1회, 합계 최대 3회, 원장 7)의 3회와 별도). 본문을 못 열면 "미확인 공시(확인 필요)"로 적고 충족으로 세지 않는다. 피드의 materiality·decision_impact·diff 값은 쓰지 않는다(새 여부는 SINCE와 accepted_at 비교, 판정은 본문). ③ STATUS가 STALE_OR_FAILED, FEED MISSING이거나 파일·python을 못 읽으면 "공시 피드 오래됨/실패(사유)" 또는 "공시 피드 미접근"으로 적고 "새 공시 없음"으로 쓰지 않는다. 이 경우 3)·5)의 현행 WebSearch/WebFetch 확인을 그대로 한다(대체 경로가 피드의 권한을 물려받지 않는다). 피드 실패는 점검 상태에 넣지 않고 푸시하지 않는다. ④ WATCHLIST가 불일치이면 보고에 "피드 명단 불일치: …" 한 줄만 적는다. ⑤ 피드 대상은 MRVL·NBIS·관심 members뿐이다. SOXL(Direxion), TSMC(해외 발행사), 8-K 없이 나오는 IR 보도자료, 실적 발표일 공지는 피드 대상이 아니므로 현행 WebSearch로 확인한다. ⑥ 피드만으로는 푸시하지 않는다. 본문 확인으로 강 후보 트리거가 충족되면 기존 알림 ⑤ 규칙(직전 기록과 state 비교)으로만 푸시한다. ⑦ 이번 실행에서 부른 WebSearch 횟수와, 3)에서 말한 대조 결과(검색에만·피드에만 있던 공시 건수)를 세어 둔다(대시보드 기록 filings.webSearchCount·onlyInSearch·onlyInFeed).

### C. 3) "공식 발표·공시의 확인" 문장 끝에 덧붙일 문장
v3.11은 검색을 줄이지 않는다: 3)·5)의 WebSearch/WebFetch 확인과 상한(5) 8회, 실적일 점검 종목당 1회, 원장 3회)은 현행 그대로다. 단 검색으로 찾은 새 공시(8-K·S-3·424B·6-K, 피드 대상 종목)를 2-2)의 출력과 대조해 "검색에만 있던 공시"(피드가 놓침)와 "피드에만 있던 공시"(검색이 놓침) 건수를 센다. 피드 STATUS가 OK가 아닌 날은 대조하지 않고 "대조 생략"으로 적는다.

### D. 출력 (g) 문구를 아래로 교체: "(g) 뉴스(공식/보도 구분)." →
(g) 뉴스(공식/보도 구분) — 맨 앞에 "공시 피드(v3.11)" 한 줄: 2-2) 규칙 ①·③의 문구, 공식 사실(피드·본문 확인)과 보도를 한 줄에 섞지 않는다.

### E. 점검 상태 문단 끝에 덧붙일 구절
2-2) 공시 피드 실패·오래됨·미접근은 점검 상태에 넣지 않는다(표시만).

### F. 대시보드 기록 끝에 덧붙일 문장
v3.11: 문서에 filings{status(OK|STALE|FAILED|MISSING|UNREAD), feedRunAt, ageHours, newCount, ownership{<종목>: 건수}, items[{code,form,items,filedAt,url,verdict(미확인|확인-관련|확인-무관|열기 실패)}], watchlistMismatch, webSearchCount, onlyInSearch, onlyInFeed}를 추가한다(보고에 쓴 값만, 없으면 필드 생략, 표시 전용).

## 3. 바뀌지 않는 것
- 트리거 기준·강도, 알림 ①~⑧ 조건, 절대 금지, 일정·폴더·쓰기 범위(대시보드 저장소만), 점검 상태 ㉠~㉥, 기존 대시보드 필드·headline 80자 규칙, WebSearch 상한과 검색 범위(줄이지 않음).
- Claude는 sec.gov를 bash·python·curl로 가져오지 않는다(검토서 §3). 이 단계는 로컬 파일만 읽고, 문서 본문은 WebFetch로만 연다(`/Archives/edgar/data` 경로는 robots 허용).

## 4. 안전 점검 (fail-open)
| 상황 | 동작 |
|---|---|
| 피드 폴더·파일 없음 / python 실패 | "공시 피드 미접근", 현행 검색 유지, 점검 상태·푸시 영향 없음 |
| 마지막 실행 24시간 초과, 실행·파이프라인 상태 PASS 아님, freshness≠CURRENT_RUN, 일부 회사 조회 실패 | STALE_OR_FAILED → "새 공시 없음"으로 쓰지 않고 현행 검색 |
| 피드 OK인데 0건 | "피드 기준 새 공시 없음". 검색은 현행대로 하므로 놓침은 대조(3)로 드러남 |
| SINCE가 피드 창(7일)보다 오래됨 | 출력에 "주의"가 나오고 그 구간은 현행 검색 |
| 피드에 새 8-K | 충족이 아니라 "본문 확인 대상". 못 열면 "미확인 공시" |
| 명단 불일치 | 한 줄 표시만(자동 동기화 없음) |
| 권한 | 새 권한 필드 없음. 읽기·표시만 넓힘(order_authority=false) |

## 5. 완료 기준 (기계 판정)
첫 정기 실행: **10/6(화) 06:40 KST**(피드의 월 22:00 실행분, 나이 약 9시간).
1. runs/2026-10-06 문서에 `filings.status`가 있고 값이 OK|STALE|FAILED|MISSING|UNREAD 중 하나.
2. 보고에 "공시 피드(SEC, 공식·로컬 수집)" 줄이 있고, STATUS OK면 `filings.feedRunAt`이 10/5 22:00 KST 이후.
3. `status` 8칩·decisions·triggers·radar 구조·`len(headline) ≤ 80`이 직전 기록과 같은 형식(회귀 없음).
4. `filings.webSearchCount`·`onlyInSearch`·`onlyInFeed` 기록 — 5회 실행 뒤 합산해(검토서 §5 4단계, K0) `onlyInSearch`가 0건이면 v3.12(피드 정상일 때 "찾기" 검색 생략, K1)를 승인받아 적용, 1건 이상이면 원인(피드 명단·창·형식)부터 본다. 토큰 절감은 **확인 필요(실측 없음)**.
수동 실행은 하지 않는다(푸시·기록이 생김).

## 6. 적용 절차 (사용자 승인 뒤)
1. (완료) 라이브 지시문 확보·복원 — 위 "기준 문서".
2. (완료) A~F 삽입, v3.10과 diff로 삽입 7곳만 다름을 확인. 삽입문 속 python은 초안 파일에서 꺼내 실행 확인.
3. `update_trigger`로 지시문만 교체(이름·일정·알림 불변), 교체 뒤 지시문을 다시 읽어 초안과 일치 확인.
4. `analysis-linkage-map-2026-10-05.md` 표 "SEC 섀도 수집기" 행을 미연결 → 연결(읽는 작업: 통합 점검 2-2)로 바꾸고 §3 미연결 목록에서 제거, `library/INDEX.md` 포인터, 관제판 e-filing-k1 → 완료 후보(10/6 실행 확인까지 waiting).

## 7. 왜 틀릴 수 있나 / 확인 필요
- 검토서 §2 표는 `source_url`을 "문서 URL"로 적었으나 실제 산출물의 `source_url`은 submissions JSON 주소다. 문서 URL은 `cik + accession_number + primary_document`로 조립한다. MU 8-K(2026-09-30)는 WebFetch로 열려 8-K 항목 2.02임을 확인했다. NBIS 6-K, Form 4·144 경로는 열어 보지 않았다(확인 필요, HIGH 판정에는 8-K·6-K 본문만 필요).
- 신선도 24시간은 사용자 결정(추천안)이다. 정상일 때 점검 시점 나이는 약 9시간, 실행 1회 누락은 약 18시간(정상 처리), 2회 누락은 약 33시간(오래됨 표시). 수집 작업이 "사용자가 로그온할 때만 실행"이라 PC가 꺼진 날은 오래됨이 될 수 있고, 그 비용은 현행 검색으로 돌아가는 것뿐이다.
- 이번 버전은 커버리지를 줄이는 변경이 없다(검색 유지). 대신 5회 대조 표본이 작아서(실행 5회) 놓침 0건이 "놓침 없음"의 증거는 아니다 — 생략 승인(v3.12) 때 표본 크기를 함께 적는다.
- `watchlist` 값이 문자열 목록이라고 가정했다(오늘 산출물로 테스트 통과). 대시보드 HTML이 모르는 `filings` 필드를 무시하는지는 확인하지 않았다 — 이번 버전은 HTML을 바꾸지 않아 화면 표시는 없고 기록만 남는다.
- 재가동 첫 실행의 diff 상태는 PREVIOUS_RUN_INCOMPATIBLE이라 피드의 diff를 쓰지 않는다(규칙 ②). 첫 실행의 새 공시 18건 중 중요 2건(MU 8-K 9/30 항목 2.02·9.01, NBIS 6-K 10/1)은 이미 알려진 사실이다.
- 이 초안을 이 세션에서 구문·출력 테스트한 것은 python 요약 부분뿐이다(오늘 22:00 실행 산출물로 정상·창 초과 두 경우 확인). 지시문 전체 통합 실행은 하지 않았다.

## 8. 적용 기록 (2026-10-05)
- update_trigger trig_01YWzNq847nJfNgDUnnukBqP: 지시문만 교체(이름·일정·알림 불변). 응답에 저장된 지시문 31,152자가 `integrated-check-prompt-v3.11-draft-2026-10-05.txt`와 글자 단위로 일치(Python 비교 True). 작업은 여전히 사용자 컴퓨터 필요 상태로 재서명됨.
- 다음: 10/6(화) 06:40 정기 실행 뒤 §5 완료 기준 1~3 확인, 5회 실행 뒤 §5-4 합산(v3.12 판단).