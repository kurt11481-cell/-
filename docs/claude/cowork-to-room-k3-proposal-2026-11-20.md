---
id: cowork-to-room-k3-proposal-2026-11-20
title: "대조 확인·일지 기록을 사장실 회사PC 스레드로 — K3 수정안 3판 (cowork-to-room C + recon-dayfill REPLACE·ADD (i))"
date: "2026-11-20"
status: "수정안 3판(R4 기록일 문장 정정) — 2판 착수 승인 13:06:03 KST · Builder 2b58d14 · Judge FAIL(J10 R4 문장만, R1~R3 PASS) · 3판 이어가기 승인 14:14:06 KST · Builder 13c5261 · Judge PASS · 병합 승인 14:38:17 KST · **병합 완료 main 0878e76(사장 PowerShell 2026-11-20 14:44 KST)** · 지침 3·4절 사장 수정 대기"
class: "K3 권한·한도(대조 apply 장소·확인 방법 = Hard safety, 대조 기록 경로) — 수동 경로: Builder(worktree) → 다른 세션이 쓴 Judge 지시문 → Opus Judge(xhigh) → 사장 PowerShell 병합"
authority: "order_authority=false · quantity_authority=none · 키움 주문 도구 금지 — 바꾸지 않음. 대조 불변식 I1~I5·자동 코어 경로·정책 파일 바꾸지 않음"
consumers: "사장 · 사장실 회사PC 스레드(대조 apply·일지 기록) · Cowork(현행 장소, 병합 뒤에도 유지) · K3 Builder·Judge"
source: "cowork-to-room-proposal-2026-11-20.md 3절 · recon-dayfill-1120-proposal-2026-11-20.md 2절 REPLACE·ADD (i)"
---

**부딪히는 결정(첫 줄):** D4 b의 Q1 '아니오'(사장실 스레드는 apply·일지 실행 안 함 — active-decisions 84행) · journal-venue C(카드 항목만, CLAUDE.md 35~42행) · CLAUDE.md 25~28행(대조 apply = Cowork·사장 터미널, Claude Code 금지). 사장이 11/20 11:55:27 KST 카드 'B + C'로 이 방향을 골랐다(active-decisions 165행). 이 문서는 그 C의 착수 승인을 받기 위한 수정안이다. 병합 권한 이전(D)은 넣지 않는다.

# 0. 결론

K3 한 건으로 네 가지를 같이 고친다. 병합 전까지는 지금 규칙(대조 `확인 <코드>`·L4·L5 일지는 Cowork에서 사장 직접 입력)이 그대로다.

| # | 무엇 | 왜 |
|---|---|---|
| **R1** | 계좌 대조 apply를 사장실 회사PC 스레드에서도 실행. 사장이 그 스레드에 **직접 친** `확인 <코드>`만 인정(카드 탭 제외). 새 확인 방법 `PROJECT_THREAD_USER_DECISION` + 4칸 기록 필수, 코드는 4번째 칸(원문)에서만 찾음 | Cowork를 여는 일 1건 줄임(C ①) |
| **R2** | 결정 일지의 스레드 기록을 카드 항목 2종 → **+ L4·L5 검토 닫기(line_review_completed)·고점 검토(peak_review_card_completed)**. S5 활성(s5_activation)은 제외. 새 두 종류는 사장이 **직접 친** 문장만(카드 탭 제외), 4번째 칸에 제안 코드 필수 | Cowork를 여는 일 1건 줄임(C ②) |
| **R3** | S5 활성 기록이 있으면 `propose`에 `--cash-flow-evidence`가 없을 때 **키움 조회 전에 거부** | 11/20 같은 증거 누락 → S7 보류를 사람·AI 누구든 못 하게(C ③ = recon-dayfill ADD (i)) |
| **R4** | 수동 대조를 '자동 HOLD 때의 공식 탈출구'로 CLAUDE.md에 다시 정의(증거 필수·기록일 조건) | recon-dayfill 2절 REPLACE. 같은 25~28행을 고치므로 한 K3로 묶음 |

