---
id: external-claude-usage-tips-review-2026-10-19
type: external-review
status: current — 결정 완료 2026-10-19 21:58 KST 사용자 원문 "결정 cl-tips: 1 a, 2 a" → 4-1절대로 반영. 3번은 redesign-t4 입력(관제판 next ⑤에 등록). 나머지 NO_CHANGE
as_of: 2026-10-19 22:00 KST
tickers: [ALL]
evidence_grade: 사용법 자료(투자 증거 아님). 1차 출처 = Anthropic 공식 문서·Anthropic 블로그(claude.com·claude.dev). 인스타 게시물 2건은 안내일 뿐
consumers: 관제판 cl-tips(결정) · 관제판 redesign-t4 next ⑤(법률팀 정리 입력, 1절 3번) · ops-dev-touch-reduction R4(결정 2 a일 때) · 프로젝트 기억과 설정 가이드 문서(결정 1 a일 때)
weekly_user_touch: 0 (일회성: 결정 1줄)
summary: 인스타 2건(프롬프트 3원칙 · claude.dev 개발자 허브 소개)을 원문까지 따라가 투자_V2와 대조. 권고 대부분은 이미 반영돼 있다. 추린 것 — ① 기억·설정 가이드에 남은 낡은 규칙을 CLAUDE.md 기준으로 정리(결정) ② 리플레이 사전 등록에 노이즈 점검 1줄(결정) ③ CLAUDE.md의 규칙 손실 없는 정리 2곳은 T4 입력. 안전 문구가 든 긴 줄의 점진 공개는 NO_CHANGE.
---

# 외부 자료 검토 — Claude 사용법 게시물 2건 (2026-10-19)

## 0. 자료

| # | 게시물 | 내용 | 따라간 원문 |
|---|---|---|---|
| P1 | instagram.com/p/Deq4u96EWZg (yonkyeong_ai_cheat, 2026-10-19, 8장) | 프롬프트 필수 3가지: ① 새 직원에게 설명하듯 구체적으로 ② 이유를 같이 ③ 예시 3~5개. 6장 "한 문장 틀"(이유→구체적 요청→예시)은 편집부 제작(캡션에 명시, 원문 아님) | Prompting best practices — 3가지 모두 원문 확인 |
| P2 | instagram.com/p/Dd_KXk9gYhc (ai.brief.kr, 10/2 게시·수정됨, 7장) | claude.dev(Anthropic 개발자 허브, 9/30 공개) 소개. 읽을 글로 Opus 5.5 작업 비용, Sonnet 5.5 개발, Claude 5 컨텍스트 엔지니어링 규칙, eval 설계 자동화, 스킬 9유형을 꼽음 | claude.dev 글 8건 + claude.com 블로그 2건(5절) |

P2의 "2주 만에 3배" 슬라이드 수치는 원문과 이름이 다르다: 원문은 claude.ai 새로고침 후 입력 가능까지 3.1→0.55초, Claude Code 새 세션 0.8→0.3초, Cowork 메시지 전송 928→48ms(모두 p75)이고 앱 프런트엔드 속도 이야기다 — 적용 대상 아님.

## 1. 결론 — 추린 3가지

### 결정 1. 기억·설정 가이드의 낡은 규칙 정리 (충돌이라 T4를 기다리지 않음 — company-org-plan-2026-10-19.md:88)
- **원문**: 컨텍스트 규칙 글(2026-07-24) — 과한 제약은 CLAUDE.md·스킬·사용자 요청 사이에 서로 어긋나는 지시를 만든다. context-layer-audit 모드 1 "one canonical owner per fact".
- **어긋난 곳** (최신 = CLAUDE.md, HEAD 37a60ea):

