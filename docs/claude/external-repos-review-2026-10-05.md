# 외부 저장소 3종 검토: Agent-Reach · ruflo · codebase-memory-mcp (2026-10-05)

- 등급: K0 문서 (런타임·정책·스킬·설정 변경 없음). 설치·실행하지 않음.
- 방법: 3개 저장소를 shallow clone 후 README·소스·설치 스크립트 직접 확인, 핵심 보안 주장은 소스 줄 단위로 재확인. 투자_V2 저장소는 read-only 대조.
- 대상 커밋: Agent-Reach `a19a171` (2026-09-16, v1.5.0) · ruflo `cd010ee` (2026-10-04, v3.51.1) · codebase-memory-mcp `268a9d8` (2026-10-04, v0.11.0). 모두 MIT.

## 0. 결론

| 저장소 | 판정 | 한 줄 이유 |
|---|---|---|
| codebase-memory-mcp | **조건부 파일럿 (REPLACE)** | 깨진 graphify 코드맵을 대체할 로컬 코드 그래프. 단, 전역 훅·자동 설정은 끄고 우리 저장소에서 효과를 직접 측정한 뒤 유지 여부 결정 |
| Agent-Reach | **설치 안 함, 설계 2개만 차용** | 기능 대부분이 이미 있음(WebFetch·WebSearch·내장 브라우저·external-pdf-intake). 소스 상태 점검(doctor)·대체 경로 개념만 가져옴 |
| ruflo | **설치 금지, 패턴 3개만 차용** | 전역 설정 수정·동의 없는 외부 통신·권한 우회 기본값이 안전경계와 정면 충돌. witness·신뢰도 장부·설정 위험 스캔 패턴만 가져옴 |

지금 진행 중인 일(S7b, 10/6 Marvell 행사, 10/15 MVLL 매도)을 막지 않는다. 첫 단계는 문구 2줄(K0)뿐이다.

## 1. 확인한 사실 요약

| 항목 | Agent-Reach | ruflo | codebase-memory-mcp |
|---|---|---|---|
| 정체 | 인터넷 플랫폼 읽기 도구 16종을 설치·점검·라우팅하는 얇은 래퍼 (Python) | Claude Code용 오케스트레이션 프레임워크, 구 claude-flow (Node/TS) | 코드베이스를 SQLite 지식 그래프로 색인하는 로컬 MCP 서버 (C 단일 바이너리) |
| 규모 | 2.4MB, 테스트 함수 약 492개 | 195MB, TS 약 85만 줄, MCP 도구 285/314/323 (문서마다 다름) | 테스트 약 8,167개, MCP 도구 17개 |
| 네트워크 | 페이지 읽기는 Jina 서버 경유, 팟캐스트는 Groq 업로드 | `funnel.ruv.io` 메시지 조회가 동의 없이 실행 (`RUFLO_FUNNEL=0`으로만 차단) | 소스상 운영 빌드 외부 통신 없음 (`src/daemon/application.c:69`). 단 SECURITY.md는 반대로 적혀 있음(오래된 문서) |
| 설정 변경 | 스킬을 `~/.claude/skills`에 복사, yt-dlp 설정 수정 | 기본값으로 `~/.claude/CLAUDE.md`에 블록 추가, 첫 세션에 `~/.claude/settings.json` 수정, 훅 7종 | 기본값으로 감지된 모든 클라이언트(최대 45종)에 MCP·스킬·에이전트·훅(Grep/Glob/Bash 게이트) 설치. `--skip-config`로 끌 수 있음 |
| 권한 | 소셜 쿠키를 평문 YAML 저장(Windows는 권한 제한도 안 걸림) | `hive-mind spawn --claude`가 권한 우회 기본값 true (`hive-mind.ts:604-607`) | 읽기 전용 Cypher, UI는 127.0.0.1:9749 (첫 실행 시 자동 켜짐) |
| 주장 대비 근거 | 문서 버전 불일치(10+/13/15/16 채널) | 토큰 30~50% 절감 근거 없음. 자체 감사에서 `Math.random` 가속 수치 발견(제거됨). `agent_spawn`은 기록만 남김 | "120배 토큰 절감" 저장소 내 근거 없음. BENCHMARK.md는 v0.3.0 언어 QA 표 |

