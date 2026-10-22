---
id: secretary-1021
title: 비서 에이전트(사장 ↔ 비서 ↔ Claude 팀) 운영 아이디어
date: 2026-10-21
class: 문서만(K0). 설치·구독·런타임·정책·예약 작업·권한 변경 0
consumer: 사장 결정(결정 secretary-1021) 받는 Cowork 세션 → 결정 시 관제판 작업 생성. 다음 주간 팀장회의 연구개발팀 안건 후보(회의가 이 파일을 읽는지는 확인 필요)
---

# 비서 에이전트 운영 아이디어 (2026-10-21)

## 0. 결론
1. **비서는 Claude 안의 Dispatch로 시작한다(권장).** 사장이 대화 1개로 지시 → Dispatch가 Cowork 하위 작업으로 나눠 실행(코딩 일은 개발 큐 등록까지) → 결과를 사이드바·휴대폰으로 보고. Pro/Max 요금제에 포함(사장 요금제는 Max로 알고 있음 — 확인 필요), 설치 0, 새 구독 0(2026-10-20 Q1 c "서브 AI 안 함"과 충돌 없음, dual-ai-review-2026-10-20.md:4).
2. **Hermes는 2순위(보류).** 텔레그램 등 여러 메신저·자체 기억·예약 작업이 강점이지만, 키움 MCP가 깔린 PC에 셸 권한을 가진 두 번째 에이전트가 생긴다. Anthropic은 지원 제공자로 나오나 연결 방식(API 키인지 구독인지)은 확인 필요 — API 키면 Max와 별도 과금.
3. **dots는 보류, Grok 봇은 부적합.** dots는 ChatGPT Pro/Business Premium 구독이 필요하고(Q1 c와 충돌), Claude에게 일을 넘기는 방법이 공개 자료에 없다. Grok 텔레그램 봇은 대화·요약용 챗봇이라 다른 AI에 지시를 내리는 도구 기능이 공개 자료에 없다.

## 1. 후보 비교
| 항목 | Claude Dispatch | Claude Code Channels | Hermes Agent (Nous Research) | OpenAI dots | Grok (텔레그램) |
|---|---|---|---|---|---|
| 정체 | Cowork 안의 상주 비서 에이전트 | 실행 중인 Claude Code 세션에 텔레그램·디스코드로 말 걸기 | 오픈소스 자가 호스팅 에이전트(MIT는 경쟁사 글 1곳 근거) | OpenAI 상주 에이전트(자기 클라우드 PC) | 텔레그램 안 챗봇 |
| Claude에 일 시키기 | **직접** — 하위 작업을 별도 Cowork·Code 세션으로 실행 | 직접(그 세션이 곧 Claude Code) | 간접 — 셸로 `claude -p` 실행은 가능해 보이나 공식 기능 아님(확인 필요) | 공개 자료에 없음 | 없음 |
| 대화 창구 | Claude 데스크톱·모바일 앱 | 텔레그램·디스코드·iMessage(맥) | 텔레그램·디스코드·슬랙·왓츠앱 등(20+는 경쟁사 글 1곳 근거) | ChatGPT 앱, 슬랙·팀즈 | 텔레그램 |
| 비용 | Pro/Max 포함 | Pro/Max 포함(연구 미리보기) | 무료 SW + 모델 API 비용 | ChatGPT Pro/Business Premium(가격 확인 필요) | 텔레그램 프리미엄(가격 확인 필요) |
| 상시 가동 조건 | 데스크톱 앱 켜짐·PC 깨어 있음(사장 PC 24시간 가동) | 터미널 세션 계속 열려 있어야 함 | 게이트웨이 서버 상시 실행 | OpenAI 클라우드 | 상시 |
| 권한 안전장치 | 권한 요청을 사장에게 전달, **10분 무응답 → 자동 거부(그 단계만 빠지고 작업은 계속)** | 권한 전달을 지원하는 채널만 휴대폰 전달, 페어링 허용 목록 | 위험 명령 승인 층, 허용 목록·페어링, 기억·스킬 쓰기 승인 옵션 | 사용자 규칙(허용·차단·승인), 자동 검토 | 해당 없음 |
| 알려진 위험 | 하위 작업은 1단계만(손자 작업 없음) | 미리보기 단계, PC 잠들면 끊김 | 설정 노출(열린 Docker API·인증 없는 대시보드)로 설치본이 악용된 사례(2026-06·09, Hermes 자체 결함 아님), 가짜 설치 파일 | "중요한 일은 검토" 경고(같은 기사의 이미지 게시 사고는 dots 관련성 확인 필요) | 부정확 답 보고(자료 시점 2025) |
| 투자_V2 적합도 | **높음** | 중간(조회·질문용 보조 창구 — 코드 수정·결정 입력 불가) | 중간(나중 후보) | 낮음 | 부적합 |

