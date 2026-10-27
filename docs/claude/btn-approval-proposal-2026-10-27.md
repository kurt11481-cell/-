---
id: btn-approval-proposal-2026-10-27
type: proposal
status: "제안 (사장 결정 대기 · 적용 안 함)"
date: 2026-10-27
class: "K3 (승인 장소 변경 · 보호 경로 CLAUDE.md → 수동 경로)"
authority: "order_authority=false · quantity_authority=none · Hard safety·주문 금지 불변"
consumers: "사장 · btn-approval Builder(워크트리) · 별도 읽기 전용 Judge · approval-venue-table-2026-10-25.md · active-decisions.md"
basis: "사장 지시 2026-10-27 10:15 KST '전부 버튼 승인으로 해줘. 그게 더 시각적으로 보기 편해'(사장실 스레드 직접 입력)"
---

# 버튼 승인 허용 — CLAUDE.md 승인 장소 개정 제안 (btn-approval)

**부딪히는 결정(먼저 읽기):** ① **D4 b(병합 bb11f04, 2026-10-25)** — CLAUDE.md:65 "buttons, cards … are not approval"을 직접 바꾼다. ② **sc-1022 S4(2026-10-23)** — 정책·한도·권한·예약 작업 변경은 "카드로 받지 않고 사장이 직접 친 메시지로만"(single-channel-redesign-2026-10-22.md:46, active-decisions.md:28). 이 제안이 병합되면 S4의 그 부분을 대체한다. ③ 승인 장소 표(approval-venue-table-2026-10-25.md:14·20)도 뒤따라 고쳐야 한다.

## 1. 결론
- CLAUDE.md는 **64~66행 3줄만** 바꾼다. 사장이 이 스레드가 올린 선택 카드에서 **직접 누른 버튼**을, 기록 조건 4가지를 다 갖췄을 때만 직접 입력과 같은 승인으로 인정한다.
- **K3 대상이다.** 근거: (가) CLAUDE.md는 보호 경로라 원래 수동 경로(CLAUDE.md:117-118), (나) 같은 줄을 만든 d124도 K3로 병합됨(bb11f04 커밋 메시지 "K3, Judge PASS_WITH_FIX"), (다) 권한 변경 승인으로 무엇을 인정할지 넓히는 일이다. → Opus Builder(워크트리) → 별도 읽기 전용 Opus Judge → 병합은 사장 PowerShell 한 줄.
- **바꾸지 않는 것:** Hard safety 전체(18~45행, sha256 8ee8d497…1f663) — 대조 `확인 <코드>`, 결정 일지 "decision text verbatim", 정책·상태 변경은 지금처럼 Cowork·사장 터미널. 병합 = 사장 PowerShell 한 줄(67~70행). 주문 금지·order_authority=false·quantity_authority=none.

## 2. 지금 규칙 (원문, CLAUDE.md:64-66, 3줄 sha256 9bc62078…e43ee9)
> In this item, the current conversation may also be the user's own message typed directly in the interactive Claude Code project thread (harness mark from=human trust=principal). Quotes relayed by a coordinator or another Claude, buttons, cards and scheduled turns are not approval. One approval covers only the immediately preceding proposal, the same day, once.

## 3. 바꿀 문장 (64~66행 → 7줄)
```
  In this item, the current conversation may also be the user's own message typed directly in the interactive Claude Code project thread
  (harness mark from=human trust=principal), or the user's own tap on a decision card (request_decision) that the same thread posted for
  that proposal. A tap counts only when the thread's decision record shows, taken from the harness wake for that card (not a summary):
  the card's message id and the proposal id it names, the option label chosen, the tapping member's account id equal to the project
  owner's, and the KST time of the tap. Quotes relayed by a coordinator or another Claude, a card closed by Claude (close_decision), a card
  posted in another thread or on an earlier day, summaries and scheduled turns are not approval. One approval covers only the
  immediately preceding proposal, the same day, once.
```
뜻(한국어): 버튼 승인 = ① 같은 스레드가 그 제안에 대해 올린 카드 ② 그 카드 id로 온 하네스 알림에서 읽은 기록 ③ 누른 사람 계정 id = 사장 계정 id ④ 누른 시각(KST)과 고른 선택지 문구. 하나라도 없으면 승인 아님. Claude가 닫은 카드·다른 스레드 카드·전날 카드·코디네이터 전달·요약·예약 턴은 승인 아님.

