---
id: cal-2027-holidays-source-2026-11-03
type: source-record
as_of: 2026-11-03 19:2x KST
task: cal-2027 (관제판) — 사전 준비만. 코드·정책·권한·예약 변경 없음
---

# 2027 미국 주식시장 휴장일·조기 폐장 원문 기록

## 1. 결론
- NYSE 공식 페이지에 2027년 휴장일 10일과 조기 폐장 1일이 올라와 있다.
- Cboe 공식 페이지의 2027 U.S. Equities 표도 같은 날짜다(휴장 10일 + 11/26 조기 폐장, 시각 표기 없음).
- Nasdaq은 아직 2027 일정을 내지 않았다. nasdaqtrader.com 달력은 2026만 있고, nasdaq.com 일정 페이지는 응답 오류(HTTP 503)였다. **확인 필요**.
- 저장소 달력 스키마(manage-us-stock-strategy/schemas/session-calendar-artifact.schema.json)는 source_families NYSE_GROUP·NASDAQ·CBOE 셋과 operating_mic_agreement_status VERIFIED를 요구한다. 그래서 Nasdaq 원문이 나오기 전에는 2027 달력을 만들 수 없다.

## 2. 원문 (NYSE)
출처: https://www.nyse.com/markets/hours-calendars (2026-11-03 KST 조회)

휴장(장 닫힘):

| 휴일 | 2027 날짜(미국 동부) | 요일 | 비고 |
|---|---|---|---|
| New Year's Day | 2027-01-01 | 금 | |
| Martin Luther King, Jr. Day | 2027-01-18 | 월 | |
| Washington's Birthday | 2027-02-15 | 월 | |
| Good Friday | 2027-03-26 | 금 | |
| Memorial Day | 2027-05-31 | 월 | |
| Juneteenth | 2027-06-18 | 금 | 6/19(토) 대체 |
| Independence Day | 2027-07-05 | 월 | 7/4(일) 대체 |
| Labor Day | 2027-09-06 | 월 | |
| Thanksgiving Day | 2027-11-25 | 목 | |
| Christmas Day | 2027-12-24 | 금 | 12/25(토) 대체 |

조기 폐장(13:00 ET):

| 날짜 | 요일 | 원문 |
|---|---|---|
| 2027-11-26 | 금 | "Each market will close early at 1:00 p.m. (1:15 p.m. for eligible options) on Friday, November 26, 2027." |

NYSE 페이지의 다른 각주(*, **, ****)는 2026·2028 날짜에만 붙어 2027에는 해당 없음.

## 2-1. 원문 (Cboe)
출처: https://www.cboe.com/about/hours (2026-11-03 KST 조회) — 2027 U.S. Equities Holiday Schedule: New Year's Day 1/1 · MLK 1/18 · Presidents' Day 2/15 · Good Friday 3/26 · Memorial Day 5/31 · Juneteenth Observed 6/18 · Independence Day Observed 7/5 · Labor Day 9/6 · Thanksgiving 11/25 · Thanksgiving Early Close 11/26 · Christmas Day Observed 12/24. NYSE와 같음. 조기 폐장 시각은 이 표에 없음.

## 3. 넣을 때 주의 (원문에서 읽은 것)
- 2027-07-02(금)과 2027-12-23(목)·12-31(금)은 NYSE 원문에 조기 폐장으로 **없다**. 정규장으로 본다.
- 2028-01-01(토)은 대체 휴장이 없다는 것이 NYSE 관행이지만, 2028년 각주는 이번 범위 밖이라 읽지 않았다. 확인 필요.
- 채권(SIFMA) 조기 폐장은 주식 일정과 다르므로 섞지 않는다.

## 4. 남은 일 (cal-2027 본 작업, 권한 자리 순번에 따름)
1. Nasdaq 2027 공지를 기다려 대조(https://www.nasdaqtrader.com/Trader.aspx?id=Calendar). 12/01 k3-queue-check 때 한 번 다시 본다. 기한 12/15까지 안 나오면 사장 결정 필요(기본 처분: 1/1부터 fail-closed 알림).
2. 현재 달력 권한 2421eeb7…은 coverage_end 2026-12-31(pre-on-roadmap-review-2026-10-15.md:85, s7-calendar-binding-builder-prompt-2026-10-02.md 4절 X2).
3. 권한 자리 차례(duet-q4-recon 다음, 기한 12/15)가 오면 수동 경로 Builder·Judge로 반영.

결론을 바꿀 조건: NYSE가 2027 일정을 고쳐 공지하거나, Nasdaq 원문이 위 표와 다르면 다시 대조한다.
