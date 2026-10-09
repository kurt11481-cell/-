# 예약 작업 지시문 원문 보관 (FX-1009 fx-1, A9)

- 보관 시각: 2026-10-09 14:54 KST. 출처: 예약 작업 목록 조회(`list_triggers`)의 지시문 필드. 읽기 전용 보관본이다.
- 이 폴더 파일은 예약 작업에 쓰이지 않는다. 되돌리기·변경 비교용이다. 예약 작업을 바꾸면(사용자 승인) 같은 때 이 파일과 아래 표의 해시도 새로 만든다.
- sha256은 줄바꿈을 LF로 정규화한 값이다. 파일이 이미 LF라 `sha256sum <파일>` 결과와 같다.
- 이벤트 예약은 같은 형식이 5개(10/14·10/15·11/6·11/10·11/13)라 표본 1개만 보관했다. 나머지 4개는 날짜·내용만 다르다(원문 비교 안 함, 확인 필요).
- 일회성으로 이미 실행된 예약 작업(`run_once_fired`)은 보관 대상이 아니다.

| 파일 | 이름 | trigger id | 모델 | sha256 (LF 정규화) | 저장소의 다른 사본 · 대조 |
|---|---|---|---|---|---|
| `integrated-check-daily.txt` | 보유·관심 종목 통합 점검 (화~토 06:40) | trig_01YWzNq847nJfNgDUnnukBqP | Sonnet 5.5 | d1bba04e5bcfd41fa8d28d4325e450ca32c466506b4a3d5f33d1950957c66f1c | `integrated-check-prompt-v3.12.2-L-loader-2026-10-09.txt` — 일치(해시 동일). 저장소 로더 v3.12.2-L = 현행. 규칙 본문은 integrated-check-prompt-v3.12.2-2026-10-09.txt(로더가 해시로 고정) |
| `monday-pre-open-check.txt` | 월요일 개장 전 점검 (월 21:20) | trig_01M1DYJ28pstoumsEV6ZSWhf | Sonnet 5.5 | d05cbe6e5c9c77413cffa5fc3d8b9e8e29edf42b28bbd885b6ff57b56b945bd0 | `monday-preopen-prompt-v2.1-2026-10-09.txt` — 일치(해시 동일) |
| `save-market-memo.txt` | SAVE 시장환경 메모 갱신 (매일 06:15) | trig_01VrX6zRZ8XYGeycXBXo1J3D | Sonnet 5.5 | 5e4838171ab3fcbb0a2e940bf43a687e0842ee86f2ade3d0b9b4818aca66aa05 | `save-memo-prompt-v2.1-2026-10-09.txt` — 일치(해시 동일) |
| `dev-board-weekly-review.txt` | 관제판 주간 점검 v1.1 (토 10:50) | trig_01XvqwKG2gt7EKLEVMHGYR6Y | Haiku 5.5 | 1ca1d45c6f0f386dbf960aee832f8ec348be9696997b28f7ca66ee717163b88d | `dev-board-review-prompt-v1.1-draft-2026-10-03.txt` — 끝 개행 1개만 다름(내용 동일). 해시는 불일치 |
| `watchlist-weekly-rescore.txt` | 관심 명단 주간 재채점, 제안 모드 (토 10:20) | trig_01MuMHqXHrRAeNVZt2ZjzRxu | Sonnet 5.5 | 674f12100d6994be9316f7080e20abb7342fb7c5f3b5b0252a5b6eacecc43722 | `weekly-watchlist-rotation-prompt-v2-draft-2026-10-03.txt` — 불일치(저장소 v2 초안과 다름). 현행 원문은 이 폴더 파일 |
| `next-sandisk-discovery.txt` | Next 샌디스크 발굴 v3.1, 제안 모드 (토 07:32) | trig_01GqUwXK9KLqTRUJPVefHhq3 | Opus 5.5 | 2315823b58974a5d0aa258c781689640ef30ad7522620cd6b2c429571caad0b8 | 저장소 사본 없었음. 이 폴더 파일이 첫 사본 |
| `us-stock-board-close.txt` | 미국주식 현황판 마감 정리 (화~토 09:10) | trig_017qqjiQdpUbHxHXsLDPrL8Z | Sonnet 5.5 | 8fe2281ebb72956423700ac8bd66bd5d4af1a391bda173a03225bf6cd3e28918 | 저장소 사본 없었음. 이 폴더 파일이 첫 사본 |
| `event-pre-open-1014-cpi.txt` | 개장 전 이벤트 10/14 CPI(9월분), 1회 (형식 표본) | trig_01YXzuwKvTKTU6tvNrbYqg6N | Sonnet 5.5 | b91ec3a3fafe93858d8c91986b0d93dde26ec13ea032563b432c67f9b892e42f | 저장소 사본 없었음. 같은 형식의 이벤트 예약 5개(10/14·10/15·11/6·11/10·11/13) 중 표본 1개 |

## 확인한 것
- 반복 7개(통합 점검·월요일·SAVE·관제판 주간·관심 명단·Next 샌디스크·현황판)와 이벤트 표본 1개의 원문을 저장했다. 저장 후 파일 해시가 조회 때 계산한 해시와 같음을 확인했다.
- 설계·계획 문서가 말한 "저장소 사본 3개만 일치"(A9)의 현재 상태: 일치 3개(통합 점검 로더·월요일·SAVE), 사실상 일치 1개(관제판 주간, 끝 개행), 불일치 1개(관심 명단), 사본 없음 2개(Next 샌디스크·현황판).
- 통합 점검 예약 작업은 10/9 14:35 KST에 이미 v3.12.1-L에서 v3.12.2-L로 교체된 상태다(`integrated-check-v3.12-change-2026-10-09.md` 8절). 계획서 5-1·5-2절의 "v3.12.1 현행" 표기와 다르다. 이 README와 INDEX는 조회로 확인한 현재 상태(v3.12.2)를 따른다.