R2는 journal-venue Judge 수정 ①("PROJECT_THREAD는 카드 항목만" — journal-venue-judge-report.md 14행)을 넓힌다. 그때 막으려던 Hard safety 번짐은 ① 직접 입력 한정(카드 탭 제외) ② 4번째 칸 코드 검사 ③ s5_activation 계속 제외로 막는다. L4·L5 닫기는 S7 멈춤을 풀어 새 매수를 다시 열 수 있는 일이라(통합 점검 161행) 카드 탭보다 강한 직접 입력을 요구한다.

사장 손: 착수 카드 1번 → (Builder·Judge 뒤) 병합 카드 1번 + PowerShell 한 줄 → 프로젝트 지침 3·4절 직접 수정. 이 수정안이 안 되면(Judge FAIL·무응답) 기본값 = NO_CHANGE(지금 규칙 유지).

# 1. 그림으로 보기

```
지금 (병합 전, 계속 이대로)
  자동 코어 06:15 대조 HOLD
      │
      ▼
  Cowork: propose(키움 읽기) → show → 사장 "확인 <코드>" → apply
      │
      ▼
  L4·L5 닫기도 Cowork에서 사장이 다시 말해야 일지에 남음

R1~R4 병합 뒤
  자동 코어 HOLD
      │
      ▼
  Cowork: propose (S5 활성이면 증거 파일 없으면 거부 = R3)
      │
      ▼
  사장실 스레드: show 표를 그대로 보여 줌
      │
      ▼
  사장이 그 스레드에 "확인 <코드>" 직접 입력 (카드 탭은 인정 안 함)
      │
      ▼
  같은 세션: apply --confirmed-via PROJECT_THREAD_USER_DECISION (4칸) → 다시 분석해 MATCH 확인
      │
      ▼
  L4·L5 닫기·고점 검토: 같은 스레드에서 propose → 사장 결정 → apply → verify (R2)
```

propose는 키움 읽기라 Windows 런타임이 필요해서 Cowork에 남는다(사장실 스레드는 지침 1절상 사장이 그 자리에서 요청한 키움 읽기만 가능하고, 지침 3절상 셸은 읽기 전용). 사장실 스레드가 propose 명령을 정확히 만들어 주는 것은 B(이미 시행)다.

# 2. 바꿀 곳 (Builder 범위)

## 2-1. CLAUDE.md (보호 경로 — 수동 경로만)

**25~28행 (R1·R4)** — 지금 문장 뒤를 아래로 바꾼다(뜻 기준, 정확한 영문은 Builder가 쓰고 Judge가 대조).
- 지금: apply는 Cowork(사장 "확인 <code>") 또는 사장 터미널. Claude Code·Codex·예약·Judge는 apply 안 함.
- 뒤: 위 둘 **+ 사장실 회사PC 스레드(대화형 Claude Code 프로젝트 스레드)**: 사장이 그 스레드에 직접 친 메시지(하네스 표시 from=human trust=principal)가 **그 제안의 `확인 <code>`를 담고 있을 때만**(결정 카드 탭은 대조 확인이 아님), 같은 세션이 `--confirmed-via PROJECT_THREAD_USER_DECISION`과 user_message `<message or card id> | <account id> | <KST time> | <verbatim text or card option>`로 apply하고, 이어서 show·분석으로 MATCH를 확인한다. 바로 앞 제안 1건·같은 날(KST)·1회. 코디네이터·다른 Claude가 옮긴 문장, 다른 스레드나 전날 카드, Claude가 닫은 카드, 요약, 예약 턴은 확인이 아니다. Codex·예약 LLM 작업·Judge·하위 에이전트·다른 Claude Code 세션은 apply하지 않는다. 코드를 치거나 추측하거나 재사용하지 않는다. **사장실 스레드는 PROJECT_THREAD_USER_DECISION만 쓰고 COWORK_CHAT_USER_MESSAGE·USER_TERMINAL 방법으로 apply하지 않는다**(방법 선택은 스크립트가 검증하지 못하는 문서 규칙 단계 — 3절).
- R4 한 줄(3판 정정): 자동 코어 대조가 HOLD일 때 수동 대조(propose → 확인 → apply)가 공식 탈출구다. S5 활성 뒤에는 `--cash-flow-evidence` 필수(없으면 propose가 거부, R3). **기록일 숫자 조건은 규칙에 넣지 않는다** — 수동 대조 전에 그날 HOLD 사유와 조회 창(auto_core_reconcile.py)을 보고 판단한다. 2판의 "마지막 체결 KST 날짜 다음 날 이후"는 Judge J10이 주간거래에 틀렸다고 지적했고, 그 지적의 "이틀 이상"도 병합 전 코드(창 밖 체결 = 파싱 오류 → I2 FAIL) 기준이다. 22d44cf(recon-dayfill 병합) 뒤에는 주간거래 행이 정상 체결로 읽히고 기록 전 체결은 집계에서 빠져 T9로 I2·I3 PASS가 확인됐다(recon-dayfill 스레드, 코디네이터 전달 2026-11-20 14:05 KST — 이 스레드는 원문 미확인, 확인 필요). 어느 숫자도 지금 코드와 맞는지 확인되지 않아 빼는 것이 안전하다(REMOVE).

