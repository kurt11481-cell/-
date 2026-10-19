---
id: rrec-ev4-remove-report
title: R-REC1 EV4(계좌 총액 사건) 제거 — 코어·리플레이·독립 계산기 동반 수정 — Builder 보고
date: 2026-10-19
prompt: docs/claude/rrec-ev4-remove-builder-prompt.md (메인 체크아웃의 커밋 안 된 파일, sha256 e29f0837176dcb588e4714bee8d3483eee66ffc1c0a257740e33a9ca5ac87014)
decision: docs/claude/rrec-ev4-remove-decision-2026-10-19.md (sha256 8274facd82288e955a1e111605491ff1c615697274019fcfcc6e7335b2723392) — 사용자 "결정 rrec-ev4: REMOVE"(2026-10-19 17:45 KST)
base: main 80d3a1da0957a872fc16b97ac204ee4d761198ca
worktree: .claude/worktrees/rrec-ev4-remove (branch worktree-rrec-ev4-remove), 커밋 없음
model: Opus 5.5 · xhigh (Claude Code, Windows 11, Python 3.13)
status: READY_FOR_JUDGE — 대상·전체 스위트 새 실패 0. 지시문 허용 범위 밖 3건은 이 세션에서 사용자 승인 뒤 반영(7절)
consumers: docs/claude/rrec-ev4-remove-judge-prompt.md (독립 Judge, 계산기 새 고정값 "Judge 확인" 겸함) · Judge PASS 뒤 Cowork 병합 스크립트(docs/claude/rrec-ev4-remove-merge-<날짜>.ps1)
order_authority: false
quantity_authority: none
---

# rrec-ev4-remove Builder 보고

R-REC1의 EV4(계좌 총액 ≤ V6 1차 선 또는 ≤ S7 HWM × 0.9)를 코어(`auto_core_rules`·`auto_core_decide`)·리플레이(`auto_core_replay`)·독립 계산기(`t2rc-oracle.py`)에서 함께 없앴다. 실행기 고정값(`t2rc-check-run.ps1` 16행)도 새 계산기 sha256_lf로 바꿨다. S7 코드·정책·상태·장부·일지·예약 작업·규칙 파일은 건드리지 않았다. 주문 권한 표지 줄 변경 0, 키움·auto_core.py·dev-run·dev-merge·reconcile apply 실행 없음.

## 0. worktree HEAD

- worktree HEAD = `80d3a1da0957a872fc16b97ac204ee4d761198ca` = 지시문 base. 그 사이 커밋 없음. 이 세션에서도 커밋하지 않음.
- 대상 7개 파일의 변경 전 sha256(작업 트리 CRLF 바이트 / LF 정규화)이 지시문 7행 base 값과 모두 일치(auto_core_rules 48433ab8…fbab4e / 62419561…61a11c, auto_core_decide 1013da08…7448f1 / 8ec0fa63…ff6261, auto_core_replay 8a872b88…e78fd2 / 6dbaf971…98ede6, schema e542a570…c3e6ce / fe3ef94b…c789d, references c47bbc87…9886a8 / 719880d4…2bd44, t2rc-oracle e41a7903…a7bb67 / 9f0e2238…1aae, t2rc-check-run 3735492e…cff167 / fcd8977b…80a7). 메인 체크아웃의 `docs/claude/t2rc-oracle.py` sha256_lf도 9f0e2238…(base 고정값)으로 같다.
- 지시문·결정·Judge 지시문(10-19 17:54~17:58)은 worktree에 없고 메인 체크아웃의 커밋 안 된 파일이라 거기서 읽었다(읽기만).
- `git status --porcelain --untracked-files=all`: 수정 18개 + 새 파일 1개(아래 1절). 이 보고서는 새 파일로 추가.

## 1. 파일별 바뀐 줄 (줄 번호는 base 기준)

