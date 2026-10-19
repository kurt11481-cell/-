---
id: rrec-ev4-remove-builder-prompt
title: R-REC1 EV4(계좌 총액 사건) 제거 — 코어·리플레이·독립 계산기 동반 수정
date: 2026-10-19
class: 권한·한도 변경(K3 — 매수 관문 R-REC1 사건 정의. auto_core*.py·tests/test_auto_core*.py·auto-core-*.schema.json = tools/dev_pipeline/authority-paths.txt 12·25·65행. 독립 계산기 고정값 = t2-rc-preregistration-2026-10-14.md 24·49~50행). 수동 경로: 이 Builder(worktree) → 별도 Judge 세션(docs/claude/rrec-ev4-remove-judge-prompt.md) → 사용자 승인 1줄 + 병합 스크립트 1번(Judge PASS 뒤 Cowork 작성)
decision: 사용자 "결정 rrec-ev4: REMOVE"(2026-10-19 17:45 KST) — docs/claude/rrec-ev4-remove-decision-2026-10-19.md
base: main HEAD 80d3a1da0957a872fc16b97ac204ee4d761198ca — sha256(메인 작업 트리 바이트, CRLF) / LF 정규화: auto_core_rules.py 48433ab8…fbab4e / 62419561…61a11c · auto_core_decide.py 1013da08…7448f1 / 8ec0fa63…ff6261 · auto_core_replay.py 8a872b88…78fd2 / 6dbaf971…98ede6 · auto-core-decision.schema.json e542a570…3e6ce / fe3ef94b…c789d · references/auto-core-decision.md c47bbc87…886a8 / 719880d4…2bd44 · docs/claude/t2rc-oracle.py e41a7903…bb67 / 9f0e2238f2a8238016be5406cd2e195aaf24c232adeda5f1fba3a52cd09b1aae(= 실행기 고정값) · docs/claude/t2rc-check-run.ps1 3735492e…ff167 / fcd8977bac37034e7805dda7dd31756b8b6a224c6cdec673d45189c0cd1680a7
model: Opus · xhigh · 새 worktree (claude --worktree rrec-ev4-remove)
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 바뀌는 것은 R-REC1 사건 목록에서 EV4를 빼는 것 하나(결정된 완화) · EV1·EV2·EV3·EV5·C0·L0·DS1·RG1~RG4·RG1 훼손 규칙·EV3B 기록 공백·닫힘·S7·노출 한도·요건 ①~④ 불변 · 정책·상태·장부·일지·예약 작업 불변 · 키움 호출 없음
weekly_user_touch: 0 (일회성: Builder 시작 1·Judge 시작 1·승인 1줄·병합 1번)
deadline: "켜" 전. C1은 ev-rg1-hyper 병합(10-18)으로 이미 0부터 다시 세는 중이라 빨리 병합할수록 버려지는 C1 세션이 적다
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree(claude --worktree rrec-ev4-remove) · 이유: 매수 관문 R-REC1 사건 정의 변경 + 독립 계산기 동반 수정(K3)

# 목표

R-REC1의 EV4(계좌 총액 ≤ V6 1차 선 또는 ≤ S7 HWM × 0.9)를 **코어·리플레이·독립 계산기에서 함께 없앤다.** 계좌 하락 위험은 S7 점검선(L2 이하 멈춤 + 일지 검토 해제)이 맡는다 — S7 코드는 바꾸지 않는다.

**동치 명세(이 절이 기준이다)**
- E1 코어: 모든 입력 x에 대해 `new rules.rrec1(x)` = `base rules.rrec1(x, ev4_sessions=[])` (결과 dict 글자까지 같음).
- E2 decide: 모든 입력에 대해 `new evaluate_session(...)`의 결과 = base에서 EV4가 한 번도 켜지지 않은 결과(base `rules.ev4_open`이 늘 False, `ev4_backfill` 계획 없음, `ev4_sessions=[]`)에서 `account["ev4_open"]`와 반환 키 `ev4_backfill`을 뺀 것.
- E3 계산기: 모든 입력에 대해 `new oracle rrec1(...)` = `base oracle rrec1(..., equity_today=None, s7_hwm=None, ev4_hist=())`. 계산기 출력에서는 `ev4_history` 키만 사라진다.
- E4 결정 파일: 최상위 `ev4_backfill`을 더 쓰지 않고, `account`에서 `ev4_open`을 뺀다. `account`의 다른 키(`total`·`first`·`s7_hwm_usd`·V6 상태 등)는 그대로. 예외 `EV4_UNDETERMINED`는 더 생기지 않는다.
- E5 완화의 범위: base 대비 느슨해지는 경우는 "EV4 사건(또는 그 재기준)이 있던 입력"뿐이다. EV4가 없던 입력에서는 결과가 글자까지 같다.