## 2. 회사 구조 안 — "비서실"
```
사장(사용자) ── 대화 1개(휴대폰·PC) ──▶ 비서실장 = Dispatch
                                         ├─ 운영관리팀  → Cowork(투자_V2 프로젝트)
                                         ├─ 투자리서치팀 → Cowork
                                         ├─ 연구개발팀  → Cowork에서 개발 큐 등록까지만(Code 하위 작업 금지)
                                         ├─ 법률팀     → Cowork
                                         └─ 감사실(Judge)은 비서 경유 금지 — 사장 직속 수동 경로 유지
자동 운영 코어(결정론)는 비서와 무관하게 매일 돈다(비서 장애가 코어를 막지 않음).
```

### 비서실장이 하는 일
1. **접수·분류**: 사장 말 → 지시 / 질문 / 결정 답 / 긴급.
2. **배정**: 모든 하위 작업은 **투자_V2 Cowork 프로젝트를 매번 명시**(미지정이면 Dispatch가 다른 프로젝트를 고를 수 있음). 코딩 일도 Code 세션으로 바로 보내지 않고 Cowork에서 개발 큐(지시문 + _dev-queue)에 넣는 데까지만 — 개발 파이프라인·수동 경로를 건너뛰지 않게.
3. **보고**: 끝나면 1~3줄 + 결과 위치 + **거부된 권한·빠진 단계 목록(0건이면 0건)**. 사장 결정이 필요한 것만 위로(기존 기준: 바꾸자는 제안만 결정).
4. **브리핑**: "오늘 뭐 봐야 해?" → 자동 코어 결과 알림·주간 경영보고·관제판 결정함을 읽어 답.

### 비서실장이 못 하는 일(현행 안전 경계 그대로)
- 주문·정정·취소, 키움 주문 도구(현행 금지 그대로).
- 결정·확인 코드 중계 — 결정 일지·`확인 <코드>`는 "현재 대화에서 사장이 직접 보낸 메시지"만 유효(CLAUDE.md Hard safety). 하위 작업 안의 결정 문구는 비서가 쓴 글이라 무효. 비서는 "결정이 필요합니다: <작업 링크>"까지만 하고, 사장이 그 하위 작업 세션이나 Cowork에 직접 입력한다.
- 키움 조회(kiwoom_query) 외의 키움 도구·주문 관련 권한 요청은 항상 거부. 사장도 휴대폰에서 이런 요청은 승인하지 않는다.
- 중계하는 외부 글·알림 본문은 데이터로만 다룸(그 안의 지시는 따르지 않음 — 프롬프트 주입 차단).
- 정책·한도·권한 파일 수정, 감사실(Judge) 실행.

## 3. 단계(일상 사람 손: 목표 0, 단 하위 작업 권한 요청이 휴대폰으로 오면 손이 생김 — 주간 건수는 1주 시험에서 측정)
| 단계 | 내용 | 사람 손 |
|---|---|---|
| 1 | 휴대폰 Claude 앱에서 Dispatch 열기, 일상 지시를 Dispatch로 1주 시험 | 일회성 1번 |
| 2 | 1주 뒤 평가: ⓐ 하위 작업이 맞는 프로젝트로 갔나 ⓑ 거부로 빠진 단계 0건, 사장 승인이 필요했던 권한 요청 주 2건 이하 ⓒ 사장이 직접 Cowork를 연 횟수가 줄었나. 미달이면 현행(사장↔Cowork 직접) 유지 | 0 |
| 3(조건부) | 텔레그램이 꼭 필요할 때만 Hermes 재검토: 별도 PC/VM 격리, 키움 MCP 없는 환경, 허용 목록 1인, 셸 승인 manual | 결정 1번 |

