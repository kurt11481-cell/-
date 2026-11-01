---
id: p1-baseline-diag2-builder-prompt
title: "개발 큐 기준선 전체 테스트 실패 급증(10/29 22+9 → 10/30 276+10) 원인 진단 — p1-baseline-diag2 (같은 진단 2차, id 재사용 불가로 새 id)"
date: 2026-11-01
class: "general(일반 변경 — 보고서 1개만 새로 씀, 코드·테스트 수정 없음). 개발 큐: Builder Sonnet → 스크립트 판정 → Judge → READY_TO_MERGE면 병합"
source: "사장 결정 카드 'P-1 원인 진단 먼저'(사장실 회사PC 스레드 '전체 코드 리뷰 진행', 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9CEJrS5Rp5pLsq4Drb4q78V, 2026-11-01 13:20 KST, 계정=사장). 근거 docs/claude/code-review-pipeline-2026-11-01.md P-1"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
weekly_user_touch: "0"
---

## 목표
개발 큐 기준선 전체 테스트의 실패 수가 크게 늘었다. 기준선 1e43b43(10/29)은 실패 22·오류 9였고, 33bae7d(10/30)와 a1ce322(10/30)는 실패 276·오류 10이다. 새로 생긴 실패 255건은 거의 모두 `test_portfolio_decision_dashboard`(Manual timing·corporate action 계열)이고, 7건이 `test_evaluate_timing_integration`이다. 대부분 `validate_manual_direction_evidence(...)`가 False를 돌려주는 단언이다.
두 기준선 사이에 시험 대상 코드는 바뀌지 않았다(`git diff --stat 1e43b43 33bae7d`에서 docs/claude를 빼면 auto_core_reconcile.py, 그 테스트, 참고 문서 1개뿐). 그래서 시험이 **저장소 밖 조건**에 의존한다고 의심한다. 후보는 현재 시각·날짜 경과, git에 없는 workspace/ 파일, 설치 사본(~/.codex/skills 등) 같은 것이다. 이 작업은 **원인을 진단하는 것만** 한다. 코드나 테스트는 고치지 않는다.

## 절차
1. 대상 테스트를 실행해 지금 실패 목록을 얻는다(아래 "테스트" 명령 2개). 실패·오류의 테스트 이름과 단언 메시지 첫 줄을 모은다.
2. 실패 클래스마다 대표 테스트 1~2개를 골라, 단언이 거짓이 되는 지점을 코드에서 따라간다. 시작점은 `manage-us-stock-strategy/scripts/run_manual_portfolio_analysis.py`의 `validate_manual_direction_evidence`(900행 부근)와 `validate_manual_acquisition_handoff`(779행 부근), 그리고 테스트 fixture(`self.stamp = "2026-09-02T22:00:03+00:00"`, test_portfolio_decision_dashboard.py 2740행 부근)다. Read·Grep으로 읽는다.
3. 거짓이 되는 원인을 다음 넷 중 하나로 분류한다. 근거로 파일:행을 단다.
   - TIME: 현재 시각·날짜(`datetime.now`, `date.today`, 만료일, 신선도 한도, 달력 범위 끝)에 따라 결과가 바뀜. 어느 날짜부터 깨지는지 계산 근거를 적는다.
   - EXTERNAL_FILE: git이 추적하지 않는 파일(workspace/outputs/…, 설치 사본, 홈 폴더)을 읽음. 그 경로를 적는다.
   - CODE: 저장소 코드의 실제 회귀. 원인 커밋을 `git log`로 찾는다.
   - UNKNOWN: 읽기와 대상 테스트만으로는 판단이 안 됨. 왜 안 되는지 적는다.
4. (10/29 이전 실패 22·오류 9의 분류는 이 작업에서 하지 않는다. 기준선 기록이 worktree 밖에 있어서다. 사장실 스레드가 따로 맡는다.)
5. 고치는 방법을 **제안만** 한다. 예: 테스트에 고정 시각 주입, fixture 파일을 저장소 안으로 옮기기. 예상 변경 파일도 함께 적는다. 이 작업에서는 고치지 않는다.

