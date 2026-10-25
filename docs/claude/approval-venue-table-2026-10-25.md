---
id: approval-venue-table-2026-10-25
type: reference
status: current
as_of: 2026-10-25
summary: "승인류별로 어디서 누가 무엇을 입력하는지 한 장 표. 규칙은 바꾸지 않고 안내만 모은 것 — 원본은 CLAUDE.md 해당 줄."
source_decision: "Projects 진단 결정 1·3 (사장 '권장안대로', 사장실 스레드 직접 입력, 2026-10-25 10:30Z)"
consumers: "사장 · 사장실 코디네이터와 회사PC 스레드 · 개발 관제판 안내 문구"
authority: "order_authority=false · quantity_authority=none · 규칙 변경 없음"
---

# 승인 입력 장소 표 (2026-10-25)

이 표는 **안내만** 모은 것이다. 규칙의 원본은 CLAUDE.md이고, 어긋나면 CLAUDE.md가 이긴다. 승인 한 건 = 바로 앞 제안 1건, 같은 날(KST), 1회. 코디네이터가 옮긴 문장·버튼·카드·예약 실행 안의 승인은 승인이 아니다(CLAUDE.md 64~66행).

## 표

| # | 승인 종류 | 어디서 | 누가 무엇을 입력 | 스크립트·명령 | 이 스레드(사장실 회사PC)가 하는 일 | 원본 |
|---|---|---|---|---|---|---|
| 1 | 권한·한도 변경 승인(주문 단계·한도·승인 상품·대사 불변식·킬 스위치) | 사장실 회사PC 스레드(대화형)에 직접, 또는 Cowork 대화 | 사장이 **직접 친** 메시지(하네스 표시 from=human trust=principal). 제안 1건에 대한 승인 | 없음(승인 문장만) | 승인 뒤 수동 경로 Builder(워크트리)와 별도 읽기 전용 Judge 시작 | CLAUDE.md 58~68행 |
| 2 | 권한 변경 병합 | 사장 본인 PowerShell(대화형 창) | `.\tools\dev-merge.ps1 <id> -ApproveAuthority` 한 줄 + 안내 뒤 Enter 한 번. 수동 경로는 `docs\claude\<id>-merge-*.ps1`(예: d124-merge-2026-10-25.ps1) | `dev-merge.ps1`, `<id>-merge-*.ps1` | 정확한 한 줄을 알려 줌. 실행하지 않음 | CLAUDE.md 62~63·69~71행, tools/dev_pipeline/README.md 4항 |
| 3 | 일반 변경 병합(READY_TO_MERGE, 권한 아님) | Cowork가 PC에서, 또는 사장 PowerShell | 별도 승인 문장 없음. `-ApproveAuthority`는 붙이지 않음 | `.\tools\dev-merge.ps1 <id>` | 결과 확인·보고만. 실행하지 않음(settings deny + CLAUDE.md) | CLAUDE.md 53~57행(dc-dev Q1 a) |
| 4 | 대조(reconcile) apply | Cowork 대화, 또는 사장 PowerShell | Cowork: `확인 <code>`(코드는 `show` 표의 그 제안 코드). 터미널: 같은 코드를 명령에 넣고 Enter 한 번 | `reconcile_broker_state.py show` → `apply --confirm <code> --confirmed-via COWORK_CHAT_USER_MESSAGE` 또는 `USER_TERMINAL` | **하지 않음.** 사장 Q1 "아니오" — Claude Code는 apply 금지 | CLAUDE.md 25~27행, broker-snapshot-reconciliation.md 2~3절 |
| 5 | 결정 일지 apply | Cowork 대화, 또는 사장 PowerShell | 사장의 결정 메시지 원문. 코드는 그 제안 것만 | `portfolio_review_journal.py show` → `apply … --confirmed-via COWORK_CHAT_USER_MESSAGE` 또는 `USER_TERMINAL` | **하지 않음.** 일지 쓰기·편집 금지 | CLAUDE.md 28~34행, portfolio_review_journal.py 머리말 |
| 6 | 정책·상태 변경, decision_mode "켜" | Cowork 대화 | 사장의 명시 승인 메시지 | 변경별로 다름 | **하지 않음**(프로젝트 지침 4절). 사장실 스레드 직접 입력이 이 종류에도 인정되는지는 **확인 필요** — CLAUDE.md 64행은 "In this item"(권한·한도 항목)에만 적용 | CLAUDE.md 35~36행, 지침 4절 |
| 7 | 예약 작업 만들기·바꾸기·지우기 | 사장실 스레드(대화형), 또는 사장이 직접(claude.ai 예약 작업 화면·Cowork) | 사장이 이 스레드에 **직접 친** `예약 작업 변경 승인: <이름>` 한 줄(바로 앞 제안 1건, 같은 날 KST, 1회, 작업 하나당 1건). 컴퓨터 연결 예약은 사장 PC에 뜨는 승인 창을 사장이 직접 누름 | `update_trigger`·`create_trigger`·`delete_trigger` (이 스레드가 호출) | 제안(지금·바꿀 sha256, diff, 일정·모델·폴더·권한 불변, 되돌리기) → 승인 뒤 호출 → 지시문 보관·README 갱신 → 첫 실행 산출물 확인. 주문·키움 주문 도구·apply·정책/상태 쓰기·예약이 예약을 바꾸는 지시문·권한 모드 상향·폴더 추가는 승인으로도 불가 | 지침 v1.8 4절, schedule-dashboard-redesign-2026-10-25.md 4절 |
| 8 | 스레드 권한 창(도구 사용 허용) | 그 스레드 화면 | 필요한 한 건만 "허용". **"이 스레드 전체 허용"은 고르지 않는다** | — | 막히면 무엇이 필요한지 쓰고 멈춤 | 지침 4절 |
| 9 | 개발 관제판 "결정함" 답(승인류 아님) | 사장실 스레드 또는 Cowork 대화 | `결정 <작업 id>: …` 한 줄 | — | 받은 세션이 결정 문서에 기록하고 관제판을 갱신 | dev-dashboard-protocol.md 3·4절 |