| 곳 | 지금 문구 | 최신 |
|---|---|---|
| 프로젝트 기억 preferences 둘째 줄 | 설정이 다르면 시작 전 전환 요청 | CLAUDE.md:100~102 — 권한·한도·Judge 작업이 Opus가 아닐 때만 재시작 요청, 그 밖엔 진행(재설계 2026-10-10) |
| 기억 tuja-v2 Council 줄(2026-10-08) | 수량·가격이 있는 모든 매수·매도 권고는 위원회 | CLAUDE.md:89 정책·한도·권한 변경에만, 주문표는 결정론 관문 |
| 기억 tuja-v2 Decision journal 줄(2026-10-05) | 카드당 확인 코드 1개 | CLAUDE.md:29~34·92 — 사장의 결정 메시지가 확인, 별도 확인 코드 없음 |
| 기억 tuja-v2 Options layer 줄(2026-10-07) | 모든 주문가 결정에 4줄 | CLAUDE.md:88 옵션 자료가 있을 때만, 없으면 생략 |
| 기억 tuja-v2 user-touch 예산 줄(2026-10-09) | 평일 아침 1·주문일 저녁 1·토요일 1 | CLAUDE.md:95 "superseded 2026-10-10 by Goal" — 일상 접촉 0 |
| 기억 tuja-v2 Order instructions 2줄(10-06·10-07) — 후보, 사장 확인 | 봉인 SHADOW 시범 뒤 K3, 가격·수량 계산은 K3 뒤 | CLAUDE.md:5~8 주문 1단계 — 자동 코어가 LOC 주문표 발행(사람이 키움 입력). LOC 기본·사람 입력은 그대로 유효 |
| 설정 가이드 문서 "자동 적용 현황" 표, 모델·추론 노력 행의 사용자 칸 | "모델이 다르면 새 대화에서 그 값으로 선택" | CLAUDE.md:100~102 |
| 설정 가이드 문서 부록 A·B | 2026-09-30 초안 — 옛 프로젝트 지침("현재 PORTFOLIO_MANAGER_FIRST")과 옛 CLAUDE.md("from explicit user confirmation or a verified read-only broker snapshot" 등) | 현행 프로젝트 지침(AUTOMATED_OPERATION_FIRST)·CLAUDE.md:3~8·10~16 |
| 설정 가이드 문서 worktree 행 | Builder·Judge용 `claude --worktree <이름>` | 일반 변경은 개발 파이프라인(사장은 dev-merge 1번), worktree는 권한·한도·보호 경로(수동 경로)만 — CLAUDE.md Change classes |

- **a**: 기억 줄마다 끝에 "(2026-10-10 재설계로 대체: <현행>, CLAUDE.md:<행>)"을 덧붙인다(Order instructions 2줄은 "일부 대체"). 가이드는 위 두 칸을 고치고, 부록 A·B 본문은 "정본 = 프로젝트 지침·저장소 CLAUDE.md" 1줄로 바꾼다(사본을 다시 고치면 또 낡는다). CLAUDE.md는 바꾸지 않는다. **b**: 그대로(기억의 [stated] 줄과 사장 소유 문서는 승인 뒤에만 고친다).
- **같은 종류지만 이미 T4 몫**: 저장소 참조 문서 3곳이 일지 apply를 아직 "확인 <code>" 뒤로 적는다(manage-us-stock-strategy/references/decision-journal-cards.md:29, portfolio-exposure-review.md:43·331). 관제판 redesign-t4 next ①(확인 코드 경로 은퇴)에 이미 들어 있고, 그동안은 CLAUDE.md:29~34가 우선한다.
- **바뀔 조건**: 사장이 기억·가이드 쪽이 맞다고 하면 반대로 CLAUDE.md를 고치는 별도 안건이 된다.

