---
id: core-failclose-builder-prompt
title: "자동 코어 매수 쪽 fail-open 2곳 막기 — core-failclose (C-1 잔여·C-2)"
date: 2026-11-02
class: "authority(K3 — 매수 관문을 조이기만 함, 완화 없음). 개발 큐 authority: Builder Opus → Judge(Opus) → 병합은 사장 결정 + -ApproveAuthority"
source: "사장 결정 카드 '승인, 개발 큐에 올리기'(사장실 회사PC 스레드 '전체 코드 리뷰 진행', 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9EMzs2Ubs695FXidpAVLkPf, 제안 core-failclose-proposal-2026-11-02, 2026-11-02 13:16 KST, 계정=사장). 근거 docs/claude/code-review-core-2026-11-01.md C-1·C-2"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
weekly_user_touch: "0 (병합 결정 1번)"
---

## 목표
입력을 못 읽었는데도 매수를 허용하는 길 2곳을 "모르면 매수 막기"로 바꾼다. 매수 관문을 조이기만 하고, 매도 판정 규칙은 바꾸지 않는다.

## C-1 잔여: EV3 줄 형식이 깨지면 매수 막기
- 지금: `ev3_dates`(manage-us-stock-strategy/scripts/auto_core_rules.py 733~734행)는 엄격한 `EV3_LINE`(69행)만 센다. 형식이 조금만 바뀌어도 날짜가 0개가 되고 R-REC1이 열린다(auto_core_decide.py 687행).
- 바꿀 것: 회복 관문 문서(`RECOVERY_GATE_DOC`, decide 64행)에서 "목록 줄(`-`로 시작) + `이벤트` + YYYY-MM-DD + `EV3`"가 한 줄에 있는 수를 느슨하게 센다. 그 수가 `ev3_dates` 결과 수보다 크면 사유 `CORE_INPUT_PARSE:EV3`를 낸다.
- 사유는 `core_input_guard`(auto_core_inputs.py 208~251행)의 reasons와 **같은 길**로 보낸다. 그래서 매수가 막히고 재배치 후보가 빠지는 효과도 coreinput2와 같다. 새 길을 만들지 않는다. `core_input_guard` 안에 넣을지, 그 결과에 더할지는 Builder가 정하고 보고한다. 단 R-REC1 읽기가 리서치 대기 뒤에 있으므로(decide 564·644행 부근) 검사는 대기 전에 한다(coreinput2와 같은 자리).
- `EV3_LINE`과 `ev3_dates`의 결과는 바꾸지 않는다(엄격한 판정은 그대로, 느슨한 수는 비교용만).
- 지금 문서(docs/claude/recovery-gate-R-REC1-2026-10-09.md 71행)에서는 새 사유가 나오지 않아야 한다. 시험으로 확인한다.

## C-2: 보유 종목인데 S7 비중이 없으면 그 매수만 막기
- 지금: manage-us-stock-strategy/scripts/auto_core_tickets.py 1136~1138행 `current = Decimal(str(ctx["weights"].get(symbol, 0)))`. weights는 decide 1116행에서 비중 있는 positions만 담는다. 보유(`held`)인데 비중이 빠지면 0으로 보고 목표까지 더 사는 수량이 나온다.
- 바꿀 것: `held`이고 `symbol not in ctx["weights"]`이면 `blocked.append({"symbol": symbol, "side": "buy", "reasons": ["CURRENT_WEIGHT_MISSING"]})` 후 `return None`. 첫 매수(`held` 아님)는 지금처럼 0에서 시작한다.
- 이 차단으로 재배치 후보(redeploy_candidate, tickets 328~331·735~739행 부근)가 달라지는지 확인해 보고한다.

## 바꿀 파일 (이 안에서만)
- manage-us-stock-strategy/scripts/auto_core_inputs.py
- manage-us-stock-strategy/scripts/auto_core_decide.py
- manage-us-stock-strategy/scripts/auto_core_rules.py
- manage-us-stock-strategy/scripts/auto_core_tickets.py
- manage-us-stock-strategy/tests/test_auto_core_input_guard.py
- manage-us-stock-strategy/tests/test_auto_core_tickets.py
- docs/claude/core-failclose-report.md (보고)
고칠 필요가 없는 파일은 고치지 않는다.

