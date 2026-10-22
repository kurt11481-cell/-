---
id: md-1022
title: "Munder Difflin으로 AI 사무실 차리는 법" 글 분석 → 뼈대 요소 · Claude Projects 대조 (pb-1022 승인 전 추가 검토)
date: 2026-10-22
class: 문서만(K0). 설치·구독·런타임·정책·예약 작업·권한 변경 0
source: https://sdk-kim-builds.com/guides/munder-difflin-ai-employee-office/ (2026-09-29, 김스듴) · https://github.com/chaitanyagiri/munder-difflin (README·SECURITY.md, 조회 2026-10-22 00:45~00:55 KST)
consumer: pb-1022 결정(delegation-loop-review-2026-10-22.md 9절에 반영) · 관제판 secretary-projects(Projects 도입 조건) · 재설계 T4 입력(연결 지도 대체 후보)
---

# Munder Difflin 글 분석 → 뼈대 요소 · Projects 대조 (2026-10-22)

## 0. 결론
1. **Munder Difflin은 도입하지 않는다(NO_CHANGE).** 소스(커밋 7586928, 2026-10-20)를 직접 확인한 결과:
   - **기본값이 승인 우회**: `autoMode: true`(src/main/config.ts:427)이면 Claude Code를 `--permission-mode bypassPermissions`로 띄운다(config.ts:191, src/shared/agentProvider.ts:176).
   - **PC 전역 설정을 고친다**: Claude를 쓰면 `~/.claude/settings.json`에 skipDangerousModePermissionPrompt·skipAutoPermissionPrompt를 true로 쓴다(config.ts:798~811, index.ts:2950~2955). 이 PC의 다른 Claude Code 작업(개발 파이프라인 Builder·Judge 등)에도 영향을 줄 수 있다.
   - **Windows는 OS 샌드박스 없이 돈다**: "a platform without a sandbox (Windows) runs as before rather than refusing to spawn"(src/main/hive.ts:1287 부근).
   - 키움 MCP가 깔린 사장 PC(Windows)에서 이 조합은 받아들일 수 없다. 성숙도도 낮다(SECURITY.md "early prototype", README 0.5.6 · package.json 0.4.6 — 배포본(harnessmd.com)이 공개 소스와 같은지는 확인 필요).
2. **Projects 도입 결정(secretary-projects)은 바뀌지 않는다.** 클라우드 실행(PC가 꺼져도)·Anthropic 운영·전체 정지 버튼·스레드별 사용량 화면이 우리 조건에 더 맞다.
3. **뼈대에 넣을 요소 2개(pb-1022 D1에 덧붙임, 둘 다 기존 규칙 재사용)**
   - E1 **플레이북 머리에 입력(누가 쓴 파일)·출력(누가 읽는 파일)** — Munder의 우편함(outbox→inbox) 발상. 새 규칙이 아니라 연결 지도의 기존 규칙(결과 문서 머리 consumers, analysis-linkage-map 21행)을 플레이북 머리로 옮기는 REUSE. 연결 지도에는 플레이북이 아닌 행도 있어 지금 지도를 없애지 않는다 — 플레이북이 생긴 작업의 지도 행만 "그 플레이북 머리 참조" 1줄로 바꿔 원본을 하나로 유지한다.
   - E2 **플레이북 머리에 반복 실패 처리** — Munder의 회로 차단기(같은 일 8회 반복·오류 5회 연속 → 조정 → 제한, src/main/breaker.ts:89~94, 기본 켜짐) 발상. 그 작업이 직전 결과 파일을 읽어 같은 실패가 연속 2회(일 작업 2일, 주간 작업 2주)면 자기 결과 파일 첫 줄에 "반복 실패 n회 — <원인 단계>"를 적고 알림 1줄. 주간 팀장회의가 연구개발팀 '팀 처리' 안건으로 받는다(사장 확인으로 올리지 않음 — 일상 사람 손 0). 결과 쓰기 막힘은 지금 규칙 그대로(매도·위험 축소 알림은 막지 않음).
4. **받아들이지 않을 것**: ① 팀장 에이전트가 "돈·되돌리기 어려운 일·범위 변경"만 AI 판단으로 올리는 방식 — 우리는 정책·한도·권한·예약 작업·코드 변경을 사장 결정으로 정한 기준과 결정론 코어를 유지. ② 완전 정지(hardStop) 기본 꺼짐·토큰 한도 비어 있음 — 우리 기본값은 막힘. ③ 플레이북에 '모델' 칸 — 예약 설정·README 표에 이은 세 번째 사본이 됨(README 10/16~17 모델 칸 불일치 기록), 모델은 README 표 한 곳.

