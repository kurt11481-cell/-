---
id: approval-without-cowork-review-2026-10-25
title: "Cowork 창에 직접 입력하지 않고 승인하는 방법 검토"
date: "2026-10-25"
status: "검토 완료(읽기 전용). 사장 결정 대기 1건. 아무것도 켜거나 바꾸지 않음"
class: "문서. 승인류 실행·설정 변경·K3 지시문·개발 큐 등록·키움 도구 호출 없음"
authority: "order_authority=false · quantity_authority=none · 키움 주문 도구 금지"
consumers: "사장 · 사장실 코디네이터"
---

# 결론
**권장: 바꾸지 않는다(NO_CHANGE). 이미 Cowork 밖의 승인 경로가 있다 — 사장 본인 터미널(`USER_TERMINAL`). 지금 당장 Cowork를 열기 싫을 때는 그 경로를 쓰면 되고, 지침·CLAUDE.md·코드 변경은 0이다.**
- 승인을 "사장실 채팅에 치고 다른 곳이 실행"하는 방식은 안전하게 만들 수 없다. 실행 주체(Cowork)가 사장실 메시지를 읽을 수단이 없어 ⓪이 실패했고(projects-new-1c-test-2026-10-25.md "Cowork 쪽 시험 결과"), 읽혀도 서버 필드에 trust/role·편집·출처가 없다(같은 문서 "읽기 결과에 나타난 필드").
- 사장이 결정할 것(1줄): **지금 방식(Cowork 입력 또는 사장 터미널)을 유지할지, 터미널 승인용 원클릭 실행 파일(5안)을 개발 큐에 올릴지.** 권장은 유지.

# 먼저 알아야 할 사실 (원문 확인)
1. **승인 확인 스크립트는 "누가 쳤는가"를 기술적으로 검증하지 않는다.** `apply_user_confirmed_broker_snapshot.py:270-281`은 코드 일치(`confirm_code`)와 방법 값이 허용 목록(30행 `("COWORK_CHAT_USER_MESSAGE","USER_TERMINAL")`)에 있는지, `user_message`에 코드가 들어 있는지만 본다. `reconcile_broker_state.py`·`portfolio_review_journal.py`에는 `isatty`·`stdin` 검사가 없다(grep 0건). 즉 위조 방어는 절차(CLAUDE.md 25-27·31-34: Claude Code·Codex·예약·Judge는 apply 금지, "코드를 지어내거나 재사용 금지")이지 암호가 아니다. 어느 안이든 위조 위험은 이 기준선보다 낮아지거나 같을 수 있을 뿐, 이 절차 위에 있다.
2. **Cowork 밖 경로는 이미 허용돼 있다.** CLAUDE.md:25-27 "…`apply` runs in Cowork after the user sends '확인 <code>'… **or by the user in their own terminal**", broker-snapshot-reconciliation.md "3. Fallback: the user's own Windows terminal"(`apply --confirm <code> --confirmed-via USER_TERMINAL`). 일지 apply도 `USER_TERMINAL` 허용(portfolio_review_journal.py:17-18·67).
3. **스크립트가 있는 승인류만 터미널 경로가 있다.** 대조 apply · 일지 apply · `dev-merge.ps1 <id> -ApproveAuthority`(dev-merge.ps1:3-9, 사장 PowerShell 사용 예 3행). 정책·상태 변경, decision_mode "켜", 예약 작업 변경, 기억 쓰기는 스크립트 검사가 없고 "사장이 이 세션에서 말했는가"를 실행 에이전트가 판단하는 구조라 터미널로 대체할 수 없다(켜는 방법은 확인 필요).
4. 사장실 스레드가 받는 사장 메시지에는 하네스가 붙인 `trust="principal"`이 있다(이 스레드 wake). 그러나 이는 하네스 알림이지 읽기 도구 출력이 아니고 Cowork에도 같은 게 오는지 확인 못 했다(1c-test 한계 1).

