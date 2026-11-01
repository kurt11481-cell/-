---
id: obsidian-tidy-2026-11-01
title: "Obsidian 두 보관함 트리·그래프 정리 (obs-tidy B)"
date: 2026-11-01
status: "진행 — 설정 쓰기는 Obsidian 닫힘 확인 뒤, 연결은 개발 큐 obs-links"
decision: "obs-tidy: B (2026-11-01 13:05 KST, 사장 버튼 선택 'B 설정 + 연결 만들기', 사장실 회사PC 스레드 'Obsidian 트리·그래프 뷰 정리', 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9VeRLPokEe3DUQWwRVS72hC)"
authority: "order_authority=false · quantity_authority=none · 키움 없음 · 정책·상태·예약 작업 변경 없음"
---

# Obsidian 트리·그래프 정리 (2026-11-01)

사장 요청(2026-11-01 13:00 KST): "obsidian 데이터 트리 및 그래프 뷰도 정리하는 건 어때?"

## 1. 결론
파일은 옮기지 않는다. 두 보관함의 `.obsidian` 설정(제외 폴더·그래프 색·북마크)을 바꾸고, 자동 목록이 문서를 링크로 잇게 한다(개발 큐 obs-links).

## 2. 근거 (2026-11-01 13시대 KST 조회)
- docs/claude 맨 위 md 523개, 하위 포함 597개. 문서 사이 링크(`[[ ]]`) 9개(파일 6개)뿐 → 그래프가 흩어진 점.
- 그래프 설정 색 그룹 0개(두 보관함 graph.json `colorGroups: []`).
- docs/claude 경로를 쓰는 곳: tools 스크립트 6개, 예약 지시문 14개(scheduled-prompts 맨 위 파일), 자동 코어가 읽는 md 7개(obsidian-ops-review-2026-10-22.md 0절 5번) → 파일 이동·이름 바꾸기는 깨짐 위험.
- 부딪히는 결정: obs-1022b Q1 a(원본은 제자리, 볼트는 읽기 보기). 설정 변경·자동 목록 형식 변경은 이 결정 안이다. 파일 이동은 하지 않는다.
- docs/claude/.obsidian은 git 추적·무시 목록 어디에도 없음(git ls-files·check-ignore 빈 결과) → 23:30 자동 커밋 대상 아님.
- INDEX-auto.md는 md 373개로 집계돼 실제(523)보다 낡음. ops-fixes.md 19행은 문서를 바꾼 세션이 make-index.py를 돌리라고 하지만 지켜지지 않음(갱신 주체 확인 필요).

## 3. 바꾸는 것
| 대상 | 내용 |
|---|---|
| docs/claude/.obsidian/app.json | 제외 폴더 추가: `__pycache__/`, `_to_delete/`, `_pending/`, `_dev-queue/`, `dev-runs/`, `scheduled-prompts/pending-` (검색·그래프에서 빠짐, 파일은 그대로) |
| docs/claude/.obsidian/graph.json | 색 그룹 7개(입구 빨강 · 헌법 금색 · ceo-inbox 노랑 · 개발 큐 지시문·보고 주황 · library 보라 · 검토·제안·설계 파랑 · 예약 지시문 초록), 없는 링크 숨김 |
| docs/claude/.obsidian/bookmarks.json(새) | 00-home · active-decisions · INDEX-auto · library |
| 개인 보관함 .obsidian/graph.json | 색 그룹 4개(index·log·CLAUDE 빨강 · 목록 노트 주황 · 20-wiki 파랑 · 10-raw 회색), 없는 링크 숨김 |
| 개인 보관함 .obsidian/bookmarks.json(새) | index · log · 20-wiki/외부자료 목록 |
| docs/claude/make-index.py | 개발 큐 obs-links: INDEX-auto.md 파일 칸을 `[이름](이름)` 링크로 → 모든 문서가 목록에 이어짐 |

## 4. 되돌리는 법
원래 설정 사본: 프로젝트 파일 `obsidian-tidy/backup-2026-11-01/`(system·personal의 app.json·graph.json, sha256 system app e03e2267… graph 01b53772…, personal app 9a1831a4… graph ac011be9…). Obsidian을 닫고 사본을 제자리에 덮고, 새로 만든 bookmarks.json 두 개는 지운다. obs-links는 git revert.

## 5. 하지 않음
파일 이동·이름 바꾸기 · 문서 본문에 링크 추가(CRLF·해시 보호, 00-home 고치면 안 되는 파일 표) · 커뮤니티 플러그인.

## 6. 바뀔 조건
- Obsidian 화면에서 꺾쇠 링크·제외 폴더가 기대대로 안 보이면 설정만 다시 조정.
- 별 모양(목록 중심) 그래프가 쓸모없다고 사장이 보면 문서끼리 잇는 방법(관련 문서 칸 자동 생성)을 따로 검토.
