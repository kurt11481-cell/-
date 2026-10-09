# 공식 원문 대체 경로 검토 (관제판 e-official, 2026-10-04)

- 목적: Micron IR 404, SEC EDGAR 자동 접근 차단 상황에서 공식 자료를 읽을 경로 확보. 인계: handover-external-batch-review-2026-10-03.md
- 방법: WebSearch로 문서 URL 확보 → WebFetch로 열기. bash/curl 등 우회 접근은 쓰지 않음.
- 경계: 읽기 전용 조사. order_authority=false. 정책·상태 파일 변경 없음.

## 결론

목록·검색 페이지가 아니라 **문서 URL 직접 열기**가 된다. 확인된 경로 3개:

| 경로 | 결과 | 비고 |
|---|---|---|
| investors.micron.com 보도자료 URL | 열림 | Q3 FY26 수치를 읽음 |
| GlobeNewswire 원문 | 열림 | IR 보도자료와 수치 일치 |
| sec.gov/Archives/edgar/data/723125/… 문서 URL | 열림 | 10-Q(2026-05-28 분기), 8-K 본문 열림 |

## 안 되는 경로

| 경로 | 결과 | 이유 |
|---|---|---|
| IR 분기실적·SEC 목록 페이지 | 내용 빔 | 동적 로딩 |
| sec.gov/cgi-bin/browse-edgar | 차단 | robots.txt |
| efts.sec.gov 검색 | 403 | 접근 거부 |
| data.sec.gov JSON | 불안정 | 긴 응답이 잘려 요약이 틀림(Form 4로 보이는 접수번호를 10-Q/8-K라고 답한 사례). 쓰지 않음 |

참고: robots.txt는 /Archives/edgar/data를 허용 항목으로 둔다(WebFetch 요약 기준).

## Micron Q3 FY26 대조 (2026-06-24 발표, 분기 종료 2026-05-28)

| 항목 | 보도자료(IR·GlobeNewswire) | 10-Q |
|---|---|---|
| 매출 | $41.456B | $41,456M (일치) |
| GAAP 순이익 | $28.243B | $28,243M (일치) |
| GAAP 매출총이익률 | 84.6% | 확인 안 함 |
| GAAP EPS | $24.67 | 확인 안 함 |
| Q4 매출 가이던스 | $50.0B ± $1.0B | 해당 없음 |
| 설비투자 | 순투자 $7.1B | PP&E 지출 $19,602M |

- 설비투자는 측정 기준·기간(누적 여부)이 달라 보임 → **확인 필요**. 카드 근거로 쓰지 않는다.
- 8-K 본문(mu-20260624.htm)에는 수치가 없고 보도자료는 Exhibit 99.1에 첨부됨.

## 한계 (확인 필요)

- WebFetch는 작은 모델 요약이라 수치를 원문과 한 번 더 대조해야 한다. 카드 근거는 두 출처 일치분만.
- URL을 확보한 것은 Micron Q3 자료뿐. 다른 종목은 종목별로 열리는지 확인 필요.
- 10/3 관찰(Q4 FY26 Prepared Remarks가 s25.q4cdn.com으로 리디렉트)은 이번에 재확인하지 않음.

## 권장 절차 (사용자 승인 시 검토 흐름에 반영)

1. 확인할 주장의 회사·분기를 정한다.
2. WebSearch로 IR 보도자료·SEC Archives 문서 URL을 찾는다(주장당 검색 3회 이내).
3. WebFetch로 열어 수치를 읽고, 보도자료와 10-Q처럼 두 출처로 대조한다.
4. 안 열리거나 불일치하면 "미확인"으로 둔다.

## 출처

- https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Results-for-the-Third-Quarter-of-Fiscal-2026/default.aspx
- https://www.globenewswire.com/news-release/2026/06/24/3317151/14450/en/micron-technology-inc-reports-record-results-for-the-third-quarter-of-fiscal-2026.html
- https://www.sec.gov/Archives/edgar/data/723125/000072312526000015/mu-20260528.htm
- https://www.sec.gov/Archives/edgar/data/723125/000072312526000013/mu-20260624.htm
- https://www.sec.gov/robots.txt