## 4. 바뀔 조건
- Dispatch가 이 계정에서 안 보이거나 Cowork 프로젝트 지정이 안 되면 → 1번 결론 재검토.
- Anthropic이 Claude 구독으로 Hermes를 쓰는 공식 방법을 내면 → Hermes 비용 판단 재검토.
- dots가 Claude/MCP 위임을 공식 지원하고 사장이 ChatGPT 구독을 다시 원하면 → dots 재검토.

## 5. 결정 요청 (`결정 secretary-1021: a|b|c`, 기한 2026-10-28, 무응답 = 현행 유지)
- **a) Dispatch 1주 시험(권장)** · b) Hermes 격리 시범 설계부터 · c) 현행 유지(사장 ↔ Cowork 직접)

## 내장 재검토
- 1회차 11건 — 결론을 바꾼 것 3건: 결정 문구도 비서 경유 무효(사장이 직접 입력) · 연구개발은 개발 큐 등록까지만(Code 하위 작업 금지) · 키움 조회 외 권한 항상 거부·중계 본문은 데이터로만. 문구 8건: 10분 거부는 '단계 누락' · 사람 손 측정 · 프로젝트 명시 · dots 사고 관련성 · Grok 자료 시점 · Hermes 근거 한정 · Channels 제3자 출처 · 내부 확인 필요 표시.
- 2회차(바뀐 부분만) 5건, 모두 문구: 0절 Code 표현 · Hermes 연결 방식 · MIT 근거 · Channels 용도 · 시험 통과 기준.

검토 완결: 원문 확인 9/9(외부 URL 7 · 내부 파일 2) · 내장 재검토 2회(반영 16건) · 미해결 3(Dispatch 계정 노출 여부, Hermes의 Claude 구독 연결, dots·Grok 가격 — 확인 필요) · 자료 시점 2026-10-21 19:40~20:05 KST · 바뀔 조건 4절

## 출처
- Dispatch: https://claude.com/docs/cowork/guide/dispatch.md (조회 2026-10-21 19:40 KST)
- Channels: https://fast.io/resources/claude-channels-guide.md (제3자 가이드, 공식 문서 재확인 필요)
- Hermes: https://parallel.ai/articles/what-is-hermes-agent.md (경쟁사 글, 편향 가능), https://docs.vultr.com/how-to-deploy-hermes-agent-open-source-self-hosted-ai-agent
- dots: https://thenextweb.com/news/openai-dots-always-on-ai-agents-cloud-computers-devday
- Grok: https://tech.yahoo.com/ai/articles/xai-chatbot-grok-available-telegram-203900522.html , https://3dnews.ru/1120341/
- 내부: docs/claude/company-org-plan-2026-10-19.md:19~20, :125, :153~154 · docs/claude/dual-ai-review-2026-10-20.md:4 · CLAUDE.md Hard safety

## 6. 장기 권한 확장 (2026-10-21 19:46 사장 요청 반영)
사장 요청(원문 요지): 장기적으로 주문 · 사장 결정·확인 코드 대신 전달 · 정책 수정 · 개발 대기열 건너뛴 코드 수정 · 키움 조회 외 권한 승인도 가능해야 하고, 지시 없이도 할 일을 먼저 제안하는 비서를 원함.

### 6-1. 원칙: 권한은 비서(LLM)가 아니라 결정론 코어와 "사장 승인 기록"에 준다
- 비서는 바꿔 끼울 수 있는 창구. 비서가 바뀌거나 고장 나도 권한 구조는 그대로.
- "대신 전달"은 비서가 결정 문구를 옮겨 적는 방식이 아니라, 사장이 누른 승인을 기록으로 남기는 방식: 승인 기록 = 사장 신원(허용된 계정) + 원문 + 시각 + 제안 해시 + 만료. 코드가 해시 일치·만료를 검사한 뒤에만 실행.
- 단계는 시스템이 스스로 올리지 않는다(automation-redesign-2026-10-10.md:138). 권한 변경은 한 번에 1건, 사장 승인 + 독립 Judge.