# 후보 비교 (검토 순서 NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD)
| # | 안 | 위조 위험 | 바꿔야 할 곳 | 사장 손 | 구현 규모 | 판정 |
|---|---|---|---|---|---|---|
| 1 | **NO_CHANGE** — Cowork에 직접 입력 | 기준선(절차) | 없음 | 승인 1건당 Cowork 열기 +1 | 0 | **유지(권장)** |
| 2 | **REUSE** 사장 터미널 `USER_TERMINAL` | 기준선과 같음. 에이전트는 사장 터미널에 못 들어가므로 provenance는 오히려 더 분명(단, 스크립트가 TTY를 검사하지 않아 에이전트의 거짓 `--confirmed-via`는 기술적으로 막히지 않음 — 기준선과 동일) | 없음(이미 CLAUDE.md:26·reference에 있음) | PowerShell 열기 → 폴더 이동 → 명령 붙여넣기. Cowork 열기보다 낫다고 말할 수 없음(초보자에겐 같거나 약간 더 번거로움) | 0 | **Cowork 안 열 때의 대체 경로(권장 동반)** |
| 3 | REUSE 사장실 회사PC 스레드/Remote Control에 사장이 직접 입력, 그 세션이 apply | 직접 입력 메시지의 trust는 하네스가 줘 가장 강한 LLM 쪽 증거. 단 relay·예약과 구별되는 필드가 Cowork/RC에서도 같은지 확인 필요. 이 세션은 키움·셸 주변 도구 접근 범위가 넓음 | CLAUDE.md 27·34("Claude Code… never run apply"), 지침 3절(스레드 apply·셸 금지), 지침 4절. 실행 도구는 Desktop Commander가 필요(지침 3절 금지) | 사장실에서 한 줄(손 +0) | 중~대: K3(권한 확대, 실행 주체 추가), Opus Judge, 병합 뒤 반대 시험 | 불가 — 지금은 금지 규칙과 정면 충돌, 이득이 위험보다 작음 |
| 4 | REPLACE 승인 파일: 사장실 승인을 파일로 남기고 Cowork가 확인 | **높음** — 파일은 코디네이터·어느 에이전트나 쓸 수 있어 사장이 쳤다는 증거가 없다. 지침 4절이 "코디네이터가 옮긴 문장은 승인 아님"으로 이미 금지 | 지침 4절 완화 필요(안전 규칙 후퇴) | 손 +0 | 소 | **기각** |
| 5 | ADD 사장 터미널용 원클릭 실행 파일(`승인.cmd`: 대기 제안 표시 → 코드 입력 → 2안 명령 실행) | 2안과 같음(실행 파일이 코드를 대신 만들면 안 됨 — 사장이 코드를 직접 입력) | 새 파일 1개 + 문서 1줄. CLAUDE.md는 "…or by the user in their own terminal"에 이미 포함 | 더블클릭 → 코드 입력 1회 | 소(일반 변경 파이프라인) | 선택 — 사장이 터미널 경로를 자주 쓰게 될 때만 |
| 6 | ADD 1회용 코드·서명(전화 앱 TOTP 또는 사장 키) | 키가 PC에 있으면 같은 Windows 계정의 Desktop Commander로 읽혀 위조 가능. 키가 전화에만 있으면 안전하나 검증 키를 PC에 둘 방법(비대칭 서명)이 필요 | 스크립트 3개 + 스키마(confirmation_method enum, additionalProperties false) + 지침·CLAUDE.md | 전화 열기 + 코드 입력(손 +2) | 대: K3, 테스트·반대 시험 필요. 그리고 입력할 곳이 결국 Cowork나 터미널이라 "Cowork 안 열기"는 해결 못 함 | 기각(비용 대비 이득 없음) |

# 왜 1·2가 남는가
- **안전한 승인에는 "실행하는 쪽이 직접 보는 사장의 입력"이 필요하다.** 사장실 → 실행 주체 사이 전달(코디네이터 요약·파일·버튼)은 모두 지침 4절이 이미 승인이 아니라고 못 박은 형태다. 그래서 선택지는 (가) 실행 세션에 사장이 직접 입력 = Cowork, (나) 사장이 직접 실행 = 터미널, 둘뿐이다. 둘 다 이미 허용돼 있다.
- "손 줄이기"가 목적이면 3안이 이론상 유일하지만, 현 규칙이 의도적으로 막은 쪽(CLAUDE.md 27·34)이고 ⓪ 시험 결과도 사장이 11:32에 멈추기로 했다(1c-test "사장 결정").

# 사장이 할 일 (바꾸지 않는 경우)
- 평소: 승인이 필요하다는 알림이 오면 Cowork 새 창에서 "확인 <코드>"를 직접 입력(현행).
- Cowork를 열기 싫을 때: 알림에 적힌 명령을 사장 PowerShell에 붙여 넣어 실행(코드는 알림에서 그대로 복사, 지어내거나 다른 제안의 코드 재사용 금지). 명령 형태는 reference "3. Fallback" 참고.

# 바뀔 조건
- Cowork가 사장실 메시지를 id로 읽을 수 있고 trust/role·편집·출처 필드가 보임(1c-test "바뀔 조건") → 3안을 다시 안건으로 꺼낼 수 있다.
- 승인류가 주 몇 건인지 데이터가 쌓여 Cowork 열기 부담이 크다고 확인됨(건수는 확인 필요) → 5안 검토.
- apply 스크립트에 TTY 검사 추가 같은 강화는 권한을 늘리지 않으므로 사장 판단에 따라 별도 일반 변경으로 가능(이번 범위 밖, 확인 필요: reconcile_broker_state.py 289·301행 흐름).

# 사장 결정 (기록만, 승인류 실행 아님)
- 2026-10-25 11:45 KST(02:45:12Z), 프로젝트 스레드 cmsg_0137MRzn9nuDvvQmVxm6WeX93sh53UmErSdcqE9uV1HX5E, 사장 원문: "권장안 승인". 내용: 권장안(NO_CHANGE 유지, Cowork 입력 또는 사장 터미널) 채택. 변경 0, 개발 큐 등록 없음.

# 확인 필요
- decision_mode "켜"·정책 편집의 터미널 경로 존재 여부
- 사장이 지금 터미널 경로를 실제로 쓰는지(사용 빈도)
- Cowork·Remote Control 세션의 사용자 메시지에 trust/role 필드가 붙는지

검토 완결: 원문 확인 apply_user_confirmed_broker_snapshot.py:30·238-290 / reconcile_broker_state.py(8·289·301·463, isatty/stdin 0건) / portfolio_review_journal.py:17-18·67 / CLAUDE.md:25-37·52-62·114-118 / dev-merge.ps1:3-20·61 / broker-snapshot-reconciliation.md 3절 / projects-new-1c-test·1c-cowork-check·board-design 0·5절 · 내장 재검토 없음(권한 변경을 제안하지 않는 NO_CHANGE 권고) · 미해결 확인 필요 3 · 자료 시점 2026-10-25 · 바뀔 조건 위 3개