| 파일 | +/− | 바뀐 내용 |
|---|---|---|
| scripts/auto_core_rules.py | +3 −19 | CONSTANTS 58~61행 `RREC_EV4_HWM_FRACTION`·`RREC_EV4_NEIGHBOR_MARGIN` 삭제 · 724~731행 `ev4_open()` 삭제 · `rrec1` 801행 키워드 `ev4_sessions: list[str]` 삭제 · docstring 820~821행을 "Events: EV1, EV2, EV3 (a)(b), EV5. The account-line event EV4 was removed by user decision rrec-ev4 REMOVE (2026-10-19); account drawdown is handled by the S7 review lines."로 교체 · 894~895행(`if day in ev4_sessions: kinds.append("EV4")`) 삭제. V6 상수(47~50행)·`v6_account`는 그대로 |
| scripts/auto_core_decide.py | +14 −143 | 176~283행 EV4 소급 절 전체 삭제(`EV4_REBUILT`·`EV4_NEIGHBOR_NEAR`·`EV4_NEIGHBOR_CLEAR`·`EV4_NEIGHBOR_NONE`, `_first_decide_session`, `_rebuilt_total`, `ev4_backfill_plan`, `ev4_backfill_resolve`) · 746~749행(`ev4_sessions` 조립, `backfill_plan`) 삭제 · 772행 `ev4_sessions=` 키워드 삭제 · 778~783행(`ev4_backfill=` 키워드, `decision["ev4_backfill"]`, 예외 `EV4_UNDETERMINED`) 삭제 · `evaluate_session` 1002·1006행 인자 `ev4_sessions`·`ev4_backfill` 삭제, docstring 1014~1018행에서 EV4 문장 삭제("rule-file N, V6 and EV4" → "rule-file N and V6") · 1084~1090행 → `account["s7_hwm_usd"] = s7.get("hwm_usd")` 한 줄만 남김 · rrec1 두 호출 1099·1104행 `ev4_sessions=ev4_all` 삭제 · 반환 1165행 `"ev4_backfill": backfill` 삭제 · 주석 142·167·643행 EV4 언급 정리(동작 변경 없음). import는 그대로(`timedelta`는 1198·1200행, `SNAPSHOT_FILE`은 633행에서 계속 쓰임). `snapshot_holdings` 유지 |
| scripts/auto_core_replay.py | +2 −4 | 215행 `ev4_sessions` 목록, 254행 키워드, 262~263행 누적 삭제 |
| schemas/auto-core-decision.schema.json | +1 −1 | 150행 `ev4_backfill.description`만 "legacy — written before rrec-ev4-remove; not written after"로(파일을 ASCII로 두려고 "—"는 JSON의 u2014 이스케이프로 씀). 속성·구조·required 불변 |
| references/auto-core-decision.md | +3 −3 | 83행 사건 목록에서 EV4 삭제 · 86~87행 "evaluation session's own EV4…" 문장 → "EV4 (account line) was removed 2026-10-19 (rrec-ev4 REMOVE); the S7 review lines pause buys from L2." |
| docs/claude/t2rc-oracle.py | +11 −27 | 15행 출처 목록 1줄 추가(결정 문서) · 66행 `V6_FIRST, V6_APPROACH` 삭제(grep: `V6_FIRST`는 1109행 EV4에서만, `V6_APPROACH`는 정의만 — 다른 사용처 없음) · `rrec1` 1041~1042행 인자 `equity_today, s7_hwm, ev4_hist=()` 삭제 · docstring 1047~1049행 → "EV4 removed (rrec-ev4 REMOVE 2026-10-19)." · 1109~1111행 EV4 판정 삭제 · 1587~1601행 `ev4_hist` 적재와 `res["ev4_history"]` 삭제 · 1936행 `s7hwm` 계산(이 호출에만 쓰임)과 1937~1938행 호출 인자 삭제 · 2261행 selftest 도우미 `_rg1_run`의 호출 인자 `None, None, ()` 삭제 · selftest 새 경우 6줄(2457행 뒤). `ORACLE_VERSION`·`exposure_check`의 `total_assets_v6` 출력 키는 그대로 |
| docs/claude/t2rc-check-run.ps1 | +1 −1 | 16행 `$ExpectedOracleSha256`만 9f0e2238… → 6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64 |
| tests (기존 11개) | +27 −269 | 3절 허용 변경 1~4와 승인 ①~③ |
| tests/test_auto_core_rrec_ev4_remove.py (새) | 352줄 | X1~X6 (3절) |

지운 키·출력: 결정 파일 최상위 `ev4_backfill`, `account.ev4_open`, `evaluate_session` 반환 키 `ev4_backfill`, 예외 `EV4_UNDETERMINED`, 계산기 출력 `ev4_history`.

## 2. 동치 E1~E5 확인

base 코드는 저장소 밖 사본으로 따로 프로세스를 띄워 돌렸다: ① `git archive HEAD manage-us-stock-strategy/scripts manage-us-stock-strategy/schemas manage-us-stock-strategy/tests manage-us-stock-strategy/assets manage-us-stock-strategy/references docs/claude/t2rc-oracle.py docs/claude/t2rc-check-run.ps1` + `stock-strategy-system/alert_policy.json workspace/policies`를 임시 폴더에 푼 것(`base`), ② `git archive HEAD` 전체(`base_full`, 달력 산출물 포함). 두 사본의 대상 파일 LF sha가 worktree 변경 전과 같음을 확인했다. 새 코드는 worktree에서 import했다. 모두 `PYTHONDONTWRITEBYTECODE=1`, 출력은 저장소 밖 임시 폴더만.

- **E1 코어**: 새 테스트 X5. 고정 시드 320개 합성 입력(`e1_inputs(seed)`)의 새 `rules.rrec1(x)` 결과를 `json.dumps(..., ensure_ascii=True, default=str)`(키 순서 유지)로 직렬화했다. 시드별 sha256 앞 16자리와 320개를 이은 전체 sha256(`129a009c822ec2598c50b83a1ccc2896c1a6d647947cf17e1396717ffc27abc3`)이 base `rrec1(x, ev4_sessions=[])`에서 잰 값과 모두 같다. 입력이 닿은 범위(테스트가 단언): 사건 EV1·EV2·EV3a·EV3b·EV5 전부, status ok·no·unk, RG1~RG4의 ok/no(RG1·RG2는 unk도), DS1, 훼손 사실(rg1_damage), EV3B 기록 공백, 시간 소멸·회복 닫힘(closed_at), 사건 없음. 입력 축: 훼손 사실 None/[]/있음(도메인 표지 포함), card_accepted_on 있음/없음, research_sessions None/전체/하나 빠짐/늦은 시작, rg2_series 기본/None/GRID, 평가 세션 마지막/이전.
  기대값 생성 방법(재현용, base 사본에서 실행, 아무것도 쓰지 않음): `python gen_e1.py <base 사본> <worktree>/manage-us-stock-strategy/tests/test_auto_core_rrec_ev4_remove.py`. 출력 2줄(`E1_EXPECTED = (…)`, `E1_EXPECTED_ALL = "129a009c…"`)을 테스트 파일에 그대로 넣었다.

