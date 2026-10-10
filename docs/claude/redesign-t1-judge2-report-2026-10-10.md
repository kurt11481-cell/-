---
id: redesign-t1-judge2-report-2026-10-10
title: 재설계 T1 독립 Judge 2차 판정 — 조건 C1~C6·T1B-1·T1B-2 (r3)
date: 2026-10-10
class: 권한·한도 변경(옛 K3) — 독립 Judge 2차
judge_prompt: docs/claude/redesign-t1-judge2-prompt-2026-10-10.md
first_judge: docs/claude/redesign-t1-judge-report-2026-10-10.md
target: .claude/worktrees/auto-core-t1 (base 74ad71e, 미커밋 — 추적 수정 20 + 새 파일 12)
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: Cowork(병합·배포 판단) · 관제판 redesign-t1 / redesign-t1b
---

# PASS-WITH-CONDITIONS

- 코드 쪽 조건 C1~C6, T1B-1, T1B-2는 모두 들어갔고 테스트가 통과한다. J1~J13 회귀는 없다. 병합과 compare 시작은 막지 않는다. Builder가 다시 고칠 것은 없다.
- 남는 조건은 1건(R1)이다. C3 가운데 06:40 로더 푸시 부분인데, r3가 배포 때 Cowork가 붙이도록 넘긴 것이라 이 diff에는 없다. apply를 켜기 전에 처리한다.
- 확인 방법: Builder 보고는 증거로 쓰지 않았다. `git -C .claude/worktrees/auto-core-t1 diff 74ad71e`, 새 파일 원문, 테스트를 직접 확인했다. 키움 조회·kiwoomcli·`auto_core.py daily`·`reconcile_broker_state.py auto/apply`는 실행하지 않았다. 상태 파일에서는 revision과 기록 시각만, 조회 정책에서는 별칭이 있는지만 읽었다(금액·값은 출력하지 않음). 추가 시나리오 1건은 stdin으로 실행했고 저장소 파일은 쓰지 않았다.

## 항목표

근거 경로는 `manage-us-stock-strategy/` 기준이고 줄 번호는 worktree 파일 기준이다.

