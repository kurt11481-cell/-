# Builder 보고서: N1·N2 (카드 등록부 문장의 interactive session 범위 명시)

- 지시문: docs/claude/n12-builder-prompt.md (메인 저장소). 사장 승인 "N1·N2 승인" (2026-10-25 09:34Z, 지시문 3행 기재).
- 작업 위치: 워크트리 `.claude/worktrees/n12-scope`, 브랜치 worktree-n12-scope, 기준 커밋 96f1e6a (Merge d6-cleanup).
- 커밋·푸시·병합: 하지 않음.

## 결론
CLAUDE.md Hard safety 절의 마지막 항목에 괄호 구절 "(never a Judge session, scheduled task or subagent)" 하나만 넣었다.
단어는 이것 말고 바뀌지 않았고, 줄 폭(약 120자)을 맞추려고 그 항목의 줄바꿈 위치만 조정했다(2줄 → 3줄).

## 바뀐 줄
전 (CLAUDE.md 42-43행):
```
  invalid record blocks every buy ticket, never sells. An interactive session that changes or accepts a card updates
  docs/claude/card-evidence-registry.json in the same session (otherwise that symbol gets no ticket).
```
후 (CLAUDE.md 42-44행):
```
  invalid record blocks every buy ticket, never sells. An interactive session (never a Judge session, scheduled task
  or subagent) that changes or accepts a card updates docs/claude/card-evidence-registry.json in the same session
  (otherwise that symbol gets no ticket).
```
줄 길이: 116 / 113 / 41자.

## 해시
| 대상 | 전 | 후 |
|---|---|---|
| Hard safety 절 (CR 제거 후 "## Hard safety" ~ "## Kiwoom query rules" 직전) | 4311e88cd19b97c332c7a4d564abb1226a645640f0f1e4a6f65f921db4d448dc (지시문 기대값과 일치) | 93d87a33b42d2a14d030bf4b4431019f0f0f771ef93b364c59a71ed1392173ec |
| CLAUDE.md 파일 (raw bytes sha256) | db863a4ba7e8787eddeb96cc233b0a2d38edd761a4fe1adc5f4aee5184392199 | 901b7e7b88946ea9ba8ba166e796a78def28ae5978e23009d552ec007343e6a5 |

## diff가 이 1곳뿐임을 확인한 방법
1. `git diff --stat`: CLAUDE.md 1개 파일, 3 insertions / 2 deletions (위 2줄 → 3줄).
2. `git diff --word-diff=porcelain CLAUDE.md`: 더해진 토큰은 "(never a Judge session, scheduled task" / "or subagent)"뿐이고 지워진 토큰은 없음.
3. Python 단어 비교: `git show HEAD:CLAUDE.md`와 수정본을 공백으로 나눈 단어 목록에서, 수정본에서 삽입 구절 7단어를 빼면
   원본과 완전히 같음(True). 첫 차이 위치는 "interactive session" 바로 뒤.
4. Hard safety 절 밖의 바이트(CR 제거 후 절 앞·"## Kiwoom query rules"부터 끝까지)는 원본과 같음(True).
5. 줄바꿈: 수정 후 CRLF 126 / LF 126 / 단독 CR 0 (원본 CRLF 125 / LF 125). 일괄 변환 없음, 바이트 단위 치환으로 편집.
6. `git status --short`: ` M CLAUDE.md` 외 변경 없음(이 보고서 파일 추가 전 기준).

## 하지 않은 것
커밋·병합, 다른 Hard safety 문장 변경(매수 차단·매도 비차단 문장 포함 그대로), 권한(주문·한도·예산) 표현 변경, 새 규칙 추가.

## 다음 단계
별도 세션의 읽기 전용 Judge가 이 워크트리의 diff와 이 보고서를 검토한다. 병합은 사장의 결정을 기다린다.
