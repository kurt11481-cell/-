---
id: integrated-check-record-guard-v3.11.2-draft-2026-10-08
type: change-proposal
status: applied (2026-10-08 14:2x KST 사용자 "적용" — 라이브 프롬프트를 의도한 새 지시문과 글자 단위로 대조해 37,722자 전체 일치, 길이 +3,790자, 그 밖의 예약 작업 변경 없음. v3.11 초안 문서에도 같은 문단 반영. 첫 확인은 10/9 06:40 KST 실행)
as_of: 2026-10-08
summary: 통합 점검(trig_01YWzNq847nJfNgDUnnukBqP)의 기록 전 검증(v3.11.1)이 종가 날짜·값과 직전 문장만 대조해, 10/8 기록에서 시장환경·레이더·saveticker·피드 시각이 옛 값으로 통과했다. 검증 2를 추가해 이 항목들을 이번 실행의 원본 값과 대조한다. K1 문구, 코드·정책·상태 파일 변경 없음.
consumers: [예약 작업 통합 점검(화~토 06:40), docs/claude/integrated-check-record-guard-2026-10-07.md, 개발 관제판 c-check-guard]
---

# 통합 점검 — 기록 전 검증 2 (v3.11.2 초안, 2026-10-08)

## 1. 근거 — 10/8 기록(runs/2026-10-08)을 원본과 대조한 결과 (읽기 전용)
| 항목 | 기록 | 원본 | 판정 |
|---|---|---|---|
| 시장환경 market.reportDate | 2026-10-06 (stale=false) | LATEST_MARKET_ENV_MEMO.md 리포트 날짜 2026-10-08, 생성 06:17 KST(점검 06:40 전) | 복사 확인 |
| 공시 피드 feedRunAt | 2026-10-05T13:00Z | 06:40 점검 시점의 최신 피드 실행 = 2026-10-07T13:00Z (이후 10/8 03:30Z 실행도 PASS) | 날짜 오기록. 경과 8.7시간 자체는 맞음 |
| 공시 피드 status | NO_NEW_FILINGS | 피드 실행 상태값(공시 없음 뜻). 허용값 OK·STALE·FAILED·MISSING·UNREAD가 아님 | 화면에 "오래됨 여부 확인 필요"로 보이는 원인 |
| 레이더 7건 pct | 10/7 기록과 완전 동일 | 종가는 8종목 모두 바뀜 | 복사 확인 |
| saveticker 가격 7건 | 10/7 기록과 동일 | — | 복사 의심 |
| 계좌 총자산 | $21,578.74 (예수금 $5.92 + 보유평가, 미결제 매도대금 제외) | 10/7은 $31,702.09 | 비교 불가 → vsHwmPct 등은 null로 정상 처리됐으나 레이더 V6 −15.3%는 어제 값 그대로 |
- 정정: 관제판에 한때 "공시 피드 실제 경과 약 56.8시간"이라고 적었으나 틀린 계산이었다(기록의 오기록 날짜를 원본으로 착각). 피드는 최신이다.
- 현재 검증(v3.11.1)은 종가·계좌 5필드만 보므로 위 항목이 통과했다.

## 2. 바꿀 곳 (문장 1곳 삽입, 기존 문장 삭제·수정 없음)
v3.11.1 "기록 전 검증" 문단(python 코드 블록 끝) 바로 뒤, 알림 문단 앞에 아래 새 문단을 넣는다. 입력 2개(FEED_FINISHED, MEMO_DATE)는 이번 실행이 2-2)와 4)에서 이미 읽은 값을 그대로 옮긴다(새 조회 없음, 읽기 전용 유지).

```
기록 전 검증 2(v3.11.2): 검증 1(v3.11.1)이 OK여도 이어서 아래 python을 한 번 더 실행한다(DIR·TODAY는 검증 1과 같고, FEED_FINISHED = 2-2) 출력 "FEED ... finished"의 UTC 시각(예 2026-10-07T13:00:09Z), MEMO_DATE = 4)에서 읽은 시장환경 메모의 "리포트 날짜"(YYYY-MM-DD). 2-2)·4)를 읽지 못했으면 빈 문자열). FAIL이 나오면 그 필드를 이번 실행에서 읽은 원본 값으로 다시 만들어 다시 검증하고, 두 번째에도 FAIL이면 그 상태로 기록하되 headline 앞에 "점검 불완전(기록 검증 실패)"를 붙이고 알림 ⑧로 알린다. WARN은 기록은 그대로 하고 보고 (i) 확인 필요에 "복사 의심(확인 필요): <WARN 내용>" 한 줄만 적는다. filings.status는 OK|STALE|FAILED|MISSING|UNREAD 중 하나만 쓴다(피드의 NO_NEW_FILINGS는 status가 아니라 "새 공시 없음"이므로 OK + newCount 0). account.vsHwmPct가 없으면(총자산 비교 불가) radar에 계좌 항목을 넣지 않는다.
DIR="<0단계 out_dir>" TODAY="<오늘 한국 날짜>" FEED_FINISHED="<값>" MEMO_DATE="<값>" python3 - <<'PY'
(아래 5절의 코드 그대로)
PY
```

