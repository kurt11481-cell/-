---
id: layer-audit-1125-builder-prompt
title: "layer-audit-1125 ④⑤ — CLAUDE.md 4항목·AGENTS.md 1줄 문구 (K3 수동 경로 Builder)"
date: 2026-11-25
class: "보호 경로(CLAUDE.md·AGENTS.md) 문구 변경 — 권한·한도 값 변경 없음, 사장 지시로 K3 수동 경로. Builder(Opus, 작업 폴더) → 별도 읽기 전용 Judge → 병합은 사장 PowerShell 한 줄"
source: "제안 2판 /mnt/project-files/layer-audit-1125/fix-proposal-3-5-2026-11-25.md · 사장 직접 입력 2026-11-25 18:59:35 KST '승인: layer-audit-1125 ④⑤ CLAUDE.md 4항목(문안 5줄)·AGENTS.md 1줄 수동 경로 착수'(cmsg_0137MRzn9nuDvvQmVxm6WeX9TpjrHV5FaTGZRhvVX3rC8S) · 순서 변경 사장 결정 카드 2026-11-25 19:00:53 KST '앞당겨 오늘 착수'(cmsg_0137MRzn9nuDvvQmVxm6WeX9A8zCr74mwt5F3gcnrRbDry, 누른 계정 = 사장)"
authority: "주문 권한·수량 권한 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 선행 조건 (하나라도 없으면 시작하지 않고 보고)
- 메인 체크아웃 `E:\사업\##금동한\코덱스저장소`의 CLAUDE.md sha256 = 48464bb4e5f462707ff0a7a42840c8affb61c48b18183332731f6efe0a8569da, AGENTS.md = 621c139f6042ffbe8c6999eafe195170568d0ecd76b59f9e3027da542bbb9149.
- 메인 체크아웃에 docs/claude/layer-audit-1125-apply.py가 있고 sha256 = 8ff54bb0f72e0e59a2e012f4ac7975f40b4e0d12718ef46cc0d233f1e011491c.

## 작업 위치
이 세션 자기 작업 폴더(worktree)에서 `git switch -C worktree-layer-audit <메인 HEAD 전체 해시>`. 기준 커밋 전체 해시와 작업 폴더 경로를 보고서에 적는다.

## 할 일 (이것만)
1. 작업 폴더 루트에서 `python <메인 체크아웃>\docs\claude\layer-audit-1125-apply.py .` 한 번. 출력이 `OK CLAUDE.md cd0868ce…`·`OK AGENTS.md c07e5094…` 두 줄이 아니면 더 하지 말고 BLOCKED.md(첫 줄 = 출력)를 쓰고 멈춘다.
2. 바뀌는 내용(스크립트가 바이트로 넣음, CRLF 유지):
   - CLAUDE.md 9행 빈 줄 뒤 새 문단 Precedence 한 줄 + 빈 줄
   - Change classes 절 Kiwoom acceptance pin 항목 앞에 Constitution·Scheduled tasks 두 줄(위치만 알려 주는 줄)
   - 'Production authority' 줄 이름 정정(Instrument identity/calendar authority …)
   - SCN-27H1 줄 끝에 Premise B0 효력 정지 문장
   - AGENTS.md 제목 뒤 빈 줄 + Codex 안내 한 줄
3. 시험(이 세 줄만, 글자 그대로, 작업 폴더에서):
   - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_reconcile_broker_state.py"`
   - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_cowork_to_room_k3.py"`
   - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_scheduled_prompt_kiwoom_profile.py"`
4. 보고서 docs/claude/layer-audit-1125-report.md(작업 폴더 안 새 파일): (a) 기준 커밋·경로·브랜치 (b) 두 파일 전후 sha256 64자·줄 수·CRLF 수 (c) CLAUDE.md '## Hard safety'부터 '## Kiwoom query rules' 앞까지 바이트 해시 전후(같아야 함) (d) `git diff --stat`·`git diff -U0` 바뀐 줄 번호 (e) 시험 결과 마지막 줄 셋 (f) `git status --short`. 주문·수량 표지 문자열은 쓰지 않는다.

## 지켜야 할 것
- 위 두 파일과 보고서 말고는 바꾸지 않는다. 손으로 편집하거나 줄바꿈을 바꾸지 않는다.
- git은 status·diff·log·rev-parse·switch만. commit·push·merge·reset 금지.
- 주문·키움·일지·원장·예약·정책·상태와 무관하다. auto_core.py 실행 금지, 비밀(.env*·토큰·계좌번호) 읽기 금지.
- 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 연결표 (analysis-linkage-map 1절 8번 — 이 변경 자체)
| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| CLAUDE.md Precedence·위치 줄 | 병합 뒤 모든 Claude Code 세션이 시작 때 자동으로 읽음 | CLAUDE.md 10행(새) → constitution-v1.5.0.md 65~76행 | 층 충돌 때 헌법 §1 순서로 판단, 헌법·예약 변경 원본을 찾아감 | 다음 지침 문서층 점검(layer-audit) · 승인 장소 표 '바뀔 조건' 줄 | 연결(병합 뒤) |
| AGENTS.md 안내 줄 | Codex 세션 시작 | AGENTS.md 3행(새) | 차이가 있으면 CLAUDE.md를 따름 | 의도적 없음 아님 — Codex 사용 여부 확인 필요 | 확인 필요 |