### 6-2. 요청 5가지의 경로
| 요청 | 장기 형태 | 이미 있는 근거 | 단계 |
|---|---|---|---|
| 주문 | 비서가 직접 주문 도구를 부르지 않음. 코어가 키움 API 주문을 만들어 대기 → 비서가 휴대폰으로 전달 → 사장 승인 1번에 코어가 제출(주문 2단계) → 봉투 안 자동 제출(3단계) | automation-redesign-2026-10-10.md:132~135 | T5 주문 2단계(K3) |
| 결정·확인 코드 전달 | 6-1의 승인 기록. 결정 일지·대조 규칙의 "현재 대화의 사장 메시지"를 "승인 기록"으로 넓힘 | — | K3(규칙 변경) |
| 정책 수정 | 비서가 개정안(diff) 작성 → 사장 승인 기록 → 수동 경로 Builder·Judge가 적용 | CLAUDE.md 변경 등급 | 비서 연결은 일반 변경, 정책 자체는 K3 |
| 대기열 건너뛴 코드 수정 | 빠른 차선: 문서·표시 전용 등 저위험 등급만 자동 테스트 통과 시 바로 병합. 권한 경로(tools/dev_pipeline/authority-paths.txt)는 계속 Judge | 개발 파이프라인 | 일반 변경(차선 규칙) |
| 키움 조회 외 권한 승인 | 허용 목록을 등급별로 넓힘. 주문 도구는 LLM 자동 승인 대상에서 영구 제외(코어만) | — | K3 |

### 6-3. 선제 제안
- Claude 쪽: Dispatch 공식 문서에 선제 제안 기능 없음. 대신 예약 작업 "비서 제안"(아침 1회, 결과 파일·자동 코어 알림·관제판을 읽고 할 일 최대 3건 제안, 없으면 침묵, 푸시)으로 구현 가능 — 기존 주간 팀장회의와 같은 방식.
- Hermes 쪽: HeartBeat2(커뮤니티 플러그인 v0.2.1 — 공식 아님)로 감시·후속 알림, ask_first·조용한 시간·하루 상한. 스크립트 전용 cron은 토큰 0으로 텔레그램 알림.

### 6-4. 결론 수정
- 지금(1단계)은 Dispatch + 예약 작업 "비서 제안" 유지(비용 0). 0절 1번 결론은 유지.
- 장기 권한의 핵심은 비서 선택이 아니라 6-1 승인 기록 + 주문 2단계. 이 둘이 생기면 어떤 비서든 창구로 붙는다.
- Hermes 재평가 시점: 주문 2단계 착수 때. 휴대폰 승인 창구로 Claude 앱 권한 요청(10분 자동 거부)과 Hermes 텔레그램(허용 사용자 ID)을 비교. 텔레그램 승인 버튼 지원 여부는 확인 필요.
- 바뀔 조건: Claude가 선제 제안·승인 버튼을 공식 지원하면 Hermes 불필요. 승인 기록 없이 비서에게 주문 도구를 주는 안은 기각(가격·문구 착오가 그대로 주문이 됨).

출처 추가: https://hermes-agent.nousresearch.com/docs/plugins/heartbeat2 · https://hermes-agent.nousresearch.com/docs/guides/cron-script-only (조회 2026-10-21 19:50 KST) · docs/claude/automation-redesign-2026-10-10.md:129~138

## 7. 정정 (2026-10-21 20:05 KST) — Dispatch 신규 사용 불가
- Anthropic 도움말: "Dispatch isn't available to new users. If you already use Dispatch, you can keep using it for now." 대안으로 "use Cowork in the cloud"(클라우드 세션 — PC가 꺼져도 동작)를 권함. Claude Code로 바뀐 것은 아님(이름 변경·통합 공지 없음). 출처 https://support.claude.com/en/articles/13947068-assign-tasks-to-claude-from-anywhere-in-cowork
- 제3자 글(felloai): 2026-09-16부터 Pro·Max에서 채팅·Cowork 통합 시작, 같은 날 Dispatch 신규 중단(Anthropic 공식 날짜는 확인 필요).
- 영향: 0절 1번과 결정 secretary-1021 a는 "사장 사이드바에 Dispatch가 보일 때만" 유효. 안 보이면 a = 클라우드 세션 1개를 비서 대화로 고정(휴대폰에서 지시, PC 연결로 저장소 접근) + 예약 작업 "비서 제안"으로 바꿈. 하위 작업 자동 분배 기능은 Dispatch만큼 확인되지 않음(확인 필요).

