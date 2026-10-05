---
id: library-index
type: index
status: current
as_of: 2026-10-05
summary: 현행 분석 문서 포인터. 수동 작성(설계 1단계, K0). 캐시이지 권한이 아님 — 가격·계좌는 항상 키움 재조회.
---

# 분석 라이브러리 색인 (수동, 2026-10-05)

규칙: 설계 `docs/claude/analysis-library-design-2026-10-03.md` 3절 읽기 순서 — INDEX → 필요한 절만(`grep -n "^#" <파일>`로 헤딩 확인 후 범위 읽기). 색인 갱신은 카드 수락·상태 변경 때만(수동). 요약은 원문 등급(D)을 넘지 못한다. 못 읽으면 기존 방식으로 진행.

## 현행 (status=current)

| 종류 | 종목 | as_of | 유효기한 | 경로(docs/claude/) | 한 줄 요약 |
|---|---|---|---|---|---|
| card(보유 현행) | MVLL·SOXL·NBIS | 2026-10-02 | 확인 필요 | integrated-stock-cards-v1-2026-10-02.md 2~4절 | 보유 3종목 HOLD·트리거 표(10/2 17:20 갱신). 보유 현행 카드로 확정(2026-10-04) |
| card(관심) | MU·BE·DELL·AMD | 2026-10-02 | 확인 필요 | 같은 파일 5절(BE·DELL·AMD)·6절(MU) | 관심 카드·트리거 표 |
| card(관심) | PWR | 2026-10-03 | 확인 필요 | watch-card-PWR-2026-10-03.md | 사용자 수락, kill ①~④ |
| card(관심) | LITE | 2026-10-03 | 확인 필요 | watch-card-LITE-2026-10-03.md | 사용자 수락, R2.1 10/10, CRDO 대체 |
| plan | MVLL | 2026-10-04 | 2026-10-08 | mvll-investor-day-plan-2026-10-04.md | Investor Day 대응 B+ 사용자 채택(10/4): ① 행사 전 약 118주(V5 지정) ② 반응 보고 약 119주 ③ 159주는 M6 v2. 9절 발표 예측 · 13절 ② 경계(시가 -10% 이하 큰 갭만 저점 매도 안 함) |
| m6 | MVLL·SOXL | 2026-10-03 | 확인 필요 | m6-relative-comparison-mvll-soxl-cash-2026-10-03.md | 현금화 근거 없음, 비교상 MVLL 근소하게 약함 |
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

## 문서 밖 최신본(포인터만)
- 시장환경 메모: workspace/outputs/save-daily-offline-replay/LATEST_MARKET_ENV_MEMO.md (SAVE 작업이 씀)
- 점검 기록: 대시보드 ArtifactData runs (파일 아님)

## 보관 (superseded, 파일은 옮기지 않음)
- mvll-holding-card-2026-10-01.md → 통합 카드 2절로 대체
- soxl-nbis-holding-cards-2026-10-01.md → 통합 카드 3·4절로 대체
- watch-card-CRDO-2026-10-03.md → 관심 제외, LITE로 교체

## 확인 필요
- 유효기한(valid_until)은 문서에 명시된 기한이 없어 비워 둠 — 카드 수락 때 정할지 결정 필요.
- 통합 점검 v3.7 대상(AMD 포함)과 명단 members(MU·BE·DELL·PWR·LITE) 차이는 v3.8 적용 전 의도 확인 필요(설계 8절).