```python
"""X5 expected values of test_auto_core_rrec_ev4_remove.py, measured on the BASE code.
usage: python gen_e1.py BASE_ROOT NEW_TEST_FILE
The base modules are imported first; the new test file is then loaded over them, so every `import` in it returns the
cached base module. e1_inputs(seed) of the new file builds the inputs; the BASE rules.rrec1 is called with
ev4_sessions=[] (the E1 definition). Prints the E1_EXPECTED tuple and E1_EXPECTED_ALL. Writes nothing."""
import hashlib
import importlib.util
import sys
from pathlib import Path

base = Path(sys.argv[1]).resolve()
new_test = Path(sys.argv[2]).resolve()
for sub in ("manage-us-stock-strategy/tests", "manage-us-stock-strategy/tests/fixtures/auto_core_t2",
            "manage-us-stock-strategy/scripts"):
    sys.path.insert(0, str(base / sub))
import auto_core_rules  # base
import auto_core_inputs, auto_core_decide, helpers, test_auto_core_decide, test_auto_core_tickets, validation_common

spec = importlib.util.spec_from_file_location("x5_new_test", new_test)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for name in ("rules", "helpers", "inputs", "decide_module"):
    origin = Path(getattr(module, name).__file__).resolve()
    assert str(origin).startswith(str(base)), (name, origin)
assert "ev4_sessions" in auto_core_rules.rrec1.__code__.co_varnames  # the base signature
hashes, dumps = [], []
for seed in module.E1_SEEDS:
    dump = module.e1_dump(auto_core_rules.rrec1(**module.e1_inputs(seed), ev4_sessions=[]))
    dumps.append(dump)
    hashes.append(hashlib.sha256(dump.encode()).hexdigest()[:16])
print("E1_EXPECTED = (")
for start in range(0, len(hashes), 6):
    print("    " + " ".join(f'"{value}",' for value in hashes[start:start + 6]))
print(")")
print(f'E1_EXPECTED_ALL = "{hashlib.sha256(chr(10).join(dumps).encode()).hexdigest()}"')
```

- **E2 decide**: 같은 합성 입력 16개를 세 판으로 돌려 JSON을 비교했다. 입력은 evaluate_session 9개(`test_auto_core_tickets.Scenario`: 기본, 현금 5,000(EV4만 켜지는 계좌), 현금 5, SOXX 급락+현금 5,000(EV2와 겹침), SOXX 급락+선 위 계좌, sell, research_block, PWR, g2b)와 decide 7개(`test_auto_core_decide.Env`: 기본, 좋은 소식, apply 모드, 현금 5,000, 이전 기록 `account.ev4_open` 참, 첫 기록 F1 전·이후 기록 없음, 같은 경우에 오늘 총액 없음)다. 세 판은 다음과 같다.
  - new: worktree
  - base_off: base에서 `rules.ev4_open`을 늘 False로 두고, `evaluate_session`에 `ev4_sessions=[]`·`ev4_backfill=None`을 강제
  - base_on: base 그대로

  임시 폴더 경로는 고정 이름으로 맞췄다. **new = base_off − {`account.ev4_open`, `ev4_backfill`}이 16/16 입력에서 키 순서까지 같다.** 차이가 난 값은 `d_apply`의 `journal.decision_sha256` 하나뿐이다. 이 값은 기록 전체의 해시(decide 새 파일 754~767행 `decision_identity_hash`)다. base_off 기록에서 두 키를 빼고 같은 함수로 다시 내면 7/7 decide 입력에서 새 값과 같다. 새 결과에 `ev4_backfill` 키·`account.ev4_open`·`EV4_UNDETERMINED` 문자열이 없음도 16/16에서 확인했다.
- **E3 계산기**: 같은 320개 입력을 계산기 입력으로 바꿔 비교했다. 변환은 `test_auto_core_rg1_oracle_parity.oracle_inputs` 방식(코어의 지표 배열)이다. 새 계산기 `rrec1(...)` = base 계산기 `rrec1(..., None, None, ())`가 **320/320 JSON 글자까지 같다.** 두 판은 importlib로 각각 불렀다(계산기는 auto_core*를 import하지 않음). 실데이터 비교는 4절 1.
- **E4 결정 파일**: 위 E2 16개 입력, 새 테스트 X1·X4·X6에서 `ev4_backfill`·`account.ev4_open`·`EV4_UNDETERMINED` 없음. `account`의 다른 키(`total`·`first`·`s7_hwm_usd`·V6 상태)는 E2에서 base_off와 같다. 옛 결정 파일(메인 체크아웃 2026-10-13~10-17, 그중 4개는 `ev4_backfill` 있음)은 새 스키마로 5/5 오류 0.
- **E5 완화의 범위**: base(EV4 켬)와 새 코드를 비교했다. 차이는 모두 base에 EV4 사건(또는 EV4 재기준) 또는 `EV4_UNDETERMINED`가 있던 입력에서만 났다.