**29~42행 (R2)** — "Holding-card S7b entries (card_decision, card_user_decision) only." → "Holding-card S7b entries (card_decision, card_user_decision) and the S5 line_review_completed and peak_review_card_completed entries; for the two S5 entries only the user's own typed message counts (no card tap) and the verbatim field must contain that proposal's code. Never s5_activation. The thread uses only PROJECT_THREAD_USER_DECISION, never the Cowork or terminal methods." 나머지 문장(바로 앞 제안·같은 날·1회, 확인이 아닌 것 목록)은 그대로.

**116행 (Decision journal)** — "holding-card position decision ... in Cowork or in the 사장실 회사PC 스레드" 문장 끝에 "L4·L5 line review and peak review completions accepted in that thread are recorded the same way (Hard safety)." 한 문장 추가.

## 2-2. 스크립트

| 파일·행 | 지금 | 바꾼 뒤 |
|---|---|---|
| apply_user_confirmed_broker_snapshot.py 30행 | `CONFIRMATION_METHODS = ("COWORK_CHAT_USER_MESSAGE", "USER_TERMINAL")` | + `"PROJECT_THREAD_USER_DECISION"` |
| 같은 파일 277~281행(키움 제안 검사) | 방법이 목록에 있고 메시지에 코드가 있으면 통과 | 방법이 PROJECT_THREAD면 **4칸 형식 검사 + 코드는 4번째 칸(`split('|', 3)[3]`)에서만 찾기**를 라이브러리 안에서 한다(CLI만 믿지 않음. 280행 '메시지 전체' 검사로는 1칸·2칸에 코드가 있어도 통과하므로). 형식·4번째 칸 코드 검사 함수는 portfolio_review_journal.py 240~246행 `project_thread_message_valid`를 **처음부터 validation_common.py로 옮겨** 대조·일지 두 곳이 같은 함수를 import(두 벌 복사 금지, apply 라이브러리가 일지 모듈을 끌어오지 않게) |
| tests/test_auto_core.py 1056~1059행 | `CONFIRMATION_METHODS`와 apply `--confirmed-via` choices를 두 방법 튜플로 고정 | 기대 튜플에 PROJECT_THREAD_USER_DECISION 추가(이 K3 범위 — 안 고치면 반드시 실패) |
| tests/test_reconcile_broker_state.py 841~852행 propose 도우미 | `--journal`을 안 넘김 | R3 뒤 기본값이 실제 일지(첫 항목 s5_activation, 20건 — 2026-11-20 직접 확인)를 읽어 조회 0회로 실패하고 실제 자료에 따라 결과가 바뀌므로, 도우미가 임시 `--journal`을 넘긴다 |
| auto_core.py 409~410행 | 원장 항목 중 AUTO_CORE_INVARIANTS가 아닌 것 = 사람 경로 | 변경 없음(새 방법도 사람 경로로 잡히는 것이 맞음). Judge 확인 항목 |
| reconcile_broker_state.py 349행 | user_message 필수 = COWORK만 | COWORK·PROJECT_THREAD 둘 다 필수 |
| 같은 파일 362행 | 메시지가 없으면 코드로 대체 | PROJECT_THREAD는 대체 없음(349행에서 이미 거부). USER_TERMINAL 동작은 그대로 |
| 같은 파일 1~16행 머리말, 522~524행 help | apply = Cowork·사장 터미널 | 사장실 회사PC 스레드 방법 한 줄 |
| 같은 파일 cmd_propose 280~289행 근처 (R3) | 증거 없어도 진행 | propose에 `--journal` 인자(기본 REPO_ROOT/stock-strategy-system/decision_journal.json — auto 538행과 같은 기본값)를 더하고, `portfolio_exposure.journal_view(load_journal(...))`로 읽어(453~456행 auto 경로와 같은 함수) 활성 기록이 있고 `--cash-flow-evidence`가 없으면 **키움 조회 전에** `CASH_FLOW_EVIDENCE_REQUIRED_AFTER_ACTIVATION`으로 거부(종료 2, 상태·출력 폴더 안 씀). 일지 파일 없음(MISSING) = 활성 없음(auto와 같음, 지금 동작), CORRUPT·읽기 오류 = 거부(fail closed) |
| assets/locales/reconcile-broker-state-ko-KR.json 5·6·51행 | "Cowork에서 '조정 확인해줘'", "Cowork 확인에는 … 원문 필요" | "Cowork 또는 사장실 회사PC 스레드에서 …", 사장실 방법도 원문 필요. R3 거부 문구 1줄 추가(증거 파일 만드는 명령 안내) |
| portfolio_review_journal.py 187~189·556~558행 | PROJECT_THREAD = `CARD_ENTRY_TYPES`만 | 허용 = CARD_ENTRY_TYPES + (line_review_completed, peak_review_card_completed). s5_activation은 계속 `PROJECT_THREAD_ENTRY_TYPE_INVALID`. 새 두 종류는 4번째 칸에 제안 코드가 없으면 `CONFIRM_CODE_NOT_IN_USER_MESSAGE`(apply)·같은 사유(chain 재검사 `_entry_inconsistency`) |
| 같은 파일 15~22행 머리말 | 카드 항목만 | 새 두 종류 한 줄 |
| schemas/portfolio-review-journal.schema.json 4행 description | 카드 항목 설명 | 스레드 방법 허용 항목 문구만 갱신(enum 29행은 이미 PROJECT_THREAD 포함 — 바꾸지 않음) |
| references/broker-snapshot-reconciliation.md 112~160행 | 2절 = Cowork 절차 | 2절에 "사장실 회사PC 스레드" 갈래 추가(같은 1~8단계, 6단계 명령만 PROJECT_THREAD + 4칸). 155~160행 '코드는 사람 증명이 아님' 단락에 스레드도 같다는 문장, 159~161행 "Claude Code denies … apply"를 사실대로("deny는 Claude Code의 Bash·PowerShell 도구에만 걸린다. 사장실 스레드의 회사PC 셸(device_bash·Desktop Commander)은 PreToolUse 훅이 키움 주문만 막으므로 이 apply는 문서 규칙으로만 통제된다" — settings.json 26~27·44~55행). 189~209행 4절: "should carry" → 활성 뒤 필수(R3), 209행 "Without the two options … exactly as before" → 활성 전만 |
| references/portfolio-exposure-review.md 321~322행 근처 | 일지 확인 장소 | 사장실 스레드 기록 가능 한 줄 |

