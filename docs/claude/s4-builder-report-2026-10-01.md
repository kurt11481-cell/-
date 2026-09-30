# S4 Builder 보고 — 신호 워크포워드 검증 (2026-10-01)

- 역할: S4 신호 검증 Builder(연구 전용, K2 수준 절차). worktree `s4-signals`, 브랜치 `worktree-s4-signals`(기준 HEAD `cf17573`).
- 성격: D/C 등급 연구. 정책·상태 변경 없음, `order_authority=false`, `quantity_authority=none`.
- 커밋·push·merge: **하지 않았다.** 사용자 승인을 기다린다.

## 1. 결론 (게이트)

**게이트 판정 5개 행 모두 `gate_failed`다.** S5 제안 후보와 검토 전용 후보 모두 없다. 자세한 표는 `SOXL_SIGNAL_WALK_FORWARD_RESULTS_2026-10-01.md`.

| 행 | G1 | G2 | G3 | G4 | G5 | G6(관찰 수) | 판정 |
|---|---|---|---|---|---|---|---|
| C1-WF | ✗ (회복 −9.5%) | ✓ | ✓ 10/10 | ✗ (20bp, 이웃 2/5) | ✓ | ✗ 13 | gate_failed |
| C2-WF | ✗ (회복, CAGR 29%) | ✗ | ✓ 7/10 | ✗ | ✓ | ✓ 21 | gate_failed |
| C1 기본 | **✓** (MDD +16.1%p, 회복 −26%, CAGR 104%) | ✓ (×1.33) | ✓ 10/10 | ✗ (**이웃 2/5**) | ✓ | ✗ 12 | gate_failed |
| C2 기본 | ✗ | ✗ | ✓ 7/10 | ✗ | ✗ (62.5%) | ✗ 19 | gate_failed |
| C3 기본 | ✗ (CAGR 39.5%) | ✗ | ✓ 9/10 | ✗ | ✓ | ✗ 19 | gate_failed |

- C1 기본이 유일하게 G1·G2·G3·G5와 20bp·50bp를 모두 통과했지만, 이웃 5개 중 3개가 G1·G2를 통과하지 못해 사전 규칙상 "고립된 최고점"으로 거부됐고 관찰 수도 부족하다.
- 1차 OOS 요약(10bp): B0 CAGR 34.6%/MDD −73.3%/회복 546, C1 36.1%/−57.3%/402, C2 7.5%/−61.4%/1124, C3 13.7%/−38.6%/431.
- 활성화 경로: 정책 반영은 S5 제안 → S6 Judge → S7 사용자 승인 → forward shadow 뒤에만 가능하다.

## 2. 추가한 파일 (모두 새 파일, 기존 파일 수정 0건)

`git status`는 아래 새 파일(untracked)만 보인다. `git diff`는 비어 있다.

| 파일 | 내용 | sha256(앞 16자) |
|---|---|---|
| `stock-strategy-system/backtests/SOXL_SIGNAL_WALK_FORWARD_PROTOCOL_2026-10-01.md` | 사전 등록 원문 + 부록 A(결과 전 수정 A1, Builder 명확화 A2) | `2e6a2d243278fff7` (LF 정규화 `868f0377bdf30904`) |
| `…/SOXL_SIGNAL_WALK_FORWARD_PROTOCOL_2026-10-01.sha256` | 프로토콜 해시 sidecar. 러너가 실행 전에 일치를 확인한다 | — |
| `…/walk_forward_soxl_signals_2026-10-01.py` | 러너 `--self-test`, `--collect`, `--run` | `5294d17cb84a1c0b` |
| `…/soxl_signal_inputs_2026-10-01/` (14개) | 4개 종목의 Nasdaq 원본·Yahoo 원본·결합 CSV, DGS3MO.csv, 출처 JSON(해시·행 수·불일치 수·Yahoo 단일 출처 세션) | 출처 JSON 참고 |
| `…/soxl_signal_walk_forward_2026-10-01_results.json` | 결과(프로토콜·러너·입력 해시 포함) | `fdf696740b0f33b6` |
| `…/soxl_signal_walk_forward_2026-10-01_daily.csv`, `_trades.csv` | 1차 OOS 일별 자산·비중, 체결 로그 | `999d67dda60d2af9`, `67a32c85dd2bdc36` |
| `…/SOXL_SIGNAL_WALK_FORWARD_RESULTS_2026-10-01.md` | 결과 보고서(한국어, 결론 먼저, 게이트 표) | — |
| `docs/claude/s4-builder-report-2026-10-01.md` | 이 문서 | — |

- 새 파일은 CRLF로 저장했다. 기존 파일의 줄바꿈은 건드리지 않았다.
- 재사용한 기존 코드(읽기만, 로드 후 메모리에서만 재정의): `walk_forward_soxl_policy_2026-08-05.py`의 `metrics`, `regime_label`, `split_map`, `EARLY_CLOSES`, `FULL_CLOSURES`(달력 대조용), `backtest_soxl_ema_policy_2026-08-05.py`의 `fetch_nasdaq`, `fetch_yahoo`, `combined_history`, `yahoo_dividends`. `sys.dont_write_bytecode`로 `__pycache__`도 만들지 않았다.
- 승인 매니페스트에 고정된 스크립트, `alert_policy.json`, `portfolio_state.json`, `workspace/policies/*`는 건드리지 않았다. 키움 도구와 `.env`·토큰·계좌번호도 쓰지 않았다.

