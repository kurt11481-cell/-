---
id: bar-isolate-builder-prompt
title: 자동 코어 — 관심 종목 하나의 30분봉 수집 실패는 그 종목만 격리(그 종목 매수 막힘·알림 1줄), 보유·기준 종목 실패는 지금처럼 FAIL
date: 2026-11-13
class: 권한 경로(auto_core*.py) 결함 수정(dev-run class authority — 경로 때문. 의미상 권한·한도·주문 단계·대조 불변식·킬 스위치 불변)
source: docs/claude/code-review-2026-11-13.md 1절 H-1·2절 #1 · 실제 사례 workspace/outputs/auto-core/2026-11-11/result.json(status FAIL, reasons ['BAR_COLLECTION_FAILED:PLTR:1'])·같은 날 decision.json(HOLD T1_NOT_OK)
authority: order_authority=false · quantity_authority 값 변경 없음 · 주문 경로 없음 · 정책·상태 파일 쓰기 없음 · 키움 호출 없음 · 스키마 변경 없음
approval: 사장 결정 카드 "급한 2건 + 실행기 점검 착수" 2026-11-13 14:40:53 KST(code-review-2026-11-13.md 6절 — 범위 H-1 개발 큐)
weekly_user_touch: 1 (병합 1번: .\tools\dev-merge.ps1 bar-isolate -ApproveAuthority — 경로 때문에 붙는 플래그. 다른 dev-run이 돌고 있으면(_lock) 병합하지 않는다)
---

```dev-run
{"task_id": "bar-isolate", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 70, "builder_timeout_min": 45, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core.py", "manage-us-stock-strategy/scripts/auto_core_decide.py", "manage-us-stock-strategy/tests/test_auto_core_bar_isolate.py", "docs/claude/bar-isolate-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core): isolate a watch-only symbol whose 30m collection fails (no buy for it, one alert) instead of failing the daily run; held/extra/exposure symbols still fail closed"}
```

## 목표

2026-11-11 06:15 KST 자동 코어 daily가 관심 명단 종목 PLTR(보유 아님) 하나의 30분봉 수집 실패(`BAR_COLLECTION_FAILED:PLTR:1`)로 run 전체 FAIL이 됐다. 그 결과 07:45 decide가 `T1_NOT_OK`로 HOLD했고(`auto_core_decide.py` 437~440행), 그날은 보유 종목 매도 주문표·노출 E·'반등 때 줄이기' 판정이 모두 없었다. 원인은 `auto_core.py` 347~360행 수집 루프가 종목 하나의 `StepFailure`를 받자마자 364~367행에서 run을 끝내기 때문이다.

고칠 것: **보유도 기준도 아닌 관심 종목**의 종목별 실패만 그 종목을 격리하고 run을 계속한다. 07:45 decide는 격리된 종목을 '자료 없음'으로 다뤄 그 종목 매수를 막고, 알림 1줄을 낸다. 보유 종목·설정 기준 종목·노출 검토가 읽는 종목의 실패와 전역 실패는 지금처럼 FAIL이다.

## 바꿀 것 1 — `manage-us-stock-strategy/scripts/auto_core.py` (daily)

1. 격리 가능한 종목 = 관심 명단 members − 보유 종목 − `symbols_extra`(설정) − 노출 검토가 읽는 종목 − decide 기준 종목.
   - 보유 종목은 `symbols_for_run`(95~114행)과 같은 출처로 정한다(이번 run의 `kiwoom_broker_snapshot.shadow.json`이 있으면 그것, 없으면 상태 파일).
   - 노출 검토가 읽는 종목 = `run_portfolio_exposure_review.py` 527~530행과 같은 출처다. 설정 `{config["benchmark"], config["supplement"]}`(`portfolio_exposure.exposure_config(<alert 정책>)`, 지금 SOXX·SOXL)와 장부로 복원한 모든 스냅숏의 보유 종목(같은 파일의 `ledger_status`·`read_ledger_entries`·`reconstruct_snapshots`를 같은 기본 경로로 다시 씀, 읽기만)이다. T1의 노출 검토에는 cards·proposals가 없다.
   - decide 기준 종목 = `auto_core_rules.C`의 `RREC_BENCHMARK`·`RREC_POWER_BENCHMARK` 값(지금 SOXX·GRID, auto_core_rules.py 64~65행). decide가 이 종목의 격리를 거부하므로(바꿀 것 2.1) T1에서도 빼야 한다.
   - 위 집합 중 하나라도 읽다 예외가 나면 격리 가능한 종목을 빈 집합으로 둔다. 그러면 지금과 같이 첫 실패에서 FAIL한다(fail-closed).
   - 새 도우미 함수 1개로 만든다(예: `isolatable_symbols(...)`). `symbols_for_run`의 서명과 결과는 바꾸지 않는다.