`.claude/settings.json`은 바꾸지 않는다(26~27·35~36행 apply deny는 Claude Code의 Bash·PowerShell 도구에만 걸리고, 사장실 스레드의 회사PC 셸에는 걸리지 않는 것이 journal-venue 때 확인된 구조 — 즉 이 경로를 막는 것은 지금도 문서 규칙과 하네스 표시다. 3절 위험 참고).

## 2-3. 사장이 병합 뒤 직접 고칠 것 (Builder 범위 밖)
- 프로젝트 지침 3절 예외 줄: "S7b 일지에 한해" → "S7b·L4·L5 검토 닫기·고점 검토 일지와 계좌 대조 apply(사장이 그 스레드에 직접 친 `확인 <코드>`)". 실행 허용 명령: `reconcile_broker_state.py show`·`apply --confirmed-via PROJECT_THREAD_USER_DECISION`, 일지 `propose-line-review`·`propose-peak-review` 추가.
- 프로젝트 지침 4절 첫 줄 "승인류(…, 대조 '확인 <코드>' …)는 실행하지 않는다" 괄호에서 대조 확인 빼기.
- 이 두 줄이 고쳐지기 전에는 병합돼도 스레드가 실행하지 않는다(지침이 더 좁음).

# 3. 위험과 막는 장치

