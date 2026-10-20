# pending-r5-align — R5 정의를 S7과 일치 (Builder 초안, 2026-10-20)

효력: 독립 Judge PASS(별도 Claude Code 세션, docs/claude/r5-align-judge-prompt.md) + 사용자 승인 1줄(예: `결정 r5-align 적용: 승인`) 뒤, 같은 Cowork 세션에서만. 그 전에는 아무것도 바뀌지 않는다(현행 로더 v3.12.8-L+R2 91c1e762… · 규칙 파일 v3.12.8 f5e4b9c8… 유지). 근거: docs/claude/r5-align-2026-10-20.md(결정 "r5-align: 1", 2026-10-20 08:04 KST) · Builder 보고 docs/claude/r5-align-report.md.

## 변경 기록
- 2026-10-20 08:xx KST — Builder(Cowork) 초안. 규칙 파일 v3.12.9: 1행 머리말 · 101행 2-3) ③(R5 추가 매수 멈춤 = ㉮ 이번 기준 세션의 S7이면 peak_reviews pause_add_recommendations 그대로, ㉯ 그 밖(S7 없음·오래됨·직전 세션 S7·종목 없음·status≠OK)은 pause_add true 또는 종가 ≤ 0.70×P면 멈춤(fail-closed), 가격 상태 표시만, peakReviews state = 멈춤 상태) · 134행 3) 매수 요건 ② 보유 (추가) 행 문구. 로더 v3.12.9-L+R2: 규칙 파일 경로·해시·writer·머리말만. 자동 운영 코어는 이미 S7 사건형이라 코드 변경 없음. 예약 작업 변경 없음.
- 같은 날 내장 재검토(Opus) 반영: ㉮를 "신선(직전 세션 포함)"에서 "이번 기준 세션"으로 좁힘(직전 세션 S7은 그 뒤 새 이탈을 모름 — 10-13 실행 실례, 코어는 최신 세션만 받음 auto_core_decide.py 950~951행). 해시 fbb05122… → 0c30e9c7…, 로더 ed8a2cd1… → 9b65d8af….
- 같은 날 2회차 재검토 반영: 101행 앞부분 "가격 상태는 표시만"을 "㉮에서는 표시만, ㉯에서는 멈춤 판정에 씀"으로(글자 충돌 제거) · 134행·머리말·로더 1행 요약에 ㉯의 "pause_add true" 분기 추가 · 멈춤 문구를 열린 사건("검토 개시 — 카드 다시 쓰기")과 ㉯ 자료 공백("R5 추가 매수 멈춤(fail-closed …) · 카드 다시 쓰기 아님")으로 나눔, 어느 것도 결정 필요로 올리지 않음. 해시 0c30e9c7… → 75fcd5de…, 로더 9b65d8af… → 6f65c89b….
- Judge가 FAIL하면 이 판(v3.12.9)은 쓰지 않는다 — 고친 판은 새 이름(v3.12.10)·새 해시로 만든다(23:30 자동 커밋으로 v3.12.9 초안이 이미 커밋됐을 수 있다).

## 1. 예약 지시문 교체 (재서명)
| 파일(이 폴더) | sha256(LF 파일) | 교체 대상 | 바뀐 곳 |
|---|---|---|---|
| integrated-check-prompt-v3.12.9-2026-10-20.txt | 75fcd5deff628549f10a61a7a628e6693107db317e071cd9994f654fc8fb7722 | 이미 docs/claude/ 같은 이름으로 있음(로더가 읽는 경로, 바이트 같음) | 1·101·134행 |
| integrated-check-daily.txt | 6f65c89b8a18283e5ced365cd058ed871440d9f7ecf1c6b27e3a2decbd4cfff9 | 예약 trig_01YWzNq847nJfNgDUnnukBqP(통합 점검 화~토 06:40) | 1행 머리말 · 4·12행 규칙 파일 경로 · 18행 해시 f5e4b9c8… → 75fcd5de… · 75행 writer v3.12.9-L+R2 |

교체 순서(Cowork):
① 예약 목록 조회로 통합 점검 예약 본문 sha256 = 91c1e762bdf2419153fa66d575811641975062164d5fa5c609b116d8c321ff9b(scheduled-prompts/README.md 11행)인지 확인. 다르면 멈추고, 그 사이 바뀐 줄을 이 폴더 로더에 옮긴 뒤 새 해시로 다시.
② docs/claude/integrated-check-prompt-v3.12.9-2026-10-20.txt sha256 = 75fcd5de…인지 확인.
③ 통합 점검 실행 중(화~토 06:40 시작)과 겹치지 않는 시각에 update_trigger 1번(이 폴더 integrated-check-daily.txt 본문 그대로, 16,563자·22,670바이트 — 운영 중인 관심 명단 재채점 본문 사본(README 16행 해시 a809c649…와 같은 파일, 36,988자·50,998바이트 실측)보다 작아 길이 거절 가능성은 낮다). 응답 "prompt re-signed" 확인, 응답 본문 sha256 = 6f65c89b….
④ scheduled-prompts/README.md 표 11행(로더 이름·해시)과 변경 기록 1줄, scheduled-prompts/integrated-check-daily.txt를 이 폴더 파일로 교체.
⑤ docs/claude/t2-rc-preregistration-2026-10-14.md 변경 기록 1줄: 로더 v3.12.9-L+R2 6f65c89b… · 규칙 파일 v3.12.9 75fcd5de… · 계산기·실행기·알림 그대로. 코어·계산기 불변이라 C1 재시작 없음.
⑥ 관제판(docs/claude/dev-dashboard-protocol.md) r5-align 작업만.
⑦ 첫 확인(교체 뒤 첫 06:40 실행과 08:50 결과 알림): 1단계 MATCH · needs·결정 필요에 R5 해석 차이 없음 · peakReviews state가 코어 exposure.peaks state와 맞음(S7 OK·종가 ≤ 0.75×P면 near) · decide compare unexplained에 R5:*·R5 사유의 buyReq:<보유>:2 없음. 표시 메모: 통합점검 대시보드의 "고점 −30% 검토 (R5)" 표 "상태" 칸은 이제 멈춤 상태라 near가 "근접"으로 읽힐 수 있다 — 칸 이름 바꾸기는 별도 표시 작업 후보(K1).

되돌리기: 로더 v3.12.8-L+R2 본문(scheduled-prompts/pending-rrec-ev4/integrated-check-daily.txt, 91c1e762…)으로 update_trigger 1번. 규칙 파일 v3.12.8은 그대로 남아 있다.
