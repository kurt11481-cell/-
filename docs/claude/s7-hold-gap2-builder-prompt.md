---
id: s7-hold-gap2-builder-prompt
title: "S7 노출 검토: 대조 HOLD로 생긴 상태 기록 공백과 팔린 종목 고점 검토 기록 때문에 영구 멈춤 — s7-hold-gap2 (s7-hold-gap은 Builder 로그인 만료로 STOP_NO_CHANGES, 같은 지시문 재실행)"
date: 2026-10-30
class: "authority(K3 — S7 HWM·검토선 평가의 fail-closed 조건 조정, H2 표시). 개발 큐 authority: Builder Opus → Judge(Opus) → 병합은 사장 승인 + -ApproveAuthority"
source: "사장 결정 카드 '착수 승인(권장안 a+b)'(사장실 회사PC 스레드 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9FHDWFwP4toHfJ5h7grmGbB, 제안 s7-hold-gap-2026-10-30, 2026-10-30 10:47 KST, 계정=사장). 진단 docs/claude/s7-hold-gap-2026-10-30.md. 1차 실행 s7-hold-gap: 10:50 KST Builder 로그인 만료(OAuth)로 변경 0, 사장 재로그인 11:18 KST 후 재등록"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
weekly_user_touch: "0 (병합 결정 1번)"
---

## 목표
2026-10-30 코어가 `G1_S7_FAIL_CLOSED`로 HOLD다. 영구 원인 둘을 고친다(셋째 `SALE_PROCEEDS_PENDING_CASH_CONFIRMATION`은 다음 정상 대조로 저절로 풀리니 건드리지 않는다).

(a) `EQUITY_GAP:2026-10-21:MVLL`. 상태 기록(원장)이 rev30(as_of 10/20) 다음 rev31(as_of 10/29)로 건너뛴다. `evaluate_review_lines`(portfolio_exposure.py 약 700~713행, else 분기)가 그 사이 세션을 rev30의 옛 보유(MVLL·NBIS)로 평가하다가 종가 누락(수집은 현재 보유 종목만)으로 `EQUITY_GAP`을 내고 멈춘다.
(b) `JOURNAL_REVIEW_UNMATCHED` ×2. `evaluate_peak_reviews`(약 873~963행)는 현재 보유 종목만 도므로, 이미 판 MVLL·NBIS의 완료된 고점 검토 일지 기록은 영원히 짝이 없다(1359행에서 hwm_line… 트리거로 셈).

## 바꿀 내용 (`manage-us-stock-strategy/scripts/portfolio_exposure.py` 만)
(a) 세션 s가 `closing_equity`에서 종가 누락으로 `equity is None`이 되는 경우에만, 다음 조건을 **모두** 만족하면 EQUITY_GAP으로 멈추지 않고 그 세션을 `result["skipped_sessions"]`에 넣고 다음 세션으로 간다(equity·HWM 갱신 없음).
 1. `snapshots`(평가 세션 이하) 중 s보다 as_of가 **늦은** 확정 상태 기록 B가 있다(`from_ledger_entry`가 True).
 2. 현재 snapshot_for(s)인 A와 B의 보유 종목 집합(`held`)이 **다르다**(보유가 실제로 바뀌었는데 그 사이 기록이 없다는 뜻).
 3. 누락된 종목은 A에서 보유이고 B에서 보유가 아니다(판 종목).
 하나라도 아니면 지금처럼 `EQUITY_GAP:<세션>:<종목>`으로 멈춘다(현재 보유 종목의 종가 누락, 보유가 같은 두 기록 사이의 누락은 그대로 멈춤).
 `skipped_sessions` 뜻이 "보류 구간 세션"에서 "평가하지 못한 세션"으로 넓어지므로 `evaluate_review_lines` docstring(605행 부근)에 한 줄 보탠다. 결과 dict에 **새 키를 만들지 않는다**.
(b) `evaluate_peak_reviews`의 마지막 미짝 수집(`for entry in peak_reviews: if id(entry) not in matched_ids`)에서, 일지 기록의 symbol이 (1) 평가 세션의 현재 보유에 없고 (2) `snapshots` 중 하나에서 보유였던 적이 있으면(포지션 종료) 미짝으로 세지 않는다. 한 번도 보유 기록이 없는 종목, 현재 보유 종목의 미짝은 그대로 `unmatched`. 새 키·새 사유 문자열 없음.

