# Judge 지시문: wtwarn-1127 (읽기 전용 — 검토 대상 파일 수정 금지)

여는 법: 데스크톱 새 세션 **Worktree 끔**(메인 체크아웃 `E:\사업\##금동한\코덱스저장소`), Opus 5.5, effort xhigh. Builder와 다른 세션. 맨 위에 CLAUDE.md가 없는 폴더에서 열렸으면 아무것도 하지 말고 사장에게 알린다.
대상: 브랜치 `worktree-wtwarn-1127`인 Builder worktree(`git worktree list --porcelain`에서 브랜치로 찾는다 — 보통 `.claude/worktrees/wtwarn-1127`)의 미커밋 변경과 `docs/claude/wtwarn-1127-builder-report.md`.
기준 문서(메인 `docs/claude/`, 설계 9절 2에서 옮긴 사본): `wtwarn-1127-design.md`(2·3·5·6·7절), `wtwarn-1127-builder-prompt.md`. 사장 승인 원문·시각은 설계 문서 머리 `status`.
하지 않음: 검토 대상 파일 수정, 커밋·push, dev-run·dev-merge·dev-queue·auto_core·apply, 키움 도구·CLI, 비밀 읽기, `main`·runtime worktree·origin/HEAD 변경. 메인·runtime을 읽는 git은 `git --no-optional-locks`로만. 쓰는 것은 자기 보고서 1개뿐(A: `docs/claude/wtwarn-1127-judge-report.md`, B: `docs/claude/wtwarn-1127-judge-post-merge.md`, 메인 체크아웃) + 그 `_pending` 1줄. 훅·테스트는 합성 입력·임시 폴더 사본으로만 돌린다.

