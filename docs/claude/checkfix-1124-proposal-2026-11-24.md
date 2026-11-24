---
id: checkfix-1124
type: proposal
status: 승인 대기 (예약 작업 변경)
as_of: 2026-11-24
source_decision: "ceo-2026-11-22 D1 'a) 고침' (2026-11-24 10:02 KST 사장실 결정 카드 — 기록용, 실행은 별도 승인) · ceo-weekly-report.md:1044-1045"
---

# 주간 팀장회의 관제판 점검 스크립트(check.py) 고침 — 제안서

부딪히는 결정: period-return-g10-1123(active-decisions.md:173, "check.py 그대로")·org-stage2-1113(active-decisions.md:150) — 주간 팀장회의 지시문 교체는 `예약 작업 변경 승인: 주간 팀장회의` 사장 직접 입력으로만 한다. 이 제안도 그 경로를 따른다.

## 1. 결론
- 멈춘 보고는 **11/22 한 번**이다(ceo-weekly-report.md:1068 "점검 불완전(스크립트)"). 10/25·11/01·11/08·11/15는 정상(:258 17건 · :485 19건 · :704 23건 · :878 11건). 보고의 "계속 6주째"(:1050)는 F-OPS-4 번호가 이어진 주 수다(ceo.py:252·254가 '불완전'과 '어긋남 n건'에 같은 번호를 씀).
- 원인: `check.py` 42행이 관제판 예약 기록의 갱신 시각이 비면 `None + timedelta`로 TypeError를 낸다. 관제판 schedules 24건에는 **문서 단위 갱신 시각이 모두 있다**(2026-11-24 10:1x KST ArtifactData list). 그런데 10건에는 data 안에도 같은 이름 칸 `updatedAt`(모두 2026-11-09T11:55:00+09:00)이 있고 나머지 14건에는 없다. 지시문 2)(ceo-weekly-meeting.txt:19)가 "id, name, updatedAt"라고만 해 어느 값인지 정하지 않았다. 11/22 실행이 data 쪽을 옮겨 trigs가 있는 6건(sch-board·boardreview·nextsndk·preevents·save·watchrot)이 null이 된 것으로 보인다 — 그 실행의 in.json은 못 봄(확인 필요). 근거: 지난 보고의 관제판 기록 시각(:488·:490 "10/27 20:04")은 문서 단위 값(2026-10-27T11:04:41Z)과 같다.
- 고침 두 가지(한 번에):
  ① 지시문 2)에 "updatedAt = 문서 단위 값, data 안 값은 쓰지 않음" 한 구절.
  ② check.py v1.1 — 시각이 없거나 형식이 달라도, 이름·문구·머리 칸이 null이어도 멈추지 않는다. 시각을 못 대조한 기록은 R1 한 줄 "수정 시각 대조 못 함 — … 갱신 시각 없음·형식 다름 (확인 필요)"(기록마다 1번). 나머지 판정은 그대로.
- 경로: 개발 큐가 아니라 **예약 작업 변경**(지침 4절). check.py sha256이 지시문 3)(:20)에 박혀 있어 둘을 함께 바꿔야 하며, ceo.py v1.6 교체와 같은 길이다. 관제판에 값을 더 채우는 일은 하지 않는다(같은 이름 칸을 늘리는 처방이라).

## 2. 바뀌는 것 (sha256, LF 기준 = 실행이 CR을 지운 뒤 값)
| 파일 | 지금 | 바꿀 것 |
|---|---|---|
| ceo-weekly/check.py | 1963295fa25091d335cb5d731126794cc109e8dd60e4cd3ab7fe94f55830173c (v1.0, 5,506 B) | 07f075487a85a8994d25955d962592ca167b86dd8c72ed541e52b439e7b57d62 (v1.1, 5,910 B) = pending-checkfix-1124/check-v1.1.py |
| 주간 팀장회의 지시문 (trig_01XvqwKG2gt7EKLEVMHGYR6Y) | eecc28975ab83aaf788d8afb191dd270471706843421fb443023bf9dd87cfb40 (v1.6, 25,154 B) | 6caaea5e81b9f4da0fa9263901cad05fc130be7bfe51558a6fa8bd74252c0466 (v1.6.1, 25,754 B, 끝 줄바꿈 있음) = pending-checkfix-1124/ceo-weekly-meeting-v1.6.1.txt |
| ceo-weekly/ceo.py | 3abd1497… | 그대로 |