## 시험
- 추가: (1) 지금 문서 형식 → 새 사유 없음 (2) EV3 줄 띄어쓰기 변형(`- 이벤트 2026-10-08 (EV3`) → `CORE_INPUT_PARSE:EV3`, 매수 막힘 (3) EV3 줄이 아예 없는 문서 → 새 사유 없음(느슨·엄격 모두 0) (4) 보유 + 비중 없음 → `CURRENT_WEIGHT_MISSING` (5) 보유 + 비중 있음 → 지금과 같은 수량 (6) 첫 매수 + 비중 없음 → 지금과 같음.
- 실행 명령은 이 형식만, 글자 그대로: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"`. 앞에 환경 변수·옵션을 붙이지 않는다. 명령에 auto_core.py 문자열을 넣지 않는다. 전체 스위트와 기준선 비교는 파이프라인이 한다. git은 status·diff·log만. `python -c`·PowerShell·파이프는 쓰지 않는다.
- 기존 시험이 blocked 목록이나 결과 dict 전체를 assertEqual로 비교하면, 새 사유가 그 시험의 입력에서 나오지 않게 한다. 기존 단언·기대값을 바꾸지 않는다. 바꿔야만 하면 BLOCKED.md에 적고 멈춘다.

## 지켜야 할 것 (어기면 Judge FAIL)
1. 위 파일 밖은 손대지 않는다. 정책(workspace/policies/*)·상태(stock-strategy-system/*)·tools/·.claude/·CLAUDE.md는 금지. 고치는 파일의 줄바꿈(CRLF)을 지킨다.
2. 매수 관문을 조이기만 한다. 기존 매수 차단 사유를 없애거나 문턱을 낮추지 않는다. 매도 판정 규칙(매도 관문·card_check·_plan_sell)은 바꾸지 않는다.
3. 단언 약화·삭제·skip 추가 없음.
4. 주문·키움·일지·원장·예약과 무관. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음. 비밀(.env*·토큰·계좌번호) 읽지 않음.
5. 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/core-failclose-report.md
(a) 바꾼 줄(파일:행) (b) C-1 느슨한 패턴과, 지금 문서에서 느슨·엄격 수 (c) C-2 차단 자리와 재배치 후보 영향 (d) 대상 시험 결과 마지막 3줄과 추가 시험 이름 (e) C-1·C-2가 그날 매도표에 미치는 영향 한 줄씩. 수량·금액을 적지 않는다. 주문·권한 표지 문자열은 적지 말고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 허용 파일 안이다.
2. C-1: 느슨 수 > 엄격 수일 때만 `CORE_INPUT_PARSE:EV3`. `EV3_LINE`·`ev3_dates` 결과 불변. 사유가 core_input_guard와 같은 길로 가고, 검사가 리서치 대기 전이다.
3. C-2: `held` + 비중 없음일 때만 `CURRENT_WEIGHT_MISSING`. 첫 매수와 비중 있는 보유는 그대로다.
4. 매도 판정 규칙 변경 없음. 기존 매수 차단 완화 없음.
5. 단언·기대값·skip 변경 없음. 새 시험 6개가 실제 분기를 거친다.
6. 새 실패 0(파이프라인 checks).
7. 보고서 (a)~(e) 있음, 수량·금액·표지 없음.

```dev-run
{"task_id": "core-failclose", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 120, "builder_timeout_min": 75, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_inputs.py", "manage-us-stock-strategy/scripts/auto_core_decide.py", "manage-us-stock-strategy/scripts/auto_core_rules.py", "manage-us-stock-strategy/scripts/auto_core_tickets.py", "manage-us-stock-strategy/tests/test_auto_core_input_guard.py", "manage-us-stock-strategy/tests/test_auto_core_tickets.py", "docs/claude/core-failclose-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core): block buys when the R-REC1 EV3 line cannot be parsed or a held symbol has no S7 weight (core-failclose)"}
```