| 수준 | EV4 없던 입력 | EV4 있던 입력 |
|---|---|---|
| decide 16개(E2 입력) | 9개: 두 키 밖 차이 0 (d_apply는 decision_sha256 1개 — 두 키 때문, 위 확인) | 7개만 차이: s_cash5000(사건 [EV4]뿐 → 닫힘, MU 요건⑤ no→ok, MU 주문표 0→1 — 비교 모드), s_cash5(닫힘, 막힘 사유 `REQ5_RREC1:no` 빠짐, G2 하드 상한은 그대로), s_crash_low·s_sell(kinds에서 EV4만 빠짐, 6개 경로), d_low_cash(사건 [EV4]뿐 → 닫힘), d_old_record_ev4_open(10-07·10-08 [EV4] → 닫힘, 알림 `2:RREC`·`EV4_UNDETERMINED` 빠짐), d_records_missing_no_total(10-06~10-08 [EV4] → 닫힘). d_records_missing_neighbor는 EV4 사건 없이 `EV4_UNDETERMINED` 알림 1개만 빠짐(E4) |
| 코어 rrec1 320개 | EV4 세션을 창 밖에만 줌: 320/320 같음 | EV4 세션 1~3개를 창 안에 줌: 320/320 다름, 모두 base에 EV4 사건. base→new status: no→no 149 · unk→unk 129 · unk→ok 17 · ok→ok 12 · no→ok 9 · unk→no 4, 열림→닫힘 49. base보다 엄격해진 경우(ok→no/unk) 0 |
| 계산기 rrec1 320개 | 총액 30,000(두 선 위)·hwm 30,000·`ev4_hist` 창 밖: 320/320 같음 | 총액 20,000 또는 없음 + `ev4_hist` 창 안 1~3일: 198/320 다름(나머지 122는 결과 동일), base→new no→no 113 · unk→unk 41 · no→ok 20 · unk→ok 10 · no→unk 7 · unk→no 4 · ok→ok 3 |

## 3. 테스트

| 스위트 (Windows worktree) | 기준선(변경 전) | 변경 뒤 |
|---|---|---|
| `-p "test_auto_core*"` | Ran 453 · 실패 1(`RegistryTests` PLTR — HEAD 등록부에도 있음) · 건너뜀 1 | **Ran 443** · 실패 1(같은 PLTR) · 건너뜀 1 |
| `-p "test_score_*.py"` | Ran 66 OK | Ran 66 OK |
| `-p "test_decision_journal_cards.py"` | Ran 36 OK | Ran 36 OK |
| 계산기 `selftest --repo <메인 체크아웃>` | PASS(앵커 5 true) | PASS(기존 골든·앵커 그대로 + 새 경우) |
| `validate_schema_contracts.py` | PASS | PASS |
| 전체 `-p "test_*.py"`(test-runner, Haiku) | HEAD 전체 사본(.git·추적 안 된 데이터 없음): Ran 3153 · 실패 28 · 오류 249 · 건너뜀 5 | worktree: Ran 3213 · 실패 21 · 오류 9 · 건너뜀 3. **실패·오류 28건(고유 ID) 모두 기준선 실행에서도 같은 테스트가 실패.** 변경 파일을 참조하는 것은 PLTR 1건뿐(기준선과 같음). 나머지는 workspace/outputs 데이터 없음(FileNotFoundError)·Kiwoom 수락 매니페스트 등 기존 실패 |

- Ran 수: 453 − 삭제 16 + 새 6 = 443 (정확히 맞음). 전체 스위트 Ran 수는 기준선 사본에 .git·데이터가 없어 setUpClass 단계 오류로 빠진 테스트가 있어 직접 비교하지 않았다. Ran 수 근거는 대상 스위트로 한다.
- Cowork 기준선(Linux VM)과의 차이: 근거 8의 실패 2 중 `test_tickets_without_risk_1r_hash_as_before`는 Windows에서 통과(지시문 예상대로). PLTR은 worktree(HEAD)에도 있었다.
- **삭제한 테스트 16개**
  - test_auto_core_t1_safety.py `Ev4BackfillTests` 10개: test_s1_record_before_f1_with_snapshot_below_the_line_is_rebuilt_and_opens_rrec1 · test_s1_record_without_evaluation_session_counts_from_its_run_day · test_s2_rebuilt_above_the_line_changes_nothing_else · test_s3_no_record_no_snapshot_neighbor_within_three_percent_opens · test_s4_no_record_no_snapshot_neighbors_far_stays_closed_with_a_push · test_s4_snapshot_without_the_holding_bars_is_not_rebuilt · test_s5_sessions_before_the_first_record_are_not_targets · test_s5_existing_fixture_without_records_is_unchanged · test_s6_every_record_reached_f1_gives_the_same_decision · test_record_before_f1_is_absent_key_and_schema_valid
  - 같은 파일 `Ev4ResolveTests` 4개(승인 ①): test_record_hwm_is_used_before_todays · test_no_known_total_is_open · test_no_plan_is_nothing · test_margin_constant_names_its_source
  - test_auto_core_tickets.py `SessionEv4Tests` 1개: test_no_previous_record_and_total_below_the_first_line_blocks_buys (X1로 대체)
  - test_auto_core_rules.py `RecoveryCoverageTests.test_ev4_lines` 1개