### 결정 2. 리플레이 사전 등록에 노이즈 점검 1줄
- **원문**: eval 글(2026-09-28) "Claude checks that the eval's noise (how far the score can move by chance alone) is smaller than the smallest improvement you'd act on"; train/test 분할("If the train set scores improve while the test set scores stay flat, then that is a common overfitting warning sign").
- **투자_V2 현황**: 표본 외 여부와 "통과할 때까지 기준 바꾸기" 위험은 이미 다룬다(fx5b-r-rec1-redesign-preregistration-2026-10-09.md:16~17·124, scoring-calibration.md:61). f-evo-loop 사전 등록은 크기 기준을 일부러 비워 두었다: "크기 기준은 두지 않는다. 크기는 다음 리플레이에서 본다"(f-evo-loop-s1-preregistration-2026-10-16.md:273). 사전 등록 양식 파일은 따로 없고(docs/claude 목록), 사전 등록 문서는 .sha256으로 봉인돼 있다.
- **a**: CLAUDE.md:93이 가리키는 기본 처분 문서의 R4 행(ops-dev-touch-reduction-2026-10-09.md:47)에 1줄 — "사전 등록은 우연 변동폭을 구하는 방법(재표본 등)과 행동할 최소 개선폭을 고정하고, 결과 보고가 계산한 변동폭을 적는다. 차이가 변동폭 안이면 NO_CHANGE." 그 문서의 상태 줄이 "대체됨 2026-10-10"(:4)이라 같은 편집에서 "R4는 유효 — CLAUDE.md:93, automation-redesign-2026-10-10.md:127" 1구절을 더한다. 문서만, 코드·정책 변경 없음. 보류 중인 리플레이 입력은 별도 요청 때만 다루므로 실제 적용은 다음 리플레이부터. **b**: 이 문서에만 기록.
- **바뀔 조건**: 기존 기준(부호 일관성 + 표본·자료 조건)이 같은 역할을 이미 한다는 계산이 나오면 b.

### 3. (결정 불필요) CLAUDE.md 정리 2곳 → redesign-t4 입력
company-org-plan-2026-10-19.md:88("정리 안건은 T4 입력으로 쌓고, 충돌·안전 경계 위반만 바로 개정안")대로 관제판 redesign-t4 next ⑤(법률팀 정리 안건 자리)에 넣는다. ⑥의 기존 범위는 "키움 승인 고정 전환 문구"뿐이라 아래는 새 입력이다.
- **원문**: 컨텍스트 규칙 글 "Keep your CLAUDE.md lightweight…", "Avoid stating 'the obvious'…", 점진 공개("loading the right context at the right times"). 비용 글 "each line in it is part of what every turn resends", 200줄 미만.
- **현황**: CLAUDE.md 117줄 · 17,498바이트(줄 수 기준은 충족). 10/10 약 11KB → 10/19 17,515바이트(company-org-plan:89 법률팀 주간 지표).
- **넣을 것(규칙 손실 0)**: ① 95행 첫 문장 — 제목에 "superseded 2026-10-10 by Goal"이 있고 Goal(16행 "Routine user touches target 0…")과 중복. 주간 접촉 비용 표기와 개발 3개·권한 변경 1개 한도는 살아 있다(org-plan:77 인용). ② 88·89행 괄호 속 이력 — 결정 1이 a로 적용된 뒤에만(그 전엔 낡은 기억·가이드 줄을 가려내는 표지).
- **넣지 않을 것(NO_CHANGE)**: 90·91·93·97행 점진 공개. 이 네 줄은 fail-closed·매도 비차단·예산/한도/권한 불변·기본 처분 문구를 담고 있어, 문서를 못 열면 규칙이 빠지는(fail-open) 위험이 생긴다. 줄여서 얻는 것은 작다 — CLAUDE.md는 캐시되는 앞부분이고 Opus 5.5 캐시 읽기는 입력가의 5%($0.20/$4, 비용 글). 컨텍스트 글도 과한 제약을 피하되 "except in highly important areas"라 한다(스킬 권고 문장). 92·96행은 줄 본문이 Cowork 행동 규칙(일지 기록 위치, 사장에게 커밋을 시키지 않음)이라, 94행은 매 세션 읽히는 비용을 사장이 보고 승인해서(review-stability-2026-10-13.md:104) 제외.
- **T4 개정안 조건**: CLAUDE.md·AGENTS.md는 보호 경로라 경로를 명시(수동 경로 또는 문구만 고친 선례 + 사장 커밋), 커밋은 review-stability 5-4 한 줄(WAIT 조건)로, test_reconcile_broker_state.py:959~968이 두 파일 문구를 검사, AGENTS.md:90("rules live only in CLAUDE.md") 확인, 줄 수·순서를 유지하거나 줄 번호 인용(review-stability-2026-10-13.md:5·104, company-org-plan 여러 곳 — 95→94 밀림은 이미 발생)을 함께 갱신.
- 스킬 Gotchas 절(스킬 글 "The highest-signal content in any skill is the Gotchas section"; 투자_V2 스킬 5개 모두 0건)은 스킬 오작동 사례가 생길 때 그 스킬에 추가.

