# 외부 Claude 스킬 3종 검토: 투자_V2 도입 여부 (2026-10-02)

- 상태: 3절 점검표 적용(2026-10-02, 사용자 승인). 그 밖의 항목은 적용하지 않음.
- 대상(클라우드 작업공간에 shallow clone, 읽기 전용. 설치·실행 없음):
  - `obra/superpowers` v6.4.2, 커밋 `8ca22db`(2026-09-25), MIT
  - `multica-ai/andrej-karpathy-skills`, 커밋 `2c60614`(2026-04-20). README·plugin.json에 MIT 표기, LICENSE 파일 없음
  - `affaan-m/ECC`, 커밋 `ef648e0`(2026-10-01), MIT
- 판단 기준: 커널 §7 검토 순서(NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD)와 "명시적 미충족 요구 + 검증 가능한 이익", 설치 전 토큰·보안·기존 결정 검토, gstack 도입 선례(`docs/gstack-development-adoption.md`: 프로젝트 참조 문서로 재작성, 설치·훅·명령 없음).

## 0. 결론

1. 세 저장소 모두 설치하지 않는다(플러그인, 훅, 전역 스킬, 규칙 복사 모두).
2. 도입 제안 1건: **fail-open 점검표**. ECC `agents/silent-failure-hunter.md`의 아이디어에 S7-1 Judge가 찾은 결함 유형(a~f)을 채워 `references/development-change-review.md`에 한 소절로 넣는다. K0, 고정 파일 아님.
3. 보류 1건: "다른 수정을 3번 해도 실패하면 멈추고 보고"(superpowers systematic-debugging). 관찰된 사례가 없어 지금은 넣지 않는다.
4. 그 밖의 유용한 관행은 투자_V2에 이미 더 엄격하게 있다(2절).

## 1. 저장소별 판정

| 항목 | superpowers | andrej-karpathy-skills | ECC |
|---|---|---|---|
| 구성 | 스킬 15, SessionStart 훅 1 (명령·에이전트 없음) | CLAUDE.md 1개(2,357 B) + 같은 내용 스킬 1 + Cursor 규칙 | 스킬 293, 에이전트 68, 명령 94, 규칙 파일 122, 훅 24개(이벤트 7종) |
| 상시 토큰(추정, bytes/4) | 세션마다 약 1.5k: 시작·`/clear`·`/compact`마다 using-superpowers 전문 주입(약 0.85k) + 스킬 목록(약 0.65k). 개발 한 번 흐름에 스킬 본문 약 2만 | CLAUDE.md에 붙이면 세션마다 약 0.6k(현 CLAUDE.md 3.7 KB의 64% 증가) | 스킬 목록 약 23.6k + 에이전트 설명 약 3.8k + `rules/common` 약 4.6k + 세션 시작 주입 최대 8,000자. 약 3만 토큰대(Claude Code의 목록 축약 여부 확인 필요) |
| 보안·데이터 | "1%라도 해당하면 반드시 스킬 사용"(`skills/using-superpowers/SKILL.md:11`). 계획 단계마다 커밋, 브랜치 마무리 스킬이 merge·push·브랜치 삭제(`skills/finishing-a-development-branch/SKILL.md:94-156`). worktree 스킬이 pip/poetry/npm install 자동 실행(`skills/using-git-worktrees/SKILL.md:108-115`). 업데이트 "often automatic"(README). 시각 도우미가 외부 로고를 받으며 버전 전송(끌 수 있음) | 낮음(문서뿐) | 훅 기본 켜짐(`.claude-plugin/plugin.json` hooks_enabled 기본 true, profile standard). 모든 도구 입력·출력을 필드당 5,000자까지 저장소 밖에 기록(`skills/continuous-learning-v2/hooks/observe.sh:238-245`, 키움 조회 결과 포함 가능). MCP 호출 전 `~/.claude.json`의 MCP 서버를 따로 띄워 점검하고 실패하면 호출 차단(`scripts/hooks/mcp-health-check.js:70-72, 420-427, 769`). `claude --model haiku -p` 요약 호출(`scripts/lib/llm-summary.js:153`). 학습된 "instinct" 자동 주입(`scripts/hooks/session-start.js`). Python 규칙이 black/ruff 자동 포맷 권장(`rules/python/hooks.md:14`) |
| 기존 결정과 충돌 | 커밋·병합은 사용자가 Windows 터미널에서(P4), CLAUDE.md "Do not commit or push unless asked", K3 멈춤 ↔ "Do not pause to check in"(`skills/executing-plans/SKILL.md:27`), Judge는 별도 세션 ↔ 같은 세션 리뷰 서브에이전트 | 없음(전부 중복) | gstack 선례(훅·설치 없음), AGENTS.md "Reflection may record lessons but may not mutate policy", 해시 고정 파일(자동 포맷이 바이트를 바꾸면 acceptance 무효 = K3), `rules/common/testing.md:3` 커버리지 80% 강제 |
| 판정 | 설치 안 함. 관행은 대부분 이미 있음 | 설치·추가 안 함(NO_CHANGE) | 설치 안 함. 아이디어 1건만 각색 |

