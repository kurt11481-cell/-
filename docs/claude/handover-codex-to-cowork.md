# 투자_V2 인수인계 요약 (Codex → Cowork)

작성: 2026-09-29 (같은 날 정정 반영) · 근거: `AGENTS.md`, `CHANGELOG.md`, 로컬 git 상태(`코덱스저장소`)
위치: 2026-09-30 Claude 프로젝트 문서에서 저장소 `docs/claude/`로 이동

## 1. 시스템 한 줄 요약
미국 주식/ETF 보유 종목 전략·전술 레이더·장 마감 후 알림을 만드는 **리서치/의사결정 보조 시스템**. 결정론적 규칙이 LLM 결론보다 우선하고, 데이터가 없거나 오래되면 "실패 시 닫힘(fail closed)"으로 표시한다. **주문 권한은 전 버전에서 일관되게 없음(`order_authority=false`).**

## 2. 절대 규칙 (AGENTS.md)
- 브로커 주문을 넣거나 예약하지 않는다. 모든 알림은 "다음 세션 검토 후보".
- 가격 변동으로 체결을 추정하지 않는다. 보유·현금·단계·원가·체결은 **사용자 명시 확인** 또는 **검증된 읽기 전용 브로커 스냅샷**으로만 갱신.
- 예약 에이전트는 runtime/dedup 메타데이터만 원자적으로 갱신 가능.
- 승인된 정책(`alert_policy.json` 등)은 사용자 명시 승인 없이 수정 금지. 비밀정보 노출 금지.
- 브로커 스크린샷은 스키마 검증된 조정안(reconciliation proposal)을 사용자가 확인하기 전까지 신뢰하지 않음. 브로커 표시가격을 확정 종가 근거로 쓰지 않음.
- 코드/식별자/스키마는 영어, 사용자용 투자 리포트는 한국어 기본.
- 변경 후 해당 validator 실행 필수.

