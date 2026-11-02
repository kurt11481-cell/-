---
id: acc-implhash2-builder-prompt
title: "키움 Acceptance 시험 2개를 T1 뒤 구현 파일 변경에 맞추기 — acc-implhash2 (acc-implhash 재시도)"
date: 2026-11-02
class: "general(개발 큐 일반 작업). 기존 단언을 바꾸므로 사장 결정 기록 있음"
source: "사장 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9BrPM94W22naif7qV4EC7RF '둘 다 승인, 오늘 진행'(2026-11-02 19:53:58 KST, 계정=사장), 수정안 docs/claude/basefail-cleanup-proposal-2026-11-02.md ④·정정"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 목표
test_v2_6_7_session_aware_kiwoom_priority.py의 두 시험은 지금 실패한다. 현재 Acceptance(835d4f46)가 10/07의 구현 파일 해시를 들고 있고, 키움 pin이 T1(CLAUDE.md 83~86행)으로 폐지된 뒤 구현 파일 10개가 바뀌었기 때문이다. 두 시험이 이 차이만 따로 보고, 나머지 검사는 그대로 엄격하게 하도록 고친다.
- `test_extended_provider_scope_candidate_validates_without_activation`(310행 부근)
- `test_guarded_priority_requires_locked_acceptance_manifest`(425행 부근)

## 바꿀 파일 (이 2개만)
- manage-us-stock-strategy/tests/test_v2_6_7_session_aware_kiwoom_priority.py
- docs/claude/acc-implhash2-report.md (보고)

## 구현 요구
1. 이 시험 파일 안에 작은 도우미를 둔다(예: `split_implementation_drift(errors, manifest)`). 이 도우미는 오류 목록을 두 갈래로 나눈다. 하나는 `implementation hash mismatch: <경로>` 오류이고, 다른 하나는 그 밖의 오류다.
2. 두 시험은 실제 manifest를 지금처럼 그대로 검증한다. 사본을 만들거나 해시를 다시 채우지 않는다. 검증기가 manifest 해시를 정책 묶음과 대조하기 때문이다(validate_kiwoom_session_aware_acceptance.py 25행).
3. 두 시험은 아래 둘을 단언한다.
   - (가) 그 밖의 오류는 `[]`이다.
   - (나) 구현 해시 오류의 경로는 모두 manifest `implementation_hashes`의 키 안에 있다.
4. 검증기(validate_kiwoom_session_aware_acceptance*.py)·Acceptance·정책·다른 시험·다른 단언은 바꾸지 않는다. skip을 더하지 않는다.
5. 같은 클래스의 다른 시험(`validate_scope_mutation`을 쓰는 assertIn 시험들)은 그대로 둔다.

## 시험
- 실행 명령은 이 한 줄만, 글자 그대로 쓴다: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_v2_6_7_session_aware_kiwoom_priority.py"`
- 앞에 환경 변수나 옵션을 붙이지 않는다. 전체 스위트와 기준선 비교는 파이프라인이 한다.
- git은 status·diff·log만 쓴다. `python -c`·PowerShell·파이프는 쓰지 않는다.
- 기대 결과: 42건 모두 통과.

## 지켜야 할 것
1. 위 2개 파일 밖은 손대지 않는다.
1-1. 줄바꿈 예외(acc-implhash 1차 BLOCKED 원인): 이 시험 파일은 git에 CRLF·LF가 섞인 채(i/mixed) 저장돼 있고, 편집 도구가 파일 전체를 LF로 바꾼다. 이 파일만은 **전체 LF로 바뀌어도 된다**(이 파일의 원본 바이트 해시를 쓰는 곳 없음, 2026-11-02 grep). 줄바꿈 때문에 멈추지 않는다. 대신 보고서에 `git diff --ignore-cr-at-eol --stat` 결과를 적어 실제 내용 변경 줄 수를 보인다. 다른 파일의 줄바꿈은 지킨다.
2. 단언을 약하게 만들거나 지우지 않는다. 바꾸는 것은 두 시험에서 오류 목록을 위처럼 두 갈래로 나누는 것뿐이다.
3. 주문·키움·일지·원장·예약과 무관하다. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음. 비밀(.env*·토큰·계좌번호)을 읽지 않는다.
4. 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/acc-implhash2-report.md
- (a) 바꾼 줄(파일:행)
- (b) 지금 나오는 구현 해시 어긋남 경로 목록(경로만)
- (c) 시험 결과 마지막 3줄
- (d) 그 밖의 오류가 0인 것을 어떻게 확인했는지
- (e) `git diff --ignore-cr-at-eol --stat` 결과(줄바꿈을 빼고 본 실제 변경 줄 수)

수량·금액은 적지 않는다. 주문·권한 표지 문자열도 적지 않고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 허용 파일 2개뿐이다. 시험 파일의 줄바꿈이 전체 LF로 바뀐 것은 허용한다. 내용 변경은 `git diff --ignore-cr-at-eol`로 본다.
2. 두 시험만 바뀌었고, 실제 manifest를 그대로 검증한다(사본·해시 다시 채우기 없음).
3. 구현 해시 오류만 따로 떼고, 그 밖의 오류 `[]`와 경로가 `implementation_hashes` 키 안에 있는지를 실제로 단언한다(항상 참 단언 아님).
4. 검증기·다른 시험·단언·skip 변경 없음.
5. 새 실패 0(파이프라인 checks). 기준선 대비 이 두 시험이 통과로 바뀜.
6. 보고서 (a)~(e) 있음, 수량·금액·표지 없음.

```dev-run
{"task_id": "acc-implhash2", "class": "general", "builder_model": "sonnet", "builder_effort": "high", "max_turns": 80, "builder_timeout_min": 45, "allowed_paths": ["manage-us-stock-strategy/tests/test_v2_6_7_session_aware_kiwoom_priority.py", "docs/claude/acc-implhash2-report.md"], "target_tests": ["test_v2_6_7_session_aware_kiwoom_priority.py"], "commit_message": "test(kiwoom): separate post-T1 implementation hash drift from other Acceptance errors in two v2.6.7 tests (acc-implhash2)"}
```