투자_V2 쪽 사실:
- CLAUDE.md 31행이 `graphify-out/GRAPH_REPORT.md`를 코드맵으로 가리키지만 파일이 없다(2026-09-30 phase1 검토에서 이미 "깨진 참조"로 지적). `graph.json`은 2026-08-31 이후 갱신 없음.
- 추적 파일 1,052개(py 278개 약 9.4만 줄, json 499개, 정책 json 30개). 대형 저장소는 아니다.
- `.env.local`은 루트에 있고 `.gitignore` 대상이다.
- 폐기 승인된 `weakness_10ema`가 `alert_policy.json`에 아직 있다 — S7 phase 2 적용 전이라 정상.

## 2. 도입 요소 후보

판정 순서는 프로젝트 지침 §7 (NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD).

| ID | 요소 (출처) | 투자_V2 적용 위치 | 순서 판정 | 등급 | 판정 |
|---|---|---|---|---|---|
| C1 | 코드 그래프 검색: search_graph·trace_path·get_code_snippet·get_file_outline (cbm) | Claude Code Builder/Judge의 코드 탐색 | REPLACE (graphify) | K1 도구 | **파일럿** |
| C2 | detect_changes: git diff → 영향 심볼·위험 (cbm) | Judge 입력 범위 축소 | REUSE (C1 위) | K1 | 파일럿 (C1 통과 시) |
| C3 | 설정 키 ↔ 코드 연결 (cbm config-link) | S7 phase 2 정책 키 폐기 시 읽는 코드 찾기 | REUSE (C1 위) | K1 | 파일럿 (C1 통과 시) |
| C4 | Markdown 문서 → 파일 참조 연결 (cbm doclinks) | docs/claude 깨진 참조 탐지 (관제판 R2 보조) | REUSE | K1 | 보류 |
| C5 | manage_adr: 프로젝트당 결정기록 1개를 SQLite에 저장 (cbm) | — | ADD (기록 이중화) | — | **거절** |
| C6 | 전역 훅(Grep/Glob 게이트)·45개 클라이언트 자동 설정·graph UI (cbm) | — | ADD | — | **거절** |
| C7 | doctor: 백엔드를 실제로 호출해 상태·사용 경로 보고 (Agent-Reach) | 통합점검 v3.5 "점검 불완전"을 소스별 상태표로 확장 | REUSE (기존 확장) | K1 프롬프트 | 도입 후보 |
| C8 | 채널별 백엔드 대체 순서 (Agent-Reach) | "대체 시 등급 강등" 규칙 명시 (키움 없으면 외부가격 reference only, 트리거 판정 불가) | NO_CHANGE에 가까움 (헌법 §5와 같음, 문구만) | K0 | 도입 후보 |
| C9 | RSS 채널 (Agent-Reach, feedparser) | 공식 공시 증분 피드 (SEC 8-K·IR 보도자료) | ADD (작게, Agent-Reach 없이) | K1~K2 | 보류 (형식·egress 확인 후) |
| C10 | YouTube 자막 (Agent-Reach, yt-dlp) | 회사 공식 행사·실적 영상 자막 수집 (요청 시만) | ADD | K1 | 보류 |
| C11 | Twitter/X·Reddit·Xueqiu 등 소셜 채널 (Agent-Reach) | — | ADD | — | **거절** |
| C12 | Agent-Reach 스킬 설치 | — | ADD | — | **거절** |
| C13 | witness 매니페스트: 수정마다 sha256+표식 문자열, 표식이 사라지면 CI 실패 (ruflo) | 안전 불변식 표식 + 폐기 항목 tombstone 검사 | ADD (작음) | K2 | 도입 후보 (S7b 뒤) |
| C14 | ReasoningBank 신뢰도 (ruflo): 사용 결과로 패턴 신뢰도 갱신·승격·정리 | 트리거 유형별·외부 출처별 성적표 (S7b scorer 위, 표시 전용) | ADD | K2 | 보류 (데이터 쌓인 뒤) |
| C15 | settings 위험 스캐너 (ruflo, 179줄) | fail-open 점검표에 "설정에 주문 도구 허용·권한 우회·다운로드+셸 없음" 1줄 | REUSE (기존 점검표) | K0 | 도입 후보 |
| C16 | 비용 추적기 (ruflo): 세션 jsonl의 usage 합산 | Builder/Judge 세션 토큰 집계 | ADD | — | 보류 (explain-usage 있음) |
| C17 | swarm·hive-mind·합의 알고리즘·메모리 DB·훅 (ruflo) | — | ADD | — | **거절** (Workflow·Agent·decision-council 있음) |
| C18 | 동의 영수증 + 정책 버전 (ruflo) | — | NO_CHANGE ("확인 <코드>" 1회용 규칙이 이미 같음) | — | 넣지 않음 |