- **새 테스트 6개** (test_auto_core_rrec_ev4_remove.py)
  - `AccountLineTests.test_x1_account_below_the_line_without_another_event_is_ok`: `Scenario(cash="5000")`, 총액 ≤ 25,626.55. base에서는 사건이 [EV4](2026-10-09) 하나뿐이었다(총액 $6,027, E5 표). 새 코드는 shock ok/False/사건 없음, MU 요건⑤ = "통과 (열린 이벤트 없음)", `REQ5_RREC1` 막힘 없음, `account`에 `ev4_open` 없음, 반환에 `ev4_backfill` 없음.
  - `test_x2_benchmark_event_with_the_account_below_the_line_is_the_event_alone`: SOXX 마지막 날 급락(EV1·EV2) + 현금 5,000 vs 같은 SOXX + 현금 30,000. `shock`·`shocks` 전체가 같고, event 날짜는 마지막 세션, "EV2" 있음, "EV4" 없음. base에서는 낮은 계좌의 kinds가 [EV1, EV2, EV4]였다.
  - `test_x3_the_s7_l2_pause_still_blocks_requirement_2`: S7 검토에 L2 열린 사건(`review_lines.open_events` L2, `pauses.*` paused + `REVIEW_LINE_OPEN:L2` — portfolio_exposure 1378~1388행과 같은 모양)을 넣었다. R-REC1 ok여도 MU 요건② s=no, "막힘 … S7 신규 매수 멈춤", `exposure.S7.pauses.new_buy` 참, MU 매수 주문표 없음. 멈춤이 없으면 같은 입력의 요건②에 그 문구가 없다.
  - `DecideRecordTests.test_x4_an_old_record_with_ev4_open_makes_no_event`: 이전 기록(S2)의 `account.ev4_open` 참·총액 20,000. 새 코드의 `shock`은 이전 기록 없는 실행과 같고, 열림 False, EV4·`EV4_UNDETERMINED` 없음, 스키마 통과. base에서는 10-07·10-08 [EV4]가 열리고 `EV4_UNDETERMINED`가 붙었다.
  - `test_x6_sessions_without_a_record_raise_no_ev4_exception`: 첫 기록 S1이 F1 전 FAIL(계좌 없음), S2·S3 기록 없음. 두 경우(오늘 총액 있음 = 옛 NEIGHBOR_CLEAR, 오늘 현금 없음 = 옛 NEIGHBOR_NONE) 모두 `EV4_UNDETERMINED` 알림·EV4 사건 없음, `shock`은 기본 실행과 같음. base에서는 두 경우 모두 `EV4_UNDETERMINED:2026-10-06,2026-10-07,2026-10-08`이 났고, 두 번째는 EV4 사건 3개도 생겼다.
  - `CoreEquivalenceTests.test_x5_rrec1_equals_the_base_called_without_ev4_sessions`: E1(2절).
- **허용 변경 1~4 (기존 테스트, base 줄 번호)**: 줄 단위 분류 스크립트로 모든 diff 덩어리를 분류했다. 그 밖의 변경 줄은 없다.
  - 1 키워드 `, ev4_sessions=[]`만 삭제(15줄, 새 줄 = 옛 줄에서 그 문자열만 뺀 것): test_auto_core_compare_fix3.py 73·79 · test_auto_core_rg1_damage.py 73·181·444 · test_auto_core_rg1_oracle_parity.py 58 · test_auto_core_rrec_bootstrap.py 31 · test_auto_core_rules.py 400·403·410·415·418·441 · test_auto_core_t2rc_corefix.py 45 · test_auto_core_tickets.py 398.
  - 2 EV4 기능 테스트 삭제: test_auto_core_t1_safety.py 57~236 `Ev4BackfillTests` · test_auto_core_tickets.py 668~685 `SessionEv4Tests`, 337~339 `Scenario` docstring의 EV4 문장 · test_auto_core_rules.py 445~454 `test_ev4_lines`.
  - 3 test_auto_core_equity_cash.py: 61(`total_view`의 `"ev4"` 키) · 75~77(기대 dict `"ev4"` + `rules.ev4_open` 단언) · 80 · 128 · 169(`view["ev4"]`) · 303~304(`rules.ev4_open` 단언). total·n·v6·status 단언은 그대로.
  - 4 test_auto_core_decide.py 68~69 `Env` docstring의 EV4 문장 · test_auto_core_risk1r.py GOLDEN(아래, 승인 ③).
- **승인 ①~③** (7절): ① test_auto_core_t1_safety.py 238~266 `Ev4ResolveTests` 삭제 ② test_auto_core_rg1_oracle_parity.py 63행 계산기 호출의 `None, None, ()`만 삭제 ③ risk1r GOLDEN `cash5` 값 교체 + 근거 주석 2줄.
- **GOLDEN 재계산 근거** (base 사본과 worktree에서 같은 `_scenarios()`·`_decide()`를 따로 실행해 비교)
  - GOLDEN의 해시 대상은 시나리오별 `tickets`(risk_1r 뺌)·`blocked`·`no_action`·`candidates`이고, decide는 `tickets`·`blocked`·`no_action`·`keys`다. `account`·`ev4_backfill`은 해시 대상이 아니다. 그래서 "base 결과에서 E4 두 키를 뺀 dict의 해시"는 base 해시와 같다.
  - `decide_compare` 612f246d…·`decide_apply` 91c252b8…는 base와 새 코드에서 **같은 값이라 바꾸지 않았다**. 지시문은 이 둘을 바꾸라고 했는데, 실제로는 바뀌지 않는다.
  - `default`·`g2b`·`research_block`·`sell`·`pwr`도 같다. sell은 마지막 날 EV1·EV2가 함께 있어 kinds에서 EV4만 빠지고 해시 대상은 그대로다.
  - **`cash5`만 c3ad82a2d647…(= 옛 GOLDEN) → c6f6158903b7727497439df2f6f6fba8c9ad15d9395f7f0eeda0a81f799db7c5**로 바뀐다. 키 경로 차이는 다음과 같다.
    - 해시 대상: `blocked[0].reasons`에서 "REQ5_RREC1:no"가 빠짐(남은 사유: …, "G2:EXPOSURE_HARD_CEILING"), `no_action.reasons`도 같음.
    - 해시 밖: `shock.events` [{2026-10-09, [EV4]}] → [], `shock.open` True → False, `status` no → ok, `rg`·`rg1_coverage` 비움, `by_symbol` MU·SOXL 열림 → 닫힘, MU 요건⑤ "막힘 미충족 RG1,RG3" → "통과 (열린 이벤트 없음)", `account.ev4_open` 사라짐.
    - 이 시나리오(SOXL 10, 현금 $5, 총액 $1,032)의 R-REC1 사건이 평가 세션의 EV4 하나뿐이었으므로, 차이는 모두 EV4 제거로 설명된다.

