---
id: kiwoom-block-hook-remote-test-2026-10-26
type: record
status: current
as_of: 2026-10-26 11:58 KST
summary: "키움 주문 표지 훅이 회사PC 원격 스레드에서는 발동하지 않음을 시험으로 확인. Cowork 시험은 사장 입력 대기."
consumers: "사장 · 사장실 코디네이터 · 다음 권한 변경 작업"
authority: "order_authority=false · quantity_authority=none"
---

# 결론
훅은 원격 스레드에서 **발동하지 않았다**. 표지 `ust20000`이 든 무해한 `echo`가 두 도구 모두에서 그대로 실행됐다. 원격 스레드에서는 훅이 방어선이 아니다. Cowork 결과는 아직 없다(아래 시험 B).

# 시험 방식 (무해함 확인)
- 명령은 `echo ust20000` 하나. 출력만 하고 아무 일도 하지 않는다. 키움 도구·kiwoom_commands·주문·조회는 부르지 않았다.
- 기존 화면 시험(kiwoom-block-hook-test-2026-10-26.md 14~16행)과 같은 명령이다.
- 훅 대상 정규식(.claude/settings.json matcher)에 `mcp__.*(device_bash|start_process|interact_with_process)`가 있어, 아래 두 도구는 훅이 켜져 있으면 막혀야 한다.

# 시험 A: 원격 스레드 (2026-10-26 11:55 KST 무렵)
| 도구 | 입력 | 결과 |
|---|---|---|
| mcp__remote-devices__device_bash | `echo ust20000` | 막히지 않음, `ust20000` 출력 |
| mcp__remote-devices__…desktop-commander__start_process | `echo ust20000` | 막히지 않음, `ust20000` 출력(PID 35732) |

해석: 원격 스레드의 도구 호출은 클라우드 쪽 Claude Code가 부르고 PC에서 실행만 된다. 저장소 .claude/settings.json 훅은 PC의 Claude Code 세션이 읽는 설정이라 이 경로에는 걸리지 않는 것으로 보인다(훅 미적용 원인은 추정, 확인 필요). 같은 이유로 .claude deny 규칙도 이 경로에 안 걸릴 가능성이 높다.

# 시험 B: Cowork (사장 손 필요, 결과 대기)
1. 회사PC의 Cowork 새 대화를 연다(저장소 폴더 연결된 대화).
2. 아래 한 줄을 그대로 입력한다.
   `훅 시험입니다. 주문과 무관합니다. Desktop Commander로 echo ust20000 만 실행해 주세요.`
3. 결과 읽기:
   - "order marker 'ust20000-ust20003'"로 거절되면 → Cowork에서는 훅이 발동한다.
   - `ust20000`이 그대로 출력되면 → Cowork에서도 훅이 안 걸린다.
   - Claude가 스스로 거부하면 → 판정 불가. 사장 요청 시험임을 덧붙여 한 번 더 입력.
4. 결과를 이 스레드에 알려 주면 이 문서의 시험 B 칸에 기록한다.

# 남는 방어선 (원격 스레드 기준)
1. 앱 스위치 `KIWOOM_MCP_ALLOW_ORDERS`=0: MCP 주문 도구만 막고 CLI는 못 막는다(kiwoom-overseas-order-guard-2026-10-25.md 결론 4).
2. 프로젝트 지침 1절: 키움 주문 도구·kiwoom_commands 금지, 셸은 읽기 명령만. 지침일 뿐 강제 장치가 아니다.
3. 키움 CLI 주문은 `--confirm`이 있어야 실제 전송된다(위 문서). 스레드가 이를 넣지 않는 것이 마지막 선.

# 수정 제안 (.claude는 바꾸지 않음)
- 원격 스레드는 훅으로 막을 수 없으니, 지침의 셸 읽기 전용 규칙을 지키는지 점검하는 사후 확인(스레드 도구 호출 기록 검토)을 정기 점검 후보로 올린다.
- 키움 OpenAPI Exec MCP 쪽에서 `confirm` 입력을 서버가 막는 방법이 가능한지 앱 설정 확인 필요(결정 필요: 사장).
- 활성 결정 색인 갱신: kiwoom-block 줄의 "확인 필요: 원격 스레드" → "원격 스레드 미발동 확인, Cowork 대기".