## 3. 도입 요소를 개선한 응용 아이디어

### A1. Judge 점검 패킷 (C2+C3+fail-open 점검표)
Builder 완료 뒤 Cowork가 `detect_changes`로 바뀐 함수·위험도, config-link로 건드린 정책 키를 뽑아 한 장으로 만든다. Judge는 그 범위와 해당 테스트만 먼저 본다.
- 이익: Judge 읽기량 감소, 정책 키 누락(예: 폐기 키를 읽는 다른 스크립트) 발견.
- 한계: 동적 키 접근(`policy[name]`)은 그래프가 못 잡는다 → 패킷은 "위치 찾기용, 증거 아님"으로 표시 (기존 graphify 원칙 그대로).

### A2. 증거 소스 점검표 + 등급 강등 체인 (C7+C8)
통합점검 매 실행 맨 위에 표 하나: `소스 | 실제 사용 경로 | 시각 | 등급(A~D) | 트리거 판정 가능?`.
- 예: 종가 = 키움 30분봉(정상) / 키움 없음 → 외부가격은 "reference only, 트리거 판정 불가"로 자동 강등.
- Agent-Reach는 "다른 도구로 대체해서 계속"이지만, 우리는 "대체하면 등급을 낮추고 판정 권한을 뺀다"로 바꾼다. 헌법 §5·EXPECTED != VERIFIED 원칙과 맞춘 개선.
- 기존 `audit_independent_close_provider.py`(독립 종가 공급자 감사, 비활성)와 겹치는지 먼저 확인.

### A3. 공식 공시 증분 피드 (C9 개선)
보유·관심 종목별 SEC 8-K/IR 보도자료 피드에서 "지난 실행 이후 새 항목"만 읽는다.
- 이익: "좋은 소식 = 회사 공식 발표 + 숫자 검증 가능" 정의(2026-10-02)와 직결, 매번 웹검색하는 토큰 감소, 놓침 감소.
- Agent-Reach 설치 없이 feedparser 또는 직접 요청이면 충분 (REUSE 최소 도구).

### A4. Tombstone + 안전 표식 회귀 검사 (C13 개선)
- 안전 표식: `order_authority=false`, `quantity_authority=none`, 실적 블랙아웃 fail-closed 등이 정책·프롬프트 초안에서 사라지면 테스트 실패.
- Tombstone: **적용 완료된** 폐기 결정(예: MVLL 전용 점검, 스크린샷 입력 경로)을 목록에 넣고, 프롬프트·문서·정책에 다시 나타나면 경보. `weakness_10ema`처럼 승인만 되고 미적용인 항목은 phase 2 병합 뒤에 등록.
- context-layer-audit 스킬의 "제거한 것이 돌아옴" 문제를 사람이 아닌 테스트로 고정한다.
- 기존 decision-record 검증 fixture가 일부 표식을 이미 검사하므로 Builder가 중복부터 확인.

### A5. 트리거·출처 성적표 (C14 개선)
S7b scorer 결과로 트리거 유형별, 외부 출처(fmkorea 작성자·SAVE 등)별 "나중에 맞았나" 기록을 표시만 한다.
- 외부 출처 점수는 증거 가중치 0 유지, "어느 단서를 먼저 공식 확인할지" 순서에만 쓴다.
- 승격·강등은 2027-01 규칙 검토에서 사람 승인. ruflo의 수치(3회 사용·0.6)는 매매 통계에 맞지 않으므로 쓰지 않고, 최소 표본은 사전등록으로 정한다.
- 반복 루프이므로 설계 시 loop-design-check 적용.

### A6. 분석 라이브러리 경량판 (창의안, 사용자 판단 필요)
cbm이 Markdown 섹션을 노드로 색인하는 점을 이용해 `chatgpt_종목분석결과`의 카드·메모·원장 md를 색인 → 재분석 전에 "이미 본 자료" 검색.
- 10/3 사용자가 제안한 "분석 라이브러리"를 새 DB 없이 구현하는 길.
- 반대 근거: 10/3 결정은 "전체 아카이브 대신 읽는 양부터 줄이기". 문서 지원은 cbm의 부기능이고 git 저장소가 아니면 자동 갱신(watcher)이 없다. → C1 파일럿 결과를 본 뒤에만 논의.