## 테스트
기존 테스트 함수는 한 줄도 바꾸지 않는다(바뀌어야 통과하는 기존 테스트가 있으면 멈추고 보고에 적는다; 특히 test_portfolio_exposure_fail_closed.py 155행 `EQUITY_GAP:{days[2]}:SOXL`은 그대로 통과해야 한다). **새 파일** `manage-us-stock-strategy/tests/test_portfolio_exposure_gap.py`만 만든다(기존 test_portfolio_exposure_fail_closed.py·hwm_fix.py의 시나리오 도우미를 가져다 쓴다). 사례:
a. 10-29 재현 모양: 기록 A(as_of d0, MVLL 보유)·B(as_of d8, MVLL 없음), 사이 세션에서 MVLL 종가 없음 → 멈추지 않고 `skipped_sessions`에 사이 세션들이 들어가고 현재 세션이 평가됨.
b. 같은 구도지만 현재 보유 종목(B에도 있는 종목)의 종가가 없으면 → 기존대로 `EQUITY_GAP`.
c. A와 B의 보유 집합이 같고 종가 누락 → 기존대로 `EQUITY_GAP`.
d. 사이 세션에 판 종목이 아닌 다른 종목 종가도 없으면 → `EQUITY_GAP`(판 종목이 아닌 누락은 건너뛰지 않음).
e. 건너뛴 세션이 있어도 현재 세션에서 HWM 대비 선 이탈이 있으면 이벤트가 잡힌다.
f. 고점 검토: 판 종목(과거 보유, 현재 미보유)의 completed 기록 → 미짝 아님. 한 번도 보유한 적 없는 종목의 기록 → 미짝. 현재 보유 종목의 짝 없는 기록 → 미짝.
- 실행: 환경 변수 `PYTHONDONTWRITEBYTECODE=1`을 켠 채 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_portfolio_exposure*"`와 `-p "test_run_portfolio_exposure_review*"` **만** 돌린다. 전체 스위트·기준선 비교는 파이프라인이 한다. `.claude/` 아래 파일을 불러오는 테스트·명령은 실행하지 않는다(보호 경로에 .pyc가 생기면 STOP_PROTECTED). 해시 계산·`python -c`·`cd`·`&&` 등 허용 목록 밖 셸 작업은 하지 않는다.

## 지켜야 할 것 (어기면 Judge FAIL)
1. `auto_core.py`·`reconcile_broker_state.py apply`·`kiwoomcli` 실행 금지. 키움 호출·예약 작업 변경·상태/정책/일지/원장 쓰기 없음. "auto_core.py"가 든 명령 금지.
2. 정책 숫자(선 비율·HWM·밴드·1.55/1.9·종목 상한)·`sale_pending_holds`·현금 흐름 보류 구간·`required_price_missing`·`CLOSE_UNVERIFIED`·NO_CONFIRMED_SNAPSHOT·EVALUATION_SESSION_NOT_IN_CALENDAR 처리 무변경. 종가 누락을 0이나 이전 종가로 메우는 코드 금지.
3. 주문·권한 줄(order_authority·quantity_authority·execution_quantity)·결과 dict의 기존 키 값 형식 변경 없음, 새 키 없음.
4. 판단이 안 되면 멈춤(fail-closed). (a) 조건 1~3을 확신할 수 없으면 건너뛰지 않는다.
5. 허용 파일만. 기존 줄바꿈(CRLF 등) 유지.
6. git commit·push·병합 없음.

## 보고 docs/claude/s7-hold-gap2-report.md
바뀐 줄(파일:행), 건너뛰기·미짝 제외 조건, 대상 테스트 결과, 남은 위험. 반드시 포함: (a) 이 변경은 제약 완화(H2): 건너뛴 세션에서 HWM 새 고점·선 이탈을 못 본다 (b) 2026-10-29 실제 입력에서 풀리는지는 병합 뒤 다음 코어 실행에서 확인 필요; 10/31 06:15 이전에는 `SALE_PROCEEDS_PENDING_CASH_CONFIRMATION`으로 HOLD 유지 (c) 같은 구조의 다른 종목 판매에도 같은 규칙이 적용됨. 이 보고서 문장에는 주문·권한 표지 문자열을 적지 말고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목 (Opus; docs/claude/hwm-fix-report.md와 hwm-fix 규칙 1을 먼저 읽는다)
1. diff가 portfolio_exposure.py·새 테스트 파일·보고서뿐이고 새 키·새 사유 문자열 없음.
2. (a) 조건 1~3 모두 필요하며 하나 빠지면 EQUITY_GAP 유지. 현재 보유 종목·같은 보유 집합 누락은 계속 멈춤.
3. 반례 탐색: 건너뛰기로 HWM 고점·선 이탈을 의도적으로 숨기는 경로가 있는지, 판 종목을 위장해 현재 보유 누락을 가릴 수 있는지, 잘못된 순서의 기록(as_of 역전)에서 건너뜀이 열리는지.
4. (b) 한 번도 보유한 적 없는 종목·현재 보유 종목의 미짝은 그대로 막힘.
5. 기존 테스트 무변경, 새 실패 0(파이프라인 checks), 보고 (a)~(c), 주문·권한 줄 무변경.

```dev-run
{"task_id": "s7-hold-gap2", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 120, "builder_timeout_min": 75, "allowed_paths": ["manage-us-stock-strategy/scripts/portfolio_exposure.py", "manage-us-stock-strategy/tests/test_portfolio_exposure_gap.py", "docs/claude/s7-hold-gap2-report.md"], "target_tests": ["test_portfolio_exposure*.py", "test_run_portfolio_exposure_review*.py"], "commit_message": "fix(s7): skip unreconciled sessions with sold-symbol close gaps and ignore closed-position peak reviews"}
```