## 4. 실데이터 확인 (읽기 전용, 출력은 저장소 밖 임시 폴더)

1. **계산기 base 판(메인 체크아웃, 9f0e2238…) vs worktree 판(6a74f813…)**: `check --day 2026-10-15/16/17 --repo <메인 체크아웃> --out <임시> --ignore-input-sha`
   - 세 날짜 모두 두 출력의 차이는 `oracle_sha256`·`ev4_history` 두 키뿐이다(키 경로 비교, diff 2개씩).
   - 판정은 모두 INFO_MATCH, 종료 코드 0.
   - base의 `ev4_history`: 10-15 [] · 10-16 ['2026-10-14'] · 10-17 ['2026-10-14', '2026-10-15'].
2. **코어 rrec1 재계산(평가 세션 2026-10-16)**: 메인 체크아웃의 봉·달력·연구 기록·등록부·R-REC1 문서로 계산했다. 결정 시각은 10-17 decision.json의 `generated_at`, 8종목은 그 기록의 `by_symbol`이다. 방식은 decide 새 파일 966~988행(evaluate_session의 R-REC1 부분)과 같고 auto_core는 import하지 않았다(거래소는 같은 history 파일에서 읽음).
   - 복제가 맞는지 확인: base 코드 + `ev4_sessions` [10-14, 10-15, 10-16]으로 돌린 결과가 10-17 decision.json의 `shock`과 **완전히 같다**.
   - 새 코드: 사건 날짜 13개(07-24…10-16) 같고, 각 사건의 kinds에서 "EV4"만 빠짐(10-14·15·16 [EV2, EV4] → [EV2]). event = 2026-10-16 [EV2](c0 493.14, l0 492.88). rg RG1 no · RG2 no · RG3 no · RG4 ok, status no, open True. 8종목 by_symbol을 포함한 나머지 키 전부 같음.
3. **가정 실험**: 같은 SOXX 봉에서 60세션 창의 종가를 사건 없는 사본으로 바꿨다. 이전 60세션 고점 위에서 하루 +0.15% 상승 ± 0.2% 지그재그이고, 10-16 종가 718.08은 EMA50 683.32·3σ 선 663.59 위다. EV3a 날짜·훼손 사실은 없음. 계좌 총액 $23,695.43, HWM $31,711.76.
   - base: `ev4_open` = True → 사건 [2026-10-16 EV4], 열림, status no (RG1 no·RG2 ok·RG3 no·RG4 ok)
   - 새 코드: 사건 없음, status ok, 열림 False

## 5. 남은 주석·코드 (고치지 않은 EV4 언급 — 지시문 범위 밖이라 그대로)

- manage-us-stock-strategy/scripts/auto_core_tickets.py:157 — "The total also feeds V6 and EV4."(지시문대로 그대로)
- manage-us-stock-strategy/scripts/portfolio_exposure.py:741 — "the core records the day's EV4 from this value."(지시문대로 그대로)
- docs/claude/t2rc-oracle.py:1739 `equity_cash_t2` docstring "total assets behind V6 / EV4", 1773 주석 "V6 / EV4 total assets"(계산기 diff 범위 밖이라 그대로. 값은 `total_assets_v6` 표시용으로 계속 쓰임)
- manage-us-stock-strategy/schemas/auto-core-decision.schema.json:149~162 — `ev4_backfill` 속성 구조(옛 파일 통과용, description만 legacy)
- 테스트 docstring·주석: test_auto_core_equity_cash.py:2·55·76·278 · test_auto_core_rules.py:433(`RecoveryCoverageTests` docstring) · test_auto_core_t1_safety.py:3~5(모듈 docstring의 Fix 1)
- 더 쓰이지 않게 된 테스트 코드(허용 범주 밖이라 지우지 않음, 동작 영향 없음)
  - test_auto_core_t1_safety.py: helper `run_day_of`·`without_backfill`(47행 docstring이 지운 `ev4_backfill_plan`을 가리킴)·`comparable`(53행 `ev4_backfill` pop), 상수 `S1, S2, S3`, import `Decimal`·`mock`·`rules`·`copy`·`validate_instance`
  - test_auto_core_equity_cash.py: `total_view`의 `hwm` 인자, `ACCOUNT_TOTAL_FIELDS`(184행)의 `"ev4_open"`(`pop(key, None)`이라 무해)