| 항목 | 판정 | 근거 |
|---|---|---|
| C1 쓰기 직전 재확인 3종 | PASS | `apply_user_confirmed_broker_snapshot.py:361-391`의 `_auto_core_write_recheck`를 `_write_applied` 바로 앞(:473)에서 부른다. 확인하는 것: ① auto_core.json을 다시 읽어 kill_switch가 false가 아니면(:375) 또는 mode≠apply면(:377) 거부. ② `git_provenance`를 다시 계산해 guarded dirty가 있거나 git을 쓸 수 없거나(:379) 커밋이 바뀌면(:385) 거부. ③ 선언이 없거나 상태가 NO_EXTERNAL_FLOW·DECLARED_IN_FULL이 아니면(:389) 거부. 거부 테스트는 각각 있다: `tests/test_auto_core.py:1121`(kill·compare·파일 삭제), `:1132`(guarded·git 불가·다른 커밋), `:1145`(선언 없음·UNDECLARED), `:1163`(실행 도중 kill switch 켜짐·코드 변경 → FAIL). 모두 상태·원장·백업·audit가 바뀌지 않음을 assert한다(:1113-1119). 대조군은 :1159. |
| C2 guard 범위 | PASS | `GUARDED_PREFIXES` = scripts·schemas·assets(`scripts/auto_core_reconcile.py:1115`)이고, 그 아래 추적 파일 전체(M·staged·D·MM·A, rename은 두 이름 모두)를 guarded로 본다(:1194-1197). apply 모드에서는 kill switch 다음, 읽기 전에 FAIL한다(`reconcile_broker_state.py:385`). 같은 검사를 C1이 쓰기 직전에 한 번 더 한다. 테스트 `:948`: validation_common·evaluate_alerts·portfolio_exposure·portfolio_review_journal·kiwoom-broker-shadow.schema(옛 고정 목록 밖) 각각에서 FAIL, 조회 0건, 상태 그대로. `:1527`: tests·references·미추적 파일은 제외. |
| C3 warnings[] | PASS (배포 부분 R1) | `proposal_warnings`(`auto_core_reconcile.py:886-890`)를 reconcile.json(:1077), result.json(`auto_core.py:328`), LATEST.json(:388, result와 같음)에 싣는다. `reasons`·`recordable`에는 들어가지 않는다. 스키마에서 `warnings`가 required이고 설명도 있다(`schemas/auto-core-result.schema.json`). 테스트 `:1375`: 경고 3종과 post-apply 오류가 있어도 applied≠null이고, 세 파일에 같은 목록이 실리며 스키마도 맞는다. 로더 푸시는 코드에 없다 → R1. |
| C4 D0·streak·기준 오래됨 | PASS | (a) 오늘 결제분이 안 보이면 이전 reconcile.json의 같은 날짜 `PENDING` 금액을 쓴다(`auto_core_reconcile.py:544-547`, `carried_settlements` :557-574). 이어 쓴 값(`PENDING_PREVIOUS_RUN`)을 다시 이어 쓰지는 않는다. ust21610 총액 대비 수수료 범위 검사도 그대로 받는다(:429-432). (b) 이전 기록이 없으면 그 날짜를 열어 두고 사유를 `SETTLEMENT_D0_NOT_SHOWN:<날짜>` 하나만 남긴다. 잔차도 수수료 범위 안이어야 한다(:548-553, :738-746). 그날은 streak를 유지한다(+1·reset 없음, `auto_core.py:244-249`). 다음 날은 그 전 실행부터 비교한다(`reconcile_broker_state.py:335-353`). 기준 오래됨: 창이 14일의 80%를 넘으면 compare 모드에서만 안내 한 줄을 남기고 실패로 처리하지 않는다(`auto_core_reconcile.py:899-906`, `auto_core.py:321`, :375-378). 한도를 넘으면 지금처럼 FAIL이고 쓰지 않는다. 테스트: `:1196` `:1212` `:1220` `:1237`, `:1395`(체결일 + D0일 → streak [0,1,2,3]), `:1409`(b: [0,1,1,2]), `:1438` `:1459`. Judge 추가 확인: 체결이 2거래일마다 있는 경우(10/13 세션 매도, 10/15 세션 매수, 기준 고정)에도 [0,1,2,3]이 되고, 두 D0일 모두 I3 PASS(`PENDING_PREVIOUS_RUN`)였다. |
| C5 FAIL 날 streak | PASS | 어느 단계든 FAIL이면 `_finish`에서 streak를 0으로 하고 `RUN_FAILED`를 남긴다(`auto_core.py:383-385`). 조건(올리지 않음)보다 엄격하고 "3거래일 연속 무인 실행"과 맞는다. 테스트 `:1465`: 30분봉·노출 FAIL → 0, 다음 정상일은 1. |
| C6 프로필 별칭 | PASS | `kiwoom_profile`(`auto_core.py:72-81`)을 계좌 조회보다 먼저 부른다(:312). 별칭이 비었거나 공백이거나 없으면 FAIL한다. collect_30m.ps1은 `-KiwoomProfile`이 Mandatory + ValidateNotNullOrEmpty이고(:15), 공백이면 중단하며(:29), 모든 호출에 `--profile … --mode real`을 붙인다(:42). 테스트 `:1487`(3가지 경우: 조회 0, 수집 0), `:1592`. 브리지 자체의 fail-closed(`kiwoom_runtime_bridge.py:362`)도 그대로다. |
| T1B-1 settings deny | PASS (메모 M1) | `.claude/settings.json` diff는 +4/−0이다. 기존 apply deny 다음에 지정된 4줄만 들어갔다. allow·ask와 다른 줄은 바뀌지 않았고, CRLF(25→29줄 모두 CRLF)와 들여쓰기도 그대로다. 테스트 `:1600`. |
| T1B-2 기대 문구 | PASS (메모 M4) | `tests/test_reconcile_broker_state.py:959-968`은 "only from a verified read-only broker snapshot"을 요구하고, 약화된 "or" 문구를 금지하며, `reconcile_broker_state.py apply` 또는 `auto-core … invariant`, "Never infer (a fill/fills) from price mov…"를 요구한다. 스냅샷 + (사용자 경로 또는 불변 조건 경로) + 체결은 브로커 기록이라는 뜻이 유지된다. CLAUDE.md·AGENTS.md 모두 통과한다. |
| J1 범위 | 유지 | 추적 20(1차 19 + settings.json) + 새 12(1차 11 + r3 지시문)이고, 모두 허용 경로 안이거나 deny 예외다. `--numstat`과 `--ignore-cr-at-eol --numstat` 결과가 같다. 수정 파일은 줄 수 = CRLF 수다. 무시된 상태 파일 2개와 settings.local.json의 해시는 메인과 같다. 원본 collect_30m.ps1 sha256 9717579c…도 그대로다. policies·stock-strategy-system·CLAUDE.md 변경 0. |
| J2 compare 무쓰기 | 유지 | `apply_auto_core`를 부르는 곳은 `auto_core_reconcile.py:1062` 하나이고 :1058(`mode=="apply"`) 안에 있다. r3가 새로 만든 쓰기 경로는 없다(이어 쓴 금액은 읽기만 한다). |
| J3 apply | 강화 | 1차에서 라이브러리가 다시 보지 않던 kill_switch·guard·선언을 C1이 다시 확인한다. |
| J4·J6 체결·현금 | 유지 | 이어 쓴 금액은 이전 실행의 브로커 조회값(대기 슬롯)이고 수수료 범위로 묶인다. 가격 추정은 없다. kiwoom_broker_shadow.py·manual_data_guards.py는 1차 Judge 뒤에 수정되지 않았다(mtime 10:05·10:12). CashDefinitionTests도 통과한다. |
| J5 주문 경로 | 유지 | r3에서 바뀐 파일과 브리지에서 `ordr`·`ust2000x`·`overseas orders`·`kiwoom_order`·`order_submit`·`kt1000x`를 찾은 결과 0건이다. kiwoomcli 호출은 candles 하나뿐이다. |
| J7·J8 기록·사람 경로 | 유지 | propose·show·apply·CONFIRMATION_METHODS는 바뀌지 않았다. 재확인은 `apply_auto_core`에만 있다. 테스트 `:1043`·`:1061`이 통과한다. |
| J12 Windows | 유지 | ps1 ASCII 테스트가 통과한다. run·register 스크립트는 1차 Judge 뒤에 바뀌지 않았다. |
| 테스트 | PASS | 직접 실행한 결과: test_auto_core **89 OK**(69→89), reconcile_broker_state 56 OK(test_agent_rules 해소), cash_flow_evidence 19·kiwoom_broker_shadow 24·s1b_plan_b 30 OK, materialize 26(기준선 E1·F3만 실패). 전체(test-runner 실행, 원본 출력에서 직접 셈): `Ran 2584`(2564→2584), failures 19 + errors 9 = **28** = 기준선 29(test-baseline-2026-10-09.md 27 + 0단계 e 2) − `test_agent_rules`. 새 실패 0. 바뀐 테스트 파일마다 `def test_` 수가 줄지 않았다. 삭제된 assert는 T1B-2의 2개뿐이고 대체되었다. 스키마 감사 PASS. |

