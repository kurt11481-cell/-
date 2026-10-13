# 예약 작업 지시문 원문 보관 (FX-1009 fx-1, A9)

- 보관 시각: 2026-10-09 14:54 KST. 출처: 예약 작업 목록 조회(`list_triggers`)의 지시문 필드. 읽기 전용 보관본이다.
- 이 폴더 파일은 예약 작업에 쓰이지 않는다. 되돌리기·변경 비교용이다. 예약 작업을 바꾸면(사용자 승인) 같은 때 이 파일과 아래 표의 해시도 새로 만든다.
- sha256은 줄바꿈을 LF로 정규화한 값이다. 파일이 이미 LF라 `sha256sum <파일>` 결과와 같다.
- 이벤트 예약은 같은 형식이 5개(10/14·10/15·11/6·11/10·11/13)라 표본 1개만 보관했다. 나머지 4개는 날짜·내용만 다르다(원문 비교 안 함, 확인 필요).
- 일회성으로 이미 실행된 예약 작업(`run_once_fired`)은 보관 대상이 아니다.

| 파일 | 이름 | trigger id | 모델 | sha256 (LF 정규화) | 저장소의 다른 사본 · 대조 |
|---|---|---|---|---|---|
| `integrated-check-daily.txt` | 보유·관심 종목 통합 점검 (화~토 06:40), 로더 v3.12.2-L+R1(2026-10-12 4단계 연구 기록 추가) | trig_01YWzNq847nJfNgDUnnukBqP | Sonnet 5.5 | ded151f3f2d243634195577c9852e438275e94756dd1557ef4292d158c1e8e1d | 이 폴더 파일이 원문. `integrated-check-prompt-v3.12.2-L-loader-2026-10-09.txt`에는 3단계(SCN-27H1)·4단계(연구 기록)가 없다. 규칙 본문은 integrated-check-prompt-v3.12.2-2026-10-09.txt(로더가 해시로 고정, 변경 없음) |
| `monday-pre-open-check.txt` | 월요일 개장 전 점검 (월 21:20) | trig_01M1DYJ28pstoumsEV6ZSWhf | Sonnet 5.5 | d05cbe6e5c9c77413cffa5fc3d8b9e8e29edf42b28bbd885b6ff57b56b945bd0 | `monday-preopen-prompt-v2.1-2026-10-09.txt` — 일치(해시 동일) |
| `save-market-memo.txt` | SAVE 시장환경 메모 갱신 (매일 06:15) | trig_01VrX6zRZ8XYGeycXBXo1J3D | Sonnet 5.5 | 5e4838171ab3fcbb0a2e940bf43a687e0842ee86f2ade3d0b9b4818aca66aa05 | `save-memo-prompt-v2.1-2026-10-09.txt` — 일치(해시 동일) |
| `dev-board-weekly-review.txt` | 관제판 주간 점검 v1.1 (토 10:50) | trig_01XvqwKG2gt7EKLEVMHGYR6Y | Haiku 5.5 | 1ca1d45c6f0f386dbf960aee832f8ec348be9696997b28f7ca66ee717163b88d | `dev-board-review-prompt-v1.1-draft-2026-10-03.txt` — 끝 개행 1개만 다름(내용 동일). 해시는 불일치 |
| `watchlist-weekly-rescore.txt` | 관심 명단 주간 재채점, 자동 모드 v3 (토 10:20, 2026-10-10 교체) | trig_01MuMHqXHrRAeNVZt2ZjzRxu | Sonnet 5.5 | 53c2df8b06f7d51fd22efca33a74e5ba2366323b648da3f9fbe0fbfbec405d86 | 저장소 다른 사본 없음 — 이 폴더 파일이 원문(변경 기록 `watchlist-auto-mode-a6-2026-10-10.md`). 이전 제안 모드 원문(86a4f603…)은 git 이력 |
| `next-sandisk-discovery.txt` | Next 샌디스크 발굴 v3.1, 제안 모드 (토 07:32) | trig_01GqUwXK9KLqTRUJPVefHhq3 | Opus 5.5 | 9ad146f548bb3916f0e49e6192c4c9728f779b9120c463ca78d0cabfd80c0319 | 저장소 사본 없었음. 이 폴더 파일이 첫 사본 |
| `us-stock-board-close.txt` | 미국주식 현황판 마감 정리 (화~토 09:10) | trig_017qqjiQdpUbHxHXsLDPrL8Z | Sonnet 5.5 | 8fe2281ebb72956423700ac8bd66bd5d4af1a391bda173a03225bf6cd3e28918 | 저장소 사본 없었음. 이 폴더 파일이 첫 사본 |
| `event-pre-open-1014-cpi.txt` | 개장 전 이벤트 10/14 CPI(9월분), 1회 (형식 표본) | trig_01YXzuwKvTKTU6tvNrbYqg6N | Sonnet 5.5 | b91ec3a3fafe93858d8c91986b0d93dde26ec13ea032563b432c67f9b892e42f | 저장소 사본 없었음. 같은 형식의 이벤트 예약 5개(10/14·10/15·11/6·11/10·11/13) 중 표본 1개 |
| `auto-core-alert.txt` | 자동 운영 코어 결과 알림 v2.1 (화~토 08:50; 2026-10-13 첫 운영일 실패 수정 — device_bash 대신 device_list_dir·device_stage_files, 한국 날짜 계산값만) | trig_01D5KxMSJgbeRG1ZL5ox3Fna | Opus 5.5(기본값) | 66548192913d277d46d792bbcc25eebab86a8e53e85815e182a92b9b3b41ba68 | 이 폴더 파일이 원문. v2(1113744f…)·v1(1035ad51…)은 git 이력 |
| `event-pre-open-calendar.txt` | 개장 전 이벤트 점검(일정표) v1 (평일 09:20 ET, CRON_TZ=America/New_York — 서머타임 자동) | trig_015WVdwRscJ2tQqjPputAxsU | Opus 5.5(기본값, 이 경로로 변경 불가) | ad80eb3eaca168784ed5f45a614fc3cc8f60e2144a4595ecad654e3fc4d6982b | 일정표 `docs/claude/event-calendar.json`, 도우미 `docs/claude/event-calendar-today.py` |

