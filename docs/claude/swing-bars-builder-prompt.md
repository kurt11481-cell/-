---
id: swing-bars-builder-prompt
title: 자동 코어 daily — 코어 결과를 다 쓴 뒤 스윙 관찰 종목 종가만 따로 모음(실패해도 코어·decide·알림 불변)
date: 2026-11-20
class: 권한 경로(auto_core.py) 기능 추가(dev-run class authority — 경로 때문. 의미상 권한·한도·주문 단계·대조 불변식·킬 스위치 불변)
source: docs/claude/swing-widen-proposal-2026-11-19.md 1절 ①(2판 — 그 제안서 48행의 'steps.bars.swing 별도 키'는 이 지시문에서 '별도 파일'로 바꿈. result에는 키를 더하지 않는다) · docs/claude/swing-prereg-draft-2026-11-19.md 3절 1번·5절(신호 종목 수집 유지)
authority: order_authority=false · quantity_authority 값 변경 없음 · 주문 경로 없음 · 정책·상태 파일 쓰기 없음 · 키움은 지금 수집과 같은 읽기 전용 조회만(30분봉 조회와 첫 수집 때 거래소 조회 usa10098) · 스키마 변경 없음
approval: 방향 = 사장 결정 카드 "장비+소프트웨어 보강 (권장)" 2026-11-20 07:30:42 KST(cmsg_0137MRzn9nuDvvQmVxm6WeX99kLV7ACodt1NhCEcecn71U — 제안서 2판 순서 ① 종가 수집 개발 큐). 큐 등록 = 별도 사장 결정 카드(authority 작업, tools/dev_pipeline/README.md 44행)
weekly_user_touch: 1 (병합 1번: .\tools\dev-merge.ps1 swing-bars -ApproveAuthority — 경로 때문에 붙는 플래그. 다른 dev-run이 돌고 있으면(_lock) 병합하지 않는다)
---

```dev-run
{"task_id": "swing-bars", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 70, "builder_timeout_min": 45, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core.py", "manage-us-stock-strategy/tests/test_auto_core_swing_bars.py", "docs/claude/swing-bars-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "feat(auto-core): after the daily result is written, collect close histories for the swing shadow watch list in a separate best-effort step (own file, never changes the core result)"}
```

## 목표

스윙 그림자 장부(docs/claude/swing_shadow_ledger.py, 사전 등록 고정 2026-11-19)는 종가 이력 파일(workspace/outputs/regular-session-closes/history/<SYM>.close-history.json의 `sessions[].session_date/close/verified`)을 읽는다. 사장이 2026-11-20에 장부 모집단을 넓히기로 했고(반도체 장비·소프트웨어 종목), 그 종목들은 보유도 관심 명단도 아니라 지금 daily가 종가를 모으지 않는다. 종가가 없으면 그 신호는 NO_PRICE(자료 손실)가 된다.

고칠 것: daily가 **코어 결과(result.json·LATEST.json)를 다 쓴 뒤**, 목록 파일 `docs/claude/swing-watch.json`의 종목 종가를 **따로 모으는 마지막 단계**를 더한다. 이 단계는 무엇이 실패해도 코어 결과·반환값·종료 코드·decide·알림을 바꾸지 않는다. 결과는 별도 파일에만 적는다.

## 바꿀 것 — `manage-us-stock-strategy/scripts/auto_core.py` (daily)

