---
id: dual-ai-review-2026-10-20
type: review
status: 결정 완료 — Q2 a(OneDrive) 2026-10-20 10:24 KST → 개발 offsite-bak · Q1 c(안 함) 2026-10-20 11:01 KST
as_of: 2026-10-20 11:20 KST
tickers: [ALL]
class: 문서만(K0). 설치·구독·런타임·정책·예약 작업·권한 변경 0
authority: order_authority=false · quantity_authority=none · execution_quantity=null
evidence: 사용자 첨부 PDF 3건(에펨코리아 AI 게시판 2026-10-18 글: Paseo 추천 1쪽 · notifold 글 5쪽 · 같은 글 그림 버전 17쪽) 원문 + 저장소 원문(HEAD bb1f1f9) + C:\Users\금동한\.codex 설정·세션 목록(비밀 파일 auth.json 내용은 읽지 않음) + 개발 관제판 tasks(2026-10-20 조회) + 웹(Codex 요금 정리 글, Google 블로그, Paseo GitHub, 2026-10-20 조회)
consumers: 관제판 dual-ai-1020(결정) · docs/claude/future-tools-roadmap-2026-10-05.md 진행 기록 · 주간 팀장회의(연구개발팀·감사실·운영관리팀 안건) · docs/claude/system-design-ops-review-2026-10-09.md 87행 AGENTS.md 보류 건
summary: AI 2개(Claude 메인 + 다른 회사 AI 서브 검수) 검토 — 가장 큰 이익은 다른 회사 AI의 교차 검수(아직 가설). 사용자가 Codex를 10/18까지 쓰고 있어 ChatGPT를 권장하되 구독 등급부터 확인하고, 수동 경로 Judge에 붙이는 시범으로 잰다. 그보다 먼저 백업 공백(코드 331커밋 미push, 결정 일지·대조 원장은 git 밖이라 PC에만 있음)을 고칠 것을 권장.
---

# AI 2개 활용 검토 + 회사 운영 도입 요소 (2026-10-20)

## 0. 결론
1. **서브 AI는 ChatGPT(Codex)가 맞다.** 이미 PC에 깔려 있고 2026-10-18에도 썼다(F3). 먼저 지금 구독 등급을 확인한다 — 이미 Plus면 추가 비용 0이고, 질문은 "구독할지"가 아니라 "시범할지"다.
2. **이익의 핵심은 "다른 회사 AI의 교차 검수"인데, 아직 가설이다.** 지금 Builder·Judge·내장 재검토가 모두 Claude이고(F1), 시스템 스스로 "같은 모델은 같은 맹점을 가질 수 있다(확인 필요)"를 열린 한계로 적어 두었다(F2). 시범이 바로 이것을 잰다.
3. **역할은 "외부 감사인"(감사실, 읽기 전용 의견 1개)만.** 판정을 올리지 못하고(낮추기·확인 요청만), 지적은 위치 안내이며 Claude가 원문으로 확인해야 채택된다. Cowork에서는 Codex를 부를 수 없어(F3) **수동 경로 Judge(Windows Claude Code)부터** 붙인다.
4. **Paseo는 도입하지 않는다.** 총괄(Cowork)·worktree 분리(개발 파이프라인)가 이미 있고, 상주 데몬·원격 접속·플러그인 권한이 키움 MCP가 있는 PC에 더해진다.
5. **AI 2개보다 먼저 고칠 것은 백업 공백이다.** ① 코드·문서: 원격보다 331커밋 앞섬, 마지막 push 2026-09-29. ② 결정 일지·대조 원장·상태 백업·자동 코어 기록·portfolio_state는 git이 무시하는 파일이라 push로도 백업되지 않는다 — 지금 PC 밖 사본이 없다(F5).
6. 글의 나머지 요령(같은 파일 동시 수정 금지, 파일 이름으로 커밋, 문서 3층, 잘된 결과물 쌓기, 기획 먼저)은 **이미 있다** — 바꿀 것 없음.