| 위험 | 막는 장치 | 남는 것 |
|---|---|---|
| 스레드가 사장 입력 없이 apply | 하네스 표시(from=human trust=principal)·카드 탭 기록(누른 계정 = 프로젝트 소유자)을 4칸에 남김, CLAUDE.md 금지 목록, 반대 시험 | 스크립트는 "누가 쳤는지"를 검증 못 함. 코드는 제안 id 앞 8자라 읽을 수 있는 누구나 앎(reference 155~158행 — Cowork도 같음) |
| 코디네이터가 옮긴 문장으로 apply | CLAUDE.md 문구 + 반대 시험(문서 규칙 단계) | 같음 |
| 방법 바꿔치기 — 스레드가 `--confirmed-via COWORK_CHAT_USER_MESSAGE --user-message "확인 CODE"`로 apply해 4칸 검사를 피함(지금도 코드는 못 막음: apply 277~281행·reconcile 349행) | CLAUDE.md "스레드는 PROJECT_THREAD만" 문장, T16으로 현행 동작 기록 | 스크립트는 호출한 세션을 모름 → 문서 규칙 단계. USER_TERMINAL은 Desktop Commander 대화형 프로세스로 콘솔 검사를 통과할 수 있는지 **확인 필요** |
| 카드 선택지 이름은 Claude가 씀 → '취소' 선택지에 코드를 넣으면 탭 한 번으로 apply | 대조·L4·L5·고점 검토는 카드 탭 인정 안 함(직접 입력만) | 카드 탭은 S7b 카드 항목만(지금 그대로) |
| portfolio_state 쓰는 세션이 하나 늘어남 | 원장 해시 체인·백업·STATE_CHANGED_OUTSIDE_LEDGER(라이브러리 그대로), apply 뒤 MATCH 재확인 | 회사PC VM 파이썬으로 Windows 저장소 상태 파일을 쓸 때 줄바꿈·해시가 Windows와 같은지 **확인 필요**(apply는 기존 줄바꿈 유지 — reference 166~167행). Judge 점검 항목 |
| 오래된 카드·전날 문장 재사용 | 제안 만료 15분(policy maximum_age_seconds=900, reference 119~120행)이 대조는 사실상 막음. 일지는 제안 만료 1시간 | — |
| R3로 수동 대조가 막혀 HOLD가 오래감 | 증거 파일은 normalize로 만들 수 있고, 자동 코어 경로(auto)는 자기 증거를 씀(바뀌지 않음) | 키움 거래내역 저장이 안 되는 날엔 수동 대조 불가 → 그날은 HOLD 유지(fail closed). 바뀔 조건 8절 |

# 4. 사전 등록 시험 (Builder가 쓰고 Judge가 실행 확인)

통과 기준: 아래 전부 PASS + 기존 대상 테스트 파일 전부 기준선과 같은 실패 수 이하(test_reconcile_broker_state·test_approval_human_check·test_portfolio_review_journal·test_decision_journal_cards·test_run_portfolio_exposure_review·test_auto_core* 중 대조 관련).