## 남는 조건

- **R1 (C3 나머지, apply 켜기 전, Cowork 배포)**: 06:40 로더가 `LATEST.json`에서 `applied ≠ null`이고 `warnings ≠ []`이면 한 줄 푸시하게 한다. 예약 프롬프트(문서)만 바꾸는 일이라 Builder 재작업이나 재Judge 대상이 아니다.

## 메모 (조건 아님)

- **M1**: deny `Bash(*auto_core.py*)`·`PowerShell(*auto_core.py*)`는 명령 문자열 어디에 있어도 걸린다. 그래서 `-p "test_auto_core.py"`(CLAUDE.md의 대상 테스트 형식)나, 그 파일명을 쓰는 grep·`git add`도 Claude Code에서 막힌다. 실제로 이번 세션에서 기존 `*reconcile_broker_state.py apply*` deny 때문에 grep 명령이 거부되었다. 병합 뒤에는 `-p "test_auto_core*"`나 전체 스위트로 실행한다(문서에 적어 두면 좋다).
- **M2**: 저장소의 C4 테스트는 체결이 1건이다. 2건 시나리오는 Judge가 따로 확인해 통과했다. 2건 테스트를 넣는 것은 선택이다.
- **M3**: C2는 조건대로 추적 파일만 본다. scripts/ 아래 미추적 .py는 guard 밖이다(위험 낮음).
- **M4**: T1B-2는 "user's explicit confirmation" 문구 자체는 더 이상 검사하지 않고, `reconcile_broker_state.py apply` 경로 이름으로 대신한다. r3 지시대로다.
- **배포 참고**:
  - `workspace/policies/auto_core.json`은 아직 없다(제안: docs/claude/redesign-t1-policy-proposals.json). 없으면 매 실행이 HOLD `AUTO_CORE_CONFIG_MISSING`이고 streak가 늘지 않는다. 정책 파일 생성은 사용자 승인 대상이다.
  - 마지막 기록은 rev 24(KST 10/10)다. compare 모드에서는 10/20 실행부터 "기준 오래됨" 안내가 나오고, 10/23 실행부터 FILL_WINDOW_TOO_LONG FAIL이 난다(기록 모드를 켜거나 사람 경로 기록이 있으면 다시 시작). streak 3에는 첫 실행을 포함해 4번 실행이 필요하다(화~토 실행, 하루도 어긋나지 않을 때). 따라서 늦어도 10/17(토) 실행부터 compare가 돌아야 10/22 실행에서 3에 닿는다.
