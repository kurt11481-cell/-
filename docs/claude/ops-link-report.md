---
id: ops-link-report
title: "ops-link-1107 A — Builder 보고 (K3 수동 경로)"
date: 2026-11-07
source: "docs/claude/ops-link-builder-prompt.md (본 저장소 메인 체크아웃)"
authority: "주문 권한 없음 · 수량 권한 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 선행 조건
- 본 저장소 원본 docs/claude/ops-linkage-guideline-2026-11-07.md 191행에 "사장 결정 2026-11-07 12:01:27 KST" 줄 있음.
- 메인 체크아웃 4개 파일 sha256 = 지시문 '바꾸기 전' 값과 모두 일치(아래 (b) '전' 칸과 같음).

## (a) 기준
- 기준 커밋: 85707c662e34eedf9ebf1cc97b030519f184ef85 (시작 때 메인 HEAD, 브랜치 codex/master-recovery-expansion)
- worktree: E:\사업\##금동한\코덱스저장소\.claude\worktrees\ops-link
- 브랜치: worktree-ops-link

## (b) 네 파일 sha256 · 줄 수 · CRLF

| 파일 | 전 sha256 | 뒤 sha256(잰 값) | 목표 일치 | 줄 수 | `\r\n` 수 = `\n` 수 |
|---|---|---|---|---|---|
| CLAUDE.md | fcf6d25bc6e5888a133eedc7a4d039fe4821b5a86d02ae73e319d381100c27b2 | fa55fb196ee659fd5d7b54e1ed956766f172cf131b19aec10f34cdeb332f1673 | 일치 | 138 → 138 | 138 = 138 |
| tools/dev_pipeline/judge-prompt.md | 877d34e27335bdc678e8ba2e707bca86bc913ec491cd7b216129c3c586632b6d | 768ee9aa82f6a67cabee9cb8074a3ad973c47a8ba607e81c5adaf78461b463c0 | 일치 | 38 → 39 | 39 = 39 |
| tools/dev_pipeline/README.md | 5601c19a4ead5d41b861c69b83dfa129e7c7f3297e1b3eae6ec5d5a60db74b1d | 103a55cf2773787780884ce8eddfa54c412170211003553507b18969591cfa26 | 일치 | 94 → 94 | 94 = 94 |
| manage-us-stock-strategy/tests/test_dev_pipeline.py | 5ec97a391eed25aa8e1bf956d17513cc7b259bc8278077ef8957eed4be994a47 | daa31643a922748d58dca6d2f3451e60faf53d6b825316c24941206a29b6ae8a | 일치 | 1918 → 1924 | 1924 = 1924 |

방법: python `open(p,'rb')` → `split(b'\n')` → 해당 줄 교체/삽입(새 줄 끝 `b'\r'`) → `b'\n'.join` 쓰기. 텍스트 모드·편집기 사용 없음.

## (c) CLAUDE.md Hard safety 18~53행 해시
- 전: 56db42e87ed8f99d385d1243264ce53035cb4bd73c9e6a8d95a0ddd88ff53057
- 뒤: 56db42e87ed8f99d385d1243264ce53035cb4bd73c9e6a8d95a0ddd88ff53057 (같음)

## (d) git diff
```
 CLAUDE.md                                           | 2 +-
 manage-us-stock-strategy/tests/test_dev_pipeline.py | 6 ++++++
 tools/dev_pipeline/README.md                        | 2 +-
 tools/dev_pipeline/judge-prompt.md                  | 1 +
 4 files changed, 9 insertions(+), 2 deletions(-)
```
`git diff -U0` 바뀐 줄:
- CLAUDE.md `@@ -111 +111 @@`
- manage-us-stock-strategy/tests/test_dev_pipeline.py `@@ -1690,0 +1691,6 @@`
- tools/dev_pipeline/README.md `@@ -18 +18 @@`
- tools/dev_pipeline/judge-prompt.md `@@ -24,0 +25 @@`

## (e) 시험
명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"` (종료 코드 0)
```
Ran 152 tests in 155.729s

OK
```

## (f) git status --short
```
 M CLAUDE.md
 M manage-us-stock-strategy/tests/test_dev_pipeline.py
 M tools/dev_pipeline/README.md
 M tools/dev_pipeline/judge-prompt.md
?? docs/claude/ops-link-report.md
```

## 하지 않은 것
- commit·push·merge·reset 없음. 5개 밖 tracked 파일 변경 없음.
- 주문·키움·일지·원장·예약·정책·상태 무관. auto_core.py·kiwoomcli 실행 없음. 비밀 파일 읽지 않음. 표지 없음.

## 다음
- 별도 읽기 전용 Judge: docs/claude/ops-link-judge-prompt.md (본 저장소).
- 병합은 사장 PowerShell 한 줄(K3 수동 경로).

## (g) 2차 수정 (2026-11-07 12:3x KST, 사장실 스레드 세션)
- 헌법 1.5.0 독립 재검토(검토자 2 발견 10·11)에 따라 지시문 docs/claude/ops-link-builder-prompt.md를 2차로 고쳤고(개정 기록 절), 이 worktree의 CLAUDE.md 111행 한 줄만 바이트 치환으로 바꿨다. 다른 세 파일과 시험은 그대로다.
- CLAUDE.md sha256: fa55fb196ee659fd5d7b54e1ed956766f172cf131b19aec10f34cdeb332f1673(1차) → d2f22333b02712d64303ff6348941018b9dbae1536d17a4998e1048003ca4cfc(2차, 지시문 목표와 같음). 줄 수 138, CRLF 유지(\r\n 수 = \n 수).
- Hard safety 18~53행: 56db42e87ed8f99d385d1243264ce53035cb4bd73c9e6a8d95a0ddd88ff53057(변경 없음).
- 머리말 authority 줄의 표지 문자열은 1차 Judge 항목 8 지적으로 일반어로 바꿨다(표지 없음).