## 3. 검사 내용
| 구분 | 검사 | 결과 |
|---|---|---|
| FAIL | filings.feedRunAt = 2-2 출력의 finished(분 단위) | 다르면 FAIL |
| FAIL | filings.ageHours = 현재 시각 − finished (허용 0.3시간) | 다르면 FAIL |
| FAIL | filings.status가 허용값 5개 중 하나 | 아니면 FAIL |
| FAIL | market.reportDate = 메모 리포트 날짜 | 다르면 FAIL |
| FAIL | 레이더 항목(종목+별칭 ID)의 pct가 직전과 같은데 종가(계좌는 총자산)가 바뀜 | 복사로 FAIL |
| FAIL | vsHwmPct 없음(비교 불가)인데 radar에 계좌 항목 | FAIL |
| FAIL | 총자산이 0.5% 넘게 바뀌었는데 점검선 여유 3값(firstCushionPct·approachPct·maxPct)이 직전과 동일 | FAIL |
| WARN | saveticker 가격의 절반 이상이 직전과 동일 | 알림 없이 (i)에 한 줄 |
| WARN | news 전체가 직전과 동일 | 알림 없이 (i)에 한 줄 |

## 4. 시험 결과 (아래 코드를 그대로, 실제 10/7·10/8 기록으로 실행. 입력: FEED_FINISHED=2026-10-07T13:00:09Z, MEMO_DATE=2026-10-08, NOW=2026-10-07T21:40Z)
| 경우 | 결과 |
|---|---|
| 10/8 기록 그대로(직전=10/7) | FAIL 11건: feedRunAt, status, market.reportDate, 레이더 7건(V6 포함), 비교 불가 총자산인데 계좌 레이더 / WARN 2건(saveticker 7/7, news) |
| 위 항목을 원본 값으로 고친 가상 기록 | OK, WARN 없음 |
| 입력 FEED_FINISHED·MEMO_DATE 빠짐 | FAIL(조용히 통과하지 않음) |

