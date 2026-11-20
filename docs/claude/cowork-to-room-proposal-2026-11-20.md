---
id: cowork-to-room-proposal-2026-11-20
title: "Cowork(비서실) 작업을 사장실로 옮기기 — 결정 제안서"
date: "2026-11-20"
status: "B + C 방향 채택(2026-11-20 11:55 KST). C K3 착수 전. 규칙·설정·스크립트 변경 0, 개발 큐 등록 0"
class: "문서. 채택 시 C는 K3(수동 경로 Builder → 별도 세션 Opus Judge → 사장 PowerShell 병합)"
authority: "order_authority=false · quantity_authority=none · 키움 주문 도구 금지 — 어느 안도 이 셋을 바꾸지 않음"
consumers: "사장 · 사장실 코디네이터 · 채택 시 K3 Builder·Judge"
---

**부딪히는 결정(첫 줄):** D4 b의 Q1 '아니오'(사장실 스레드는 apply·일지·정책/상태·decision_mode 실행 안 함 — active-decisions 84행, approval-venue-table 23행) · approval-without-cowork NO_CHANGE(10/25 11:45, 같은 문서 46행) · projects-new '승인 이전 중단'(89행) · sc-1022 S4(31행) · btn-approval '전부 아님'(85행) · dc-dev Q1 a 일반 병합 = Cowork(83행) · journal-venue C(123행, 선례). 사장이 새로 연 질문(2026-11-20 11:36 KST 직접 입력)이라 다시 다룬다. 10/25 기록이 미리 정해 둔 대응(Cowork 부담 확인 → 5안 터미널 원클릭, approval-without-cowork 42행)도 4절에 함께 비교한다.

# 결론

**권장: '전부 이전'(D)은 하지 않는다. 오늘부터 B, 그리고 K3 한 건으로 C(좁게)를 한다.**
1. **B "준비·회수"(규칙 변경 0, 오늘부터):** Cowork에 칠 문장·명령을 사장실 스레드가 정확히 만들어 주고(입출금 증거 옵션 같은 빠짐을 미리 점검), 사장은 붙여 넣기만, 결과는 사장실 스레드가 회사PC 파일·git으로 바로 읽어 확인·보고한다.
2. **C "대조 확인·일지만 이전"(K3 1건):** ① 계좌 대조 `확인 <코드>` → apply ② 결정 일지 전부(L4·L5 검토 닫기·고점 검토 포함)를, 사장이 **사장실 회사PC 스레드에 직접 친 문장**으로 그 스레드가 실행한다. 함께 ③ **propose에 입출금 증거가 없으면 거부**하는 결정적 검사를 넣어 오늘 같은 실수를 사람·AI 누구든 못 하게 한다.
3. **일반 병합은 옮기지 않는다.** 병합을 하려면 사장실 스레드가 PowerShell을 실행할 수 있어야 하는데, 그러면 같은 스레드가 사장 터미널 확인(`USER_TERMINAL`)과 권한 병합(`-ApproveAuthority`)까지 흉내 낼 수 있게 된다. 대신 B로 "Cowork에 '병합 <id>' 한 줄"만 준비한다.
4. **Cowork에 남는 것:** 일반 병합, 정책·상태 변경, decision_mode "켜", `.claude` 설정, 컴퓨터 연결 예약의 지시문 교체(서명 제약), 기억 쓰기.
5. **어디로도 못 옮기는 것:** 키움 주문 입력(사장 몫), 주문·정정·취소·예약, 비밀 읽기, 인증·토큰 재발급.

사장이 고를 것(카드 1장): **A 그대로 / B만 / B + C(권장) / D 전부 이전**.

# 1. 그림으로 보기