- manage-us-stock-strategy/scripts/auto_core_decide.py 683행(base) `multipliers = …`: EV4 소급 절을 지운 뒤 `_run`에서 더 쓰이지 않는다. T2 원본(319b48f)부터 있던 줄이고, 정책 키가 없을 때 같은 자리에서 멈추는 동작을 바꾸지 않으려고 남겼다.
- 범위 밖 문서(Builder가 고치지 않음, 병합 때 Cowork 몫): 통합 점검 규칙 파일 `scheduled-prompts/pending-ev-rg1/integrated-check-prompt-v3.12.7-2026-10-18.txt` 102행, recovery-gate-R-REC1-2026-10-09.md 1절, CLAUDE.md R-REC1 줄 "account line L1,", gate-rule-epochs.json, t2-rc 사전 등록 변경 기록.

## 6. 바뀐 파일 sha256 (작업 트리 바이트, 모두 CRLF·LF 단독 줄 0)

| 파일 | sha256 (작업 트리 바이트) | LF 정규화 앞 16자리 |
|---|---|---|
| docs/claude/t2rc-check-run.ps1 | beaf8446802621e1a9cd29c2a6c025eef62a5c9bc6c8ceb3c247e8d2906a15a7 | 593a067a848f5d6b |
| docs/claude/t2rc-oracle.py | d79b12212ee2c043e8c1ad8be739e84498506126b8ed42c60cc23f2a5ff42631 | 6a74f813c918046b |
| manage-us-stock-strategy/references/auto-core-decision.md | 61b0af682c1c43e6b750cf6312d8e6ff6a6a1d3f436dbf3d9afa53834c5c6010 | f656b63c3d446317 |
| manage-us-stock-strategy/schemas/auto-core-decision.schema.json | 3b540d749011d8ff953d8a81f621ecbbbedc66935252755da960c3782ee94514 | 9c594f3b55e7bd60 |
| manage-us-stock-strategy/scripts/auto_core_decide.py | 97b78ac5edfc1850267a8b1c70a3919c9dc2a0f93d8ed8534c54bd935e0d57ec | 39eb1cb686b91cde |
| manage-us-stock-strategy/scripts/auto_core_replay.py | d346ba92f7839860b63295ff1e12ae26d7fefeb8e431a03959e4482d5b06dbd0 | 088a0f30ba206007 |
| manage-us-stock-strategy/scripts/auto_core_rules.py | 187a46f628c621da908fe696eeb1c8a130ae01946b9533add393a9283d90ab56 | 9ba4b9ae4480ce45 |
| tests/test_auto_core_compare_fix3.py | e42fff9044295aca7e4c2d1b8518f99e2859d1c0ea10f351adfea9eb244faae9 | a54becf51183fb1e |
| tests/test_auto_core_decide.py | 6c6e8611f07a2e583f9da652d98c8b7e452d8c4bab5af05a297f6f21778fb644 | 30063967af89c286 |
| tests/test_auto_core_equity_cash.py | 526d927485e8f02dc0040c2663f0915b8752845814695bee278369a8fc3b02b4 | 64a4e5864cca5ea0 |
| tests/test_auto_core_rg1_damage.py | a1b5ad03926894ae94e3be0a839b928379ada3c1b6135dfb004e334b17cf082e | db247f6ff4bc8055 |
| tests/test_auto_core_rg1_oracle_parity.py | f0e93633139176dfc71ff4ea06178d64ab12f7849135835ed6523169ef1e6be0 | 7c129478d4c5c839 |
| tests/test_auto_core_risk1r.py | 2a95458c3563af25c077baa966f9ee8be918f78a9f18bfde407d6221672831f6 | 4d07b6b2f65d4844 |
| tests/test_auto_core_rrec_bootstrap.py | 7a1832d2ca1a40de851071aa897dbbcbff391f26f3552338aaa84aa8d0cdcd9e | 56d2a61ef0056e20 |
| tests/test_auto_core_rrec_ev4_remove.py (새) | 6c8db4bc21fbaa51127d992ae82391773c5fba43fd955b6ff0f6775b06003f74 | 631b284d7d2f936a |
| tests/test_auto_core_rules.py | 0b457f6c5b7864c7aaa9605713f7b985785dff0d2f9523aed104ef9de266f0b8 | 10753a057905f562 |
| tests/test_auto_core_t1_safety.py | b6d00d34907df4237bab30935d074b43bd695d352e05b7a4428838e6a80f4a3d | e242ea79c075d83f |
| tests/test_auto_core_t2rc_corefix.py | a6402a15148f4f4facd9746445d4bfcd91c651fb588ab880633c1e2a800dd613 | a83b7001281319b5 |
| tests/test_auto_core_tickets.py | b687a826c725c28c78c2fb967d31fe82e885601e5a3c963664cab838d69eac42 | 5e100d8656205cbd |

(tests/ = manage-us-stock-strategy/tests/)

- 새 계산기 sha256_lf(계산기 108~111행 `sha256_lf` 방식) = **6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64**
- 실행기 16행 `$ExpectedOracleSha256` = 같은 값. 실행기 61~63행과 같은 PowerShell 식(UTF-8 읽기 → CRLF→LF → SHA256)으로 다시 재도 같은 값이고, 계산기 `check` 출력의 `oracle_sha256`과도 같다.
- 비ASCII 바이트 수는 모든 기존 파일이 base와 같다(스키마 0, 스크립트 3개 0). 새 테스트 파일은 0.