# 근거 (Cowork 2026-10-19 읽기 전용 확인 — Builder는 원문을 다시 연다)

1. **코어 rrec1**(auto_core_rules.py): 시그니처 800~803행(`ev4_sessions: list[str]` 필수 키워드), docstring 820~821행, 사건 루프 894~895행(`if day in ev4_sessions: kinds.append("EV4")`), `event = events[-1]`. `ev4_open` 724~731행, 상수 `RREC_EV4_HWM_FRACTION` 58행·`RREC_EV4_NEIGHBOR_MARGIN` 59~61행. V6 상수(47~48행 부근)와 V6 계좌 상태 함수(716~722행)는 **표시용으로 남는다.**
2. **decide**(auto_core_decide.py): 주석 142·167·643행에 EV4 언급. EV4 소급 계산 절 176~283행(`EV4_REBUILT` 등 상수 4개, `_first_decide_session`, `_rebuilt_total`, `ev4_backfill_plan`, `ev4_backfill_resolve`). 조립 746~749행(`ev4_sessions`, `backfill_plan`), 호출 772·778행 키워드, 779~783행(`decision["ev4_backfill"]`, 예외 `EV4_UNDETERMINED`), `evaluate_session` 시그니처 1002·1006행과 docstring 1014~1018행, 1084~1090행(`account["ev4_open"]`, backfill 해석, `ev4_all`), rrec1 호출 1099·1104행, 반환 1165행 `"ev4_backfill": backfill`. `snapshot_holdings`(166행)는 F1도 쓰므로 남긴다(주석만 고침).
3. **리플레이**(auto_core_replay.py): 215행 `ev4_sessions` 목록, 254행 키워드, 262~263행 누적.
4. **결정 스키마**(auto-core-decision.schema.json 149~165행): `ev4_backfill` 속성(선택 키). 옛 결정 파일이 남아 있으므로 속성은 지우지 않고 description만 "legacy — written before rrec-ev4-remove; not written after"로 고친다.
5. **참조 문서**(references/auto-core-decision.md 83~86행): R-REC1 사건 목록과 "evaluation session's own EV4" 문장.
6. **독립 계산기**(docs/claude/t2rc-oracle.py, auto_core*를 import하지 않음): 66행 `V6_FIRST, V6_APPROACH = 25626.55, 26395.34   # rule file V6 / R-REC1 EV4`(2026-10-19 grep: 1109행 EV4 말고 쓰는 곳 없음), `rrec1` 1041~1042행 시그니처(`equity_today, s7_hwm, ev4_hist=()`), docstring 1047~1050행, 1109~1111행 EV4(이 계산기에서 `V6_FIRST`를 쓰는 곳은 1109행뿐 — `V6_APPROACH`는 정의만 있음), 1587~1601행 `ev4_hist` 적재·`res["ev4_history"]`, 1937~1938행 호출. 실행기 docs/claude/t2rc-check-run.ps1 16행 `$ExpectedOracleSha256` = 계산기 LF 정규화 sha(지금 9f0e2238…). 사전 등록 24행: 계산기 수정 → 새 sha·Judge 확인 → C1 0부터.
7. **소비처**: `ev4_open`·`ev4_backfill`·`EV4_UNDETERMINED`·`ev4_hist`를 읽는 실행 코드는 위 파일과 테스트뿐(`git grep`, 2026-10-19). 예약 지시문 중 EV4를 적은 것은 통합 점검 규칙 파일 `scheduled-prompts/pending-ev-rg1/integrated-check-prompt-v3.12.7-2026-10-18.txt` 102행뿐 — **Builder 범위 밖**(병합 때 Cowork가 v3.12.8로 교체). auto_core_compare.py 270~292행은 통합 점검의 `shock.open`·RG를 코어와 대조한다(차이 = B7) — 그래서 규칙 파일 교체는 병합과 같은 세션에 한다.
8. **테스트 기준선**(Cowork, 장치 VM Linux Python 3.10, 메인 작업 트리): `test_auto_core*.py` Ran 453, 실패 2 = test_auto_core_decide `RegistryTests`(symbol PLTR — 메인 작업 트리의 커밋 안 된 등록부 변경, worktree(HEAD)에는 없을 수 있음) + test_auto_core_risk1r `test_tickets_without_risk_1r_hash_as_before`(decide_compare·decide_apply 해시가 OS마다 다름 — Windows에서는 통과). 계산기 `selftest` PASS. 계산기 `check --day 2026-10-17 --repo . --ignore-input-sha` → verdict INFO_MATCH, `ev4_history` ['2026-10-14', '2026-10-15']. **Windows worktree에서 다시 잰다.**
9. **EV4가 쓰인 기존 테스트**(`grep -n -i ev4`): test_auto_core_t1_safety.py(`Ev4BackfillTests` 57행~, 그 파일의 F6 수정 테스트는 남김) · test_auto_core_tickets.py(`SessionEv4Tests` 668~684행, 338·398행) · test_auto_core_rules.py(`test_ev4_lines` 445~453행, 400~441행 `ev4_sessions=[]`) · test_auto_core_equity_cash.py(55~128행 기대값의 `"ev4"` 키) · test_auto_core_decide.py(69행 docstring) · `ev4_sessions=[]` 키워드만: test_auto_core_compare_fix3.py 73·79, test_auto_core_rg1_damage.py 73·181·444, test_auto_core_rg1_oracle_parity.py 58, test_auto_core_rrec_bootstrap.py 31, test_auto_core_t2rc_corefix.py 45.
10. **줄 끝**: 메인 작업 트리의 대상 파일은 CRLF다(위 base 줄). worktree도 체크아웃된 줄 끝 그대로 둔다(일괄 변환 금지). 계산기 고정값·비교는 LF 정규화 sha로만 한다.

