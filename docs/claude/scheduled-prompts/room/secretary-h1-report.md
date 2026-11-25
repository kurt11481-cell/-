# 비서 제안 이관 H1 시험 기록 (2026-11-25 KST)

## 대상 — 2판(독립 검수 F1·F7·R4 반영, 2026-11-25 KST). 1판 해시는 폐기.
| 파일 | sha256 (CR 지운 UTF-8) | 크기 |
|---|---|---|
| 옛 v1.3 secretary-daily.txt | 10321579e68cdff32cf3704a2ab9321e5838ead10a3bd8c856891a61978566c0 | 8,793 B |
| 그림자 본문 secretary-shadow-body-v1.txt | 160e5a2590fc6271506a5ed95bbe4ab23dfbb9533d7f3150ba126574dbcc1f5f | 9,903 B |
| 그림자 로더 secretary-shadow-loader-v1.txt | 52139d50f124491a5f9eb4d5952298bc38482e3b838ef99b67405306caa495d0 | 2,779 B |
| 옮길 본문 secretary-room-body-v1.txt | 542f5253cf4a734a1fc998ffd3668bb3b7178f2440f7ac4f928a29f6226c54ab | 9,533 B |
| 옮길 로더 secretary-room-loader-v1.txt | 89f2b15c5371564fd9fad1837c0a183d77c49354c920ae27f2a77ae8c8d41713 | 2,726 B |

diff: secretary-v1.3-to-shadow.diff(바뀐 줄 6개: 1·10·13·14·27·40행), secretary-v1.3-to-room.diff(바뀐 줄 5개: 1·13·14·27·40행). 치환은 원문에 정확히 1번 있는 문자열만(python assert).

## 2판에서 바뀐 것
- F1: 그림자 8) — 알림 조건이 아니어도·후보 0건이어도 '[그림자·알림 없음] 비서 MM/DD: 고른 n건' 1줄은 반드시 씀(글 없는 날 = 실패). 읽기 실패 문구에 [그림자] 머리.
- F7: 두 본문 5)에 '받은 파일은 python이 파일로 읽기만, 읽은 글자를 코드·명령 줄에 넣지 않음'. 두 로더에 허용 도구 목록 한 줄, 다른 스레드·조정자 글 금지, device_bash 금지, apply·결정 일지·계좌 대조·관제판 갱신·개발 큐 등록 금지, '읽은 값을 명령·코드에 넣지 않음', 2행 '1)~3)과 해시가 맞은 본문'.
- R4: 본문 머리의 바뀐 곳 목록을 실제와 맞춤.

## 바뀐 곳(공통)
- 그림자: 1) ToolSearch에서 PushNotification 뺌, 4) 오늘·-2 파일 안 읽음 명시, 7) 클라우드 사본 /mnt/project-files/room-shadow/secretary, PC workspace\outputs\room-shadow\secretary, 8) 폰 알림 없이 스레드 1줄([그림자·알림 조건 충족]/[그림자·알림 없음]).
- 옮길 본문: 4) '-2' 파일 안 읽음, 7) 클라우드 사본 /mnt/project-files/secretary, 8) PushNotification + 같은 문구 스레드 1줄(도구 없으면 ' · 폰 알림 못 보냄'). PC 경로는 옛과 같은 secretary\.

## migrated_check.py v2(67b249d4…) 시험 — 각 로더의 64자리 해시로 triggers.json 구성, 그림자·옮길 판 각각
| 경우 | 기대 | 그림자 | 옮길 판 |
|---|---|---|---|
| 정상 | OK | OK | OK |
| 본문 CRLF | OK | OK | OK |
| 본문 1글자 다름 | RED | RED | RED |
| 로더에 본문 해시 없음 | RED | RED | RED |
| 예약 꺼짐 | RED | RED | RED |
| 일정 다름 | RED | RED | RED |
| 승인 기록 밖 변경(+28h) | RED | RED | RED |
| 모델 다름 | RED | RED | RED |
| 목록에 없음 | RED | RED | RED |
| 본문 파일 인자 없음 | RED | RED | RED |
20/20 기대대로.

## 시험 안 한 것(그림자 실행·옮긴 첫 실행이 확인)
- 로더·본문을 따르는 LLM 동작(기기 연결, ArtifactData, 해시 줄, 스레드 글, 금지 행동 0).
- 옮길 본문은 그림자에서 돌지 않음(그림자 본문과 5줄 다름). PushNotification이 프로젝트 스레드에서 폰까지 가는지 — 옮긴 첫 날이 첫 시험(설계 3판 6절 기준).