## 2. 이미 있는 것 (NO_CHANGE)

| 외부 관행 | 투자_V2의 기존 장치(근거) |
|---|---|
| Karpathy 4원칙: 가정 명시, 단순함, 외과적 변경, 검증 가능한 목표 | 커널 §7 검토 순서·"복잡도는 명시적 요구가 있을 때만", CLAUDE.md "multi-file edits 전 계획", Builder 지시문 "바꿔도 되는 파일(이것만)… 목록 밖을 바꿔야 하면 멈추고 묻는다", 기존 단언 변경 금지, 값 고정, 테스트 T1~T11과 목표 "새 실패 0"(`s7-split-adjustment-builder-prompt-2026-10-02.md` 3절) |
| superpowers verification-before-completion | Builder 마지막 줄 "새 실패 수 N", Cowork 읽기 전용 재확인, Judge가 테스트 직접 실행(`s7-1-judge-prompt-2026-10-01.md` J9) |
| superpowers TDD(실패하는 것 먼저 보기) | "테스트를 먼저 쓴다… 고치기 전 코드에서의 실패 수를 보고에 적는다"(같은 지시문 1단계), 실제 보고(`s7-u3-cash-flow-evidence-builder-report-2026-10-02.md`: 수정 전 18건 실패) |
| superpowers 테스트 기대값을 대상 코드와 독립으로 | T1 "V 값 = 미리 나눈 종가로 계산한 값", Judge J8 "동어반복·항상 참 아님"(`s7-calendar-binding-judge-prompt-2026-10-02.md`) |
| 실패 테스트를 개수가 아닌 이름으로 비교 | 기준선 실패·오류 ID 목록 정렬 diff(`s7-u3-cash-flow-evidence-builder-report-2026-10-02.md` "두 ID 목록은 정렬 후 diff로 동일") |
| superpowers systematic-debugging, ECC 디버깅 | `references/development-incident-analysis.md`(gstack 각색: 근거·가설·최소 확인·같은 실패 반복 중단) |
| superpowers 재검토 때 지적별 해소 확인 | S6 재확인 r1·r2: 필수 수정 항목마다 OK/부족(파일:행), 새 fail-open 확인(`s6-judge-prompt-2026-10-01.md` 6~7절) |
| superpowers·ECC 리뷰어 에이전트 | `references/development-change-review.md` + 별도 세션 Independent Judge(J1 범위, J9/J12 적대 점검) |
| superpowers worktree | `claude --worktree <name>`, Judge 별도 worktree |
| ECC "테스트를 고쳐서 통과시키지 않기" | P4 "전 기간 금지: 테스트 약화", incident-analysis "Do not weaken a validator" |
| ECC `--no-verify` 차단 훅 | pre-push 훅(main 직접 push 차단), settings.json `git commit`·`git push` ask, 커밋은 사용자가 직접 |
| ECC strategic-compact, 세션 저장 | CLAUDE.md Compact instructions, `docs/claude/` 인계 문서 |

