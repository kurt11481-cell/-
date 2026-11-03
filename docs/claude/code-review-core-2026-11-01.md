# 코드 리뷰 ① 코어 판정 (2026-11-01)

status: 읽기 전용 리뷰 결과 — 코드·정책·예약 변경 없음. 수정은 개발 큐 후보로만 둔다(K3 해당 여부는 각 항목에 표시).
작성: 사장실 회사PC 스레드 "전체 코드 리뷰 진행" (계획 승인: 사장 버튼 2026-11-01 13:03 KST)
기준: 브랜치 codex/master-recovery-expansion HEAD d2c9d9e

## 읽은 범위 (전부 다 읽은 것은 아님)
| 파일 | 줄 | 읽은 정도 |
|---|---|---|
| auto_core.py | 426 | 전체 |
| auto_core_decide.py | 1285 | 전체 |
| auto_core_tickets.py | 1304 | plan·매도·매수 회로·보유 범위(721~1190행) |
| auto_core_rules.py | 993 | rrec1·ev3_dates(733~905행), 예외 처리 grep |
| auto_core_inputs.py / bars / compare / replay | 1328 | 예외 처리 grep만 (**미검토**) |

참고: ev3 날짜를 확인하려고 회사PC VM에서 auto_core_rules 모듈을 1회 import했다. 순수 함수만 썼고 파일 쓰기는 없었다. 이후에는 읽기 명령만 썼다.

## 발견

### C-1 (중) 회복 관문 문서가 없거나 서식이 바뀌면 사용자 지정 충격 이벤트가 조용히 사라짐 — fail-open
- auto_core_decide.py 644~645행: `recovery-gate-R-REC1-2026-10-09.md`가 없으면 빈 글로 처리한다.
- auto_core_rules.py 69행 `EV3_LINE`은 "- 이벤트 YYYY-MM-DD(EV" 서식에 정확히 맞는 줄만 읽는다. 지금 읽히는 날짜는 2026-10-08 1건이다.
- rules.py 891~893행: 이벤트가 하나도 없으면 `status ok, open False`가 되어 R-REC1이 매수를 막지 않는다.
- 문서가 없을 때 inputs에는 sha256 None으로 기록되지만, 어떤 관문도 이것을 막지 않는다.
- 영향: 문서 이름 변경·서식 수정·삭제 한 번으로 EV3a 이벤트가 빠진다. 다른 EV1·EV2 이벤트가 같은 창에 있으면 영향이 줄어든다(확인 필요).
- 수정 후보: 문서가 없거나 EV3 줄이 0건이면 G1 사유(예: `G1_RECOVERY_DOC_UNREADABLE`)로 매수만 막는다. 코어 판정 입력이므로 **K3**.

### C-2 (중, 확인 필요) 보유 종목의 S7 비중이 비어 있으면 현재 비중을 0으로 계산
- auto_core_decide.py 1077행은 weight가 None인 종목을 빼고, auto_core_tickets.py 1133행은 `weights.get(symbol, 0)`을 쓴다.
- 보유 종목인데 S7 review의 weight가 None이면 current = 0이 되고, 목표까지 전량 매수하는 delta가 나온다.
- S7 fail_closed·G1_S7 관문(decide 1013~1017행)이 같은 상황을 먼저 막는지는 **확인 필요**.
- 수정 후보: 보유 종목은 weight가 없으면 `G1_WEIGHT_MISSING`으로 막는다(fail closed). **K3**.

### C-3 (하) 종가 기록이 없는 종목의 거래소를 NASDAQ로 가정
- auto_core_decide.py 598~601행: `exchange or "NASDAQ"`. T1(auto_core.py 127~140행)은 같은 경우 추측하지 않고 FAIL로 처리한다. 두 쪽 규칙이 다르다.
- T1은 보유 종목·관심 명단·symbols_extra만 모은다. 그래서 RG2 기준 지수(rg2_benchmark)처럼 T1이 모으지 않는 종목에서 이 경로가 실제로 쓰이는지 **확인 필요**.
- load_symbol이 exchange를 어디에 쓰는지에 따라 영향이 달라진다(확인 필요).

### C-4 (하) 일지 기록 뒤 실패하면 같은 평가 세션이 반복해서 FAIL할 수 있음
- decide 724~727행 주석이 이 경로를 인정하고 있다. 기록이 끝난 뒤 실패하면 다음 날 append가 CORE_DECISION_ALREADY_RECORDED로 거부되어 FAIL이 된다.
- fail closed라 안전 쪽이지만, 풀려면 사람이 개입해야 한다. 절차 문서가 있는지 **확인 필요**.