# 바꿀 것

## A. auto_core_rules.py
1. `rrec1`: 키워드 인자 `ev4_sessions`를 없애고 894~895행을 지운다. docstring에서 `ev4_sessions` 설명(820~821행)을 지우고 "Events: EV1, EV2, EV3 (a)(b), EV5. The account-line event EV4 was removed by user decision rrec-ev4 REMOVE (2026-10-19); account drawdown is handled by the S7 review lines."를 넣는다(영문, ASCII).
2. `ev4_open`(724~731행)과 상수 `RREC_EV4_HWM_FRACTION`·`RREC_EV4_NEIGHBOR_MARGIN`을 지운다. 지금 쓰는 곳은 decide(B에서 함께 지움)와 허용된 테스트 변경 2·3뿐이다(2026-10-19 grep) — 그 밖에서 쓰이면 멈추고 보고한다. V6 상수·V6 함수는 그대로.

## B. auto_core_decide.py
1. 176~283행의 EV4 소급 절 전체를 지운다. 지운 뒤 안 쓰이게 된 import(`timedelta` 등)는 다른 곳에서 안 쓸 때만 지운다.
2. 746~749행, 772·778행 키워드, 779~783행을 지운다(결정 파일에 `ev4_backfill`을 쓰지 않음, 예외 `EV4_UNDETERMINED` 없음).
3. `evaluate_session`: 인자 `ev4_sessions`·`ev4_backfill`과 docstring 해당 문장을 지운다. 1084~1090행에서 `account["ev4_open"]`·backfill·`ev4_all`을 지우고 `account["s7_hwm_usd"] = s7.get("hwm_usd")`는 남긴다. rrec1 두 호출(1099·1104행)에서 `ev4_sessions=` 키워드를 지운다. 반환 dict에서 `"ev4_backfill"`을 지운다.
4. 주석 142·167·643행의 EV4 언급을 고친다(예: "the rule-file N and the V6 account line"). 동작 변경 없음.

## C. auto_core_replay.py
1. 215행 `ev4_sessions` 목록, 254행 키워드, 262~263행을 지운다. 다른 동작 불변.

## D. 스키마·참조
1. auto-core-decision.schema.json `ev4_backfill` description을 근거 4대로 legacy로 고친다(속성·구조는 그대로).
2. references/auto-core-decision.md 83~86행: 사건 목록에서 EV4를 빼고 "EV4 (account line) was removed 2026-10-19 (rrec-ev4 REMOVE); the S7 review lines pause buys from L2" 한 문장. 그 밖은 그대로.

