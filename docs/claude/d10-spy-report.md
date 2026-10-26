# d10-spy Builder 보고

사장 결정 d10 (REUSE, 2026-10-26). 변경 파일은 allowed_paths 세 개뿐이다: `score_decision_journal.py`, `test_score_spy_history.py`(새 파일), 이 보고.

## 바꾼 곳 (manage-us-stock-strategy/scripts/score_decision_journal.py)
| 위치 | 전 | 후 |
|---|---|---|
| 상수 (74행) | 없음 | `BENCHMARK_HISTORY_SOURCE = "KIWOOM_CLOSE_HISTORY"` |
| 새 함수 `load_benchmark_closes` (154-175행) | 없음 | reference-closes 결과가 `MISSING`이 아니면 그 결과를 그대로 돌려줌. `MISSING`이고 달력이 있을 때만 `load_close_histories([SPY], ...)`로 history/SPY.close-history.json을 읽음 |
| `load_inputs` benchmark 줄 (819행) | `load_reference_closes(closes_root)` | `load_benchmark_closes(closes_root, calendar, load_close_histories)` |
| `score_journal` benchmark 블록 (609행) | 키 `symbol, label, status, errors` | 같은 키. `source`는 결과에 `source`가 있을 때(history 경로)만 추가 |
| 모듈 설명 (29-31행) | SPY는 reference 파일만 | history 대체 경로 설명 추가 |

`load_reference_closes`(116-149행)는 한 줄도 바꾸지 않았다. 지평 계산·`_split_suspect`·`_score_horizon`·채점 규칙·라벨(`REFERENCE_ONLY`)·최소 표본(30)은 그대로다.

## reference-closes 경로 불변 확인
- reference 파일이 있으면(OK이든 INVALID이든) `load_reference_closes` 결과를 그대로 돌려주며 `source` 키가 붙지 않는다. 시험 a, a2, d가 키·값 동일을 단언한다.
- 리포트의 benchmark 블록도 reference 경로에서는 이전과 같은 4개 키다(시험 a).

## history 검증 방식
- 기존 `run_portfolio_exposure_review.load_close_histories`를 그대로 재사용한다(`load_inputs`가 이미 쓰는 같은 함수, 스키마·자기 해시·페이지 해시·심볼·달력 해시·페이지 재현 검증 포함).
- 상태가 `MISSING`이면 이전과 같은 `MISSING` 결과. 그 밖의 실패는 `INVALID`(closes 비어 있음, errors 최대 5개, source 표시).
- `unverified` 세션(예: 겨울시간 -05:00 라벨, 달력 비활성, 페이지 미검증)은 benchmark closes에서 뺀다. 검증된 세션이 하나도 없으면 `INVALID`(`CLOSE_HISTORY_NO_VERIFIED_SESSIONS`). 그 지평은 기존 코드대로 `BENCHMARK_UNAVAILABLE`이 된다.
- history 파일과 reference 파일은 읽기만 한다(쓰기 없음).

## 시험
새 파일 `manage-us-stock-strategy/tests/test_score_spy_history.py` (10건, 임시 폴더 합성 파일, 임시 통합 권한 루트로 달력 활성):
- a reference만 → 이전과 같은 결과·리포트 블록 / a2 reference가 깨짐 → history로 대체하지 않고 INVALID
- b 둘 다 없음 → MISSING
- c history만 → OK, closes 동일, source 표시(리포트 블록 포함), 라벨 REFERENCE_ONLY
- d 둘 다 → reference 승, source 없음
- e history 값 변조(해시 불일치) → INVALID / e2 JSON 아님 → INVALID / e3 미확인 세션만 빠짐 / e4 미확인 세션뿐 → INVALID. 모두 예외 없음
- f 달력 없음 → MISSING, history 읽지 않음

실행 결과:
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_score_spy_history.py"`: 10건 OK
- `-p "test_score_*.py"`: 76건 OK (새 10건 포함)
- `-p "test_journal_score_*.py"`: 14건 OK
- 전체 스위트·기준선 비교는 파이프라인이 한다(실행 안 함). 기존 시험 파일은 고치지 않았다.

## 확인 필요
- 키움이 SPY 30분봉을 주는지, SPY가 정책 symbols_extra에 들어간 뒤 첫 수집에서 history/SPY.close-history.json이 생기는지는 이 작업에서 확인하지 못했다(정책·키움 조회는 범위 밖). 파일이 없으면 benchmark는 지금처럼 `MISSING`이다.
- SPY가 미국 ETF라 거래소 값(`exchange`)이 history 검증에 영향을 주는지는 실제 파일로 확인 필요(시험은 `NYSE` 합성 값).

## 범위 확인
- SPY는 채점 출력의 참고 비교에만 쓰인다. 주문표·관문·코어 입력으로 가지 않는다. 추가한 코드·시험 줄에는 주문·권한 표지가 없다.
- 기존 파일 줄바꿈(CRLF) 유지.
