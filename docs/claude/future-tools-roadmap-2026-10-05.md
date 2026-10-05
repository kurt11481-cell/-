# 외부 저장소 8종 장기 도입 검토 (2026-10-05)

- 등급: K0 문서 (런타임·정책·스킬·설정 변경 없음). 설치·실행하지 않음.
- 요청: 지금 당장 도입하지 않더라도 장기 발전(스스로 진화, 효율, 혁신)에 쓸 도구가 있는지 검토.
- 방법: 8개 저장소 shallow clone 후 README·문서·일부 소스 확인. GitHub 별 수는 2026-10-05 저장소 페이지 표시값. 투자_V2는 read-only 대조: 헌법 v1.2.1 §11·14·15·24·25·26·28, P4 로드맵 §5·§7, `decision_journal.json`(entries 1건), `score_decision_journal.py`.
- 대상 커밋: ponytail `e15862b` · OpenShell `71c3cd9` · Agent-Reach `a19a171` · hydradb `e0f5095` · iFixAi `482fd85` · openrig `b5a9dea` · paperclip `1c07b59` · hindsight `f7dd3f4`.
- 선행 검토: `external-repos-review-2026-10-05.md` (Agent-Reach·ruflo·codebase-memory-mcp).

## 0. 결론

| 저장소 | 별 | 판정 | 도입 시점(트리거) |
|---|---|---|---|
| NVIDIA/OpenShell | 10.0k | **장기 1순위 후보** | 주문 권한 단계 검토 착수 시 (헌법 §14 READ_ONLY 탈출) |
| ifixai-ai/iFixAi | 20.3k | **장기 후보** | 권한 단계 변경 검토 직전 감사 |
| DietrichGebert/ponytail | 154.7k | **점검 기능만 후보** | P6 월간 점검 첫 회 |
| vectorize-io/hindsight | 44.6k | 설계 차용, 도구 보류 | 원장 칸 설계 시 차용. 도구는 §2 재검토 조건 충족 시 |
| paperclipai/paperclip | 95.9k | 패턴 차용, 도구 보류 | 예약 작업 비용 한도가 필요할 때 |
| mvschwarz/openrig | 4.9k | 제외 | Windows 지원 + 권한 기본값 변경 시 재검토 |
| hydra-db/hydradb | 13 | 제외 | — (Thesis Graph 아이디어만) |
| Panniantong/Agent-Reach | 90.8k | 제외 (기결정) | `external-repos-review-2026-10-05.md` 따름 |

- 진화는 도구가 아니라 루프로 만든다: 결정 원장 → 채점 → 발견 → 제안 → 검증 → 사용자 승인 (헌법 §15 EVOLUTION_0~4, 기본 상한 EVOLUTION_4). 도구는 각 단계의 문지기로 붙인다.
- 현재 EVOLUTION_0: 원장 1건. 판단 품질 결론은 원장 30건 이상에서만 낸다(P4 §7).
- 진화 대상은 분석 품질이다. `BETTER_INTELLIGENCE != MORE_EXECUTION_AUTHORITY`, 시스템은 자기 Authority Envelope를 스스로 넓힐 수 없다(헌법 §14).
- 별 수는 품질 지표가 아니다. HydraDB(13)는 인기 목록과 거리가 멀고, OpenRig(4.9k)는 중간 규모.

## 1. 단계별 로드맵

| 시스템 단계 (헌법 §26·§15) | 도구 | 역할 | 도입 조건 | 등급 | 구조 판정 |
|---|---|---|---|---|---|
| 지금 ~ 원장 30건 (EVOLUTION_0) | Ponytail `/ponytail-audit`·`/ponytail-debt` | P6 월간 점검의 Complexity Review 입력: 지울 것·단순화할 것·미룬 단순화 목록 (보고만) | P6 첫 회 (S4 완료 뒤 약 1개월) | K0~K1 | REUSE (§24 사다리와 동일) |
| 원장 30건 이후 (EVOLUTION_1 자동 발견 → 2 자동 제안) | 새 도구 없음. 기존 채점기 + Workflow | 트리거 유형별 성적, "어느 가정이 틀렸나" 집계, 표시 전용 | 원장 30건 + 첫 20세션 채점 결과 | K1~K2 | REUSE |
| GUARDED INTENT 전 (ORDER_INTENT_ONLY 검토) | iFixAi | 권한 승격 전 시스템 감사. 결과는 Grade D → 차단 근거만, 승격 근거 아님 | 권한 단계 변경 검토 착수 | K2(어댑터) | ADD (Cold Path) |
| 주문 권한 단계 (HUMAN_PER_ORDER 이상) | OpenShell | 권한 경계를 실행 환경에서 강제·증명 | 사용자가 READ_ONLY 탈출을 검토할 때 | K3 | ADD (권한 경계) |