1. 상수: `SWING_WATCH_PATH = REPO_ROOT / "docs/claude/swing-watch.json"`, `SWING_FILE = "swing-bars.json"`, `SWING_TIME_BUDGET_MIN = 20`, `SWING_SYMBOL_TIMEOUT_S = 600`.
2. `daily`의 새 인자는 `swing_watch_path: Path | None = None`이다. **None이면 swing 단계 전체를 건너뛴다.** `main()`만 `SWING_WATCH_PATH`를 넘긴다. 그래서 이 인자를 넘기지 않는 기존 테스트는 실제 저장소 목록 파일을 읽지 않는다.
3. `collect_bars`에 키워드 인자 `timeout: int = 3600`을 더하고 지금 213행의 3600 대신 그 값을 쓴다(기본값이 같아 코어 동작 불변). swing 단계는 별도 인자 `swing_collector`(기본 `functools.partial(collect_bars, timeout=SWING_SYMBOL_TIMEOUT_S)`)를 쓴다. **공용 `collector`에 timeout을 넘기지 않는다**(기존 가짜 collector는 키워드가 고정이라 TypeError가 난다).
4. 새 함수 `collect_swing_bars(...)`(이름은 바꿔도 됨). 호출 지점은 daily의 마지막 `_finish(...)`가 코어 결과를 쓴 뒤 **한 곳뿐**이다(지금 450행 근처). 킬 스위치 HOLD로 일찍 끝나는 경로(398~400행)·439·444행 근처의 다른 `_finish` 반환에는 넣지 않는다. 부르는 조건: `swing_watch_path`가 None이 아니고 코어 결과 status가 OK 또는 HOLD(킬 스위치가 아닌 HOLD 포함). FAIL·킬 스위치 날에는 부르지 않고 swing-bars.json도 쓰지 않는다.
5. **호출 전체를 `try/except Exception`으로 감싼다.** 어떤 예외가 나도 삼키고(남길 수 있으면 swing-bars.json에 적음) 코어 `_finish`의 반환값을 그대로 돌려준다. 반환 dict에 키를 더하지 않는다. `symbols_for_run`은 다시 부르지 않고 코어 수집 루프가 쓴 종목 목록을 넘긴다.
6. 목록 읽기: utf-8-sig로 읽는다. 형식 `{"schema": "swing-watch-1", "symbols": ["AMAT", ...]}`.
   - 파일이 없으면: 아무것도 하지 않고 파일도 쓰지 않는다.
   - 그 밖의 읽기 오류·깨진 JSON·dict 아님·schema 값 다름·symbols가 list 아님·코드가 패턴 `^[A-Z][A-Z0-9.]{0,11}$` 아님: 수집하지 않고 swing-bars.json에 status `LIST_INVALID`와 `reason`(200자 이내)을 쓴다.
   - 중복 코드는 한 번만 센다. 빈 목록은 정상이다.
7. 대상 = 목록 종목 − 코어가 이번 run에 모은 종목, 알파벳 순. 대상이 0개면 status OK, 빈 배열로 쓴다.
8. 종목마다 지금 수집 루프(412~429행)와 같은 `known_exchange`·`resolve_exchange`·`history_updater`와 `swing_collector`를 쓴다(같은 runtime·rate_policy·profile·closes_root·첫 수집 150일 규칙). **모든 예외**(StepFailure·subprocess.TimeoutExpired·그 밖의 Exception)를 그 종목에서 잡아 `failed`에 `{"symbol", "reason"}`(reason 200자 이내)로 적고 다음 종목으로 간다.
9. 시간 예산: 종목을 시작하기 전에 남은 예산(단계 시작부터 `SWING_TIME_BUDGET_MIN`분)이 `SWING_SYMBOL_TIMEOUT_S`보다 적으면 그 종목과 남은 종목은 시작하지 않고 `deferred`에 적는다. 시계는 시험에서 바꿀 수 있게 인자로 받는다(예 `clock=time.monotonic`). 최악의 경우 코어 약 3분 + 20분 + 마지막 종목 10분 안쪽으로 끝난다(예약 한도 60분 안).
10. 결과 파일 `workspace/outputs/auto-core/<날짜>/swing-bars.json`: `{"schema_version": "auto-core-swing-bars-1.0", "run_day_kst", "status": "OK"|"PARTIAL"|"LIST_INVALID", "histories": [{"symbol", "sessions", "verified_sessions"}], "failed": [...], "deferred": [...]}`. status는 failed·deferred가 모두 비면 OK, 아니면 PARTIAL. 이 파일 쓰기가 실패해도 예외를 밖으로 내지 않는다.
11. **코어 result.json·LATEST.json은 이 단계에서 다시 쓰지 않고, result에 키를 더하지 않는다.** daily 종료 코드는 코어 결과 status로만 정한다(지금과 같음).
12. 모듈 docstring의 daily 단계 목록에 '6 (best effort, after 5) swing watch list closes -> swing-bars.json, never changes the result' 한 줄을 더한다. ASCII.

그 밖은 바꾸지 않는다: `symbols_for_run`·`isolatable_symbols`·bar-isolate 동작·노출 검토·결과 스키마·decide 파일(`auto_core_decide.py`는 allowed_paths에 없다)·첫 수집 시작일·코어 수집의 timeout 값.

## 새 테스트 — `manage-us-stock-strategy/tests/test_auto_core_swing_bars.py`

선례 `test_auto_core_bar_isolate.py`처럼 기존 fixture(`test_auto_core.DailyTests`)를 상속하고 `load_tests`로 이 파일 테스트만 돌린다. fixture: 보유 AAA·BBB, 관심 NEWW, extra SOXX. 목록 파일은 임시 경로로 만들어 `swing_watch_path`로 넘기고, 가짜 swing collector는 `swing_collector`로 넘긴다.

