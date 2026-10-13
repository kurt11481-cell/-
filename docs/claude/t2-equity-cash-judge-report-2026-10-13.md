---
id: t2-equity-cash-judge-report-2026-10-13
title: t2-equity-cash 독립 Judge 보고 (읽기 전용)
date: 2026-10-13
prompt: docs/claude/t2-equity-cash-judge-prompt.md
builder_prompt: docs/claude/t2-equity-cash-builder-prompt.md
builder_report: .claude/worktrees/t2-equity-cash/docs/claude/t2-equity-cash-report.md
model: Opus 5.5 · xhigh · Builder와 다른 새 세션, 메인 체크아웃 기준
writes: 이 보고서 1개만 (코드·테스트·정책·상태·일지 수정 없음, 커밋 없음)
---

# 범위와 방법

- 기준: 메인 체크아웃 HEAD = worktree HEAD = `1fe378b` (worktree 브랜치에 커밋 없음). 메인 체크아웃의 `manage-us-stock-strategy/` 변경 없음.
- 줄 번호의 `wt/`는 `.claude/worktrees/t2-equity-cash/`(변경 후 파일)이다.
- 실행한 것: worktree 안에서 `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"`와 새 파일 단독 실행, `git status/diff`, grep, sha256, 파이썬 순수 산술(저장소 코드 미import), 2026-10-13 스냅샷·결정 기록에서 현금 3칸·수량·계좌 칸만 읽기(계좌 식별자 출력 없음).
- 실행하지 않은 것: 키움·auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply, 전체 스위트(Judge 프롬프트 허용 목록 밖), 스키마 감사(스키마 파일이 바이트 단위로 같아 결과가 바뀔 수 없음).
- Builder 보고의 파일 sha256 8개를 다시 계산해 모두 일치함 → 보고 작성 뒤 변경 없음.