## 2. 도구별 근거

### OpenShell (NVIDIA)
도입 근거
- prover boundary check: 후보 정책이 경계 정책(최대 허용 범위)보다 넓은 접근을 허용하면 SMT 솔버가 반례를 보여 준다. "Authority Envelope 자가 확대 금지"(헌법 §14)를 기계적으로 증명하는 수단. (`docs/how-it-works/policies/prover.mdx`)
- 요청 검사 protocol: `rest`(HTTP 메서드·경로·쿼리), `mcp`(MCP 메서드·도구 이름), `json-rpc`, `graphql`, `websocket`. 조회 허용·주문 차단을 네트워크 계층에서 걸 수 있다. (`network-rules.mdx`)
- provider: 에이전트는 실제 자격증명을 보지 못하고, 승인된 엔드포인트 요청에만 게이트웨이가 넣는다.
- advisor의 proposal risk check: 자격증명이 있는 호스트에 새 HTTP 메서드(`capability_expansion`) 등 위험한 새 접근을 자동 표시 → 사람 검토. (`advisor.mdx`)

지금 도입하지 않는 근거
- 현재 READ_ONLY, 키움 MCP 주문 게이트 0, Cowork 샌드박스로 충분 → NO_CHANGE.
- 기본 `enforcement`는 `audit`(허용 + 기록). 차단하려면 `enforce`를 명시해야 한다.
- Windows는 WSL 2 실험 지원, 0.1.x, Docker/Podman/VM 필요. 익명 텔레메트리 기본(`OPENSHELL_TELEMETRY_ENABLED=false`로 끔).
- prover 모델은 "확장 중"이라 모든 정책 기능을 증명하지는 않는다(문서 명시).

지금 차용 가능 (별도 승인, K2): "최대 권한 경계" 파일 + 설정·MCP 허용 목록·스킬이 경계를 넘지 않는지 보는 정적 테스트. fail-open 점검표 "Permission widening"(2026-10-05 추가)의 테스트화. `external-repos-review` A4(안전 표식 회귀 검사)와 묶을 수 있다.

### iFixAi
도입 근거 — 투자_V2 규칙과 맞는 점검 (`docs/inspections.md`)

| 점검 | 내용 | 투자_V2 규칙 |
|---|---|---|
| B02 Non-LLM Governance Layer | 통제가 프롬프트가 아니라 규칙으로 강제되는가 | 결정론 규칙 > LLM 출력 |
| B05 Source Provenance | 사실마다 출처를 대는가 | Evidence 규칙 (§5) |
| B06 Explicit Uncertainty | 모르면 모른다고 하는가 | 확인 필요 / NOT VERIFIED |
| B08 Privilege Escalation (필수) | 권한 확대 유도를 거부하는가 | Execution-Authority NONE |
| B16 Silent Failure | 실패를 성공처럼 보고하지 않는가 | fail-closed, 점검 불완전 경보 |
| B28 RAG Context Integrity | 읽은 문서 속 숨은 명령을 무시하는가 | 외부자료 PDF 인테이크 |
| B30 Malicious Deployer Rules | 안전장치를 끄는 규칙 생성을 거부하는가 | 정책 파일 무단 수정 금지 |

- 채점은 다른 벤더 모델이 자동 배정(자기 채점 금지), mock 실행 가능, 실행 manifest로 재현(`docs/reproducibility.md`).

지금 도입하지 않는 근거
- HTTP 엔드포인트 또는 `ChatProvider.send_message` 어댑터가 필요하다(K2). 투자_V2는 배포된 에이전트 구조가 아니다.
- 전체 실행 약 $10~18 (업체 추정, 2026 중반 OpenRouter 가격, 피검 쪽 비용 별도). API 키 2개 → 비밀값 규칙상 사용자가 환경변수로 넣고 Claude는 읽지 않는다.
- 텔레메트리 기본 켜짐(`IFIXAI_TELEMETRY=0`으로 끔).
- 결과는 TEST(Grade D). 승격을 막는 근거는 되지만 올리는 근거는 못 된다(헌법 §22).

### Ponytail
도입 근거
- `/ponytail-audit`: 저장소 전체를 delete·stdlib·native·reuse·yagni·shrink 태그로 순위 매긴 목록. 보고만 하고 고치지 않는다.
- `/ponytail-debt`: `ponytail:` 주석으로 남긴 의도적 단순화를 원장으로 모으고, 재검토 트리거가 없는 항목을 표시.
- 헌법 §24 사다리(NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD)와 같은 관점, §25 Cold Path "Complexity Review" 입력. P4 §5의 I8 은퇴 같은 REMOVE 후보 찾기에 쓸 수 있다.

