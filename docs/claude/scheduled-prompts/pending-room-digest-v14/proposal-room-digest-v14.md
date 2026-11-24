# 결과 모음 v1.3 → v1.4 교체 제안 (2026-11-24 KST, schedule-to-room-1124b 실행 1단계)

공개: 금지 절에 예외 2개가 더해짐(클라우드 임시 파일, sha256 고정 도우미 1개 실행). PC 쓰기 범위는 그대로. 검사는 늘기만 함.
근거: 지침 v2.19 4절 ⑧ "이 대조가 결과 모음에 들어가기 전에는 옛 예약을 끄지 않는다".

| 항목 | 값 |
|---|---|
| 대상 예약 | 사장실 결과 모음 v1.3 (월~토 09:35) trig_01GrAs6UCfspeTBK3mMncyrd · (일 10:05) trig_01XChapmUEKxAcjKF9AFiERJ — 둘 다 같은 지시문 |
| 지금 지시문 sha256 | 8c271239d3d5090c3ff78752e0835af9751e1404ec86f91b90044afa7a54b077 (scheduled-prompts/room-digest.txt, 11/15 교체 때 두 예약 본문과 일치 확인, 그 뒤 두 예약 updated_at 그대로 11/15) |
| 바꿀 지시문 sha256 | bb09da26efd1bed8689f76c6e9f877dfe7fbfaf0cf400eaa20b43a6dd092bc08 (pending-room-digest-v14/room-digest-v1.4.txt, 끝 줄바꿈 1개) |
| diff | pending-room-digest-v14/room-digest-v1.3-to-v1.4.diff (머리 판 표기, 1-1) 새 단계, 4) 🔴 첫 줄·바뀐 예약 줄, 금지·데이터 문장 예외) |
| 새 파일 | scheduled-prompts/room-digest/migrated_check.py (67b249d4…), scheduled-prompts/room-migrated.json (빈 목록) |
| 불변 | 일정(월~토 09:35·일 10:05)·모델(세션 모델)·깨우는 스레드·폴더 없음·권한 모드 그대로, 지시문만 교체 |
| 시험 | H1 16건 기대대로(h1-report.md) |
| 되돌리는 법 | update_trigger로 두 예약에 v1.3 지시문(8c271239…)을 다시 넣음. 도우미·room-migrated.json은 남겨도 v1.3이 읽지 않음 |
| 적용 뒤 확인 | 두 예약 본문 sha256 = bb09da26…(update_trigger 응답 대조), README 표·변경 기록, 첫 실행 11/25 09:35 글에 🔴 없음(EMPTY) |

연결표
| ① 자료 | ② 읽는 점검(원문) | ③ 바뀌는 행동(원문) | ④ 소비자 | ⑤ 끊김 알림(원문) | ⑥ 상태 |
|---|---|---|---|---|---|
| list_triggers(사장실 예약) + room-migrated.json + 본문 파일 | room-digest-v1.4.txt 1-1) / migrated_check.py | 결과 모음 첫 줄 🔴 → 사장이 본인 승인과 대조 | 사장 | room-digest-v1.4.txt 4) '대조 불가' 🔴 | 연결 |
| room-migrated.json | 이관 스레드가 쓰고(옮길 때·지시문 바꿀 때) 결과 모음이 읽음 | 대조 기준 | 결과 모음 | README 표와 어긋나면 이관 스레드가 같은 커밋에서 고침(사람 확인) | 연결(자동 대조 없음 — 한계) |
| 이관 밖 사장실 예약의 updated_at | 1-1) INFO | 결과 모음 마지막 줄 '바뀐 예약 N개' | 사장 | 없음(표시만) | 의도적 표시만(⑧ 범위 = 옮긴 예약) |

한계: room-migrated.json과 로더를 함께 고치면 updated_at 대조(승인 기록 ±30분)만 남는다. 로더 전체 해시는 보지 않는다(지시문을 손으로 옮겨 쓰는 오탐 때문에 뺌) — 로더 변경은 updated_at과 본문 해시 포함 여부로 잡는다.