- 지시문 diff(pending-checkfix-1124/ceo-weekly-meeting-v1.6-to-v1.6.1.diff): 머리 줄(v1.6.1 + 한 문장) · 2) 한 구절 · 3) check.py 해시. 그 밖 바이트 동일.
- check.py diff(pending-checkfix-1124/check-v1.0-to-v1.1.diff): iso() 예외 처리 · name/text/head null 처리 · 42~48행 '대조 못 함' 줄 · R6 날짜 형식 처리.
- 불변: 일정(일 09:47)·모델(claude-sonnet-5-5)·폴더 1개·권한 모드·읽기·쓰기 범위·ceo.py.
- 점검 약화 아님(멈추던 점검이 돌고 '확인 필요' 줄이 생김). R4의 마감·재개일 형식 오류는 이번 범위 밖(11/15까지 문제없었음, 보고에서 빠지는 점검).

## 3. H1 시험 (클라우드, 2026-11-24 KST, 기대값을 먼저 적고 돌림 — pending-checkfix-1124/h1/expect.txt)
입력 = 실제 관제판 schedules 24건(문서 단위 시각은 같은 날 list 값) + trigs에 맞춘 **가짜 예약 목록**(시각 고정) + 작업 1건. 실제 list_triggers·tasks로는 돌리지 않음 → 적용 뒤 첫 실행(11/29)으로 확인.
| 경우 | 기대 | v1.0 | v1.1 |
|---|---|---|---|
| ⓐ 문서 단위 시각(실제 응답 모양) | 둘 다 종료 0, 출력 같음 | 종료 0 | 종료 0 · 출력 바이트 동일 |
| ⓑ data 안 시각(6건 null = 11/22 추정) | v1.0 TypeError, v1.1 대조 못 함 6줄 | 종료 1 TypeError | 종료 0 · 6줄 |
| ⓒ 가짜 이상(관제판 시각 '10/27 20:04'·예약 시각 null·head·text·name null) | v1.0 멈춤, v1.1 종료 0 + 대조 못 함 2줄 | 종료 1 ValueError | 종료 0 · 2줄(+ 이름 없는 Windows 기록 1건이 "trigs 없는 관제판 항목: None"으로 보임) |
- ceo.py는 "RESULT n건"과 "R1 …"/"미점검 …" 줄만 읽으므로(ceo.py:245~256·352) 새 문구도 그대로 셈·표시된다.

## 4. 적용 뒤 첫 보고에서 보일 것
- F-OPS-4: "관제판 점검 불완전"(🟠) → "장부 어긋남 n건"(ℹ, 회사 상태 색에 안 들어감). 번호 기준이라 '계속 7주째'로 찍힌다(ceo.py:508).
- '대조 못 함' 줄도 '장부 어긋남 n건'에 함께 세어진다(ceo.py는 안 바꿈). 지시문 2)를 바로잡으면 평소 0건.

## 5. 승인·적용 순서
0. 승인 전(이 제안과 함께): pending-checkfix-1124/(check-v1.0.py·check-v1.1.py·두 diff·지시문 v1.6.1·h1/)와 이 제안서를 저장소에 두고 해시 확인.
1. 사장이 이 스레드에 직접 입력: `예약 작업 변경 승인: 주간 팀장회의` (같은 날 KST, 바로 앞 제안 1건, 1회).
2. 같은 세션, 이 순서로: ① update_trigger로 지시문을 v1.6.1 파일 그대로 + 이름 "주간 팀장회의 v1.6.1 (일 09:47)"(막히면 비서실 직접 지시 경로) ② 사장 PC 승인 창은 사장이 직접 누름 ③ get_trigger 응답 본문 + 끝 줄바꿈 1개의 sha256 = 6caaea5e… 대조 ④ **그 뒤에** ceo-weekly/check.py를 v1.1로 바꿈 ⑤ check.py를 다시 받아 `tr -d '\r' | sha256sum` = 07f07548…, ceo.py = 3abd1497… 확인 ⑥ ceo-weekly-meeting.txt 보관본을 v1.6.1로, README 15행 해시·변경 기록, 관제판 sch-boardreview 이름·note, active-decisions 한 줄, _pending 목록(check.py 포함).
3. ①~⑤ 중 하나라도 실패하거나 11/28(토)까지 지시문·check.py가 짝이 안 맞으면 같은 세션에서 둘 다 v1.6·v1.0으로 되돌리고 해시를 다시 확인. 일요일 09:47 전후에는 손대지 않는다.
4. 승인이 11/28을 넘기면 D1 기본값(현행 유지) — 그 주 회의는 세션이 어느 칸을 읽느냐에 따라 다시 멈출 수 있다.

