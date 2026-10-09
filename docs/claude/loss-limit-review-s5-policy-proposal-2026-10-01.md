# 손실한도·노출 정책 — S5 정책 제안 초안 (2026-10-01, 적용 안 함)

- 성격: K3 준비 제안서. 정책·상태 파일은 바꾸지 않았다(`alert_policy.json` `184008bd…`, `portfolio_state.json` `28fd77c5…`). S6 Independent Judge → S7 사용자 승인 전에는 효력이 없다.
- 권한: `order_authority=false`, `quantity_authority=none`, `execution_quantity=null`. 이 문서의 "권고"는 비중 표시뿐이다.
- 입력: 인계 문서 10절, `s4-3-leverage-up-candidates-2026-10-01.md` 7절·S4-3 Builder 보고, `loss-limit-review-s5-prep-decisions-2026-10-01.md`(A-1b·A-2·3·4·5·6·6b), S1 결정 1·2, `mvll-holding-card-2026-10-01.md`(HWM 갱신·종가 기준).
- 근거 등급: 모두 C/D(합성·연구)다. A/B 등급(검증된 실운영) 근거는 없다.
- 권장 설정: 이 문서 검토 Opus · xhigh. S6 Judge는 별도 Claude Code 세션 Opus · xhigh(파일 수정 없음).
- 상태: **S7 사용자 승인 완료(2026-10-01, 항목 1~7), 적용 안 함.** 기준은 "S5 확정안 r2" 절, 5절 diff r2, "S7 사용자 승인" 절이다. 0~4·6절과 부록 B·C의 규칙 초안(C.5, C.8~C.13 포함)은 이력이며, 확정안 r2와 다르면 확정안 r2가 우선한다. 정책 파일 반영은 S7 Builder(worktree, K3) → 별도 Judge → 사용자 커밋·병합으로만 한다.

## S5 확정안 r2 (2026-10-01, 사용자 결정 D1~D7 + S6 필수 수정 14건 + 재확인 수정 4건과 C1, 재확인 2차 입력)
- 정정(2026-10-09, FX-1009 D3): 1.55 = 사용자 승인 위험 예산(미검증 현행안). 채택 기준을 통과한 값이 아니다(본문 "검증 범위 밖"·"forward shadow도 없다").
- p-earn 개정(2026-10-03): 확인된 미공지는 금지 구간 아님, 확인 못 함은 금지 유지. :35·:398·:575·:580(이 메모를 넣기 전 :34·:397·:574·:579)의 '실적일 미확인 = 금지'를 대체 — `docs/claude/p-earn-earnings-blackout-amendment-2026-10-03.md`

- 권한: 주문·수량 권한 없음. 모든 권고는 종가 확정 뒤 다음 정규장 전 1회, 목표 비중으로만 표시한다.
- 근거 범위(S6 J4): 카드 종목 코어 + SOXL 보충 구성은 S4-3 I1(SOX 단일 지수, ETF 코어) 근거 밖이다. 감수 위험 표(부록 C.6)는 지수 1배 + 3배 모형이다.
- R0 공통 fail-closed(S6 J6)
  - 다음 중 하나면 채우기·신규 매수 권고를 멈추고 "미확인"으로 표시한다: E·자산·V 계산 불가, 미등록 상품 보유, HWM·선·멈춤 상태 또는 `decision_journal.json` 없음·손상, 브로커 대조가 `broker_snapshot_max_age_calendar_days`(4일)보다 오래됨, 필요한 가격 누락, 입출금 미신고(R6).
  - 줄이기 권고와 경고는 "미확인" 표시를 달고 계속 낸다.
- R1 노출 측정
  - 명목 N = Σ(배수 × 평가액 비중). 등록된 상품만 센다: SOXL·TQQQ 3, MVLL 2, BE·MU·NBIS·DELL·AMD·DRAM 1, 현금 0. 미등록 상품은 신규 매수 권고를 막고, 보유 중이면 E 계산 불가(R0).
  - SOX 환산 V = 포트폴리오 252세션 일간 수익률 표준편차 ÷ SOXX 표준편차(SOXX는 측정용, 보유 안 함). 현재 비중 고정, 모든 상품과 SOXX에 같은 세션 창. 이력 252 미만이면 가용 세션(최소 60), 60 미만이면 그 상품 신규 편입 불가.
  - 가격 출처: 키움 정규장 종가. 최신 세션은 정규장 마지막 30분봉 종가(평일 16:00 표기 봉, 조기 폐장일은 폐장 직전 봉). Yahoo는 참고용이고 평균하지 않는다. 과거 이력에서 시간외가 섞이지 않은 정규장 종가를 얻는 방법은 S7 Builder가 먼저 확인한다(확인 필요). 얻지 못하면 V 계산 불가(R0).
  - E = max(N, V).
- R2 위험 예산
  - 목표 1.55, S7 적용 때 바로. 검증 범위(1.32) 밖이고 OOS·forward shadow를 생략한 사용자 승인 위험 예산이다.
  - E ≥ 1.85: 줄이기 권고 + 신규 매수 권고 멈춤.
  - E ≤ 1.25: 채우기 권고(카드 ADD 종목, 없으면 SOXL). 기본 대상 SOXL이 R5로 멈춰 있으면 대체하지 않고 권고를 생략한다.
  - 비중을 늘리는 모든 권고(채우기, 대역 안 1.25 < E < 1.85의 신규 매수, 교체의 매수 쪽)는 권고 목표 비중으로 계산한 예상 E ≤ 1.55이고 종목 상한 이내여야 한다. 넘으면 그 권고를 내지 않는다(S6 재확인, 필수 수정 9).
  - 절대 상한: E ≥ 1.9이면 모든 신규 매수 권고 차단 + 줄이기 "긴급". 바꾸려면 별도 사용자 승인과 Judge.
  - 줄이기 순서(S6 J11): ① 종목 상한(0.4배) 초과분(매도 전용 MVLL 포함) ② 카드 TRIM·EXIT 종목 ③ SOXL. SOXL이 없으면 다른 종목으로 대체하지 않고 "초과 미해소" 경고만 낸다.
  - 분류(S6 J1): 줄이기·1.85 밴드·1.9 상한·검토선·멈춤·종목 상한·R5·R6은 위험 축소 통제다. 채우기 권고는 수익 추구 성격이라 따로 기록한다: 근거 사용자 승인 위험 예산, 수익 게이트 미통과, OOS·SHADOW 생략, 표시 전용, 알림 등급 B 이하. R3의 8개 상품에 상품 승인 게이트(`new_buy_instrument_approved`)가 열리고, #13 등록으로 승인 규칙 게이트도 채워진다. 그래도 S5 규칙의 `quantity_authority`가 "none"이라 매수 제안은 hard gate로 계속 watch_only·B 이하이고 후보를 만들지 않는다(`validate_research_packet.py`). 검증 현금 `cash_policy`, watchlist watch_only, 진입 규칙 등 나머지 매수 게이트는 그대로다(S6 재확인 새 문제 2, 2차 새 문제 1).
- R3 구성
  - 카드 종목 코어 BE·MU·NBIS·DELL·AMD. 편입·비중은 보유 카드(ADD/HOLD/TRIM/EXIT)와 Champion vs Challenger vs Cash.
  - 종목 상한(S6 J4·필수 수정 12): 명목 ≤ 0.4배. 대상은 개별 주식, 단일 종목 레버리지 상품(MVLL), 분류가 없는 상품. 지수 레버리지 ETF(SOXL·TQQQ)는 대상이 아니고 E로 관리한다.
  - DRAM(1배 액티브 메모리 ETF)에도 종목 상한 0.4배를 적용한다(S7 사용자 선택 ①, 10-01). MU 금지 구간의 DRAM 대체 금지도 그대로다.
  - 실적 금지 구간(2세션 전 ~ 발표 뒤 첫 세션) 신규 매수 금지. 실적일 미확인은 금지 구간으로 본다. MU 금지 구간에 DRAM으로 대체하지 않는다.
  - 개별 종목 합계·루트 테제 상한·현금 하한 없음.
  - 보충은 SOXL. TQQQ·DRAM은 허용 목록(카드 판단). SOXX·SMH·USD는 쓰지 않는다. MVLL은 매도 전용.
  - 상품 등록(필수 수정 4, S6 재확인 새 문제 1·2): 권한 원본은 `workspace/policies/instrument_registry.json`이다. `decision_harness.instrument_registry`는 비권한 운영 캐시이고, 원본 해시는 `decision_harness.instrument_registry_authority.required_canonical_sha256`로 고정돼 있다(`validate_registry_consistency.py`). 원본에 MU·DELL·AMD·TQQQ를 더하고 BE·MU·NBIS·DELL·AMD·SOXL·TQQQ·DRAM의 `new_buy_instrument_approved`를 true로 한 뒤, `required_canonical_sha256`을 갱신하고 캐시를 동기화한다. MVLL·NBIL은 false 유지. 현재 원본·캐시 모두 이 값이 false다.
  - 효과: 이 8개 상품에 기존 상품 승인 게이트가 열린다(`validate_research_packet.py`, `validate_decision_record.py`, `run_tactical_opportunity_radar.py`, `build_new_buy_strategy_draft.py`). #13 S5 승인 규칙 등록으로 승인 규칙 게이트도 채워지지만, `quantity_authority` "none" hard gate 때문에 매수 제안은 계속 watch_only·B 이하다. 검증 현금·watchlist watch_only·진입 규칙 등 나머지 매수 게이트는 그대로다.
  - 종목 간 되돌리기(±10%p)는 S4-4 사전 등록 검증 전까지 카드 참고 표시만.
- R4 HWM 검토선
  - 자산 = 대조로 확인된 보유 × 정규장 종가 + 확인된 예수금. HWM 시작 $28,473.94(2026-09-30 종가). S7 적용일에 9/30~적용일 종가 자산 고점으로 다시 확인한다.
  - 판정: 종가 자산 ≤ HWM × 선 배수(반올림 전 값으로 비교).
  - L1 HWM × 0.90($25,626.55): 가벼운 점검 카드, 채우기 권고 계속.
  - L2 HWM × 0.80($22,779.15): 전면 재검토, 끝날 때까지 채우기·신규 매수 권고 멈춤. 이후 × 0.70, × 0.60 …도 같음.
  - 같은 하락 구간 선마다 1회, 새 HWM이면 다시 건다. 검토 결론 "계속"이면 HWM 유지. 자동 매도 없음.
  - 멈춤 해제는 `decision_journal.json`의 "검토 완료 + 사용자 확인"으로만.
- R5 종목 고점 −30%(전향, S6 J10)
  - 고점 = S7 적용일(신규 편입은 첫 대조 확인일) 이후 확인된 정규장 종가 최고치. 소급 고점(보유 시작 뒤)은 검증된 출처가 없어 카드에 참고로만 표시한다.
  - 종가 ≤ 고점 × 0.70이면 다음 정규장 전 그 종목 카드 재작성. 끝날 때까지 그 종목 채우기 권고 멈춤. 같은 하락 구간 1회, 새 고점이면 다시 건다. 자동 매도 없음.
  - S7 적용일에 보유 종목 전체의 기준 카드를 1회 쓴다. 기준 고점이 아직 없는 종목은 채우기 권고를 멈춘다.
  - 현행 `peak_drawdown` 초안(비활성)은 바꾸지 않는다. R5는 새 섹션의 `single_stock_peak_review`에만 둔다.
- R6 입출금
  - 대조 때 사용자 신고로 HWM에 반영한다(입금 +, 출금 −). 신고 금액은 대조에서 확인된 "매매로 설명되지 않는 예수금 변화" 이내여야 한다. 배당·수수료·세금은 입출금이 아니다(HWM 조정 없음).
  - 미신고면 HWM 갱신·선 판정을 보류하고 채우기·신규 매수 권고를 멈춘다(R0).
