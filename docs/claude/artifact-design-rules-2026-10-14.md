---
id: artifact-design-rules-2026-10-14
type: standing-rule
status: active (2026-10-14 사용자 지시 "페이지를 고칠 때 디자인 시스템 색·글자 규칙 유지")
as_of: 2026-10-14
summary: 투자_V2 화면(아티팩트) HTML을 고치거나 재게시할 때 투자_V2 디자인 시스템의 색·글자·누르는 요소 크기 규칙을 유지한다. 표시 전용 규칙이며 권한·정책·상태·주문과 무관하다.
consumers: [Cowork 세션(아티팩트 HTML 재게시 전), dev-dashboard-protocol.md, dashboard-order-panel-2026-10-07.md, 미국주식 현황판·개발 관제판·통합점검 화면]
---

# 투자_V2 화면 디자인 유지 규칙 (2026-10-14)

## 1. 규칙
- 아래 화면의 HTML을 고치거나 재게시하는 세션은 이 문서의 색·글자·크기 규칙을 유지한다. 새 칸을 추가할 때도 같은 변수와 크기를 쓴다.
- 재게시 전에 Artifact `read`로 현재 버전을 읽고 그 위에서 고친다(이전 사본으로 덮어쓰면 디자인이 되돌아간다).
- 이 규칙은 화면 표시만 다룬다. 데이터 읽기·쓰기, 계산·판정, 권한(order_authority=false, quantity_authority=none)은 바꾸지 않는다.
- 저장소(db) 데이터만 갱신하는 예약 작업은 HTML을 재게시하지 않으므로 해당 없음(us-stock-board-close, integrated-check-daily, dev-board-weekly-review 확인 2026-10-14).

## 2. 대상 화면
| 화면 | 주소 | 2026-10-14 적용 버전 |
|---|---|---|
| 디자인 시스템 "투자_V2" (기준) | https://claude.ai/artifact/KwbvzJzU6HFMJZE6TDFVTY | version 15 |
| 미국주식 현황판 | https://claude.ai/artifact/K5HqLvCGfQD9AQNbSHVE3Q | version 6 |
| 투자_V2 개발 관제판 | https://claude.ai/artifact/PM54MdPfrgYt4LfFxQT9Tu | version 5 |
| 투자_V2 통합점검 | https://claude.ai/artifact/DuS4d8Fa9qZWceBJWjTU6d | version 20 |

기준값의 원본은 디자인 시스템의 `project/tokens.json`과 `project/README.md`다. 값이 다르면 디자인 시스템이 우선한다.

## 3. 색 (라이트 = 토스 TDS 팔레트 중 대비 4.5:1 이상 단계, 다크 = 투자_V2 다크)
| 역할 | 라이트 | 다크 |
|---|---|---|
| 페이지 바탕 | #f2f4f6 | #0b1220 |
| 카드 바탕 | #ffffff | #121b2e |
| 본문 글자 | #191f28 | #e8eefb |
| 보조 글자 | #4e5968 | #9fb0cc |
| 구분선(장식) | #e5e8eb | #26334d |
| 입력칸·버튼 테두리 | #6b7684 | #6b7a96 |
| 대표색(버튼·링크·포커스) | #1b64da | #7aa2f7 |
| 연한 강조 바탕 | #e8f3ff | #172544 |
| 상승 | #027648 (초록) | #4ade80 |
| 하락 | #bc1b2a (빨강) | #f87171 |
| 경고 | #92400e | #fbbf24 |

- 가격 등락은 국제 관례: 초록=상승, 빨강=하락(사용자 결정 2026-10-14). 색만으로 구분하지 않고 ▲▼와 +/− 부호를 함께 쓴다.
- 예외: 통합점검 "주문 지시" 칸의 매수·매도 색은 키움 화면 관행(매수 빨강 #C62F2F / 다크 #FF7A72, 매도 파랑 #1F5FC4 / 다크 #78AEFF)을 유지한다(사용자 결정 2026-10-14, 입력 실수 방지). CSS 변수 `--buy`/`--sell`로 가격 등락 `--up`/`--down`과 분리한다.
- 새 색을 넣으면 글자 대비 4.5:1(24px 이상 3:1), 입력칸 테두리·아이콘 3:1을 라이트·다크 모두에서 계산해 확인한다.

## 4. 글자 (KRDS 기준)
- 글꼴: "Pretendard GOV", "Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif. 웹 글꼴은 Google Fonts의 Noto Sans KR(400·700). 숫자·코드용 고정폭 글꼴은 유지해도 된다.
- 굵기는 400(본문)과 700(제목·강조) 두 가지만 쓴다.
- 크기: 본문 17px, 표·빽빽한 수치 15px, 단위·시각 같은 짧은 표기 13px(최소). 문장은 16px 아래로 내리지 않는다. 제목 19/24px, 페이지 제목 휴대폰 22px · PC 24px 이상.
- 줄간격 1.5.

## 5. 누르는 요소와 화면 폭
- 버튼·선택칸·입력칸·체크박스 줄은 높이 44px 이상(기본 버튼 48px). 키보드 포커스 외곽선 3px, 대표색.
- 휴대폰 폭(375px)에서 페이지 전체가 가로로 밀리지 않게 한다. 넓은 표는 표 안에서만 가로 스크롤하고, 휴대폰에서는 목록 줄(ListRow) 모양을 우선한다(미국주식 현황판 보유 종목 참고).

## 6. 재게시 전 확인
1. 현재 버전을 `read`로 읽고 그 위에서 고친다.
2. 휴대폰(375px)·PC 폭, 라이트·다크에서 렌더해 오류·가로 밀림이 없는지 본다.
3. 바꾼 색 조합의 대비를 계산한다.
4. 바뀐 점을 사용자에게 한국어로 짧게 알린다.