## 쓰는 법 (초보자용, 한 번에 한 단계)
1. 알림이 "승인이 필요하다"고 하면 위 표에서 **그 종류의 줄**을 찾는다.
2. "어디서" 칸의 장소를 연다(사장실 스레드 / Cowork / PowerShell).
3. "누가 무엇을 입력" 칸의 문장을 **직접 친다**. 복사해 붙인 코디네이터 문장은 승인이 아니다.
4. 코드는 알림이 보여 준 **그 제안의 코드**만 쓴다. 지어내거나 이전 코드를 다시 쓰지 않는다.

## 아직 어긋난 곳 (이 문서가 고치지 않는 것)
- 프로젝트 지침 v1.7 4절은 "승인류는 이 프로젝트에서 실행하지 않는다"로 되어 있어 표 1번(사장실 스레드 직접 입력 인정)과 읽는 방식이 다르다. 안전한 쪽(실행하지 않음)이라 막히지는 않지만, D5·D8 지침 문구 정리에서 같이 맞춘다(d5-d8-instruction-wording-draft.md).
- 개발 관제판 화면의 "Cowork 대화에 보내세요" 문구는 이번 세션에서 이 표를 가리키도록 고친다(보고 참고).

## 함께 기록하는 결정 (사장 '권장안대로', 2026-10-25 10:30Z)
- 결정 1 예: 승인 장소 표 작성 + 관제판 옛 문구 수정. 승인 규칙은 그대로.
- 결정 2 조사 먼저: 회사PC `.claude` 규칙 읽기 전용 조사 → `claude-settings-audit-2026-10-25.md`. 넣는 일은 사장 본인 또는 K3.
- 결정 3 원클릭 파일만 일반 변경으로 개발 큐 등록(`approve-1click`). **Builder·Judge를 로컬 스레드로 옮기는 일은 보류**(권한 확대라 K3 + Opus Judge + 사장 승인이 필요하고, CLAUDE.md의 dev-run 금지 조항과 충돌). 권한 검사(사람 앞 Enter, 콘솔 핸들 검사, 해시 검사)는 약화하지 않는다.

바뀔 조건: CLAUDE.md의 승인 관련 줄(25~36행, 53~71행)이 바뀌면 이 표를 다시 맞춘다. 표와 CLAUDE.md가 다르면 CLAUDE.md가 이긴다.