## E. docs/claude/t2rc-oracle.py (계산기 — auto_core*를 import하지 않는 원칙 유지)
1. `rrec1`: 인자 `equity_today`·`s7_hwm`·`ev4_hist`를 없애고 1109~1111행을 지운다. docstring의 EV4 문장(1047~1050행)을 "EV4 removed (rrec-ev4 REMOVE 2026-10-19)" 한 문장으로.
2. 1587~1601행 `ev4_hist` 적재와 `res["ev4_history"]`를 지운다. 1937~1938행 호출에서 해당 인자를 지운다. `exposure_check`의 `total_assets_v6` 등 V6 표시는 그대로(다른 곳에서 쓰면 남김, 안 쓰면 보고서에 적고 남김).
3. 66행 `V6_FIRST, V6_APPROACH`는 다른 곳에서 안 쓰이면 지운다(grep 결과를 보고서에). `exposure_check`의 `total_assets_v6` 출력 키는 그대로 둔다(계산기 출력 형식 유지). `selftest`: 기존 골든·앵커 불변 + 새 경우 1개(총액이 두 선 아래여도 다른 사건이 없으면 rrec1 status ok·open False).
4. 맨 위 docstring 출처 목록에 이 결정 1줄. `ORACLE_VERSION`은 그대로.

## F. docs/claude/t2rc-check-run.ps1
1. 16행 `$ExpectedOracleSha256`만 새 계산기의 LF 정규화 sha256으로 바꾼다(계산기 108~111행 `sha256_lf`와 같은 계산). 다른 줄·줄 끝 그대로.

# 바꾸지 않는 것

