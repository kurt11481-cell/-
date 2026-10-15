---
id: pre-on-roadmap-review-2026-10-15
title: T2 "켜" 전 남은 개발 검토 — ④①⑥⑦⑧⑨·C1 재시작 위험·슬롯
date: 2026-10-15 16:xx KST (HEAD 1a0171a)
class: 검토 기록(문서). 코드·정책·상태·예약 작업 변경 없음
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: 관제판 redesign-t2·t2-rc·hwm-fix·ev-rg1-hyper·pre-on-fix·rrec-k3-timing·t2rc-c45·cal-2027 · 정책 문턱 변경 K3 세션(4절 절차) · ④① Builder 지시문(작성 예정)
근거 입력: 관제판 log 20261015-1420-risk-recheck · redesign-t2-judge2-report-2026-10-11.md G절 · t2-rc-preregistration-2026-10-14.md · t2rc-oracle.py(5607b09b…)
---

# T2 "켜" 전 남은 개발 검토

## 0. 결론
- ④·①·⑥은 개발 파이프라인 1번(①④를 한 run, ⑥ push 포함)으로 묶는다. 셋 다 독립 대조 판정을 바꾸지 않으므로 C1을 되돌리지 않는다. 언제 병합해도 된다. 기한은 "켜" 전이다.
- ⑦⑧⑨는 이번 세션에서 문서로 닫았다(2·4·5절).
- C1 재시작 위험은 hwm-fix의 EV4 재계산과 ev-rg1-hyper의 RG1에만 있다. 권장: 둘 다 "켜" 전에, 계산기 동반 수정과 함께 병합한다. 자세한 것은 3절이다.
- 빠진 항목 1건: 달력 권한이 2026-12-31까지만 있다. 12월 안에 K3로 갱신해야 한다(6절). 관제판에 없었다.

## 1. 개발 항목 (코어)
| 항목 | 원문 | 판정 |
|---|---|---|
| ④ 휴장 날 중복 입력 | auto_core_decide.py:939-940 `_no_new_session` → "주문표 N건 — 저녁 키움 입력"(apply 모드, 넘어온 주문표 :906-916). 요건: judge2:171-175 | 확인. 영향은 기록 모드에서만 생긴다(:939 `mode == "apply"`). 다음 휴장: 2026-11-26, 12-25(달력 2421eeb7). 11/27 KST·12/26 KST 실행이 같은 주문표를 다시 안내한다. **기한 = "켜" 전** |
| ① r4 E | auto_core_tickets.py:531-573 `ticket_rows`: 발행일 하한(`placed < start`)만 있다. 끝 날짜 마감 뒤 컷이 없다. 요건: judge2:168 | 확인 |
| ⑥ G0_TICKET_SESSION_NOT_YET | decide:329 → gate0(:698) → HOLD(:771-773). 예외 목록(:683-760)에 없어 push가 없다. 알림 ⑥은 FAIL만 보낸다(auto-core-alert.txt:121). 요건: judge2:177 | 이상 상태다. 매수를 막는 쪽(fail-closed)이지만 조용하다(대시보드 HOLD 사유로만 보임). 권장: 예외 push. ④ run에 같이 넣는다(같은 파일) |

④ 범위 제약(재검토가 찾음):
- 알림 4c는 이미 있는 orders 문서를 바꾸지 않는다(auto-core-alert.txt:83). 그래서 주문표 행 표시는 대시보드 orders에 닿지 않는다.
- 따라서 ④는 NEXT_USER(알림 ⑩ :125가 그대로 보냄)와 core 표시만 고친다. 알림을 고치려면 재서명과 사용자 승인이 필요하다(사전 등록 :49 고정값).
- 새 세션 없음 날에 S7 등 입력 파일을 새로 쓰면 안 된다. 지금 계산기는 그날 S7_MISSING으로 우연히 NOT_CHECKED가 된다(t2rc-oracle.py:1294-1306). 입력이 생기면 MISMATCH로 C1에 셀 수 있다.
- ①은 F6 결과 상태 이름을 CLASSIFIED(t2rc-oracle.py:1233) 밖으로 늘리지 않는다.

권한 분류:
- ①④⑥은 auto_core*.py를 고친다. 그래서 파이프라인 class는 authority다(authority-paths.txt:12). NEEDS_APPROVAL이고, 병합할 때 `-ApproveAuthority` 1번이 필요하다.
- 내용은 CLAUDE.md "Authority/limit change" 목록(주문 단계·주문 도구·예산·상한·상품·대조 불변 조건·kill switch)에 해당하지 않는다. 그래서 K3 동시 1건 슬롯을 쓰지 않는다고 본다. **해석이다.** 문서에 명시된 문장은 없다.
- 같은 방식의 선례: t2rc-corefix2(ef3bad1)가 autocore-on이 슬롯을 쥔 동안 병합됐다.