| id | 시험 | 기대 |
|---|---|---|
| T1 | 대조 apply, PROJECT_THREAD, 4칸 + 4번째 칸 `확인 <코드>` | 적용, 원장 confirmation_method = PROJECT_THREAD_USER_DECISION, user_message 4칸 그대로 |
| T2 | PROJECT_THREAD, --user-message 없음 | 거부(종료 2, 상태 불변) |
| T3 | PROJECT_THREAD, 3칸·빈 칸·`user_` 없음·`KST` 없음 | 거부 `PROJECT_THREAD_MESSAGE_INVALID`(라이브러리 직접 호출로도) |
| T4 | PROJECT_THREAD, 4칸 맞지만 코드 없음·다른 코드 | 거부 |
| T5 | COWORK·USER_TERMINAL 기존 동작 | 바뀌지 않음(test_auto_core.py 1056~1059행 기대 튜플 갱신과 propose 도우미의 임시 `--journal` 외 기존 테스트 불변) |
| T6 | 일지 line_review_completed·peak_review_card_completed, PROJECT_THREAD, 4칸 + 코드 | 기록, verify PASS |
| T7 | 같은 두 종류, 4칸이지만 코드 없음 | 거부, 손으로 넣은 항목은 verify가 잡음 |
| T8 | s5_activation, PROJECT_THREAD | 거부 `PROJECT_THREAD_ENTRY_TYPE_INVALID`(apply·verify 둘 다) |
| T9 | 카드 항목(card_decision 등) PROJECT_THREAD | 지금과 같음(코드 요구 추가 없음) |
| T10 | propose, 일지에 활성 기록 있음, 증거 없음 | 키움 조회 0회(reader 호출 수 0), 거부 `CASH_FLOW_EVIDENCE_REQUIRED_AFTER_ACTIVATION`, 출력 폴더 없음 |
| T11 | propose, 활성 기록 없음, 증거 없음 | 지금과 같음 |
| T12 | propose, 일지 CORRUPT·읽기 실패 | 거부(fail closed), 키움 조회 0회 |
| T13 | propose, 활성 + 증거 있음 | 지금과 같음 |
| T14 | auto 경로 | 바이트 단위로 결과 불변(R3는 propose에만) |
| T15 | PROJECT_THREAD, 코드가 1칸(id)이나 2칸에만 있음 | 거부(대조·일지 둘 다) |
| T16 | PROJECT_THREAD 4칸 메시지를 COWORK 방법으로 넣음 | 현행대로 통과함을 시험으로 기록(우회는 문서 규칙으로만 막힘 — 3절) |
| T17 | 새 두 종류 기록 뒤 | load_journal OK, journal_view의 activation_date 불변, auto 결과 불변 |
| T18 | propose, 일지 파일 없음(MISSING) | 지금과 같음(키움 조회 1회) |
| T19 | 대조 PROJECT_THREAD, 형식만 맞춘 위조 `user_…`·`… KST` | 통과함을 명시(스크립트 한계 기록 — 사람 증명은 하네스 표시) |
| T20 | 만료(15분) 넘은 대조 제안에 맞는 4칸 | 거부 BROKER_PROPOSAL_EXPIRED |

# 5. 연결표 (analysis-linkage-map 1절 8번)

| ① 자료 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 사장 직접 입력 `확인 <코드>`(스레드) | 사장, 사장실 회사PC 스레드 | 병합 뒤 apply_user_confirmed_broker_snapshot.py 277~281행 + 4칸 검사 | portfolio_state 보유·현금 → 06:15 코어 대조·주문표 | apply 거부 사유를 그 스레드가 즉시 보고, MATCH 재확인 | 지금 **끊김** → R1으로 메움(이 K3) |
| 일지 L4·L5 닫기·고점 검토(스레드) | 같은 스레드 | 병합 뒤 portfolio_review_journal.py 187~189·556~558행 | S7 pauses 해제 → QQQ 관문 ⓑ 새 매수 멈춤 해제(통합 점검 161행) | verify 실패를 그 스레드가 보고 | 지금 **끊김** → R2 |
| 입출금 증거 파일 | cash_flow_evidence.py normalize(사장 저장 거래내역) | 지금 cash_flow_evidence.py 393~397행(없으면 S7 보류만) → 병합 뒤 reconcile_broker_state.py propose(R3) | 증거 없는 수동 대조 자체가 안 만들어짐 → S7 보류 재발 없음 | propose 거부 문구(로캘 새 줄) | 지금 **끊김** → R3 |
| 수동 대조 탈출구 규칙 | CLAUDE.md 25~28행 | 사장실 스레드·Cowork가 HOLD 때 읽음 | 기록일·증거 조건을 지킨 수동 대조 | 다음 06:15 reconcile.json HOLD 지속 → 아침 알림 | 지금 **끊김**(문서에 없음) → R4 |

