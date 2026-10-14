---
id: integrated-check-needs-recheck-saveticker-2026-10-14
type: review
status: current
as_of: 2026-10-14
tickers: [NBIS, BE, SOXL, MRVL, MU, DELL, PWR]
summary: 통합점검 10/14 확인 필요 재검토(Cowork) + saveticker 판정 사용 검토(권고 B, 사용자 결정 대기 st-1014)
---

# 통합점검 확인 필요 재검토 · saveticker 판정 사용 검토 (2026-10-14 09:3x KST, Cowork)

원본: 대시보드 runs/2026-10-14(06:52 KST 실행). 같은 날 앞선 검토: redesign-t2-day2-check-2026-10-14.md.

## 1. 재검토에서 바뀐 것 (처음 → 재검토)
- 현금 원인: 확인 필요 → 규칙 파일 1-1 ②가 `overseas accounts cash-by-currency`(ust21120)를 지정, fc_ord_alowa는 `overseas accounts cash`(ust21110)에만 있음(키움 스펙 검색 2026-10-14). redesign-t2-day2 4절 ⑪과 같은 건.
- 현금 비교 시점: 08:37 스냅숏(정산 뒤)과 비교했던 것은 시각 불일치. 점검 시각에 가까운 06:15 스냅숏: 주문가능 12,472.23 · 예수금 9,396.68 · D+1 매도 정산 3,072.51. 점검이 쓴 fx_entr 12,469.19와 $3.04 차이, 매수 요건 ② 통과는 그대로. 점검은 규칙의 대체값(상태 파일 12,469.18) 대신 fx_entr를 씀(규칙 이탈, 오늘 결과 영향 없음).
- 실적일: MRVL·DELL·PWR 회사 IR 페이지에서 Q3 일정 공지 없음 확인(10/14 09:4x KST). MU는 IR 페이지에 일정 표시 없음 → 확인 필요 유지.
- Oracle: Oracle 공식 발표(2026-10-13) "the primary power source for Project Jupiter will continue to be provided by the Bloom Energy fuel cell microgrid." → BE2(Jupiter 변경, −) 미확인 보도와 반대. BE3(+) 근거는 아님(상대방 발표 = EXTERNAL_REFERENCE). BE 매수는 R-REC1 RG2·RG3로 막힘 그대로.
  https://www.oracle.com/news/announcement/oracle-proposes-plan-to-offset-customers-utility-costs-2026-10-13/
- Direxion: 공시 피드(SEC) 대상에 SOXL 없음(BE·DELL·LITE·MRVL·MU·NBIS·PWR) → 구조상 매일 확인 필요. SEC EDGAR는 도구 정책상 열 수 없음.
- CME(EXT-20261005-05): 개시 확인 자료 여전히 없음. 최종 기한 10/12 경과 — 원장 1절 규칙에 기한 경과 처리 규칙이 없음(정리 필요).
- 유지(새 근거 없음): NBIS C5- 1세션째(붕괴선 207.37~207.41, 종가 206.86~206.90), C4- 창 10/13 종료 → 다음 세션 C3-·C5- 2개 예상(3개 아님), SOXL S5(C3- 묶음 1개), 종가 대조, S7 VERIFIED, SMA200 무영향, BE 시각(장 마감 후, 코드 경로 auto_core_decide.py 374행 → portfolio_exposure).

## 2. saveticker 판정 사용 검토
- 현행: 6) 내장 브라우저 종목 페이지 = 표시 전용, 뉴스 제목만 "단서 → 공식 확인". 4) SAVE 메모(06:15 작업) = 시장 환경 표시 전용. 10/2 결정: SAVE·saveticker는 공식 출처로 가는 단서, 목표가(AM9) 표시 전용.
- 실적: 최근 9회 기록 중 종목 페이지 미조회 2회(10/10·10/14), 10/13은 뉴스 칸 1/7. 단서→공식 확인이 10/13 Oracle 공식 발표를 놓치고 "미확인 보도"로 남김.
- 대안: A 유지 / B(권고) 브라우저 읽기를 06:15 SAVE 작업 하나로 합치고 종목별 뉴스 제목을 파일로 → 06:40 점검은 파일만 읽고 단서마다 공식 확인 결과(URL|못 찾음|대상 아님)를 기록, 공식 확인분만 트리거·연구 기록 official_facts로. 목표가·P/C·건수는 표시 전용 유지 / C saveticker 값을 직접 트리거·근거로 = K3, 10/2 결정·증거 규칙·FX-1009 동결과 충돌, 과거 자료 없어 검증 불가 → 지금은 하지 않음.
- 루프 점검: B 진행(수정 조건 붙임). 끝 기준 = 대상 종목마다 행 또는 미조회 사유, 단서마다 결과 칸(빈 칸 0). 경계 = 트리거 기준·강도·정책 파일 불변, saveticker 값이 트리거 근거에 나오면 기록 전 검증 FAIL. 재시도 없음, 2일 연속 미조회면 기존 SAVE 알림 한 줄.
- 등급: K1/K2(예약 지시문 2개 + 해시 고정 규칙 파일). 현금 명령 교체(⑪)와 같은 해시 변경 한 번으로 묶을 수 있음.

## 3. 사용자 결정 대기
- st-1014: saveticker 사용 방식 — B(권고) / A 유지 / C(fx-6 뒤 K3 검증 사전등록)

## 4. 결정·후속 (2026-10-14 09:42~)
- 사용자 결정 "st-1014: B". 변경안·시험·독립 검토: integrated-check-v3.12.4-change-2026-10-14.md (적용은 사용자 승인 대기).
- 정정(1절): "MRVL·DELL·PWR 미공지 확인" 중 PWR는 틀림 — Quanta 2026-10-13 06:55 ET 보도자료로 3분기 실적 10/29 장 전 공지. 회사 보도자료 목록 페이지가 갱신 전이었다. saveticker 종목 페이지 단서로 발견(B안이 잡는 사례).