auto_core_compare.py, auto_core_tickets.py(157행 docstring의 "V6 and EV4"는 지시문 범위를 넓히지 않도록 그대로 두고 보고서 "남은 주석"에 적는다), auto_core_inputs.py, portfolio_exposure.py(741행 주석 그대로 — 보고서에 적음), score_decision_journal.py, rules.CONSTANTS의 다른 값, 정책·상태·장부·일지·workspace/policies·stock-strategy-system, 예약 지시문·규칙 파일(docs/claude/scheduled-prompts/**), 사전 등록 문서, recovery-gate 문서, CLAUDE.md, gate-rule-epochs.json, 관제판.

# 테스트

새 파일 `manage-us-stock-strategy/tests/test_auto_core_rrec_ev4_remove.py`(authority-paths 25행 패턴). 기존 helpers(`helpers.sessions`·`helpers.bars`·`helpers.zigzag`·`rules.build_series`)와 test_auto_core_tickets.py `Scenario` 방식을 따른다.

- X1 계좌만 선 아래: `Scenario(cash="5000")`(옛 `SessionEv4Tests`와 같은 입력). 먼저 base에서 그 입력의 사건이 EV4뿐인지 확인한다(아니면 다른 사건이 없는 입력을 만든다) → 새 코드는 `shock.open` False, status ok, MU 요건 ⑤ "통과 (열린 이벤트 없음)", REQ5_RREC1 막힘 없음. `account`에 `ev4_open` 없음, 반환에 `ev4_backfill` 없음.
- X2 EV2와 겹침: 마지막 세션이 EV2이고 계좌도 선 아래 → event 날짜·rg·status는 EV2 단독 입력과 같고 kinds에 "EV4" 없음.
- X3 S7 멈춤은 그대로: S7 검토에 L2 열린 사건(pauses new_buy paused, REVIEW_LINE_OPEN:L2)이 있는 입력 → R-REC1이 ok여도 요건 ②가 "막힘 … S7 신규 매수 멈춤".
- X4 옛 기록 무시: 이전 decision 기록의 `account.ev4_open`이 참이어도 사건이 생기지 않는다(decide 수준, 임시 폴더 기록).
- X5 E1 동치: 고정 시드 합성 입력 300개 이상(EV1·EV2·EV3a·EV5·DS1·RG2 조합, 훼손 사실 있음/없음, card_accepted_on 있음/없음)에서 새 rrec1 = 테스트 안에 고정한 기대값. 기대값은 base 코드로 만든 결과를 상수(해시 목록)로 고정한다 — 만드는 방법(base 체크아웃에서 `ev4_sessions=[]`로 부른 스크립트)을 보고서에 적는다.
- X6 예외 없음: 이전 기록이 없는 세션들(옛 NEIGHBOR_NONE 경우)에서도 `EV4_UNDETERMINED` 예외·알림 줄이 없다.

기존 테스트 변경은 아래 넷만 허용한다(그 밖이 필요하면 멈추고 보고):
1. `ev4_sessions=[]` 키워드 삭제만(근거 9의 파일들).
2. EV4 기능 테스트 삭제: `Ev4BackfillTests`(test_auto_core_t1_safety.py — 같은 파일의 다른 테스트와 그 파일이 쓰는 helper는 남김), `SessionEv4Tests`(test_auto_core_tickets.py — X1로 대체), `test_ev4_lines`(test_auto_core_rules.py). 338행 docstring의 EV4 문장 삭제.
3. test_auto_core_equity_cash.py 기대 dict의 `"ev4"` 키와 `rules.ev4_open` 단언 삭제(total·n·v6 단언은 그대로).
4. test_auto_core_risk1r.py `GOLDEN`의 `decide_compare`·`decide_apply` 두 값과 test_auto_core_decide.py 69행 docstring. GOLDEN을 바꿀 때는 **base 코드의 같은 시나리오 결과에서 E4의 두 키를 뺀 dict의 해시 = 새 값**임을 보고서에 보인다(base 체크아웃에서 계산). 시나리오에 EV4 사건이 있어서 그 밖의 값까지 바뀌면 그 차이를 키 경로로 모두 적고, EV4 제거로만 설명되는지 보인다.

실행(Claude Code는 "auto_core.py"가 든 명령을 거부한다):
- 변경 전 worktree 기준선: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"`, `python docs/claude/t2rc-oracle.py selftest --repo <메인 체크아웃>`.
- 변경 뒤 같은 명령 + `-p "test_score_*.py"`·`-p "test_decision_journal_cards.py"`. 전체 스위트는 `test-runner` 서브에이전트(Haiku)로 돌려 실패만 보고 — 기준선 대비 새 실패 0. Ran 수는 삭제한 테스트 수만큼만 줄고 새 테스트만큼 는다(표로).
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` 통과.

# 실데이터 확인 (읽기 전용, 보고서에 결과만)

입력은 메인 체크아웃(E:\사업\##금동한\코덱스저장소)의 workspace/outputs·docs/claude에서 읽고, 출력은 저장소 밖 임시 폴더(예: $env:TEMP\rrec-ev4-check)에만 쓴다. auto_core.py·키움 실행 금지.
1. 계산기: worktree 판과 base 판(메인 체크아웃)으로 `check --day 2026-10-15`·`2026-10-16`·`2026-10-17` `--repo <메인 체크아웃>` `--out <임시>` `--ignore-input-sha`. 두 출력의 차이가 `oracle_sha256`·`ev4_history`뿐이어야 한다(10-14~10-16은 EV2가 같은 날 켜져 판정이 같다). 다르면 키 경로와 이유를 적는다.
2. 코어 rrec1 재계산(파일을 쓰지 않는 python 한 번, worktree 코드, 메인 체크아웃의 봉): 평가 세션 2026-10-16 포트폴리오와 8종목 → 10-17 decision.json `shock`·`by_symbol`과 비교. 기대: 사건 날짜 목록 같음, 각 사건의 kinds에서 "EV4"만 빠짐, event 2026-10-16 [EV2], rg RG1 no·RG2 no·RG3 no·RG4 ok, status no(바뀐 것이 kinds뿐).
3. 가정 실험: 같은 봉에서 마지막 세션의 EV2를 없앤 합성 SOXX(EMA50 위·3σ 선 위로 올린 사본)와 계좌 총액 $23,695.43(HWM $31,711.76) → base는 EV4로 열림·no, 새 코드는 사건 없음·ok. 결과 두 줄만 적는다.

# 지켜야 할 것 (어기면 Judge FAIL)

1. 바뀐 파일: auto_core_rules.py, auto_core_decide.py, auto_core_replay.py, auto-core-decision.schema.json(description 1곳), references/auto-core-decision.md, docs/claude/t2rc-oracle.py, docs/claude/t2rc-check-run.ps1(16행), 새 테스트 1개, 허용된 기존 테스트 변경(위 1~4), 보고서. 그 밖이 필요하면 멈추고 보고한다.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 든 줄을 만들거나 바꾸거나 지우지 않는다. 주문 경로 문자열 없음. 키움·auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행 금지.
3. 스크립트는 ASCII만(한국어는 `\u` 이스케이프). 정책·상태·장부·일지·workspace/policies·stock-strategy-system·workspace/outputs 쓰기 금지, docs/claude는 위 목록과 보고서만. 줄 끝은 체크아웃된 그대로.
4. E1~E5를 어기는 차이(EV4가 없던 입력의 출력 변화, EV1·EV2·EV3·EV5·RG·DS1·닫힘 변화), 계산기의 auto_core import는 FAIL.
5. **커밋하지 않는다.** 예약 작업·관제판·사전 등록·규칙 파일을 고치지 않는다.

# 보고 `docs/claude/rrec-ev4-remove-report.md` (worktree 안에 새로)

0 worktree HEAD(base와 다르면 그 사이 커밋이 docs/claude만인지) · 1 파일별 바뀐 줄(diff 요약, 지운 함수·상수·키 목록) · 2 동치 E1~E5를 어떻게 확인했는지 · 3 테스트(기준선·변경 뒤 Ran 수, 삭제·추가 테스트 이름, 새 실패 0, 계산기 selftest, 허용 변경 1~4 목록 파일:행, GOLDEN 재계산 근거) · 4 실데이터 1~3 결과 · 5 남은 주석(tickets 157행, portfolio_exposure 741행 등 고치지 않은 EV4 언급 — 파일:행) · 6 바뀐 파일 sha256(작업 트리 바이트)·계산기 sha256_lf·실행기 16행 값 · 7 멈춤·범위 문제(없으면 "없음").

# 병합·고정값 교체·C1 재시작 (Judge PASS 뒤 — Builder는 하지 않는다)

1. **Cowork**(Judge PASS 확인 뒤): 병합 스크립트 docs/claude/rrec-ev4-remove-merge-<날짜>.ps1 작성(ev-rg1-hyper-merge-2026-10-18.ps1 방식 — 자동 코어·decide·T2rcCheck·DocsCommit·DevQueue 실행 중이면 멈춤, Judge 마지막 줄 `VERDICT: PASS`, base 뒤 메인 이동은 docs/claude 커밋만, 대상 경로에 커밋 안 된 변경 없음, 계산기·실행기 한 병합). 함께 교체할 초안: ① 통합 점검 규칙 파일 v3.12.8(102행에서 "EV4 계좌 1차 선 도달 — …" 구절 삭제, 사건 목록 EV1·EV2·EV3·EV5) + 로더의 규칙 파일 경로·해시 ② 문서: recovery-gate-R-REC1-2026-10-09.md 1절 EV4 행 삭제 + 적용 메모 1줄, CLAUDE.md R-REC1 줄의 "account line L1," 삭제(사용자 커밋), gate-rule-epochs.json `GATE:REQ5_RREC1` 1줄, t2-rc-preregistration 변경 기록 1줄(계산기·실행기·로더·규칙 파일 새 고정값, C1 0부터). 사용자에게 승인 1줄 요청(예: `결정 rrec-ev4-remove 병합: 승인`).
2. **사용자**: 승인 1줄 → 병합 스크립트 한 번(시각: 화~토 06:00~09:00 KST·23:20~23:45 KST 밖).
3. **Cowork**(병합 출력 확인 뒤, 같은 세션): 규칙 파일·로더 교체(재서명, scheduled-prompts/README.md 변경 기록) · 문서 ② 반영 · 관제판.
4. **첫 확인**: 병합 뒤 첫 08:40 t2rc-check.json의 oracle_sha256 = 새 sha·verdict MATCH, 첫 decide의 shock.events에 EV4 없음, compare.json에 RREC:open B7 없음.

# 작성 기록 (Cowork, 2026-10-19)

- 원문 확인: 결정 문서 rrec-ev4-remove-decision-2026-10-19.md · authority-paths.txt 12·25·65행 · auto_core_rules.py 724~731·798~830·890~896행 · auto_core_decide.py 140~146·164~292·640~646·738~790·998~1022·1080~1110·1160~1168행 · auto_core_replay.py 210~265행 · auto_core_compare.py 262~296행 · schema 149~165행 · references 83~86행 · t2rc-oracle.py 66·1041~1050·1104~1114·1580~1603·1934~1940행 · t2rc-check-run.ps1 1~30행 · t2-rc 사전 등록 18~24·48~50행 · 테스트 파일 grep(근거 9) · 기준선 실행(근거 8).
- 동치 명세(E1~E5)는 "EV4를 빈 목록으로 부른 base"로 정의해, Judge가 base 코드와 직접 대조할 수 있게 했다.