2. 수집 루프(347~360행)에서 종목 하나의 처리(`known_exchange`·`resolve_exchange`·`collector`·`history_updater`)가 `StepFailure`를 내면 다음과 같이 한다.
   - 그 종목이 격리 가능한 종목이고, 사유가 `EXCHANGE_UNRESOLVED:`·`BAR_COLLECTION_FAILED:`·`CLOSE_HISTORY_FAILED:` 중 하나로 시작하면 격리한다. `{"symbol": <종목>, "reason": <StepFailure 문자열>}`를 격리 목록에 더하고 다음 종목으로 넘어간다. 그 종목의 이력은 갱신하지 않는다.
   - 그 밖의 경우는 지금처럼 다시 올린다(→ FAIL). 보유·extra·노출 설정 종목의 실패, `SESSION_CALENDAR_UNAVAILABLE:` 같은 전역 사유, 그 밖의 모든 사유가 여기에 든다.
   - `StepFailure`가 아닌 예외(예: 수집 시간 초과 `subprocess.TimeoutExpired`)는 손대지 않는다. 지금처럼 `UNEXPECTED_ERROR` FAIL이다.
3. 격리 목록이 비어 있지 않을 때만 `result["steps"]["bars"]`에 `"isolated": [...]`(종목 순서)를 넣는다.
   - 비어 있으면 `steps.bars`는 지금과 똑같이 `{"status": "OK", "histories": [...]}`이다.
   - `steps.bars.status`는 "OK" 그대로 둔다.
   - `result["status"]`·`reasons`·`warnings`에는 아무것도 더하지 않는다(warnings 스키마 설명은 "Never a reason to hold" — 다른 뜻의 칸이다).
   - 격리가 있어도 노출 계산(362행)은 지금처럼 돈다.
4. 모듈 docstring 15~16행 "the first failure stops it"을 바뀐 동작에 맞게 고친다(보유·기준 종목과 전역 실패는 멈춤, 관심 종목만의 실패는 격리). ASCII.

## 바꿀 것 2 — `manage-us-stock-strategy/scripts/auto_core_decide.py`

1. T1 결과의 `steps.bars.isolated`를 읽는다.
   - `steps`·`steps.bars`·`isolated` 중 하나라도 없으면 격리 없음이다(`((t1.get("steps") or {}).get("bars") or {}).get("isolated")` 식으로, KeyError 없이). 옛 기록과 기존 decide 테스트의 T1(`test_auto_core_decide.py` 97행 `{"status": "OK"}` — steps 없음)도 이렇게 읽힌다.
   - 형식을 검사한다. 비지 않은 list이고, 항목마다 키가 정확히 `symbol`(비지 않은 대문자 str)·`reason`(str)이며, 같은 종목이 두 번 나오지 않아야 한다.
   - 격리 종목이 decide의 보유 종목(holdings)이나 기준 종목(`benchmarks`, 624행)에 들면 안 된다.
   - 어긋나면 기존 `DecideFailure` 경로로 멈춘다(`DecideFailure("T1_BARS_ISOLATED_INVALID")`, 새 상태값 없음). 437행의 T1 FAIL 판정은 바꾸지 않는다.
   - 보유·기준 종목 대조는 holdings(548행 부근)와 `benchmarks`(624행)가 정해진 뒤에 한다. 새 세션 없는 날 일찍 끝나는 경로(532~537행 부근)에서는 대조하지 않아도 된다.
2. 봉 불러오기 루프(629~638행)에서 격리 종목은 불러온 결과(`load_symbol` 또는 `bars_loader`)를 바로 덮는다.
   - **새 dict로** 덮는다(`{**loaded, "status": "ISOLATED", "errors": ["T1_BARS_ISOLATED"], "split_suspects": []}`). 불러온 dict를 직접 고치지 않는다(테스트 Env의 `bars_loader`는 같은 dict를 돌려준다 — 같은 Env의 다음 실행이 오염됨).
   - 그 종목에는 `SPLIT_SUSPECTED` 예외를 내지 않는다.
   - 그러면 `rules.evaluate_symbol`(auto_core_rules.py 539~548행)이 기존 '자료 문제' 경로로 그 종목을 UNK(`BARS_ISOLATED`)로 보인다.
   - 이 덮어쓰기가 꼭 필요한 이유: `collect_30m.ps1`(43~67행)은 최신 날짜부터 과거로 내려가며 페이지마다 저장한다. 과거 쪽에서 실패해도 평가 세션 봉은 이미 저장돼 있을 수 있다. decide는 페이지를 직접 읽으므로(634행 `load_symbol`) 덮어쓰지 않으면 그 종목이 OK로 읽혀 매수 판정이 날 수 있다.
