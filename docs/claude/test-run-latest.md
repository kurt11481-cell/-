# 전체 테스트 실행 결과 (5단계-1)

- 실행일: 2026-09-30
- 명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"` (원본 폴더, 서브에이전트가 실행)
- 결과: 1897개 실행, 233초, **FAILED (failures=8, errors=15)**
- 출처: 서브에이전트 보고를 그대로 옮긴 것이며, 이 문서를 쓰는 시점에 개별 실패는 직접 재확인하지 않았다.
- 전체 로그(저장소 밖): scratchpad의 `full_tests.txt`
- 스키마 감사 `validate_schema_contracts.py`: PASS (errors 없음)

## 실패 모듈

| 모듈 | 건수 | 원인 | 예상 여부 |
|---|---|---|---|
| `test_materialize_kiwoom_session_aware_acceptance_candidate` | 15 (ERROR 14, FAIL 1) | 현재 active Kiwoom acceptance가 유효하지 않음: priority policy, source registry, provider-scope 항목 전부 `acceptance hash mismatch`. ERROR 14건은 test 01~09b(test_08은 제외 심볼 BRK.B, BRKb, COST로 3회 계산), FAIL 1건은 test_10(active acceptance가 유효하길 기대) | 예상(15건, 6~9단계 대상) |
| `test_v2_6_7_session_aware_kiwoom_priority` | 2 FAIL | `test_extended_provider_scope_candidate_validates_without_activation`, `test_guarded_priority_requires_locked_acceptance_manifest`가 `implementation hash mismatch: manage-us-stock-strategy/scripts/run_manual_portfolio_analysis.py` 보고. 고정된 acceptance 해시가 현재 스크립트 바이트와 어긋남 | 예상 |
| `test_sec_scheduled_shadow` | 5 FAIL | test 01·05·23: PowerShell `Join-Path` 파라미터 바인딩 오류(종료코드 1, 기대 0), 환경/로캘 문제로 추정. test 35·37: SEC 접근 가드의 `SEC_ACCESS_BLOCKED`(종료코드 7, 기대 1) | **예상 밖** |
| `test_save_daily_pipeline` | 1 ERROR (import) | `pypdf` 미설치로 모듈 import 실패 | **예상 밖** |

## 메모

- 예상 실패 17건(15 + 2)은 Kiwoom acceptance 고정 해시 문제로 보이며, 서브에이전트는 같은 뿌리로 판단했다. `docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md`와의 일치 여부는 확인하지 않았다.
- 예상 밖 실패 6건(`test_sec_scheduled_shadow` 5건, `test_save_daily_pipeline` 1건)은 원인이 테스트 환경(PowerShell, pypdf, SEC 접근 가드)으로 보이나 원인 확정은 하지 않았다.
- 이 실행 중 파일 수정과 커밋은 없었다.