도입하지 않는 부분
- 상시 모드(플러그인 훅: SessionStart·SubagentStart·UserPromptSubmit) — 지침 §7과 중복, 매 프롬프트 개입.
- 성과 수치는 자체 측정(Haiku 4.5, 과제 12개, n=4). 일반화는 확인 필요.
- 악성 복제본 사례(GitHub 이슈 #735) → 설치한다면 `DietrichGebert/ponytail`에서만.

방식: 플러그인·훅 없이 `skills/ponytail-audit/SKILL.md`만 Claude Code 수동 스킬(또는 같은 내용의 프롬프트)로 P6 때 1회 실행. 결과는 후보 목록이며 삭제는 항목별 승인.

### Hindsight
차용할 설계
- observation: 근거 인용 + 근거 개수 + 반박 이력 보존. 원장·Failure Museum·Assumption Ledger 칸으로 추가(§24 FIELD before NEW STATE).
- mental model refresh: "검색 실패 ≠ 빈 결과" — 실패하면 기존 내용을 그대로 둔다(fail-closed와 같음).

도구를 들이지 않는 근거
- recall의 `temporal_window`는 "ranks, it does not filter"(`api/recall.mdx`). `evidence_timestamp <= decision_as_of`를 보장할 수 없어 Replay·과거 판단 검증에 쓸 수 없다.
- 기억 삭제는 mental model의 staleness에 잡히지 않는다(`api/mental-models.mdx`).
- retain마다 LLM 호출, Postgres + pgvector 서버.
- LLM이 기억을 자동 통합·수정 → 결정론 규칙 우선과 충돌 소지, loop-design-check 실패 유형 5(낡은 기억)에 해당.
- 같은 역할을 프로젝트 메모리·문서·외부주장 원장이 이미 한다.

재검토 조건: (a) 메모·카드·원장 검색이 grep으로 감당되지 않을 만큼 커짐, 그리고 (b) 시점 하드 필터 제공(또는 as-of별 bank 분리로 무결성 증명).

### Paperclip
차용할 패턴
- 예산 100% 도달 시 자동 정지(`docs/guides/board-operator/costs-and-budgets.md`) → 예약 작업 토큰 한도.
- 작업 체크아웃 잠금 → 여러 세션을 동시에 돌릴 때 관제판에 진행 세션 표시.
- 루틴 실행 1회 = 추적 작업 1건.

도구를 들이지 않는 근거
- 파일 8,300개, Node 24.11+, 내장 Postgres의 새 서브시스템. 관제판·예약 작업과 역할 중복. "Hot-Path blocker 해결 전 새 subsystem 금지"(지침 §7).
- "24시간 자율 회사" 지향. 예산 정지는 기록된 사용량 기준이라 늦게 걸릴 수 있다(README).
- README의 Skill Studio 평가·버전 기능은 문서에서 실체를 확인하지 못함(확인 필요).

재검토 조건: 예약 작업이 관제판으로 감당되지 않을 만큼 늘고 비용 초과가 반복될 때.

### 제외
- OpenRig: macOS/Linux만(네이티브 Windows 미지원, WSL2 미검증). 워크스페이스 사전 신뢰, Claude `--permission-mode acceptEdits` 기본, 훅·설정 파일 기록. owner/checker·스냅샷 복원 아이디어는 Builder/Judge·관제판에 이미 있다.
- HydraDB: v0.2.0(2026-09-28 첫 공개), AGPL-3.0, Rust + C 라이브러리 빌드, S3 전제. 규모 불일치.
- Agent-Reach: `external-repos-review-2026-10-05.md` 결정 유지(같은 커밋 `a19a171`).

## 3. 도구 없이 할 혁신 아이디어 (각각 별도 승인)

| ID | 아이디어 | 출처 | 트리거 |
|---|---|---|---|
| I1 | Thesis Graph 집중도 점검: 보유·관심 종목의 Capital Conversion 사슬과 root thesis를 연결해 같은 근본 논지를 공유하는 노출 합계를 표시(티커 분산 != 논지 분산, 지침 §6). JSON + 작은 스크립트, 표시 전용 | 헌법 §28, HydraDB 아이디어 | 카드 코드화(S7a) 결과에 논지 항목이 있을 때 (형식 확인 필요) |
| I2 | Failure Museum: 채점 결과가 나쁜 결정마다 "어느 가정이 틀렸나"(헌법 §11) 한 줄 + 근거 인용 | 헌법 §28, Hindsight 관찰 형식 | 첫 20세션 채점 |
| I3 | Blind Challenger Tournament: 발견 하나당 도전 규칙을 사전등록 → 시점 무결성 리플레이로 챔피언과 비교 → Judge → 사용자 승인 (EVOLUTION_3~4) | 헌법 §20·§28 | 원장 30건 + 발견 루프 안정 |
| I4 | 권한 경계 코드화: 최대 권한 경계 파일 + 정적 테스트 | OpenShell prover 개념 | 별도 승인 시 언제든 (K2) |

## 4. 진화 루프 설계 점검 (loop-design-check)

- 판정: 지금은 만들지 않음 (전제 미충족: 원장 1건). 원장 30건 뒤 발견(표시 전용)부터.
- 형태: 발견 = dead-band 조절기(같은 트리거 유형이 N건 이상 일관되게 틀릴 때만 발견으로 올림). 도전안 검증 = 목표 도달 시 멈춤(사전등록 → Builder → 별도 Judge).
- 완료 기준: 사전등록 지표(현금·SPY 대비 20/60세션 성과, 최소 표본, 표본 외 구간) 통과.
- 경계: 정책·상태·원장 파일과 채점기·승인 기준은 루프가 바꾸지 못한다. 발견 하나당 도전안 2회까지, 이후 사람. 기준 데이터 = 키움 종가·브로커 스냅샷(`score_decision_journal.py`의 시점 규칙과 PENDING/NOT_SCORABLE 상태 그대로).
- 실패 유형: 1 결정 불가 목표 — 통과(사전등록). 2 피고가 채점 — 위험 → 결정론 채점기 + 독립 Judge. 3 경계 미명시 — 이 문서로 명시. 4 실행 중에만 정할 것 — 표본 부족이면 "판단 보류"로 멈춤. 5 낡은 기억 — 자동 합성 기억 도입 금지(Hindsight 보류 근거).
- 레드라인: 루프는 정책을 바꾸지 않는다(상한 EVOLUTION_4 = 자동 검증 + 사람 승인). 배분·주문·병합에 자동 권한 없음.

## 5. 관제판 대기 항목 (2026-10-05 추가)

| id | 이름 | 재개 조건 |
|---|---|---|
| `f-ponytail-audit` | Ponytail 저장소 군살 점검 1회 | P6 월간 점검 첫 회 |
| `f-evo-loop` | 진화 루프 1단계(자동 발견, 표시 전용) 설계 | 원장 30건 + 첫 20세션 채점 결과 |
| `f-ifixai-audit` | iFixAi 권한 승격 전 감사 | 권한 단계 변경 검토 착수 |
| `f-openshell` | OpenShell 권한 경계 런타임 검토 | 주문 권한 단계 검토 착수 (I4 정적 테스트는 별도 승인 시 언제든) |

## 6. 확인 필요

- OpenShell: 키움 MCP(Windows 로컬) 통신을 게이트웨이 경유로 보낼 수 있는지, WSL 2 실사용, prover가 MCP 규칙까지 모델링하는지.
- iFixAi: 우리 구조용 어댑터 범위, 실제 비용, judge 결과의 실행 간 변동.
- Paperclip: Skill Studio 평가·버전 기능의 실체.
- Hindsight: 시점 하드 필터 계획 여부.
- 카드의 root thesis 항목 형식(I1 전제).
- 별 수 급증의 실사용 의미.

## 근거 파일
- 투자_V2: `knowledge/fund_manager_system_constitution_v1_2_1.md`(프로젝트 지식), `docs/claude/system-review-p4-roadmap-2026-09-30.md` §5·§7, `stock-strategy-system/decision_journal.json`, `manage-us-stock-strategy/scripts/score_decision_journal.py`, `docs/claude/external-repos-review-2026-10-05.md`.
- OpenShell: `README.md`, `docs/how-it-works/policies/network-rules.mdx`, `prover.mdx`, `advisor.mdx`.
- Hindsight: `README.md`, `hindsight-docs/docs/developer/api/recall.mdx`(query_timestamp·temporal_window), `api/mental-models.mdx`, `observations.mdx`.
- iFixAi: `README.md`, `docs/inspections.md`, `docs/reproducibility.md`.
- Paperclip: `README.md`, `docs/guides/board-operator/costs-and-budgets.md`, `docs/guides/agent-developer/skills-store.md`.
- Ponytail: `README.md`, `skills/ponytail-audit/SKILL.md`, `skills/ponytail-debt/SKILL.md`, `hooks/claude-codex-hooks.json`, GitHub 이슈 #735.
- OpenRig: `README.md`. HydraDB: `README.md`, `CHANGELOG.md`, hydradb.com.

## 진행 기록
- 2026-10-05: 검토 작성(Cowork). 설치·설정 변경 없음. 사용자 승인으로 이 문서 저장 + 관제판 대기 항목 4개 추가.
- 2026-10-05: 작업 중 `git status`가 남긴 `.git/index.lock`(0바이트)을 사용자 삭제 승인 뒤 제거. 교훈: Cowork device_bash에서는 index를 건드리는 git 명령을 쓰지 않는다(삭제 권한이 없으면 잠금 파일이 남는다).
