---
id: integrated-check-record-guard-2026-10-07
type: change-proposal
status: applied (2026-10-07 사용자 승인 "적용" — 라이브 프롬프트를 기대본과 글자 단위로 대조해 일치 확인, 길이 +2,213자, v3.11 초안 문서에도 동일 3곳 반영)
as_of: 2026-10-07
summary: 통합 점검(trig_01YWzNq847nJfNgDUnnukBqP)의 대시보드 기록이 직전 기록 문장·옛 종가를 복사하는 사고를 막는 기록 가드(종가 날짜·값 검증 + 직전 기록 복사 금지 + 동일 문장 경고). K1 문구, 코드 변경 없음.
consumers: [예약 작업 통합 점검(화~토 06:40), docs/claude/integrated-check-statefile-binding-2026-10-07.md §5·§6, 개발 관제판]
---

# 통합 점검 — 기록 가드 (2026-10-07)

## 1. 다른 세션과의 겹침
- 겹친다. 다른 세션의 "v3.12 수정본"(종가 검증, closes.json)은 이 세션이 제안하려던 "종가 날짜 점검"과 같은 목적이다. 그 수정본 파일은 저장소·라이브 프롬프트 어디에도 없어(2026-10-07 확인) 내용을 직접 대조하지 못했다. 그쪽 평가문에서 지적한 3가지(검사 범위 확대, 허용 오차 0, 사람 대조 유지)를 이 안에 반영했다.
- 이미 끝난 것(중복 작업 금지): 상태 파일 값 하드코딩 제거(수정안 문서 §1~3, 라이브 적용 완료), 10/7 기록 옛 문구 정정(§6, version 3).
- 번호 충돌: 기존 문서가 v3.12를 "피드 생략 판단(K1)"과 "전날 지시 결과 1줄"에 이미 쓰고 있다. 혼동을 피하려고 이 안은 v3.11.1로 부른다.

## 2. 바꿀 곳 (문장 3곳 삽입, 기존 문장 삭제·수정 없음)
1. 0)단계 끝(94자 삽입): 직전 기록의 값·문장은 비교에만 쓰고 새 기록에 복사하지 않는다(v3.11.1). 새 기록의 잔고 대조·미체결·키움 총평가금액 필드는 이번 실행의 1) 결과로만 만든다.
2. 2) 참고 기준 줄 바로 뒤(새 줄): 종가 저장·날짜 확인(v3.11.1): 종목별 종가를 구한 직후, 구한 값 그대로 이 세션 임시 폴더(0단계 out_dir과 같은 곳)에 closes.json {"basis":"<기준 미국 거래일 YYYY-MM-DD>","closes":{"<코드>":{"date":"YYYY-MM-DD","close":숫자}}}로 저장한다(date = 그 종가를 낸 봉·일봉 행의 미국 날짜, 휴장이면 그 종목은 넣지 않는다). date가 basis와 다른 종목은 ㉢ 실패로 보고 점검 불완전(사유 "종가 날짜 불일치 <코드>")으로 둔다.
3. 알림 문단 바로 앞(새 문단, 검증 코드 포함):