# 6. 진행 중 권한·한도 1건 상한 (CLAUDE.md 119행)

확인 2026-11-20 12:0x KST, 원문: git log — swing-bars(authority 분류) 병합 af40710(dev-runs/LATEST.json merged_at 2026-11-20T02:24:30Z = 11:24 KST), recon-dayfill-k3 병합 22d44cf(11:32 KST). docs/claude/_dev-queue 비어 있음. 따라서 진행 중 권한·한도 0건 → 이 K3 착수 가능. 관제판 tasks에 다른 K3 '진행 중'이 있는지는 착수 직전에 다시 확인한다.

# 7. 절차

1. 사장 착수 카드(이 수정안 1건, 오늘 KST, 1회).
2. 이 스레드가 Builder 지시문(docs/claude/cowork-to-room-k3-builder-prompt.md) 작성 → 수동 경로 Builder(worktree, Opus high) 시작.
3. **Judge 지시문은 다른 세션이 작성**(사장실 코디네이터에 새 스레드 요청) → 별도 읽기 전용 Opus · xhigh Judge.
4. Judge PASS → 병합 카드 → 사장 PowerShell 병합 한 줄(이 스레드가 정확한 줄을 줌).
5. 병합 뒤: 사장이 지침 3·4절 수정(2-3절), 이 스레드가 active-decisions·관제판 갱신. 첫 실사용 1건(다음 대조 또는 L4·L5 닫기)을 그 스레드가 verify까지 보고.

# 8. 기본값·바뀔 조건
- Judge FAIL·시험 미달·사장 무응답 → NO_CHANGE(지금 규칙 유지). 노출·권한·한도를 올리지 않는다.
- Judge가 R1만 FAIL → R2·R3·R4만 진행(R1 빼고 다시 판정).
- VM 파이썬 쓰기에서 줄바꿈·해시 차이가 나오면 → 스레드 apply는 Windows 파이썬(Desktop Commander) 경로로 한정하는 문장을 넣고 다시 판정.
- R3 거부로 수동 대조가 2영업일 넘게 못 되는 일이 생기면 → '증거 없음 사유 + S7 보류 수용' 우회 옵션을 따로 제안(K3).
- 스레드에서 사장 입력이 아닌 것으로 apply가 한 번이라도 실행되면 → 즉시 되돌림 안건.

# 9. 확인 필요
- 회사PC VM 파이썬으로 portfolio_state.json·decision_journal.json을 쓸 때 Windows 실행과 바이트가 같은지(S7b 실사용 1건이 어느 셸이었는지 포함).
- 프로젝트 스레드에서 `.claude/settings.json` deny·훅이 발동하지 않는다는 것의 직접 시험(journal-venue 때는 '가능성 높음').
- L4·L5 닫기 propose의 실제 입력 인자(propose-line-review)와 사장 결정 문장 형식 — Builder가 기존 테스트에서 확인.

# 사장 결정 (기록만)
- 2026-11-20 13:06:03 KST **착수 승인**: 사장 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9WVwwMsyJTXTwnGmPTd6xyN(질문 "cowork-to-room-k3 수정안 2판으로 K3 작업을 시작할까요?", 고른 항목 A '착수 (권장)', 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH = 사장, 하네스 wake 기록). 수정안 id cowork-to-room-k3-proposal-2026-11-20(2판). 같은 날 KST 1회(CLAUDE.md 69~77행). 병합은 별도 카드 + 사장 PowerShell.