C1 영향 없음의 근거:
- 계산기 판정 = 회로 집합 일치 AND 주문표 항목 일치 AND 누락 없음(t2rc-oracle.py:1523).
- G0는 코어의 outcomes를 그대로 읽는다(:1833-1834). next_action은 읽지 않는다.
- keys 갱신은 apply 모드에서만 한다(decide:715). 그래서 비교 기간에는 ①이 재발행에 닿지 않는다.

## 2. ⑨ 처리 기록
"지시문 R1·R2·R3"(judge1 redesign-t2-judge-report-2026-10-10.md:222, judge2:180)는 할 일이 아니다. "켜" 조건 자체다(redesign-t2-builder-prompt-2026-10-10.md:46-48).
- R1 리플레이: 10/14 판정. R-A PASS, R-B 미검증, R-C는 C1·C2로 대체(사전 등록 :18-19).
- R2 대조 5일: 관제판에서 세고 있다.
- R3 사용자 "켜": 대기.

기록 누락이 아니므로 닫는다.

## 3. C1 재시작 위험 — hwm-fix·ev-rg1-hyper
- **규칙.** 사전 등록 :24는 불일치가 생기면 원인에 따라 고친 뒤 C1을 0부터 다시 센다고 정한다. 불일치 없이 계획해서 계산기를 함께 고치는 경우는 적혀 있지 않다.
  - 다만 계산기는 고정값이다(:49, t2rc-check-run.ps1:12-16). 새 sha에는 Judge와 사용자 승인이 필요하다.
  - 그래서 "함께 고쳐도 C1을 0부터"로 보는 것이 보수적인 읽기다. **해석이다.**
- **R-REC1의 위치.** R-REC1은 회로 집합이 아니라 주문표 요건에 들어간다. 그래서 불일치는 매수 주문표가 나올 날에만 생긴다. 두 수정 모두 "더 엄격하게만"이다. 어긋나면 코어가 막고 계산기는 주문표를 기대한다 → 누락 → MISMATCH. 입력 금지 쪽이라 위험하지는 않다.
- **hwm-fix ①(portfolio_exposure.py):** 계산기는 S7 파일의 hwm_usd(:1821)와 과거 decision의 account.s7_hwm_usd(:1475-1484)만 읽는다. 둘 다 공유 입력이라 어긋나지 않는다.
- **hwm-fix ②(EV4 재계산, auto_core):** 어긋난다.
  - 10/12: 27,695.15. 옛 기준 27,229.82(=30,255.36×0.9)보다 크고, 새 기준 28,540.58(=31,711.76×0.9)보다 작다.
  - 10/13(10/14 실행, 27,750.04)도 새 기준에서는 EV4가 열린다.
- **ev-rg1-hyper:** 계산기 rrec1의 RG1(:979-1044)과 어긋난다.
- **시기 비교**
  - (a) "켜" 전·슬롯이 열리는 대로, 계산기 동반 수정, 가능하면 한 K3 묶음 — **권장**
    - C2(첫 매수 주문표 일치)가 병목일 가능성이 크다. 10/14 R-REC1 사건이 열려 있고 RG1~RG3가 미충족이다(관제판 redesign-t2 ⑤). 매수가 막힌 동안 병합하면 잃는 것은 C1 세션 수뿐이다.
    - C2 일치 뒤에 병합하면, 그 일치는 옛 관문 아래에서 확인한 것이 된다.
  - (b) 두 K3를 따로 "켜" 전에 병합: C1을 두 번 다시 센다.
  - (c) "켜" 뒤 병합: 실제 주문표가 알려진 매수 쪽 fail-open 결함 2개를 안고 나간다. 권하지 않는다.
- **선행 조건(사용자 결정 hwm-fix a):** t2-rc 적용과 T1 첫 기록 확인(10/16)이 먼저다. 그 뒤 ev-rg1-hyper와 순서를 정한다. cashflow-api-gap·deposit-interest-i3 ③은 같은 K3 묶음이다. 여기에 ev-rg1-hyper까지 넣을 수 있는지는 **확인 필요**다(Judge 범위가 커지면 FAIL 위험).
- **바뀔 조건:** C2가 먼저 채워지면 (a)의 이점이 줄어든다. 그때는 시기를 다시 판단한다.

