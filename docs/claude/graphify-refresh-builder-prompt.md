---
id: graphify-refresh-builder-prompt
title: graphify 그래프 재생성 (코드만, GRAPH_REPORT.md 다시 만들기)
date: 2026-10-25
class: "도구 갱신(general 성격, 코드·설정 변경 없음). 개발 큐 자동 실행 경로에는 맞지 않음 — 아래 '실행 경로' 참고. 아직 큐에 올리지 않음"
source: "사장 '올린다'(2026-10-25 11:44 KST, 다른 스레드 직접 입력, 코디네이터가 서버 복사본으로 전달) + /mnt/project-files/tool-review/graphify-refresh-builder-prompt-draft.md"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음"
weekly_user_touch: "0 (실행 경로 결정 1번)"
---

## 목표
CLAUDE.md 73행은 graphify-out/GRAPH_REPORT.md를 "Code map (locator only, never evidence)"로 둔다. 지금 GRAPH_REPORT.md가 없다(확인 필요: 삭제 또는 미생성). 코드만 대상으로 그래프를 갱신하고 GRAPH_REPORT.md를 다시 만든다. 위치 안내용이며 증거가 아니다.

## 확인된 현재 상태 (사장 터미널 출력 02:44Z, 초안 기준)
- graphifyy 0.9.53 설치(uv tool), graph.json·manifest.json 2026-08-31, cache 2026-09-24
- 전역·저장소 settings.json에 graphify hook 없음. 자동 갱신 경로·git hook은 확인 필요

## 금지
1. `graphify install --project`, `graphify claude install`, `graphify hook install` 실행 금지(CLAUDE.md·settings.json·git hook 수정).
2. 비밀 파일(.env·토큰·계좌) 제외 확인 전 실행 금지. `.graphifyignore`로 제외 목록을 먼저 점검하고 결과를 보고에 쓴다.
3. 환경변수 `GRAPHIFY_BACKEND=none`(LLM 호출 없음, 문서·PDF 전송 방지)과 `GRAPHIFY_NO_AUTO_REFRESH=1`로 실행.
4. graphify 버전 업그레이드 금지(0.9.53 유지, 업그레이드는 별도 결정).
5. 주문·키움 도구 호출 없음. 정책·상태 파일 쓰기 없음.

## 먼저 확인 (실행 전)
- 갱신 명령 이름과 인자는 `graphify --help`로 확인(확인 필요).
- 갱신이 ~/.claude/skills/graphify 또는 ~/.claude/CLAUDE.md를 건드리는지(건드리면 중단).
- 실행 전 ~/.claude/CLAUDE.md 지문과 저장소 CLAUDE.md·.claude/settings.json 해시를 기록.

## 완료 기준
- graphify-out/GRAPH_REPORT.md 생성, graph.json 수정시각 갱신.
- ~/.claude/CLAUDE.md 지문(F7D43E69…7590) 불변. 저장소 CLAUDE.md·settings.json 불변(git diff 없음).
- 보고 `docs/claude/graphify-refresh-report.md`: 실행 명령, 제외 점검 결과, 전후 해시, 남은 위험.

## 실행 경로 (확인 필요 — 사장 결정 질문 1개)
이 작업은 dev-run 헤드리스 Builder에 맞지 않는다(근거: tools/dev-run.ps1 Builder 허용 도구 = python unittest·스키마 검증·git 읽기만, 그 외 Bash 없음, mcp 전부 금지 → graphify 실행 불가. graphify-out/은 .gitignore 153행이라 worktree 변경으로 남지 않고 메인 체크아웃 비교·allowed_paths 검사도 못 맞춤). 그래서 dev-run 블록과 `_dev-queue/<id>.txt`는 만들지 않았다. 대안: (가) 사장 터미널에서 위 조건대로 직접 실행 후 Cowork가 결과 확인, (나) Cowork가 같은 조건으로 실행(승인은 사장 직접 입력). 기본값 = (가).