1. `swing_watch_path`를 넘기지 않으면: swing-bars.json이 없고, collector 호출이 {AAA,BBB,NEWW,SOXX}뿐이다. ('지금과 같음'의 근거는 기존 test_auto_core*.py가 고치지 않은 채 전부 통과하는 것이다.)
2. 목록 경로를 넘겼지만 파일이 없으면: swing-bars.json이 없고 swing collector가 불리지 않는다.
3. 목록 `["SWA", "AAA", "SWA"]`: SWA만 한 번 수집되고(AAA는 코어가 이미 모음) status OK, histories에 SWA. 가짜 swing collector 안에서 읽은 result.json·LATEST.json 바이트가 daily 반환 뒤 바이트와 같고, `load_json(result.json) == 반환값`이다(코어 결과가 swing 단계 전에 이미 디스크에 있음도 이것으로 확인).
4. SWA가 `StepFailure("BAR_COLLECTION_FAILED:SWA:1")`, SWB가 `subprocess.TimeoutExpired`, SWC가 `RuntimeError`를 내면: 셋 다 `failed`에 있고 status PARTIAL, daily 반환값·종료 코드·result.json 바이트는 3번 방식으로 확인해 바뀌지 않는다.
5. 시계를 바꿔 남은 예산이 종목 상한보다 적으면 남은 종목이 `deferred`에 있고 swing collector가 불리지 않는다.
6. 코어 결과가 FAIL인 날(예 보유 AAA 수집 실패): swing collector가 불리지 않고 swing-bars.json이 없다.
7. 킬 스위치 HOLD 경로: swing collector 0회, swing-bars.json 없음. 킬 스위치가 아닌 HOLD 날에는 swing 단계가 돈다.
8. 목록 형식이 틀리면(schema 값 다름 · 소문자 코드 · 깨진 JSON): swing collector가 불리지 않고 status LIST_INVALID.
9. 목록이 전부 코어 종목(`["AAA", "NEWW"]`)이면 swing collector 0회, status OK, histories 빈 배열.
10. swing-bars.json 쓰기가 실패해도(그 경로에 같은 이름의 폴더를 미리 둠) daily 반환값·종료 코드가 3번과 같다.
11. 실제 기본 swing collector가 runner에 timeout 600을 넘긴다(runner를 가짜로 바꿔 인자 확인).

키움·kiwoomcli·PowerShell을 실제로 부르는 테스트는 만들지 않는다.

## 지켜야 할 것 (어기면 Judge FAIL)