## 5. 코드
```python
import json,os,glob,datetime as dt
D=os.environ['DIR'];T=os.environ['TODAY']
P=lambda s:dt.datetime.fromisoformat(s.replace('Z','+00:00'))
now=P(os.environ['NOW']) if os.environ.get('NOW') else dt.datetime.now(dt.timezone.utc)
if not os.path.exists(D+'/run-doc.json'): print('FAIL',['run-doc.json 없음']); raise SystemExit
d=json.load(open(D+'/run-doc.json',encoding='utf-8'))
pf=sorted(f for f in glob.glob(D+'/runs/*.json') if os.path.basename(f)[:-5]<T)
p=json.load(open(pf[-1],encoding='utf-8')) if pf else {}
bad=[];warn=[]
FF=os.environ.get('FEED_FINISHED','').strip();MD=os.environ.get('MEMO_DATE','').strip()
# A 공시 피드: 기록의 실행 시각·경과 시간·상태가 2-2 출력과 같아야 한다
f=d.get('filings')
if f:
    if not FF: bad.append('FEED_FINISHED 입력 없음(2-2 출력의 finished 값)')
    else:
        if f.get('feedRunAt','')[:16]!=FF[:16]: bad.append(f'filings.feedRunAt {f.get("feedRunAt")} != 2-2 출력 {FF[:16]}Z')
        age=(now-P(FF)).total_seconds()/3600
        if f.get('ageHours') is None or abs(f['ageHours']-age)>0.3: bad.append(f'filings.ageHours {f.get("ageHours")} != 재계산 {age:.1f}')
    if f.get('status') not in ('OK','STALE','FAILED','MISSING','UNREAD'): bad.append(f'filings.status "{f.get("status")}" 허용값 아님(OK|STALE|FAILED|MISSING|UNREAD)')
# B 시장환경: 기록의 reportDate가 메모의 리포트 날짜와 같아야 한다
m=d.get('market')
if m:
    if not MD: bad.append('MEMO_DATE 입력 없음(4)에서 읽은 리포트 날짜)')
    elif m.get('reportDate')!=MD: bad.append(f'market.reportDate {m.get("reportDate")} != 메모 {MD}')
# C 레이더: 종가(계좌는 총자산)가 바뀌었는데 같은 항목의 pct가 직전과 같으면 복사
cl=lambda x:{t['code']:t.get('close') for t in x.get('tickers',[])}
c0,c1=cl(p),cl(d);r0={(r['code'],r['id']):r.get('pct') for r in p.get('radar',[])}
a0,a1=p.get('account',{}),d.get('account',{})
for r in d.get('radar',[]):
    k=(r['code'],r['id'])
    if r.get('pct') is None or r0.get(k)!=r['pct']: continue
    if r['code']=='계좌': ch=a0.get('total') is not None and a1.get('total') is not None and abs(a1['total']-a0['total'])>0.005
    else: ch=c0.get(r['code']) is not None and c1.get(r['code']) is not None and abs(c1[r['code']]-c0[r['code']])>0.005
    if ch: bad.append(f'radar {k[0]} {k[1]} pct {r["pct"]} 직전과 동일(종가·총자산은 바뀜)')
# E 계좌 점검선: 비교 불가 총자산이면 V6 레이더가 없어야 하고, 총자산이 바뀌면 여유 값도 바뀌어야 한다
if a1.get('vsHwmPct') is None and any(r['code']=='계좌' for r in d.get('radar',[])): bad.append('account.vsHwmPct 없음(비교 불가)인데 radar에 계좌 항목이 있음')
ks=('firstCushionPct','approachPct','maxPct')
if a0.get('total') and a1.get('total') and abs(a1['total']-a0['total'])/a0['total']>0.005 and all(a1.get(x) is not None and a1.get(x)==a0.get(x) for x in ks): bad.append('계좌 점검선 여유 3값이 직전과 동일(총자산은 0.5% 넘게 바뀜)')
# D·F 경고(복사 의심, 실패 아님): saveticker 가격, 뉴스
s0={x['code']:x.get('price') for x in p.get('saveticker',[])};s1=[x for x in d.get('saveticker',[]) if x.get('price') is not None]
if s1 and sum(s0.get(x['code'])==x['price'] for x in s1)*2>=len(s1): warn.append(f'saveticker 가격 {sum(s0.get(x["code"])==x["price"] for x in s1)}/{len(s1)}건이 직전과 동일')
if d.get('news') and d.get('news')==p.get('news'): warn.append('news 전체가 직전과 동일')
print('FAIL' if bad else 'OK',bad)
print('WARN',warn)
```

## 6. 한계·확인 필요
- 옮겨 적는 오류와 복사만 잡는다. 레이더 pct·점검선 값의 계산 자체가 틀리면 못 잡는다(사람 대조 유지).
- 레이더 복사 검사는 종가가 같은 날(예: 휴장 다음 날)에는 같은 pct를 허용한다. 직전 기록이 없으면 대조 항목은 건너뛴다.
- 이 변경은 "총자산 비교 불가일 때 V6를 어떻게 보여줄지"를 정하지 않는다. 빠뜨리게만 막는다. 표시 방식(예: 미결제 매도대금 포함 총자산 병기)은 별도 결정(확인 필요).
- confirmedCloseDate가 10/7·10/8 기록 모두 2026-10-02인 것이 정상인지 확인 필요(이 검증 범위 밖).
- 이번 실행 세션이 검증 2를 실제로 돌리는지는 첫 실행(10/9 06:40 KST) 전에는 확인할 수 없다. 검증용 임시 파일은 검증 1과 같은 폴더 안이다.

## 7. 적용·검증·롤백
1. 적용: 사용자 승인 뒤 라이브 프롬프트에 2절의 새 문단 1곳만 삽입하는 update_trigger 1회. 적용 뒤 라이브 원문과 기대본을 글자 단위로 대조한다. v3.11 초안 문서에도 같은 곳을 반영한다.
2. 확인: 10/9 06:40 실행 뒤 runs/2026-10-09에서 4절 항목(reportDate·feedRunAt·status·레이더·V6)과 "직전 기록과 동일" 줄.
3. 롤백: 삽입한 문단을 지운다.