## 테스트
- 아래 두 명령을 **글자 그대로** 실행한다. 앞에 환경 변수를 붙이거나 `-B` 같은 옵션을 더하지 않는다. 1차 실행(2026-11-01 14:35 KST)은 `PYTHONDONTWRITEBYTECODE=1 python -B ...` 꼴이라 허용 목록에 걸려 거부됐다. 전체 스위트와 기준선 비교는 파이프라인이 한다.
  - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_evaluate_timing_integration.py"`
  - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_portfolio_decision_dashboard.py"`
- 실패가 많아 출력이 길면, 실패 이름과 단언 첫 줄을 클래스별로 세어 보고서에 적는다. 대표 실패 몇 건은 traceback에서 False가 난 검증 함수 줄(파일:행)까지 따라간다.
- `.claude/` 아래 파일을 불러오는 테스트나 명령은 실행하지 않는다. 그 밖의 셸 작업(`python -c`, 스크립트 직접 실행, 파이프, PowerShell, `head`)은 하지 않는다. git은 `git status`·`git diff`·`git log`만 쓴다.
- 1차 실행이 읽기로 이미 배제한 가설(달력 coverage_end 2026-12-31, artifact 줄바꿈·부재, 검증 경로가 observed_at을 받을 때의 현재 시각 직접 의존)은 다시 보지 않아도 된다. 이번에는 실행 결과로 확정하는 데 집중한다.

## 지켜야 할 것 (어기면 Judge FAIL)
1. 새 파일 `docs/claude/p1-baseline-diag2-report.md` 하나만 만든다. 코드·테스트·다른 문서·기준선 기록은 손대지 않는다. 단언을 약화하거나 skip을 더하는 일은 금지다(builder-rules).
2. 주문·키움·정책·상태·일지·원장·예약 작업과 무관하다. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음.
3. 비밀(.env*, 토큰, 계좌번호)은 읽지 않는다. 설치 사본이나 홈 폴더 경로는 존재·경로만 적고, 내용은 필요한 줄만 인용한다.
4. 판단이 안 되면 UNKNOWN으로 적고 계속한다. 범위를 넘으면 BLOCKED.md를 쓰고 멈춘다.

## 보고 docs/claude/p1-baseline-diag2-report.md
반드시 포함:
(a) 지금 대상 테스트 2개의 결과 마지막 3줄(실행·실패·오류 수)
(b) 실패 클래스별 표: 클래스, 실패 수, 분류(TIME/EXTERNAL_FILE/CODE/UNKNOWN), 근거 파일:행, 깨지기 시작한 날짜(TIME이면)
(c) 생략(사장실 스레드가 따로 맡음)이라고 한 줄
(d) 고치는 방법 제안과 예상 변경 파일. 고치면 기준선 실패가 몇 건으로 줄어들지 추정하고, 모르면 "확인 필요"
(e) CODE로 분류한 것이 있으면 맨 위에 따로 적는다
이 보고서 문장에는 주문·권한 표지 문자열을 적지 말고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 보고서 1개뿐이다.
2. 분류마다 파일:행 근거가 있다. TIME은 날짜 계산 근거가, EXTERNAL_FILE은 경로가 있다.
3. 보고서의 실패 수와 (a)의 테스트 결과가 맞는다.
4. 코드를 고친 흔적이 없다. 제안만 있다.
5. 보고서에 (a)~(e)가 모두 있고, 표지가 없다.

```dev-run
{"task_id": "p1-baseline-diag2", "class": "general", "builder_model": "sonnet", "builder_effort": "high", "max_turns": 90, "builder_timeout_min": 50, "allowed_paths": ["docs/claude/p1-baseline-diag2-report.md"], "target_tests": ["test_evaluate_timing_integration.py", "test_portfolio_decision_dashboard.py"], "commit_message": "docs(claude): p1-baseline-diag report - why the dev-queue baseline failures rose from 22+9 to 276+10 (diagnosis only, no code change)"}
```
