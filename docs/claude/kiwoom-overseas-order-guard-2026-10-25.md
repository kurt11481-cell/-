---
id: kiwoom-overseas-order-guard-2026-10-25
type: audit
status: current (읽기 전용 코드 확인, 키움 도구·CLI 실행 0건, 패키지 수정 0건)
as_of: 2026-10-25
summary: "키움 CLI가 미국주식 주문(overseas orders buy/sell/modify/cancel = ust20000~20003)을 --confirm으로 실제 전송하는가 — 예. server.py 주석이 틀렸고 CSV가 맞다. 추가로 kiwoom_order_preview도 options로 --confirm을 넣으면 실제 전송된다."
source_decision: "kiwoom-block 보강안 ④ (사장 '보강안 4개 진행', 2026-10-25), docs/claude/kiwoom-order-block-review-2026-10-25.md 1절 29행 확인 필요 항목"
consumers: "사장 · kiwoom-block Judge(J5) · 키움 MCP 주석/코드 수정을 정할 사장 결정 · docs/claude/kiwoom-block-builder-report.md"
authority: "order_authority=false · quantity_authority=none"
---

# 결론
1. **`--confirm`으로 실제 전송이 되는가: 예.** 설치된 `kiwoom_cli`는 `overseas orders buy/sell/modify/cancel`(ust20000~20003)을 `coverage=guarded`로 읽고, `guarded` + `order_write` + `--confirm`이면 안전 검사를 통과해 `/api/us/ordr`로 요청을 보낸다. CLI 층에서 해외 주문을 막는 코드는 없다.
2. **주석과 CSV 중 맞는 쪽: CSV(`guarded`).** `server.py` 271~272행 "Overseas order writes stay blocked by the CLI even with --confirm while coverage is preview-only"는 지금 설치본과 맞지 않는 옛 주석이다. CSV 비고에도 "Guarded after real-call CLI round-trip verification"이라고 적혀 있다.
3. **새로 찾은 경로: `kiwoom_order_preview`도 실제 주문을 낼 수 있다.** 미리보기 도구는 `options`를 그대로 CLI 플래그로 바꾸므로 `options={"confirm": true}`(또는 키 `-confirm`/`--confirm`)이면 `--confirm`이 붙어 실제 전송된다. 도구 설명 "no order is ever submitted under any condition"(server.py 257행)과 `readOnlyHint: True`(293~294행)는 코드와 맞지 않는다. 이 도구는 스위치 `KIWOOM_MCP_ALLOW_ORDERS=1`일 때만 생긴다(server.py 252행).
4. 따라서 Claude 쪽에서 이 경로들을 막는 층은 경로마다 다르다. **`kiwoom_cli`와 런타임 패키지(`kiwoom`)는 `KIWOOM_MCP_ALLOW_ORDERS`를 읽지 않는다**(`C/**`·`K/.venv/Lib/site-packages/kiwoom/**` grep `ALLOW_ORDERS|KIWOOM_MCP`(대소문자 무시) 0건. 이 스위치를 읽는 곳은 `K/src/kiwoom_exec_mcp/config.py` 23·68행과 이를 쓰는 `server.py` 252행 `if SETTINGS.allow_orders:`뿐이다). 그래서:
   - **스위치 ①은 MCP 주문 도구만 막는다.** 스위치 `0`이면 `kiwoom_order_submit`·`kiwoom_order_preview`가 생기지 않는다. MCP 쪽은 이 스위치 + deny `mcp__*__kiwoom_order_submit`(기존)·`mcp__*__kiwoom_order_preview`(②) + 훅(③)이 막는다.
   - **CLI 경로(셸에서 `kiwoomcli`·`python -m kiwoom_cli`)는 스위치와 무관하다.** 이 경로를 막는 것은 deny `Bash(*overseas orders*)`·`PowerShell(*overseas orders*)` 2줄(②) + 주문 표지 훅(③) + 지침뿐이다. 국내 주문(`domestic orders`)은 deny에도 없어 훅과 지침뿐이다. CLI 자체는 막지 않는다.

# 근거 (원문 file:line, 이 세션에서 읽음)
경로 앞부분: `K = .runtime-cache/kiwoom-mcp-20260928/mcp_exec` (본 저장소 작업 폴더, git 미추적), `C = K/.venv/Lib/site-packages/kiwoom_cli`.