### A7. 실행 경계 도달성 검사 (검토 후 제외)
"어떤 스크립트에서도 키움 주문 TR까지 호출 경로가 없다"를 그래프로 검사하는 안. 정적 grep 테스트가 더 단순하고, 동적 호출은 그래프도 못 잡으므로 이익이 없다.

## 4. 도입 근거 / 도입하지 않는 근거

### codebase-memory-mcp
도입 근거
- 지금 코드맵은 깨져 있다(GRAPH_REPORT.md 없음, graph.json 2026-08-31). 고치거나 지워야 하는 상태라 REPLACE 대상이 이미 있다.
- Python 지원, git 변경 기준 증분 재색인, `.gitignore`·`.cbmignore` 존중, `.claude/` 기본 제외(저장소 안 worktree 중복 색인 방지).
- 소스상 운영 빌드에 외부 통신 없음, 텔레메트리 없음. Windows amd64 설치 스크립트에 SHA-256 검증 필수.
- 테스트 약 8,167개, CodeQL·fuzz CI. 읽기 전용 Cypher라 저장소를 바꾸지 않는다.
- 도구 권한 프로필(Scout/Analysis)로 노출 도구 수를 줄일 수 있다.

도입하지 않는 근거
- 우리 저장소는 작다(추적 1,052개). "120배 절감"은 대형 저장소 기준이고 저장소 안에 근거가 없다 → 이익이 작을 수 있다.
- 기본 설치가 전역 훅(Grep/Glob/Bash 앞 게이트)과 다른 클라이언트 설정까지 바꾼다 → 다른 프로젝트·Codex까지 영향. 반드시 `--skip-config` + 수동 등록.
- 1인 유지보수, 문서 불일치(SECURITY.md 네트워크·지원 버전 설명이 소스와 다름), `ingest_traces`는 설명과 달리 미구현.
- 백그라운드 데몬 자동 시작, graph UI 첫 실행 자동 켜짐 → 끄는 설정 필요.
- MCP 도구 17개 스키마가 세션 컨텍스트를 차지할 수 있음(지연 로딩 여부 확인 필요).
- 가장 단순한 대안은 CLAUDE.md의 깨진 graphify 줄을 지우는 것(REMOVE). 파일럿이 이익을 못 보이면 이 대안으로 간다.

### Agent-Reach
도입 근거
- doctor(실제 호출로 상태 확인)와 채널별 대체 순서는 v3.5 "점검 불완전" 경보와 잘 맞는 설계다.
- RSS·YouTube 자막은 회사 공식 자료 수집에 쓸 수 있다.

도입하지 않는 근거
- 겹침: 웹 읽기(Jina) = WebFetch, 검색(Exa) = WebSearch, 로그인 사이트 = 내장 브라우저(saveticker), 커뮤니티 글 = 외부자료 PDF + external-pdf-intake.
- 소셜 채널은 증거 등급상 가설(가중치 0)인데 쿠키 평문 저장·계정 정지 위험이 따라온다(접속이 막힌 환경에서는 유료 프록시까지 권장).
- Jina 경유 = 읽는 URL이 제3자 서버로 간다.
- 스킬이 "모든 조사·검색에 MUST USE" + 작업 뒤 `check-update` 실행 → 토큰 증가, 기존 라우팅과 충돌.
- npm·pipx 전역 설치가 버전 미고정, 금융 소스는 중국 Xueqiu뿐(지연 시세).

### ruflo
도입 근거
- 분리 가능한 좋은 패턴이 있다: witness 매니페스트, 신뢰도 장부, 설정 위험 스캐너.

도입하지 않는 근거
- 기본값으로 `~/.claude/CLAUDE.md`에 블록 추가, `~/.claude/settings.json` 수정 → 프로젝트 지침 계층(§1 Authority Chain) 밖에서 행동을 바꾼다.
- `funnel.ruv.io` 원격 메시지를 동의 없이 조회, MCP 서버를 `npx ruflo@latest`로 매번 미고정 실행 → 공급망 위험.
- `hive-mind spawn --claude` 권한 우회 기본값 true → Execution-Authority NONE 원칙과 충돌.
- 매 프롬프트 훅이 라우팅 표를 주입 → 토큰 증가.
- 성능·토큰 절감 주장 근거 없음, 자체 감사에서 조작된 가속 수치 발견(현재 제거), 문서 수치 상호 불일치.
- 195MB·TS 85만 줄 → MINIMUM_SUFFICIENT_SYSTEM, "Hot-Path blocker 해결 전 새 subsystem 금지"와 충돌. 필요한 오케스트레이션은 Workflow·Agent·decision-council로 이미 있다.