# 판정 표

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| 1. 바뀐 파일·줄이 지시문 범위뿐. rules.C·주문표 수량/가격·S7·대조 모듈·G1 대조·리플레이 불변 | PASS | worktree `git status`: M `auto_core_decide.py`·M `auto_core_tickets.py`·?? 새 테스트·?? 보고서, 이 4개뿐. `git diff --stat` 2 files +52 −10(hunk 12개). `auto_core_rules.py`·`auto_core_compare.py`·`auto_core_replay.py`·`kiwoom_broker_shadow.py`·`auto_core_reconcile.py`·`schemas/` diff 없음(sha256도 Builder 보고와 같음). G1은 여전히 주문가능 `cash`로 대조: wt/…/auto_core_decide.py:523. 판정 매수 현금 `cash`(주문가능) 줄 그대로: :511. 리플레이 호출 그대로 `deposit=cash`: wt/…/auto_core_replay.py:252. diff 안의 변경은 import(:46)·상수(:69~73)·`equity_cash`(:141~163)·`_run`(:505, :512~513, :631, :646)·docstring(:838~839)·`_dashboard`(:1029~1030)와 tickets `rule_file_nominal` 인자명·docstring·상태 문자열(wt/…/auto_core_tickets.py:152~166)뿐. `_dashboard`의 shock 줄 재배치는 같은 식이라 출력 동일(T6 `dashboard` 전체 동등 비교로 확인) |
| 2. `equity_cash`: 가드 통과 → 주문가능, 실패·누락 → 알려진 값 최솟값, 모두 없음 → None. 가드 import(복제 없음). 가격 추정 금액 없음 | PASS | 모두 없음 → `(None, CASH_UNAVAILABLE)`: :153~154. 주문가능·출금가능 누락 → `min(known)`, `MIN_FALLBACK:CASH_VALUE_MISSING:…`: :155~157. 가드 실패 → `min(known)`, `MIN_FALLBACK:<코드>`: :160~162. 통과 → 주문가능: :163. 가드는 `from kiwoom_broker_shadow import order_available_cash_errors`(:46) 하나뿐이며 decide 안에 같은 비교식 없음; 테스트가 동일 객체임을 확인(`assertIs`, wt/…/test_auto_core_equity_cash.py:83). 입력은 스냅샷 현금 3칸(`EQUITY_CASH_FIELDS` :70)뿐이고 수량은 가드의 참/거짓 판정에만 쓰임(:158~160) — 가격 × 수량 금액 없음. T1 쪽 호출(kiwoom_broker_shadow.py:245~247, manual_data_guards.py:202~217)과 같은 (settled, held) 쌍·같은 ±$1 허용 |
| 3. 2026-10-13 값(27,695.15·N 1.2466·EV4 없음·V6 none)이 함수를 거친 계산으로 확인 | PASS | 테스트 입력이 실측과 같음: 2026-10-13 스냅샷 예수금 9,396.68·출금가능 9,396.68·주문가능 12,469.18, MVLL 159/159·NBIS 13/13·SOXL 75/53(이 세션에서 직접 읽음). 같은 날 decision.json의 기존 값 total 24,622.6487·N 1.402175·review·EV4 true·s7_hwm 30,255.36. 테스트는 `equity_cash` → `rule_file_nominal` → `v6_account`·`ev4_open` 순서로 계산(test_auto_core_equity_cash.py:54~61, :71~80)하고, decide() 전체 실행으로도 확인(:279~309). 별도 순수 산술(Decimal, 배수 MVLL 2·NBIS 1·SOXL 3 = alert_policy): 보유 15,225.9687 + 12,469.18 = 27,695.1487, N 1.246618, V6 none(cushion +8.07%), EV4 False(27,695.15 > 25,626.55, > 30,255.36×0.9 = 27,229.824); 기존 방식 24,622.6487·1.402175·review·EV4 True — 실제 결정 기록과 일치 |
| 4. 매수 결제 전 이중 계산 없음(T3), 미결제 없을 때 결과 불변(T4·T6) | PASS | T3: 주문가능 7,000 < 출금가능 10,000 → `MIN_FALLBACK:CASH_ORDER_AVAILABLE_BELOW_WITHDRAWABLE`, 총자산 10,000(기존 13,000 = 이중 계산): test_auto_core_equity_cash.py:105~121; decide 경로에서도 −3,000만 바뀜: :256~276. T4: 세 값 같음 → `rule_file_nominal` 결과 dict 전체 동일 + 골든: :123~133. T6: 기존 decide 픽스처 4종에서 `exposure.cash_basis`·`journal.decision_sha256` 밖 기록 전체·dashboard 동일: :235~245, :247~254. 비교 대상 `old_deposit`(:49~51)은 변경 전 `_decimal(cash.foreign_currency_deposit)`와 같은 값이고, 변경 후 코드의 나머지 차이(runCore 필터·shock 줄 재배치·None일 때만 쓰이는 상태 문자열)는 이 픽스처들에서 출력에 영향 없음을 코드로 확인 |
| 5. 권한 표지 줄·주문 경로·정책/상태 쓰기 없음, 키움 호출 없음, 커밋 없음 | PASS | diff의 +/− 줄과 새 테스트 전체에서 `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY` grep 0건. 주문 도구·`kiwoom_query`·`confirm` 문자열 0건. 새 import `kiwoom_broker_shadow`는 `validation_common`만 import하는 순수 정규화 모듈(kiwoom_broker_shadow.py:1~12) — 네트워크·키움 호출 없음. 테스트는 `tempfile.TemporaryDirectory` 픽스처(test_auto_core_decide.py:73)에만 씀. worktree HEAD = 1fe378b(커밋 없음). 비ASCII 0건(스크립트 2·테스트 1) |
| 6. 대상 테스트 통과(새 실패 0) | PASS | 이 세션 실행: `-p "test_auto_core*.py"` → Ran 336, OK (skipped=1) (Builder 기준선 324 + 새 12). 새 파일 단독 → Ran 12, OK. 실행 후 `git status` 변화 없음. 전체 스위트(2,979, 기준선과 같은 실패 28건)는 Builder 보고 4절 근거이며 이 Judge는 허용 목록에 따라 다시 돌리지 않음 |
| 7. `CASH_UNAVAILABLE` 읽는 곳, runCore 키 불변, 결정 스키마가 새 칸 수용 | PASS | `DEPOSIT_UNAVAILABLE`/`CASH_UNAVAILABLE` grep(메인 체크아웃 전체, graphify-out·worktrees 제외): 생산처 auto_core_tickets.py와 두 프롬프트 문서뿐 — 리터럴로 읽는 곳 없음, 기존 다른 의미의 같은 문자열도 없음. 유일한 소비는 표시 `"N " + status`(wt/…/auto_core_tickets.py:233). runCore: `cash_basis`만 뺀 사본(wt/…/auto_core_decide.py:1029); 공휴일 이월 경로는 원천 기록의 runCore를 복사(:786)하므로 역시 없음; T6 `assertNotIn`(test:243). 대조 모듈은 exposure의 `N`·`caps`·`peaks`만 키로 읽음(auto_core_compare.py:222~235). 결정 스키마 `exposure`는 제한 없는 `{"type": "object"}`(schemas/auto-core-decision.schema.json:70) → 스키마 변경 불필요, 테스트가 `validate_instance(..., DECISION_SCHEMA) == []` 확인(test:221, :296) |
| 8. (의견) 위험 1이 변경 전보다 나빠지지 않았나 | PASS(의견) | 아래 "항목 8 의견" 참고. 낮게 잡히는 날이 "매도 다음 날마다"에서 "가드 실패일·열린 매수 예약일"로 줄었고, 가드 실패일의 값은 기존(예수금)과 같거나 같은 방향이다. 나빠지지 않음 |

# 고칠 최소 항목

