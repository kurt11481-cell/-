---
id: ri1-session-builder-prompt
title: "오늘 리서치 기록의 평가 세션이 코어 평가 세션과 다르면 매수 막기 — ri1-session (RI-1)"
date: 2026-11-03
class: "authority(매수 관문을 조이기만 함, 완화 없음). 개발 큐 authority: Builder → Judge → 병합은 사장 결정 + -ApproveAuthority"
source: "사장 결정 카드 '셋 다 진행'(카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9NQaebhrHGyYfpP6G8BQFus, 질문 '남은 작은 수정 3건을 어떻게 진행할까요?', 2026-11-03 21:48:48 KST, 계정=사장). 근거 docs/claude/code-review-core-2026-11-01.md 3차 RI-1"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 목표
auto_core_inputs.check_record는 오늘 리서치 기록의 날짜, 달력, 작성 시각을 검사한다. 그러나 기록에 적힌 evaluation_session이 decide가 계산한 평가 세션(auto_core_decide.py 522행 `expected_completed_session`)과 같은지는 보지 않는다. 그래서 작성 도구가 지난 세션을 적으면, 지난 세션의 실적 일정과 공식 사실이 오늘 것으로 쓰인다.
이것을 "다르면 오늘 기록 INVALID"로 바꾼다. 오늘 기록이 INVALID면 이미 있는 규칙대로 매수만 막히고, 매도는 그대로다(CLAUDE.md 47~50행).

## 바꿀 파일 (이 3개만)
- manage-us-stock-strategy/scripts/auto_core_decide.py
- manage-us-stock-strategy/tests/test_auto_core_decide.py
- docs/claude/ri1-session-report.md (보고)

## 구현 요구
1. auto_core_decide.py에서 `inputs.load_research(...)`를 부른 바로 뒤(지금 597~599행 부근)에 아래를 넣는다. 오늘 기록 상태가 "OK"이고 `today_record["evaluation_session"] != evaluation_session`이면 today_record를 새 dict로 바꾼다. 원본 dict는 고치지 않는다. 새 dict의 값은 다음과 같다.
   - status = "INVALID"
   - reasons = ["RESEARCH_RECORD_SESSION_MISMATCH"]
   - facts = []
   - earnings = None
   - integrated_check_run = None
   - 그 밖의 키(dropped·evaluation_session·written_at·record_day_kst)는 그대로 둔다.
2. 그 뒤의 research_ok·facts·research_block·inputs.research_record·earnings·compare 호출이 모두 이 바뀐 today_record를 쓰게 한다. 같은 함수 안의 지역 변수 하나만 바꾸면 된다.
3. auto_core_inputs.py·load_research·check_record는 바꾸지 않는다. R-REC1 window의 sessions·damage 계산도 바꾸지 않는다.
4. 결과 JSON의 필드 이름이나 필드 수를 늘리지 않는다. 새 사유 문자열 하나만 더해진다. 그 값은 기존 `RESEARCH_RECORD_NOT_OK:<reason>` 경로로 나간다.
5. 매도 쪽 판정, 노출, 원장, 일지 쓰기 코드는 건드리지 않는다.

## 시험 (test_auto_core_decide.py)
- 새 시험 1개를 더한다. 오늘 기록의 evaluation_session을 평가 세션의 바로 전 세션으로 적고(작성 시각은 유효 범위 안), decide를 돌린다. 그리고 아래를 단언한다.
  - (가) `decision["inputs"]["research_record"]["status"] == "INVALID"`
  - (나) reasons에 RESEARCH_RECORD_SESSION_MISMATCH가 있다.
  - (다) 매수 티켓 사유에 `RESEARCH_RECORD_NOT_OK:RESEARCH_RECORD_SESSION_MISMATCH`가 있다(505~516행 방식).
  - (라) 매도 판정이 같은 입력의 정상 기록 때와 같다. 판단이 어려우면 매도 티켓 목록 비교로 한다.
- 기존 505~516행 cases 묶음에 넣어도 된다. 다른 시험과 단언은 바꾸지 않는다. skip은 넣지 않는다.
- 실행 명령은 이 한 줄만, 글자 그대로 쓴다: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"`
- 앞에 환경 변수나 옵션을 붙이지 않는다. 전체 스위트는 파이프라인이 한다. git은 status·diff·log만 쓴다. `python -c`·PowerShell·파이프는 쓰지 않는다.

## 지켜야 할 것
1. 위 3개 파일 밖은 손대지 않는다. 줄바꿈은 지금 그대로 지킨다(세 파일 모두 i/lf).
2. 매수 관문을 조이기만 한다. 다른 검사를 풀지 않는다.
3. 주문·키움·일지·원장·예약과 무관하다. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음. 비밀(.env*·토큰·계좌번호)을 읽지 않는다.
4. 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/ri1-session-report.md
- (a) 바꾼 줄(파일:행)
- (b) 새 시험 이름과 단언 4개
- (c) 시험 결과 마지막 3줄
- (d) 운영 기록 영향: workspace/outputs/research-records 최근 기록들의 evaluation_session이 그날 평가 세션과 같아 이 수정으로 막혔을 날이 없는지 읽어서 확인(읽기만, 날짜만 적음)

수량·금액은 적지 않는다. 주문·권한 표지 문자열도 적지 않고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 허용 파일 3개뿐이다.
2. 비교는 오늘 기록이 OK일 때만 걸리고, 기록 없음·INVALID 경로는 그대로다.
3. 바뀐 today_record가 research_ok·facts·earnings·compare에 모두 쓰인다(옛 dict가 새는 곳 없음).
4. 매도 판정·R-REC1 window·결과 필드 목록이 바뀌지 않았다.
5. 새 시험이 실제로 불일치를 만들고 4개 단언을 한다(항상 참 단언 아님). 기존 단언·skip 변경 없음.
6. 새 실패 0(파이프라인 checks).
7. 보고서 (a)~(d) 있음, 수량·금액·표지 없음.

```dev-run
{"task_id": "ri1-session", "class": "authority", "builder_model": "sonnet", "builder_effort": "high", "max_turns": 80, "builder_timeout_min": 45, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_decide.py", "manage-us-stock-strategy/tests/test_auto_core_decide.py", "docs/claude/ri1-session-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core): block buys when today's research record names another evaluation session (ri1-session)"}
```