## 2. 이미 반영 — 바꿀 것 없음 (NO_CHANGE)

| 자료의 권고 | 원문 | 투자_V2 현황(근거) |
|---|---|---|
| 새 직원처럼 구체적으로 · 완료 기준 명시 | 프롬프트 문서 "brilliant but new employee"; Opus 5.5 글 "Say what 'done' looks like" | 빌더 지시문이 목표 · 동치 명세 · 바꿀 것 · 바꾸지 않는 것 · 테스트 · "그 밖이 필요하면 멈추고 보고"(rrec-ev4-remove-builder-prompt.md:16·20·40·68·72·83) |
| 이유를 같이 말하기 | 프롬프트 문서 "Claude is smart enough to generalize from the explanation." | CLAUDE.md 규칙 다수가 이유를 함께 적음(예: Kiwoom 줄 "Without the profile the call uses an old token and fails with 8005", 재인증 금지 이유 "it can invalidate another task's token") |
| 읽기 실패를 "조용한 날"로 보지 않기 | 자동화 글(10-08) | 통합 점검 "점검 상태" 정상 조건(integrated-check-prompt-v3.12.8:158), 공시 피드 STALE_OR_FAILED(:84), 이벤트 점검 "못 얻으면 확인 필요" + --check-record(7·8단계), 현황판 조회 실패 시 raw 안 덮음(us-stock-board-close.txt:23~24) |
| 규칙 파일을 매 실행 새로 읽고, 못 읽으면 기본값으로 돌지 않기 | 자동화 글 "If it can't read the file, it should stop and say so instead of running on defaults" | 로더: 규칙 파일 해시 불일치·미접근이면 판정·기록 없이 "통합 점검 중단" 알림(scheduled-prompts/integrated-check-daily.txt:22~23). 카드 묶음 등 보조 문서는 "문서 미접근" 표시 후 계속(integrated-check-prompt-v3.12.8:47) |
| 외부 텍스트는 지시가 아님 · 피해 범위 제한 | 자동화 글 | SAVE 문구 = 데이터(save-market-memo.txt:8), 키움 읽기 전용 · 주문 0, 외부 주장 증거 0 |
| 시간대 명시 | 자동화 글 | 주간 회의 0)단계 TZ=Asia/Seoul, 종가 기준일 기록(integrated-check-prompt-v3.12.8:59) |
| 쓰기 직전 재검증 | 자동화 글 "never hedge an item's status" | 기록 전 검증 run-doc.json(integrated-check-prompt-v3.12.8:175~179) |
| 기존 결함과 새 결함 분리 · 리뷰 수렴(라운드 상한) · 위험도별 사람 승인 | 코드 리뷰 글(10-15) | 새 실패 = 실패 − 기준선(tools/dev_pipeline/README.md:84), 재시도 1회(:87), 문서만이면 Judge 생략 · 권한 변경은 수동 경로 + 사장 승인(CLAUDE.md Change classes) |
| 하위 에이전트 보고는 증거를 확인하고 받기 | Opus 5.5 글 "check its evidence before you accept it" | V5: 발견마다 원문을 다시 열어 반영(review-stability-2026-10-13.md:59) |
| 확인 못 한 것 표시 + 어디 봤는지 | Opus 5.5 글 | "확인 필요" 규칙 + 검토 완결 끝 줄 "원문 확인 n/m" |
| "막힌 것 · 바뀐 것 · 발견" 보고 머리 | Opus 5.5 글 | 주간 팀장회의 보고(결정 자격 · 발견 · 팀 제안 — scheduled-prompts/ceo-weekly-meeting.txt:33·46) |
| "think hard" 류 문구 삭제 | Opus 5.5 글 | CLAUDE.md · AGENTS.md · 예약 지시문에 해당 문구 0건(grep) |
| 스킬 description = 언제 쓰는지 | 스킬 글 "the description field is not a summary, it's a description of when to trigger this skill" | 계정 스킬은 트리거·제외 조건 형태(예: context-layer-audit "…when docs drift… Not for routine writing or debugging."). 저장소 스킬 manage-us-stock-strategy는 기능 요약 + 트리거("Use when Codex is asked…", Codex 표기), 제외 조건 없음(SKILL.md:3) |