## 5. 권장 순서 (한 번에 한 단계, 각 단계 사용자 승인)

1. **지금 (K0, 문구만)**: C15 점검표 1줄 + C8 등급 강등 문구. 런타임 변경 없음. → 2026-10-05 반영 완료 (`manage-us-stock-strategy/references/development-change-review.md` Fail-open patterns에 2항목 추가).
2. **S7b 커밋 뒤 (K1 도구 파일럿)**: C1 codebase-memory-mcp. (S7b는 2026-10-05 병합 완료 → 선행 조건 충족, 착수 시점은 사용자 결정. 관제판 작업 `s-cbm-pilot`.)
   - 설치 조건: `install.ps1 --skip-config`, Claude Code에 MCP만 수동 등록, 훅 없음, UI 끔, `.cbmignore`에 `.env*`·`workspace/` 민감 경로 명시.
   - 사전등록 측정: 비슷한 Builder 작업 2건을 cbm 사용/미사용으로 비교 (세션 토큰, 도구 호출 수, 놓친 파일 수).
   - 성공 시 CLAUDE.md 31행을 cbm으로 교체, 실패 시 cbm 제거 + 31행 삭제(REMOVE).
3. **S7b 데이터가 쌓인 뒤 (K2)**: A4 tombstone·안전 표식 검사 → A5 성적표 (loop-design-check 거침).
4. **선택**: A3 공시 증분 피드 (아래 확인 필요 해소 후), A1 Judge 패킷 (C1 통과 시).

## 6. 확인 필요

- cbm 토큰 절감 폭: 저장소 내 근거 없음 → 우리 저장소에서 측정해야 함.
- cbm MCP 도구 스키마의 Claude Code 컨텍스트 비용(지연 로딩 여부), Windows에서 데몬·UI 실제 동작.
- SEC EDGAR 회사별 피드의 현행 형식과 User-Agent 요건, 통합점검 실행 환경의 egress 허용 여부.
- A2와 기존 `audit_independent_close_provider.py`의 중복 범위.
- A4와 기존 decision-record 검증 fixture·테스트의 중복 범위.
- 세 저장소의 GitHub 별 수·실사용 규모 (네트워크 조회 안 함).

## 근거 파일
- 클론 위치(세션 임시): Agent-Reach `a19a171`, ruflo `cd010ee`, codebase-memory-mcp `268a9d8`.
- ruflo: `v3/@claude-flow/cli/src/init/executor.ts:2235-2265`, `commands/hive-mind.ts:295-301,604-607`, `parser.ts:552`, `funnel/message-transport.ts:49,128-140`, `init/mcp-generator.ts:66`, `docs/reviews/intelligence-system-audit-2026-05-29.md`.
- codebase-memory-mcp: `src/daemon/application.c:69-81`, `src/cli/cli.c` (훅 설치), `install.ps1:106,348`, `src/mcp/mcp.c:524-830`, `docs/CONFIGURATION.md:148,221-236`.
- Agent-Reach: `agent_reach/channels/`, `config.py:61,78`, `skill/SKILL_en.md:4-8,43`, `cli.py:689-776`.
- 투자_V2: `CLAUDE.md:31`, `docs/claude/system-review-phase1-2026-09-30.md:125`, `docs/claude/external-skills-review-2026-10-02.md`.

## 진행 기록
- 2026-10-05: 검토 작성 (Cowork). 핵심 보안 주장 7건 소스 재확인, 프록시 표현 1건 정정. 설치·설정 변경 없음. 사용자 승인 대기.
- 2026-10-05: 사용자 승인으로 1단계 반영 — Fail-open patterns에 "Fallback inheriting authority"(C8), "Permission widening"(C15) 추가, 출처 표기. 다음 단계: C1 파일럿 (S7b 완료로 조건 충족, 착수는 별도 승인). 관제판에 s-cbm-pilot 추가.