## 8. 사장 재검토 (2026-10-21 20:02 KST, 사장 "없음. 비서 agent 아이디어를 재검토하라")
바뀐 입력: 사장 사이드바에 Dispatch 없음 → 신규 사용 불가 확정. 1차 누락: Anthropic 자체 현행 기능(Claude Code Projects·Remote Control)을 안 봄.

| 항목 | 처음 | 재검토 | 이유 | 원문 |
|---|---|---|---|---|
| 1순위 비서 | Dispatch 1주 시험 | **Claude Code Projects**(Code 탭·claude.ai/code 사이드바에 "Projects"가 있을 때) | 입력 변경 + 1차 누락. Projects = "한 대화에서 Claude가 작업마다 스레드를 열어 병렬로 돌림", 휴대폰에서 확인·지시, 예약(routine), 프로젝트 메모리, "Waiting on you"(승인 대기 모음), Pause(전체 정지). Pro·Max 공개 베타·순차 배포 | claude-projects.md 9~15·34·58·201·391행 |
| Projects 없을 때 | (없음) | **지금 이 투자_V2 클라우드 대화를 "비서실" 대화로 고정** + 예약 작업 "비서 제안"(아침, 할 일 최대 3건, 없으면 침묵) | 새 기능 0으로 바로 가능. PC 연결로 저장소 읽기·쓰기, 예약 작업·푸시는 이미 쓰는 방식. 단, 일을 별도 스레드로 나눠 보이게 하는 기능은 없음 | 이 세션 동작 · company-org-plan-2026-10-19.md:125 |
| Hermes | 2순위(보류), 주문 2단계 때 재평가 | 유지 — 새 근거 없음. 단 Projects도 없고 텔레그램이 꼭 필요하면 다시 후보 | — | 1절 |
| dots / Grok | 보류 / 부적합 | 유지 — 새 근거 없음 | — | 1절 |
| Channels | 조회·질문용 보조 | 유지. Remote Control(휴대폰으로 PC의 Claude Code 세션 조종, Pro·Max, 푸시 알림)도 같은 등급 | 비서(분배·선제 제안)가 아니라 창구 | remote-control.md 28·288~307행 |
| 장기 권한(6절) | 권한은 코어 + 사장 승인 기록 | 유지 — 새 근거 없음 | — | 6절 |

### 8-1. Projects를 쓸 때 꼭 지킬 것 (새로 찾은 위험)
- 스레드는 자동 모드로 돈다("most tool calls run without asking you"). 내 PC 스레드는 그 PC의 MCP 서버·설정을 그대로 씀 → **키움 MCP 주문 게이트가 Claude Code 쪽에서도 0인지 시험 전에 확인 필요**(데스크톱 앱 쪽 0은 기록됨, Claude Code 쪽은 미확인). 확인 전에는 내 PC 스레드 금지.
- 클라우드 스레드는 GitHub 저장소만 봄. 상태·결정 일지 등 git 밖 기록은 못 봄 → 운영 일은 내 PC 스레드, 클라우드 스레드는 문서·리서치만.
- 프로젝트 메모리·지시는 "강제 설정이 아니라 지키려는 지시"(240행) → 안전 경계는 지시가 아니라 저장소 .claude 권한 규칙·코어 코드에 둔다(현행 그대로).
- 코딩은 개발 큐 등록까지(2절 규칙 유지). 결정·확인 코드는 사장이 그 스레드에 직접(2절 유지).
- "Require trusted devices"가 켜져 있으면 내 PC 스레드 불가(277행).

### 8-2. 결정 요청 수정 (`결정 secretary-1021: a|b|c`, 기한 2026-10-28, 무응답 = 현행 유지)
- **a) Projects가 보이면 Projects 1주 시험(클라우드 스레드 = 문서·리서치만, 내 PC 스레드는 주문 게이트 확인 뒤) / 안 보이면 투자_V2 비서실 대화 + 예약 "비서 제안"(권장)** · b) Hermes 격리 시범 설계부터 · c) 현행 유지
- 사람 손: 일회성 1~2번(사이드바 확인, 예약 작업 승인). 일상 목표 0, 실제 건수는 1주 시험에서 측정.

