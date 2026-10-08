# 프롬프트 캐싱 문서 검토 (2026-10-09)

- 원본: Claude Platform Docs "프롬프트 캐싱"(platform.claude.com/docs/ko/build-with-claude/prompt-caching, 2026-10-09 열람). 함께 대조: Claude Code 문서 prompt-caching, costs.
- 변경 등급: K0(지침 문구). 런타임·정책·권한·settings.json 변경 없음. order_authority=false.
- 사용자 승인: 2026-10-09 Cowork, "1~4 모두". 추가 사용량(usage credits)은 꺼져 있음(사용자 확인 2026-10-09).

## 1. 결론

문서의 캐싱 설정(cache_control, TTL)은 지금 투자_V2에 적용할 곳이 없다. 설정은 그대로 두고, 설정 가이드와 CLAUDE.md의 캐시 관련 문구 중 틀리거나 낡은 곳만 바로잡았다.

## 2. 적용 대상 판단

| 대상 | 판단 | 이유 |
|---|---|---|
| API 요청의 cache_control(자동·명시 중단점) | 해당 없음 | 저장소에 Anthropic API 호출 코드 없음(2026-10-08 확인) |
| Claude Code 메인 대화 TTL(promptCacheTtl) | 변경 안 함 | 구독 한도 안에서는 이미 1시간. 추가 사용량이 꺼져 있어 5분으로 내려가는 경우가 없음 |
| 보조 에이전트 TTL(subagentPromptCacheTtl, 에이전트 cacheTtl) | 변경 안 함 | test-runner·summarizer는 짧은 단발 작업. 1시간 저장은 입력가의 2배, 5분은 1.25배 |
| DISABLE_PROMPT_CACHING* | 쓰지 않음 | 디버깅용 |
| ENABLE_PROMPT_CACHING_1H, FORCE_PROMPT_CACHING_5M | 쓰지 않음 | 기본값이 이미 맞음 |
| 상태줄 prompt_cache 표시 | 도입 안 함 | /usage의 "Prompt cache (main)" 줄로 충분 |
| Chat·Cowork·예약 작업 | 설정할 곳 없음 | 플랫폼이 자동 관리. 예약 작업은 실행마다 새 세션 |

## 3. 바로잡은 문구

| 이전 | 수정 | 적용 위치 |
|---|---|---|
| 추론 노력을 중간에 바꾸면 캐시가 깨진다 | Claude Code의 Opus 5.5·Sonnet 5.5(구독)는 /effort를 바꿔도 캐시 유지. 모델 변경은 여전히 깨짐. Haiku·Chat·Cowork는 확인 필요라 기존대로 시작 때 정함 | 설정 가이드, CLAUDE.md Session hygiene |
| MCP 서버를 붙였다 떼면 캐시가 깨진다 | 도구 검색이 켜진 기본 상태에서는 유지 | 설정 가이드 |
| 구독 캐시는 1시간 | 메인 대화만 1시간(구독 한도 안). 보조 에이전트 5분, 추가 사용량 사용 중에는 메인도 5분 | 설정 가이드 |
| (없음) | CLAUDE.md 수정은 실행 중인 세션에 반영되지 않음. /clear·/compact·재시작 뒤 적용. /usage의 "Prompt cache (main)" 줄로 적중률·놓친 원인 확인(v2.1.251+) | 설정 가이드 |

## 4. 확인한 수치 (공식 가격표, 100만 토큰당 달러)

| 모델 | 입력 | 5분 저장 | 1시간 저장 | 캐시 읽기 |
|---|---|---|---|---|
| Opus 5.5 | 4 | 5 | 8 | 0.20 |
| Sonnet 5.5 | 2 | 2.50 | 4 | 0.10 |
| Haiku 5.5(10만 토큰 이하) | 0.10 | 0.125 | 0.20 | 0.01 |

- Opus 5.5·Sonnet 5.5의 캐시 읽기는 입력가의 0.05배(다른 모델은 0.1배).
- 캐시 최소 길이: Opus 5.5·Sonnet 5.5·Haiku 5.5 모두 512토큰. 중단점 최대 4개, 되돌아보기 20블록.

## 5. 나중을 위한 설계 메모 (API·Agent SDK 자동화 단계)

최종 목표인 자동 점검·매매를 API나 Agent SDK로 만들 때 적용한다. 지금은 적용하지 않는다.
1. 요청 최상위 cache_control(자동 캐싱)로 시작한다. 지침·정책처럼 잘 안 바뀌는 내용을 앞에, 시세·시각·당일 데이터처럼 매번 바뀌는 값을 마지막 중단점 뒤에 둔다.
2. 요청 간격이 5분을 넘고 1시간 안에 같은 앞부분을 다시 쓸 때만 1시간 TTL이 이득이다. 하루 1~2회 도는 점검은 실행 사이에 캐시가 남지 않으므로 기대하지 않는다.
3. 응답의 cache_creation_input_tokens·cache_read_input_tokens로 적중률을 기록한다.
4. 캐시는 같은 앞부분 처리를 재사용할 뿐 출력 내용을 바꾸지 않는다. 증거 원문·해시·fail-closed 원칙과 충돌하지 않는다.

## 6. 확인 필요

- Chat·Cowork에서 추론 노력을 중간에 바꿀 때 캐시가 유지되는지(공식 문서는 Claude Code 기준).
- Haiku 5.5의 노력 변경 시 캐시 유지 여부(Claude Code 문서는 Opus 5.5·Sonnet 5.5·Fable 5.1만 명시).

## 7. 연결

- 읽는 곳: CLAUDE.md Session hygiene(모든 Claude Code·Cowork 세션), 설정 가이드 문서(토큰 절약 절), docs/claude/haiku-5-5-review-2026-10-08.md(가격 확인 행).
- 5절은 자동매매 단계 설계 때 참고한다(docs/claude/future-tools-roadmap-2026-10-05.md의 주문 권한 단계와 함께 검토).

## 8. 출처

- https://platform.claude.com/docs/ko/build-with-claude/prompt-caching
- https://code.claude.com/docs/en/prompt-caching
- https://code.claude.com/docs/en/costs