## 1. 글·원본의 주장 (사실·해석·가설)
| # | 주장 | 분류 | 원본 대조 |
|---|---|---|---|
| M1 | 무료 데스크톱 앱, 이미 쓰는 Claude Code·Codex 등을 여러 개 묶어 팀처럼 | 사실 | README "A local multi-agent harness…", MIT, 약 8.2k stars, README 0.5.6 |
| M2 | 팀장(마이클)만 상대, 나머지는 알아서, 중요한 것만 올림 | 사실(설계) | README "only escalates *critical* items" |
| M3 | 직원 간 쪽지는 파일 우편함, git은 본체만 커밋 | 사실(설계) | README outbox/→inbox/, "No agent ever touches git" |
| M4 | 회로 차단기 | 사실 | breaker.ts DEFAULTS enabled true · hardStop false · 반복 8 · 오류 5. 토큰 한도는 비어 있음(글) |
| M5 | 쉬지 않고 일한다 | 과장 | 글 스스로 "켜진 컴퓨터에서만", 구독 한도에 닿으면 멈춤 |
| M6 | 안전하게 쓸 수 있다 | **반대 증거** | 기본 승인 우회 + 전역 설정 수정 + Windows 샌드박스 없음(0절) |
| M7 | 비용은 기존 구독 | 사실 | 글: 기본 모델 Opus 5.5(README 373행). 소스 기본값(config.ts:431·435)과 표기가 다름 — 확인 필요 |
| M8 | 같은 블로그 9/18 "에이전트 대신 매뉴얼", 9/29 "AI 직원 사무실" | 해석 | 두 글 모두 팀 도입 상담 홍보가 붙음 — 단서로만 |

## 2. 지금 시스템과 대조
| Munder 요소 | 투자_V2 현재 | 판정 |
|---|---|---|
| 팀장 1명이 받고 나눔 | 사장 ↔ Cowork 대화 + 비서 제안(월~토 09:25) + 주간 팀장회의(일 09:47) | 있음 |
| 파일 우편함 | 결과 파일을 다른 작업이 읽는 연결 규칙(analysis-linkage-map, 손 관리 표, 결과 머리 consumers) | 있음 — 기계 검사는 없음(E1) |
| 단일 커밋 | docs/claude는 23:30 InvestmentV2-DocsCommit 하나가 커밋(CLAUDE.md:96) | 있음 |
| 예약·트리거 | 반복 예약 작업 10개(README 표 기준) + Windows 작업 | 있음 |
| 작업 관찰 | 관제판·통합점검·주간 팀장회의 대시보드 — 결과 화면만(실시간 작업 화면 없음) | 부분(필요성 낮음) |
| 회로 차단기 | "한 번만 다시"(auto-core-alert.txt:10·18, ceo-weekly-meeting.txt:19), 주간 회의의 작업 실패 발견(ceo.py F-RND-3), 추가 사용량 꺼짐 = 요금제 한도가 정지선(prompt-caching-review, 10/09 기준) | 부분 — 연속 실패를 세는 규칙 없음(E2) |
| 에이전트별 기억 | 메모리 + docs + CLAUDE.md(일별로 나뉘지 않음) | pb-1022 D1 notes.md로 |

## 3. Claude Projects 도입안과 대조
| 항목 | Munder Difflin | Claude Code Projects (대기 중) | 지금 |
|---|---|---|---|
| 사장이 말하는 상대 | 팀장 에이전트 1명 | 프로젝트 대화 1개(Claude가 작업마다 스레드) | Cowork 대화 + 비서 제안 |
| 실행 위치 | 사장 PC만(앱 켜짐) | 클라우드(PC 꺼져도) + 필요 시 PC 스레드 | 클라우드 예약 세션 + PC 연결 |
| 승인 | 기본 bypassPermissions + 전역 설정 수정 | 자동 모드, 승인은 그 스레드 안, 지시는 강제 아님. 권한 규칙(.claude/settings.json)은 시작 폴더 기준(저장소 1개인 프로젝트면 그 저장소 것) | 예약 = 자동 승인 + 지시문 금지 목록 + 해시 고정, 결정론 코어 |
| 정지 | 회로 차단기 켜짐, 완전 정지 기본 꺼짐 | Pause = 전체 정지, 하루 200 스레드 상한 | 키움 주문 게이트 0, 주문 도구 금지 |
| 사용량 | 전사본에서 비용 추적, 직원별 토큰 한도(기본 비어 있음) | 설정 Usage 탭: 스레드별·모델별 토큰 | 작업별 사용량 잴 방법 없음 |
| 기억·지시 | 에이전트별 md + 공유 검색 | 프로젝트 메모리 + 지시(16,000자) + 저장소 .claude/skills + 계정 스킬 | 메모리·docs·CLAUDE.md |
| 비용 | 무료(+Pro 연 150달러), 구독 사용 | Max 포함, 한도 공유 | Max |
| 성숙도 | 개인 오픈소스, early prototype | Anthropic, 공개 베타(기존 프로젝트가 없는 계정부터 배포 — 이 계정은 늦을 수 있음) | — |
| 키움 MCP 있는 PC 위험 | **높음(확인됨)** | 중간(PC 스레드 자동 모드 — 주문 게이트 확인 전 PC 스레드 금지, secretary-agent-idea 8-1) | 낮음 |
판정: Projects가 열리면 Projects, 그 전에는 지금 구조. Munder는 어느 단계에도 들어가지 않는다.
- 빠진 대안 — "키움 MCP가 없는 별도 PC·VM에서 격리 시범": 기각. 전역 설정 수정·샌드박스 없음 문제는 격리로 피할 수 있지만, 투자_V2 일은 저장소·키움 결과 파일이 있는 사장 PC에서 해야 하고 Projects가 같은 이점을 더 안전하게 준다. 별도 장비 관리도 사람 손을 늘린다.

## 4. pb-1022에 주는 영향
- 권장(Q1 a, Q2 a) 유지. D1 플레이북 머리에 E1(입력·출력)·E2(반복 실패 처리) 칸 추가(모델 칸은 넣지 않음).
- 위치: Projects는 저장소 .claude/skills만 스킬로 읽으므로(claude-projects.md 359행), Projects가 열리면 플레이북을 그쪽으로 옮기는 일(보호 경로 — 수동 경로)이 생긴다. 지금은 docs/claude/playbooks 유지.
- 사람 손: 일상 0. 일회성 = 플레이북으로 바꾸는 작업마다 지시문 교체 승인 1번(pb-1022 4절과 같은 승인에 포함).

## 5. 바뀔 조건
- Munder가 ① 기본값을 묻기 모드로 ② 전역 설정을 고치지 않고 ③ 샌드박스 없는 플랫폼에서 실행을 거부하고 ④ 배포본이 공개 소스와 같음을 보이면 → 다시 검토(그래도 Projects가 열려 있으면 NO_CHANGE).
- Projects의 Usage 탭처럼 작업별 사용량을 잴 방법이 생기면 → E2에 사용량 한도 추가.

## 6. 내장 재검토 기록
- 1회차 8건 — 결론을 바꾼 것 2건: ① 승인 모드 "미기재(확인 필요)" → 소스에서 확인(기본 bypassPermissions·전역 settings.json 수정·Windows 샌드박스 없음) — NO_CHANGE 근거 강화(Cowork가 같은 커밋을 다시 받아 행 확인) ② E2 — "연속 2회 → 사장 확인"을 "결과 파일 표시 + 주간 회의 팀 처리"로(일상 사람 손 0), 모델 칸 삭제. 문구 6건: 버전 0.5.6·0.4.6 · 회로 차단기 기본 켜짐 · 반복 실패 '부분' · E1은 REUSE·지도 행 1줄 참조 · Projects Usage 탭·권한 규칙 범위·배포 순서 · 관찰 화면 '부분'·반복 예약 10개·격리 시범 대안.

검토 완결: 원문 확인 14/14(외부 4 · 소스 6 · 내부 4) · 내장 재검토 1회(반영 8건, 결론 변경 2건 — 바뀐 부분은 원문 직접 대조) · 미해결 2(배포본=공개 소스 여부, 기본 모델 표기 차이 — 확인 필요) · 자료 시점 2026-10-22 00:45~01:30 KST · 바뀔 조건 5절

## 출처
- 글: https://sdk-kim-builds.com/guides/munder-difflin-ai-employee-office/
- 저장소: https://github.com/chaitanyagiri/munder-difflin (커밋 7586928 2026-10-20) — src/main/config.ts:191·427·798~811, src/shared/agentProvider.ts:176·179, src/main/index.ts:2950~2955, src/main/hive.ts:1279~1287, src/main/breaker.ts:89~94, README.md, SECURITY.md, package.json
- Projects: https://code.claude.com/docs/en/claude-projects.md (244·338·359·382·391·407·415행, 저장본)
- 내부: analysis-linkage-map-2026-10-05.md 21행, scheduled-prompts/README.md 표, auto-core-alert.txt:10·18, ceo-weekly-meeting.txt:19, CLAUDE.md:96, secretary-agent-idea-2026-10-21.md 8-1절
