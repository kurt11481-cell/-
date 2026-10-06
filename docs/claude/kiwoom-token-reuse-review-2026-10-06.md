---
id: kiwoom-token-reuse-review-2026-10-06
type: review
status: current
as_of: 2026-10-06
summary: 대조·수동 분석이 실행마다 키움 토큰을 새로 받아 kiwoomcli(MCP) 토큰을 무효로 만드는 원인 진단과 수정안. 수정 대상 kiwoom_runtime_bridge.py는 키움 acceptance 고정 파일이라 K3(사용자 승인 + Independent Judge 필요).
consumers: [docs/claude/s7-builder-report-2026-10-01.md 9번(매 세션 루틴), references/portfolio-exposure-review.md Routine 서두, 개발 관제판]
---

# 키움 토큰 재발급 문제 검토 (2026-10-06, Cowork, 코드 변경 없음)

## 1. 결론

- 대조 작업과 수동 분석에는 새 토큰이 **필요 없다.** 아직 유효한 토큰을 다시 쓰면 된다.
- 원인은 한 곳: `manage-us-stock-strategy/scripts/kiwoom_runtime_bridge.py` 354~359행 `_runtime_session`.
  - `get_auth(mode="real", token_store_kind="memory")` → 토큰을 파일에 저장하지 않는 메모리 저장소
  - `auth.refresh_access_token()` → 유효 여부와 상관없이 **실행할 때마다 새 토큰 발급**
  - 시장 데이터 브리지와 계좌 브리지(`kiwoom_account_readonly_bridge.py` 274행)가 같은 함수를 쓴다. 대조 propose·수동 분석이 실행될 때마다 새 토큰이 나온다.
- kiwoomcli(MCP 조회 포함)는 계좌 별칭(실전계좌) 파일 토큰을 쓴다. 같은 앱키로 새 토큰이 발급되면 저장된 토큰이 서버에서 무효가 되는 현상이 두 번 재현됐다(10/02 13:37, 10/06 09:37 return_code 3·메시지 8005). 서버 규칙 자체는 키움 문서에서 찾지 못함(확인 필요).

## 2. 부수 발견: kiwoomcli 자동 복구가 작동하지 않는 이유

- 런타임 `kiwoom/core/client.py` 84행은 return_code가 8005·8031·8103이면 토큰을 다시 받아 한 번 재시도한다.
- 실제 응답은 `return_code: 3`, 메시지 안에 `[8005:Token이 유효하지 않습니다]`라서 이 자동 복구가 걸리지 않는다. 그래서 사람이 `kiwoomcli auth login`을 해야 했다.
- 이것은 외부 공식 런타임(Kiwoom-REST-API) 쪽 문제다. 고치면 런타임 커밋이 바뀐다.

## 3. 수정안 (검토 순서 NO_CHANGE → REUSE)

| 안 | 내용 | 효과 | 변경 등급 |
|---|---|---|---|
| 0 절차만 | 지금처럼 kiwoomcli 작업을 먼저 하고, 브리지 실행 뒤 `kiwoomcli auth login` | 코드 무변경. 매번 사람 손이 필요하고, 다음 날 아침 예약 작업(현황판 등)이 8005로 실패할 수 있음(확인 필요) | K0 |
| **A 토큰 공유(권장)** | `_runtime_session`을 `get_auth(profile=<정책의 별칭>, token_store_kind="file")` + `auth.get_access_token()`으로 변경. 유효한 파일 토큰을 재사용하고, 만료 10분 전이거나 없을 때만 발급해 같은 파일에 저장 → kiwoomcli와 같은 토큰을 씀 | 재발급이 하루 1회 수준으로 줄고 서로 무효화하지 않음 | **K3**: 이 파일은 `kiwoom-acceptance-pin-scope.json` 고정 대상 → 현재 acceptance 무효, 재고정 필요. 정책 파일에 별칭 키 추가도 사용자 승인 필요 |
| B 자동 복구 보완 | 런타임 client가 return_code 3 + 메시지 8005도 인증 오류로 인식 | kiwoomcli가 스스로 복구. 단 복구할 때마다 새 토큰을 받으므로 A 없이 쓰면 서로 무효화하는 문제가 남음 | 외부 런타임 수정(런타임 커밋 변경) |

권장: **A만.** B는 A 적용 뒤에도 문제가 남을 때만 검토한다.

**사용자 결정(2026-10-06):** "A + 1회 자동 복구로 진행 승인" — 사용자 개입이 가장 적은 방식으로 선택. B(외부 런타임 수정)는 하지 않는다(런타임 커밋이 정책에 고정, 이득 작음). 1회 자동 복구는 브리지 안에서 공유 파일 토큰을 1번만 재발급·재시도한다. Builder 지시문: `kiwoom-token-reuse-builder-prompt-2026-10-06.md`.

## 4. A 적용 시 지켜야 할 것

- 별칭은 코드에 쓰지 않고 정책(`workspace/policies/kiwoom-readonly-policy.json`)에서 읽는다. 별칭이 없거나 자격 증명을 찾지 못하면 fail-closed(지금처럼 KIWOOM_API_UNAVAILABLE).
- 세션 중 8005가 나면 (사용자 결정 10/6) 브리지가 1번만 공유 파일 토큰을 재발급·재시도한다. 그래도 실패하면 지금처럼 회로 차단(fail-closed). 재발급 토큰은 공유 파일에 저장되므로 kiwoomcli를 깨지 않는다.
- 토큰 값·.env·키링 내용은 읽지도 출력하지도 않는다. 로그에는 "재사용/발급"만 남긴다.
- `.env`의 APP_KEY와 별칭 키링의 앱키가 같은지는 확인하지 않는다(비밀 정보). 다르면 별칭 쪽으로 통일되며, 첫 실행 뒤 kiwoomcli 조회 → 브리지 실행 → kiwoomcli 조회 순서의 실측으로 검증한다.
- 동시 실행 금지 규칙(브리지 실행 중 kiwoomcli 사용 금지)은 그대로 둔다.
- 대상 테스트: test_kiwoom_runtime_return_code.py, test_k2_bridge_evidence_integrity.py, test_reconcile_broker_state.py, test_kiwoom_broker_shadow.py + 새 단위 테스트(유효 토큰 재사용 시 발급 호출 0회, 만료 시 1회, 별칭 없음 fail-closed).

## 5. 실측 검증 (적용 뒤, 사용자 PC)

1. `kiwoomcli auth login` → 2번(토큰만 재발급)
2. MCP 미체결 조회 → 정상
3. 대조 propose 또는 수동 분석 1회
4. MCP 미체결 조회 → 8005가 없으면 통과
