---
id: t3-trial-prompt-profile-test-builder-prompt
title: 파이프라인 첫 시험 — 예약 지시문 키움 조회 규칙(실전계좌·real) 검사 테스트
date: 2026-10-10
class: 일반 변경(테스트만 추가, 동작 변경 없음) — 재설계 T3 dev 파이프라인 첫 시험(관제판 redesign-t3 완료 기준)
rule: CLAUDE.md "Kiwoom query rules" (사용자 상시 규칙 2026-10-07) — 모든 kiwoom_query는 options에 "profile": "실전계좌", "mode": "real"
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: 전체 테스트 스위트(예약 지시문을 바꿀 때마다 규칙 누락을 잡음) · docs/claude/analysis-linkage-map-2026-10-05.md 점검 목록 · 관제판 redesign-t3
---

```dev-run
{"task_id": "t3-trial-prompt-profile-test", "class": "general", "builder_model": "sonnet", "builder_effort": "medium", "max_turns": 40, "builder_timeout_min": 30, "allowed_paths": ["manage-us-stock-strategy/tests/test_scheduled_prompt_kiwoom_profile.py", "docs/claude/t3-trial-prompt-profile-test-report.md"], "target_tests": ["test_scheduled_prompt_kiwoom_profile*.py"], "commit_message": "test: scheduled prompts that call kiwoom_query must state profile and real mode"}
```

## 목표
예약 작업 지시문(docs/claude/scheduled-prompts/ 아래 .txt)이 키움 조회 규칙을 빠뜨리면 테스트가 실패하게 한다. 지금은 사람이 눈으로만 확인한다. 코드·지시문·정책은 바꾸지 않는다(테스트 파일 1개 + 보고 1개).

## 바꿀 내용
새 파일 `manage-us-stock-strategy/tests/test_scheduled_prompt_kiwoom_profile.py` (unittest, 표준 라이브러리만):
1. 도우미 함수(테스트 파일 안): 글 하나를 받아, 글에 `kiwoom_query`가 있으면 한 줄 안에 `"profile"\s*:\s*"실전계좌"`와 `"mode"\s*:\s*"real"`이 함께 있는 줄이 하나 이상 있는지 본다. 없으면 위반. `kiwoom_query`가 없는 글은 검사 대상 아님.
2. 저장소 검사: 저장소 루트 기준 `docs/claude/scheduled-prompts/` 아래 모든 `.txt`(하위 폴더 포함)를 UTF-8로 읽어 도우미로 검사 → 위반 파일 0. 폴더가 없거나 `kiwoom_query`가 있는 파일이 1개도 없으면 실패(fail-closed — 폴더가 옮겨져 검사가 조용히 비는 것을 막는다). 저장소 루트는 다른 테스트처럼 이 파일 위치에서 계산한다.
3. 도우미 단위 테스트(합성 문자열): 규칙 줄이 있음 → 통과 · profile만 있음 → 위반 · mode만 있음 → 위반 · 두 값이 다른 줄에 나뉨 → 위반 · kiwoom_query 없음 → 대상 아님 · 공백 변형(`"profile":"실전계좌"`) → 통과.
- 테스트 파일 안에 주문 관련 이름(주문 API 경로·주문 도구 이름)을 쓰지 않는다. 파일을 고치거나 만들지 않는다(읽기만).

## 테스트
- 대상: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_scheduled_prompt_kiwoom_profile*.py"` → 전부 OK(지금 저장소의 지시문 4개는 규칙을 지키고 있어야 한다. 위반이 나오면 지시문을 고치지 말고 BLOCKED.md에 파일 이름을 적고 멈춘다).

## 보고
`docs/claude/t3-trial-prompt-profile-test-report.md`(한국어, 10줄 안팎): 만든 테스트 목록, 검사한 지시문 파일 수와 이름, 대상 테스트 결과.

## Judge 확인 항목
- J-a 테스트만 추가했고 다른 파일 변경이 없는가.
- J-b 도우미가 "같은 줄에 두 값" 조건을 정확히 보고(다른 줄에 나뉘면 위반), 검사 대상이 0개면 실패하는가(fail-closed).
- J-c 실제 저장소 검사가 docs/claude/scheduled-prompts 하위 폴더까지 보고 UTF-8로 읽는가. 파일을 쓰지 않는가.
- J-d 테스트 이름·내용이 CLAUDE.md "Kiwoom query rules"와 맞는가(규칙을 약하게 바꿔 적지 않았는가).