| 단계 | 원문 | 내용 |
|---|---|---|
| 명령 등록 | `C/maps/api_commands.csv` 286~289행 | ust20000~20003, `command_path=kiwoomcli overseas orders buy/sell/modify/cancel`, `status=implemented`, `coverage_status=guarded`, `safety_policy=order_write`, `path=/api/us/ordr`, 비고 "Guarded after real-call CLI round-trip verification (… on zero-balance account)" |
| CSV → 정의 | `C/registry.py` 13·43~45·78~91행 | `api_commands.csv`를 읽어 `coverage_status=row["coverage_status"]`로 그대로 씀(덮어쓰기 없음) |
| `--confirm` 플래그 | `C/commands/orders.py` 113~120·145~153행 | `overseas` 시장의 쓰기 명령 4개에 `--confirm`(store_true) 추가 |
| 전송 분기 | `C/commands/orders.py` 177~190행 | `args.confirm`이 거짓이면 미전송 확인만 출력, 참이면 `execute_rest_command(..., confirm=True)` |
| 안전 검사 | `C/safety.py` 9~20행 | `planned`면 차단(10행), `preview-only`면 차단(16~17행), `order_write`인데 confirm 없으면 차단(19~20행). **`guarded` + confirm이면 어느 조건에도 안 걸림** |
| 실제 호출 | `C/executor/rest.py` 30~38행 | `enforce_before_request` 통과 뒤 `client.fetch_page(api_id, path, method, body)` |
| 런타임 쪽 차단 | `K/.venv/Lib/site-packages/kiwoom/**/*.py` grep `ordr|order_write|allow_orders` | 일치 0건 — 런타임 패키지에 주문 경로 차단 없음 |
| 도움말 문구 | `C/argument_maps.py` 259~265행 | `order_write`이고 `preview-only`가 아니면 "--confirm 없이는 … 미전송 주문 확인만" — 즉 `--confirm`이면 전송. CSV와 일치 |
| 약어 플래그 | `C/main.py` 22~24·28~29행 | `allow_abbrev=False`, 하위 파서도 같은 클래스 → `--conf` 같은 줄임 플래그는 안 받음(훅이 `--confirm` 전체만 봐도 됨) |
| MCP 제출 도구 | `K/src/kiwoom_exec_mcp/server.py` 252·265~287행 | 스위치가 켜졌을 때만 등록. `confirm=true`면 `_execute(..., confirm=True)` |
| 틀린 주석 | 같은 파일 271~272행 | "Overseas order writes stay blocked by the CLI even with --confirm while coverage is preview-only" — 설치본 CSV는 `guarded` |
| MCP 미리보기 도구 | 같은 파일 254~263·293~294행 | `_guarded_query(command_path, options, ORDER_POLICIES)`; 설명 "no order is ever submitted under any condition", `readOnlyHint: True` |
| options → 플래그 | 같은 파일 114~122·142~147행, `K/src/kiwoom_exec_mcp/runner.py` 190~202행 | `args = [*parts, *options_to_args(options)]`; `options_to_args`는 키를 `--{key.replace('_','-').lstrip('-')}`로 바꾸고 값이 `True`면 플래그만 붙임 → `{"confirm": true}` = `--confirm` |
| `kiwoom_query` | 같은 파일 36·207~217행 (`READ_POLICIES`는 36행, `kiwoom_query`는 207~217행; 거절하는 `_guard`는 79~97행) | `READ_POLICIES`만 받음 → `order_write` 명령은 `_guard`에서 거절. 읽기 명령에는 `--confirm` 인자가 없어 넣어도 인자 오류 |
| 환전 신청 | `C/maps/api_commands.csv` 314행 | `overseas exchange request`(ust31302)도 `guarded`·`order_write`·`--confirm`이면 전송 — 주문은 아니지만 같은 패턴. 훅의 `--confirm` 표지가 셸 경로를 막음 |

확인하지 않은 것: 키움 서버가 이 계좌에서 주문을 실제로 접수하는지(계좌·인증 상태). 이 문서는 "CLI가 요청을 보내는가"만 판단한다. 실제 실행은 하지 않았다.

# 제안 문구 (패키지는 고치지 않음 — 사장 결정 사항)
설치 패키지를 바꾸는 일이라 이 작업 범위 밖이다. 고친다면 아래처럼 바꾸는 안을 낸다.
- server.py 271~272행 주석:
  `Overseas order writes (overseas orders buy/sell/modify/cancel, coverage=guarded) are submitted with --confirm exactly like domestic ones; the CLI blocks only coverage=preview-only commands.`
- server.py 257행 설명:
  `Runs without --confirm, but options are passed to the CLI as flags: an options key "confirm" would add --confirm and submit a real order.`
- (코드 안, 사장 결정 시) `kiwoom_order_preview`와 `_execute`에서 `options`의 confirm 계열 키를 버리거나 거절하고, 미리보기 도구의 `readOnlyHint`를 `False`로. 이 변경은 키움 패키지 수정이라 별도 K3 대상.

# 바뀔 조건
- 설치본이 바뀌어 CSV 286~289행이 `preview-only`가 되거나 `safety.py`에 `guarded` 해외 주문 차단이 생기면 결론 1이 "아니오"로 바뀐다.
- `options_to_args`가 confirm 키를 거르도록 바뀌면 결론 3이 사라진다.
- 실제 호출 시험은 주문 권한 밖이라 하지 않는다. 결론은 코드 읽기에만 기대며, 위 원문이 바뀌지 않는 한 유지된다.