- R7 현행 정책 정리(전체 경로는 5절)
  - 원가 기준 종목 한도는 판정 규칙에서 내린다. `holding_risk_rules.positions`는 보유 종목 등록부로도 쓰여(`evaluate_alerts.py`, `validate_research_packet.py`, `reconcile_broker_state.py`) 고정 평가기 수정이 전제다(K3).
  - `freeze_new_buy_candidates_on_any_breach`는 지우지 않고 false로 둔다. 키가 없으면 코드 기본값이 true다(`validate_research_packet.py`). L2·R0 멈춤이 대신한다.
  - NBIL de minimis 항목 삭제.
  - `decision_harness.approved_rule_registry`: 은퇴 규칙에 묶인 7개(soxl·mvll·nbis_max_loss_review, mvll_staged_reduction, soxl_staged_timing, nbil_de_minimis_manual_exit, post_reduction_weakness_rearm)를 은퇴 표시하고, S5 줄이기·채우기 권고를 종목 단위 승인 규칙(status "approved", `quantity_authority` "none")으로 등록한다. 검토선·R5는 hold·watch 성격이라 등록하지 않는다. `validate_research_packet.py`는 hold·watch가 아닌 제안에 승인 규칙 참조를 요구한다(Cowork 발견 C1, 5절 #13).
  - SOXL·MVLL 타이밍 축소 슬롯 은퇴(D5). gap·halt 감시만 남기고 SOXL weakness_10ema watch-only도 은퇴한다. 슬롯이 없으면 엔진이 gap·halt 감시도 내지 않아 `timing_engine.py` 수정이 전제다(K3).
  - `dynamic_gross_leverage_cap` → superseded 표시(불변식 `soxl_only_result_can_validate_live_portfolio_cap = false` 유지). 수익 게이트 차단 목록의 "dynamic leverage cap"(신호 티어)과 "peak drawdown exits"는 차단 유지.
  - 유지: `cash_policy`, 실적 금지 구간, 주문 권한 없음.
- R8 가상 운용: K132-G 보고 전용(월 1회 한 줄, 정책 효과 없음, Cold Path라 실패해도 핵심 판단을 막지 않음, 승격 없음). 나머지 기각 후보는 추적하지 않는다.
- R9 교체 매매: 매도 → 체결·주문 가능 현금 확인 → 매수(미체결 매도 대금은 현금이 아니다).
- 감수 위험(부록 C.6, 합성 D, 1.55 열은 미저장 탐색): SOX 32년 최대 낙폭 −98%·최악 1년 −84%, 1994~2010 연 0.2%, 2010~ 최대 낙폭 −64%·최악 1년 −58%. 하루 만에 −21.6%(L2 −20% 초과) 가능. L1 연 약 3회, L2 연 약 1회.
- 검증 상태: 전부 C/D. 포트폴리오 수준 미검증, 1.55는 검증 범위 밖이고 OOS·forward shadow 없음, L2 멈춤·R5·R6 미검증.

## S6 Judge 판정 (2026-10-01)

- 세션: Claude Code worktree `judge-s6`, Opus · xhigh, HEAD `6ff8f25`. 파일 수정 없음. 정책·상태 해시 일치.
- 최종: **PASS_WITH_FIXES**(문서 수정 14건, 새 사용자 결정 없음). FAIL 항목 없음. J2·J5·J12는 PASS(조건·주석), 나머지는 FIX. 사전 점검 P1~P8 모두 CONFIRMED(P5의 V 2.80은 미저장 D라 NOT VERIFIED, N 2.285만으로 1.9 초과 확인).
- J2 요지: 현 상태(N 2.285, E 약 2.8) 대비로는 위험 축소다. 검증 범위 1.32 대비로는 밖이라 미검증 사용자 위험 예산이다. 지금 닫혀 있는 매수 권고 경로를 여는 점은 S7 질문에 적는다.
- J8 고지 순서: D1 결정 전에 C.6 표를 보였는지는 기록(단일 커밋)으로 확인할 수 없다(NOT VERIFIED). D1b는 C.6 뒤에 정했다. 그래서 S7 승인 질문에서 C.6 위험과 "OOS·SHADOW 생략"을 다시 확인받는다.
- J12: L1~L4 산술 일치. C.6의 1.0·1.32 열은 S4-3 커밋 결과와 일치. 1.55 열은 결과 JSON의 REF|fixed1.5와 배수가 달라 비교 불가(미저장 D).
- 필수 수정 14건과 반영 위치(r1)

| # | 내용 | 반영 |
|---|---|---|
| 1 | 수익 게이트 #8 분리: 위험 축소 통제만 면제, 채우기 권고는 별도 기록 | R2 분류, 5절 #8 |
| 2 | "dynamic leverage cap"·"peak drawdown exits" 차단 유지, `peak_drawdown` 재사용 취소 | R5·R7, 4절 #7, 5절 #7 |
| 3 | 경로 `holding_timing_rules.` 접두, slots 배열 표현, SOXL weakness_10ema 처리 명시 | R7, 5절 #4~#8 |
| 4 | #1·#2 실제 효과(등록부 역할, false 명시), 상품 등록 변경 추가 | R3·R7, 5절 #1·#2·#12 |
| 5 | 공통 fail-closed 조항 | R0, 5절 `fail_closed` |
| 6 | 미등록 상품 배수 기본값 삭제 | R1, 5절 `nominal_multipliers` |
| 7 | V 가격 출처, 공통 창, 조기 폐장일 봉 | R1, 5절 `sox_equivalent` |
| 8 | R6 미신고 시 채우기도 멈춤, 신고 한도, 배당·수수료 구분 | R6, 5절 review lines |
| 9 | L2 신규 매수 멈춤, 채우기 예상 E ≤ 1.55, 연산자, policy_version | R2·R4, 5절 |
| 10 | R5 전향 기준 | R5, 5절 `single_stock_peak_review` |
| 11 | 줄이기 순서 | R2, 5절 `reduce_order` |
| 12 | 종목 상한 대상 정의, "S4-3 I1 근거 밖" 한 줄 | R3, 확정안 머리 |
| 13 | 차단 목록 정리(F1.32 삭제, 기각 5개 추가), K132-G 필드, 9절·4절 낡은 문구 | 5절 #8·K132-G, 4·9절 |
| 14 | 감수 위험 −98%·−84%, C.6 1.55 열 출처, C.9 수치 통일, S7 재확인 기록 | 감수 위험, 부록 C.6·C.9, 아래 확인 항목 4 |

- K 등급: 새 섹션 2개 K3 / #1·#2 K3(고정 평가기 포함 스크립트 8개) / #3 K2 / #4·#5 K3(고정 타이밍 엔진 + 상태) / #6 K2(`build_holding_fact_pack.py`가 공식을 읽음) / #7 변경 없음 / #8 K3 / 상품 등록 승인 K3 / R6 대조안 형식 K3 / K132-G 가상 운용 K2(Cold Path) / 문서 정리 K0.
- Cowork 확인(읽기 전용, 10-01): `decision_harness.instrument_registry`는 SOXL·MVLL·NBIL·DRAM·NBIS·BE 6개이고 `new_buy_instrument_approved`가 모두 false다. `shadow_acceptance.py`는 `holding_risk_rules`·`holding_timing_rules`로 의미 해시를 만들고, `run_deployment_provenance.py`는 `alert_policy.json`을 provenance에 넣는다.
- S6 재확인 1차(10-01, 대상 `4df8331`): **FAIL(경미)**. 필수 수정 14건 중 13건 OK, 9번 부족(비중을 늘리는 권고 중 채우기에만 예상 E ≤ 1.55가 걸림, 대역 안 신규 매수·교체는 fail-open). 새 문제 3건: ① 상품 등록 대상이 비권한 캐시였음(권한 원본은 `workspace/policies/instrument_registry.json`) ② "기존 매수 게이트 그대로"와 상품 승인 게이트 개방이 모순 ③ 부록 C 규칙 초안의 우선 규칙 누락. 확인 항목: 5 범위 안, 6 새 결정 필요(두 선택지로 묻기), 7 범위 안.
- r2 반영: 9번 → R2 "비중을 늘리는 모든 권고", 5절 `exposure_increasing_*`. 새 문제 1 → R3, 5절 #12, 4절 #12, 9절 요구 10. 새 문제 2 → R2 분류, R3 효과, 5절 분류 필드. 새 문제 3 → 머리 상태 줄. 확인 항목 6 → R3 DRAM 줄. Cowork 발견 C1(`approved_rule_registry`에 은퇴 규칙 7개가 남고 S5 권고용 승인 규칙이 없음) → R7, 5절 #13, 4절 #13, 9절 요구 11.
- S6 재확인 2차(10-01, 대상 `e5790b3`): **PASS**(fail-open 없음, 재판정 불필요). 조건이던 문구 2건을 반영했다: ① 상품 승인 게이트와 함께 #13 승인 규칙 게이트도 채워지지만 `quantity_authority` "none"이라 매수는 watch_only·B 이하(R2 분류, R3 효과, 항목 5) ② #13·#14가 감소 뒤 EMA 재무장 규칙도 은퇴시킴을 항목 7에 적음. C1 확인: 승인 규칙은 정확히 7개, 등록은 종목 단위·status "approved". S7 Builder 요구 2·11과 계산·테스트 사례에 반영했다.
- S7 승인 때 묻는 항목(1~5와 7은 적용 확인, 6은 선택)
  1. 채우기 권고를 "미검증 사용자 위험 예산의 수익 추구 권고(표시 전용, B 이하)"로 기록한다.
  2. R5 기준을 전향(S7 적용일 이후 고점)으로 한다.
  3. 줄이기 순서: ① 종목 상한 초과 ② 카드 TRIM·EXIT ③ SOXL.
  4. C.6 감수 위험과 OOS·SHADOW 생략을 다시 확인한다.
  5. 상품 신규 매수 승인을 하나씩 확인한다: BE, MU, NBIS, DELL, AMD, SOXL, TQQQ(등록부에 없던 3배 상품), DRAM. MVLL·NBIL은 미승인. 효과: 이 상품들에 상품 승인 게이트가 열리고, S5 승인 규칙 등록(#13)으로 승인 규칙 게이트도 채워진다. 수량 권한이 없어 매수 제안은 계속 watch_only·B 이하이고, 나머지 매수 게이트는 그대로다. 권한 원본 파일 변경이다.
  6. DRAM 종목 상한: ① 0.4배 적용(추천) ② 미적용. 어느 쪽이든 MU 금지 구간 DRAM 대체 금지는 남는다.
  7. SOXL weakness_10ema watch-only와, 사용자 요청으로 만든 감소 뒤 EMA 재무장 규칙(`post_reduction_weakness_rearm`, `holding_timing_rules.weakness_rearm`, 면제 목록 "confirmed-fill EMA rearm")을 은퇴한다. D5 "gap·halt만 유지"의 적용이고, 슬롯 은퇴 뒤에는 대상이 없다. 수익 게이트의 안전 면제 목록에서 항목 2개를 빼는 변경이다(S6 2차 새 문제 2).

## S7 사용자 승인 (2026-10-01, Cowork 대화, 한 번에 하나씩)

- 성격: "S6 Judge 판정" 절의 항목 1~7에 대한 사용자 명시 승인. 정책·상태 파일은 아직 바꾸지 않았다. 주문·수량 권한은 계속 없다.

| # | 질문 요지 | 사용자 답(원문) |
|---|---|---|
| 1 | 채우기 권고를 "미검증 사용자 위험 예산의 수익 추구 권고(표시 전용, B 이하, 수량 권한 없음)"로 기록·적용 | "그대로 적용 (추천)" |
| 2 | R5 고점을 S7 적용일 이후 정규장 종가 최고치로(전향) | "적용일부터 (추천)" |
| 3 | 줄이기 순서 ① 종목 상한 초과(MVLL 포함) ② 카드 TRIM·EXIT ③ SOXL | "이 순서로 적용 (추천)" |
| 4 | 1.55의 감수 위험(SOX 32년 −98%·최악 1년 −84%, 1994~2010 연 0.2%, 2010~ −64%·−58%, 하루 −21.6%, 최근 5년 1.32보다 수익 낮고 낙폭 8%p 깊음)과 OOS·shadow 생략을 알고 유지 | "1.55 유지" |
| 5 | 신규 매수 상품 승인 BE·MU·NBIS·DELL·AMD·SOXL·TQQQ·DRAM(MVLL·NBIL 미승인), 효과 고지(매수 제안은 watch_only·B 이하) | "8개 모두 승인 (추천)" |
| 6 | DRAM 종목 상한 0.4배 | "① 적용 (추천)" |
| 7 | SOXL weakness_10ema 감시와 감소 뒤 EMA 재무장 규칙 은퇴 | "둘 다 은퇴 (추천)" |

- 이 승인으로 S7 Builder가 5절 diff r2(새 섹션 2개, 기존 키 #1~#8·#12~#14)와 `workspace/policies/instrument_registry.json` 변경을 worktree에서 구현할 수 있다. 병합 전 별도 Judge가 필요하다.

## 0. 결론 (초안 시점, 확정안이 우선)

> 10-01 사용자 결정(부록 C.6): **위험 예산 목표 E = max(N, V) ≤ 약 1.55**(검증 범위 1.32 밖, 사용자 승인 위험 예산). 적용 시점(D1b): **S7 적용 때 바로**(사용자 결정 10-01). F1.32 forward shadow(D2)는 이 결정으로 대체됐다. 구성(D1c): 카드 종목 코어(BE·MU·NBIS·DELL·AMD) + SOXL 보충, 종목 간 되돌리기는 S4-4 검증 뒤(부록 C.8).
>
> 10-01 사용자 조건 추가(부록 C): 지수 ETF는 SOXL·TQQQ·DRAM만 쓴다(SOXX 제외). 그래서 아래 B1(SOXX ETF 코어)은 "카드 종목 코어"로 바꿔 검토 중이다. D1은 부록 C 결론에 따라 다시 묻는다.

1. **제안을 두 묶음으로 나눈다.**
   - **A 안전 묶음(S6·S7 통과 시 적용):** 노출 목표 1.0배(명목과 SOX 환산 중 큰 값), 개별 종목 명목 0.4배, HWM 검토선(−10% 점검, −20% 전면 재검토 + 되사기 멈춤, 이후 −10%p마다), 자동 매도 없음, 원가 기준 종목 한도와 낡은 레버리지 공식 정리. 지금 2.29배를 1.0배로 낮추는 방향이라 위험을 줄이는 통제로 분류한다.
   - **B 구현·수익 묶음:** ① ETF 코어(1.0배까지 SOXX, 초과분만 SOXL)는 S4-3 I1 "ETF 코어 권장"이라 A와 함께 적용을 제안한다. ② 고정 1.32배(F1.32)는 S4-3 판정이 "S5 제안 후보(forward shadow 필요)"라 바로 적용하지 않는다. 60세션 forward shadow 뒤 승격을 심사한다.
2. **F1.32 통과는 경계선이다.** SPX 성장 기준은 배당 보정으로만 통과했다(가격 지수 +0.499%p, 기준 +0.5%p). 꼬리는 −14.0%p로 완화 한도 −15%p에 가깝다. 1.0배보다 급락마다 9~11%p 더 깊다. 그래서 승격은 forward shadow와 사용자 위험 재확인 뒤로 둔다.
3. **조건부 4개(T1·T2·K132-G·T2-132b)와 X1은 사전 등록대로 기각을 유지한다.** 사후 완화하지 않는다.
4. **1.9배 상한(S1 결정 2)은 폐지를 제안한다.** 조정 폭 상단(목표 + 0.3)이 사실상의 상한이 된다(D3).
5. **포트폴리오 수준(개별 종목 혼합)에서는 검증되지 않았다.** 현행 불변식 `soxl_only_result_can_validate_live_portfolio_cap = false`는 유지한다. 새 규칙의 권한 근거는 "검증된 수익 개선"이 아니라 "사용자가 승인한 위험 예산"으로 적는다.
6. **사용자 결정은 7개다(10절).** 첫 질문은 D1(ETF 코어 채택)이다. S2(MVLL 매도 대금을 현금으로 둘지 SOXX로 옮길지)와 바로 연결된다.

## 1. 근거와 등급

| 단계 | 결과 | 등급 | 이 제안에서 쓰는 곳 |
|---|---|---|---|
| S1 결정 1·2 | 손실 예산 −10%·−20%, 레버리지 상한 1.9배 | 사용자 결정 | 2.4·4절 |
| S4 | 급락 탈출·재진입 신호 게이트 통과 없음(NO_CHANGE) | C/D | 기본 노출을 신호로 팔지 않는 근거 |
| S4-2 | CPV 기각. BF10(고정 1.0배) 기준선 1년 최악 −48%(실제)·−66%(합성) | C/D | 6.3절 |
| S5 준비 결정 | A-1b·A-2·3·4·5·6·6b | 사용자 결정 | 2절 |
| S4-3 | F1.32 후보(forward shadow 필요), ETF 코어 권장, 조건부 4개·X1 기각 | C/D(합성, SPX 배당 보정) | 3절 |
| MVLL 카드 | HWM $28,473.94(9/30 종가, 사용자 승인), 종가 = 16:00 표기 30분봉 종가 | 키움 읽기 전용 조회, 공식 종가 대조 확인 필요 | 2.4·6절 |

- 공개 자료 확인(10-01, 상품 공식 페이지)
  - SOXX와 SOXL은 같은 NYSE Semiconductor Index를 추종한다.
  - 보수: SOXX 0.33%, SOXL 순 0.75%(총 0.91%), SMH 0.35%(MVIS US Listed Semiconductor 25 추종).
  - 백테스트는 ^SOX(PHLX Semiconductor)를 썼다. 지수가 달라 생기는 차이는 확인 필요.

## 2. A 안전 묶음 — 규칙 초안 (초안 이력, 확정안 R1~R6이 우선)

### 2.1 노출 측정

- 명목 N = Σ(배수 × 평가액 비중). SOXL 3, MVLL 2, 1배 주식·1배 ETF 1, 현금 0.
  - 보유 종목 전체에 적용한다. 현행 공식은 청산된 NBIL을 담고 보유 중인 NBIS를 빼고 있다.
- SOX 환산 V = 포트폴리오 252세션 일간 수익률 표준편차 ÷ 같은 기간 SOXX 일간 수익률 표준편차.
  - 포트폴리오 수익률 = 오늘 비중 × 종목별 과거 일간 수익률(비중 고정 가정).
  - 기준 상품: SOXX(SOXL과 같은 지수). 수익률은 분할 보정 일봉(현행 `technical_price_basis_required`).
  - 이력이 252세션 미만이면 가용 세션(최소 60)으로 계산하고 "짧은 이력"으로 표시한다. 60세션 미만이면 그 종목은 신규 편입 불가(fail-closed).
- 노출 E = max(N, V). 목표 X* = 1.55(사용자 결정 10-01, 부록 C.6. 이전 초안 1.0).
- 성질(S5 준비 A-1b): 시장 전체 변동성이 오르면 분자·분모가 같이 올라 E가 줄지 않는다(고정 1.0배 유지). SOX보다 크게 움직이는 개별 종목은 더 무겁게 센다. SOXL만 보유하면 BF10과 거의 같다.

### 2.2 조정 권고 (표시만)

- 줄이기: E ≥ X* + 0.3. 기본 순서 SOXL → SOXX. 카드에서 TRIM이 난 종목으로 대체할 수 있다.
- 되사기: E ≤ X* − 0.3.
  - D1에서 ETF 코어를 채택하면 1배로 채울 비중이 있는 동안 SOXX, 모자라면 SOXL.
  - 채택하지 않으면 결정 6b대로 SOXL.
  - 어느 쪽이든 카드 ADD 종목으로 대체할 수 있다(종목당 0.4배, 실적 금지 구간 준수).
- 0.3 = SOXL 비중 10%p(S4-2 BF10의 조정 폭).
- 권고는 종가 확정 뒤 다음 정규장 전에 한 번, 비중으로만 낸다. 수량·주문은 없다.
- 교체(매도 후 매수)는 두 단계다: 매도 → 체결과 주문 가능 현금 확인 → 매수. 미체결 매도 대금은 현금이 아니다(현행 `cash_policy`).

### 2.3 개별 종목

- 한 종목의 명목 노출(배수 × 비중) ≤ 0.4배. MVLL은 비중 20% 이하, 1배 주식은 40% 이하.
- 넘은 상태면 그 종목 신규 매수를 바로 막는다. 가격이 올라 넘은 경우는 다음 카드에서 TRIM 검토를 권고한다.
- 실적 금지 구간 재사용: `earnings_blackout_single_stocks`(실적 2세션 전 ~ 발표 뒤 첫 세션, 신규 매수만).
- 개별 종목 합계 상한, 루트 테제 상한, 현금 하한은 두지 않는다(결정 5·6).
  - 감수 위험: 테제가 틀리면 종목 분산 효과가 없다(Ticker 분산 ≠ Root-Thesis 분산). 최대 선 검토의 테제 점검이 대응한다.

### 2.4 HWM 검토선

- 자산 = 대조로 확인된 보유 수량 × 정규장 종가 + 확인된 예수금.
  - 종가는 16:00 표기 30분봉 종가다. 키움 일봉 종가는 시간외 값이 섞인다(MVLL 카드 정정). 공식 종가와의 대조는 확인 필요.
- HWM은 종가 자산이 신고가일 때만 올린다. 시작값 $28,473.94(2026-09-30 종가, 사용자 승인). 이전 값 $28,028.57은 장중 평가였다.
- 입출금(D7 추천안)
  - 입금은 HWM에 더하고 출금은 뺀다.
  - 매매로 설명되지 않는 예수금 변화가 있는 대조안에는 입출금 신고 칸을 둔다.
  - 신고가 없으면 HWM 갱신과 선 판정을 보류하고 신규 매수·되사기 권고를 멈춘다(fail-closed).
- 선과 행동

| 선 | 기준 | 행동 | 되사기·신규 매수 권고 |
|---|---|---|---|
| L1 | HWM × 0.90 | 가벼운 점검 카드 1장: 테제·집중도·노출/현금·대안 각 한 줄, 결론 유지/조정 | 계속 |
| L2 | HWM × 0.80 | 전면 재검토: 보유 종목별 ADD/HOLD/TRIM/EXIT 카드 + Champion vs Challenger vs Cash·SPY | 검토 완료 기록 전까지 멈춤 |
| L3, L4 … | HWM × 0.70, × 0.60 … | L2와 같음 | 멈춤 |

- 판정은 종가 확정 뒤, 다음 정규장 전에 한다. 같은 하락 구간에서 선마다 한 번만 걸린다. 새 HWM이 나오면 다시 걸린다.
- 검토 결론이 "계속"이면 HWM은 그대로 두고 다음 검토 지점은 그 아래 선이다.
- 자동 매도는 없다. 선에서 매도 권고를 자동으로 만들지도 않는다(카드 판단으로만).
- 기록: `stock-strategy-system/decision_journal.json`. 아직 없는 파일이라 S7에서 최소 형식으로 만든다. 멈춤 해제는 이 기록의 "검토 완료 + 사용자 확인"으로만 한다.
- 한계: 종가 판정이라 하루 급락과 개장 갭은 막지 못한다(6.2절).

### 2.5 권한·현금 (현행 유지)

- 주문·수량 권한 없음, 체결 추론 금지, 보유·평단 변경은 대조 apply로만.
- `cash_policy` 그대로: 검증된 주문 가능 현금만 현금으로 본다. 미체결 매도 대금·SGOV·증거금은 현금이 아니다.
- `new_buy_activation.cash_and_quantity_gate`의 "user_approved_risk_budget" 조건은 S7 승인으로 채워진다. "positive verified cash" 조건은 그대로 남는다.

## 3. B 구현·수익 묶음 (초안 이력, SOXX ETF 코어와 F1.32는 D1·D1c로 대체)

### 3.1 B1 ETF 코어 (A와 함께 적용 제안, D1)

- 규칙: 노출 예산 중 개별 종목이 쓰고 남은 몫은 SOXX(1배)로 먼저 채운다. 1배로 채울 비중이 모자랄 때만 SOXL을 쓴다. E가 목표에 닿고 남는 비중은 현금이다.
  - 개별 종목이 없으면 1.0배 = SOXX 100%(매매 없음), 1.32배 = SOXX 84% + SOXL 16%.
- 근거(S4-3 I1, C/D)
  - SOX·NDX·SPX 모두에서 ETF 코어가 "3배 + 현금"보다 연 +1.8~+3.1%p 높았고, 최대 낙폭은 같거나 얕았다(+0.8~+7.1%p).
  - 실제 상품 2010~2026: 1.0배를 SOXX로 들면 연 25.4%, SOXL + 현금으로 들면 21.2%.
  - 이유는 산수다. SOXL은 빌린 2배분에 단기 금리를 내고 보수도 높다(순 0.75% 대 0.33%). 키움 달러 예수금은 이자가 없어 "SOXL 1/3 + 현금 2/3"의 현금 2/3는 아무것도 벌지 않는다.
- 의미 변화
  - 현금이 거의 0이 된다. 1.0배는 SOXX가 스스로 유지하므로 급락 때 현금으로 되살 일이 없다. 1.0배를 급락 내내 유지하는 것 자체가 급락 매수 효과다.
  - 1.32배일 때는 SOXL 16% 몫이 흔들리고, 그 되돌림(SOXX → SOXL 교체)이 급락 매수 역할을 한다.
  - 카드 ADD 종목을 살 돈은 SOXX 매도에서 나온다(2.2절 두 단계).
  - 결정 6b(되사기 기본 SOXL)는 "SOXX 먼저, 모자라면 SOXL"로 바뀐다.
- S2 연결(참고, D등급, 확인 필요): ETF 코어를 채택하면 S2 최종 구성의 "현금 약 60%"는 대부분 SOXX로 바뀐다. 다만 MVLL을 남기면 V가 먼저 차서 현금이 남는다.

| 남기는 MVLL | SOXX | 현금 | 명목 |
|---|---|---|---|
| 20% | 약 22% | 약 47% | 약 0.73배 |
| 10% | 약 56% | 약 23% | 약 0.87배 |
| 0% | 약 84% | 약 5% | 약 0.95배 |

  - 가정: NBIS 10.8% 유지, S5 준비 결정의 1년 변동성 배율·베타(Yahoo, D), MVLL = MRVL 2배, 종목 고유 위험끼리 상관 0. Cowork 간이 계산이다.
  - S7 전이라도 MVLL 매도 대금을 SOXX로 옮길지는 사용자 수동 판단이다(시스템 권한 없음).
- 확인 필요: 키움 수수료율, 리밸런싱으로 실현되는 해외주식 양도세, SOXX와 ^SOX의 추종 차이.

### 3.2 B2 고정 1.32배 (F1.32) — forward shadow 뒤 승격 심사 (D2)

> 10-01 사용자 결정 D1·D1b로 대체: 위험 예산 1.55를 S7 적용 때 바로 쓴다. 이 절의 F1.32 shadow는 하지 않는다(기록용으로 남김).

- S4-3 판정: G1·G3·G4·G6·G7 통과(G2·G5 해당 없음) → "S5 제안 후보(forward shadow 필요)".
- 약점(Builder 보고 4절, Cowork 독립 재계산 일치)
  - SPX G1: 가격 지수로는 +0.499%p로 기준(+0.5%p)에 못 미친다. 배당 보정 +1.55%p로 통과했다. Shiller 배당 자료가 2023-06까지라 그 뒤는 마지막 값을 이어 썼다.
  - G3: SPX 전체 최대 낙폭 차 −14.0%p(한도 −15%p). 한도는 사용자가 결과 전에 −10%p에서 완화했다.
  - 이득이 특정 시기에 몰린다: SOX 32년 +0.6%p 중 대부분이 2026년(2026 제외 +0.2%p). NDX 2000-04 −7.4%p/년, 1995-99 +17.8%p/년.
  - 1.32배는 SOX 자료에서 고른 값이다(설계 오염). NDX·SPX의 최적 고정 배수는 2.00·1.68이다(최적점 주변은 평평).
- shadow 설계(제안)
  - 시작은 S7 적용일. 실제 계좌와 분리된 shadow 원장을 쓴다(SHADOW ≠ ACTUAL).
  - 같은 시작 자산, 실제 SOXX·SOXL 종가, 종가 t 결정 → 종가 t+1 체결, 상품별 10bp, 상품별 비중 10%p 조정 폭(S4-3 ETF 코어 규칙 그대로).
  - 기간: 최소 60 완료 세션(약 3개월).
- 승격 심사 조건: 수익은 조건이 아니다. 60세션 수익 차는 잡음이라 판정력이 없다.
  1. 세션 누락·데이터 실패 0. 실패한 날은 표시하고 사유를 기록한다.
  2. SOXL 추종: 일간 (SOXL − 3 × SOXX) 차의 평균·표준편차가 과거 값(S1: 평균 −0.06%p, 표준편차 0.36%p, 2024-06~2026-08, D)에서 크게 벗어나지 않는다. 허용 폭은 확인 필요(Judge 질문 5).
  3. 조정 권고가 났다면 2.2절 두 단계로 실제 실행할 수 있었는지 확인한다. 권고가 없었으면 해당 없음.
  4. 사용자가 6절 감수 위험 표를 다시 확인한다.
- 승격 절차(추천): Cowork가 조건 충족 보고를 만든다 → 짧은 Judge 1회(X* 값 하나를 바꾸는 K3) → 사용자 승인.
- 정직한 한계: 이 shadow는 1.32배의 수익 우위를 증명하지 못한다. 확인하는 것은 실제 상품 추종과 운영 가능성뿐이다. 장기 우위의 근거는 여전히 S4-3(C/D)이다.

### 3.3 기각 유지 (D6)

- T1·T2·K132-G·T2-132b는 G4(N0 = NDX 1985~94)에서 실패했다. K132-G는 −0.59%p로 기준 −0.5%p에 근소하게 못 미쳤다.
  - 원인(Cowork 확인, D): 게이트가 1987 폭락과 1990 하락 뒤의 V자 반등을 1.0배로 보냈다.
- X1(급락 추가 매수)은 G1·G2·G4·G5·G6·G7에서 실패했다.
- 사후 완화하지 않는다. 다시 보려면 새 사전 등록과 쓰지 않은 데이터가 필요하다. 남은 것은 사실상 앞으로 쌓일 자료뿐이다.
- (10-01 사용자 결정 D6) K132-G만 보고 전용 가상 운용으로 지켜본다(부록 C.12). 나머지는 추적하지 않는다.

## 4. 현행 정책과의 대응

| # | 현행 위치 | 지금 | 제안 | 이유 |
|---|---|---|---|---|
| 1 | `holding_risk_rules.positions`(SOXL −20%·MVLL −60%·NBIS −10%, 원가 기준) | 합계 $11,490(41%), `action_on_breach=null` | 판정 규칙에서 내리고 카드에 원가 대비 손익만 참고 표시(D4) | 새 예산의 약 2배, 원가 기준 비대칭, 행동 미승인. HWM 선이 대체 |
| 2 | `holding_risk_rules.freeze_new_buy_candidates_on_any_breach` | 종목 한도 위반 시 신규 매수 멈춤 | false로 둠(키 삭제 시 코드 기본값 true), L2·R0 멈춤이 대체 | 같은 취지를 포트폴리오 선으로(S6 필수 수정 4) |
| 3 | `holding_risk_rules.de_minimis_manual_exit_positions.NBIL` | 청산 예외 항목 | 삭제 | 청산 완료(사용자 확인 9/30) |
| 4 | `holding_timing_rules.positions.SOXL` 축소 슬롯(EMA, anchor 99주) | 실제 보유 75주와 다름 | 슬롯 은퇴, gap/halt 표시는 유지(D5) | 기본 노출을 신호로 파는 구조(S4에서 성과 나쁨). 노출 조정은 2.2절이 맡음 |
| 5 | `holding_timing_rules.positions.MVLL` 슬롯(anchor 396주) | 축소 슬롯 | 은퇴, MVLL은 카드·S2가 판단(D5) | 매수 불가·매도 전용 종목. 0.4배 상한과 카드로 충분 |
| 6 | `risk_overlay_rules.dynamic_gross_leverage_cap` | 비활성, NBIL 포함·NBIS 누락 공식, SOXL 티어 0.75~3.0 | `superseded_by_portfolio_exposure_policy`, 연구 기록으로 보존 | 새 노출 규칙이 대체. `soxl_only_result_can_validate_live_portfolio_cap=false`는 유지 |
| 7 | `risk_overlay_rules.peak_drawdown` | 비활성, 종목별 고점 대비 초안(전향, 소급 없음, 5년 OOS 게이트) | 변경 없음. R5는 새 섹션 `single_stock_peak_review` | 재사용 취소(S6 필수 수정 2) |
| 8 | `risk_overlay_rules.walk_forward_activation_gate` | 로컬 5년 이력 요구로 실패 고정 | 위험 축소 통제는 면제 목록에, 채우기 권고는 별도 "미검증 수익 추구" 목록에, 기각 5개는 차단 목록에(5절 #8) | S6 J1·J7, 필수 수정 1·13 |
| 9 | S1 결정 2 "1.9배"(정책 파일 밖) | 결정 기록만 | 유지: E ≥ 1.9 절대 상한(D3) | 바꾸려면 별도 사용자 승인 + Judge |
| 10 | `new_buy_activation.earnings_blackout_single_stocks` | 실적 금지 구간 | 그대로 재사용 | 결정 5 |
| 11 | `cash_policy` | 검증 현금만 | 그대로 | — |
| 12 | `workspace/policies/instrument_registry.json`(권한 원본) + 캐시 `decision_harness.instrument_registry` | MU·DELL·AMD·TQQQ 없음, 신규 매수 승인 모두 false | 원본에 4개 추가, 8개 승인, 원본 해시 갱신, 캐시 동기화(5절 #12) | S6 필수 수정 4, 재확인 새 문제 1 |
| 13 | `decision_harness.approved_rule_registry` | 원가 한도·타이밍 슬롯 승인 규칙 7개 | 7개 은퇴, S5 줄이기·채우기 승인 규칙을 종목 단위로 등록(5절 #13) | Cowork 발견 C1, S6 2차 |
| 14 | `holding_timing_rules.weakness_rearm` | 감소 체결 뒤 EMA 재무장 | 은퇴(5절 #14) | 슬롯 은퇴로 대상 없음(S6 2차) |

- 표의 `risk_overlay_rules.*`·`new_buy_activation.*`는 실제로 `holding_timing_rules.` 아래 경로다(S6 P1). 표와 5절 r2가 다르면 5절 r2가 우선한다.

- 코드 영향(읽기 전용 확인, 10-01): `holding_risk_rules`는 스크립트 8개가 읽는다(`evaluate_alerts.py`, `audit_hard_risk_policy.py`, `portfolio_policy_gates.py`, `portfolio_decision_dashboard.py`, `build_holding_fact_pack.py`, `reconcile_broker_state.py`, `shadow_acceptance.py`, `validate_research_packet.py`).
  - `evaluate_alerts.py`는 `deployment_gate`가 해시로 고정한 평가기다. 1·2번 변경은 고정 스크립트 수정을 부를 수 있어 K3로 다룬다.
  - (S6 정정) `alert_policy.json` 원본 해시를 직접 고정한 곳은 없지만, `run_deployment_provenance.py`가 이 파일을 배포 provenance에 넣고 `shadow_acceptance.py`가 `holding_risk_rules`·`holding_timing_rules`로 의미 해시를 만든다. `timing_engine.py`·`SKILL.md` 등도 `deployment_gate` 고정 대상이다(9절 요구 1·2).

## 5. diff 초안 r2 (`alert_policy.json`과 `workspace/policies/instrument_registry.json`, 적용 안 함)

- `alert_policy.json` 최상위에 새 섹션 두 개를 더한다. 값은 사용자 결정 D1~D7, S6 필수 수정 14건, 재확인 수정 반영본(r2)이다.

```json
"portfolio_exposure_policy": {
  "policy_version": "2026-10-01-s5-final-proposal-r2",
  "status": "proposed_not_applied",
  "authority_basis": "user_approved_risk_budget_not_validated_portfolio_return",
  "validation_status": "beyond_validated_1.32_oos_and_forward_shadow_skipped",
  "order_authority": false,
  "quantity_authority": "none",
  "execution_quantity": null,
  "target_exposure": 1.55,
  "target_effective_from": "s7_activation",
  "thresholds": {
    "reduce_when_exposure_gte": 1.85,
    "add_when_exposure_lte": 1.25,
    "exposure_increasing_projected_exposure_lte": 1.55,
    "hard_ceiling_when_exposure_gte": 1.9
  },
  "exposure_increasing_recommendations": ["add", "new_buy_within_band", "swap_buy_leg"],
  "exposure_increasing_requires_single_stock_cap": true,
  "exposure_increasing_breach": "omit_recommendation",
  "hard_ceiling_breach": "block_all_new_buys_and_flag_urgent_reduce",
  "hard_ceiling_change_requires": "separate_user_approval_and_judge",
  "exposure_measure": "max(nominal, sox_equivalent_volatility_ratio)",
  "nominal_multipliers": {"SOXL": 3, "TQQQ": 3, "MVLL": 2, "BE": 1, "MU": 1, "NBIS": 1, "DELL": 1, "AMD": 1, "DRAM": 1, "cash": 0},
  "unregistered_instrument": "block_new_buy_recommendation_and_exposure_unavailable_if_held",
  "sox_equivalent": {
    "benchmark": "SOXX",
    "benchmark_role": "measurement_only_not_held",
    "window_sessions": 252,
    "minimum_sessions": 60,
    "below_minimum_sessions": "block_new_entry",
    "common_session_window": true,
    "weights": "current_weights_held_fixed",
    "return_basis": "split_adjusted_regular_session_close",
    "price_source": "kiwoom_regular_session_close",
    "latest_close_bar": "final_regular_session_30m_bar",
    "early_close_bar": "final_30m_bar_before_early_close",
    "reference_only_sources": ["yahoo"],
    "average_provider_prices": false,
    "regular_session_history_unavailable": "exposure_unavailable"
  },
  "fail_closed": {
    "triggers": [
      "exposure_or_equity_or_v_unavailable",
      "unregistered_instrument_held",
      "hwm_line_or_pause_state_missing_or_corrupt",
      "decision_journal_missing_or_corrupt",
      "broker_snapshot_older_than_broker_snapshot_max_age_calendar_days",
      "required_price_missing",
      "undeclared_cash_flow"
    ],
    "pause": ["add_recommendations", "new_buy_recommendations"],
    "continue_with_unverified_label": ["reduce_recommendations", "warnings"]
  },
  "composition": "card_stock_core_with_soxl_supplement",
  "composition_evidence": "outside_s4_3_i1_scope_c6_is_index_1x_plus_3x_model",
  "card_stock_core": ["BE", "MU", "NBIS", "DELL", "AMD"],
  "allowed_index_etfs": ["SOXL", "TQQQ", "DRAM"],
  "excluded_instruments": ["SOXX", "SMH", "USD"],
  "sell_only_holdings": ["MVLL"],
  "add_default": "card_add_stock_else_SOXL",
  "add_when_default_paused": "omit_recommendation_no_substitute",
  "reduce_order": ["single_stock_cap_excess_including_sell_only", "card_trim_or_exit", "SOXL"],
  "reduce_when_soxl_absent": "warn_excess_unresolved_no_substitute",
  "above_band_action": "reduce_recommendation_and_pause_new_buy_recommendations",
  "add_recommendation_classification": {
    "nature": "return_seeking",
    "authority_basis": "user_approved_risk_budget",
    "return_gate": "not_passed",
    "oos_and_shadow": "skipped",
    "output": "display_only",
    "max_alert_grade": "B",
    "instrument_approval_gate": "opened_for_r3_instruments_via_canonical_registry",
    "other_buy_gates": "unchanged_verified_cash_watchlist_watch_only_entry_rules"
  },
  "cross_stock_rebalance": {"band_abs": 0.10, "status": "display_only_until_s4_4_validation"},
  "single_stock_nominal_cap": 0.4,
  "single_stock_cap_applies_to": ["stock", "single_stock_leveraged_etf", "unclassified", "DRAM"],
  "dram_cap": "apply_user_choice_2026-10-01",
  "single_stock_cap_exempt": ["SOXL", "TQQQ"],
  "single_stock_cap_breach": "block_new_buy_and_first_in_reduce_order",
  "single_stock_peak_review": {
    "applies_to": "every_held_instrument",
    "drawdown_from_peak": 0.30,
    "trigger": "regular_session_close_lte_peak_times_0.70",
    "peak_basis": "verified_regular_session_close_high_since_s7_activation_or_first_reconciled_date_rearm_on_new_high",
    "retroactive_peak": "display_only",
    "activation_baseline_cards": "one_card_per_held_instrument_on_s7_activation",
    "no_baseline_peak": "pause_add_recommendations_for_instrument",
    "action": "rewrite_holding_card_before_next_regular_session",
    "pause_add_recommendations_until_card_done": true,
    "automatic_sell": false,
    "one_trigger_per_drawdown": true
  },
  "earnings_blackout_ref": "holding_timing_rules.new_buy_activation.earnings_blackout_single_stocks",
  "earnings_date_unverified": "treat_as_blackout",
  "blackout_substitution_prohibited": {"MU": ["DRAM"]},
  "swap_execution": "sell_then_verify_fill_and_orderable_cash_then_buy",
  "recommendation_output": "target_weights_only",
  "shadow_candidates": {
    "K132-G": {
      "status": "rejected_s4_3_g4_report_only",
      "mode": "forward_shadow_report_only",
      "instruments": ["SOXX", "SOXL"],
      "rule": "1.32 when gate on, 1.0 when shadow equity < 0.80 x 252-session shadow high; gate back on at >= 0.90",
      "comparators": ["SOXX 100%", "F1.32 fixed"],
      "ledger_separate_from_actual": true,
      "policy_effect": "none",
      "report_cadence": "monthly_one_line",
      "failure_blocks_core_decision": false,
      "promotion": "none_without_new_preregistration"
    }
  }
},
"portfolio_review_lines": {
  "policy_version": "2026-10-01-s5-final-proposal-r2",
  "status": "proposed_not_applied",
  "equity_basis": "verified_holdings_times_regular_session_close_plus_verified_cash",
  "close_basis": "kiwoom_final_regular_session_30m_bar_close",
  "hwm_initial_usd": 28473.94,
  "hwm_initial_as_of": "2026-09-30",
  "hwm_recheck_at_activation": "closing_equity_high_2026-09-30_through_activation",
  "hwm_update": "new_closing_equity_high_only",
  "line_breach": "closing_equity_lte_hwm_times_fraction_unrounded",
  "cash_flow_adjustment": "user_declared_at_reconciliation_within_unexplained_cash_change",
  "cash_flow_excludes": ["dividends", "fees", "taxes"],
  "undeclared_cash_flow_action": "hold_hwm_and_line_evaluation_and_pause_add_and_new_buy_recommendations",
  "lines": [
    {"id": "L1", "fraction_of_hwm": 0.90, "action": "light_check_card", "pause_add_recommendations": false, "pause_new_buy_recommendations": false},
    {"id": "L2", "fraction_of_hwm": 0.80, "action": "full_review_cards_vs_cash_and_spy", "pause_add_recommendations": true, "pause_new_buy_recommendations": true}
  ],
  "further_lines_step": 0.10,
  "further_lines_action": "same_as_L2",
  "one_trigger_per_line_per_drawdown": true,
  "rearm_on_new_hwm": true,
  "review_continue_keeps_hwm": true,
  "automatic_sell": false,
  "pause_release": "decision_journal_review_completed_and_user_confirmed",
  "evaluation_time": "after_completed_close_before_next_regular_session",
  "record": "stock-strategy-system/decision_journal.json"
}
```

- 기존 키 변경 r2(4절 번호, 경로는 해당 파일 안의 전체 경로)

```text
#1 holding_risk_rules.positions.{SOXL,MVLL,NBIS}
     원가 손실 한도를 판정에서 내린다. 보유 종목 등록부 역할(evaluate_alerts.py, validate_research_packet.py,
     reconcile_broker_state.py)은 유지하거나 새 등록부로 옮긴다. 고정 평가기 evaluate_alerts.py 수정 전제(K3)
#2 holding_risk_rules.freeze_new_buy_candidates_on_any_breach
     true -> false (키 삭제 금지: validate_research_packet.py 기본값 true). L2·R0 멈춤이 대신함
#3 holding_risk_rules.de_minimis_manual_exit_positions.NBIL                         removed
#4 holding_timing_rules.positions.SOXL
     slots 배열의 축소 슬롯 전부 은퇴. watch_only_triggers ["weakness_10ema","gap_risk","halt_risk"] -> ["gap_risk","halt_risk"]
     슬롯 없이 gap·halt 감시를 내도록 timing_engine.py 수정 전제(K3), timing_plan 상태 이관은 승인된 쓰기 경로로만
#5 holding_timing_rules.positions.MVLL
     slots 배열의 축소 슬롯 전부 은퇴, gap·halt 감시만(#4와 같은 전제)
#6 holding_timing_rules.risk_overlay_rules.dynamic_gross_leverage_cap.status       -> "superseded_by_portfolio_exposure_policy"
     (gross_effective_leverage_formula는 build_holding_fact_pack.py가 읽음, K2)
#7 holding_timing_rules.risk_overlay_rules.peak_drawdown                             변경 없음(비활성 초안 유지)
#8 holding_timing_rules.risk_overlay_rules.walk_forward_activation_gate
     .safety_only_controls_exempt_from_return_gate
          - "SOXL weakness_10ema watch-only"
          - "confirmed-fill EMA rearm" (#14와 함께 은퇴)
          + "S5 exposure measurement, reduce recommendations, 1.85 band and 1.9 hard ceiling"
          + "S5 portfolio review lines and recommendation pauses"
          + "S5 single-stock nominal cap and peak review (R5)"
          + "S5 cash-flow declaration fail-closed (R6)"
     .return_seeking_rules_blocked
          유지 "post-reduction reentry", "peak drawdown exits", "time stops", "dynamic leverage cap", "additional indicator votes"
          + "T1", "T2", "K132-G", "T2-132b", "X1" (S4-3 rejected; K132-G report-only shadow, no promotion)
     (new) .user_approved_unvalidated_return_seeking
          ["S5 add recommendations up to 1.55 risk budget (display only, alert grade <= B)"]
#12 workspace/policies/instrument_registry.json (권한 원본, approved policy 변경, K3)
     instruments + MU, DELL, AMD, TQQQ (identity·instrument_type은 S7 Builder가 원본 형식대로 채움)
     new_buy_instrument_approved true: BE, MU, NBIS, DELL, AMD, SOXL, TQQQ, DRAM / false 유지: MVLL, NBIL, 그 밖의 상품
   + alert_policy.json decision_harness.instrument_registry_authority.required_canonical_sha256  -> 새 원본 해시
   + alert_policy.json decision_harness.instrument_registry (비권한 캐시)                          -> 원본과 동기화
     (캐시만 바꾸면 POLICY_REGISTRY_MISMATCH로 멈춤. validate_registry_consistency.py로 확인)
#13 alert_policy.json decision_harness.approved_rule_registry (K3)
     은퇴 표시: soxl_max_loss_review, mvll_max_loss_review, nbis_max_loss_review, mvll_staged_reduction,
               soxl_staged_timing, nbil_de_minimis_manual_exit, post_reduction_weakness_rearm
     등록: S5 줄이기 권고, S5 채우기 권고(미검증 수익 추구 표시)
           종목 단위(rule.symbol 일치), status "approved", quantity_authority "none"
           검토선·R5는 hold·watch라 등록하지 않음. allowed_actions 이름은 validate_research_packet.py 어휘에 맞춘다(S7 Builder)
#14 holding_timing_rules.weakness_rearm                                           status -> "retired_with_reduction_slots"
     (슬롯 은퇴로 대상 없음. timing_engine.py 고정 해시 범위라 #4·#5와 함께 K3)
```

## 6. 금액표와 감수 위험 (6.1 검토선은 유효, 6.2·6.3은 1.0/1.32 기준 이력 — 1.55는 부록 C.6)

### 6.1 검토선 (HWM $28,473.94)

| 선 | HWM 배수 | 자산 하한 | HWM 대비 손실 | 행동 |
|---|---|---|---|---|
| L1 | 0.90 | $25,626.55 | −$2,847.39 | 점검 카드 1장, 되사기 계속 |
| L2 | 0.80 | $22,779.15 | −$5,694.79 | 전면 재검토, 되사기·신규 매수 멈춤 |
| L3 | 0.70 | $19,931.76 | −$8,542.18 | L2와 같음 |
| L4 | 0.60 | $17,084.36 | −$11,389.58 | L2와 같음 |

- 9/30 종가 구성(참고): SOXL $11,205.00(39.4%), MVLL $14,180.72(49.8%), NBIS $3,082.30(10.8%), 예수금 $5.92. 명목 2.285배, SOX 환산 1년 약 2.80(D).
- 목표 예(HWM 기준, 수량 아님)
  - 1.0배 ETF 코어: SOXX $28,474.
  - 1.32배: SOXX $23,918 + SOXL $4,556.
  - 개별 종목 0.4배: MVLL $5,695(20%) 또는 1배 주식 $11,390(40%).

### 6.2 하루 스트레스 (2020-03-16, SOXX −15.2%·SOXL −38.6%, Yahoo, D)

| 구성 | E | 그날 손실 |
|---|---|---|
| SOXX 100% | 1.00 | −15.2% |
| SOXX 84% + SOXL 16% | 1.32 | −18.9% |
| SOXX 74% + SOXL 26% (1.32의 조정 폭 상단) | 1.52 | −21.3% |

- 종가 판정이라 이런 하루는 검토선이 막지 못한다. 1.32배부터는 하루 만에 L2(−20%)에 가까워진다.

### 6.3 기간 최악 (SOX, ETF 코어, 현금 0%, 10bp, S4-3 2.3·2.5절, D)

| 항목 | 1.0배(B0) | 1.32배(F1.32) |
|---|---|---|
| 32년 연수익 | 15.1% | 16.2% |
| 1994~2010 연수익 | 6.9% | 4.7% |
| 2010~2026 연수익 | 23.7% | 28.4% |
| 32년 최대 낙폭 | −88% | −96% |
| 2010~ 최대 낙폭 | −47% | −56% |
| 2010~ 1년 창 최악 | −39% | −49% |
| 급락 고점→저점 | 지수와 같음 | 매번 9~11%p 더 깊음 |

- 이전 감수 위험(S5 준비 A-2: BF10 = SOXL + 현금, S4-2 창 시작 대비 최저 자산): 1년 최악 −48%(실제)·−66%(합성), 3년 합성 −85%. 계산 정의가 달라 위 표와 직접 비교하지 않는다(확인 필요).
- 2000~02형 긴 하락에서는 1.0배도 −84~−88%다. 검토선은 매도를 강제하지 않는다. 이 꼬리를 막는 것은 L2 이하 검토에서 내리는 판단뿐이다.

## 7. 미검증·한계

1. 포트폴리오 수준 미검증: S4-2·S4-3은 지수 하나로 만든 모형이다. 개별 종목 혼합과 V(변동성 비율) 환산은 검증되지 않았다.
2. L2 멈춤 규칙 미검증: S4-3은 −20% 도달 횟수만 셌다.
3. HWM 선 빈도는 간이 재현뿐이다(SOXL + 현금 형태, 2010~2026 L1 연 1.3회·L2 연 0.5회, D). ETF 코어에서는 계산하지 않았다.
4. V의 기준 SOXX(NYSE 지수)와 백테스트 ^SOX(PHLX 지수)가 다르다.
5. 16:00 표기 30분봉 종가와 공식 종가가 센트 단위로 다를 수 있다.
6. 입출금 보정 절차가 정해지지 않았다(D7).
7. 수수료·세금은 모형에 없다.
8. 하루 급락·개장 갭(6.2절).
9. F1.32는 경계선 통과다(3.2절).
10. 결정 기록 원장(`decision_journal.json`)이 아직 없다. 멈춤 해제가 이 원장에 달려 있다.

## 8. S6 Judge 질문

> S6 Judge는 `s6-judge-prompt-2026-10-01.md`의 J1~J12로 판정했다(아래 질문 4·5는 대상이 없어 J4·J5로 교체). 결과는 "S6 Judge 판정" 절.

1. A 묶음을 "위험을 줄이는 통제"로 분류해 수익 게이트(walk-forward)에서 면제하는 것이 타당한가? 되사기 권고(수익 추구 성격)를 같은 묶음에 둬도 되는가?
2. `soxl_only_result_can_validate_live_portfolio_cap = false`를 유지한 채 "사용자 승인 위험 예산"을 권한 근거로 쓰는 것이 Authority Chain에 맞는가?
3. 원가 기준 종목 한도·타이밍 슬롯 은퇴가 hard-risk 경로와 고정 해시(`deployment_gate`, acceptance manifest)에 주는 영향과 필요한 변경 등급은?
4. ETF 코어(B1)를 S4-3 I1만으로 실제 포트폴리오에 적용해도 되는가? 개별 종목 혼합은 I1 범위 밖이다.
5. F1.32 forward shadow 설계가 "forward shadow 필요"를 충족하는가? 승격 조건에 수익을 넣지 않은 것과 추종 허용 폭은 적절한가?
6. fail-closed 경로가 빠짐없는가: 데이터 누락, 원장 없음, 입출금 미신고, V 계산 불가, 대조 지연(`broker_snapshot_max_age_calendar_days` 4일).
7. 기각 후보를 사후 완화하지 않은 처리와 1.9배 상한 유지는 타당한가?
8. 검증 범위(1.32) 밖의 위험 예산 1.55를 forward shadow 없이 S7에서 바로 적용하는 것을 "사용자 승인 위험 예산"으로 기록하는 처리가 Authority Chain과 맞는가? 감수 위험(부록 C.6) 고지가 충분한가?

## 9. S7 구현 범위 (승인 뒤, S6 Judge 요구 반영)

- K3. 새 worktree에서 Builder, 끝나면 별도 Judge. Builder 지시문은 S6 재확인 PASS와 S7 승인 뒤 따로 쓴다.
- 정책: 5절 r2의 새 섹션 2개와 기존 키 #1~#8·#12~#14.
- 계산: N·V·E, R0 fail-closed, 줄이기 순서, 비중을 늘리는 권고(채우기·신규 매수·교체 매수 쪽)의 예상 E, HWM·선 판정, R5 전향 고점, 멈춤 상태, 권고 표시(비중).
- 원장: `decision_journal.json` 최소 형식(line_id, hwm, breach_date, review_status, conclusion, user_confirmed_at).
- 가상 운용: K132-G 보고 전용 원장(실제 계좌와 다른 파일, Cold Path, K2).
- 표시: 카드·현황판에 E, 다음 선까지 거리, 멈춤 상태 한 줄.
- S6 Judge 요구 사항
  1. 고정 파일 범위부터 확정한다. `evaluate_alerts.py`·`timing_engine.py`·`SKILL.md`·`ko-KR.json`을 고치면 `deployment_gate` 해시와 설치 스킬을 동기화한다. `run_manual_portfolio_analysis.py`와 그 테스트는 건드리지 않는다(acceptance 고정 16개, 건드리면 별도 K3).
  2. `alert_policy.json` 변경이 배포 provenance(`run_deployment_provenance.py`), `shadow_acceptance.py` 의미 해시, `workspace/policies/shadow_acceptance_policy.json`의 `required_baseline_tickers`(NBIS·MVLL·SOXL)에 주는 영향을 확인한다(S6 미확인). 상품 등록부 원본 변경도 `shadow_acceptance.py`의 의미 해시(등록부 경로를 읽음)에 영향을 준다(S6 2차).
  3. `timing_engine.py`는 열린 슬롯이 없으면 gap·halt watch도 내지 않는다. 슬롯 은퇴 뒤 watch를 유지하려면 엔진을 고쳐야 한다. anchor 등식과 timing_plan 상태 이관은 승인된 쓰기 경로로만 한다.
  4. HWM·멈춤·선 발동 상태의 저장 위치와 쓰기 경로를 정한다. 현재 대화의 사용자 확인에 묶고, 예약 작업·Judge·Claude Code는 쓰지 않는다.
  5. R6 신고는 대조안 해시에 넣는다(신고 뒤 새 코드). apply 경로라 K3. 미결제 매도 대금은 현금이 아니되 자산 계산에서 거짓 선 발동이 나지 않게 한다.
  6. 시작 HWM 재확인(9/30~적용일 종가 자산 고점), 선 비교는 반올림 전 값, 30분봉 종가와 공식 종가 대조 허용 오차, L1·L2·1.9·R5의 알림 등급 매핑.
  7. 카드 ADD·TRIM 대체는 검증을 통과한 유효 기간 안의 카드만 쓴다. 실적일 미확인은 금지 구간으로 본다. MU 금지 구간에 DRAM으로 대체하지 않는다.
  8. 테스트: 영향 파일 11개(test_timing_engine, test_reconcile_broker_state, test_portfolio_decision_dashboard, test_build_holding_fact_pack, test_holding_card, test_v2_4_dual_phase, test_v2_5_leveraged_confirmation, test_v2_6_12_holding_valuation_shadow, test_v2_6_3_free_web_new_buy, test_v2_6_7_session_aware_kiwoom_priority, test_v2_6_integration)과 test_evaluate_timing_integration. 필수 수정 5~11마다 새 fail-closed 테스트.
  9. (Cowork 추가) V 과거 이력의 정규장 종가 확보 방법(키움 30분봉 이력 길이 등)을 먼저 확인한다.
  10. (재확인 반영) 상품 등록은 권한 원본 `workspace/policies/instrument_registry.json`을 고치고 `required_canonical_sha256` 갱신과 캐시 동기화를 한 번에 한다. `validate_registry_consistency.py`가 통과해야 한다.
  11. (C1, S6 2차) `approved_rule_registry`: 7개 은퇴, S5 줄이기·채우기 규칙은 종목 단위·status "approved"·`quantity_authority` "none"으로 등록한다. `validate_research_packet.py`를 고치면 K2 이상이다.
- 테스트 사례: 선 경계(정확히 닿음, 같은 구간 1회, 새 HWM 재무장, "계속" 뒤 다음 선), R0 트리거 각각, V 이력 부족, 0.4배 초과와 줄이기 순서, 신규 매수·교체 매수 쪽 예상 E 초과 시 권고 생략, SOXL 없음·R5 멈춤 때 권고 생략, 실적 금지 구간·실적일 미확인, 교체 두 단계, R5 기준 고점 없음, 입출금 신고 한도·배당 구분.

## 10. 사용자 결정 (한 번에 하나씩)

| 번호 | 질문 | 추천 | 대안 |
|---|---|---|---|
| D1 | 위험 예산 | (결정됨 10-01) E = max(N, V) ≤ 약 1.55 | — |
| D1b | 1.55 적용 시점 | (결정됨 10-01) S7 적용 때 바로 | — |
| D1c | 구성 | (결정됨 10-01) 카드 종목 코어(BE·MU·NBIS·DELL·AMD) + SOXL 보충. 종목 간 되돌리기는 S4-4 검증 뒤 정식 권고 | — |
| D2 | F1.32 처리 | D1·D1b에 흡수(목표가 사용자 위험 예산 1.55로 정해짐) | — |
| D3 | 1.9배 결정 | (결정됨 10-01) E 절대 상한 1.9 유지 | — |
| D4 | 원가 기준 종목 한도 | (결정됨 10-01) 폐지, 대신 종목 고점 대비 −30%면 그 종목 카드 재작성(검토만) | — |
| D5 | SOXL·MVLL 타이밍 슬롯 | (결정됨 10-01) 은퇴, gap/halt 표시만 유지 | — |
| D6 | 기각 후보 | (결정됨 10-01) 기각 유지, K132-G만 보고 전용 가상 운용 | — |
| D7 | 입출금 보정 | (결정됨 10-01) 대조 때 사용자 신고, 미신고 변화는 HWM 갱신·선 판정 보류 | — |

- 이미 정한 것(다시 묻지 않음): 고정 1.0배 목표(A-2), 측정 방식(A-1b), 선별 행동(결정 3), HWM(결정 4, 시작값 $28,473.94), 개별 종목 0.4배(결정 5), 카드 자유 배분(결정 6), 자동 매도 없음.

## 11. 다음 단계

1. 사용자: Windows 터미널에서 이 수정본(r2) 커밋(Cowork가 명령 안내).
2. S6 재확인 2차: 같은 Judge 세션에 `s6-judge-prompt-2026-10-01.md` 7절 지시. 재확인 1차의 수정 4건과 C1만 본다.
3. (완료 10-01) S7 사용자 승인 1~7. S7 Builder 지시문 작성 완료(10-01, `s7-builder-prompt-2026-10-01.md`) → Builder worktree `s7-policy`(K3) → 별도 Judge → 사용자 커밋·병합.
4. 병행 가능(Cold Path): S4-4 사전 등록 "종목 코어 + 종목 간 되돌리기"(Builder, 2000~2010 바구니 + forward shadow). S7을 막지 않는다.
5. S7 전까지 실제 매매(MVLL 축소 등)는 사용자 수동 판단이다. 1.55 기준 참고는 부록 C.6 "S2 영향".

## 12. 진행 기록

- 2026-10-01 초안 작성(Cowork, Opus). 정책·상태 파일 원본 해시 변경 없음 확인(`alert_policy.json` `184008bd…`, `portfolio_state.json` `28fd77c5…`). 공개 자료로 SOXX·SOXL 추종지수와 보수를 확인했다.
- 2026-10-01 D1 재검토(사용자 대안 2개, 부록 B). 탐색 D등급, 스크립트 미저장. 결론: 구조는 "현금을 놀리지 않는 것"이 핵심이고, 2배 상품은 구조상 이득이 없다.
- 2026-10-01 D1 재검토 2(사용자 조건 4개, 부록 C). 32종목 횡단면·무작위 바구니 탐색, D등급, 스크립트 미저장.
- 2026-10-01 사용자 결정: 위험 예산 목표 약 1.55(부록 C.6). 다음 질문 D1b(적용 시점).
- 2026-10-01 사용자 결정 D1b: S7 적용 때 바로 1.55(원문 "S7 적용 때 바로"). D2(F1.32 shadow) 대체. 다음 질문 D1c(구성).
- 2026-10-01 사용자 결정 D1c: 카드 종목 코어 + SOXL 보충, 되돌리기는 검증 뒤, 코어에 AMD 추가(부록 C.8).
- 2026-10-01 사용자 결정 D3: 1.9 절대 상한 유지(부록 C.9). D3~D7은 하나씩 결정(사용자 원문 "하나씩 본다").
- 2026-10-01 사용자 결정 D4: 원가 기준 폐지, 종목 고점 대비 −30% 카드 재작성(부록 C.10).
- 2026-10-01 사용자 결정 D5: SOXL·MVLL 타이밍 슬롯 은퇴(부록 C.11).
- 2026-10-01 사용자 결정 D6: 기각 유지, K132-G만 보고 전용 가상 운용(부록 C.12).
- 2026-10-01 사용자 결정 D7: 대조 때 사용자 신고(부록 C.13). D1~D7 완료, "S5 확정안" 절 작성, 5절 diff를 결정 반영본으로 교체.
- 2026-10-01 S6 Judge 지시문 작성: `s6-judge-prompt-2026-10-01.md`. 8절 질문 4·5는 대상이 없어져 J4(카드 종목 코어)·J5(K132-G)로 바꿨다. Cowork 사전 점검 P1~P8(경로, 수익 게이트 분류, R5 기준점, 낡은 초안 부분, S7 전환, 미등록 상품 배수, V 가격 출처, 고정 해시)을 Judge가 직접 확인한다. 문서 정리는 Judge 판정 뒤 한 번에 한다.
- 2026-10-01 S6 Judge 판정 PASS_WITH_FIXES(HEAD `6ff8f25`, 문서 수정 14건, 새 사용자 결정 없음). Cowork가 근거 일부를 읽기 전용으로 다시 확인하고(상품 등록부, 등록부 역할, freeze 기본값, 슬롯 없는 엔진 동작, 의미 해시) r1로 반영했다: "S5 확정안 r1" 절, "S6 Judge 판정" 절, 4·5·8·9·11절, 부록 C.6·C.9. 정책·상태 파일 원본 해시 변경 없음. 다음은 S6 재확인.
- 2026-10-01 S6 재확인 1차 FAIL(경미, 대상 `4df8331`): 수정 4건(필수 수정 9, 새 문제 1~3)과 확인 항목 6을 선택 질문으로. Cowork가 근거를 읽기 전용으로 확인하고(권한 원본 등록부와 해시 고정, 상품 승인 게이트 사용처) r2로 반영했다. 추가로 `approved_rule_registry` 정리(C1)를 넣었다. 정책·상태 파일 무변경.
- 2026-10-01 S6 재확인 2차 PASS(대상 `e5790b3`, 재판정 불필요). 조건 문구 2건(승인 규칙 게이트 효과, 재무장 규칙 은퇴)과 Builder 요구 3건을 반영했다. 다음은 S7 승인 질문(1~7, 한 번에 하나).
- 2026-10-01 S7 사용자 승인 1~7 완료("S7 사용자 승인" 절, 답 원문 기록). DRAM 상한은 ① 적용. 정책·상태 파일 무변경. 다음은 S7 Builder 지시문.
- 2026-10-01 S7 Builder 지시문 작성(`s7-builder-prompt-2026-10-01.md`, Cowork). 정지점 2개(1단계 조사, 2단계 계획·결정 요청 P1~P8). 키움 분봉 API `usa06011`은 명세만 확인했고 30분봉 이력 길이는 확인 필요(라이브 조회 전). 정책·상태 파일 무변경. 다음은 사용자 커밋 → Builder 실행.
- 2026-10-02 S7 1차 구현(나눠서 적용, 더하기만, 옛 통제 유지) 완료: Builder 커밋 `770c6fc`(worktree-s7-policy), S7-1 Judge PASS_WITH_FIXES → 수정 → 재확인 PASS. 사용자 결정 P0~P8-6·P3(15:30 봉 종가)와 Cowork 실측은 `s7-builder-prompt-2026-10-01.md` 5~9절. 2차(옛 통제 은퇴·#12·고정 파일)는 새 통제가 실제 자료로 판정되는 것을 확인한 뒤. 선행: 세션 달력 9월 이후 활성화(별도 K3) → **2026-10-02 해소**: 2026 전체 달력은 이미 통합 Production 권한에서 ACTIVE였다. S7 코드가 옛 파일을 읽던 것을 통합 권한 연결로 고쳤다(`s7-calendar-binding-builder-prompt-2026-10-02.md`, 병합 `cd39212`).

## 부록 B. D1 재검토 — 사용자 대안 2개 (2026-10-01, 탐색 D등급)

- 사용자 대안(원문 요지)
  1. SOXL + 개별 종목(BE·NBIS·DELL·SNDK·MU 등) + 현금 3종으로 1.32배 운영.
  2. SOXX 2배 레버리지 상품을 포트폴리오 종목으로 고려.
- 결론
  - 대안 1의 "개별 종목 + 1.32배"는 ETF 코어와 함께 쓸 수 있다. 손해가 나는 부분은 **놀리는 현금**이다. 같은 위험(SOX 환산 1.32)에서 대안 1 원안은 연 약 1.5%p를 더 내고, 조정 매매가 약 7배 많다.
  - 대안 2: SOXX 2배 상품은 찾지 못했다. 가장 가까운 USD(ProShares Ultra Semiconductors)는 다른 지수(Dow Jones U.S. Semiconductors, NVDA 약 20%)를 따른다. 같은 지수로 놓고 보면 2배와 3배는 구조상 차이가 거의 없다(연 ±0.4%p, 꼬리는 2배가 조금 깊음).
  - 최적안(추천): **SOXX 코어 + 카드 종목(종목당 ≤ 0.4배) + 모자란 노출만 SOXL.** 현금은 V가 먼저 차서 남는 몫만. USD는 구조가 아니라 "NVDA 비중이 큰 반도체" 테제로, 카드에서 따로 판단한다.
  - 목표 1.32배는 여전히 D2(forward shadow 뒤 승격) 경로다. 위 구조 결론은 1.0배·1.32배 모두에 적용된다.

### B.1 같은 위험에서 구성 비교 (5종목 각 8% = 40%, 목표 E = 1.32)

| 구성 | SOXX | SOXL | USD | 현금 | 차입 노출 | 연 비용(보수 + 차입비 4.28%) |
|---|---|---|---|---|---|---|
| 대안 1 원안: SOXL + 종목 + 현금 | 0% | 25.1% | 0% | 34.9% | 0.50 | 약 2.33%(약 $663) |
| ETF 코어 + 종목 + SOXL 보충 | 52.8% | 7.2% | 0% | 0% | 0.14 | 약 0.84%(약 $240) |
| ETF 코어 + 종목 + USD 보충 | 36.0% | 0% | 24.0% | 0% | 0.24 | 약 1.37%(약 $391) |

- 방법: Yahoo 수정종가 최근 252세션(2025-09-30~2026-09-30), E = max(명목, SOX 환산 V), 비중 고정. 금리 = FRED DGS3MO 2026-09-28 4.28%. 3배·2배 상품의 내재 차입비를 (배수 − 1) × 단기 금리로 근사(확인 필요). 금액은 HWM $28,473.94 기준.
- 5종목만 40%면 V 0.65(명목 0.40). SOXX와의 상관이 0.4~0.8이라 따로 셀 때보다 덜 잡힌다.
- 목표 1.0배일 때(ETF 코어): SOXX 40.2%, 현금 19.8%(V가 먼저 참).

### B.2 실제 상품 2010-03-11~2026-09-30 (1.32배, 현금 0%, 10bp, 조정 폭 5·10·15%p 평균)

| 구성 | 연수익 | 최대 낙폭 | 최악 1년 | 조정 횟수(폭 10%p) |
|---|---|---|---|---|
| SOXX 84 + SOXL 16 | 30.0% | −56.8% | −49.5% | 9 |
| SOXL 44 + 현금 56 | 28.0% | −58.3% | −51.5% | 64 |
| SOXX 68 + USD 32 | 31.7% | −59.1% | −51.2% | 7 |
| USD 66 + 현금 34 | 30.4% | −61.3% | −54.1% | 19 |
| 참고: SOXX 100(1.0배) | 25.5% | −45.8% | −37.8% | 0 |

- USD의 우위는 지수 구성(NVDA 비중)에서 왔다. 일간 (USD − 2 × SOXX) 차의 표준편차는 최근 2년 2.32%p다(SOXL − 3 × SOXX는 0.36%p).

### B.3 구조만 비교 (합성, 같은 지수, 1.32배, ETF 코어 1배 + 3배 대비 연수익 차 %p, 폭 3개 평균)

| 구성 | SOX 1994~ | NDX 1985~ | SPX 1954~ |
|---|---|---|---|
| 1배 + 2배(현금 0) | +0.42 | −0.25 | −0.12 |
| 3배 + 현금 | −1.92 | −2.69 | −2.71 |
| 2배 + 현금 | −1.17 | −1.65 | −1.84 |

- 최대 낙폭 차: 1배 + 2배 −0.7·−1.0·−1.4%p, 3배 + 현금 −1.1·−2.0·−6.9%p.
- 엔진: 부록 A 산식(합성 2배 = 2r − 0.0095/252 − 금리/252), 고정 목표 비중, 비중 이탈이 폭 이상이면 같은 종가에 조정(부록 A의 t+1 체결과 다름, 비교 대상 모두 같은 조건).

### B.4 종목 위험 (최근 252세션, Yahoo, D)

| 종목 | 연 변동성 | SOXX 대비 | SOXX 상관 | 2년 최악 하루 |
|---|---|---|---|---|
| BE | 114% | 2.47 | 0.60 | −24.8% |
| NBIS | 109% | 2.35 | 0.54 | −37.4% |
| DELL | 76% | 1.63 | 0.41 | −19.0% |
| SNDK | 115% | 2.49 | 0.69 | −21.3% |
| MU | 81% | 1.76 | 0.82 | −16.2% |
| SOXX | 46% | 1.00 | 1.00 | −10.4% |

- 개별 종목이 SOXX보다 나을지는 이 시스템에서 검증되지 않았다(카드 판단 영역). 이 종목들의 최근 상승은 사후 선택이라 근거로 쓰지 않는다.
- 확인 필요: 키움에서 미국 주식 매도 대금을 같은 날 재매수에 쓸 수 있는지(교체 두 단계의 지연), 해외주식 양도세(조정 횟수가 많을수록 불리), 2배 반도체 신상품(TSXU·XSEM 등)의 규모·추종 방식.

## 부록 C. D1 재검토 2 — 사용자 조건 반영 (2026-10-01, 탐색 D등급)

- 사용자 조건(원문 요지)
  1. 지수 ETF는 SOXL·TQQQ·DRAM만 고려(SOXX 제외).
  2. 개인적으로 관찰하는 개별 종목은 BE·MU·NBIS·DELL.
  3. 개별 종목 비중을 늘리고 스윙 매매로 이익을 극대화하는 방안 검토.
  4. 최근 5년에 더 큰 비중. 변동성과 휩쏘가 잦아지는 경향 반영.
- 결론
  1. **종목 비중 확대는 그 자체로 레버리지를 올리는 것과 같다.** 4종목 25%씩(명목 1.0배)의 SOX 환산 V는 1.46~1.55(최근 6개월~2년)로 SOXL 44%(1.32배, V 1.30)보다 크다.
  2. **최근 5년에 통한 스윙은 "종목 사이 비중 되돌리기"뿐이다.** 오른 종목을 덜고 내린 종목을 채워 목표 비중으로 돌린다. 무작위 4종목 바구니 1,500개에서 연 +2.4~+2.7%p, 71~73%가 이득이었다. 이전 5년은 +0.0~+0.5%p(50~59%)라 국면에 따라 달라진다.
  3. **종목별 타이밍 스윙은 두 기간 모두 손해였다.** 최근 5년 중앙값: 50일선 이탈 매도 연 −18%p, 200일선 −15%p, −15% 손절 −18%p, 과열 덜기·눌림 더하기 −1~−3%p.
  4. **이 바구니에 SOXL·TQQQ를 더하는 이득은 작다.** 같은 위험(V 1.32)으로 맞추면 SOXL 20%는 연 +1.6%p에 낙폭 약 −10%p 더 깊음, TQQQ 20%는 −2.8%p.
  5. **DRAM은 1배 액티브 메모리 ETF다**(보수 0.65%, 2026-04-02 상장, 124세션). MU와 상관 0.94라 MU 대체이거나 삼성전자·SK하이닉스 간접 보유 수단이다. 검증할 이력이 없다.

### C.1 국면 (최근 5년 2021-10~2026-09 대 이전 5년 2016-10~2021-09, Yahoo, D)

| 상품 | 연 변동성 | 하루 ±10% 일수/년 | 1일 자기상관 | 10일 분산비 | 밤사이 갭 비중 |
|---|---|---|---|---|---|
| SOXX | 30% → 39% | 1.0 → 0.8 | −0.22 → −0.07 | 0.68 → 0.79 | 39% → 39% |
| SOXL | 90% → 115% | 17 → 35 | −0.19 → −0.06 | 0.72 → 0.81 | 40% → 39% |
| TQQQ | 65% → 68% | 7.8 → 7.0 | −0.20 → −0.03 | 0.72 → 0.84 | 43% → 35% |
| MU | 46% → 57% | 2.0 → 5.0 | −0.09 → −0.01 | 0.87 → 0.96 | 41% → 44% |
| DELL | 35% → 54% | 1.6 → 3.4 | −0.01 → +0.03 | 1.07 → 0.99 | 49% → 45% |
| BE | 105% → 90% | 22 → 14 | −0.01 → +0.03 | 1.09 → 1.07 | 21% → 38% |
| NBIS(2024-10~) | 114% | 30 | −0.04 | 0.77 | 36% |

- 변동성과 큰 등락일은 늘었다. 하루 단위 되돌림(휩쏘)은 2020년이 든 이전 5년이 더 강했다. 개별 종목에는 뚜렷한 하루 되돌림이 없다.

### C.2 종목별 타이밍 스윙 (32종목 횡단면, 20bp, 종가 t 결정 → t+1 체결, 현금 0%)

| 규칙 | 비교 기준 | 이전 5년 중앙값(이득 비율) | 최근 5년 중앙값(이득 비율) |
|---|---|---|---|
| 50일선 위에서만 보유 | 계속 보유 | −19.9%p(0%) | −18.1%p(3%) |
| 200일선 위에서만 보유 | 계속 보유 | −11.9%p(7%) | −14.7%p(12%) |
| 20일 고점 −15% 손절, 20일선 회복 재진입 | 계속 보유 | −3.2%p(21%) | −18.2%p(3%) |
| 기본 75% ± 25% 추세 기울이기(50일선) | 75% 고정 | −1.9%p(36%) | −1.0%p(38%) |
| 기본 75% ± 25% 역추세(과열 덜기·눌림 더하기, z ±1.5) | 75% 고정 | −0.8%p(32%) | −1.1%p(31%) |
| 위와 같음, 200일선 위에서만 더하기 | 75% 고정 | −0.7%p(36%) | −2.7%p(25%) |

- 종목: NVDA AMD AVGO MRVL MU INTC QCOM TXN ADI NXPI ON MCHP AMAT LRCX KLAC TER MPWR SMCI ANET WDC STX DELL HPE VRT BE TSM ASML COHR CIEN LITE ORCL PLTR.
- 역추세 기준 z ±1.0·±2.0 이웃도 모두 중앙값 음수.

### C.3 종목 사이 비중 되돌리기 (무작위 4종목 바구니 1,500개, 25%씩, 20bp, 현금 0%)

| 방식 | 이전 5년: 보유 대비 연 차(이득 비율) | 최근 5년: 보유 대비 연 차(이득 비율) | 최근 5년 바구니당 매매 |
|---|---|---|---|
| ±5%p 벗어나면 | +0.50%p(59%) | +2.37%p(71%) | 27회 |
| ±10%p 벗어나면 | +0.04%p(50%) | +2.70%p(73%) | 8회 |
| 상대 ±25% 벗어나면 | +0.45%p(57%) | +2.60%p(71%) | 18회 |

- 최대 낙폭은 같거나 조금 얕았다(중앙값 +0.1~+1.1%p).
- 사용자 바구니(BE·MU·DELL ± SOXL/TQQQ, NBIS 포함 2년)도 같은 방향이었지만, 사후에 고른 종목이라 수치는 근거로 쓰지 않는다.
- 이 방식은 같은 종가에 조정한다고 가정했다(C.2와 다름). 세금(해외주식 양도세)은 넣지 않았다.

### C.4 위험 예산 (SOX 환산 V, 명목 N)

| 구성 | N | V(최근 1년) | V(최근 2년) |
|---|---|---|---|
| BE·MU·DELL·NBIS 25%씩 | 1.00 | 1.54 | 1.55 |
| 위 4종목 20%씩 + SOXL 10% + TQQQ 10% | 1.40 | 1.57 | 1.59 |
| 위 4종목 15%씩 + SOXL 10% + 현금 30% | 0.90 | 1.17 | 1.17 |
| SOXL 44% + 현금 | 1.32 | 1.30 | 1.30 |
| TQQQ 33% + 현금 | 1.00 | 0.43 | 0.51 |

- 4종목 균등이면: 목표 1.0 → 종목 약 65% + 현금 35%, 목표 1.32 → 약 86% + 14%, 100% 보유에는 목표 약 1.55가 필요하다.
- HWM 선 도달(2021-10~2026-09, 같은 하락 구간 1회): BE·MU·DELL 1/3씩 100%는 −10% 14회, −20% 5회, −30% 4회(최대 낙폭 −41%). SOXL 44%는 10·5·3회(−58%).
- 2년 최악 하루: NBIS −37.4%, BE −24.8%, SNDK −21.3%, DELL −19.0%, MU −16.2%. 25% 비중이면 NBIS 하나로 하루 약 −9%(L1 근처).

### C.5 제안 구성 (초안, D1 확정 전)

- 코어: 카드 종목(BE·MU·NBIS·DELL, DRAM은 MU 대체 후보). 종목당 명목 ≤ 0.4배(결정 5).
- 위험 예산: E = max(N, V) ≤ X*(A-1b 유지). 종목 비중은 이 예산이 정한다.
- 스윙: 종목 사이 밴드 되돌리기(목표 비중 ±10%p). 덜기 권고는 바로 낸다. 채우기 권고는 그 종목 카드가 EXIT·TRIM이 아니고 실적 금지 구간 밖일 때만 낸다(실적 갭은 종목 사건일 수 있음, 결정 6b 취지).
- 레버리지 ETF: 종목을 살 수 없을 때(실적 금지 구간, 카드 미작성) 노출을 채우는 기본 대상은 SOXL. TQQQ는 테제 분산용 소량(선택).
- 종목별 타이밍 매매는 카드 재량으로만 하고 기록·채점한다(decision_journal). 기계 규칙으로 두지 않는다.
- 감수 위험: 루트 테제가 하나(AI 설비 투자)라 종목 분산 효과가 작다. 최근 5년은 AI 호황 한 국면이다. 2000~02형 하락에서는 이 구성의 낙폭이 반도체지수(−84%)보다 클 수 있다(확인 필요).
- 다음 검증 제안: S4-4 사전 등록 "종목 코어 + 밴드 되돌리기" 대 보유. 이번 탐색에 쓰지 않은 구간(2000~2010 반도체·기술주 바구니)과 forward shadow로 판정한다.

### C.6 사용자 결정 — 위험 예산 목표 약 1.55 (2026-10-01)

- 사용자 원문: "목표를 약 1.55로 상향"
- 규칙: E = max(명목 N, SOX 환산 V) ≤ 1.55, 조정 폭 ±0.3(권고 범위 1.25~1.85). 측정 방식(A-1b)과 종목당 0.4배(결정 5)는 그대로.
- 의미: 4종목 균등 100% 보유를 허용하는 수준이다(V 약 1.54~1.55).
- 검증 상태: **검증 범위 밖.** S4-3에서 "S5 제안 후보"는 고정 1.32배뿐이었고, 1.5배는 보고 전용이었다. 근거는 사용자 승인 위험 예산(최근 5년 가중)이며 수익 개선 검증이 아니다. S6 Judge 질문에 추가한다.
- 감수 위험 (합성, 1배 + 3배, 현금 0%, 10bp, 폭 10%p, D): 연수익 / 최대 낙폭 / 최악 1년

| 지수·구간 | 1.0 | 1.32 | 1.55 |
|---|---|---|---|
| SOX 32년 | 15.1% / −88% / −64% | 16.2% / −96% / −76% | 15.5% / −98% / −84% |
| SOX 1994~2010 | 6.9% / −88% / −64% | 4.7% / −96% / −76% | 0.2% / −98% / −84% |
| SOX 2010~ | 23.7% / −47% / −39% | 28.4% / −56% / −49% | 32.3% / −64% / −58% |
| SOX 최근 5년(2021-10~) | 30.9% / −47% / −39% | 39.2% / −56% / −49% | 38.3% / −64% / −58% |
| NDX 최근 5년 | 15.3% / −36% / −35% | 16.4% / −47% / −46% | 18.4% / −53% / −53% |
| SPX 최근 5년 | 12.0% / −25% / −21% | 13.2% / −34% / −29% | 15.3% / −37% / −33% |

- 1.55 열 출처: Cowork 탐색(스크립트 미저장, D). S4-3 커밋 결과의 REF|fixed1.5(SOX 32년 연 15.7%, 최대 낙폭 −98.0%)와는 배수·정의가 달라 직접 비교하지 않는다(S6 J12).
- 최근 5년 반도체지수에서도 1.55는 1.32보다 수익이 높지 않았고(38.3% 대 39.2%) 낙폭은 8%p 깊었다. 이득은 2010~ 전체(+3.9%p)와 NDX·SPX에서 보였다.
- 하루 스트레스: 2020-03-16형(SOXX −15.2%, SOXL −38.6%)이면 1.55(SOXX 72.5% + SOXL 27.5% 환산)는 −21.6%. 4종목 균등 바구니의 최근 2년 최악 하루는 −20.7%(2025-01-27). 하루 만에 L2(−20%)를 넘을 수 있다.
- 검토선 빈도(최근 5년, BE·MU·DELL 100%): −10% 14회, −20% 5회, −30% 4회. L1 점검은 연 약 3회, L2 전면 재검토는 연 약 1회로 본다.
- S2 영향(참고, 현 보유 SOXL·MVLL·NBIS 그대로, MVLL = MRVL 2배 모형, 최근 1년, D): 9/30 E 2.81 → MVLL 20%로 줄이면 1.88(1.55를 맞추려면 SOXL 약 28%), MVLL 10%면 SOXL 약 38%, MVLL 0%면 SOXL 약 47%. 어느 경우든 현금 약 41%가 남는다(종목 코어로 채울 몫). 종목당 0.4배 때문에 MVLL 20% 이하 1회차는 그대로 필요하다.

### C.7 사용자 결정 — 1.55 적용 시점 (2026-10-01)

- 사용자 원문: "S7 적용 때 바로"
- 의미: S7 승인·적용과 함께 목표 1.55를 쓴다. 1.0이나 1.32를 거치지 않는다. 지금 E 약 2.8에서 내리는 방향이라 되사는 왕복 매매가 없다.
- 대체: D2(F1.32 60세션 forward shadow)는 하지 않는다.
- 검증 상태: 1.55는 검증 범위 밖이고 forward shadow도 없다. S6 Judge 질문 8에 넣었다. 감수 위험은 C.6 표 그대로다.

### C.8 사용자 결정 — 구성 (2026-10-01)

- 사용자 원문: "카드 종목 코어 + SOXL 보충. 종목 간 되돌리기는 검증 뒤 정식 권고. 단, 카드 종목 코어에 AMD도 추가"
- 규칙 초안
  - 카드 종목 코어: BE·MU·NBIS·DELL·AMD. 편입·비중은 보유 카드(ADD/HOLD/TRIM/EXIT) 판단. 종목당 명목 ≤ 0.4배(1배 주식 40% 이하).
  - SOXL 보충: E = max(N, V)가 1.55 아래로 0.3 이상 벗어나면 기본 보충 대상. 종목 매수가 막힐 때(실적 금지 구간, 카드 미작성)도 SOXL.
  - DRAM·TQQQ: 쓸 수 있는 지수 ETF 목록에는 남기되 기본 대상은 아님(카드 판단). SOXX·SMH·USD는 쓰지 않는다(사용자 조건).
  - 종목 간 되돌리기(±10%p): S4-4 사전 등록 검증 전까지는 카드에 참고 표시만. 통과하면 정식 권고로 올린다(별도 승인).
- AMD 위험(Yahoo, D): 연 변동성 73%(1년)·64%(2년), SOX 대비 1.57·1.49, SOXX 상관 0.78, 다른 코어 종목과 상관 0.33~0.59, 2년 최악 하루 −17.3%(2026-02-04).
- 5종목 균등이면(D): 100% 보유 V 1.44(1년·2년). E 1.55를 채우려면 종목 약 89~90%(각 약 18%) + SOXL 약 10~11%, 명목 약 1.2. 2년 최악 하루 −17.8%(2025-01-27).
- 감수 위험: 5종목 모두 AI 설비 투자 한 테제다(AMD·MU는 반도체, DELL 서버, NBIS AI 클라우드, BE 전력). 종목 분산 ≠ 루트 테제 분산.

### C.9 사용자 결정 — 1.9 절대 상한 유지 (2026-10-01)

- 사용자 원문: "유지"
- 규칙: E = max(N, V) ≥ 1.9이면 모든 신규 매수 권고를 막고(fail-closed) 줄이기 권고를 "긴급"으로 표시한다. 목표(1.55)와 별개로, 따로 사용자 승인과 Judge를 거쳐야 바뀐다.
- 관계: 권고 범위 상단 1.85에서 줄이기 권고와 신규 매수 멈춤이 먼저 걸린다. 1.9는 목표가 나중에 바뀌어도 남는 상위 안전판이다.
- 하루 스트레스(2020-03-16형, SOXX 0.55 + SOXL 0.45 환산, D): 약 −25.7%. 1.55에서는 약 −21.6%(C.6과 같은 환산, S1 하루 경계 −20%보다 깊음).

### C.10 사용자 결정 — 원가 기준 폐지, 종목 고점 −30% 카드 재작성 (2026-10-01)

- 사용자 원문: "원가 기준 폐지, 대신 \"종목 고점 대비 −30%면 그 종목 카드 재작성\""
- 폐지: `holding_risk_rules.positions`(SOXL −20%·MVLL −60%·NBIS −10%, 평균 매입가 기준)와 `freeze_new_buy_candidates_on_any_breach`. 카드에는 원가 대비 손익만 참고로 표시한다.
- 새 검토 규칙(현행 비활성 `peak_drawdown` 초안 재사용)
  - 대상: 보유 중인 모든 종목·ETF(SOXL 포함).
  - 기준: 보유 시작 뒤 정규장 종가 최고치. 새 고점이 나오면 다시 건다(같은 하락 구간 1회).
  - 종가가 고점 × 0.70 이하이면 다음 정규장 전에 그 종목 보유 카드(ADD/HOLD/TRIM/EXIT)를 다시 쓴다.
  - 자동 매도·매도 권고 없음. 카드가 끝나기 전에는 그 종목 채우기(ADD) 권고를 멈춘다.
- 빈도(최근 5년, NBIS 2년, D): BE·MU 연 0.8회, DELL·AMD 연 0.4회, NBIS 연 2.1회, SOXL 연 0.8회. 합치면 연 4회 안팎.
- 코드 영향: `holding_risk_rules`를 읽는 스크립트 8개(고정 해시 평가기 `evaluate_alerts.py` 포함)를 S7에서 고쳐야 한다(K3).

### C.11 사용자 결정 — 타이밍 축소 슬롯 은퇴 (2026-10-01)

- 사용자 원문: "은퇴"
- 대상: `holding_timing_rules.positions.SOXL.slots`(anchor 99주, 실제 75주), `holding_timing_rules.positions.MVLL.slots`(anchor 396주). EMA 이탈·기술적 손절·과열 신호에 따른 조각별 축소 후보를 더 내지 않는다.
- 유지: gap·halt 감시 표시(watch-only), 실적 금지 구간.
- 대체: 노출 조절은 E 권고 범위(1.25~1.85), 종목 판단은 보유 카드, MVLL 매도 근거는 MVLL 카드 트리거와 예약 점검(S7 전 수동 판단).
- 근거: 기본 노출을 신호로 파는 구조는 S4와 부록 C.2에서 손해(최근 5년 50일선 이탈 매도 중앙값 연 −18%p).
- 코드 영향: 타이밍 엔진(`deployment_gate` 해시 고정)이 이 키를 읽는다. 키 제거가 엔진 수정을 부르는지 S7 Builder가 먼저 확인한다(K3).

### C.12 사용자 결정 — 기각 유지, K132-G 보고 전용 가상 운용 (2026-10-01)

- 사용자 원문: "기각 유지, K132-G만 가상 운용(보고 전용)으로 지켜봄"
- 기각 유지: T1·T2·K132-G·T2-132b(G4, NDX 1985~94), X1. 정책 반영 없음.
- K132-G 가상 운용
  - 실제 계좌와 분리된 shadow 원장(SHADOW ≠ ACTUAL). 정책·권고·주문에 쓰지 않는다.
  - 규칙: S4-3 등록 원문 그대로(1.32배, shadow 자산이 252세션 최고의 80% 아래면 1.0배, 90% 이상 회복하면 1.32배). 상품은 SOXX + SOXL(ETF 코어 방식, 가상이라 SOXX 제외 조건과 무관), 실제 종가, 종가 t 결정 → t+1 체결, 10bp.
  - 비교: SOXX 100%(B0), 고정 1.32(F1.32).
  - 보고: 월 1회 한 줄(누적 수익 차, 최대 낙폭 차, 게이트 꺼짐 횟수). Cold Path라 실패해도 핵심 판단을 막지 않는다.
  - 승격 경로 없음. 다시 후보로 올리려면 새 사전 등록이 필요하다.
- 구현: S7 범위에 선택 항목으로 넣는다(Cold Path).

### C.13 사용자 결정 — 입출금 보정 (2026-10-01)

- 사용자 원문: "대조 때 사용자가 신고"
- 규칙: 키움 잔고 대조안에서 예수금이 매매로 설명되지 않게 바뀌면 입출금 신고 칸을 둔다. 사용자가 "확인 <코드>"와 함께 신고하면 입금은 HWM에 더하고 출금은 뺀다. 신고가 없으면 HWM 갱신과 선 판정을 보류하고 신규 매수 권고를 멈춘다(fail-closed).
- 구현: `reconcile_broker_state.py` 대조안 형식 변경이 필요하다(apply 경로, K3). S7 Builder가 broker-snapshot-reconciliation 절차 문서와 함께 확인한다.