```
지금
  사장실 스레드: 분석·제안 ───▶ "Cowork에 이렇게 치세요"
                                      │
                                      ▼
  사장: Cowork 창 열기 → 입력 (오늘 5번)
                                      │
                                      ▼
  Cowork: 실행 (사장실은 실수를 미리 못 막고 결과도 늦게 앎)

B + C 뒤
  사장실 스레드: 분석·제안 + 명령 미리 점검
                                      │
                                      ▼
  대조 확인·일지 → 사장이 같은 스레드에 한 줄 → 그 자리에서 실행·검증
                                      │
                                      ▼
  병합·정책·설정·PC 예약 → 사장실이 준비한 한 줄을 Cowork에 붙여 넣기
                                      │
                                      ▼
  사장실 스레드가 결과 파일을 바로 읽어 보고 (회수)
```

# 2. Cowork가 지금 맡은 일 — 3분류

"옮겨도 됨" = 규칙 변경 없이 사장실 스레드가 이미 함. "규칙 개정 필요" = 사장 직접 입력이 규칙상 필요한 승인류. "못 옮김" = 헌법·절대 안전.

| # | 일 (오늘 사례) | 지금 장소 | 분류 | 원문 |
|---|---|---|---|---|
| 1 | 계좌 대조 `확인 <코드>` → apply | Cowork 또는 사장 터미널. Claude Code는 apply 금지 | 규칙 개정 필요 → **C ①** | CLAUDE.md 23~28행 · reference 159~160행 |
| 2 | 대조 propose·증거 파일 만들기(`cash_flow_evidence.py normalize`)·apply 뒤 MATCH 확인 | Cowork(Windows 키움 런타임) | 스레드 실행은 지침 1절(키움 조회 조건)·3절(셸 읽기 전용)에 걸림. **B로 명령만 준비**, 결정적 검사는 **C ③** | reference 70·152~153·189~209행 |
| 3 | 결정 일지: 보유 카드 S7b | **이미 사장실 스레드 가능**(실사용 1건) | 옮겨도 됨(완료) | CLAUDE.md 35~42행 · portfolio_review_journal.py 70행 |
| 4 | 결정 일지: L4·L5 검토 닫기·고점 검토 등 | Cowork 또는 사장 터미널. 스크립트도 스레드 방법을 카드 항목으로만 허용 | 규칙 개정 필요 → **C ②** | CLAUDE.md 29~34·116행 · journal.py 187~189·556~558행 |
| 5 | 일반 변경 병합('llm-newsdiag 병합해줘') | Cowork가 Desktop Commander로 | 규칙 개정 필요하지만 **옮기지 않음 권장**(위 결론 3) | CLAUDE.md 61~65·129~133행 · 지침 3절 |
| 6 | 권한 병합(`-ApproveAuthority`)·수동 경로 병합 .ps1 | 사장 본인 PowerShell | 그대로(Cowork 일 아님) | CLAUDE.md 69~71·81~82행 |
| 7 | 예약 지시문 교체 | 사장실 스레드를 깨우는 예약은 **이미 스레드가 바꿈**(11/18 등). 컴퓨터 연결 예약은 스레드 update_trigger가 needs_device_approval 3회 → Cowork 지시 + PC 서명 | 컴퓨터 연결 예약만 기술 제약. 기기 연결 스레드에서 PC 승인 창이 뜨는지 시험 1회 = **확인 필요** | README 81·96행 · approval-venue-table 26행 |
| 8 | 예약 새로 만들기 | 사장실 스레드 가능(11/17) | 옮겨도 됨(완료) | README 95행 |
| 9 | S7 검토선 재실행 | Cowork | CLAUDE.md에 장소를 정한 줄 없음 → K3 아님. 스레드가 하려면 **지침 3절 예외(사장이 지침 수정)**. 이번 권장에는 넣지 않고 B로 준비 | 확인한 범위: CLAUDE.md 전 행 |
| 10 | 정책·상태 변경, decision_mode "켜" | Cowork(CLAUDE.md는 "this session", 막는 곳은 지침 4절·Q1) | 남김 권장(코어 행동을 직접 바꾸는 큰 스위치, 드물게 씀) | CLAUDE.md 43~45행 · active-decisions 84행 |
| 11 | `.claude` 설정 변경 | Cowork(사장 승인) | 남김 — 스레드가 자기 안전장치를 고치는 구조가 됨 | CLAUDE.md 132~133행 |
| 12 | 수동 경로 Builder·Judge 띄우기 | 이미 사장실 스레드 가능(오늘 recon-dayfill-k3) | 옮겨도 됨(완료) | CLAUDE.md 79~80행 |
| 13 | 카드 수락·등록부, 원장 등록, 관제판 갱신 | 대화형 세션·사장실 스레드 | 옮겨도 됨(완료) | CLAUDE.md 50~52·134행 · active-decisions 47행 |
| 14 | 개발 지시문 작성·큐 등록 | 원래 Cowork 몫, 사장실 스레드도 실제로 함(recon-dayfill-k3 지시문 등) | 옮겨도 됨(사실상 완료, 규칙 문구는 Cowork로 적혀 있음) | CLAUDE.md 61~62행 |
| 15 | 기본값 NO_CHANGE 기록·알림 | "Cowork records it" | 사장실 스레드도 결정 문서 기록은 함. 문구 정리만 | CLAUDE.md 117행 |
| 16 | 기억 쓰기 | 직접 입력 필요(S4) | 남김 | active-decisions 31행 |
| 17 | 키움 주문 입력, 주문·정정·취소·예약, 비밀, 인증·토큰 | 누구도 안 함(입력은 사장) | **못 옮김**(절대 안전) | CLAUDE.md 18~22·46·56행 · 지침 1절 · 헌법 §2-1 적용 한계 |

