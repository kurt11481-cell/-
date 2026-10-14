---
id: claude-md-design-rule-report
title: CLAUDE.md 화면 디자인 유지 규칙 한 줄 추가 — Builder 보고
date: 2026-10-14
prompt: docs/claude/claude-md-design-rule-builder-prompt.md (원본 체크아웃에 있음, 아직 커밋 전)
class: 문구만(old K0), 수동 경로(CLAUDE.md는 파이프라인 보호 경로). Judge는 별도 세션
authority: 없음. 정책·상태·예약 작업·키움 호출·테스트 실행 없음
---

## 결과

- 바꾸기 전 CLAUDE.md: sha256 `c4146cbb79fadce7283c73a5bbfaedb66fbeb86e1510282672d3389e3e55c589`, 117줄 (지시문 base와 일치 → 진행)
- 바꾼 뒤 CLAUDE.md: sha256 `ef0557878d7735623152eb43274885b0c156d534b21b7d372d553fd56fe529ce`, 118줄
- 위치: 97행 `- Doc-only commits (...)` 바로 다음 = 새 98행, 그 뒤 빈 줄과 `## Session hygiene` (100행) 유지

## git diff --stat (CLAUDE.md)

```
 CLAUDE.md | 1 +
 1 file changed, 1 insertion(+)
```

## 추가된 줄 원문

```
- Artifact page design (user 2026-10-14): before editing or republishing the HTML of 미국주식 현황판, 개발 관제판 or 통합점검, read the live version and keep the 투자_V2 design-system colors, type and touch sizes in docs/claude/artifact-design-rules-2026-10-14.md. Display only: no data, rule or authority change; the 통합점검 order panel keeps Kiwoom buy red / sell blue (--buy/--sell), separate from price up green / down red.
```

## 줄 끝 확인

- 바이트 계산: `\r\n` 118개 = `\n` 118개 → 전 줄 CRLF, 파일 끝 CRLF, BOM 없음(UTF-8)
- 삽입은 바이트 단위(CRLF로 split → 1줄 insert → CRLF로 join)라 다른 줄 바이트 변화 없음 (numstat `1 0`)
- 이 보고 파일도 CRLF로 저장

## 알아둘 점

- 추가된 줄이 가리키는 `docs/claude/artifact-design-rules-2026-10-14.md`와 이 작업 지시문은 원본 체크아웃에만 있고 이 worktree 기준 커밋(1d98bd0)에는 없다. 병합 전후로 23:30 DocsCommit(또는 _pending 등록)으로 커밋되는지 확인 필요. 이 Builder는 docs/claude 외 범위를 건드리지 않았고 해당 파일도 복사하지 않았다.

## 브랜치와 병합

- worktree 브랜치: `worktree-claude-md-design-rule` (기준 커밋 1d98bd0)
- 커밋: `docs(CLAUDE.md): keep design-system rules when editing artifact pages` (해시는 `git log -1 worktree-claude-md-design-rule`)
- Judge 통과 후 원본 저장소에서 사용자가 칠 명령 한 줄:

```
git merge --no-edit worktree-claude-md-design-rule
```
