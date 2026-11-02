# acc-implhash2 Builder 보고 (2026-11-02)

## (a) 바꾼 줄
파일: manage-us-stock-strategy/tests/test_v2_6_7_session_aware_kiwoom_priority.py
- test_v2_6_7_session_aware_kiwoom_priority.py:104-119: 상수 `IMPLEMENTATION_DRIFT_PREFIX`와 모듈 도우미 `split_implementation_drift(errors, manifest)` 추가. 오류 목록을 (구현 해시 어긋남 경로, 그 밖의 오류) 두 갈래로 나눈다.
- test_v2_6_7_session_aware_kiwoom_priority.py:314-317: 클래스 도우미 `assert_only_implementation_drift` 추가. (가) 그 밖의 오류 `[]` 단언(316행), (나) 어긋남 경로가 manifest `implementation_hashes` 키 안에 있음을 단언(317행).
- test_v2_6_7_session_aware_kiwoom_priority.py:347-349: `test_extended_provider_scope_candidate_validates_without_activation`의 마지막 단언(`assertEqual(..., [])`)을 위 도우미 호출로 교체. 실제 manifest(`current_acceptance_manifest_path()`)를 그대로 사용.
- test_v2_6_7_session_aware_kiwoom_priority.py:452, 454, 461: `test_guarded_priority_requires_locked_acceptance_manifest`. 452행 manifest를 변수로 받음, 454행 `manifest=manifest`, 461행 `assertEqual(errors, [])`를 도우미 호출로 교체. 실제 manifest 그대로 사용.
- 검증기·Acceptance·정책·다른 시험·다른 단언 변경 없음. skip 추가 없음. 사본·해시 다시 채우기 없음.

## (b) 구현 해시 어긋남 경로
두 시험 모두 같은 10개 경로가 나온다(manifest 835d4f46…). 방법: 시험 파일 도우미에 임시로 `self.maxDiff = None`과 `self.assertEqual(drifted, [])`를 넣고 지시문 명령 한 줄로 실행해 옮겨 적은 뒤 임시 줄을 지웠다.
- manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json
- manage-us-stock-strategy/schemas/kiwoom-acceptance-pin-scope.schema.json
- manage-us-stock-strategy/schemas/kiwoom-cash-flow-evidence.schema.json
- manage-us-stock-strategy/schemas/kiwoom-reconciliation-proposal.schema.json
- manage-us-stock-strategy/scripts/apply_user_confirmed_broker_snapshot.py
- manage-us-stock-strategy/scripts/cash_flow_evidence.py
- manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py
- manage-us-stock-strategy/scripts/kiwoom_broker_shadow.py
- manage-us-stock-strategy/scripts/manual_data_guards.py
- manage-us-stock-strategy/scripts/reconcile_broker_state.py

임시 줄을 지운 뒤 같은 명령을 다시 돌려 42건 통과를 확인했다(아래 (c)). 임시 줄 제거 후 `git diff --ignore-cr-at-eol --stat`도 29줄 추가·3줄 삭제로 같다.

## (c) 시험 결과 마지막 3줄
```
Ran 42 tests in 0.298s

OK
```
명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_v2_6_7_session_aware_kiwoom_priority.py"` (지시문 그대로, 앞에 옵션 없음). 첫 실행은 결과만 보려고 끝에 `tail`을 붙였다(지시문의 "파이프 금지"를 어김). 같은 명령을 그대로 다시 돌려 위 결과를 얻었다. 두 번 모두 42건 통과.

## (d) 그 밖의 오류가 0인 것을 확인한 방법
두 시험 안의 `assertEqual(others, [])`가 실행되어 통과했다. `others`는 `implementation hash mismatch: ` 접두사로 시작하지 않는 오류 전부이므로, 스키마·정책 해시·source registry·범위 해시·전환 상태·불변식·source artifact 해시 오류가 하나라도 있으면 실패한다. 접두사 검사는 도우미 한 곳에만 있고, 접두사는 검증기 76행의 문자열과 같다.

## (e) `git diff --ignore-cr-at-eol --stat`
```
 .../test_v2_6_7_session_aware_kiwoom_priority.py   | 32 ++++++++++++++++++++--
 1 file changed, 29 insertions(+), 3 deletions(-)
```
줄바꿈을 포함한 `git diff --stat`은 326 추가·300 삭제로 보인다. 편집 도구가 파일 전체를 LF로 바꿨기 때문이며, 지시문 1-1항이 허용한 예외다. 실제 내용 변경은 위 29줄 추가·3줄 삭제다. 다른 파일은 바뀌지 않았다(이 보고서 제외).

주문·권한 표지: 표지 없음. 수량·금액: 적지 않음.