검토 완결(재검토): 원문 확인 6/6(도움말 2·Projects·Remote Control·Claude Tag·이전 기록) · 내장 재검토 1회(이 대화 안) · 미해결 3(Projects 노출 여부, Claude Code 쪽 키움 주문 게이트, Claude Tag 개인 요금제 제공 여부 — 확인 필요) · 자료 시점 2026-10-21 20:10 KST · 바뀔 조건: Projects 노출 여부, 주문 게이트 확인 결과
출처 추가: https://code.claude.com/docs/en/claude-projects.md · https://code.claude.com/docs/en/remote-control.md · https://support.claude.com/en/articles/15811196-what-to-expect-with-claude-cowork-in-the-cloud · https://qz.com/anthropic-claude-tag-slack-ai-agent-062326

### 8-3. 상태 (2026-10-21 20:10 KST)
- 사장 확인: Code 탭 사이드바에 Projects 없음. 사장이 대기 명단 신청함(https://claude.com/ko/form/projects).
- 따라서 a안은 "투자_V2 비서실 대화 + 예약 작업 비서 제안" 쪽으로 진행 대상. Projects가 열리면 사장이 알려 줄 때 8-1 조건으로 옮김(자동 감지 없음).
- 결정 secretary-1021 아직 답 없음(기한 2026-10-28, 무응답 = 현행 유지).

## 9. Projects vs Hermes (2026-10-21 20:15 KST, 사장 요청 — 이 대화에서 연 원문만 사용)
- 결론: Claude 팀에게 일을 나눠 시키는 비서 = Projects가 낫다(대기 중). 먼저 말 거는 알림 + 텔레그램 = Hermes가 낫다. 지금은 둘 다 바로 쓰지 않고, 대안(비서실 대화 + 예약 "비서 제안") 유지.
- Projects 근거: claude-projects.md 9~15(공개 베타·스레드 분배·휴대폰), 194(알림은 데스크톱 앱만), 240(지시는 강제 아님), 244·273(자동 모드), 391(전체 정지), 397~407(요금제 한도 공유, 하루 스레드 200), 440(모델은 Anthropic만).
- Hermes 근거: parallel.ai 글(MIT·v0.21.6·제공자·20+ 메신저·허용 목록·cron·MCP·셸·승인 층·사고 사례), heartbeat2(커뮤니티 v0.2.1), cron-script-only(토큰 0 알림). Windows PC 직접 설치 가능 여부·Claude 구독 연결은 확인 필요.

## 10. 결정 기록
- 답: 결정 secretary-1021: a (2026-10-21 20:19 KST, Cowork) — 사장 원문 "결정 secretary-1021: a / projects 기능이 열리면 projects 도입 진행"
- 반영: ① Projects 미노출 → 대안 진행: 예약 작업 "비서 제안 v1"(월~토 09:25 KST) 지시문 초안 docs/claude/scheduled-prompts/pending-secretary/secretary-daily.txt(sha256 20b13bfd…, LF). 등록은 사장 승인 뒤("결정 secretary-daily: 승인"), 등록 조건: 컴퓨터 연결·코덱스저장소 폴더·자동 승인. 결과 파일 workspace/outputs/secretary/<날짜>.md(소비자 = 비서실 대화, 주간 팀장회의 다음 개정). ② Projects가 열리면(사장이 알려 줌) 8-1 조건으로 도입 진행 — 사장 지시로 기록, 도입 전 Claude Code 쪽 키움 주문 게이트 확인이 첫 단계.
- 사람 손: 일회성 승인 1번. 일상 0(알림 읽기는 선택, 제안 실행은 사장이 고를 때만).
- 답: 결정 secretary-daily: 승인 (2026-10-21 20:23 KST) → 예약 작업 생성 trig_01QL11yZhnxCJx7FXfCnRMT4(월~토 09:25, 첫 실행 10/22, 자동 승인·폴더 1개·컴퓨터 연결 확인, 모델 Opus 5.5 표시).
- 첫 실행 확인 (2026-10-22 13:20 KST, Cowork): 10/22 09:26 실행 성공. 결과 workspace/outputs/secretary/2026-10-22.md 있음 · 제안 2건(≤3) · 실행 시간대 저장소 쓰기는 그 파일 1개뿐(금지 위반 없음) · 예약 작업 모델은 현재 claude-sonnet-5-5. 휴대폰 알림 도착 여부는 확인 필요. 관제판 secretary-daily → done.