## 3. 도입 제안: fail-open 점검표 (K0)

**근거(관찰된 실패):** S7-1 Judge(2026-10-02)는 Builder가 "새 미통과 0"으로 보고한 결과에서 fail-open 성격 결함 6건을 찾았다(`s7-builder-prompt-2026-10-01.md` 9.1 a~f). 테스트는 통과했지만 판단 경로가 열려 있었다.

| 유형 | S7-1 사례 |
|---|---|
| 일부 누락을 완전한 입력처럼 처리 | c: 창 안 종가 하나 누락으로 252 → 69로 줄었는데 V가 "확인됨" |
| 오래된 입력을 최신처럼 처리 | d: 8/29까지인 달력에서 8/28을 최근 완료 세션으로 평가 |
| 근거 없음 → 허용 | e: 원장 줄 없는 스냅샷 사용, 미신고 현금이 수익으로 |
| 모르는 값을 아는 분류에 넣음 | f: "수수료출금"을 출금(TRANSFER)으로 분류 |
| 일부 실패 사유만 막는 판정(새 상태가 빠져나감) | a: `HELD`에서 R0 안 켜짐 / b: 적용 시작 후보가 R0 일부만 보고 READY |

**위치:** `manage-us-stock-strategy/references/development-change-review.md`의 "Assess concrete defects" 아래 새 소절. deployment_gate 고정 6개·acceptance 고정 16개에 들지 않는다. SKILL.md·AGENTS.md·CLAUDE.md는 바꾸지 않는다.

**문안 초안(영문, 기존 문서 언어에 맞춤):**

```
### Fail-open patterns

Check every changed decision path for these shapes. Each one turns missing
or doubtful evidence into a normal-looking result:

- Partial treated as complete: a gap shortens a window, list or history and
  the result is still marked verified; a warning label is not a block.
- Stale treated as current: an old session, snapshot, calendar or ledger is
  used without proving it covers the evaluated date.
- Missing evidence treated as permission: an absent record, ledger line or
  journal entry yields READY/OK instead of a blocking reason.
- Unknown mapped to known: unrecognized text, category or status falls into an
  existing class instead of UNCLASSIFIED and a stop.
- Deny-list gates: READY/PASS excludes a few named failures instead of
  requiring every precondition, so a new or intermediate state passes.
- Swallowed errors: a broad except returning None/{}/[]/0, `.get(key, 0)` on
  price, quantity or cash, or a lost traceback.

Idea adapted from affaan-m/ECC agents/silent-failure-hunter.md (MIT, commit
ef648e0); patterns from the S7-1 Judge fixes (2026-10-02).
```

**Builder 지시문(파일 변경 없음):** Cowork가 다음 K2/K3 Builder 지시문의 보고 단계에 한 줄 더한다. "보고 전 자기 점검: change-review의 Fail-open patterns 6개를 바꾼 판단 경로마다 확인해 '해당 없음/처리함(테스트 이름)'으로 적는다."

**비용:** 문서를 읽을 때만 약 250토큰. 상시 로드·설치·훅 없음.

**효과 확인과 되돌리기:** 다음 K2/K3 Judge 2~3회에서 fail-closed 관련 FIX 건수를 기록한다. 줄지 않으면 소절을 지운다(REMOVE). 되돌리기는 이 소절 삭제 하나다.

## 4. 보류 (관찰만)

- **수정 3회 실패 시 멈춤**(superpowers `skills/systematic-debugging/SKILL.md:195-198`, "If ≥ 3: STOP and question the architecture"). 지금 incident-analysis는 "같은 실패 반복"만 막는다. Builder가 서로 다른 수정을 여러 번 헛도는 사례가 아직 없다. 생기면 incident-analysis에 한 줄 더한다.
- **Judge 지시문 유도 문구 금지**(superpowers SDD 리뷰어 템플릿). 최근 Judge 지시문 3개(S6, S7-1, S7 달력)를 간단히 검색해 유도 문구를 찾지 못했다. 넣지 않는다.