## 3. 검증 절차

- 기준선: 전체 테스트 2058개 중 실패 23 + 오류 291 = **314건**(1 skipped). 작업 후 재실행 결과도 314건이며 **실패 ID 집합이 완전히 동일**하다(diff 없음). 원인은 이 worktree의 고정 해시 불일치·한글 경로·`pypdf` 미설치 등 이번 작업과 무관한 항목이다.
- self-test(합성 데이터, 네트워크 불필요) 통과: ① 9개 절단 길이에서 18개 변형의 신호 일치 ② 종가 t 신호 → t+1 시가 체결 ③ 비용(10bp) 계산 ④ 폴드 학습 구간이 시험 시작 전에 끝남, 시험 구간 데이터를 바꿔도 선택 불변 ⑤ 갭은 시가로만 체결 ⑥ 시가 결측·0이면 대기 동작 동결. 추가로 C2 상태 기계(0→전체 직접 경로 없음, 실패 FTD, 낙폭 탈출, 거래량 fail-closed)와 휴장일 생성기 = 기존 손입력 목록(2018-09~2026-07) 일치를 확인했다.
- 실제 데이터로도 절단 9개(전체 이력의 30~100%)에서 모든 변형의 신호가 전체 이력과 일치함을 확인했다.
- 독립 엔진 검증(주식 수 기준으로 새로 짠 시뮬레이터, scratchpad 일회용): B0, B1, C1, C1_band5, C2, C2_k3.0, C3의 자산곡선이 러너와 상대오차 1e-14 이하로 일치했다.
- 입력: 4개 종목 종가 불일치 0건(Yahoo 분할 기준 정렬 후), 분할 기준 차이로 설명한 행 0건, 세션 누락·중복 0건.

## 4. 실행 이력·수정 사항 (규칙·파라미터 변경 아님)

1. 프로토콜 확정 후 결과 계산 전에 **수집 절차**만 수정했다. FRED DGS3MO가 `Mozilla/5.0` User-Agent 요청에서 응답하지 않아(타임아웃) 기본 urllib 요청과 재시도로 바꿨고 정상 수집했다(4,209행).
2. 최초 `--run` 뒤 **표시 필드**(`estimated_cost_nav`)가 연속 실행 경로에서 시험 시작 자산으로 정규화되지 않은 것을 발견해 정규화만 고쳐 재실행했다. 손익·MDD·게이트·선택 결과는 두 실행이 같다.
3. 종료일은 2026-09-29(수집 시점 뉴욕 시각 2026-09-30 11:35, 9/30 세션 미완료).
4. post-hoc 탐색: 없다. 결과 문서의 이웃 변형 "참고" 해석은 게이트 판정에서 제외했다.

## 5. 확인 필요

1. **C1을 계속 후보로 볼지**: 결과상 방향(MDD 감소)은 이웃에서도 유지되지만 G1 세 조건을 동시에 넘는 것은 파라미터에 민감하다(5개 중 2개). 관찰 수 12개는 "검토 전용" 기준에도 못 미친다. 계속하려면 S5에서 새 규칙이 아니라 forward shadow 설계부터 다뤄야 한다(이 데이터로 파라미터를 고르면 post-hoc).
2. **G4 이웃 규칙의 엄격도**: 사전 등록 A1-4대로 판정했다(과반 미달 → 거부). 이웃 3개의 실패 원인은 회복 기간(494~514세션 vs 필요 ≤491)과 CAGR 88% 같은 경계 근처였다. 규칙 변경은 결과를 본 뒤의 변경이므로 하지 않았고 판단은 S5/S6에 맡긴다.
3. **Yahoo 단일 출처 구간**: 2010~2016-09-28(SOXX·QQQ·TQQQ는 1,697세션, SOXL 1,651세션)과 SOXL 2026-04-20 1세션. 1차 OOS와 학습 구간은 Nasdaq 교차확인 구간이라 게이트에는 영향이 없지만, 보조 OOS 2013~2016 일부는 교차확인이 없다.
4. **SOXL 2023-06-05 Nasdaq 고가(21.44) < 시가(21.75)**: Yahoo 고가는 21.75. 엔진은 시가·종가만 쓰므로 영향 없음. Nasdaq 데이터 품질 참고사항.
5. **2010~2017 조기 종료일**은 규칙으로 생성했고 벤더로 직접 검증하지 못했다(FTD 거래량 fail-closed에만 영향).
6. **G3 정의**: 폴드 MDD 개선 기준(승인된 A2). 폴드 수익률 기준 개수는 병기했고 C1은 4/10, C3는 5/10이다.
7. **추가 산출물 요청**: 러너에 `--collect`와 프로토콜 해시 sidecar를 추가했다(계획 승인분). 다른 위치로 옮기거나 합치고 싶으면 알려 달라.
8. **커밋 제안(승인 시)**: 브랜치 `worktree-s4-signals`에 위 새 파일만 커밋한다(입력 CSV 포함). push·merge는 하지 않는다.

Builder 완료, worktree s4-signals, 새 실패 수 0