없음 (병합을 막는 결함 없음).

# 참고 관찰 (병합 비차단)

1. **줄 끝 기술 정정**: Builder 보고 5절 4는 "줄 끝은 기존 파일과 같은 LF 유지"라고 적었으나, 실제 작업본은 수정된 두 스크립트가 기존과 같은 CRLF(인덱스 LF, `git ls-files --eol` i/lf w/crlf)이고 새 테스트만 작업본 LF다. 파일 안에 줄 끝이 섞인 곳은 없고 커밋 시 인덱스는 모두 LF라 저장소 불일치는 생기지 않는다.
2. **예수금만 없고 가드 통과 → `ORDER_AVAILABLE`**: Builder는 "값 누락"을 가드 입력(주문가능·출금가능) 누락으로 해석했다(:155~157, T5 마지막 경우 test:156~157). 가드가 통과하면 승인된 정의가 주문가능 하나로 정해지므로 지시문 "가드 통과 → 주문가능"과 맞는다.
3. **음수 값 미점검**: T1 검증은 `CASH_VALUE_NEGATIVE`를 따로 막지만(kiwoom_broker_shadow.py:240~241) `equity_cash`는 그대로 최솟값에 넣는다. 기존 fc_entra 경로도 점검이 없었고, 그런 날은 T1 대조가 실패해 G1으로 HOLD된다 — 기존보다 나빠지지 않음(Builder 위험 4와 같음).
4. **가드의 성격**: T1 가드는 "결제 > 보유 행이 하나라도 있는가"만 보고 금액 일치까지는 보지 않는다. 지시문대로 승인된 가드를 그대로 쓴 것이며 이번 범위 밖이다.
5. **지시문 숫자**: Builder 지시문의 "D+1 매도 결제 3,072.51"은 실제 차이 3,072.50이다(Builder 보고는 3,072.50으로 맞음). 결과에 영향 없음.
6. **결정 기록 해시**: `decision_identity_hash`는 exposure를 포함하므로(wt/…/auto_core_decide.py:728~740) 같은 입력에서도 해시가 변경 전과 달라진다. 지금은 decision_mode compare라 일지 기록이 없어 영향 없음(Builder 위험 3과 같음).

# 항목 8 의견 (위험 1: 낮게 잡힌 날의 EV4가 ev4_sessions에 남아 며칠 매수를 막음)

- 경로: decide는 이전 기록 중 `account.ev4_open`이 참인 날의 평가 세션을 `ev4_sessions`로 모으고(wt/…/auto_core_decide.py:610), R-REC1은 창 안의 그 날을 EV4 사건으로 세어 RG 관문을 통과할 때까지 매수만 막는다(auto_core_rules.py:793~794).
- 변경 전: 매도 체결 뒤 결제 전에는 fc_entra에 매도대금이 빠져 총자산이 매번 낮게 잡혔다. 2026-10-12(10-13 실행)가 실제 예: 24,622.65 → review·EV4 열림(바른 값 27,695.15면 둘 다 아님).
- 변경 후: 결제 > 보유 행이 있는 보통의 매도는 가드를 통과해 주문가능을 쓰므로 낮게 잡히지 않는다. 낮게 잡힐 수 있는 날은 (a) 가드 실패일 — 최솟값 = 대개 예수금이라 변경 전과 같은 값, (b) decide 시점에 열린 매수 예약금이 있는 날 — 드물고 그날은 G0_OPEN_ORDERS로 HOLD뿐이다. (c) 매수 결제 전: 변경 전에는 이중 계산으로 높게 잡혀 EV4가 가려졌고, 이제 바른 값이라 EV4가 열릴 수 있다 — 과대평가를 바로잡은 것이며 매수만 막는 방향이다.
- 결론: 위험 1의 발생 빈도는 줄고 크기는 커지지 않았다. 변경 전보다 나쁘지 않다.
- 알아둘 점(이번 범위 밖): 이 변경은 소급하지 않는다. 이미 기록된 2026-10-13 결정의 `ev4_open: true`(평가 세션 2026-10-12, 옛 정의로 낮게 잡힌 값)는 병합 뒤에도 `ev4_sessions`에 남아 RG 관문 통과 전까지 R-REC1 EV4 사건으로 매수를 막는다. 지금은 compare 모드라 사용자 주문 입력에는 영향이 없다. 지난 기록을 고치는 일은 하지 말아야 하며, 필요하면 이제 기록에 남는 `exposure.cash_basis`를 근거로 MIN_FALLBACK일의 EV4를 표시하거나 따로 다루는 방안을 별도 작업으로 검토할 수 있다(의견만).

# 결론

지시문 "Judge 확인 항목" 1~6과 추가 항목 7·8 모두 통과. 병합 대상 4개 경로(코드 2·새 테스트·Builder 보고)는 Builder가 보고한 sha256 그대로다.

VERDICT: PASS