## 5. 넣지 않을 것

- 세 저장소의 설치(플러그인, `npx`, `install.sh`/`.ps1`, 전역 스킬, `rules/` 복사): 1절의 토큰·보안·충돌.
- ECC 훅 전체, continuous-learning·instinct(지시를 자동으로 바꿈), `rules/common`(커버리지 80% 강제 등), AgentShield(코드가 저장소 밖 패키지라 확인 불가).
- ECC 금융 관련 스킬(`market-research`, `investor-*`, `ito-baskets`, `prediction-market-*`, `llm-trading-agent-security`): 창업 자금 조달·예측시장·지갑 거래 대상이라 미국주식 read-only 판단 지원과 맞지 않는다.
- Karpathy CLAUDE.md 추가: 내용이 모두 중복이고 세션마다 약 0.6k 토큰이 는다.
- superpowers 계획·실행 흐름(brainstorming → writing-plans → executing-plans/SDD → finishing): 사용자 git, K3 멈춤, 별도 세션 Judge 구조와 충돌.

## 6. 확인 필요

- ECC 스킬 293개 설명이 Claude Code에서 모두 상시 로드되는지(목록 축약 여부). 1절 ECC 토큰은 상한 추정이다.
- ECC `mcp-health-check`가 이 PC의 키움 MCP 설정에서 실제로 어떻게 동작하는지. 설치하지 않으므로 확인하지 않았다.
- superpowers 자동 업데이트는 하네스·마켓플레이스 설정에 따라 다르다.

## 7. 설계 구상용 참고 스킬 (2026-10-02 추가, 설치 없음)

시스템에 넣지 않는다. 설계 작업을 시작할 때 Cowork가 고정 커밋의 원문을 읽어 사고 도구로만 쓴다. 두세 번 써서 쓸모가 확인되면 그때 gstack처럼 참조 문서로 각색할지 검토한다.

| 순위 | 스킬(ECC 커밋 `ef648e0`) | 쓸 곳 | 핵심 |
|---|---|---|---|
| 1 | `skills/loop-design-check/SKILL.md` | S7b 결정 원장·채점기, 통합 정기 점검 개선, 장기 GUARDED_AUTONOMOUS 단계 | 루프마다 기계가 판정할 수 있는 완료 기준 + "하면 안 되는 것" 경계 + 재시도 상한. 자기 단언보다 외부 대조. 무인 실행은 중간에 묻지 못하니 모호함을 미리 정리. 실패 유형 5개와 레드라인 3개(판단은 사람, 책임은 넘기지 않음, 스스로 규칙을 고치는 루프일수록 검토 강화) |
| 2 | `skills/living-docs-governance/SKILL.md` | 문서 단순화(REMOVE/SIMPLIFY) | 기존 문서에 헌법·지도·상태·이력 4역할 배정, 사실마다 원본 하나, 일부러 없앤 것의 "삭제 구역"(스크린샷 경로, EMA 슬롯 은퇴, 기각된 S4-3 후보 등)으로 새 세션의 재발명 방지. 새 파일보다 역할표부터 |
| 3 | `skills/council/SKILL.md` | 선택지가 팽팽한 K3급 go/no-go 결정 | 회의론자·실용주의자·비판자 서브에이전트 3개에 질문과 최소 맥락만 줘 앵커링을 막고, 가장 강한 반대 의견을 결론에 남긴다. 비용은 답 한 번의 약 3~4배라 드물게 쓴다 |
| 참고 | `skills/agent-architecture-audit/SKILL.md` | 분석 결과가 일반적·보수적으로 흐를 때 원인 진단 | 12층 목록(지침 비대·충돌, 메모리 오염, 요약본이 사실처럼 재유입, 만료 상태를 현재 근거로 재사용 등)만 쓴다. 코드용 grep은 이 시스템에 맞지 않는다 |

**loop-design-check 실패 유형과 현재 대조:**