1. diff는 auto_core.py, 새 테스트 파일, 보고뿐이다. 기존 테스트 파일은 고치지 않는다. 기존 테스트가 실패하면 고치지 말고 BLOCKED로 보고한다.
2. 권한 표지 4종(`order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`)이 들어간 줄을 만들거나 바꾸거나 지우지 않는다. 주문 경로 문자열(`/api/us/ordr`, `ust2000x`, `kiwoom_order`, `order_submit`)을 넣지 않는다. `schemas/` 파일은 고치지 않는다.
3. 실행하지 않는다: 키움·kiwoomcli, `run_auto_core.ps1`, `collect_30m.ps1`, daily 자체. 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"` 형식 그대로만 돌린다(앞에 환경 변수나 플래그를 붙이지 않는다). 명령에 auto_core.py 문자열을 넣지 않는다. 전체 테스트는 돌리지 않는다(파이프라인이 돌린다).
4. auto_core.py(git i/lf, 작업 트리 CRLF)의 줄바꿈을 지킨다. scripts/*.py는 ASCII 전용이다.
5. `docs/claude/swing-watch.json`을 만들지 않는다(목록은 사장 결정 뒤 별도 커밋).

## 보고 `docs/claude/swing-bars-report.md`

- 바꾼 줄(파일:줄)과 새 테스트 목록, 대상 테스트 결과(Ran 수, 실패 0)와 `git diff --ignore-cr-at-eol --stat`. 보고 머리말에 권한 표지 4종 글자를 쓰지 않는다('권한 표지 줄 변경 없음'으로).
- 남은 위험(보고에 그대로 적는다):
  - daily 예약 한도 60분(register_auto_core_task.ps1 25행). 종목 상한 600초와 예산 20분으로 최악 약 33분이지만, 예약이 끊기면 `host_status.ps1` 142~145행이 작업 종료 코드 경고를 낸다. 코어 결과는 이미 쓰였으므로 decide에는 닿지 않는다.
  - 목록 종목 수집은 키움 읽기 조회를 늘린다(rate 정책 안). 첫 수집은 150일치라 길다. verified=false 세션은 장부가 버리므로 histories의 verified_sessions를 본다.
  - `docs/claude/strategy1101_score.py` 259행은 history 폴더의 모든 파일을 읽는다(입력 목록이 늘어남). 계산에 쓰는 종목은 그 파일이 정한다 — 영향 확인 결과를 보고에 적는다.
  - 목록 종목이 나중에 보유·관심이 되면 코어 수집으로 넘어간다(7번 빼기).

## 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| docs/claude/swing-watch.json(수집 대상 목록) | 사장 결정 뒤 Cowork 별도 커밋(이번 변경 밖) | `auto_core.py` daily swing 단계(이번 변경) | 수집 대상 | swing-bars.json status LIST_INVALID | 연결 |
| 목록 종목 종가 이력 history/<SYM>.close-history.json | 예약 InvestmentV2-AutoCore 화~토 06:15 KST(`register_auto_core_task.ps1` 25행) → `auto_core.py` daily 마지막 단계(이번 변경, 코어 `_finish` 뒤) | `docs/claude/swing_shadow_ledger.py` 85행 `load_closes`(같은 history 파일) — 신호 난 주 회사PC 손 실행(관제판 tasks/swing-1119 resume.date → `docs/claude/scheduled-prompts/secretary-daily.txt` 17행) | 그림자 장부 판정 지점의 자료 손실이 줄어 넓힌 종목 신호가 판정에 들어감 → 판정 지점 사장 카드(몫 키우기·새 진입 멈춤) | 장부 손 실행의 trade_status에 NO_PRICE·DATA_GAP로 보임(swing_shadow_ledger.py run()) · 예약 강제 종료는 `host_status.ps1` 142~145행 경고 | 연결(손 실행) |
| workspace/outputs/auto-core/<날짜>/swing-bars.json(status·failed·deferred) | 위와 같음 | 없음 | 없음 | 없음 — LIST_INVALID나 매일 deferred가 신호 주까지 조용히 이어질 수 있음. 코어 알림은 일부러 없음(코어 알림을 흐리지 않기 위해) | 끊김 — 메울 변경: 주간 점검이 swing-bars.json status를 읽음 · 승인 경로: 예약 지시문 변경(사장 직접 입력) |
| 같은 history 폴더 | 위와 같음 | `docs/claude/strategy1101_score.py` 259행(폴더 전체 glob) — 의도한 소비자 아님 | 없음(입력 목록만 늘어남, 계산 종목은 그 파일이 정함 — 보고에서 확인) | 그 채점 실행의 입력 해시 목록 | 영향 확인 필요(보고) |

## Judge 확인 항목

1. diff가 auto_core.py·새 테스트·보고뿐이다. auto_core_decide.py·스키마·기존 테스트·권한 표지 줄·주문 경로 변경이 없다. 정책·상태 파일 쓰기가 없다.
2. swing 단계는 마지막 코어 `_finish`(result.json·LATEST.json 쓰기) 뒤 한 곳에서만 돌고, 전체가 try/except로 감싸여 있으며, 코어 결과 파일을 다시 쓰지 않고, 반환값과 종료 코드는 코어 결과 그대로다(코드 읽기 + 테스트 3·4·10).
3. `swing_watch_path` 기본값이 None이고 `main()`만 실제 경로를 넘긴다. 기존 test_auto_core*.py가 고치지 않은 채 통과한다(테스트 1).
4. 목록 종목의 어떤 실패(StepFailure·TimeoutExpired·일반 예외)도 daily를 FAIL로 만들지 않는다(테스트 4). FAIL·킬 스위치 날에는 swing 단계가 돌지 않는다(테스트 6·7).
5. 시간 예산과 종목 상한이 지켜진다: 코어 수집 timeout은 3600 그대로, swing은 600(테스트 5·11).
6. 대상 테스트가 전부 통과한다.
7. G9: 연결표 ②③⑤ 원문 행 대조 — register_auto_core_task.ps1 25행, auto_core.py 변경 위치, swing_shadow_ledger.py 85행, secretary-daily.txt 17행, strategy1101_score.py 259행, host_status.ps1 142~145행. 끊김 행은 메울 변경·승인 경로가 적혀 있다.
8. `auto_core_decide.py`·`t2rc-oracle.py`·`auto-core-alert` 쪽이 swing-bars.json이나 목록 종목을 읽지 않는다(grep 결과를 보고에).
