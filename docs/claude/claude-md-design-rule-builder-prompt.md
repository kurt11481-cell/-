---
id: claude-md-design-rule-builder-prompt
title: CLAUDE.md에 화면 디자인 유지 규칙 한 줄 추가 (문구만)
date: 2026-10-14
class: 문구만(old K0). 경로가 CLAUDE.md(파이프라인 보호 경로)라서 수동 경로: Builder는 worktree, Judge는 별도 세션
decision: 사용자 "CLAUDE.md에 한 줄 추가 — 작업용 지시문 만들어줘"(2026-10-14 Cowork)
evidence: docs/claude/artifact-design-rules-2026-10-14.md (규칙 본문, 2026-10-14 사용자 지시)
base: CLAUDE.md sha256 c4146cbb79fadce7283c73a5bbfaedb66fbeb86e1510282672d3389e3e55c589 (117줄, CRLF)
authority: 없음. order_authority=false · quantity_authority·execution_quantity 불변 · 정책·상태·예약 작업·키움 호출 없음
weekly_user_touch: 0 (일회성: Builder 1번, Judge 1번, 병합 1번)
---

[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: medium · 세션: Windows 터미널 `claude --worktree claude-md-design-rule` · 이유: 한 줄 문구 추가

## 목표

CLAUDE.md의 Working rules 끝에 한 줄을 추가해, 어느 세션이든 투자_V2 화면(아티팩트) HTML을 고칠 때 디자인 시스템 규칙 문서를 따르게 한다. 그 밖의 줄은 한 글자도 바꾸지 않는다.

## 바꿀 곳 1군데

`## Working rules` 절의 마지막 줄("- Doc-only commits (user decision 2026-10-09 Q5, …" 로 시작하는 줄) **바로 다음**, `## Session hygiene` 제목 앞의 빈 줄 **앞**에 아래 한 줄을 그대로 넣는다.

```
- Artifact page design (user 2026-10-14): before editing or republishing the HTML of 미국주식 현황판, 개발 관제판 or 통합점검, read the live version and keep the 투자_V2 design-system colors, type and touch sizes in docs/claude/artifact-design-rules-2026-10-14.md. Display only: no data, rule or authority change; the 통합점검 order panel keeps Kiwoom buy red / sell blue (--buy/--sell), separate from price up green / down red.
```

## 지켜야 할 것

1. 시작 전에 CLAUDE.md sha256이 위 base 값과 같은지 확인한다. 다르면 고치지 말고 멈춘 뒤 BLOCKED.md에 현재 sha256과 이유를 적는다.
2. 줄 끝은 CRLF 그대로(새 줄도 CRLF). 다른 줄의 줄 끝·공백·인코딩(UTF-8, BOM 없음)을 바꾸지 않는다. 일괄 변환 금지.
3. 바뀌는 파일은 CLAUDE.md 하나와 보고 파일 하나뿐. 다른 파일·설정(.claude/**, AGENTS.md)은 건드리지 않는다.
4. 테스트 실행 불필요(문서만). 키움·auto_core 실행 없음.
5. worktree 브랜치에 커밋 1개: `docs(CLAUDE.md): keep design-system rules when editing artifact pages`. 원본 브랜치 병합·push는 하지 않는다.

## 보고 `docs/claude/claude-md-design-rule-report.md`

- 바꾸기 전·후 CLAUDE.md sha256과 줄 수(117 → 118 예상)
- `git diff --stat`와 추가된 줄 원문
- 줄 끝 확인 결과(바뀐 파일 전체가 CRLF인지)
- worktree 브랜치 이름과 커밋 해시, 사용자가 원본에 병합할 때 칠 명령 한 줄

## Judge 확인 항목 (별도 세션, 파일을 고치지 않음)

1. 바뀐 줄이 정확히 1줄 추가인지(`git diff` 원본 브랜치 대비), 위치가 Working rules 마지막 줄 다음인지.
2. 추가 문장이 위 원문과 글자 그대로 같은지.
3. 줄 끝 CRLF 유지, 다른 줄 변화 없음, CLAUDE.md 외 바뀐 파일은 보고 파일뿐인지.
4. 문장이 권한·정책·주문 규칙과 충돌하지 않는지(표시 전용임을 밝히는지).
5. 판정: 통과 / 실패(이유) 한 줄.