## 1. 첨부 3건 요지 (원문)
| # | 글 | 요지 |
|---|---|---|
| A | "AI 2개 이상 사용하시면 Paseo 추천합니다"(e/acc, 2026-10-18 18:24, 1쪽) | AI별 역할 지정, Opus 5.5를 총괄로 두면 다른 AI를 불러 일 시킴, 워크스페이스·worktree 관리로 작업이 안 꼬임 |
| B | "코딩은 클로드, UI 그림은 GPT…"(notifold, 2026-10-18 14:13, 5쪽) | (가) 잘하는 일로 분업(코딩 Claude, 그림 GPT) (나) 비싼 요금제는 일 많은 쪽 (다) 방향 잡기(Fable·Astra) → 개발(Opus) (라) 같은 폴더 동시 작업 사고와 규칙 ①~④(①같은 파일 동시 수정 금지 · ②커밋 전 `git log --oneline -3` · ③`git add` 파일 이름 · ④커밋 즉시 push) (마) Claude가 뒤에서 `codex exec -s read-only`로 점검 — "짠 AI는 자기 코드라 잘 못 찾는데, 다른 회사 AI는 다른 데를 찌릅니다", "Codex 지적도 자주 틀려서 Claude가 맞는지 확인" (바) 문서 3층(입구 CLAUDE.md · 인계 150줄 덮어쓰기 · 절차서) (사) 잘된 결과물을 저장소에 쌓고 파일로 줌 |
| C | B의 그림 버전(17쪽) | B와 같은 내용(새 주장 없음). "같은 파일은 한 AI만 · 저장 전에 먼저 확인", "Codex는 Claude 뒤에", "보기만 하고 고치지는 마" |

외부 글은 증거 강도 0(개인 경험담). 아래 판단은 저장소 원문으로만 한다.

