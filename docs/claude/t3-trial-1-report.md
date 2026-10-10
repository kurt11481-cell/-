# t3-trial-1 보고 (2026-10-10)

- 변경: 테스트 파일 1개 추가 `manage-us-stock-strategy/tests/test_scheduled_prompt_kiwoom_profile.py` (동작·지시문·정책 변경 없음).
- 도우미 단위 테스트 7개: 규칙 줄 있음 통과 · profile만 위반 · mode만 위반 · 두 값이 다른 줄 위반 · kiwoom_query 없음 대상 아님 · 공백 변형 통과 · 다른 profile 값 위반.
- 저장소 검사 1개: docs/claude/scheduled-prompts/ 하위 모든 .txt(9개)를 UTF-8로 읽어 검사. 폴더 없음 또는 kiwoom_query 파일 0개면 실패(fail-closed).
- kiwoom_query가 있어 검사된 지시문 4개: event-pre-open-1014-cpi.txt · integrated-check-daily.txt · us-stock-board-close.txt · watchlist-weekly-rescore.txt. 모두 규칙 준수, 위반 0.
- 대상 테스트 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_scheduled_prompt_kiwoom_profile*.py"`: 8개 실행, 전부 OK.
- 커밋·git add 하지 않음(작업 트리에만 남김).
