# Builder 지시문: d10-spy (결정 채점기가 SPY 기준 종가를 자동 코어 수집 이력에서도 읽게, 일반 변경)

사장 결정: "결정 d10: REUSE" (사장실 스레드 직접 입력, 2026-10-26 15:33 KST). 근거 문서: docs/claude/roadmap-fix-decisions-2026-10-26.md 2절, docs/claude/operating-diagnosis-2026-10-25.md 181-183행(9-1).
작업 위치: dev-run 헤드리스 Builder(워크트리). 커밋·푸시·병합은 하지 않는다. 비밀(.env*, 토큰, 계좌번호)은 읽지 않는다. 키움 도구·주문·정책·상태 파일은 건드리지 않는다. 줄바꿈은 파일의 기존 방식을 유지하고 일괄 변환하지 않는다.

## 쓸 수 있는 명령 (중요)
이 Builder는 승인 창이 없다. 아래 외의 셸 명령은 모두 거부되니 시도하지 않는다.
- 파일 읽기·검색·수정은 Read, Grep, Glob, Edit, Write 도구로 한다.
- 셸은 `python -m unittest ...` 한 가지 형태, 그리고 `git status`, `git diff`, `git log`만 된다. `cd`, `&&`, `;`, 파이프, heredoc, `python -c`, PowerShell은 쓰지 않는다.
- sha256 등 해시는 직접 계산하지 않는다(이 작업에는 해시 고정 갱신이 없다).

## 관찰된 사실
- `manage-us-stock-strategy/scripts/score_decision_journal.py` 116-149행 `load_reference_closes`는 `<closes_root>/reference-closes/SPY.json`(schema reference-closes-1.0)만 읽는다. 파일이 없어 2026-10-25 주간 채점 출력의 benchmark가 `MISSING`이다(workspace/outputs/journal-scores/20261025T002001Z/journal-scores.json).
- 자동 코어는 `workspace/policies/auto_core.json`의 `symbols_extra`(지금 SOXX, GRID)를 키움에서 받아 `<closes_root>/history/<SYMBOL>.close-history.json`(schema regular-session-close-history-1.0)에 쌓는다. 사장이 같은 날 symbols_extra에 SPY를 넣을 예정이다(이 작업 범위 밖, 정책 파일은 건드리지 않는다).
- 같은 파일의 `load_close_histories`(771-792행 부근 `load_inputs`에서 호출)가 이미 history 파일을 달력 검증과 함께 읽는다.

## 할 일
1. `load_reference_closes`(또는 `load_inputs`의 benchmark 줄)를 고쳐: reference-closes/SPY.json이 **있으면 지금과 똑같이** 그것을 쓴다. **없을 때만** history/SPY.close-history.json을 `load_close_histories`와 같은 검증으로 읽어 같은 모양 `{status, closes, errors}`로 돌려준다. history도 없으면 지금처럼 `MISSING`.
   - history 쪽 값을 쓸 때 결과에 출처를 남긴다(예: `source: "KIWOOM_CLOSE_HISTORY"`). 기존 키·라벨 `REFERENCE_ONLY`는 바꾸지 않는다. reference-closes 파일 쪽 결과는 키 하나도 바뀌지 않아야 한다.
   - history 파일의 검증 실패·미확인(unverified) 세션은 benchmark closes에서 뺀다(fail-closed: 그 지평은 BENCHMARK_UNAVAILABLE).
   - 분할 의심 검사(`_split_suspect`)·지평 계산·채점 규칙은 그대로.
2. 시험 `manage-us-stock-strategy/tests/test_score_spy_history.py`(임시 폴더에 합성 파일):
   - (a) reference-closes만 있음 → 지금과 같은 결과(키·값 동일).
   - (b) 둘 다 없음 → `MISSING`.
   - (c) history만 있음(정상) → `OK`, closes가 history 값과 같음, 출처 표시 있음.
   - (d) 둘 다 있음 → reference-closes가 이김.
   - (e) history가 깨짐/미확인 세션 → 그 세션 빠짐 또는 INVALID, 예외 없음.
   - 기존 시험 파일 test_score_learning.py·test_score_ticket_outcomes.py·test_journal_score_runner.py는 고치지 않는다.
3. 실행: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_score_*.py"` 와 `-p "test_journal_score_*.py"`. 전체 스위트·기준선 비교는 파이프라인이 한다.

## 하지 않는 것
- 채점 규칙·지평·최소 표본(30건)·라벨·증거 등급 변경. SPY를 매매 근거·관문 입력으로 쓰는 일.
- 정책·상태 파일, auto_core*.py, collect 스크립트, 예약 작업, tools/**, .claude/**, CLAUDE.md 수정.
- history 파일을 쓰거나 reference-closes 파일을 만드는 일(읽기만).

## 보고
`docs/claude/d10-spy-report.md`: 바꾼 함수·줄(전/후), reference-closes 경로가 바뀌지 않았다는 확인, history 검증 방식(어느 함수 재사용), 시험 목록과 결과, 확인 필요(예: 키움이 SPY 30분봉을 주는지는 사장 정책 반영 뒤 첫 수집에서 확인).

## Judge 확인 항목
1. 변경이 allowed_paths 세 파일뿐이다.
2. reference-closes/SPY.json이 있을 때 결과가 이전과 바이트 수준으로 같은 구조다(키 추가 없음).
3. history 경로는 기존 load_close_histories 검증을 거치고, 실패·미확인 세션은 빠진다(fail-closed).
4. 채점 규칙·지평·최소 표본·라벨이 바뀌지 않았다. SPY가 주문표·관문·코어 입력으로 가지 않는다.
5. 주문·권한 표지(`/api/us/ordr`, `ust2000`, `ust2001`, `order_submit`, `quantity_authority`, `kill_switch`)가 추가된 줄에 없다.

```dev-run
{"task_id": "d10-spy", "class": "general", "builder_model": "sonnet", "builder_effort": "high",
 "max_turns": 100, "builder_timeout_min": 60,
 "allowed_paths": ["manage-us-stock-strategy/scripts/score_decision_journal.py",
                   "manage-us-stock-strategy/tests/test_score_spy_history.py",
                   "docs/claude/d10-spy-report.md"],
 "target_tests": ["test_score_*.py", "test_journal_score_*.py"],
 "commit_message": "feat(score): read SPY benchmark closes from the auto-core close history when no reference file"}
```
