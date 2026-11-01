# Judge 지시문: constitution-protect (읽기 전용, Opus, K3)

파일을 고치지 않는다(보고서도 쓰지 않는다). 워크트리 `.claude/worktrees/constitution-protect`의 변경을 Builder 시작 HEAD와 비교해 판정한다.

읽을 것: 이 지시문, docs/claude/constitution-protect-builder-prompt.md, docs/claude/constitution-protect-builder-report.md, `git -C .claude/worktrees/constitution-protect diff`, tools/dev_pipeline/devpipe.py(glob_to_regex 337행, parse_authority_patterns 355행, authority 판정에서 base의 목록을 읽는 1485·1932행 근처, 보호 경로 102-120행), manage-us-stock-strategy/tests/test_dev_pipeline.py 1450-1490행, tools/commit-docs.ps1.

판정 항목(각 PASS / PASS_WITH_FIX / FAIL + 근거 파일:행):
1. 범위: 바뀐 파일이 authority-paths.txt 하나이고, 추가는 끝의 3행(빈 행·주석·패턴)뿐인가. 기존 65행 바이트 불변, CRLF·ASCII 유지.
2. 효과: 패턴 `docs/claude/constitution-v*.md`가 constitution-v1.3.0-readonly-copy.md·constitution-v1.4.0.md(본 저장소에 아직 미커밋 사본 있음)와 앞으로의 constitution-v*.md에 맞고, docs/claude의 다른 파일(예: top-guideline-review-2026-11-01.md, active-decisions.md, _pending/*.txt, 하위 폴더 파일)에는 맞지 않는가.
3. 범위 설명이 맞는가: 이 줄이 바꾸는 것은 개발 큐 작업이 헌법 파일을 건드릴 때 NEEDS_APPROVAL로 끝나는 것뿐이고, Cowork·스레드의 문서 쓰기와 23:30 문서 자동 커밋(commit-docs.ps1)은 바뀌지 않는다.
4. 부작용: 대기 중이거나 앞으로의 개발 큐 판정, 기존 테스트가 이 줄로 깨지는 곳이 있는가. 워크트리 안에서 직접 실행해도 된다: `python -B -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py" -k authority_paths`.
5. 권한: 이 변경이 권한·한도를 넓히지 않는가(목록에 넣기만 하므로 더 엄격해지는 쪽인가).

회신: 한국어 판정 표와 수정안. 마지막 줄은 정확히 `VERDICT: PASS`, `VERDICT: PASS_WITH_FIX`, `VERDICT: FAIL` 중 하나. 기록은 사장실 스레드가 docs/claude/constitution-protect-judge-report.md로 옮긴다.
