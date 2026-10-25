---
id: kiwoom-order-block-review-2026-10-25
type: audit
status: current (읽기 전용 검토, 키움 도구 호출 0건, 설정 수정 0건)
as_of: 2026-10-25
summary: "claude-settings-audit의 확인 필요 2건 — 키움 MCP 실제 도구 이름과 주문 기능 위치, 저장소 deny가 이 원격 스레드에 적용되는지."
source_decision: "사장 '확인 필요사항 2개 검토' (2026-10-25 10:39Z)"
consumers: "사장 · 사장실 코디네이터 · (보강 시) K3 Builder/Judge"
authority: "order_authority=false · quantity_authority=none"
---

# 결론
1. **`kiwoom_order_submit`은 올바른 주문 도구 이름이다.** 다만 지금 이 PC의 키움 MCP는 읽기 3개(`kiwoom_commands`, `kiwoom_help`, `kiwoom_query`)만 노출하고, 주문 도구 2개는 **운영자가 환경값 `KIWOOM_MCP_ALLOW_ORDERS=1`을 켰을 때만 생긴다.** 그러므로 deny는 "그 스위치가 켜질 때"의 2중 방어선이고, 지금은 걸릴 대상이 없는 게 정상이다.
2. **읽기 3개 도구로는 주문이 안 나간다**(소스로 확인). `kiwoom_query`는 주문 명령을 코드에서 거절한다.
3. **진짜 구멍 후보는 도구가 아니라 CLI 직접 호출이다.** 미국주식 주문 명령(`overseas orders buy/sell/modify/cancel`)이 키움 CLI에 `guarded`로 등록돼 있고, 소스의 "해외 주문은 preview-only라 막힘" 주석이 CSV와 맞지 않는다. 셸에서 CLI를 직접 부르는 경로는 deny에 없다 → **확인 필요 + 보강 권장.**
4. **저장소 deny가 이 원격 스레드에 적용되는지는 여전히 확인 필요**(읽기만으로는 증명 불가). 구조상 **적용되지 않을 가능성이 높다**고 본다. 사장이 안전하게 확인하는 방법을 5절에 적었다.

# 1. 실제 도구 이름과 주문 기능 위치 (원문)
| 사실 | 원문 위치 |
|---|---|
| 읽기 3개 + 문서 서버 4개(`spec_groups`, `spec_search`, `spec_show`, `get_example`) | manage-us-stock-strategy/references/kiwoom-mcp-local-integration.md 34행 |
| 주문 도구 `kiwoom_order_preview`, `kiwoom_order_submit`은 `if SETTINGS.allow_orders:` 안에서만 등록 | .runtime-cache/kiwoom-mcp-20260928/mcp_exec/src/kiwoom_exec_mcp/server.py 252~287행 |
| 스위치 = 환경값 `KIWOOM_MCP_ALLOW_ORDERS`, **정확히 `1`일 때만** 켜짐(`true`/`yes`는 꺼짐) | 같은 폴더 config.py 9·23·68행 |
| 2026-09-29 설정 점검: 실전(real) 모드, 주문·디버그 헤더 `0`, 프로필 미선택 | kiwoom-mcp-local-integration.md 63~70행 |
| 과거(2026-09-30) Cowork 세션에는 주문 도구 2개가 노출된 적이 있었음 → 그 뒤 스위치를 끈 것으로 보임(경위는 확인 필요) | docs/claude/system-review-phase1-2026-09-30.md 37·300행 |
| `kiwoom_query`는 `READ_POLICIES = {read, account_read}`만 허용, `order_write`는 "only accepts …" 오류로 거절 | server.py 37·79~98·207~217행 |
| `kiwoom_commands`는 번들 CSV만 읽음(네트워크 없음) | server.py 도구 주석 `openWorldHint False`, 연동 문서 34행 |
| 미국주식 주문 명령 4개: `overseas orders buy/sell/modify/cancel` = ust20000~20003, `safety_policy=order_write`, `status=implemented`, `coverage=guarded` | .venv/.../kiwoom_cli/maps/api_commands.csv |
| 주석 "해외 주문은 preview-only 동안 CLI가 막음" ↔ CSV는 `guarded` | server.py 271~272행 ↔ csv ust20000 줄. **어느 쪽이 맞는지 확인 필요**(`safety.py`·`argument_maps.py`가 `guarded`일 때 `--confirm`으로 실제 전송을 허용하는지 코드로 더 읽어야 함) |

따라서 질문 "주문 기능이 어느 이름에 있나": **지금 노출된 3개에는 없다.** 주문은 (a) 스위치를 켜면 생기는 `kiwoom_order_submit`(+`confirm=true`), (b) 셸에서 직접 `kiwoomcli overseas orders … --confirm`, 두 경로에만 있다. (a)는 소스 주석도 "confirm은 AI가 켤 수 있고, 사람 승인은 클라이언트의 도구 승인에 달려 있다"고 적는다(server.py 274~275행).