오늘 Cowork를 연 5건 중 C로 없어지는 것은 2건(대조 확인·L4·L5 일지)이고, 증거 누락 실수는 C ③이 막는다. 나머지 3건(병합·S7 재실행·PC 예약 지시문)은 B로 "붙여 넣기 한 번 + 결과 자동 회수"가 된다.

# 3. C를 하면 바뀌는 곳 (K3 범위)

| 바꿀 곳 | 지금 | C 뒤 |
|---|---|---|
| CLAUDE.md 25~28행(대조 apply) · reference 112~160행 | Cowork·사장 터미널, Claude Code 금지 | + 사장실 회사PC 스레드: 사장이 그 스레드에 직접 친 `확인 <코드>`(바로 앞 제안 1건·같은 날·1회) → 같은 세션 apply → MATCH 확인 |
| apply_user_confirmed_broker_snapshot.py 30행 허용 목록 | `COWORK_CHAT_USER_MESSAGE`·`USER_TERMINAL` | + `PROJECT_THREAD_USER_DECISION` |
| reconcile_broker_state.py 349·362행 | user_message 필수는 Cowork 방법만, 없으면 코드로 대체 | 새 방법도 4칸(메시지·카드 id │ 계정 │ KST 시각 │ 원문) 필수, 일지의 형식 검사기와 같게. 머리말 7~8행·help 524행 |
| portfolio_review_journal.py 187~189·556~558행, 스키마 4행, 머리말 15~22행, CLAUDE.md 116행 | 스레드 방법 = 카드 항목만 | line_review·peak_review까지 명시(S5 activation은 제외) |
| propose 증거 검사(C ③) | 증거 없어도 진행 → S7 보류 | S5 활성 뒤 증거 없으면 거부(recon-dayfill-1120 2절 ADD (i)) |
| `.claude/settings.json` deny | apply 명령 deny(26~27행). MCP 도구에는 안 걸림 | 바꾸지 않음. 원격 스레드 발동 여부 **확인 필요** |
| 프로젝트 지침 3·4절 | apply·일지 실행 안 함(S7b 예외) | 예외를 C ①②로 넓힘(사장 직접 수정) |
| 헌법 | Cowork 언급 없음 | 변경 없음 |