### 문제 없음으로 본 것
- 매수 회로는 관문 사유가 하나라도 있으면 막는다: G0·G1·연구 기록·요건 1~5·정책 상품·S7 목표(tickets 1112~1190행). 현금이나 equity를 모르면 막는다.
- 보유 범위 계산 오류는 HOLD_RANGE_UNVERIFIED로 매수를 막는다(tickets 829·910·950행).
- 중지 스위치, apply 가드, 일지 쓰기 직전 재확인(decide 738~749행)이 있다.
- 실패 기록은 주문표를 0으로 만든다(_settle 1248~1269행).

## 결론을 바꿀 조건
C-1·C-2가 다른 관문에 이미 막혀 있다는 근거(테스트나 코드)가 나오면 하로 낮춘다.

## 추가: 2차 리뷰 — 판정 비교·봉·모드 (2026-11-02 15:5x KST, 읽기 전용)
- 반영된 수정: C-1 잔여·C-2는 core-failclose로 병합됐다(6aea772, 2026-11-02 15:06 KST). C-1의 "문서 없음·미커밋"은 coreinput2(db56303)가 이미 막았다.
- auto_core_compare.py(판정 대조·연속 일수): 설명 파일(redesign-t2-compare-explained.json)은 coreinput2 뒤로 커밋 검사를 받는다. 커밋 안 됐거나 링크면 아무것도 설명하지 않는다(auto_core_decide.py 836~849행). 연속 일수는 Cowork 안내(next_action_for_cowork)에만 쓰인다. decision_mode를 바꾸는 일은 사람이 한다(auto-core-config.schema.json 5행). 결함 없음.
- decision_mode: 설정에 키가 없으면 compare다(decide 418행). apply면 일지에 쓰기 직전에 모드·kill_switch·provenance를 다시 확인한다(770~779행). 결함 없음.
- auto_core_bars.py: 봉 하나만 빠져도 그 세션의 고가·저가·거래량은 INCOMPLETE가 된다. 기록에 없는 큰 가격 점프는 SPLIT_SUSPECTED로 그 종목 지표를 모두 unknown으로 만든다. 기업 행사 기록이 INVALID면 그 종목을 쓰지 않는다(171~196행). fail-closed다. 거래소 기본값이 NASDAQ인 점은 C-3과 같은 뿌리다(bars 91·172행, decide 631행).
- **미검토**: auto_core_replay.py(과거 재현, 운영 판정 경로 밖), auto_core_inputs.load_research의 세부, 봉의 "마지막 세션 = 평가 세션" 신선도 확인 위치.

## 추가: 3차 리뷰 — 리서치 기록·리플레이 (2026-11-03 21:5x KST, 읽기 전용)
읽은 범위: auto_core_inputs.py 250~385행(check_record·load_research), auto_core_decide.py 594~625행, auto_core_rules.py 215~232·540~552행, auto_core_replay.py 397~436행. 기준 커밋 8f2fdd5.

### RI-1 (하) 오늘 리서치 기록의 평가 세션이 코어의 평가 세션과 같은지 확인하지 않는다
- check_record는 기록 날짜, 달력 안 세션인지, 작성 시각(그 세션 16:00 ET 이후, 판정 시각 이전)을 본다(auto_core_inputs.py 296~306행). 그러나 기록의 evaluation_session이 decide가 계산한 평가 세션(auto_core_decide.py 522행)과 같은지는 어디에서도 비교하지 않는다(grep).
- 그래서 작성 도구가 실수로 지난 세션을 적으면, 지난 세션의 실적 일정·공식 사실이 오늘 것으로 쓰인다(fail-open).
- 실제 기록: 최근 12개(10/17~11/03 KST) 모두 기록 날짜 바로 전 미국 세션을 적었다. 어긋난 적은 없다.
- 고치는 법(안): load_research 결과 today의 evaluation_session ≠ 평가 세션이면 status를 INVALID(RESEARCH_RECORD_SESSION_MISMATCH)로 둔다. auto_core_* 파일이라 권한 작업 개발 큐 후보다. 급하지 않다.

### 문제 없음으로 본 것
- 봉 신선도: 평가 세션 종가가 없으면 build_series가 None을 돌려주고, 그 종목은 CLOSE_MISSING으로 UNK가 된다(rules 223·544~547행). fail-closed다. 위 2차의 "신선도 확인 위치" 미검토 항목은 이것으로 닫는다.
- 리서치 사실: 공식 도메인이 아니면 버린다. 피해 도메인 사실은 RG1에만 쓰인다. 발표 시각이 판정 시각보다 뒤이거나 요약이 200자를 넘어도 버린다(310~331행).
- auto_core_replay.py: 일지는 합성 값이다. 쓰는 곳은 workspace/outputs/auto-core/replay/<run-id>/ 두 파일뿐이다(427~428행). 운영 상태를 바꾸지 않는다. 거래소를 모르면 NASDAQ으로 두는 것(424행)은 C-3과 같은 뿌리다.