```
기록 전 검증(v3.11.1): 기록할 문서 JSON을 이 세션 임시 폴더에 run-doc.json으로 저장한 뒤, 쓰기 전에 아래 python을 한 번 실행한다(DIR = 0단계 out_dir, TODAY = 오늘 한국 날짜). 이 검증용 임시 파일 쓰기는 사용자 폴더 쓰기가 아니므로 허용한다. FAIL이면 그 필드를 closes.json과 이번 실행 값으로 다시 만들어 다시 검증하고, 두 번째에도 FAIL이면 그 상태로 기록하되 headline 앞에 "점검 불완전(기록 검증 실패)"를 붙이고 알림 ⑧로 알린다. "직전 기록과 동일"에 headline·reconcile·kiwoomTotal·kiwoomDiff·openOrders가 나오면 이번 1) 결과로 다시 만들고, 실제로 변동이 없으면 보고 (i) 확인 필요에 "직전과 동일(변동 없음 확인)" 한 줄을 적는다. 이 검증은 옮겨 적는 오류만 잡는다 — 종가 계산 자체의 오류는 못 잡으므로 사람의 키움 일봉 대조는 그대로 필요하다.
DIR="<0단계 out_dir>" TODAY="<오늘 한국 날짜 YYYY-MM-DD>" python3 - <<'PY'
import json,os,glob
D=os.environ['DIR'];T=os.environ['TODAY']
if not(os.path.exists(D+'/closes.json') and os.path.exists(D+'/run-doc.json')): print('FAIL',['closes.json 또는 run-doc.json 없음']); raise SystemExit
c=json.load(open(D+'/closes.json',encoding='utf-8'));d=json.load(open(D+'/run-doc.json',encoding='utf-8'))
pf=sorted(f for f in glob.glob(D+'/runs/*.json') if os.path.basename(f)[:-5]<T)
p=json.load(open(pf[-1],encoding='utf-8')) if pf else {}
bad=[f'{k} 종가 날짜 {v["date"]} != 기준 {c["basis"]}' for k,v in c['closes'].items() if v['date']!=c['basis']]
rows=[('tickers',t['code'],t.get('close')) for t in d.get('tickers',[])]+[('holdings',h['code'],h.get('close')) for h in d.get('account',{}).get('holdings',[])]
for w,k,v in rows:
    if k in c['closes'] and v is not None and abs(v-c['closes'][k]['close'])>0.005: bad.append(f'{w}.{k} 문서 {v} != closes {c["closes"][k]["close"]}')
def tx(x):
    a=x.get('account',{});return {'headline':x.get('headline'),'reconcile':a.get('reconcile'),'kiwoomTotal':a.get('kiwoomTotal'),'kiwoomDiff':a.get('kiwoomDiff'),'openOrders':json.dumps(a.get('openOrders'),sort_keys=True)}
a,b=tx(d),tx(p)
print('FAIL' if bad else 'OK',bad)
print('직전 기록과 동일:',[k for k in a if a[k] is not None and a[k]==b.get(k)])
PY
```

## 3. 시험 결과 (프롬프트에 들어갈 코드를 그대로 실제 10/6·10/7 기록으로 실행)
| 경우 | 결과 |
|---|---|
| 정정된 10/7 기록 + 맞는 closes | OK |
| 10/5 값(10/6 기록의 종가)이 섞인 기록 | FAIL — 종목 8개·보유 3개 모두 검출(SOXL은 0.35% 차이라 허용 오차 0.3%였다면 놓칠 수 있었다) |
| 종가 날짜가 기준과 다른 closes(MU 10/5) | FAIL |
| 정정 전 v2 기록(옛 문구 잔존) | 직전 기록과 동일: reconcile·kiwoomTotal·kiwoomDiff·openOrders 검출 |
| closes.json·run-doc.json 없음 | FAIL (조용히 통과하지 않음) |

## 4. 한계
- 옮겨 적는 오류와 복사만 잡는다. 종가 계산 자체가 틀리면 못 잡으므로 사람의 키움 일봉 대조는 그대로 필요하다.
- 실행 세션에서 closes.json을 실제로 만드는지는 첫 실행(10/8 06:40 KST) 전에는 확인할 수 없다(확인 필요).
- 검증용 임시 파일 쓰기 허용은 "절대 금지"의 파일 쓰기 금지에 대한 예외 문구가 늘어나는 것이다. 사용자 폴더 쓰기는 여전히 없다.

## 5. 적용·검증·롤백
1. 적용: 라이브 프롬프트에 위 3곳만 삽입한 한 번의 update_trigger(길이 +2213자). 적용 뒤 라이브 원문과 기대본을 글자 단위로 대조한다.
2. 확인: 10/8 06:40 KST 실행 뒤 runs/2026-10-08에서 종가 날짜·값, "직전과 동일" 한 줄, 점검 상태.
3. 롤백: 삽입한 문장 3곳을 지운다.
4. v3.11 초안 문서에도 같은 3곳을 반영한다.
