---
id: ust21100-fix-builder-prompt
title: 계좌 읽기 브리지 ust21100(미국주식 거래내역) 요청 본문 — 필수 필드 krw_repl_skip_yn 빈 값 수정
date: 2026-10-13
class: 권한 경로(kiwoom_*bridge*.py) 버그 수정(dev-run class authority — 경로 때문. 의미상 권한·한도·주문 단계 불변, 읽기 전용 조회 본문 한 칸)
source: docs/claude/redesign-t2-firstrun-report-2026-10-13.md 9·10절 · 실측 docs/claude/ust21100-diag-2026-10-13.py(2026-10-13 10:26 KST, 사용자 실행)
authority: order_authority=false · quantity_authority 값 변경 없음 · 주문 경로 없음 · 정책·상태 파일 쓰기 없음 · 키움 호출은 기존 읽기 전용 조회 그대로
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 ust21100-fix -ApproveAuthority — 경로 때문에 붙는 플래그. 다른 dev-run이 돌고 있으면(_lock) 병합하지 않는다)
---

```dev-run
{"task_id": "ust21100-fix", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 60, "builder_timeout_min": 40, "allowed_paths": ["manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py", "manage-us-stock-strategy/tests/test_kiwoom_account_bodies.py", "docs/claude/ust21100-fix-report.md"], "target_tests": ["test_kiwoom_account_bodies*.py", "test_s1b*.py", "test_broker_visibility_audit*.py", "test_kiwoom_broker_shadow*.py", "test_reconcile_broker_state*.py", "test_auto_core*.py"], "commit_message": "fix(kiwoom bridge): ust21100 sends krw_repl_skip_yn=N (server requires it; empty value returned 1511)"}
```

## 목표

자동 운영 코어 daily가 2026-10-13 두 번(08:46, 10:13 KST) 모두 I1에서 멈췄다: `REQUIRED_READ_NOT_PASS:account_transaction_history_read:…:KIWOOM_API_RESPONSE_ERROR:2`. 원인은 브리지가 ust21100에 보내는 본문의 한 칸이다. 그 칸만 고치고 회귀 테스트를 넣는다.

## 실측 (2026-10-13 10:26 KST, 같은 런타임·같은 토큰, 기간 20261010~20261013)

| 본문 | return_code | return_msg |
|---|---|---|
| 브리지 그대로(tp "0", krw_repl_skip_yn "") | 2 | 입력 값 오류입니다[1511:필수 입력 값에 값이 존재하지 않습니다. 필수입력 파라미터=krw_repl_skip_yn] |
| krw_repl_skip_yn "N" | 20 | [2000](501724:관련자료가 없습니다) — 브리지가 이미 "내역 없음"으로 통과시키는 응답 |
| tp "", krw_repl_skip_yn "N" | 2 | …[1511:… 필수입력 파라미터=tp] |

- 키움 명세(ust21100)는 두 칸 모두 required "N"이고 예시도 빈 값이지만, 실제 서버는 필수로 다룬다. stex_tp·stk_cd 빈 값은 통과한다.
- "N" = 원화대용입출금 **비제외**(모두 포함). kiwoomcli 기본값과 같고, S7 U3 실측(2026-10-02)과 cash_flow_evidence가 전제한 조회와 같다.

## 바꿀 것

1. `manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py` `ACCOUNT_BODIES["account_transaction_history_read"]`의 `"krw_repl_skip_yn": ""` → `"N"`. 그 밖의 칸·다른 조회 본문·SAFE_FIELDS·no-data 판정·페이지 처리·검증은 바꾸지 않는다.
2. 그 줄 위에 주석 1~2줄(ASCII): 2026-10-13 실측, 서버가 tp·krw_repl_skip_yn을 필수로 다룸(1511), "N" = 비제외 = kiwoomcli 기본.
3. (Cowork가 이 지시문 아래 "추가 실측" 절을 채우면 그 절의 칸도 같은 방식으로 고친다. 절이 비어 있으면 1~2만.)

## 테스트 — 새 파일 `manage-us-stock-strategy/tests/test_kiwoom_account_bodies.py`

- `ACCOUNT_BODIES["account_transaction_history_read"]`에서 tp == "0", krw_repl_skip_yn == "N"(빈 값 금지).
- `request_body(validate_request({"operation": "account_transaction_history_read", "params": {"strt_dt": "20261010", "end_dt": "20261013"}}))` == 날짜 두 칸이 채워지고 나머지는 위 템플릿과 같은 dict.
- 나머지 조회 본문 전체(account_deposit_read … account_day_trades_read)가 변경 전 값과 같다(골든 dict로 고정).
- 키움을 실제로 부르는 테스트는 만들지 않는다.

## 지켜야 할 것 (어기면 Judge FAIL)

1. 바뀐 줄은 위 1·2(와 3에 적힌 칸)뿐. ACCOUNT_APIS(경로·API ID), DATED_PARAMETERS, SAFE_FIELDS, NO_DATA_* 표, 검증 함수, 워커 흐름 불변. 주문 경로 문자열(`/api/us/ordr`, `ust2000x`, `kiwoom_order`, `order_submit`) 없음.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`가 들어간 줄을 만들거나 바꾸거나 지우지 않는다.
3. 스크립트 ASCII만. 키움·auto_core.py·run_auto_core.ps1을 실행하지 않는다. Claude Code 설정상 "auto_core.py"가 들어간 명령은 거부되므로 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"`으로만 돌린다.

## 보고 `docs/claude/ust21100-fix-report.md`

바꾼 줄, 새 테스트, 대상 테스트 결과(Ran 수), 남은 위험(서버의 다른 숨은 필수 칸 — 실측 범위 밖).

## Judge 확인 항목

1. diff가 ust21100 본문 krw_repl_skip_yn "" → "N"(+주석, + "추가 실측" 절에 적힌 칸)뿐이다.
2. 새 테스트가 빈 값을 실제로 잡는다(되돌리면 실패).
3. 다른 조회 본문·경로·검증·no-data 판정 불변(골든 테스트).
4. 권한 표지 줄·주문 경로 변경 없음, 키움 호출 없음, 정책·상태 파일 변경 없음.
5. 대상 테스트 전부 통과, 기존 테스트 파일 무변경.

## 추가 실측

(Cowork가 bridge-dated-diag-2026-10-13.py 결과로 채운다. 비어 있으면 해당 없음.)