절차: 사장 카드 'B + C' → 사장실 스레드가 K3 수정안 작성(recon-dayfill 2절 REPLACE와 같은 25~28행을 고치므로 한 K3로 묶음) → 사장 착수 승인(카드 탭) → Builder(worktree) → **Judge 지시문은 다른 세션이 작성** → Opus Judge → 사장 PowerShell 병합 → 사장이 지침 3·4절 수정. 반대 시험: 코디네이터가 옮긴 문장·다른 스레드 카드·전날 문장·4칸 없는 입력은 apply 거절. 권한·한도 진행 중 1건 상한(CLAUDE.md 119행)과 swing 쪽 권한 작업이 겹치는지 착수 전 **확인 필요**.

# 4. 안 비교 (모두 주문 권한·수량 권한·키움 주문 도구 그대로)

| 안 | 오늘 같은 날 사장 손 | 실수 예방 | 위조·권한 위험 | 비용 | 판정 |
|---|---|---|---|---|---|
| A 그대로 (Cowork 또는 사장 터미널) | Cowork 5번 | 없음 | 기준선 | 0 | 비효율 확인됨 |
| 5안 터미널 원클릭(10/25 미리 정한 대응) | 더블클릭 + 코드 입력. Cowork 대신 터미널 | 없음 | 기준선과 같음 | 일반 변경 1건(파일 지금 없음 — 상태 확인 필요) | 장소만 바뀌고 소통 문제는 그대로 |
| B 준비·회수 | Cowork 5번, 붙여 넣기만 | 있음(LLM 점검) | 기준선과 같음 | 0, 오늘부터 | 바로 시작 |
| **B + C(권장)** | 같은 스레드 한 줄 2번 + Cowork 붙여 넣기 3번 | 있음 — 증거 누락은 코드가 막음 | 실행 세션이 하네스 표시(from=human trust=principal)로 사장 입력을 직접 봄. 다만 스크립트는 "누가 쳤는지"를 검증하지 못하고, 스레드가 제안을 만들면 확인 코드(제안 id 앞 8자)를 스스로 안다 → 4칸 기록·반대 시험으로 보완. portfolio_state 쓰기 주체가 하나 늘어남 | K3 1건 | **권장** |
| D 전부 이전 | Cowork 0번 목표(PC 예약 지시문은 안 될 수 있음) | 같음 | **높아짐** — 스레드가 PowerShell을 실행하면 `USER_TERMINAL`·`-ApproveAuthority`를 흉내 낼 수 있고, 정책·`.claude`까지 쓰면 자기 안전장치를 고칠 수 있음 | K3 여러 건 + 설정 변경 | 비권장 |

선례 주의: 스레드 일지 경로(S7b)는 실사용 1건뿐이다(decision_journal.json의 PROJECT_THREAD_USER_DECISION 1건).

# 5. 연결표 (analysis-linkage-map 1절 8번)

| ① 자료 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 사장의 직접 입력(`확인 <코드>`·일지 결정 문장) | 사장, 사장실 회사PC 스레드 | 지금 S7b만: CLAUDE.md 35~42행 · journal.py 187~189행 | 같은 세션 apply → verify | verify 실패 시 그 스레드 즉시 보고 | **끊김** — C(K3)로 메움 |
| 대조 apply 결과(portfolio_state) | 같은 세션 | 자동 코어 06:15 대조 · auto_core_reconcile.py | 주문표 현금·보유, S7 검토선 | 아침 알림·통합 점검 | 연결 |
| 입출금 증거 | 증거 파일(cash_flow_evidence.py) | 지금: 없으면 S7 보류만(cash_flow_evidence.py 393~422행) | C ③ 뒤: propose 거부 | propose 출력 | **끊김** — C ③으로 메움 |
| 일지 L4·L5 닫기 | 같은 세션 | S7 pauses·review_lines | QQQ 관문 ⓑ 새 매수 멈춤 해제 | 통합 점검 161행 | 연결 |
| B의 Cowork 결과 | 사장실 스레드가 git log·결과 파일 읽음 | 일마다 다름(dev-runs/LATEST.json 등) | 다음 제안·관제판 | 그 스레드 보고 | 연결(규칙 변경 없음) |
| PC 예약 지시문 교체 | Cowork + PC 서명 | README 변경 기록 | 다음 예약 실행 | 결과 모음(매일 10:43) | **끊김(기술)** — 시험 1회로 확인 |

