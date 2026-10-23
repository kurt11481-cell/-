---
id: split-weekly-general-measure-2026-10-23
title: "키움 수정주가 일봉 vs 원래 일봉 측정 (split-weekly-general 1단계)"
date: "2026-10-23"
status: "결정됨 — 승인(2026-10-23 06:44 KST) · 지시문 v3.4 교체 완료(08:05) · 첫 실행 10/24 10:20 확인 대기"
authority: "읽기 전용 kiwoom_query(실전계좌·real) · 주문·정책·상태 무관"
consumers: "관제판 split-weekly-general · 관심 명단 주간 재채점 지시문(다음 교체 때) · 비서실"
weekly_user_touch: "0 (채택 시 1회성: 예약 지시문 교체 승인 1줄 + PC 앱 승인)"
---

# 키움 수정주가 일봉 vs 원래 일봉 (2026-10-23 00:3x KST 조회)

## 결론
1. **분할이 없는 종목에서는 수정주가(adjusted) 일봉이 원래(raw) 일봉과 같다.** 배당 조정은 보이지 않는다(관측 2종목, 배당락일 확인 필요).
2. **원래 일봉은 분할을 표시하지 않는다**(CRWD 분할 반영일에도 upd_stkpc_tp·upd_rt 빈칸) → "분할 감지 칸으로 adjusted 전환" 안은 쓸 수 없다.
3. 제안: 관심 명단 주간 재채점의 일봉 조회를 **전 종목 adjusted**로 바꾸는 1줄 변경(지금은 CRWD만). 분할이 생겨도 주간 작업이 "가격 실패"(0.55~1.9 비율 검사)로 멈추지 않는다.

## 측정 (overseas candles stock-daily, pages 3 = 300봉, 2025-08-14 ~ 2026-10-22)
| 종목 | raw vs adjusted (과거 299봉) | 비고 |
|---|---|---|
| ETN (NYSE, 배당 종목 — 이 기간 배당락일 확인 필요) | 모든 칸 같음 | 다른 곳은 20261022 봉 1개뿐 — 장중 봉(두 조회 시각 차) |
| VLO (NYSE, 배당 종목 — 이 기간 배당락일 확인 필요) | 모든 칸 같음 | raw upd_stkpc_tp "1f"가 20250814·20260107·20260602에 있음 — 사양에 뜻 없음(확인 필요) |
| CRWD (NASDAQ, raw만) | — | 20260701 772.74 → 20260702 193.98(4:1), 그날 flu_rt +0.41, upd_stkpc_tp·upd_rt 빈칸. 키움 봉 기준 분할 반영일은 20260702 |
- 사양(usa06012): 요청 upd_stkpc_tp "0:미적용, 1:적용", 응답 upd_stkpc_tp·upd_rt는 설명 없음.
- 참고: flu_rt는 분할일에도 분할을 반영한 등락률(+0.41%)이라 종가 비율과 비교해 분할을 잡을 수도 있다 — 전 종목 adjusted가 더 단순해 쓰지 않는다.

## 바뀔 조건
- 배당락일이 확인된 날에 raw ≠ adjusted가 나오면 결론 1 철회(배당 조정 있음 → 수익률 기준이 바뀌므로 재검토).
- 사양에 "1f" 뜻이 나오면 결론 2 재검토.

## 남은 것
- 채택하면: 관심 명단 주간 지시문 4)의 "CRWD만 adjusted" 문장을 "전 종목 adjusted"로 바꾸는 예약 지시문 교체 → 사장 직접 승인 `결정 split-weekly-general: 승인` + PC 앱 승인. 통합점검·Next 샌디스크 일봉 조회는 범위 밖.
- 기본 처분: 답 없음 = 현행 유지(CRWD만 adjusted), 알림만.

## 결정 기록
- 사장 원문 "결정 split-weekly-general: 승인"(2026-10-23 06:44 KST, 투자_V2 비서실 — 직접 입력, 제안 00:36과 같은 날).
- 준비(06:5x): 교체본 docs/claude/scheduled-prompts/pending-wl-adjall/watchlist-weekly-rescore.txt (51,181B, sha256 35ab03c84cc47f2e7442120abaae78f8b430dc96046f903cf8f2194d301e1fb3; 현행 a809c649…). 바뀐 줄 4개(1·84·248·255행): 머리 줄 v3.4 · 4) 조회 options adjusted "adjusted" + 수정주가 문장 · 카드 표 "키움 일봉(수정주가)" 2곳. 결정론 시험: python 3블록 컴파일 OK(바뀐 블록은 카드 문구 2곳뿐), load() 비율 검사 — ETN·VLO adjusted 300봉 통과(raw와 같음), CRWD raw 실패(분할 끊김 → 지금 방식의 근거).
- 1차 교체 호출 06:5x = needs_device_approval(변경 없음) → PC 앱 승인 뒤 재시도.
- 08:05 교체 완료: 사장이 PC 앱에서 접속(08:01) 뒤 재호출 → "prompt re-signed by 금동한", updated_at 2026-10-22T23:05:32Z, 응답 본문 sha256 35ab03c8… = 보낸 본문. 저장소 원문 watchlist-weekly-rescore.txt 교체, README 표·변경 기록 갱신, 옛 판 pending-wl-adjall/watchlist-weekly-rescore-v3.3.txt.