# 2. deny가 이 원격 스레드에 적용되는가
- 확정 못 한 이유: 이 스레드의 도구는 `mcp__remote-devices__*`(파일·셸·Desktop Commander·화면 조작)이고, 저장소 `.claude/settings.json`의 규칙은 `Bash(...)`, `PowerShell(...)`, `Edit(...)`, `Read(...)` 이름으로 쓰여 있다. 이 도구들이 PC의 Claude Code 권한 엔진을 거치는지 보여 주는 문서나 설정을 이 저장소에서 찾지 못했다. 공식 설명("로컬 스레드는 PC 설정·훅·권한을 적용받는다")과 이 세션의 도구 구성이 일치하는지는 시험이 있어야 안다.
- 내 판단(근거 약함): 규칙 이름이 도구 이름과 달라 **적용되지 않을 가능성이 높다.** 그렇다면 이 스레드를 막는 것은 지침 문장과 키움 MCP 쪽 코드 방어(1절)뿐이다.
- 이 스레드가 한 일에서 얻은 약한 증거: 이 세션에서 deny에 걸리는 동작을 시도한 적이 없어 증거 없음.

# 3. 구멍이면 — 보강안 (K3 대상, 이 문서는 적용하지 않음)
강화만 한다(허용 범위를 넓히지 않음). 순서는 효과가 큰 순.
1. **키움 쪽 스위치 확인·고정**(사장 확인, 4절 B): `KIWOOM_MCP_ALLOW_ORDERS`가 지금 `0`인지.
2. **deny 추가**: `mcp__*__kiwoom_order_preview`, `Bash(*overseas orders*)`, `PowerShell(*overseas orders*)`, `Bash(*kiwoomcli*)`/`PowerShell(*kiwoomcli*)`(루틴 조회는 MCP `kiwoom_query`와 저장소 브리지를 쓰므로 영향이 작을 것으로 보나 영향 범위 확인 필요).
3. **주문 표지 훅(PreToolUse)**: 요청에 `/api/us/ordr`, `ust20000`~`ust20003`, `--confirm`이 있으면 거절. MCP 도구에 훅이 걸리는지는 확인 필요.
4. **원격 도구에도 걸리게 하는 방법**은 2절 시험 결과에 따라 정한다(규칙이 안 걸리면 PC 쪽 설정이 아니라 키움 MCP 서버 쪽 방어(1번)와 지침이 유일한 선).
5. **주석/CSV 불일치 해소**: 해외 주문이 CLI에서 실제로 막히는지 코드(`safety.py` 16·29행, `argument_maps.py` 260~266행)로 확인한 뒤 결과를 문서에 고정.
- 어느 것도 `.claude`·`tools/**` 수정이라 Claude 세션이 직접 하지 않는다. 사장이 직접 하거나 K3(Opus Judge + 사장 승인).

# 4. 사장이 직접 할 수 있는 안전한 확인 (한 단계씩, 주문 없음)
**A. 스위치 확인 (읽기만, 값은 화면에 두지 않음)**
1. Claude 데스크톱 앱 설정에서 키움 실행 MCP 서버(`kiwoom_exec`)의 환경값 목록을 엽니다. 정확한 메뉴 이름은 **확인 필요**이니, 못 찾으면 화면만 알려 주세요.
2. 환경(env) 목록에서 `KIWOOM_MCP_ALLOW_ORDERS`가 **없거나 `0`** 인지만 봅니다. 앱ID·시크릿 값은 열지도 복사하지도 마세요.
3. 결과를 "없음/0/1" 한 단어로 알려 주세요.

**B. 규칙이 이 스레드에 걸리는지 (무해한 시험)**
1. 사장이 메모장으로 `E:\사업\##금동한\코덱스저장소\docs\claude\_probe-deny.txt`를 만들고 글자 `probe` 한 줄을 씁니다(비밀 없음).
2. 사장 본인이 `.claude\settings.json`의 `deny` 맨 끝에 한 줄 `"Read(./docs/claude/_probe-deny.txt)"`를 넣습니다(쉼표 주의). 이 줄은 시험이 끝나면 지웁니다.
3. 이 스레드에 "probe 파일 읽어봐"라고 말합니다. 저는 파일 도구로 읽기만 시도합니다.
4. 읽히면 → **규칙이 이 스레드에 적용되지 않음**(2절 판단 확정). 막히면 → 적용됨. 어느 쪽이든 3단계에서 위험한 일은 없습니다.
5. 끝나면 2번의 줄과 `_probe-deny.txt`를 지웁니다.

# 5. 이 검토가 하지 않은 것
키움 도구 호출(`kiwoom_commands` 포함) 0건, 인증·토큰 접근 0건, `.env`·전역 설정·`.runtime-cache/private-data` 읽기 0건, 설정 수정 0건. 읽은 곳: 연동 문서, 설치된 `mcp_exec` 소스(server.py·config.py), 설치된 `kiwoom_cli`의 CSV와 grep 결과 줄.

검토 완결: 원문 확인 server.py 30~98·207~290행 · config.py 9~68행 · api_commands.csv(ust20000~20003, ust21050 등) · 연동 문서 전체 · system-review-phase1 37·300행 · 내장 재검토 없음(권한 변경 제안 없음, 보강안은 K3 대기) · 미해결: 스위치 현재값, 해외 주문 CLI 차단 여부, 규칙 적용 여부 · 자료 시점 2026-10-25 · 바뀔 조건: 스위치가 1로 확인되거나 B 시험에서 규칙이 걸리는 것으로 나오면 3절 우선순위를 다시 본다.