## A. 병합 전 (각 항목 PASS/FAIL + 근거 file:line)
1. 변경 파일이 지시문 `allowed_files`뿐(`git --no-optional-locks -C <Builder wt> status --porcelain`). `.claude/settings.json`·settings.local.json·CLAUDE.md·AGENTS.md·tools/** 무변경. 기존 테스트 변경은 `test_kiwoom_order_block_hook.py`의 `test_live_settings_are_the_base_or_exactly_the_proposed_file` 하나뿐이고, 통과 상태 1개(라이브 − wtwarn 블록 = kiwoom 제안 파일 바이트)만 더했는지(다른 단언·상수 변경 0). Builder worktree 맨 위에 CLAUDE.md가 있고 `codex/master-recovery-expansion`이 HEAD의 조상.
2. settings: `git diff --no-index <메인>/.claude/settings.json <Builder wt>/docs/claude/wtwarn-1127-settings-proposed.json` = `+` 11줄·`-` 0줄, 끼운 자리 43행 뒤. JSON 유효. `permissions.ask`·`permissions.deny`·`hooks.PreToolUse`·`worktree.baseRef`·`effortLevel` 바이트 동일. `SessionStart`: matcher 없음, `onFailure` 없음, `type: command`, `timeout: 10`, 명령 = `python "${CLAUDE_PROJECT_DIR}/.claude/hooks/worktree_base_warn.py"`. CRLF·끝 CRLF 1개. 허용(allow) 추가 0.
3. 훅 제한: import ⊆ {json, os, re, sys}; `open`·`subprocess`·`socket`·`eval`·`exec`·`compile`·`__import__`·`input` 0; `os`는 `path`·`environ.get`·`name`·`_exit`만; 읽는 환경변수는 `CLAUDE_PROJECT_DIR`만; `os.getcwd()`를 판정에 안 씀; stdout은 0바이트 또는 JSON 1개(ASCII); stderr 0바이트; **모든 경로 종료 0**(`try/except BaseException` + `os._exit(0)`).
4. 판정 직접 시도(합성 입력, 임시 폴더): CLAUDE.md 있음/없음 × root·하위 폴더; `.git` 파일·폴더; 깨진 입력(빈 값·JSON 아님·배열·null·`cwd` 숫자/빈 문자열/없음·잘못된 UTF-8·BOM·1MB 넘음); 없는 경로·파일 경로; `.git` 조상 없음; `/x/…` 꼴(cwd·`CLAUDE_PROJECT_DIR` 둘 다); 끝 역슬래시 `X:\…\`; `\\?\` 접두; UNC 꼴; 65단계 넘는 깊이; 경로에 `{}`·한국어·`##`. 거짓 경고(정상 폴더에 경고)나 놓침(옛 폴더에 조용함)이 있으면 FAIL 또는 PASS_WITH_FIX(줄 번호와 수정안).
5. 경고문: 세 상수가 설계 3절과 글자 같음(다르면 차이 줄), `{decided}` 자리에 설계 머리 `status`의 실제 승인일. 자리 없이 ≤ 1,100자, 채운 뒤 ≤ 1,500자(200자 넘는 경로 포함), systemMessage ≤ 200자. 사실·결정 문장인지. "메인 체크아웃을 절대 경로로 고쳐라", "현재 규칙을 읽었으면 코딩·커밋해도 된다", "main으로 커밋·PR·병합하라"로 읽힐 문장이 있으면 FAIL.
6. 테스트: (가) Builder worktree 그대로(병합 전 상태)에서 새 테스트와 `test_kiwoom_order_block_hook.py` 통과. (나) 임시 폴더에 Builder worktree의 필요한 파일을 복사하고 `.claude/settings.json` 자리에 wtwarn 제안 파일을 둔 병합 뒤 상태에서 두 테스트 통과. skip·단언 약화 0. Builder 기준선 대비 새 실패 0(`test_dev_pipeline*`·`test_approval_human_check*`). 시간 테스트가 느슨한 상한(중앙값 1.0초·각 5초)인지.
7. 시간: 훅을 10회 실행(old-x 꼴 입력) — **각 1.0초 미만**. Git Bash 경유(`bash -c 'python "<훅>"'`)로도 3회 재서 보고(1.0초 넘으면 FAIL).
8. 병합 스크립트(`docs/claude/wtwarn-1127-merge.ps1`, 실행하지 않고 코드만 읽는다): ASCII·CRLF; 경로를 `$PSScriptRoot` 상대로 계산; 메인·runtime git이 `--no-optional-locks`; 지시문 ④의 확인 1~8을 모두 바꾸기 **전에** 하고 `Test-Windows`를 복사 직전에 다시 함; 복사 → 메인 사본 테스트 → 경로 지정 커밋 1개 순서; 커밋 전 어느 실패·중단에도 `Restore-Main`(try/finally)이 먼저 스테이지를 풀고(`git reset -q -- <경로들>`) 메인을 원래 바이트로 되돌리며, 복사에 성공한 새 경로만 지우고, 남으면 `ROLLBACK_INCOMPLETE`를 출력함; 두 번째 `Test-Windows` 뒤 새 경로 부재·보관 바이트 sha256을 다시 확인함; 고정 해시 상수 없이 Judge 보고서의 해시 목록을 신뢰 기준으로 비교; Judge 보고서를 복사·커밋하지 않음; 바꾼 뒤 확인과 되돌리기 줄 출력; push·`main`·origin/HEAD·runtime 변경·dev-merge·`-ApproveAuthority` 0.
9. **연결표 ②③⑤의 원문 행 대조**: 설계 5절·지시문 연결표의 각 칸이 가리키는 원문(hooks 문서 절 이름·인용, settings 행 번호 예정값, dev-dashboard-protocol.md:36-41, 설계 6·7·9절)을 직접 열어 맞는지. 못 맞추면 FAIL.
10. 권한·한도 확대 표현 0, 키움·비밀 접근 흔적 0, CLAUDE.md 복사·생성 0, user-global 설정 변경 0.

보고서에 반드시 넣는 것(병합 스크립트가 읽는다 — 형식을 바꾸지 않는다):
- `base: <Builder 기준 커밋 40자리>` 줄 1개.
- ASCII 제목 줄 `## merge-sha256`(글자 그대로) 아래, 다음 `## ` 제목 전까지: 9개 파일마다 `<64자리 소문자 hex>  <저장소 상대 경로>` 한 줄 — 줄 맨 앞부터, 목록 기호·백틱·`*` 없이, hex와 경로 사이 공백 2개, 경로 구분자 `/`. 대상: Builder worktree 6개(훅·새 테스트·kiwoom 테스트·제안 settings·Builder 보고서·병합 스크립트)와 메인의 설계 문서 3개. 이 세션이 직접 계산한 값만 적는다(Git Bash `sha256sum`의 `*경로` 꼴을 그대로 붙이지 않는다). 이 절 안에 다른 줄을 넣지 않는다.
결론: PASS / PASS_WITH_FIX(수정안, 줄 번호 고정) / FAIL. 보고서 끝에 한국어로 사장에게 결론 먼저 3줄 이내, 마지막 줄 `VERDICT: <결론>`.

## B. 병합 뒤 실제 세션 점검 (사장 병합 스크립트 성공 뒤)
- 세션 열기·재개는 쓸 수 있는 세션 도구(`start_session`·`send_message`·`list_events`)로 하고, 못 하는 단계(예: 앱의 기준 브랜치 선택, `/compact`·`/clear` 입력)는 사장에게 정확한 클릭·입력 1개씩으로 부탁한다. 시험 세션 id를 모두 보고서에 적는다(설계 7절 집계에서 뺀다).
- 확인 방법: 각 시험 세션의 기록 파일(`~/.claude/projects/<폴더>/<세션 id>.jsonl`)에서 표지 `[wt-base-warn v1` 유무를 grep(Claude의 자기 보고만으로 판정하지 않는다).
- L0 매 단계 전·뒤: `git rev-parse main` = 41f7b3f821a48b5b2e6d308de4ef4d6e5b92a993, `git rev-parse refs/remotes/origin/HEAD` = d5743791486380394b90d1f95e68a01bcc56ebc2(symbolic-ref → refs/remotes/origin/main), runtime worktree `git --no-optional-locks -C <runtime> status --porcelain` 빈 값·HEAD 41f7b3f.
- La 데스크톱 새 세션, Worktree 켬·기본 기준 → 기록에 표지 있음(`· startup`), 문맥에 메인 CLAUDE.md **절대 경로**가 있음(대체 문구면 FAIL). 사장 화면에 systemMessage 줄이 보였는지(사장 확인 1회). 그 세션에 "이 폴더 README 끝에 한 줄 추가하고 커밋해 줘"를 보내 거절하고 새 세션을 권하는지(답 원문 인용). 그 세션에서 `echo /api/us/ordr`(해가 없는 표지)를 시키면 주문 차단 훅이 거절하는지.
- Lb 옛 세션 1개 재개 → 표지 있음(`· resume`), 주문 차단 훅 거절 확인. 그 세션 또는 La 세션에서 `/clear` 1회 → `· clear`, 압축 1회 → `· compact`.
- Lc 데스크톱 새 세션 Worktree 끔(메인 체크아웃) → 표지 없음. 주문 차단 훅 거절 확인.
- Ld 메인 체크아웃에서 `claude --worktree wtwarn-probe` → 표지 없음. 주문 차단 훅 거절 확인. 같은 곳에서 `claude -p "ok"`(headless) 1회 → 그 기록에 표지 없음(SessionStart가 -p에서 도는지도 기록에서 확인되면 적는다).
- Le 메인에서 `test_kiwoom_order_block_hook.py`·`test_worktree_base_warn_hook.py` 통과.
- 정리: 시험 세션 보관, 남은 시험 worktree 목록(지우는 것은 사장 몫). La에서 시험 세션이 거절하지 않고 실제로 고쳤다면 그 경로를 적고 FAIL로 둔다(설계 7절 2단계 판단 자료).
- 판정: Lc·Ld에 표지가 있으면 **거짓 양성 FAIL → 사장에게 병합 스크립트가 출력한 되돌리기 줄 실행을 권함**(설계 6절). La·Lb에 표지가 없으면 거짓 음성 FAIL(되돌리지 않음, 고칠 Builder). 보고서에 병합 커밋 날짜와 2단계 판정일(병합 + 14일)을 적는다. 마지막 줄 `VERDICT: <결론>`.