# 6. 확인 필요
- 원격 스레드에서 `.claude` deny·훅이 발동하는지.
- 기기 연결 스레드의 update_trigger(컴퓨터 연결 예약)에 PC 승인 창이 뜨는지.
- propose 출력 문구("Cowork에서 '조정 확인해줘'") 파일 위치.
- 5안(approve-1click) 현재 상태 — tools/에 파일 없음.
- 권한·한도 진행 중 1건 상한과의 겹침.
- Cowork 메시지에도 trust/role 표시가 붙는지.
- 주당 Cowork 입력 건수(오늘 5건 외 집계 없음).

# 7. 바뀔 조건
- K3 Judge가 C ①을 FAIL → ②③만 진행.
- 컴퓨터 연결 예약도 스레드에서 서명된다고 확인 → Cowork 일상 일은 병합·정책만 남음.
- 병합에 '정확한 명령 문자열만 허용'하는 장치가 생기면 → 일반 병합 이전을 다시 검토.
- 스레드에서 사장 입력이 아닌 것으로 apply가 한 번이라도 실행되면 → 즉시 되돌림.

# 사장 결정 (기록만, 승인류 실행 아님)
- 2026-11-20 11:55:27 KST, 사장 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9VXRDzaQCitKNEUSPie4Cm4(제안 id cowork-to-room-1120), 선택 'B + C (권장)', 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH. 방향 채택이다. C의 K3 착수 승인은 수정안이 나온 뒤 별도 카드로 받는다.
- 다음: B는 즉시 시행. C는 Opus · xhigh 새 스레드에서 K3 수정안(recon-dayfill 2절 REPLACE와 한 묶음) → 착수 카드 → Builder → 다른 세션이 쓴 Judge 지시문 → Opus Judge → 사장 PowerShell 병합.

# 재검토 기록
- 내장 재검토 1회(Opus 독립 작업자, 추론 노력 high — 주간 한도 경고 표시라 Fable 대신 Opus). 지적 8건 중 8건 반영: 부딪히는 결정에 Q1 추가·5안 비교(1), 7번 인용·판정 수정(2), 14~16번 추가·13번 인용(3), 'C 범위' 셈 수정·9번 분리(4), 일지 스크립트 개정 지점(5), 대조 4칸·개정 지점(6), **일반 병합 이전 제외**(7, 결론 바뀜), 비교 행·선례 1건·같은 K3 묶기(8). 원문 재확인: journal.py 68~71·185~190·554~559행, reconcile_broker_state.py 345~364행, README 81·96행, 일지 grep 1건.
- 결론이 바뀐 부분(일반 병합 제외)은 위 원문으로 직접 확인했고 추가 라운드의 새 지적 없음.

검토 완결: 원문 확인 CLAUDE.md 1~138행 · approval-without-cowork 1~53행 · approval-venue-table 1~45행 · active-decisions 31·83·84·85·89·123행 · README 10~25·81·92~101행 · reference 60~209행 일부 · journal.py·reconcile_broker_state.py 위 행 · holding-cards-LITE-SOXL 120~132행 · recon-dayfill-1120-proposal 8·23·30행 · constitution-v1.5.0 166~192행 · 내장 재검토 1회(반영 8건) · 미해결 확인 필요 7 · 자료 시점 2026-11-20 12:0x KST(main 22d44cf) · 바뀔 조건 위 4개
