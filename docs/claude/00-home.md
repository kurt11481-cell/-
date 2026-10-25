---
id: 00-home
type: home
status: current
as_of: 2026-10-22
summary: "Obsidian으로 docs/claude를 열 때 첫 화면 — 고치면 안 되는 파일, 지금 상태 보는 곳, 찾는 곳. 입구일 뿐 원본이 아님(원본은 각 파일·관제판)."
consumers: "사장(Obsidian PC 창) · Cowork 세션(재개·찾기 입구). 비서·팀장회의·자동 코어는 읽지 않음"
source_decision: "duet-1022 Q1 a (2026-10-22 18:41) = obs-1022b Q1 a ③ (지식 문서 사본 제외)"
---

# 투자_V2 홈

## ⚠ 고치면 안 되는 파일 — 편집·이름 바꾸기·옮기기·사본 만들기 금지
자동 코어가 이 파일들을 매일 직접 읽는다. 손대면 다음 판정에 바로 반영된다(obsidian-ops-review-2026-10-22.md 4절).

| 파일 | 손대면 |
|---|---|
| integrated-stock-cards-v1-2026-10-02.md · watch-card-LITE-2026-10-03.md · watch-card-PWR-2026-10-03.md · watch-card-PLTR-2026-10-17.md | 카드 절 해시가 어긋나 그 종목 주문표가 안 나옴(매수·매도 모두) |
| m6-relative-comparison-7stock-*.md (2개) | 이름 바꾸면 매수 요건 막힘. **본문에 종목 코드를 넣거나 같은 이름으로 사본을 만들면 매수 관문이 풀림** |
| recovery-gate-R-REC1-2026-10-09.md | **EV3 이벤트 줄을 지우면 충격 사건이 사라져 매수 관문이 풀림** |
| *-builder-prompt.md | 개발 실행이 멈춤 |
| ceo-weekly-report.md | 회의 중 고치면 그 주 보고 실패. "- 답:" 줄을 직접 쓰면 결정된 것처럼 보이지만 반영은 안 됨 |
| external-claims-ledger.md | "### EXT" 머리를 바꾸면 주간 보고에서 빠짐 |

- 이 구멍(굵은 글씨 두 줄)을 막는 수정은 권한·한도 대기열에 있다(관제판 duet-q4-coreinput). 막히기 전까지는 위 규칙이 유일한 방어선.
- 볼트는 **읽기 보기**로 쓴다. 고칠 일은 Cowork에 말로 한다.
- Obsidian은 저장할 때 Windows 줄바꿈(CRLF)을 LF로 바꾼다(2026-10-22 22:11 시험: CRLF 4줄 → LF 4줄). 이 저장소의 CRLF 파일이나 해시로 고정된 파일을 Obsidian에서 고치면 해시가 깨진다 — 편집은 ceo-inbox/ 새 노트만.
- **계좌·주문 화면 캡처, 보유 종목·수량·금액은 여기 두지 않는다** — 이 폴더는 GitHub로 올라간다.
- 사장 메모·아이디어는 ceo-inbox/ 에(.md만). 개인 메모(일기·좋은 글)는 개인 볼트(E:\사업\##금동한\Obsidian\Obsidian)에.

## 지금 상태 보기 (휴대폰에서도 열림)
- 개발 관제판 — 작업 진행·결정함: https://claude.ai/artifact/PM54MdPfrgYt4LfFxQT9Tu
- 주간 팀장회의(사장 보고): https://claude.ai/artifact/GccBmdQcQopX415T5TRFWN
- 통합점검(주문표 패널): https://claude.ai/artifact/DuS4d8Fa9qZWceBJWjTU6d
- 미국주식 현황판(보유): https://claude.ai/artifact/K5HqLvCGfQD9AQNbSHVE3Q

## 찾기
- [로드맵](roadmap.md) — 개발·운영이 어디까지 왔고 다음이 무엇인지
- [라이브러리](library.md) — 문서·자료 목록의 입구
- [막혔다 푼 방법](ops-fixes.md) — 오류 문구로 검색
- [현행 결정 색인](active-decisions.md) — 지금 유효한 사장 결정. 변경 제안 전에 먼저 검색
- 결정 문서 찾기: [자동 목록](INDEX-auto.md)에서 결정 id(예: duet-1022)로 검색
- 검색 요령(Ctrl+Shift+F): 종목 `/\bNBIS\b/` · 결정 id `"duet-1022"` · 폴더 `path:scheduled-prompts` (예약 지시문 .txt는 Obsidian 목록에 안 나옴 — 원본은 claude.ai 예약 작업)
- 문서 아래 "언급한 문서" 목록 = 이 문서 이름을 적은 다른 문서("링크되지 않은 언급"을 눌러 펼침). **언급 줄에 마우스를 올리면 나오는 "링크" 버튼은 누르지 않는다** — 누르면 그 원본 문서가 고쳐진다(줄바꿈·해시가 깨짐).

### 보기 (파일 이름·수정 시각만, 표에서 고치지 않음 — obs-sys Q1 a)
최근 바뀐 문서(7일, 30개):
![[00-views.base#최근 바뀐 문서]]

자동 코어가 읽는 문서 — 수정 시각이 바뀌면 Cowork에 알림:
![[00-views.base#고치지 말 것]]

운영 규칙(플레이북·해결집·예약 지시문 목록):
![[00-views.base#운영 규칙]]

## 원칙
- 원본은 제자리에 있다. 이 노트·로드맵·라이브러리는 입구라서 판단 근거가 아니다.
- 결정은 Cowork 투자_V2 대화에서 사장 원문으로 한다(일지·대조·정책/상태·권한 결정은 지금 규칙상 거기서만 유효).
- 이 노트의 경로는 T4(docs/claude → archive/ 이동) 때 다시 확인한다.
