# 비서 제안 사장실 이관 설계 3판 (2026-11-25 KST)

근거: schedule-to-room-1124(사장 카드 '전부 이관' 2026-11-24 13:13:57), 지침 v2.19 3절·4절 ⑦⑧, 원 제안서 3절, 사장 카드 '1장 (시험 통과 시 자동 이관)'(2026-11-25 09:58:49 KST). 2판 대비 독립 검수(새 Fable high 스레드, review/independent-review-2026-11-25.md) 필수 8건·권장 7건 반영(9절).

## 0. 결론
비서 제안 새 예약을 '그림자'로 5회 돌리고, 아래 3절 기준을 모두 통과하면 같은 승인 1장으로 옛 Cowork 예약을 끄고 새 예약을 정식 본문으로 바꾼다. 불통과·기한 초과면 그림자를 끄고 멈춰 보고한다. 통과 판정은 새 Fable 스레드가 파일로 남기고, 옮기는 실행은 예약이 깨운 턴이 아니라 이관 스레드의 대화 턴에서 판정 파일·당일 해시를 다시 대조한 뒤 한다.

## 1. 옛값·새값 (지침 4절 ⑦ — '확인 필요' 칸은 예약 전용 스레드를 만든 뒤 실제 값으로 채운 다음 카드)
| 항목 | 옛(Cowork) | 그림자 | 옮긴 뒤 |
|---|---|---|---|
| 일정 | 월~토 09:25 KST | 월~토 09:27 | 월~토 09:25 |
| 모델 | claude-sonnet-5-5 | **claude-opus-5-5 · medium**(예약 전용 스레드 cse_01KuMGKfQLYvw8SXh4CXihrv, get_session 2026-11-25 10:14 KST — Sonnet 요청이 먹지 않음) → 카드 첫 줄 '모델 바뀜(Sonnet→Opus)' | 같음 |
| 폴더 | 코덱스저장소 1개 | **코덱스저장소 1개**(같은 get_session userSelectedFolders) — 넓어지지 않음 | 같음 |
| 권한 모드 | auto | **auto**(같은 get_session) — 높아지지 않음 | 같음 |
| 실행 방식 | 매번 새 세션 | 예약 전용 스레드 1개를 깨움(persistent_session_id) | 같음 — 그림자 예약과 그 스레드를 그대로 바꿔 씀(새 스레드·새 예약은 새 승인) |
| 알림 | 폰 push 켜짐(예약 알림 + PushNotification) | 없음(예약 알림 값 없음 — persistent 예약은 notifications 칸을 받지 않음, PushNotification 안 부름) | PushNotification 1줄 + 스레드 1줄 |
| PC 쓰는 곳 | workspace/outputs/secretary/ | workspace/outputs/room-shadow/secretary/ | workspace/outputs/secretary/ |
| 클라우드 중계 사본 | /mnt/user-data/outputs/ | /mnt/project-files/room-shadow/secretary/ | /mnt/project-files/secretary/ |
| 지시문 | 전체 본문 | 로더 52139d50… + 본문 160e5a25… | 로더 89f2b15c… + 본문 542f5253… |
| 클라우드 즉석 계산 | 있음(5) python) | 같음, 읽은 글자를 코드에 넣지 않음 | 같음 |

create_trigger 값(그림자): name '[그림자] 비서 제안', cron 'CRON_TZ=Asia/Seoul 27 9 * * 1-6', persistent_session_id = session_01KuMGKfQLYvw8SXh4CXihrv(스레드 '예약: 비서 제안(그림자)'), prompt = 그림자 로더 전문, notifications·create_new_session_on_fire 넣지 않음. 만든 뒤 get_trigger로 지시문 해시 = 52139d50… 확인.

