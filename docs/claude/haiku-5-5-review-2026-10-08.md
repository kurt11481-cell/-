# Haiku 5.5 세팅 가이드 검토·적용 (2026-10-08)

- 원본: Notion "Haiku 5.5 세팅 가이드"(외부 제작자 페이지, 2026-10-08 열람). 외부자료라 주장은 공식 문서로 교차확인했다.
- 변경 등급: K1(Claude Code·Cowork 보조 작업의 모델 선택). 런타임 계약·정책·권한·pin 대상 파일 변경 없음. order_authority=false.
- 사용자 승인: 2026-10-08 Cowork, "A + B 모두".

## 1. 결론

"메인 모델은 그대로, 잔일만 Haiku"는 투자_V2 원칙(판단 품질 > 운영 부담 > 단순화 > 자동화)과 맞는다.
모든 보조 에이전트를 Haiku로 강제(CLAUDE_CODE_SUBAGENT_MODEL_FORCE)하거나 대화 전체를 Haiku로 바꾸는 것은 적용하지 않는다.

## 2. 가이드 주장 확인

| 주장 | 결과 | 근거 |
|---|---|---|
| Haiku 5.5 출시 2026-10-07, 100만 토큰당 입력 0.1·출력 0.5달러(10만 토큰 이하) | 확인됨. 10만 토큰 초과는 0.5·2.5달러 | anthropic.com/claude/haiku |
| Haiku 첫 effort 지원(low~max), 기본 medium | 확인됨 | anthropic.com/claude/haiku, code.claude.com/docs/en/model-config |
| Claude Code v2.1.293 이상 필요 | 확인됨 | model-config |
| `haiku` 별칭 = Anthropic 연결 시 Haiku 5.5, Bedrock·Vertex·Foundry는 Haiku 4.5 | 확인됨 | model-config |
| 에이전트 파일 `model: haiku`, 위치 .claude/agents/ · ~/.claude/agents/ | 확인됨 | code.claude.com/docs/en/sub-agents |
| CLAUDE_CODE_SUBAGENT_MODEL은 기본값(에이전트 파일 지정이 우선), FORCE는 전부 고정(v2.1.257+), 기본값만으로는 Explore·Plan 안 바뀜 | 확인됨. 추가: FORCE를 켜면 에이전트 파일의 model도 무시되고 호출 때 모델 지정도 막힘 | sub-agents |
| 평균 운영비 약 75% 감소, 같은 글 토큰 약 30% 증가 | 확인 필요(공식 원문 미확인) | — |
| Sonnet 5.5 캐시 읽기 0.2→0.1달러 | 확인 필요 | — |
| Max·Team 월 API 크레딧(금액·이월 없음) | 확인 필요 | — |
| 달걀 낙하 실험 수치 | 확인 필요(적용과 무관) | — |

확인 필요 항목은 모두 API 요금 이야기라 이번 적용 판단에 영향이 없다.

## 3. 적용 전 상태

- 저장소 .claude/agents/ 없음. 설정 가이드 문서에는 "Haiku = 서브에이전트 전용" 한 줄만 있었다.
- 예약 작업 13개: 12개 claude-sonnet-5-5, Next 샌디스크 1개 claude-opus-5-5.
- 저장소에 Anthropic API 직접 호출 코드 없음 → 월 API 크레딧은 현재 쓸 곳 없음(향후 Agent SDK 자동화 때 재검토).

## 4. 적용한 것 (A)

| 파일 | 내용 |
|---|---|
| .claude/agents/test-runner.md | model haiku, effort low, 도구 Bash·Read·Grep·Glob. 테스트 실행 후 실패만 보고. 수정·apply·커밋·키움 도구·.env 금지 |
| .claude/agents/summarizer.md | model haiku, 도구 Read·Glob·Grep. 긴 로그·JSON·문서 요약. 요약은 위치 찾기용이며 판정 근거 아님 |
| CLAUDE.md Working rules | 전체 테스트는 test-runner(Haiku)로. Haiku 사용 범위 규칙 1개(Cowork는 Agent model "haiku") |
| 설정 가이드 문서(Claude Docs) | 모델 고르기의 Haiku 줄 갱신 |

쓰지 않는 곳: 투자 판단, 카드, 주문 가격·수량, K2/K3 검토, Judge. 이유: 판단 품질 우선, Haiku는 범위가 좁은 일에 맞는다는 공식 안내.

## 5. 예약 작업 시범 (B)

- 대상: "관제판 주간 점검 v1.1"(trig_01XvqwKG2gt7EKLEVMHGYR6Y). 판정을 check.py가 하고 모델은 도구 호출·결과 복사만 하므로 Haiku에 맞는다.
- 상태: Cowork에서 모델 변경 시도 → 서버 거부("device-bound routine은 모델 직접 변경 불가"). 2026-10-08 13:35 사용자가 데스크톱 앱 Scheduled 화면에서 claude-haiku-5-5로 변경 완료(지시문 내용 동일 확인, 다음 실행 10/10 10:50 KST).
- 판정 기준: 10/10·10/17 실행 결과를 Cowork가 관제판 실제 상태로 다시 계산해 대조한다. 놓친 항목 0이면 유지, 1건이라도 놓치거나 모델 탓 "점검 불완전"이면 Sonnet 복귀.
- 관제판 schedules/sch-boardreview 기록도 같은 시각에 갱신해 모델 변경으로 인한 R1 오탐은 없다.
- 다음 후보(시범 통과 후 별도 승인): SAVE 시장환경 메모, 미국주식 현황판. 통합 점검·재채점·이벤트 점검·Next 샌디스크는 판단이 들어가므로 유지.

## 6. 적용하지 않은 것

| 항목 | 이유 |
|---|---|
| settings.json의 CLAUDE_CODE_SUBAGENT_MODEL(_FORCE) | Builder의 코드 분석용 보조 에이전트까지 Haiku로 내려가 판단 품질이 떨어질 수 있음. FORCE는 에이전트별 지정도 무시 |
| 대화 전체 /model haiku | 메인 모델은 기존 표(Sonnet/Opus) 유지 |
| 기본 Explore를 Haiku로 덮어쓰기 | K2/K3 Builder가 Explore 결과로 수정 범위를 정함. 위치 누락은 fail-open 위험 |
| Bedrock 등 전체 모델명 지정 | 해당 없음(Anthropic 연결) |

## 7. 사용자 할 일

1. Claude Code 업데이트: Windows 터미널에서 `claude update` 후 `claude --version`이 2.1.293 이상인지 확인.
2. 관제판 주간 점검 모델 변경(5절).
3. 새 파일 커밋(worktree가 baseRef head라 커밋해야 Builder worktree에 보임).
4. (선택) Max·Team 요금제라면 월 API 크레딧 연결. 현재 시스템에는 쓸 곳이 없다.

## 8. 연결

- 읽는 곳: CLAUDE.md(모든 Claude Code·Cowork 세션), 관제판 작업 h55-haiku, 시범 판정 세션(10/10 이후 Cowork).
- 관련: docs/claude/skill-token-review-2026-10-02.md(토큰 절약), docs/claude/future-tools-roadmap-2026-10-05.md(도입 검토).

## 9. 출처

- https://www.anthropic.com/claude/haiku
- https://code.claude.com/docs/en/model-config
- https://code.claude.com/docs/en/sub-agents
- https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork
