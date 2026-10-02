# S7 분할 보정 Builder 보고 (2026-10-02, K2)

- 지시문: `docs/claude/s7-split-adjustment-builder-prompt-2026-10-02.md` 3절
- worktree `s7-split`, 시작 HEAD `2442907`(지시문 커밋과 일치). 커밋하지 않았다.
- 결과 요약: 대상 테스트 8개 파일과 스키마 감사 통과. 전체 테스트 **새 실패 0**.
- 순서 이탈 한 가지: 지시문은 테스트를 먼저 쓰라고 했지만 구현을 먼저 하고 테스트를 뒤에 썼다. 그래서 "고치기 전 실패 수"는 아래 방법으로 따로 쟀다.

## 1. 바꾼 파일

| 파일 | 구분 |
|---|---|
| `manage-us-stock-strategy/scripts/corporate_actions.py` | 새 파일. 순수 함수(검증, 보정, 적용 요약, 분할 대조 필요 판정). 파일·시계·네트워크 접근 없음 |
| `manage-us-stock-strategy/schemas/corporate-actions.schema.json` | 새 파일 |
| `manage-us-stock-strategy/scripts/portfolio_exposure.py` | `build_exposure_review(corporate_actions=)` 추가, V·고점 경로 연결, 자산 경로 보호, 주석 |
| `manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py` | 기록 파일 읽기(`load_corporate_actions`), `inputs` 기록, 읽기 전용 감시 목록에 추가 |
| `manage-us-stock-strategy/tests/test_corporate_actions.py` | 새 파일(27개) |
| `manage-us-stock-strategy/tests/test_run_portfolio_exposure_review.py` | 새 클래스 `CorporateActionsRunnerTests`(5개) 추가만. 기존 단언 변경 없음 |
| `manage-us-stock-strategy/references/portfolio-exposure-review.md` | K0: "Corporate-action record" 절, Files 표 두 줄, Routine 2단계 추가(뒤 단계 번호는 밀림), SPLIT_GUARD 문단 한 문장 |

`git diff --stat`(추적 중인 파일): 4개 파일, 310 추가 / 31 삭제. 새 파일 3개는 미추적.

바꾸지 않은 것: `regular_session_close_history.py`, `portfolio-exposure-review.schema.json`(`inputs`에 속성 제한이 없어 수정 불필요, C9), `alert_policy.json`, `workspace/policies/*`, 상태·원장·journal, 이력·쪽 파일, 키움 고정 16개, deployment_gate 고정 6개, 기존 픽스처. 목록 밖 수정이 필요한 일은 없었다.

## 2. 원시 sha256 (작업 트리 바이트 기준)

| 파일 | 전 | 후 |
|---|---|---|
| `scripts/portfolio_exposure.py` | `674c3267682874c44f956c0b744512ca62a9d8ac3b0ab1668993decbf8911dfa` | `585803c220bfcf1dbef9282799e77dad0101a447f6a5cc3c8479f997073477fc` |
| `scripts/run_portfolio_exposure_review.py` | `3e5060f0fb4264f197b6d389c7c443b30a0f75fc3e1439d7f9e8edbd647b8a09` | `14a69b5bca15a82b1c114b38c261c77654d5f4cfdc722b713a40393d9fddd095` |
| `tests/test_run_portfolio_exposure_review.py` | `c1a19cd6d76989d10c04a0f3c8188e8f8726570f49f1c0ec459f67c08a163036` | `0116608366a4927d2c4baf25fe1b7e67868e085ca1db2af4072b4ec0981752d1` |
| `references/portfolio-exposure-review.md` | `2974143dfb47898803fa276db993220c9ee01226b8a7e649ed05ea179d4d7035` | `f36c2390d93989f48dd952f75eb3da46d458bc5c7f9978057925daf2f4a2b2ba` |
| `scripts/corporate_actions.py` (새) | - | `874c6e91e6e2d5cca8c55362bc63990fa250fc9e3ae54e0114708d2f3dc44f5a` |
| `schemas/corporate-actions.schema.json` (새) | - | `2dcf2d5ee0ac5c9b5df0fa1f0ce80f3ea24049a411573934e962b9ce8e7500f2` |
| `tests/test_corporate_actions.py` (새) | - | `7922367e365769ba389393506f02e1f19164315049dc367511eb4fe0ebbff4e0` |

변경 금지 파일 `regular_session_close_history.py`, `portfolio-exposure-review.schema.json`, `alert_policy.json`은 전후 해시가 같다. `git status`에도 나타나지 않는다. (참고: 이 worktree의 `portfolio_state.json`은 Git 미추적이다. 쓰지 않았고 `as_of` 한 줄만 검색으로 확인했다.)
"전" 해시는 HEAD 블롭을 CRLF로 환원해 계산했고, 변경 금지 파일에서 같은 방법이 작업 트리와 일치함을 확인했다.

## 3. 줄바꿈 (R9)

변경·신규 7개 파일 모두 CRLF만 있고(bare LF 0), BOM 없음. 일괄 변환은 하지 않았다. 새 파일 3개만 작성 뒤 CRLF로 바꿨다. 기존 파일은 Edit 도구가 CRLF를 보존했다.

## 4. 구현 요약

- 기록 위치: `<closes_root>/corporate-actions.json`(`--closes-root`를 따름, 새 옵션 없음). 형태와 검증 V1~V5는 지시문 그대로이고, 추가 키·중복·달력 밖 세션·new=old·published_date>effective 등은 파일 전체 INVALID. 날짜는 `YYYY-MM-DD` 엄격 형식만 허용한다(문자열 비교 때문). 파일 없음은 MISSING(동작 불변).
- 보정(R1): effective_session보다 앞선 세션 종가에 `Πold/Πnew`를 한 번에 곱한다(Decimal, 반올림 한 번이라 300×1/3이 정확히 100). 입력 딕셔너리는 바꾸지 않는다.
- 사용처(R2): V 수익률(`ExposureModel`)과 `evaluate_peak_reviews`만 보정 종가. `closing_equity`(review lines, `activation_candidate`, 현재 자산), 포지션 표시 close, 기준 상품 종가 확인은 원주가.
- 판단 한 가지: 평가 세션 이후에 효력이 생기는 기록은 적용하지 않는다(`--session`으로 과거 세션을 볼 때 이후 분할이 평가 세션 종가를 바꾸지 않게). 지시문에 명시되지 않은 부분이다.
- SPLIT_GUARD(R3): 값·연산자 무변경, 보정 종가에 그대로 적용.
- INVALID(R4): V 불가(`V_UNAVAILABLE:CORPORATE_ACTIONS_INVALID`), 고점 점검 보유 종목 모두 UNVERIFIED(사유 `CORPORATE_ACTIONS_INVALID`, 트리거에는 `PEAK_CORPORATE_ACTIONS_INVALID:<SYM>`). 자산·선은 영향 없음. 활성화 전에도 UNVERIFIED로 표시한다(지시문의 "각 종목"을 그대로 읽음).
- 자산 경로(R5): 스냅샷 as_of < effective_session ≤ 세션이고 그 종목을 보유하면 그 세션 자산은 미확인, 사유 `SPLIT_RECONCILIATION_REQUIRED:<SYM>:<effective_session>`(종가 누락과 같은 처리, `required_price_missing` 트리거와 review lines의 `EQUITY_GAP`에 나타남). 수량은 비율로 고치지 않는다. 스냅샷 as_of가 effective_session과 같으면 정상.
- 출력(R6): `inputs.corporate_actions = {status, sha256, errors, applied[{symbol, effective_session, new_shares, old_shares, price_factor}]}`. `applied`는 평가 세션에 이미 효력이 있는 기록만. 한 줄 표시와 display block은 그대로.
- 읽기 전용(R7): 기록 파일을 `watched`에 넣었다. 파일을 쓰거나 고치는 코드는 없다.

## 5. 테스트

