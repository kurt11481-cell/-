VERDICT: PASS

# ic-rules-1103 마지막 대조 (2026-11-03 KST, 읽기 전용)

> 보관 메모(2026-11-03 KST): 마지막 대조 세션이 worktree(.claude/worktrees/epic-dijkstra-852359)에 쓴 원본을 그대로 옮김. 계좌 금액 없음 확인. 참고 ①은 작성자가 재확인 판(76d0fb53…) 사본과 diff해 1·161행만 바뀐 것을 확인함.

기준: docs/claude/ic-rules-1103-recheck-report.md 끝 "결론을 바꿀 조건" — 조건 1·2를 반영한 수정본이 161행과 1행 머리 밖을 건드리지 않고 해시가 맞으면 PASS. 세 항목 모두 맞았다.
대조 대상은 본 저장소(E:\사업\##금동한\코덱스저장소, 브랜치 codex/master-recovery-expansion)의 파일이다. 본 저장소에는 쓰기가 막혀 이 보고만 worktree에 둔다.

## 1. 바뀐 줄
- 규칙 파일: `diff integrated-check-prompt-v3.12.11-2026-11-02.txt integrated-check-prompt-v3.12.12-2026-11-03.txt` → 1c1, 102c102, 124c124, 134c134, 161c161, 170c170. 6줄뿐이다. 기대와 같다.
- 지시문: `diff scheduled-prompts/integrated-check-daily.txt scheduled-prompts/pending-ic-rules-1103/integrated-check-daily.txt` → 1c1, 4c4, 12c12, 18c18, 88c88. 5줄뿐이다. 기대와 같다.
- 지금 만든 규칙 diff는 pending-ic-rules-1103/rules.diff와 바이트까지 같다(`diff -q` 출력 없음).

## 2. 161행 반영 (원문 인용)
- 조건 1(직전 기록 없음):「직전 기록이 없거나 못 읽은 날에는 (v)의 "더 깊은 선 처음 이탈"과 (vii) ㉮㉯㉰의 "새로"를 새로 생긴 것으로 본다 — 지금 이탈한 가장 깊은 선과 지금 성립 중인 ㉮㉯㉰(미해제 RG1 훼손 포함)를 결정 필요에 올리고 끝에 "(직전 기록 없음, 중복일 수 있음)"을 붙인다(332행 알림 억제 규칙과 같은 방향).」 → 뜻대로 들어갔다.
- 조건 2(미해제 RG1 0줄 문구):「(풀리지 않은 RG1 공식 테제 훼손이 이어지는 종목은 "RG1 훼손 미해제 — 카드 재수락 대기(매수 ⑤ 막힘)"으로 적는다)」 → 뜻대로 들어갔다. 기본 문구 "… RG1 훼손 새로 없음, 카드 그대로"는 그 바로 앞 (vii) 본문에 그대로 남아 있다. 괄호 문장이 미해제 종목에 대한 예외로 읽힌다.
- 1행 머리에도 "재확인 조건 2건 반영(docs/claude/ic-rules-1103-recheck-report.md): 직전 기록이 없으면 "새로"로 봄 · 미해제 RG1 훼손 0줄 문구"가 있다.

## 3. 해시
- 규칙 파일: 118112 bytes, LF 정규화 sha256 = 3cf70cfa9d3d407800f98c655b1773330bda0245d54f9a2f9bf8f7bd0092fde6 → 맞음.
- 지시문(pending) 바이트 sha256 = 07731460749729348ffeb9f31baeeb13a5d353f1293233eba0edc98863744bfe → 맞음.
- 지시문 18행 비교값 = 3cf70cfa…92fde6 → 규칙 파일 해시와 같다.
- 지시문 1단계 python을 원문대로 실행했다. 경로만 E:/사업/##금동한/코덱스저장소/... 로 바꿨고, 파일은 만들지 않았다. 출력: `RULES 118112 bytes sha256(LF 정규화) 3cf70cfa…92fde6 MATCH`.

## 참고 (FAIL 아님, 새 조건 아님)
- 재확인 때 본 판(76d0fb53…, 117405 bytes)의 사본이 없다. 그래서 102·124·134·170행이 그 판과 같은지는 바이트로 대조하지 못했다. 다만 v3.12.11 대비 바뀐 줄 집합이 그대로라서 161행 밖에서 늘어난 줄은 없다.
- "(직전 기록 없음)" 날에 올리는 항목이 (a)의 "최대 4개"를 넘을 수 있다. 넘칠 때 어느 것을 먼저 올릴지는 정해져 있지 않다.
- 규칙 파일과 pending 폴더는 아직 미커밋이다(git status `??`). docs/claude/_pending/ic-rules-1103.txt 목록에는 들어 있다. 재확인 조건 3(커밋 뒤 update_trigger 응답 해시 대조)은 그대로 남아 있다.

## 읽은 것
- ic-rules-1103-recheck-report.md 끝 30줄
- 규칙 파일 1·161행과 diff
- pending 지시문 1~30행과 diff
- rules.diff
- _pending/ic-rules-1103.txt
- 비밀·계좌 파일은 읽지 않음