## 확인한 것
- 반복 7개(통합 점검·월요일·SAVE·관제판 주간·관심 명단·Next 샌디스크·현황판)와 이벤트 표본 1개의 원문을 저장했다. 저장 후 파일 해시가 조회 때 계산한 해시와 같음을 확인했다.
- 설계·계획 문서가 말한 "저장소 사본 3개만 일치"(A9)의 현재 상태: 일치 3개(통합 점검 로더·월요일·SAVE), 사실상 일치 1개(관제판 주간, 끝 개행), 불일치 1개(관심 명단), 사본 없음 2개(Next 샌디스크·현황판).
- 통합 점검 예약 작업은 10/9 14:35 KST에 이미 v3.12.1-L에서 v3.12.2-L로 교체된 상태다(`integrated-check-v3.12-change-2026-10-09.md` 8절). 계획서 5-1·5-2절의 "v3.12.1 현행" 표기와 다르다. 이 README와 INDEX는 조회로 확인한 현재 상태(v3.12.2)를 따른다.

## 변경 기록
- 2026-10-09 22:13~22:27 KST — 사용자 지시("fx 동결을 우회하여 예외적으로 지금부터 연결", 금동한 PC 서명 승인): SCN-27H1 시나리오 지침(`docs/claude/market-scenario-27h1-2026-10-09.md`, 갱신 스크립트 `docs/claude/scn27h1-triggers.py`) 연결 블록을 지시문 3개 끝에 추가 — 통합 점검 '3단계'(로더만 변경, 규칙 파일 v3.12.2와 해시 고정 그대로), Next 샌디스크 '10)', 관심 명단 '추가 단계'. 위 표의 해시는 교체 뒤 list_triggers 값과 일치 확인. 표시 전용 — 판정·점수·알림 기준 불변(통합 점검 알림 ⑪ = SCN 🔴 첫날 1회만 추가).
- 통합 점검을 v3.12.3-L로 교체할 때(fx-2) 이 폴더 `integrated-check-daily.txt` 끝의 '3단계' 블록을 새 로더에 그대로 옮긴다. 저장소 v3.12.3-L 로더 파일에는 이 블록이 없다.
- 2026-10-10 14:2x KST — 사용자 "병합 완료, 배포 승인": 재설계 T1 배포. 새 예약 작업 '자동 운영 코어 결과 알림'(06:55) 생성 — Judge 조건 R1(경고·실패 푸시)을 통합 점검 로더 수정 대신 별도 작업으로 처리(통합 점검 지시문·규칙 파일 해시 변경 없음). 첫 생성은 폴더 미첨부로 지우고 저장소 폴더를 붙여 다시 만듦(실행 기록 없음).
- 2026-10-10 20:16~20:17 KST — 사용자 결정 A6 a(재설계 7절, 09:27) + 관제판 c-nextsndk-r21: 관심 명단 주간 지시문을 v3(자동 모드 + 유지 보호 ⑧)로 교체하고 이름을 "관심 명단 주간 재채점 (자동 모드)"로 바꿈. 교체 응답의 지시문 sha256이 위 표 값과 일치. 회귀 50/50·SNDK 리플레이·독립 검토 반영은 `watchlist-auto-mode-a6-2026-10-10.md`. SCN-27H1 '추가 단계' 블록은 그대로 옮김. 일정·모델·자동 승인 불변.
- 2026-10-12 13:24~13:25 KST — 사용자 "결정 redesign-t2: 예약 작업 변경 승인"(재설계 T2 배포 8절 4): ① 통합 점검 로더 v3.12.2-L+R1 — 4단계 연구 기록 쓰기(workspace/outputs/research-records/<날짜>/research-record.json, 쓰기 예외 1개 추가, 규칙 파일·해시 불변) ② 자동 운영 코어 결과 알림 v2 — 06:55→08:50, 이름 변경, decide 결과 알림·통합점검 대시보드 runs.core 옮기기·기록 모드 orders 새 문서. 두 지시문 모두 교체 응답에서 "prompt re-signed" 확인. 초안·해시 = pending-t2/ 같은 파일(교체본과 같음). 결정 기록 docs/claude/redesign-t2-merge-decision-2026-10-12.md.
- 2026-10-13 22:4x KST — 사용자 결정 "결정 ev-calendar-auto: a"(docs/claude/external-phil-repo-review-2026-10-13.md 4절): 반복 예약 '개장 전 이벤트 점검(일정표) v1' 생성(폴더 = 코덱스저장소 1개, 컴퓨터 필요, 자동 승인). 일정표 39행(공식 출처)·앤트로픽 IPO 감시. 기존 일회성 5개(10/14·10/15·11/6·11/10·11/13)는 그대로 두고 일정표 legacy_trigger로 중복 실행 방지. 첫 내용 있는 실행 예정 10/19(월, 이번 주 목록·IPO 감시), 첫 결과 보고 10/22(메타). loop-design-check 결과는 docs/claude/event-strategy-2026-10-13.md 1절.
- 2026-10-13 23:1x KST — 사용자 "케이스별 주가 반응, 전략 재검토": 지시문은 그대로 두고 도우미 event-calendar-today.py에 CPI 다음 날 'macro_followup'(재무부 일일 금리표 2년물 변화 → H/N/D, 판정표 docs/claude/event-strategy-2026-10-13.md v2 4절)을 추가. 일정표 허용 도메인에 home.treasury.gov 추가. 첫 해당 실행 10/15.