## 6. 되돌리기
check.py ← pending-checkfix-1124/check-v1.0.py(1963295f…), 지시문 ← pending-period-return-g10/ceo-weekly-meeting-v1.6.txt(eecc2897…), 이름 "주간 팀장회의 v1.6 (일 09:47)". 지시문 되돌리기도 update_trigger + 사장 PC 승인이 다시 필요. 관제판 sch-boardreview 이름·note, README·보관본도 되돌린다.

## 7. 연결표 (analysis-linkage-map-2026-10-05.md 1절 8번)
| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| board.txt(R1·R2 줄) | 주간 팀장회의 trig_01XvqwKG2gt7EKLEVMHGYR6Y 일 09:47, ceo-weekly-meeting.txt:29 → check.py v1.1 21~64행(R1 21~55, R2 56~64) | ceo.py:245~256(RESULT·R1·R2 셈, F-OPS-4·5)·352(새로 n건)·467(S-OPS-4)·528(7절 원문) | 주간 보고 운영관리 발견(ℹ)·7절 원문 → 비서 제안·사장이 읽음. 관제판 기록 고침은 이 예약이 못 함(지시문:6 관제판 쓰기 금지) — 회사PC 스레드가 사장 지시를 받을 때만 | 스크립트 실패 = board.txt "점검 불완전(스크립트)"(지시문:29) → F-OPS-4 🟠(ceo.py:252) · 사장 알림 한 줄 | 연결(③⑤) / ④ 끊김 — R1 어긋남이 4주 넘게 '알림만'으로 남음(ceo-weekly-report.md:758 등). 메울 변경: 비서 제안이 R1 줄을 관제판 고침 할 일로 올리기 · 승인 경로: 비서 제안 지시문 `예약 작업 변경 승인: 비서 제안` — 이번 제안 범위 밖, 따로 올림 |
| R1 '대조 못 함' 줄(새) | 위와 같음, check.py v1.1 44~48행 | ceo.py:245~254·352·528 | 위와 같음 | 7절 원문에 매주 남고, 알림 '장부 어긋남 새로 x건(전체 y건)'의 전체 수에 들어감(ceo.py:352·620). 줄별 '계속 n주째' 표시는 없음 | 연결 |

## 8. 바뀔 조건
- 11/22 실행 기록에서 in.json의 sch.updated가 문서 단위 값이었다면 원인 추정이 틀린 것 — 그래도 v1.1은 멈춤을 막으므로 고침은 유지, 1절 원인 문장만 고친다.
- 사장 무응답·11/28 넘김 → 현행 유지(D1 기본값).

검토 완결: 원문 확인 · 내장 재검토 1회(Fable, 8건 중 반영 8건 — 4번은 R6 형식까지 넓혀 반영, 7번 ④는 '끊김'으로 적고 메울 변경은 따로) · 미해결 1(11/22 in.json 미확인) · 자료 시점 2026-11-24 10:1x KST · 바뀔 조건 8절.

## 7. 적용 기록 (2026-11-24)

- 10:35 KST 사장 비서실 직접 지시로 5절 2. ①·④·⑤·⑥ 일부 적용: ① trig_01XvqwKG2gt7EKLEVMHGYR6Y 지시문 = pending-checkfix-1124/ceo-weekly-meeting-v1.6.1.txt(6caaea5e…), 이름 '주간 팀장회의 v1.6.1 (일 09:47)', 응답 "prompt re-signed by 금동한"(updated_at 01:35:20Z) ④ 그 뒤 ceo-weekly/check.py → v1.1 ⑤ `tr -d '\r' | sha256sum` check.py 07f07548…·ceo.py 3abd1497… 일치 ⑥ 보관본 ceo-weekly-meeting.txt(6caaea5e…)·README 15행·변경 기록·_pending 목록(check.py 포함).
- 하지 않은 것: ③ 응답 본문 바이트 sha256 대조(응답이 파일로 저장되지 않아 눈 대조만) · ⑥ 관제판 sch-boardreview 이름·note(관제판 쓰기 — 이번 지시 범위 밖) · ⑥ active-decisions 한 줄(이 결정 행을 색인에서 못 찾음).
- 확인 필요: 별도 `예약 작업 변경 승인: 주간 팀장회의` 직접 입력 기록 · 첫 실행 2026-11-29(일) 09:47.