## 3. 핵심 파일
| 용도 | 경로 |
|---|---|
| 스킬 원본(정식) | `manage-us-stock-strategy/` (SKILL.md, scripts, schemas, tests, references) |
| 포트폴리오 상태 | `stock-strategy-system/portfolio_state.json` |
| 알림 정책 | `stock-strategy-system/alert_policy.json` |
| 런타임/중복제거 | `stock-strategy-system/alert_runtime_state.json` |
| 자동화 프롬프트 | `stock-strategy-system/AUTOMATION_PROMPT_EN.md` |
| 리서치 전용 레지스트리/유니버스 | `workspace/policies/` |
| 통합 Production authority | `workspace/policies/integrated_identity_session_activation.json` |
| 개발 리뷰 절차 | `manage-us-stock-strategy/references/development-{plan-review,change-review,incident-analysis}.md` |
| 키움 문서/연동 | `references/kiwoom-documentation-tools.md`, `references/kiwoom-mcp-local-integration.md` |
| 외부 가이드 | `E:\사업\##금동한\chatgpt md_주식\` — manifest v3.4 §12.3/§12.8/§14.0, Codex Prompt Guidance v1.0 §9 |

## 4. 버전 흐름 (CHANGELOG)
- **v2.2** 전술 레이더: MVLL, SOXL, NBIS, BE, TOST, NOW, FSLY 7종. 기회 품질과 실행 가능성 분리.
- **v2.3** 보유 전략 + 전술 기회 + 자금 재배치 통합 오케스트레이터(읽기 전용). 검증된 현금만 매수여력.
- **v2.4** POST_MARKET 확정 빌드 + PRE_OPEN 델타 리프레시, hard-risk 규칙 출처 명시.
- **v2.5** 선택적 독립 종가 검증, 브로커 스냅샷 조정(명시 확인 후 원자 적용), 초보자용 한국어 렌더링.
- **v2.6** 보유 종목 Shadow 리서치 베이스라인(NBIS, MVLL/MRVL, SOXL), 5/20/60 세션 Shadow 체크포인트, GitHub Actions 안전 CI.
- **v2.6.3** 무료 Web 근거 기반 신규매수 리서치 초안(수량 없음).
- **v2.6.4~6.5** 키움 REST 읽기 전용 Shadow 어댑터, 리플레이/락 강화.
- **v2.6.7** 세션 인지 키움 우선순위: 키움 = `KIWOOM_PRIMARY_GUARDED_SCOPED`, yfinance = 진단 Shadow/스코프 폴백.
- **v2.6.8** 장 마감 후 자동화 10:15 KST 단일 확정 실행(`POST_MARKET_FINALIZED`).
- **v2.6.9** 이벤트 리스크 번들(공식 출처), append-only 해시 체인.
- **v2.6.12~13** 보유 종목 밸류에이션 스냅샷, Shadow 활성화 게이트, 이벤트 커버리지 완성.
- **Recovery and expansion hardening**: 스케줄 작업 배포 출처 게이트, MVLL RVOL20 계보, 키움 후보 발굴 allowlist, 미래 주문 Shadow 계약(수량 null).
- **Capital Reallocation Shadow (최신)**: NEW_BUY/ADD/HOLD/TRIM/EXIT 액션별 이벤트 준비도, KEEP_CASH 비교 포함 가상 전체 포트폴리오 재컴파일(`SHADOW_ONLY`), 독립 읽기 전용 Judge.
- 사이드카: Continuous Improvement Evidence(런 원장, 1/5/10/20 세션 사후 성과, 비적용 정책 제안).

## 5. git 상태
- 2026-09-30 갱신: 아래 미커밋 변경은 5개 커밋(`6558eb9`~`8c251f9`)과 CLAUDE.md 커밋(`73f9c19`)으로 정리됨. 브랜치 `codex/master-recovery-expansion`, push 전. 상세는 `docs/claude/test-and-policy-review-2026-09-29.md` §5.
- (2026-09-29 기록) 원격 대비 로컬 커밋 11개 미푸시. 최근 커밋은 수동 자문(advisory) 대시보드 계열 `195e115` → `0026e79`, 그 전은 SEC 공식 이벤트 intake live shadow 계열.
- (2026-09-29 기록) 미커밋: 수정 44개 파일(+11,065/-296) + 미추적 76개 항목.
  - 처음 보고한 "548개 파일/CRLF 문제"는 Linux git이 `core.autocrlf` 없이 본 착시. 작업본 CRLF는 Windows git(`autocrlf=true`) 기준 정상이며, 일부 증거 artifact가 CRLF 원본의 raw 해시를 참조하므로 **줄바꿈 일괄 변환 금지**.
  - 주요 코드: `portfolio_decision_dashboard.py`, `run_manual_portfolio_analysis.py`, `render_beginner_portfolio_report.py`, `validate_technical_snapshot.py`, `deployment_provenance.py`, `kiwoom_account_readonly_bridge.py` 및 테스트.
- 커밋하지 않고 로컬에 둔 것: `visualizations/`, `%SystemDrive%/`(환경변수 미전개로 생긴 폴더로 보임), 미추적 `workspace/outputs/*`.
- 백업 브랜치 다수(`backup/pre-*`) 존재.

## 6. Cowork 환경 차이
- AGENTS.md의 **context-mode(`ctx_*`) 규칙은 Codex 전용** — Cowork·Claude Code에는 해당 도구 없음. Claude Code는 `CLAUDE.md`를 읽음.
- VM의 git 사용 시 `-c core.autocrlf=true`와 `--no-optional-locks` 사용 (index.lock 잔존 방지).
- 테스트는 VM 복사본 + Python 3.13(uv) 환경에서 실행.
- 키움 REST API MCP(Spec/Exec) 연결됨. 문서 조회는 Spec 사용, **`kiwoom_order_submit`은 사용하지 않음**(주문 금지 원칙).
- GitHub push/pull: VM에 인증 없음 → 사용자가 직접 push 또는 Claude Code의 GitHub 플러그인 사용.

## 7. 다음 단계
- `docs/claude/test-and-policy-review-2026-09-29.md`의 실패 분류 참조. 남은 핵심 과제는 Kiwoom acceptance manifest 해시 고정 문제(K3).
