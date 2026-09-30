# 수동 분석 preflight FAIL 진단 (P4 §9 S4 관찰)

- 날짜: 2026-09-30
- 등급: K2 읽기 전용 진단. 코드·설정·정책·상태 파일은 수정하지 않았다.
- 대상: `docs/claude/system-review-p4-roadmap-2026-09-30.md` §9 "S4 관찰(조치 대기)"의 확인 필요 항목
- 세션: Cowork, Sonnet 5.5 / high

## 1. 결론

- 세 hard fail(`ACQUISITION_TIMESTAMP_INVALID`, `AUTHORITY_REVALIDATION_AT_ACQUISITION_CUTOFF_FAILED`, `TEMPORAL_EVIDENCE_VIOLATION`)과 `acquisition_completed_at` 누락은 **원인이 하나**다. 실패한 계좌 조회 결과의 `retrieved_at`이 null로 지워져 취득 완료 시각(cutoff)을 만들지 못한다.
- 지우는 코드는 커밋 `52fb932`(2026-09-29)에서 처음 들어왔다. 9/9~9/17 PASS 실행은 그 이전 코드로 돌았다.
- 조정(reconcile) 적용은 원인이 아니다. 적용 전 실행(02:34, 02:37 UTC)부터 같다.

## 2. 근거

1. `run_manual_portfolio_analysis.py:721` `_acquisition_complete_cutoff`: 모든 결과에 `retrieved_at` 문자열이 있어야 값을 낸다. 하나라도 없으면 None.
2. cutoff가 None이면 세 코드가 함께 붙는다.
   - `ACQUISITION_TIMESTAMP_INVALID`: :1744.
   - `AUTHORITY_REVALIDATION_AT_ACQUISITION_CUTOFF_FAILED`: 판정에 "cutoff가 None이 아님"이 포함(:1540).
   - `TEMPORAL_EVIDENCE_VIOLATION`: 판정에 같은 조건이 포함(:1805).
   - `manual_view["acquisition_completed_at"]`은 null(출력에서 확인).
3. `kiwoom_account_readonly_bridge.py:237-241` `_sanitize`: `bridge_status`가 PASS/PARTIAL이 아니면 `runtime_commit`과 `retrieved_at`을 None으로 만든다.
4. 실패하는 조회는 미체결(`account_open_items`)과 실현손익(`account_realized_pnl_read`)이다. 둘 다 매번 `KIWOOM_API_RESPONSE_ERROR`이며, 원인은 키움의 "내역 없음"(`return_code=20`) 응답이다(`open-orders-diagnosis-2026-09-30.md` §1).
5. 출력 대조 (`workspace/outputs/manual-portfolio-analysis/`):

| 실행 | preflight | 미체결 실패 결과의 `retrieved_at` | `runtime_commit` |
|---|---|---|---|
| `manual-20260917T151230776810Z-179b5a58fdff` | PASS | `2026-09-17T15:12:33.379042+00:00` | 있음 |
| `manual-20260930T023434703180Z-2ae4c4f9267b` | FAIL | null | null |
| `manual-20260930T033605866426Z-de8c5915d000` | FAIL | null | null |

   두 시점 모두 두 조회 실패는 같다. 달라진 것은 실패 결과에 시각이 남느냐뿐이다.
6. 커밋 이력: `git log -S`로 `safe.update(runtime_commit=None, retrieved_at=None` 줄이 처음 나오는 커밋은 `52fb932`(2026-09-29)다. `_failure_timing_evidence`는 `a5e872a`(2026-09-29)에서 들어왔다.
7. 합성 재현(읽기 전용, 함수 직접 호출): `[성공(시각 있음), 실패(시각 null)]` → cutoff None. 실패 결과에 시각이 있으면 정상 값.

## 3. 영향

- `evidence_grade`: 9/17 GRADE_B → 9/30 UNVERIFIED. `decision_quality_eligible=false`, 사유 `MANUAL_REAL_DATA_NOT_VERIFIED`.
- 조정 계층(`broker_diff_status=MATCH`)은 이 FAIL과 무관하게 정상이다.
- S5 카드 파일럿이 분석 증거 등급을 근거로 쓰면 영향을 받는다.

## 4. 확인하지 못한 것 (확인 필요)

- 오늘 5회 중 직접 연 것은 2회(02:34, 03:36 UTC). 나머지 3회는 로드맵 기록을 따랐다. 같은 코드 경로라 같은 원인일 가능성이 높다.
- `_failure_timing_evidence`(:812)는 부모 캡처 파일이 전달될 때만 실패 시각을 대신 채운다. 오늘 실행에 캡처가 전달됐는지는 확인하지 못했다. 일반 경로에서는 채워지지 않는 것으로 보인다.
- 9/29 커밋에서 시각을 지운 의도(주석: "Failed responses expose safe diagnostics, never Worker metadata")는 커밋 메시지로 확인하지 못했다. 설계 충돌이라는 점만 코드로 확인했다.

## 5. 수정 방향 (이 진단에서는 수정하지 않음)

- 후보: 실패 결과에도 부모 프로세스가 찍은 조회 시각을 남기거나, cutoff 계산이 실패 결과를 다르게 다루게 한다.
- 변경 등급: **K3.** `run_manual_portfolio_analysis.py`는 Kiwoom acceptance 고정 파일이고, 시간 계약(temporal evidence)을 바꾼다. 사용자 승인과 독립 Judge가 필요하다.
- 순서: S1b 안 A(브리지 관측 추가)와 같은 `kiwoom_account_readonly_bridge.py`를 건드리므로 I0 Judge 이후에 함께 설계한다.
- 권장 세션: Opus · xhigh, 새 Cowork 작업 또는 새 worktree. 이 문서를 첫 입력으로 넣는다.