3. 격리 종목이 있으면 `exceptions`에 1개를 더한다(366~367행 경로 → `push: True`).
   - 코드: `("T1_BARS_ISOLATED", <줄>)`
   - 줄: "관심 종목 30분봉 수집 실패 <종목들 ', '로> — 오늘 그 종목 매수 막힘(보유 종목 매도·노출 판정은 계속) — Cowork 원인 확인"
   - 파일은 ASCII 전용이므로 한국어는 `\uXXXX` 이스케이프로 쓴다(같은 파일 581~594행처럼).
   - 줄에는 종목 코드만 넣고 StepFailure 사유 문자열은 넣지 않는다(사유는 T1 결과에 있다).
4. decide 결과에 새 필드를 만들지 않는다. 기존 `alerts`·종목별 `reasons`·`inputs.t1_result`만으로 보인다.

그 밖은 바꾸지 않는다: 매수 문턱·한도·R-REC1·재배치 순위 계산식·주문표 형식·`input_block`(코어 입력 문서 막힘)·연구 기록 문턱·T1 FAIL 처리·첫 수집 시작일(first-collect).

## 새 테스트 — `manage-us-stock-strategy/tests/test_auto_core_bar_isolate.py`

선례 `test_auto_core_first_collect.py`·`test_auto_core_reconcile_orddt.py` 184~231행처럼 만든다.
- 기존 테스트 클래스를 상속해 fixture를 쓴다(daily 쪽 `test_auto_core.DailyTests`, decide 쪽 `test_auto_core_decide`의 env 도우미).
- `load_tests`로 이 파일의 테스트만 돌게 한다. 상속한 테스트가 두 번 돌면 안 된다.
- fixture의 NOW·RECORD(test_auto_core.py 41~42행)를 그대로 쓴다. fixture는 보유 AAA·BBB, 관심 NEWW, extra SOXX이다.
- fixture alert 정책은 `{}`라서 노출 설정 읽기가 실패한다. 그러므로 격리를 시험할 때는 노출 검토 종목 읽기를 `mock.patch`로 고정한다(예: {"SOXL"}). 기존 테스트는 patch가 없어 격리가 꺼진 채로 지금처럼 통과해야 한다.

daily:
1. NEWW 수집이 `BAR_COLLECTION_FAILED:NEWW:1`로 실패하면:
   - status OK, reasons는 실패 없는 run과 같다.
   - `steps.bars.isolated == [{"symbol": "NEWW", "reason": "BAR_COLLECTION_FAILED:NEWW:1"}]`.
   - histories에 NEWW가 없고 AAA·BBB·SOXX는 있다.
   - 노출 실행기가 불렸고 `steps.exposure.status == "OK"`이다.
2. `history_updater`가 NEWW에서 `CLOSE_HISTORY_FAILED:NEWW:x`를 내거나, 거래소 읽기가 NEWW에서 `EXCHANGE_UNRESOLVED:NEWW`를 내면 → 각각 격리된다.
3. 보유 AAA 실패 → FAIL `BAR_COLLECTION_FAILED:AAA:1`(지금과 같음). extra SOXX 실패 → FAIL. 이때 노출 검토 종목 patch에는 SOXX를 넣지 않는다(예: {"SOXL"}) — extra 제외만으로 FAIL임을 보이기 위해.
4. NEWW를 노출 설정 종목으로 patch하고 NEWW가 실패하면 → FAIL.
5. NEWW에서 `SESSION_CALENDAR_UNAVAILABLE:x` → FAIL. NEWW에서 `RuntimeError` → FAIL `UNEXPECTED_ERROR:`.
6. 노출 설정 읽기가 예외를 내면(patch 없이 fixture 그대로) NEWW 실패 → FAIL. 격리하지 않는다.
7. 실패가 없으면 `steps.bars`의 키가 정확히 {"status", "histories"}이다.