## 4. 버튼이 사장 본인 클릭인지 확인하는 법 (기록 양식)
결정 문서 "결정 기록" 절에 한 줄로 적는다:
`버튼 승인 · 제안 <id> · 카드 <cmsg_…> · 선택 "<선택지 문구>" · 누른 계정 <user_…> (= 사장) · <YYYY-MM-DD HH:MM KST>`
- 출처는 그 카드 id로 온 하네스 알림만. 코디네이터 요약·압축 요약·인계 파일은 가리킴일 뿐.
- 사장 계정 id는 이 프로젝트 기록상 `user_01KuMGKfZu1SBYxtMmg4vAiH`(이 스레드 첫 메시지의 author-id). 다르면 승인 아님.
- 사전 시험 T0(읽기 전용): 이 제안의 결정 카드를 사장이 누를 때 온 알림에 **카드 id·선택지·누른 계정 id·시각**이 실제로 들어 있는지 기록한다. 하나라도 없으면 Builder를 시작하지 않고, 버튼 승인은 계속 "승인 아님"(현행 유지)으로 둔다. **지금 알림 형식은 확인 필요.**

## 5. 하지 않음 (어떤 버튼으로도)
주문·정정·취소·예약, 키움 주문 도구·kiwoom_commands, reconcile/일지 apply(Claude Code 금지 유지), 정책·상태 파일 쓰기, .claude 설정 수정, dev-run·dev-merge·dev-queue 실행, -ApproveAuthority 입력(사장 터미널 한 줄 그대로).

## 6. 뒤따르는 문서 정리 (병합 뒤, 문서만)
- approval-venue-table-2026-10-25.md 14행·20행·26행(예약 작업)에 "또는 직접 누른 버튼(기록 조건 4가지)" 추가.
- active-decisions.md에 btn-approval 한 줄, sc-1022 S4 줄에 "카드 금지 부분은 btn-approval로 대체" 표시.
- 프로젝트 지침 v2.0 4절의 "CLAUDE.md가 직접 입력을 요구하는 승인" 예외는 Change classes에 대해선 사라짐(Hard safety 항목은 그대로 직접 입력).

## 7. 위험과 대처
| 위험 | 대처 |
|---|---|
| 오래된 카드를 나중에 누름(이 앱은 닫은 카드도 사장이 누를 수 있음) | "같은 날·바로 앞 제안 1건"이 아니면 무효 → 다시 제안 |
| 실수로 누름 | 카드 선택지에 무엇이 실행되는지 한 줄로 적고, 항상 "보류/현행 유지" 선택지를 둠 |
| 알림에 누른 사람 정보가 없음 | T0에서 막힘 → 현행 유지 |
| "In this item" 범위가 Hard safety로 번짐 | Judge 검토 항목 4 |

## 8. 되돌리는 법
64~66행을 2절 원문으로 되돌리는 커밋 1개(수동 경로, 사장 PowerShell 한 줄). 효력은 즉시 "직접 입력만"으로 돌아간다.

## 9. 결정 (사장)
- 지금 CLAUDE.md:65가 "버튼은 승인 아님"이라서, **K3 착수 승인은 이번에 한해 사장이 직접 치는 한 줄**(`btn-approval 착수 승인`)이 필요하다. 카드는 T0 시험과 방향 확인용.
- 기본값(무응답): NO_CHANGE(현행 유지).

동시 실행 한도(권한 작업 1건) — 지금 진행 중인 권한 작업 수: **확인 필요**(worktree 목록에 locked 4개: d10-spy·kiwoom-block-fix3·t2rc-eqnone3·t2rc-eqnone4, 등급은 확인 안 함).

바뀔 조건: T0 알림에 누른 계정 id나 카드 id가 없으면 이 제안은 철회. Judge가 Hard safety 해시 변경이나 범위 번짐을 찾으면 FAIL.

검토 완결: 원문 확인 7/8(CLAUDE.md 전문·00-home·active-decisions 해당 줄·single-channel 46행·projects-new 1~40·100~120행·d124 builder/judge·approval-venue-table) · 내장 재검토 0회(제안 단계, Judge에서 독립 검토) · 미해결 2(알림 형식, 진행 중 권한 작업 수) · 자료 시점 2026-10-27 10:17 KST · 바뀔 조건 위 줄.