| 실패 유형 | 투자_V2 현재 |
|---|---|
| 1 기계가 판정 못 하는 목표 | Builder는 "새 실패 0"과 지정 테스트로 판정 가능. 카드 판단 품질은 "판단에 씀"(주관 평가)뿐이라 S7b 사후 채점이 이 빈칸 |
| 2 실행자가 스스로 판정 | Judge는 별도 세션. S7b 채점기도 카드 작성 경로와 독립이어야 한다 |
| 3 경계 없는 완료 기준 | 테스트 약화·기존 단언 변경 금지로 막음 |
| 4 실행 중 질문에 기대 | 예약 점검은 무인 실행. 모호할 때의 처리 규칙이 프롬프트에 있는지 확인 필요 |
| 5 비대한 지침·낡은 기억 | P4 로드맵 약 90 KB, `docs/`·`docs/claude/` 문서 100개 이상 → 2순위와 연결 |

넣지 않은 것: superpowers `brainstorming`(선택지 2~3개 + 추천 + 승인은 Cowork 결정 요청 방식에 이미 있음), ECC `santa-method`(Judge 2명 = 비용 2배), `agentic-os`·`blueprint`·`architecture-decision-records`·`intent-driven-development`·`product-lens`(커널·plan-review·Builder 지시문·§9 기록과 중복이거나 대상이 아님). ECC `eval-harness`의 pass^k(같은 입력을 여러 번 돌려 모두 같은 판단이 나오는지)는 S7b 채점기 설계 때 카드 판단 일관성 측정 아이디어로만 검토한다.

## 8. 계정 스킬 설치 (2026-10-02, 사용자 요청)

사용자 요청: "ECC 추천 스킬 4개만 우선 설치, 필요한 상황에서 자동 활용". 원문을 그대로 넣지 않고 투자_V2에 맞게 줄여 각색한 계정 스킬(claude.ai) 3개로 제안했다. 제안 카드 한 장에 최대 3개라 문서 정리와 품질 진단을 한 스킬의 두 모드로 합쳤다. 기능 4개는 모두 들어 있다.

| 계정 스킬 | 원본(ECC `ef648e0`) | 자동 사용 조건(설명문) |
|---|---|---|
| `loop-design-check` | `skills/loop-design-check` | 반복 루프(Builder→Judge, 예약 점검, 대조→카드→원장→채점, 자동화 확대) 설계·수정, 헛돌기·검증 속이기 의심 |
| `decision-council` | `skills/council` | 시스템·개발·운영의 팽팽한 K3급 결정·go/no-go, 사용자가 반대 의견 요청. 매매는 사용자가 명시할 때만 |
| `context-layer-audit` | `skills/living-docs-governance` + `skills/agent-architecture-audit` | 문서 흩어짐·재발명(모드 1), 판단 품질 저하·지침 충돌·기억 오염(모드 2) |