수정 전 코드에서의 실패 수: 수정한 두 스크립트를 HEAD 버전으로 잠시 되돌려(백업 후 복원, 복원 뒤 해시 일치 확인) 새 테스트만 돌렸다.
- `test_corporate_actions.py`: 27개 중 **21개 오류**(나머지 6개는 순수 검증 테스트로, 새 모듈만 쓰므로 통과)
- `CorporateActionsRunnerTests`: 5개 모두 실패 또는 오류(하위 케이스 포함 failures 3, errors 5)

수정 후 대상 테스트(파일별 `-p`):

| 파일 | 결과 |
|---|---|
| test_corporate_actions.py | 27 OK |
| test_portfolio_exposure.py | 43 OK |
| test_portfolio_exposure_fail_closed.py | 32 OK |
| test_portfolio_exposure_judge_fixes.py | 29 OK |
| test_portfolio_exposure_display.py | 7 OK |
| test_run_portfolio_exposure_review.py | 22 OK |
| test_regular_session_close_history.py | 19 OK |
| test_s7_calendar_binding.py | 10 OK |

스키마 감사 `validate_schema_contracts.py`: PASS, errors 없음.

지시문 T1~T11 대응: T1·T2·T3·T4·T6·T7·T8·T9·T10은 `test_corporate_actions.py`, T5는 같은 파일의 검증 테스트와 러너의 비정상 파일 테스트, T11(기록 변경·생성 감지, `inputs`의 상태·sha256·applied)은 러너 테스트. 추가로 벤치마크(SOXX) 분할, 평가 세션 이후 기록 미적용, 스냅샷 as_of=effective 경계, 미보유 종목 비적용, upd_rt 허용오차 경계를 넣었다.

전체 테스트(서브에이전트, `python -m unittest discover -s manage-us-stock-strategy/tests`):
- 0단계 기준선: tests=2243, failures=23, errors=291, skipped=1 (고유 실패·오류 ID 314개)
- 3단계: tests=2275, failures=23, errors=291, skipped=1 (고유 ID 314개)
- **새 실패 0**, 사라진 실패 0. 늘어난 32개(27+5)는 모두 통과.
- 기준선의 314개는 이번 변경과 무관한 기존 실패다(dashboard 143, integrated_authority_snapshot 38, order_intent 15 등. 원인은 분석하지 않았다). 기준선은 구현 초기에 일부 파일을 수정하는 동안 돌렸지만, 실패 모듈에 exposure 관련이 없고 전후 실패 집합이 완전히 같다.

## 6. R5가 실데이터 경로에 미치는 영향

- 이 worktree에는 Git 무시 폴더(`workspace/outputs/regular-session-closes/`)가 없어 실데이터 실행은 하지 못했다. Cowork가 병합 뒤 5절 순서로 확인한다.
- 분석: 기록 파일이 아직 없으므로(MISSING) R5는 작동하지 않는다. MVLL 기록(effective 2026-06-26)을 넣어도, 상태 파일의 현재 스냅샷 as_of가 2026-09-29(effective 이후)이므로 지금 평가 세션의 자산은 바뀌지 않을 것으로 본다. 활성화 전 HWM 구간은 2026-09-30 하루뿐이라 과거 스냅샷도 쓰이지 않는다. 원장 과거 스냅샷은 읽지 않았으므로 확정이 아니다.

## 7. 남은 문제

- 실데이터 실행(기록 파일 생성, V 값, `NOT_READY` 사유 확인)은 Cowork 몫(지시문 5절).
- 기록되지 않은 분할 중 3:2 같은 작은 분할은 코드가 잡지 못한다. 루틴 2단계(키움 수정 표시 확인)에 맡겼다(지시문 4절).
- 기록되지 않은 분할이 보유 중에 생기면 자산 경로에는 분할 감시가 없다. 지시문 4절과 같은 기존 한계다.
- 정책 문구에 기록 파일을 적는 일은 K3라 하지 않았다.
- 기준선의 기존 실패 314건은 별개의 문제다.