## 2. 파일 (impl/, PC 반영 위치 docs/claude/scheduled-prompts/room/)
그림자 본문·로더, 옮길 본문·로더, diff 2개, h1-report.md(2판 해시, migrated_check 20/20). room-migrated.json에 그림자를 만든 날 등록(name '[그림자] 비서 제안', body_path …/room/secretary-shadow-body-v1.txt, body_sha256 160e5a25…, cron 위 값, model "", changes[].at = create_trigger 응답 updated_at). 옮길 때 같은 항목을 옮길 판 값으로 바꾸고 changes에 더함.

## 3. 통과 기준 (사전 등록 — 판정자가 회차별 ①~⑧ 표를 판정 파일로 남김)
| | 기준 | 재는 법 |
|---|---|---|
| ① | 같은 입력 | 그림자·옛 파일의 후보 id 전체(오늘 제안·그 밖 후보·멈춤 의심)와 '## 확인 필요'의 읽기 실패 항목이 같음. 다르면 그 작업의 관제판 갱신 시각이 두 실행 사이일 때만 인정. 설명 안 되는 차이 2회 이상 = 불통과 |
| ② | 형식 | 머리말 5칸(id·type·as_of·consumers·items) + '## ' 머리 4개(오늘 제안·그 밖 후보·멈춤 의심·확인 필요) |
| ③ | 저장 | 판정자가 PC 파일 크기 = /mnt/project-files/room-shadow/secretary/ 사본 크기를 직접 대조, 크기 > 0 |
| ④ | 시각 | PC 파일 수정 시각이 그날 그림자 스레드 '[그림자] 본문 해시 일치' 글 뒤, 같은 날짜 |
| ⑤ | 금지 행동 0 | 그림자 스레드에 결정 카드 0, 글은 해시 줄 + 알림 줄(또는 실패 1줄)만, room-shadow\secretary\에 날짜 파일 말고 없음, secretary\에 <날짜>-2.md 없음·<날짜>.md 수정 시각이 옛 실행 시각, 금지 경로(docs/claude/scheduled-prompts/, CLAUDE.md, .claude/, tools/, 정책·상태 파일)에 그림자 실행 시간대 변경 0(그 밖 경로는 판정에 안 씀), 결과 모음에 그림자 밖 '바뀐 예약' 줄 0 |
| ⑥ | 로더 | 스레드 글 '본문 해시 일치' + 판정 때 get_trigger 지시문 해시 = 52139d50…(끝 줄바꿈이 빠진 값 1035ba12…도 일치로 봄; 옮긴 뒤는 89f2b15c… 또는 31f88e12…) |
| ⑦ | 이관 대조 | 1회차 전에 room-migrated.json 등록 확인 + 판정자가 대조 스크립트를 직접 1회 실행해 RESULT OK + 세는 날마다 결과 모음 글에 🔴·'대조도 못 함' 없음 |
| ⑧ | 새만 실패 0 | 옛이 됨 = secretary/<날짜>.md 있고 크기 > 0. 그날 옛이 됐는데 그림자가 ②~⑦ 중 하나라도 어기면 실패 → 즉시 불통과. ①의 설명 안 되는 차이는 1회째는 기록만, 2회째에 불통과 |
참고 칸(판정에 안 씀): items 순서·문구 차이, last_served_model.
5회 = 옛·새가 둘 다 돈 날 5회(옛이 안 된 날은 셈에서 뺌; 제안서의 '5개장일'을 이렇게 바꿈). 10실행일 안에 못 채우면 그림자를 끄고 보고. 본문·로더를 고치면 새 해시·새 카드·5회 처음부터.

## 4. 1회차 확인 (R5)
그림자 첫 실행(만든 다음 실행일 09:27) 뒤 이관 스레드가 그날 첫 턴에 기기 연결·관제판 읽기·파일 크기를 보고 사장에게 1줄. 기기 연결 실패면 그 자리에서 멈추고 보고(5회 세기 시작 안 함).

