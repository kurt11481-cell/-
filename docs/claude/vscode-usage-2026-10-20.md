---
id: vscode-usage-2026-10-20
type: review
status: 결정 — 기존 도구 유지(사용자 2026-10-20 11:21 KST "기존 도구 사용을 유지 하기로 결정"): 데스크톱 Code 탭·Windows 터미널 그대로, VS Code로 옮기지 않음. 규칙 2(Judge는 claude --permission-mode manual로 시작)는 터미널에도 그대로 적용
as_of: 2026-10-20 11:30 KST
authority: order_authority=false · 정책·상태·예약 작업·설정 변경 없음
consumers: 수동 경로 작업 안내(관제판 devpipe-merge-lock 재개 때) · offsite-bak 첫 push 확인 · 프로젝트 메모리 안내 선호(사용자가 고르면 갱신)
summary: VS Code + GitHub + Claude Code for VS Code(2.1.304) 설치로 운영 간소화는 없고, 개발은 '사람이 직접 하는 개발 일을 한 창에 모으는' 정도의 작은 이득. 지킬 규칙 6개.
---

# VS Code 사용 안내 (2026-10-20)

사용자 질문(11:01): "vscode에 github 연결, claude code for VS code 설치 완료. 이를 통한 개발 및 운영 간소화 가능한가?" 같은 메시지에서 "결정 dual-ai-1020 : Q1 c".

## 결론
1. 운영(매일 자동 루프) 간소화: 없음 — 자동 코어·점검·알림은 Windows 작업과 Cowork 예약 작업이 돌린다.
2. 개발 간소화: 작음 — 일반 변경은 지금처럼 개발 파이프라인(사람 손 = dev-merge 1번)이 더 단순. VS Code 이득은 사람이 직접 하는 일(수동 경로 Builder·Judge, dev-merge·등록 명령)을 저장소가 열린 한 창에서 하는 것(cd 불필요, 세션 탭). 손 수는 그대로.
3. GitHub 연결: 예약 백업 push(offsite-bak)와는 별개 — VS Code의 GitHub 인증은 VS Code가 실행하는 git·내장 터미널 git에만 쓰인다(VS Code github 확장 github.gitAuthentication, git 확장 terminalAuthentication). 예약 push는 Windows 자격 증명 저장소만 쓴다(offsite-bak-builder-prompt.md: GIT_TERMINAL_PROMPT=0, GCM_INTERACTIVE=never). 판정은 첫 밤 push.state.

## VS Code에서 지킬 규칙
1. 수동 경로 Builder는 VS Code 내장 터미널(Ctrl+`)에서 `claude --worktree <이름>` — 채팅 패널에는 worktree 시작 옵션이 없다(code.claude.com/docs/en/worktrees: CLI --worktree·데스크톱 앱 worktree 옵션·세션 중 요청). 이 저장소는 worktree 기준이 현재 HEAD(.claude/settings.json:40 baseRef head).
2. Judge는 VS Code든 Windows 터미널이든 Manual로 시작한다 — 터미널은 `claude --permission-mode manual`, VS Code는 모드 표시에서 Manual. 보고서 1개 쓰기만 승인. (11:2x 추가 확인: 지금까지 Judge 지시문은 '새 세션(메인 체크아웃)'만 적고 시작 모드를 정하지 않아 — r5-align-judge-prompt.md:6, :10 — 터미널 Judge도 Auto로 시작해 왔다. 앞으로 Cowork가 쓰는 Judge 지시문의 실행 권장 줄에 이 시작 명령을 넣는다.) — VS Code·터미널 모두 2.1.283부터 Auto로 시작하고(permission-modes), 프로젝트 설정에 시작 모드 지정이 없다. Plan은 승인하면 편집 모드로 바뀌어 Judge 계약과 맞지 않는다. Manual 선택은 다음 대화로 이어지므로 Builder 시작 때 모드 표시 확인.
3. Source Control의 스테이징(+)·커밋·동기화·Push·Pull을 하나도 쓰지 않는다 — 스테이징만 있어도 23:30 문서 커밋(commit-docs.ps1:24-27 STOP)과 dev-merge(devpipe.py:1918 STOP_MAIN_STAGED)가 멈춘다. VS Code의 자동 상태 갱신 자체는 GIT_OPTIONAL_LOCKS=0이라 잠금을 만들지 않는다(재검토 확인, microsoft/vscode extensions/git).
4. dev-merge 전 `workspace\outputs\dev-runs\_lock`이 없는지 확인(있으면 기다림 — 관제판 devpipe-merge-lock 임시 운영 규칙).
5. 저장소 파일을 손으로 고치거나 저장하지 않는다(CRLF·해시 증거, 자동 저장 기본 켜짐). .env* 같은 비밀 파일을 편집기에 열지 않는다(열린 파일·선택 영역이 메시지에 붙을 수 있음).
6. CLAUDE.md의 "Shift+Tab plan mode"는 VS Code 패널에서는 모드 표시 또는 /plan.

## 영향받는 대기 작업
수동 경로 대기 = devpipe-merge-lock 1건(재개 때 위 규칙 적용). r5-align은 Judge·적용 끝나 해당 없음.

## 사용 범위 재평가 (사용자 질문 11:16 "권한 변경용 Builder·Judge 세션과 병합·등록 명령만 VS Code로 하면 편해지는가?")
- 조금 편해진다, 크지 않다. 10월 기준 수동 경로 Judge 보고 13건·파이프라인 병합 15건(2026-10-20 조회, 파일 시각·커밋 기준 대략). 건당 줄어드는 것은 폴더 이동(cd) 2~3줄과 창 찾기. 사람이 하는 일의 수(세션 시작·지시문 붙여넣기·승인·병합 명령)는 그대로.
- 같은 이득을 새 도구 없이: Cowork가 주는 명령 블록에 cd를 넣어 주는 지금 방식, 또는 Windows 터미널 시작 폴더를 저장소로 지정.
- 판단: 어느 쪽이든 괜찮고, 한 곳만 정해 섞어 쓰지 않는 것이 핵심. VS Code를 고르면 규칙 3(Source Control 버튼 금지)이 추가 부담.

## 바뀔 조건
VS Code 패널에 worktree 시작 옵션이 생기면 1번 갱신 / 첫 밤 push.state가 인증 실패면 VS Code 밖 Windows 터미널에서 git push 1번.

검토 완결: 원문 확인 9/10(GIT_OPTIONAL_LOCKS는 재검토 subagent 확인만, 본 세션 미열람) · 내장 재검토 1회(12건 중 반영 12) · 미해결 0 · 자료 시점 2026-10-20 11:30 KST · 바뀔 조건 위 절