## 7. 멈춤·범위 문제

1. **허용 범위 밖 3건 — 멈추고 사용자에게 물은 뒤 반영.** 셋 다 지시문이 지우라고 한 함수·상수·인자의 직접 결과이고, 고치지 않으면 테스트가 깨진다.
   - 질문(이 세션, AskUserQuestion): ① `Ev4ResolveTests` 삭제(지운 `ev4_backfill_resolve`·`RREC_EV4_NEIGHBOR_MARGIN`을 시험) ② parity 63행 계산기 호출의 EV4용 위치 인자 `None, None, ()` 삭제(지운 계산기 인자) ③ risk1r GOLDEN은 지시문이 지목한 `decide_compare`·`decide_apply`가 아니라 `cash5` 하나만 바뀜.
   - 사용자 선택(원문): **"3건 모두 진행 (권장)"** (2026-10-19, 이 Claude Code 세션)
   - 반영 근거는 3절(줄·해시)과 2절 E5(cash5 차이 = EV4뿐).
2. **지시문 해석으로 처리한 것(범위 안으로 판단 — Judge 확인 요청)**
   - 계산기 1936행 `s7hwm` 계산 삭제: 지운 인자에만 쓰이던 값. "호출 인자" 범주로 봤다.
   - 계산기 2261행 selftest 도우미 `_rg1_run`의 호출 인자 삭제: 1937행 말고 rrec1을 부르는 유일한 곳이라, 시그니처 변경에 따라 인자만 뺐다.
   - decide `evaluate_session` docstring의 "rule-file N, V6 and EV4" → "rule-file N and V6": 지시문 B3(해당 문장 삭제)·B4(주석 정리)의 범위로 봤다.
3. **지시문 근거와 실제가 다른 점**
   - 근거 8: Windows 기준선 실패는 1(PLTR)이다. risk1r는 지시문 예상대로 Windows에서 통과.
   - 근거 9·허용 4: GOLDEN `decide_compare`·`decide_apply`는 바뀌지 않는다. 해시 대상에 `account`·`ev4_backfill`이 없기 때문이다.
   - 근거 9: `Ev4ResolveTests`와 parity 63행이 목록에 없었다(→ 1번 질문).
   - 근거 6: 계산기 rrec1 호출처가 2261행 하나 더 있었다.
4. **도구 주의**: Claude Code의 Write/Edit 도구가 입력의 "백슬래시-u 네 자리" 이스케이프를 실제 문자로 바꿔 저장했다. 스키마 150행("—")과 새 테스트 41~43행(한글 상수)에서 발견해, 파일 안 이스케이프 표기로 되돌렸다. 값은 같고 파일은 ASCII다(6절).
5. **실행 흔적**: 전체 스위트(test-runner)가 worktree에서 `manage-us-stock-strategy/scripts/__pycache__` pyc 2개를 만들어(19:08) 지웠다. `workspace/outputs/v2_5_shadow`는 폴더 수정 시각만 바뀌고 남은 파일은 없다(git status 깨끗). 메인 체크아웃에는 쓴 파일이 없다. 그곳의 pyc는 모두 이 세션 전(17:19~17:21, cpython-310)에 생긴 것이다. worktree의 무시된 파일 `stock-strategy-system/portfolio_state.json`(10-17)·`alert_runtime_state.json`(08-12)·`.claude/settings.local.json`(10-05)은 worktree를 만들 때부터 있던 것이고 손대지 않았다.
6. **다른 독자(L3)와 남은 위험 — 병합 때 확인할 것**
   - auto_core_compare.py 270~275행: 통합 점검(규칙 파일 102행)의 `shock.open`과 코어의 `shock.open`이 다르면 `RREC:open` = B7(UNEXPLAINED)이다(timing이면 B6). 규칙 파일이 EV4를 계속 세는 동안, EV4만 켜지는 날에는 B7이 생긴다. 277~292행 RG 비교도 같다. 그래서 규칙 파일 v3.12.8 교체를 병합과 같은 세션에 해야 한다(지시문 근거 7). 10-14~10-16은 같은 날 EV2가 켜져 열림이 같았다(4절 2).
   - score_decision_journal.py는 `ev4_*` 키를 읽지 않는다(grep). 다만 `shock.open`·`event`·`by_symbol`을 읽어 충격 구간을 만들므로(1328~1415행), 병합 뒤 EV4만으로 열리던 날은 구간에서 빠진다(의도된 효과).
   - S7 대체 장치: 정책 `portfolio_review_lines.lines` L1 0.9(멈춤 없음)·L2 0.8(신규·추가 멈춤)·`further_lines_action` same_as_L2(alert_policy.json). 요건② 문구(auto_core_tickets 240~241행)는 X3으로 확인했다. 일지 검토 뒤 풀림과 L3 재멈춤은 이 Builder가 따로 시험하지 않았다(코드 변경 없음, Judge 7항).
   - 비교 모드 효과 예: 현금 5,000 합성 계좌(EV4만 켜지던 입력)에서 MU 비교용 주문표가 0 → 1장(E5 표). "켜" 전이라 주문 입력 없음.
7. 그 밖의 멈춤 없음. 커밋·병합·예약 작업·관제판·사전 등록·규칙 파일 변경 없음.