## 5. 옮기기 (통과 판정 뒤, 이관 스레드 대화 턴)
1) 판정 파일과 당일 해시(get_trigger 그림자 지시문, 옮길 본문 PC 파일 — 옮길 본문·로더는 그림자를 만들 때 그림자 본문과 함께 PC docs/claude/scheduled-prompts/room/에 둠) 다시 대조. 2) 시간창 = 09:40 뒤 ~ 다음 날 09:20 전(결과 모음과 겹치지 않게). 3) 옛 예약 끄기(update_trigger enabled false, 지시문 없이). 이 예약은 컴퓨터 연결 예약이라 허용 카드나 PC 승인 창이 한 번 더 뜰 수 있음(확인 필요) — 뜨면 그 답을 기다리고, get_trigger로 꺼진 것을 본 뒤에만 4). 4) 그림자 예약 자체의 이름·일정(09:25)·지시문을 옮길 판으로 바꿈(같은 스레드). 5) room-migrated.json·README 표·변경 기록·관제판 schedules·결과 모음 표 갱신(본문 파일은 이미 PC에 있음). 6) room-shadow 폴더는 남김.

## 6. 옮긴 뒤 첫 실행 기준·되돌리기 (F4)
통과 = 09:35 결과 모음 전에 secretary/<날짜>.md 있고 PC 크기 = 클라우드 사본 크기 + 새 스레드에 해시 줄·알림 줄 + PushNotification이 오류 없이 끝남(또는 ' · 폰 알림 못 보냄' 없음). 확인 = 이관 스레드가 그날 첫 턴(그 전에는 결과 모음의 '안 돎·늦음' 줄이 알림). 알림 조건이 아닌 날은 알림 줄이 없으므로 그날은 해시 줄 + 파일로만 판정하고, 폰 도달은 알림 조건이 처음 충족된 날 사장에게 1줄로 확인받음. 하나라도 어기면 그날 안에 새 예약 끄기 → 옛 예약 다시 켜기(같은 카드 범위, 켜기 때도 허용 창이 뜰 수 있음).

## 7. 승인 1장이 덮는 범위 (F8 — 카드에 그대로 열거)
① 예약 전용 스레드에 그림자 예약 만들기(1절 값) ② 본문·로더 4개 PC 반영과 room-migrated.json·README 등록 ③ 통과 시 옛 예약 끄기 ④ 통과 시 새 예약 지시문·이름·일정을 옮길 판으로 바꾸기 ⑤ 불통과·기한 초과·첫 실행 실패 시 그림자/새 예약 끄기와 옛 예약 다시 켜기. 해시 4개(52139d50… · 160e5a25… · 89f2b15c… · 542f5253…). 이 밖의 변경은 새 승인.

## 8. 연결표 (R7)
| 산출 | 읽는 곳 |
|---|---|
| 그림자 결과(room-shadow/secretary) | 판정 스레드 → 옮기기·중단. 코어·대시보드·스크립트는 읽지 않음(git grep: room-shadow 참조 0, workspace/outputs 전체를 훑는 스크립트 0). 23:30 자동 커밋 대상인지는 확인 필요(.gitignore 대상 아님) |
| 옮긴 실행(secretary/) | 결과 모음 표의 '비서 제안' 행, 비서실 대화(옛과 같음) |
| 로더·본문 해시 | 결과 모음 1-1) 대조 → 🔴 |
그림자 기간 동안 결과 모음 글 '예약 N개 돌았음'에 그림자가 하나 더 셈해진다(정상).

## 9. 독립 검수 반영 기록
필수 F1~F8, 권장 R1~R7 모두 반영. F2·F5·F6의 실제 값은 예약 전용 스레드를 만든 뒤 1절 '확인 필요' 칸에 채운다. R6: 판정 때와 옮기는 턴에 get_trigger 지시문 해시를 로더 파일과 대조(3절 ⑥, 5절 1)).

## 10. 되돌리기
그림자 단계: 그림자 끄기·room-migrated.json에서 빼기, 옛 예약은 손대지 않음. 옮긴 뒤: 6절.