- 2026-11-20 14:1x KST Judge(Opus, 지시문 sha256 9f987057…bde8) 커밋 2b58d14 판정 **FAIL** — J1~J9·J11·J12 PASS, J10 FAIL: R4 기록일 조건 문장(CLAUDE.md 38~40행·참조 문서 R4 단락)이 주간거래 체결에 틀림. → 3판: R4의 기록일 숫자 조건을 빼고(위 2-1절), Builder가 CLAUDE.md·참조 문서 R4 문장 두 곳만 고친 새 커밋 → 같은 지시문으로 재판정. 3판 이어가기는 사장 카드로 받는다.
- 2026-11-20 14:14:06 KST **3판 이어가기 승인**: 사장 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9MF3ouuSFAwQ5ZUyxiauV8a(질문 "cowork-to-room-k3 3판(R4 기록일 문장 정정)으로 Builder를 이어갈까요?", 고른 항목 A '이어서 진행 (권장)', 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH = 사장, 하네스 wake 기록). 같은 날 KST 1회.
- 2026-11-20 14:2x KST Judge 2회차(Opus, 같은 지시문) 커밋 13c52614f6ebb829411175bf042d79263e0fe4a9 **PASS**(J1~J12) — docs/claude/cowork-to-room-k3-judge-report.md.
- 2026-11-20 14:38:17 KST **병합 승인**: 사장 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX99v8pqnMuHkWHFiQgZmVmto(질문 "cowork-to-room-k3(커밋 13c5261, Judge PASS)를 오늘 병합할까요?", 고른 항목 A '병합 승인 (권장)', 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH = 사장, 하네스 wake 기록). 실행 = 사장 본인 PowerShell 한 줄 docs/claude/cowork-to-room-k3-merge-2026-11-20.ps1(오늘 KST만). 스레드는 병합을 실행하지 않음.
- 2026-11-20 14:44 KST **병합 완료**: 사장 본인 PowerShell 출력 "MERGED commit=13c52614 main=0878e76 / COWORK_TO_ROOM_K3_DONE"(사장이 프로젝트 대화에 직접 붙임, 메시지 cmsg_0137MRzn9nuDvvQmVxm6WeX9PMDVHFB94vRXvGfTKH3wnp). git log 확인: 0878e76 Merge cowork-to-room-k3, 15 files. 남은 일: 사장이 프로젝트 지침 3·4절 수정(2-3절 + Windows 파이썬 한정), 첫 실사용 전 훅 발동 확인.
- Judge 권고(병합 막지 않음, 기록): R3는 없는 `--journal` 경로를 넘기면 우회됨(문서 규칙만) — 다음 수정 후보. 키움 주문 차단 훅이 `--confirm` 명령을 막아 스레드 apply가 실제로는 막힐 수 있음 — 첫 실사용 때 해롭지 않은 명령으로 발동 여부 확인, 풀려면 .claude 훅 별도 K3.

# 재검토 기록
- 내장 재검토 1회(Opus 독립 작업자, 읽기 전용). 지적 11건(상 3·중 5·하 3) 모두 원문으로 다시 확인하고 반영: test_auto_core.py 1054~1059행 고정 튜플(1), test_reconcile_broker_state.py 840~853행 도우미 + 실제 일지 첫 항목 s5_activation·20건(2), 방법 바꿔치기 우회(3), 4번째 칸 한정(4), 대조·S5 일지 카드 탭 제외(5, **결론 바뀜**), journal-venue-judge-report.md 14행 수정 ① 넓힘 근거(6), reference 159~161행·settings.json 44~55행 훅(7), 반대 시험 T15~T20(8), validation_common 이동 확정(9), 453~456행 정정(10), auto_core.py 407~411행 변경 없음 명시(11).
- 결론이 바뀐 곳(카드 탭 제외)은 위험 이유(선택지 이름을 Claude가 씀, L4·L5 닫기가 새 매수를 다시 엶)를 원문으로 확인. 추가 라운드는 바뀐 곳만 Judge 단계에서 본다(착수 뒤 Judge가 독립 판정).

검토 완결: 원문 확인 CLAUDE.md 18~45·116·119행 · cowork-to-room-proposal 전문 · recon-dayfill-1120 1~2절 · apply_user 1~60·265~300행 · reconcile_broker_state 1~30·280~420·445~470·500~557행 · journal.py 1~30·60~80·170~262·540~570·885~905행 · cash_flow_evidence 380~426행 · reference 105~212행 · 로캘 5·6·38·51행 · settings.json 26~37·44~55행 · test_auto_core 1054~1059 · test_reconcile 840~853 · journal-venue 제안·Judge 14행 · 내장 재검토 1회(반영 11건) · 미해결 확인 필요 3(9절) + USER_TERMINAL 대화형 프로세스 통과 여부 · 자료 시점 2026-11-20 12:4x KST(main 22d44cf) · 바뀔 조건 8절