## 2. 현재 시스템 대조 (원문 확인, 2026-10-20 조회)
- **F1 검토 3층이 모두 Claude.** 파이프라인 Judge = `claude -p … --model opus --effort xhigh --tools "Read,Grep,Glob"`(tools/dev-run.ps1:356), 수동 경로 Judge도 Claude Code Opus(예: docs/claude/r5-align-judge-report.md:5), 감사실 = 독립 Judge + 내장 재검토 subagent(docs/claude/company-org-plan-2026-10-19.md:93).
- **F2 같은 모델 맹점은 열린 한계.** "같은 모델의 subagent는 같은 맹점을 가질 수 있다(확인 필요)"(docs/claude/review-stability-2026-10-13.md:19). 내장 재검토 실측(문서 1건, n=1): 1회차 17건(결론·문구 변경 9)·2회차 15건(4), 비용 227,030토큰·172,787토큰(같은 문서 :17~18). 이번 검토의 내장 재검토도 13건을 찾았다(6절).
- **F3 Codex는 지금도 쓰고 있다.** `~/.codex/session_index.jsonl` 마지막 3줄 updated_at 2026-10-18(KST 11:05·11:23·17:01, "거리 전신 패션스냅 만들기"·"Guardian review" 2건), auth.json 수정 시각 2026-10-19(내용 미열람). 설정(config.toml): model `gpt-6.1-sol`, sandbox `workspace-write`, computer-use·browser 플러그인 켜짐, 키움 MCP kiwoom_exec 켜짐(`enabled_tools` = kiwoom_commands·kiwoom_help·kiwoom_query, `KIWOOM_MCP_ALLOW_ORDERS = "0"`, `KIWOOM_PROFILE = ""`). Codex 예약 2개(Pre-Open·Post-Close) 모두 `status = "PAUSED"`. Codex는 Windows 실행 파일뿐이고 Cowork 작업 VM에는 없다(`which codex` 없음). 구독 등급은 확인 필요.
- **F4 AGENTS.md는 ChatGPT 시절 안내 그대로.** 19~26행이 `gpt_final_configuration_manifest_v3_4.md` 등을 읽으라 함. 정리는 "Codex를 계속 쓰는지 사용자 확인 뒤"로 보류(docs/claude/system-design-ops-review-2026-10-09.md:85, :87). CLAUDE.md:73도 AGENTS.md를 언급.
- **F5 백업 공백.** `git status -sb` = `[ahead 331]`, 원격 끝 5db9c32(2026-09-29), 로컬 HEAD bb1f1f9(2026-10-19 23:30 KST), 커밋 안 된 파일 58개. git 무시: `stock-strategy-system/backups/`·`reconciliation_ledger.jsonl`·`decision_journal.json`·`workspace/outputs/auto-core/`(.gitignore:46, :47, :53, :157), `portfolio_state.json`(:31). 원격은 인증 없이 `ls-remote`가 막혀(“could not read Username”) 비공개로 보임 — 소유자 화면 확인만 남음. 지금 규칙은 push를 하지 않는 쪽: commit-docs.ps1:8 "never pushes", .claude/settings.json:12 `Bash(git push:*)`는 ask.
- **F6 입구 문서 크기.** CLAUDE.md 117행·17,498바이트, AGENTS.md 11,507바이트.
- **F7 이미 있는 장치.** 문서 커밋은 `_pending/<id>.txt`의 경로만(CLAUDE.md "Doc-only commits"), 공유 문서 편집 전후 sha256 대조(CLAUDE.md Session hygiene 마지막 줄), Builder는 별도 worktree(tools/dev_pipeline/README.md:9), 절차서 = manage-us-stock-strategy/references/, 상태판 = 개발 관제판, 결과물 모음 = docs/claude/library/INDEX.md, 재발 실수 기록 = review-stability 2절 사례표.
- **F8 Claude 사용량 압박 기록 없음.** docs/claude에서 사용량 한도 관련 문서 0건(키움 토큰 문서 제외). 추가 사용량 꺼짐(docs/claude/prompt-caching-review-2026-10-09.md:5).
- **F9 작업 상한.** 관제판 active 2건(org-setup, swap-soxl-pwr), 상한 개발 3·권한 1(CLAUDE.md:95). 같은 tools/** 수동 경로 작업 devpipe-merge-lock이 waiting.

## 3. AI 2개(Claude 메인 + 서브 검수)의 장점 — 우리 시스템 기준
| # | 장점 | 우리에게 크기 | 이유(원문) | 바뀔 조건 |
|---|---|---|---|---|
| 1 | **다른 회사 AI 교차 검수**(오류가 겹치지 않음) | **큼 — 단, 가설** | 검토 3층이 모두 Claude(F1), 같은 맹점은 시스템이 적어 둔 열린 한계(F2). Codex가 실제로 다른 결함을 찾는지는 자료 없음 | 시범 10건에서 Claude가 놓친 실제 결함(원문 확인) 0~1건이면 "작음" |
| 2 | Claude 사용량 절감 | 조건부·작음 | 내장 재검토 1건 약 40만 토큰(F2)이지만 Cowork에선 Codex를 못 불러 대체 불가(F3), 한도 압박 기록도 없음(F8) | Max 한도 경고·대기가 실제로 생기면 다시 봄 |
| 3 | 공급자 장애 대비 | 작음 | 자동 코어는 결정론 코드, LLM 실패가 코어를 막지 않음(CLAUDE.md Goal). 영향은 개발·검토·리서치뿐 | Claude 장애로 06:40 리서치 기록이 빠져 매수 티켓이 막힌 날이 생기면 "중" |
| 4 | 그림(아이콘·이미지) | 작음(개인 용도) | 투자_V2 대시보드는 HTML이라 수요 없음. 사용자는 이미 Codex로 그림을 만듦(F3) | — |
| 5 | 방향 잡기 2차 의견 | 작음 | 위원회는 정책·한도·권한 변경 때만(CLAUDE.md "Council") | 1번이 "큼"으로 확인되면 위원회에 외부 1표 검토 |

**단점·위험**
- 지적이 자주 틀린다(글 B). → 기존 V1 규칙대로 위치 안내, Claude가 원문 확인 후 채택. 확인 비용은 시범에서 잰다.
- 코드·문서·보유·전략 자료가 OpenAI로 간다. 비밀(.env·토큰·계좌번호)과 상태 파일은 주지 않는다.
- 지금 Codex 설정은 넓다(F3: workspace-write, computer-use·browser, 키움 조회). 시범은 별도 실행 옵션으로 `-s read-only` + MCP·플러그인 끔. Paseo를 거절한 이유(상주 프로그램·PC 권한)는 지금 Codex 설정에도 해당한다.
- 지침 이중 관리(CLAUDE.md + AGENTS.md). → AGENTS.md를 "외부 감사인 입구" 몇 줄 + CLAUDE.md 링크로 줄이고 CLAUDE.md:73도 함께 고친다(보호 경로 → 수동 경로).
- 비용: 이미 Plus면 0. 새로 구독하면 월 $20(실제 청구액 확인 필요), 시작 때 자동 갱신을 꺼서 무응답이면 기간 만료로 끝나게 한다.

**서브 AI 후보 비교**
| | ChatGPT Plus (Codex) | Google AI Pro (Gemini CLI) | DeepSeek |
|---|---|---|---|
| 코딩 CLI 포함 | 포함 — Plus "Codex on web, CLI, IDE extension"(developersdigest, 2026-10-16 갱신) | 포함 — AI Pro·Ultra에 Gemini CLI·Code Assist 상향 한도(Google 블로그) | 정액 구독형 코딩 CLI 확인 못 함(확인 필요) |
| 우리 PC 준비 | **설치·로그인·AGENTS.md·Judge 런처 있음, 10/18 사용**(F3·F4) | 새로 설치·설정 | 새로 설치 |
| 읽기 전용 실행 | `codex exec -s read-only`(글 B, 시범 첫 단계에서 동작 확인) | 확인 필요 | 확인 필요 |
| 자료 위험 | 미국 회사 | 미국 회사 | 개인 포트폴리오 자료 전송 부담 큼 |
| 판단 | **권장** | 대안 | 비권장 |

## 4. 적용안 (NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD)
- **NO_CHANGE**: 시범 안 함. 검토는 Claude 3층 그대로. 남는 것 = 같은 맹점(측정 안 됨). 무응답 기본값.
- **REMOVE/SIMPLIFY**: 해당 없음(Codex 예약 2개는 이미 PAUSED).
- **REUSE (권장 경로의 바탕)**: 이미 깔린 Codex·AGENTS.md를 다시 쓴다. 새 도구 설치 없음.
- **REPLACE**: 하지 않음. Claude Judge를 Codex로 바꾸지 않는다(판정 권한은 Claude 감사실).
- **ADD — "외부 감사인" 시범(Q1 a일 때만)**
  1. 범위: **수동 경로 Judge 세션**(사용자가 여는 Windows 대화형 Claude Code, 권한·한도 변경)에 의견 1개를 덧붙인다. Cowork가 Judge 지시문을 쓸 때 "Codex 읽기 전용 의견을 받아 원문 확인 후 표기" 1단계를 넣는다(문서만). 지금 허용 목록은 `Bash(cd *)`뿐이라(.claude/settings.local.json:3~4) `codex exec`마다 승인 창이 1번 뜬다 — 0으로 하려면 일회성으로 allow 규칙 1줄을 넣는다(settings 변경 = Cowork가 사용자 승인 받아). Cowork 내장 재검토(V5)와 파이프라인 자동 Judge(Read·Grep·Glob만, tools/dev-run.ps1:356)는 제외 — 시범 결과 뒤 다시 본다.
  2. 실행 옵션: `codex exec -s read-only`, MCP(키움 2개 포함)·computer-use·browser 끔. 비밀·상태 파일 금지는 지시문뿐이다 — 저장소 루트에 `.env.local`이 있고 Claude 쪽 차단(.claude/settings.json `Read(./.env.*)`)은 Codex에 걸리지 않는다. `-s read-only`가 읽기 범위까지 막는지는 확인 필요 → 시범 1건째에 Codex 세션 기록으로 .env*·auth.json·상태 파일을 열지 않았는지 확인하고, 열었으면 시범 중단.
  3. 권한: 판정을 올릴 수 없다(PASS를 만들지 못함). 낮추기·확인 요청만. 결과는 감사실 보고에 원문 그대로.
  4. 사전 등록(기본 처분): 시범 10건 또는 2026-12-31 중 먼저(수동 Judge 보고는 10/7~10/20에 19건 — 닿을 수 있는 수준). 기준 = Claude Judge가 놓쳤고 Claude가 원문으로 확인한 **실제 결함 2건 이상** → 유지 제안. 미달·무응답 → 시범 종료(NO_CHANGE). 함께 잴 것: 틀린 지적 비율, Claude 확인 토큰, 1건 소요 시간.
  5. 사람 손: 일상 0(allow 규칙을 넣은 경우. 넣지 않으면 Judge 1건당 승인 1번). 일회성: 구독 등급 확인 1번, allow 규칙 승인 1번, 새 구독이면 구독·자동 갱신 끄기 1번.
  6. 준비(Q1 a 뒤): Judge 지시문 1단계 = Cowork가 지시문을 쓸 때 넣음(문서). AGENTS.md + CLAUDE.md:73 정리 = 수동 경로 작업 1건(보호 경로). allow 규칙 = Cowork·사용자 승인.
- **Paseo**: 도입 안 함 — ① 총괄(Cowork)·worktree 분리(파이프라인)가 이미 있음 ② 상주 데몬·원격 접속·"플러그인은 데몬 PC 권한으로 실행" 경고(GitHub README), 키움 MCP가 있는 PC ③ 1인 개발, 열린 이슈 754개 ④ Windows 지원을 README 본문에서 확인 못 함. 다시 볼 조건: 두 회사 AI가 동시에 파일을 고치는 작업이 생길 때.

## 5. 그 밖의 회사 운영 도입 요소
| # | 요소(글 출처) | 우리 상태 | 제안 |
|---|---|---|---|
| E1 | 커밋 즉시 push(B 규칙④) → 코드·문서 원격 백업 | **공백**(F5) | **Q2 a(결정)**: 매일 23:50 별도 스크립트 offsite_backup.ps1(manage-us-stock-strategy/scripts/, 개발 파이프라인 offsite-bak)가 지금 브랜치 push. commit-docs.ps1의 "never pushes"는 그대로 두고 push는 새 스크립트만 한다. 보유 카드·결정 문서 등 docs/claude 489개가 비공개 GitHub에 처음 올라간다(.env·상태 파일은 git 무시). Windows 작업의 GitHub 인증 확인 필요 |
| E1b | (글에 없음, 이번 발견) 기록 파일 PC 밖 백업 | **공백**: 결정 일지·대조 원장·상태 백업·자동 코어 기록은 git 밖(F5) | **Q2 a·b 모두 포함**: 매일 PC 밖 위치로 복사. 위치(OneDrive 폴더 또는 외장 디스크)는 Q2 답에서 고름. GitHub에 안 올리고 코드 사본만 원하면 같은 위치에 `git bundle` |
| E2 | 파일 이름으로 커밋·커밋 전 log 확인(B 규칙②③) | 있음(F7) | 바꿀 것 없음 |
| E3 | "갑자기 바뀐 건 다른 쪽이 한 것, 되돌리지 마"(B) | 있음: sha256 재확인(F7) | 시범 시 AGENTS.md에 같은 줄만 |
| E4 | 문서 3층·인계 150줄(B (바)) | 있음(F7). 다만 CLAUDE.md 17.5KB 매 세션 로드(F6) | 법률팀 후보: context-layer-audit로 입구 다이어트를 측정한 뒤 결정(이번엔 변경 없음) |
| E5 | 잘된 결과물 쌓기(B (사)) | 있음: docs/claude/library/INDEX.md | 바꿀 것 없음 |
| E6 | 방향 먼저, 코딩 다음(B (다)) | 있음: Cowork 지시문 → Builder, 세션 시작 모델·노력 안내 | 바꿀 것 없음 |
| E7 | AGENTS.md 정리(F4) | 보류 중 | Q1 a면 외부 감사인 입구로, c면 보류 유지 |
| E8 | (이번 발견) Codex 키움 설정 | `KIWOOM_PROFILE = ""`(F3) — 키움 조회 규칙은 매 호출 options에 profile "실전계좌" 필수(CLAUDE.md:46) | 서버 기본 profile이 비어 있어(config.toml 키움 블록 2개) Codex가 호출 options에 profile "실전계좌"를 빠뜨리면 8005. 투자_V2 일을 Codex에 시키지 않는 동안은 영향 없음. Q1 a 시범은 MCP를 끄므로 해당 없음. 기록만 |

**순서(F9 상한)**: Q2(백업) 먼저 → Q1 시범 준비. 둘 다 tools/** 수동 경로라 devpipe-merge-lock과 한 작업으로 묶을지는 그때 정한다.

## 6. 내장 재검토 반영 (V5)
- 1회차 13건 — 결론을 바꾼 것 4건: Codex 사용 중(구독 등급 확인 먼저) · Cowork VM 호출 불가(시범 범위를 수동 경로 Judge로) · push로 덮이지 않는 기록 파일(E1b) · 작업 순서(백업 먼저). 문구 반영 9건: Codex 설정 범위·Paseo 이유 대칭 · 원격 비공개 확인 · 보유 문서 업로드 · "never pushes" 반전 · AGENTS.md와 CLAUDE.md:73 함께 · 글 번호 통일 · F8 근거 교체 · n=1 표기 · 자동 갱신.
- 2회차(바뀐 부분만) 6건 — 결론을 바꾼 것 1건: Q2를 "push+복사 / 복사만 / 현행" 3지로 나눔(더 큰 공백 E1b는 GitHub 업로드 없이도 메울 수 있음). 문구 반영 5건: Judge 세션 승인 창(손 0 조건) · 지시문은 문서, 수동 경로는 AGENTS.md·CLAUDE.md:73뿐 · Codex 읽기 범위와 .env.local · 끝 줄 숫자 · E8 원인 문구.

## 7. 결정 요청 (`결정 dual-ai-1020: Q1 ?, Q2 ?`, 기한 2026-10-27, 무응답 = 현행 유지)
- **Q1 서브 AI**(7-1로 권장 좁힘): **a) 지금 Plus일 때만 축소판 외부 감사인 시범(권장)** · b) Google AI Pro로 같은 시범 · **c) 안 함 — 지금 Plus가 아니면 이쪽이 권장**
- **Q2 백업**: **a) 코드·문서 매일 자동 push + 기록 파일 PC 밖 매일 복사(권장)** · b) 기록 파일(+코드 `git bundle`) PC 밖 매일 복사만, GitHub 업로드 없음 · c) 현행. a·b는 복사 위치(OneDrive / 외장 디스크)도 함께 답한다.

- **답(Q2)**: 사용자 "1. 결정 Q2 a(OneDrive)"(2026-10-20 10:24 KST, Cowork 대화) → 개발 파이프라인 작업 offsite-bak(docs/claude/offsite-bak-builder-prompt.md): 매일 23:50 지금 브랜치 push + git 밖·추적 안 되는 기록 파일(결정 일지·대조 원장·상태·자동 코어 기록·종가·연구 기록 등) OneDrive 날짜별 압축(30개 보관, workspace/private_inputs는 계좌 식별 정보 가능성으로 제외) + 05:50 PC 상태 점검 8번째 항목 backup_recent(26시간 기준). 08:50 알림 연결은 등록·첫 OK 확인 뒤 알림 지시문 v2.4(사용자 승인 1번) — 그 전까지 백업 실패는 host-status LATEST.json에만 보인다. 등록 전 GitHub 원격 비공개 확인(일회성). Q1은 대기.

- **답(Q1)**: 사용자 "결정 dual-ai-1020 : Q1 c"(2026-10-20 11:01 KST, Cowork 대화) → 서브 AI 시범 안 함. 검토는 Claude 3층 그대로. AGENTS.md는 E7대로 보류 유지(system-design-ops-review-2026-10-09.md:87의 "Codex 계속 쓰는지" 질문에는 "투자_V2에는 안 씀"으로 답이 됨). 다시 볼 조건은 7-1 바뀔 조건.

## 7-1. 자동화·간소화 관점 재평가 (사용자 질문 2026-10-20 10:24 "운영 자동화, 간소화 측면에서 AI 2개 사용은 합리적인가?")
**결론: 자동화·간소화만 기준이면 합리적이지 않다.** 운영 자동화 이익은 0이고 부품은 늘어난다. 합리적인 근거는 "검수 품질" 하나뿐이고 그것도 측정 전 가설이다. 그래서 Q1 권장을 좁힌다 — **지금 Plus 구독 중이면(추가 비용 0) 축소판 시범, 아니면 c(안 함)**.

| 기준 | 장점 | 단점 |
|---|---|---|
| 운영 자동화(매일 루프) | 없음 — 자동 코어는 결정론 코드이고 LLM 입력은 06:40 연구 기록 하나뿐(CLAUDE.md Hard safety 마지막 줄·Goal). 두 번째 AI는 이 루프에 닿지 않는다 | 없음(닿지 않으므로) |
| 사람 손 | 늘지 않게 만들 수 있다(Claude가 뒤에서 부름) | 줄여 주는 손도 없다 — 지금 남은 손(키움 주문 입력, dev-merge 1번, 결정 답)은 그대로 |
| 간소화(부품 수) | — | 계정·로그인·설정·지침 파일이 2벌이 된다. 실제로 AGENTS.md는 ChatGPT 시절 안내로 3주째 낡아 있다(F4) — 2벌 관리가 낡는다는 우리 쪽 증거. Codex 기본 설정은 권한이 넓다(F3) |
| 고장 지점 | Claude 장애 때도 개발 검토가 이어짐(작음) | Codex 로그인 만료·한도·업데이트로 실패할 수 있음(만료 주기 확인 필요) — 그래서 실패해도 아무것도 막지 않게(의견 없음으로 기록) 해야 한다 |
| 개발 품질 | 다른 회사 모델이 Claude가 놓친 결함을 찾으면 병합 뒤 결함·재작업이 준다(가설, F2) | 틀린 지적을 Claude가 원문으로 확인하는 비용(측정 전) |
| 비용 | 이미 Plus면 0 | 새로 구독하면 월 $20 |

- 판단 기준: 프로젝트 지침 7절 "복잡도 증가는 명시적 미충족 요구 + 검증 가능한 이익이 있을 때만". 미충족 요구(같은 모델 맹점)는 시스템이 적어 둔 열린 한계(review-stability-2026-10-13.md:19)로 명시돼 있지만, 이익은 아직 검증 전 → 검증 자체를 가장 작은 형태로만.
- **축소판 시범(4절 ADD를 줄임)**: ① 수동 경로 Judge에만 ② AGENTS.md 재작성 안 함 — 규칙은 매번 부를 때 지시문 안에 넣음(지침 2벌 관리를 만들지 않음) ③ 설정 변경은 `codex exec -s read-only` 허용 1줄만(Judge마다 승인 창을 없애 일상 손 0) — 단 8절 읽기 범위 확인(.env.local·auth.json을 못 읽음) 뒤에만, 사용자 승인 1번(일회성) ④ Codex 실패 = "의견 없음" 기록, 아무것도 막지 않음 ⑤ 10건 또는 2026-12-31 자동 종료, 기준 미달 = 끝(현행).
- 같은 회사 안의 대안(부품 0): Builder와 Judge를 다른 모델로 두는 것(파이프라인 Judge는 이미 Opus 고정, Builder는 작업마다 Sonnet/Opus). 같은 회사 모델이라 맹점 분리 효과는 더 약할 수 있고 측정된 적 없음.
- 바뀔 조건: 수동 경로 Judge가 PASS한 변경에서 병합 뒤 결함이 나오는 사례가 쌓이면(품질 근거 강화) / Claude 장애·한도로 개발이 멈춘 날이 생기면(가용성 근거) / Codex 로그인 만료가 잦으면(시범 중단).

## 8. 확인 필요
- 현재 ChatGPT 구독 등급(Free/Plus/Pro) — ChatGPT 설정 화면에서 1번 확인.
- `codex exec -s read-only`가 지금 설치본·로그인으로 동작하는지(시범 첫 단계).
- 새 구독 시 실제 청구액과 Codex 주간 한도.
- GitHub 원격이 비공개인지 소유자 화면 확인.
- Windows 작업 환경의 GitHub 인증(Q2 a일 때).
- `codex exec -s read-only`의 읽기 범위(.env.local·auth.json·상태 파일을 읽을 수 있는지).

## 9. 바뀔 조건
- 결론 1·2·3: 시범 10건 결과(기준 2건) / Claude 한도 경고 발생 / Cowork에서 Codex 호출 수단이 생김.
- 결론 4(Paseo): 두 회사 AI 동시 편집 작업 발생, Windows 공식 지원 확인.
- 결론 5(백업): 원격이 공개로 확인되면 push 전에 비공개 전환 또는 다른 백업 경로.

검토 완결(7-1 포함): 원문 확인 15/21(근거 항목 F1~F9·첨부 3·웹 3 확인, 8절 6건 확인 필요) · 내장 재검토 1차 2회(반영 19건) + 7-1·백업 지시문 2회(1회차 18건·2회차 10건 모두 반영 — 2회차는 지시문만 바꿈: 압축 임시 이름, 종가 폴더 추가, P7 승격 방지 등) · 미해결 0 · 자료 시점 2026-10-20 12:20 KST · 바뀔 조건 9절