decide:
8. 보유가 아닌 관심 종목 X가 격리되지 않았을 때 매수 주문표가 나오는 env를 쓴다.
   - 기존 fixture: `test_auto_core_decide.py` 390~397행 `Env(holdings={"SOXL": 10})` + `env.write_good_news()` → MU 매수 주문표 1건. MU를 X로 쓴다.
   - 격리 있는/없는 두 실행은 별도 Env로 하거나 compare 모드로 한다(apply 모드 같은 날 재실행은 `_rerun` HOLD 경로, 757~770행 부근).
   - T1의 `steps.bars.isolated`에 X를 넣으면 다음이 모두 성립해야 한다.
     - X 매수 주문표 0건.
     - X가 재배치 후보가 아니다(`redeploy_ranking` 1214행 결과와 그것이 보이는 decision 칸 — 어느 칸으로 확인했는지 보고).
     - alerts에 `T1_BARS_ISOLATED`(push True) 1건이 있다.
     - 보유 종목 매도 주문표·매도 판정(evidence의 sell)이 격리 없는 실행과 같다. 단, X가 재배치 대상이던 env라면 '재배치 후보 없음' 실행과 같다.
9. 격리 항목이 잘못된 형식(키 누락·보유 종목·기준 종목 SOXX·중복)이면 decide status FAIL, reasons에 `T1_BARS_ISOLATED_INVALID`.
10. `steps.bars`에 `isolated` 키가 없는 T1에서는 decide 결과가 지금과 같다(같은 env 두 번 실행 비교 또는 기존 단언 재사용).

키움·kiwoomcli·PowerShell을 실제로 부르는 테스트는 만들지 않는다.

## 지켜야 할 것 (어기면 Judge FAIL)

1. diff는 위 '바꿀 것 1·2'와 새 테스트 파일, 보고뿐이다. 기존 테스트 파일은 고치지 않는다.
   - 기존 테스트가 실패하면 고치지 말고 BLOCKED로 보고한다. 예를 들어 `test_auto_core.py` 1317~1324행 `test_first_failure_stops_the_run`은 보유 AAA가 먼저 실패하므로 그대로 통과해야 한다.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`가 들어간 줄을 만들거나 바꾸거나 지우지 않는다. 주문 경로 문자열(`/api/us/ordr`, `ust2000x`, `kiwoom_order`, `order_submit`)을 넣지 않는다. `schemas/` 파일은 고치지 않는다.
3. 실행하지 않는다: 키움·kiwoomcli, `auto_core.py`, `run_auto_core.ps1`, `collect_30m.ps1`.
   - 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"` 형식 그대로만 돌린다(앞에 환경 변수나 플래그를 붙이지 않는다).
   - 명령에 auto_core.py 문자열을 넣지 않는다.
   - 전체 테스트는 돌리지 않는다(파이프라인이 돌린다).