## 4. ⑧ 정책 문턱 동반 수정 절차
1.55·1.85·1.9·0.4 중 하나를 바꾸는 K3(사용자 승인)는 아래 사본을 한 변경 묶음에서 함께 바꾼다. 하나라도 빠지면 G1 POLICY_THRESHOLD_CHANGED(주문표 0) 또는 독립 대조 MISMATCH가 된다. 둘 다 fail-closed이지만 자동 운영이 멈춘다.

| 위치 | 행 | 승인 경로 |
|---|---|---|
| stock-strategy-system/alert_policy.json | 해당 키 | 보호 경로 — 사용자 승인 |
| manage-us-stock-strategy/scripts/auto_core_tickets.py `POLICY_EXPECTED` | :58-59 (표시 문자열 :235·:239 "≥ 1.85") | 권한 경로 — -ApproveAuthority |
| docs/claude/t2rc-oracle.py | :61(1.55) · :1805·:1853(1.85 상수) · :1724·:1813(0.4 기본값) · :2083(자기 확인 기본값 1.85) | 새 sha → Judge → 실행기 고정값(t2rc-check-run.ps1:16) 교체 승인. C1 재시작 검토(3절) |
| docs/claude/integrated-check-prompt-v3.12.6-2026-10-15.txt | :99-100 · :134 · :278 | 규칙 파일 해시 재서명 — 사용자 승인 |

## 5. ⑦ 처리
redesign-t2-replay-2026-10-14.md "보충(2026-10-15)" 절에 적었다.
- extra_tickets: P-R1 0, P-R2 0.
- 가정 24번 두 가지를 명시했다.

## 6. 빠져 있던 항목
- **cal-2027(K3, 12월 안).** 달력 권한 2421eeb7은 coverage_end 2026-12-31이다. 그 뒤를 덮는 산출물이 없다(artifacts 전수 확인). 2027년 첫 실행은 fail-closed로 멈춘다(s7-calendar-binding-builder-prompt:113 X2). K3 슬롯이 겹치므로 3절 묶음 뒤 순서에 넣는다.
- **C4·C5 알림 장치 없음.** 사전 등록 :30-31은 6주·12주 알림을 약속했는데, 지금은 나가지 않는다.
  - 가장 싼 해법은 1회 예약 작업 2개다: 2026-11-27(D0+6주), 2027-01-08(+12주).
  - 예약 작업 생성이라 사용자 결정이 필요하다. 기본 = 현행(Cowork가 "켜" 판정 때 셈).
  - 01-08은 cal-2027이 끝나야 의미가 있다.
- **"켜" 뒤 남은 위험(낮음).** 계산기에는 재발행 막힘·닫힌 키·G2B 하루 한도 모델이 없다(tickets:780-793, :983-994). 그래서 키가 닫힌 뒤 거짓 MISMATCH가 날 수 있다. 입력 금지 쪽이다. "켜" 뒤 첫 사례 때 계산기 보완을 검토한다.
- **선택(낮음).** judge2:193-195 plan()은 종목별 마지막 reduce 항목만 남긴다. ①④ run에 넣을 수 있다.
- **확인 필요.** 1a0171a 병합 뒤 VM git에 host_status*가 M으로 보인다. 차이는 CRLF뿐이다(--ignore-cr-at-eol). 10/16 06:15 result.json의 guarded_dirty_paths가 []인지 확인한다.

## 7. 사용자 손
- ①④⑥ 병합 1번.
- K3 묶음 승인 1번 + 병합 1번(계산기 고정값 교체 포함).
- cal-2027 K3 1번.

모두 일회성이다. 일상 0.

검토 완결: 원문 확인 13/13 · 내장 재검토 1회(Opus, 반영 9건) + 변경분 원문 재확인 1회 · 미해결 2(Windows git 상태 10/16 확인 / 리플레이 HWM 가정이 S7 add를 줄여 회로를 덜 열었는지) · 자료 시점 2026-10-15 16시 KST, HEAD 1a0171a · 바뀔 조건: C2가 먼저 채워짐, Judge가 묶음 범위를 거절, 사용자가 C1 재시작 읽기를 다르게 정함

## 결정 기록
- 2026-10-15 16:32 KST 사용자 원문 "결정 pre-on-fix: a" → ④①⑥ 한 파이프라인 run(⑥ = 예외 알림). 지시문 docs/claude/pre-on-fix-builder-prompt.md(sha d49339c8…), 큐 docs/claude/_dev-queue/pre-on-fix.txt. 결과 뒤 사용자 `.\tools\dev-merge.ps1 pre-on-fix -ApproveAuthority` 1번.