- **설치 위치:** 사용자 계정 스킬(Cowork·채팅에서 사용). 저장소 `.claude/skills/`에는 넣지 않았다. Builder/Judge 세션에서 자동으로 켜지면 안 되기 때문이다. 세 스킬 모두 "Builder/Judge 세션에서는 쓰지 않는다"를 적었다.
- **토큰(2026-10-02 개정판):** 본문을 영문 압축형으로 다시 썼다(CLAUDE.md·AGENTS.md·참조 문서와 같은 언어, 출력은 한국어). 근사치(o200k 토크나이저 기준, Claude 실제 값과 다를 수 있음): 상시 설명 3개 합계 310 → 141, 본문 합계 4,169 → 1,926. 위원회 기본은 서브에이전트 1개가 세 목소리를 따로 답하는 가벼운 방식이고, 3개 병렬은 K3이거나 사용자가 요청할 때만 쓴다. 문서 점검은 파일 목록·제목부터 보고, 20개가 넘는 파일 훑기는 서브에이전트 1개가 요약표만 돌려준다. 보고 길이 상한 20~25줄.
- **보안:** 세 스킬 모두 지시문뿐이다(스크립트·훅·네트워크·설치 명령 없음). 원본 ECC 폴더도 SKILL.md 한 파일씩이었다. 위원회는 서브에이전트에 비밀·계좌번호·원본 계좌 자료를 넘기지 않는다. 문서 점검은 읽기 전용이다.
- **기존 결정과의 관계:** gstack 선례(전역 설치 없음)와 달리 사용자 수준 설치다. 사용자의 이번 명시 요청이 우선한다. 저장소 파일·고정 파일·정책은 바꾸지 않았다. 결과물은 설계 의견이며 K3·정책을 승인하지 않는다고 스킬마다 적었다.
- **라이선스:** ECC MIT, 각 스킬 끝에 출처와 저작권 표기. agent-architecture-audit의 표기 출처 oh-my-agent-check는 ECC 안에 별도 라이선스가 없다(확인 필요, 문장은 새로 썼다).
- **확인 필요:** 계정 스킬이 Claude Code에도 동기화되는지. 동기화되더라도 각 스킬의 Builder/Judge 제외 문구로 막는다.
- **되돌리기:** claude.ai 스킬 설정에서 해당 스킬을 끄거나 지운다. 잘못 켜지는 일이 반복되면 설명문을 좁힌다.

## 근거 파일

- 외부(각 저장소 루트 기준): superpowers `hooks/hooks.json`, `hooks/session-start`, `skills/*/SKILL.md`, `README.md`(Updating, Visual companion telemetry). ECC `.claude-plugin/plugin.json`, `hooks/hooks.json`, `scripts/hooks/*.js`, `skills/continuous-learning-v2/hooks/observe.sh`, `scripts/lib/llm-summary.js`, `agents/silent-failure-hunter.md`, `rules/common/testing.md`, `rules/python/hooks.md`. karpathy `CLAUDE.md`, `README.md`, `.claude-plugin/*.json`.
- 내부: `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json`, `.githooks/pre-push`, `.github/workflows/safety-ci.yml`, `docs/gstack-development-adoption.md`, `manage-us-stock-strategy/references/development-*.md`, `docs/claude/system-review-p4-roadmap-2026-09-30.md`(118행 금지 목록), `docs/claude/s7-builder-prompt-2026-10-01.md`(9절, deployment_gate 6개 목록), `docs/claude/s6-judge-prompt-2026-10-01.md` 6~7절, `docs/claude/s7-split-adjustment-builder-prompt-2026-10-02.md` 3절, `docs/claude/s7-u3-cash-flow-evidence-builder-report-2026-10-02.md`, `docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md` 2-1절.

## 진행 기록

- 2026-10-02 Cowork 검토(읽기 전용). 도입 여부 사용자 결정 대기.
- 2026-10-02 사용자 "점검표 도입 승인". Cowork가 `references/development-change-review.md`의 "Assess concrete defects" 끝에 "Fail-open patterns" 소절(21줄 추가, 기존 줄 변경 없음, LF 유지)을 넣었다. 테스트가 이 문서를 참조하지 않음(grep 확인), `git diff --check` 통과. 설치된 Codex 스킬 사본은 갱신하지 않았다(배포 고정 6개 아님, AGENTS.md는 저장소 경로를 읽음).
- 다음 K2/K3 Builder 지시문부터 보고 단계에 한 줄: "보고 전 자기 점검: change-review의 Fail-open patterns 6개를 바꾼 판단 경로마다 확인해 '해당 없음/처리함(테스트 이름)'으로 적는다." 효과는 다음 Judge 2~3회의 fail-closed FIX 건수로 본다.
- 2026-10-02 사용자 질문(설계 구상용 스킬)에 7절 추가. 설치·파일 도입 없음.
- 2026-10-02 사용자 요청으로 8절 계정 스킬 3개(기능 4개) 제안 카드 제시. 저장은 사용자가 카드에서 한다.
- 2026-10-02 사용자 요청으로 토큰 최적화 개정판 3개를 다시 제안(첫 제안은 저장 전이었음).