4. 고치는 기존 파일(auto_core.py·auto_core_decide.py — git i/lf, 작업 트리 CRLF)의 줄바꿈을 지킨다. scripts/*.py는 ASCII 전용이다.

## 보고 `docs/claude/bar-isolate-report.md`

보고에 넣을 것:
- 바꾼 줄(파일:줄)과 새 테스트 목록, 그리고 테스트 8에 쓴 env가 무엇인지(어느 종목이 어떤 근거로 매수 주문표를 내는지).
- 대상 테스트 결과(Ran 수, 실패 0)와 `git diff --ignore-cr-at-eol --stat`.
- 남은 위험:
  - 수집 시간 초과(`TimeoutExpired`)는 여전히 run 전체 FAIL이다.
  - 같은 종목이 여러 날 격리되면 그동안 그 종목 매수가 계속 막힌다. 다음 성공 수집은 마지막 이력 세션부터 다시 받는다.
  - 노출 설정·장부 읽기 실패 날은 격리가 꺼진다.
  - 08:40 독립 대조(`docs/claude/t2rc-oracle.py`)는 페이지를 직접 읽고 격리를 모른다. 격리 날 그 종목이 대조 쪽 후보로만 나오면 `missing_in_core` → 알림 ⑫ "독립 대조 MISMATCH"가 날 수 있다(아래 연결표 3행, 별도 승인 경로).

## 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| T1 결과 `steps.bars.isolated`(격리 종목·사유, 실패 날만) — workspace/outputs/auto-core/<날짜>/result.json·LATEST.json | 예약 InvestmentV2-AutoCore 화~토 06:15 KST(`register_auto_core_task.ps1` 25행) → `auto_core.py` daily 수집 루프(현 347~360행, 이번 변경) | 예약 InvestmentV2-AutoCoreDecide 07:45 KST(같은 파일 27행) → `auto_core_decide.py` T1 읽기(현 434~436행 뒤, 이번 변경) | 그 종목 매수 요건 UNK·매수 주문표 없음·재배치 후보 제외. 보유 매도·노출 E·줄이기 판정은 계속(지금은 전부 없음) | 아래 알림 행. decide가 격리를 못 읽으면 저장된 최신 페이지로 그 종목 매수 판정이 날 수 있다(collect_30m.ps1 43~67행 최신부터 저장) — 막는 것은 decide 덮어쓰기와 새 테스트 8뿐 | 연결 |
| decide `alerts`의 예외 `T1_BARS_ISOLATED`(push) | `auto_core_decide.py` 예외 → alerts(현 366~367행), 07:45 KST | 자동 운영 코어 결과 알림 trig_01D5KxMSJgbeRG1ZL5ox3Fna 화~토 08:50(`docs/claude/scheduled-prompts/auto-core-alert.txt` 42행 ⑦, `auto-core-alert/read.py` 44행 'D PUSH') + 사장실 알림 올리기 — 아침 trig_01KkJL5f5ttgyM2NT2xSC5Vk 09:05(같은 5) 재사용) | 사장 폰 알림 1줄·사장실 글 → Cowork가 수집 실패 원인 확인(키움 자료 범위·조회 제한) | 알림 예약이 안 돌면 사장실 결과 모음(예약 작업 결과 요약)이 실행 기록 없음으로 봄. 알림 줄 회귀는 새 테스트 8 | 연결 |
| decide `candidates`(격리 종목 없음) | `auto_core_decide.py` 07:45 KST | 독립 대조 08:40(`docs/claude/t2rc-oracle.py` 214행 페이지 직접 읽음·1569~1571행 `missing_in_core`) → `auto-core-alert.txt` 47행 ⑫ | 격리 날 그 종목이 대조 쪽 후보로 나오면 거짓 MISMATCH 알림 → Cowork 확인 | ⑫ 알림 자체로 보임(D PUSH 격리 줄과 같은 날) | 끊김 — 메울 변경: t2rc-oracle가 T1 `steps.bars.isolated` 종목을 비교에서 뺌 · 승인 경로: 예약 작업 변경(사장 직접 입력 승인), bar-isolate 병합 뒤 따로 제안 |

## Judge 확인 항목

1. diff가 '바꿀 것 1·2', 새 테스트 파일, 보고뿐이다. 기존 테스트·스키마·권한 표지 줄·주문 경로 변경이 없고, 키움 호출과 정책·상태 파일 변경도 없다.
2. 새 테스트가 바뀐 동작을 실제로 잡는다.
   - daily의 격리 분기를 되돌리면 테스트 1·2가 실패한다.
   - decide의 덮어쓰기를 빼면 테스트 8의 '매수 주문표 0건' 또는 alerts 단언이 실패한다(보고에 근거).
   - 보유·extra·노출 설정 종목 실패와 전역·비 StepFailure 실패는 FAIL이다(테스트 3~6).
3. 격리 종목 매수 0건, 재배치 후보 아님. 보유 종목 매도 판정은 격리 없는 실행과 같다(테스트 8).
4. 실패 없는 날의 T1·decide 출력이 지금과 같다(테스트 7·10). `steps.bars.status`·`result.status`·`warnings`가 바뀌지 않았다.
5. 잘못된 격리 항목은 decide FAIL이다(fail-closed, 테스트 9). 437행 T1 FAIL → HOLD `T1_NOT_OK` 경로는 그대로다.
6. 대상 테스트가 전부 통과한다.
7. G9: 연결표 ②③⑤의 원문 행 대조 — register_auto_core_task.ps1 25·27행, auto_core.py·auto_core_decide.py 변경 위치, collect_30m.ps1 43~67행, auto-core-alert.txt 42·47행, read.py 44행, t2rc-oracle.py 214·1569~1571행.
8. 격리 가능 종목에서 보유·extra·노출 검토 종목(설정 + 장부 스냅숏 보유)·decide 기준 종목(RREC_BENCHMARK·RREC_POWER_BENCHMARK)이 모두 빠지고, 그중 하나라도 읽기 실패면 격리가 꺼진다. decide 덮어쓰기가 새 dict다.