## 3. 채택하지 않음 · 보류

| 항목 | 이유 | 바뀔 조건 |
|---|---|---|
| 예시 3~5개(P1 ③) | 두 Anthropic 원문이 엇갈린다: 프롬프트 문서 "Include 3–5 examples for best results" ↔ 컨텍스트 글 "giving examples actually constrains them to a certain exploration space". 투자_V2의 고정 형식 출력(주간 보고·대시보드)은 이미 코드(ceo.py)와 형식 명세가 만들어 예시가 필요 없다 | 특정 출력의 형식이 반복해서 흔들리면 그 출력에만 `<example>` 3개 |
| effort 표 변경 | 비용 글: Opus 5.5 일상 = medium, "keep xhigh and max for work where you've measured a gain". Sonnet 5.5 글: agentic coding은 잘 정의된 일 medium·어려운 일 high, "Use xhigh or max only where your evals show a quality gain". 현행(CLAUDE.md:100 루틴 medium · 분석·개발 high · K3·Judge Opus xhigh, Claude Code 기본 effortLevel medium — .claude/settings.json)과 모순 없음. xhigh는 측정 없이 정한 값이지만 낮춰서 생길 놓침 위험도 측정이 없다 → 기본 처분 | 같은 Judge 과제를 high·xhigh로 한 번씩 돌려 발견이 같으면 high로 |
| 병렬 탐지 + 투표형 리뷰 | 내장 재검토 한 번이 이미 17만~23만 토큰(review-stability-2026-10-13.md:104; 이번 검토도 1회차 약 29만·2회차 약 38만). 여러 에이전트 투표는 그 몇 배 | 재검토가 놓친 오류가 다시 나올 때 |
| 스킬 사용량 측정 hook | 저장소 설정 기준 hook 0개(.claude/settings.json; 사용자 홈·플러그인 hook은 확인 필요), 새로 만들면 .claude/** 보호 경로. 미충족 요구 없음 | 스킬이 안 불린 사례 관측 |
| manage-us-stock-strategy 스킬 유형 분리 | 여러 유형에 걸치지만 references 40여 개로 이미 점진 공개. 재구성 이익 검증 불가 | 스킬 오작동 사례 |
| 통합 점검 지시문 prompt-audit | 규칙 파일이 278줄 · 95,620바이트로 크지만 코어의 유일한 LLM 입력(연구 기록)을 만드는 작업이라 바꾸면 위험. T4가 이미 "통합 점검 82KB 규칙(→ 짧은 설명 작업)" 은퇴를 계획(automation-redesign-2026-10-10.md:145) | T4 착수, 또는 실행당 토큰·한도 소진 기록 |
| 북마크 방식 읽기 | SAVE 종목 단서는 72시간 창(필수 단서 168시간, save-market-memo.txt:193)이라 겹칠 뿐 빈틈 없음 | 단서 누락 사례 |
| 실행당 예산 상한 | 예약 작업 만들기 도구에 예산 칸이 없다. 추가 사용량은 꺼져 있음(2026-10-09 기준) | 플랫폼이 예산 칸을 제공할 때 |

## 4. 결정 문구
`결정 cl-tips: 1 a, 2 a` (권장). 각 번호 b = 현행 유지. 무응답 기한 2026-10-26 09:00 KST → 1·2 모두 b.

## 5. 출처 (조회 2026-10-19 21:05~21:55 KST. 웹 글은 WebFetch 요약 도구를 거친 인용 — 원문 대조가 필요하면 링크를 직접 연다)
- P1: https://www.instagram.com/p/Deq4u96EWZg/ (내장 브라우저로 캡션 · 8장 확인)
- P2: https://www.instagram.com/p/Dd_KXk9gYhc/ (내장 브라우저로 캡션 · 7장 확인)
- Prompting best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- The new rules of context engineering for Claude 5 generation models (2026-07-24): https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models
- Lessons from building Claude Code: How we use skills (2026-06-03): https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills
- Building effective agent automations (2026-10-08): https://claude.dev/blog/building-effective-agent-automations/
- Automating eval design and hillclimbing (2026-09-28): https://claude.dev/blog/automating-eval-design-and-hillclimbing/
- How the Claude Code team does code review (2026-10-15): https://claude.dev/blog/solving-code-review-at-anthropic/
- What a task costs on Opus 5.5 (2026-09-25): https://claude.dev/blog/what-a-task-costs-on-opus-5-5/
- Using Claude Code: Spending your effort (2026-09-25): https://claude.dev/blog/spending-your-effort/
- Getting the most out of Opus 5.5 (2026-09-22): https://claude.dev/blog/getting-the-most-out-of-opus-5-5/
- Building with Claude Sonnet 5.5 (2026-09-28): https://claude.dev/blog/building-with-claude-sonnet-5-5/
- How we made claude.ai 3x faster in two weeks (2026-09-23): https://claude.dev/blog/how-we-made-claude-ai-faster/
- 설정 가이드 문서: https://claude.ai/code/artifact/8a84d9d6-7dd8-4806-b25b-fc65d3a8f8ea (Claude Docs로 읽음)
- 저장소 원문: CLAUDE.md(HEAD 37a60ea)와 위 표의 파일:행. 프로젝트 기억 preferences.md·areas/tuja-v2.md(이 세션에서 읽음). 관제판 tasks/redesign-t4(version 4)

## 6. 검토 기록
- 1회차 내장 재검토(Sonnet, 약 21:22~21:36 KST): 18건, "바꿈" 9건. 원문 재확인 후 반영 — 결정 1을 "점진 공개 지금"에서 "어긋남 정리(충돌)"로 바꾸고 범위를 기억·설정 가이드까지 넓힘, 점진 공개는 T4 입력으로 돌림(org-plan:88), 보존 문구·제외 줄·AGENTS.md:90·테스트·5-4 커밋 순서 추가, 노이즈 줄 위치를 R4 행으로 정하고 f-evo-loop:273 반영, "규칙 파일 못 읽음" 근거를 로더 22~23행으로 정정, 수치 정정(168시간, 3x 원문 수치), 예시 양쪽 인용, 스킬 설명 행 정정, Sonnet 5.5 글 열어 effort 행 보강, hook·예산 칸 확인. "캐시 읽기 5% ↔ 10%" 지적은 모델 차이(Opus 5.5 $0.20/$4, Sonnet 5.5 $0.20/$2)라 모순 아님.
- 2회차(바뀐 부분만, Sonnet, 약 21:39~21:53 KST): 15건, "바꿈" 7건. 원문 재확인 후 반영 — 결정 1 범위를 기억 7줄(Order instructions 2줄은 후보)·가이드 3곳(자동 적용 현황 사용자 칸, 부록 A·B, worktree 행)으로 정정하고 가이드의 "추론 노력 고르기" 표는 어긋남이 아님을 확인, 참조 문서 3곳의 "확인 <code>"는 T4 ① 몫으로 명시, 3번 근거를 org-plan:88 + 관제판 redesign-t4 ⑤·⑥으로 정정(automation-redesign:145에는 CLAUDE.md 정리 없음), 3번을 규칙 손실 0 정리 2곳으로 좁히고 90·91·93·97 점진 공개는 NO_CHANGE(fail-open 위험 > 캐시 때문에 작은 이익), 88·89 이력 정리는 결정 1 a 뒤로, R4 문서 상태 줄 보강과 노이즈 문구(방법·최소 개선폭 고정, 변동폭은 결과 보고에서), 변경 경로·줄 번호 인용 조건, 날짜·범위 단서.
- 미해결(기본 처분 — 알림만): 가이드 첫 표 "화면 배치" 행이 파이프라인과 어긋난다는 2회차 지적은 이 세션에서 원문 위치를 찾지 못함(확인 필요, 결정 1 a 적용 때 함께 확인) · claude.ai 프로젝트 지침(커널) 본문과 CLAUDE.md의 전면 대조는 하지 않음.
