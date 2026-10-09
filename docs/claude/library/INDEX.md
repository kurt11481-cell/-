---
id: library-index
type: index
status: current
as_of: 2026-10-09
summary: 현행 분석 문서 포인터. 수동 작성(설계 1단계, K0). 캐시이지 권한이 아님 — 가격·계좌는 항상 키움 재조회.
---

# 분석 라이브러리 색인 (수동, 2026-10-05)

규칙: 설계 `docs/claude/analysis-library-design-2026-10-03.md` 3절 읽기 순서 — INDEX → 필요한 절만(`grep -n "^#" <파일>`로 헤딩 확인 후 범위 읽기). 색인 갱신은 카드 수락·상태 변경 때만(수동). 요약은 원문 등급(D)을 넘지 못한다. 못 읽으면 기존 방식으로 진행.

## 현행 (status=current)

| 종류 | 종목 | as_of | 유효기한 | 경로(docs/claude/) | 한 줄 요약 |
|---|---|---|---|---|---|
| scenario(시스템 전제) | ALL | 2026-10-09 | 2027-06-30 | market-scenario-27h1-2026-10-09.md | 사용자 지정(10/9) 시나리오 SCN-27H1: B0 = 2027 상반기까지 후반부 강세장(조건부, 신한 김성환 9/22·9/30·10/7). 종료 트리거 T1~T6 점검표(3절, 부록 A 스크립트로 갱신) — 10/9 🟠 주의(T1 금리·T3 HY·T4 유가 근접). 전략 4절 · 작업별 적용 5절. 근거 강도 0, 규칙·예산 불변. 예약 3개(통합 점검·관심 명단·Next 샌디스크 월간) 10/9 연결 |
| card(보유 현행) | MVLL·SOXL·NBIS | 2026-10-02 | 다음 M6 카드에서 갱신 | integrated-stock-cards-v1-2026-10-02.md 2~4절 | 보유 3종목 HOLD·트리거 표(10/2 17:20 갱신). 보유 현행 카드로 확정(2026-10-04) |
| card(관심) | MU·BE·DELL·AMD | 2026-10-02 | 확인 필요 | 같은 파일 5절(BE·DELL·AMD)·6절(MU) | 관심 카드·트리거 표 |
| card(관심) | PWR | 2026-10-03 | 확인 필요 | watch-card-PWR-2026-10-03.md | 사용자 수락, kill ①~④ |
| card(관심) | LITE | 2026-10-03 | 확인 필요 | watch-card-LITE-2026-10-03.md | 사용자 수락, R2.1 10/10, CRDO 대체 |
| plan | MVLL | 2026-10-04 | 2026-10-08 | mvll-investor-day-plan-2026-10-04.md | Investor Day 대응 B+ 사용자 채택(10/4): ① 행사 전 약 118주(V5 지정) ② 반응 보고 약 119주 ③ 159주는 M6 v2. 9절 발표 예측 · 13절 ② 경계(시가 -10% 이하 큰 갭만 저점 매도 안 함) |
| technical | MRVL(→MVLL) | 2026-10-06 | 2026-10-07 | 외부 폴더 chatgpt_종목분석결과/기술분석/MRVL_20261006/MRVL_기술분석_리포트.md (+ 같은 폴더 MVLL_이벤트_시나리오_매도가.md: 시나리오 5개 확률 A20·A'15·B35·C1 20·C2 10, ① 사다리 $39·$40+21:30 정리, ② 시나리오별 가격대) | 행사 당일 기술·옵션(D): 중기 상승, 단기 266~280 박스 가능성, 옵션 중립/변동성 대기(10/9 ±7.2%). MVLL 환산선(V1≈272.5·V2≈268.3·②≈257.7·$40≈279.7). 소비처: Investor Day 계획 ①②, 10/7·10/8 통합점검, 10/8 M6 v2 |
| m6 | MVLL·SOXL | 2026-10-03 | 확인 필요 | m6-relative-comparison-mvll-soxl-cash-2026-10-03.md | 현금화 근거 없음, 비교상 MVLL 근소하게 약함 |
| m6 | MVLL·SOXL·NBIS·MU·BE·DELL·PWR·LITE | 2026-10-08 | 다음 M6 카드 | m6-relative-comparison-7stock-2026-10-08.md | 7종목+현금 비교(10/6 확정 종가, 10/8 사용자 수락 "판단에 씀"): M6 약세 철회·MVLL 20%(159주) 유지 결정, 보유 3 HOLD(MVLL 근거 약 1), 관심 5 WATCH(MU·BE·DELL ② E 1.93, PWR·LITE 상품 승인). Marvell 발표 자료 원문 재확인(C2 없음). 7절 매도 뒤 경로 재계산 → oi-pilot-1 입력 |
| leadership | ALL | 2026-10-03 | 확인 필요 | next-leading-sectors-2026-10-03.md | 차기 후보 1 전력 병목·2 AI 네트워크·3 광부품 상류 |
| ledger | ALL | 2026-10-03 | — | external-claims-ledger.md | 외부 주장 원장(강도 0, 추가 전용) |
| external-review | ALL | 2026-10-03 | — | external-batch-review-2026-10-03.md | 외부자료 10건 검토, 판단 변화 없음 |
| 명단(머리말 없음) | 관심 5 | 2026-10-03 | — | watchlist-registry.json · watchlist-rubric-r2-scores-2026-10-03.json | 관심 명단 단일 출처(R2.1). 파일 자체가 원본 |
| design | — | 2026-10-03 | draft | analysis-library-design-2026-10-03.md | 이 라이브러리 설계(사용자 승인 전 초안) |
| design | ALL | 2026-10-04 | 확인 필요 | next-sandisk-discovery-design-2026-10-04.md | Next 샌디스크 발굴: 결과 문서 next-sandisk-scan-*.md(병목 씨앗)·N-렌즈 v1.1, 예약(매월 첫 토요일 전체 + 나머지 토요일 주간 점검, 제안 모드)+수시(17절)·다른 작업 연결(19절), 사용자 결정(10/4~5, 15·16절). 유지 보호(다음 실적까지·최대 13주)·F5는 자동 모드 전, 씨앗 칸 1개(관심 5+1)는 첫 점화 씨앗 전. 사이클 시계 → 10/8 M6 카드 입력 |
| research | ALL | 2026-10-04 | — | library/research/next-sandisk-2026-10-04/ | Next 샌디스크 조사 3건 정리 기록(D급) + 원 보고서 출처 193개, 리플레이 스크립트·SNDK/SOXX 일봉(참고값), 수시 발굴 1회차 원 보고서 6건(scan-*.md), 어닝콜 공급 제약 지도(10/5, 연결 L4). 설계 부록 E-4·19절 |
| leadership-n | CIEN·HWM·CRS·SOLS 외 | 2026-10-04 | 2026-11-07 | next-sandisk-scan-2026-10-04.md | Next 샌디스크 수시 1회차(사용자 수락 10/4): 씨앗 0 · 관찰 4(CIEN·HWM·CRS·SOLS, v1.1 표시로 모두 병목 품질주) · GFS 제외(X2) · G2 해석 유지. 다음 달 조사 목록 포함 |
| design-review | ALL | 2026-10-04 | 2027-01-02 | next-sandisk-lens-v2-review-2026-10-04.md | 판별 기준 재검토(위원회 Lite): v1.1 적용(10/4, 관찰 표시 분리·질문 3 보강, 판정 불변). ②③⑥은 2027-01 검토 |
| design-review | ALL | 2026-10-05 | — | strategy-risk-framework-review-2026-10-05.md | 외부 리스크 지침 검토(사용자 승인 10/5): **L1/L2 한 화면 검토 템플릿 5-1**(계좌 점검선 도달 시 사용, fail-closed: N·E>1.9면 위험 감수 불가), 종목 프로토콜 개정 a1(반영 주장 3문·리스크 분류·이벤트 유사 사례·ETF 투시), M6 v2 입력 2줄(판단 영수증 사양 1-1), 원장 EXT-20261005-07~10. 리스크 전체 표는 리플레이 검증 뒤 |
| design | ALL | 2026-10-05 | — | analysis-linkage-map-2026-10-05.md | **분석 결과 연결 지도·규칙(사용자 상시 지시 10/5)**: 모든 분석 결과는 다른 작업이 읽는 곳에 남기고 소비자 지정. 새 작업 체크리스트 1절 |
| design | ALL | 2026-10-06 | K3 승인 전(시범 3회 뒤) | order-instruction-design-2026-10-06.md | **주문 지시서(ORDER_INTENT_ONLY) 설계**: 9단계 판단 회로(관문→3층 확률→체결 포함 후회표→4인 위원회 줄이기·보류만→결정론 수량), 낮 발행·저녁 LOC·다음 날 대조, 봉인 SHADOW 시범 10/7~(기록 order-instructions/). 권한 변화 없음 |
| rules(예약) | ALL | 2026-10-09 | 사용자 승인 때까지 | integrated-check-prompt-v3.12.2-2026-10-09.txt (규칙 본문) + integrated-check-prompt-v3.12.2-L-loader-2026-10-09.txt (예약 작업 지시문, 해시 고정) | **통합 점검 현행 규칙**(화~토 06:40). 로더는 규칙 파일 sha256(LF) ee098920…1e59를 확인한다. 롤백 원본: integrated-check-prompt-v3.12.1-2026-10-09.txt · v3.12.1-L 로더. 예약 지시문 원문 보관: scheduled-prompts/README.md (8개, 해시 표) |

## 문서 밖 최신본(포인터만)
- 시장환경 메모: workspace/outputs/save-daily-offline-replay/LATEST_MARKET_ENV_MEMO.md (SAVE 작업이 씀)
- 점검 기록: 대시보드 ArtifactData runs (파일 아님)
- 개장 전 기록: workspace/outputs/pre-open/<날짜>-<이벤트>.md (월요일·이벤트일 예약이 씀, 공식 사실=URL / 프리마켓=참고)
- 종목 분석(Chat): chatgpt_종목분석결과/종목분석/SNDK_20261005/SNDK_종목분석_요약.md (Phase 1~2·WATCH 판정) · 옵션 분석: chatgpt_종목분석결과/옵션분석/SNDK_20261002/SNDK_옵션분석_리포트.md
- 종목 분석(Chat): chatgpt_종목분석결과/종목분석/CIEN_20261006/CIEN_종목분석_요약.md (Phase 2·WATCH 판정, 2026-10-06) · 데이터시트: CIEN_Phase1_데이터시트.md (Level 1~3) — 소비처: 주간 재채점·Next 샌디스크 주간 점검·M6 v2
- 행사 뒤 시나리오(Cowork): chatgpt_종목분석결과/기술분석/MRVL_20261006/MRVL_CIEN_행사후_시나리오_후회분석.md (2026-10-07, MRVL·CIEN 시나리오 4개 D · ② 119주/CIEN 후회 비교 · 권장 P 결정 대기) — 소비처: Investor Day 계획 11-3, 10/8 M6 v2(CIEN 도전자 행), CIEN 주간 재채점
- 옵션 분석(Cowork): chatgpt_종목분석결과/옵션분석/MRVL_20261007/MRVL_옵션분석_리포트.md (+ CBOE 체인 CSV, 2026-10-07 프리마켓 스냅샷: 중립/변동성 대기, $270~$300 박스, MVLL 매도 시점 몬테카를로) — 소비처: MVLL ②③ 가격(설계 7-5), 10/8 M6 v2, oi-pilot-1
- 종목 분석(Chat): chatgpt_종목분석결과/종목분석/PWR_20261006/PWR_종목분석_요약.md (Phase 2·WATCH 유지, 2026-10-06, 가격 키움 미검증) · 데이터시트: PWR_Phase1_데이터시트.md (Level 1~3) — 소비처: PWR 관심 카드 갱신 제안·통합 점검·주간 재채점·M6 v2

## 보관 (superseded, 파일은 옮기지 않음)
- mvll-holding-card-2026-10-01.md → 통합 카드 2절로 대체
- soxl-nbis-holding-cards-2026-10-01.md → 통합 카드 3·4절로 대체
- watch-card-CRDO-2026-10-03.md → 관심 제외, LITE로 교체

## 구판 (참고만, 삭제·이동 안 함)
- 통합 점검 지시문 v3.4~v3.12 전체 파일(integrated-check-prompt-v3.4-baseline · v3.5~v3.9-draft · v3.10-reconstructed · v3.11-draft · v3.12), 구 로더 v3.12-L. 롤백용으로만 v3.12.1 규칙 파일과 v3.12.1-L 로더가 남아 있다. 현행은 위 rules 행의 v3.12.2.
- 관심 명단 주간 초안 watchlist-weekly-prompt-v1-draft-2026-10-03.txt · weekly-watchlist-rotation-prompt-v2-draft-2026-10-03.txt (현행 예약 원문은 scheduled-prompts/watchlist-weekly-rescore.txt)
- 관제판 점검 초안 dev-board-review-prompt-v1-draft-2026-10-03.txt (v1.1 초안은 현행 예약과 끝 개행만 다름)

## 이름 접두어 (A5, 이름 변경은 하지 않음 — 새 문서에서 첫 등장 때 붙인다)
- 로드맵 S0~S8: 예 "로드맵 S7b" = 일지, S7a = 카드 코드화 (future-tools-roadmap-2026-10-05.md)
- 정책(손실한도 검토) S0~S7: 예 "정책 S7" = 정책 적용 (loss-limit-review-s5-policy-proposal-2026-10-01.md)
- 카드 트리거 S4·S5·S6·S8: 예 "카드 트리거 S4" (SOXL 카드 트리거, 통합 점검 규칙 파일·OI-20261009-SOXL-2)

## 확인 필요
- 유효기한(valid_until)은 문서에 명시된 기한이 없어 비워 둠 — 카드 수락 때 정할지 결정 필요.
- 통합 점검 v3.7 대상(AMD 포함)과 명단 members(MU·BE·DELL·PWR·LITE) 차이는 v3.8 적용 전 의도 확인 필요(설계 8절).
