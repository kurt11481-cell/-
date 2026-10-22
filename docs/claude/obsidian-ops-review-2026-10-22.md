---
id: obsidian-ops-review-2026-10-22
title: "\"시스템이 Obsidian을 기반으로 운영\" 타당성 검토 + 수정안 (obs-1022b)"
date: "2026-10-22"
status: "결정은 duet-1022로 흡수(duet-redesign-2026-10-22.md 3·6절) — Q1 a는 지식 문서 사본만 뺀 판으로 duet-1022 Q1에, Q2는 duet-1022 Q4로"
class: "검토 + 변경 제안. Q1 a = docs/claude 문서(입구 노트 3장·지식 문서 사본 3개)·Obsidian 설정·make-index.py 출력 1개 추가·관제판 규칙 1줄 + 비서 지시문 교체 1건(표시 추가만, 별도 승인). 새 예약 작업 없음. Q2 a = 자동 코어 입력 문서 보호(권한·한도 경로 등록만)"
authority: "order_authority=false · quantity_authority=none · 키움 없음 · 자동 코어·통합점검 입력 불변 · 증거 가중 0"
consumers: "사장(Obsidian PC 창) · 비서 제안(월~토 09:25, v1.1 승인 뒤 '멈춤 의심' 후보) · Cowork 세션(00-home·roadmap·library·INDEX-research-auto를 재개·찾기 입구로)"
weekly_user_touch: "0 (1회성 = 결정 1줄 + 비서 교체 승인 1줄·PC 앱 승인 1번 + Obsidian 닫아도 되는 시각 답·CRLF 시험 파일 저장 1~2번 또는 컴퓨터 사용 승인)"
supersedes: "obsidian-vault-design-2026-10-22.md (obs-1022)"
summary: "Obsidian 앱이나 노트를 운영 엔진·원본으로 삼는 것은 불합리. 이미 모든 작업이 쓰는 docs/claude를 Obsidian으로도 여는 창은 합리적. 원본은 제자리에 두고 볼트 안 입구·자동 목록으로 한곳에서 찾게 한다. '사장 기억 없이'의 실제 빈칸은 이벤트·수동 대기와 보류 작업 20건이 어떤 점검에도 안 뜨는 것이고, 자동 코어가 docs/claude md 7개를 커밋 검사 없이 읽어 편집으로 매수 관문이 풀릴 수 있는 구멍이 있다."
decision: "대기 — obs-1022b Q1 a(권장)/b/c · Q2 a(권장)/b"
---

# "시스템이 Obsidian을 기반으로 운영" 타당성 검토 (2026-10-22)

사용자 요청(2026-10-22): 16:28 개발·운영 흐름 로드맵 · 작업 플로우 점검(어디까지 진행, 어디서 중단, 어떻게 처리) · 라이브러리 역할 · "시스템이 Obsidian을 기반으로 운영(각 팀장·비서·관제판·점검 등이 Obsidian을 조회)" · 사장 기억에 의존하지 않는 개발·운영. 16:32 "합리적인가 검토". 17:24 "옵시디언에 시스템 개발 운영 연구 현황 기록을 남기는가? 파편화된 시스템 기록을 한곳에 모아야 한다." 조건(15:54): 무료 기능만.

## 0. 결론
1. **"Obsidian = 운영 엔진·기록 원본"은 불합리, "Obsidian = 이미 있는 공용 기록 폴더(docs/claude)를 여는 창"은 합리적이다.** 에이전트는 앱이 아니라 파일과 관제판 DB를 읽는다.
2. **현황 기록이 Obsidian에 남는가:** 창만 열면(Q1 b) 일부만 남는다. 원본을 옮기면 자동 코어·예약 작업·스킬 경로, 휴대폰 대시보드, GitHub 차단선(보유·현금·주문표 기록은 일부러 git 밖, .gitignore:45-57)이 깨진다. 그래서 **원본은 제자리, 볼트 안에는 입구·자동 목록**으로 모은다(5-1절 표). 보유 종목·수량·금액·주문표 값은 볼트(= GitHub로 가는 곳)에 쓰지 않는다.
3. 에이전트에게 Obsidian은 더해 주는 것이 없다. 비서는 관제판(상태 4종)과 ceo-weekly-report.md를, 팀장회의는 관제판과 고정 목록·이번 주 바뀐 최상위 문서 요약을 읽는다(secretary-daily.txt:11-12, ceo-weekly-meeting.txt:22, ceo.py:29 — 하위 폴더 제외).
4. **"사장 기억 없이"의 실제 빈칸:** 대기 32건 중 이벤트 조건 16·수동 1과 보류 3, 합계 20건은 어떤 점검·화면에도 "재개 가능"이나 "멈춤"으로 뜨지 않는다(비서 ㉰·주간 met()·화면이 날짜·선행 작업 유형만 계산). 예: l2-review-1017(조건일 10/20, 마지막 갱신 10/19), event-ctx2(조건 10/16, 마지막 갱신 10/14). → 비서가 직접 "멈춤 의심"을 계산(Q1 a ⑤).
5. **docs/claude는 순수 기록이 아니다(발견된 구멍):** 자동 코어가 그 안의 md 7개를 커밋 검사 없이 매번 읽는다. 카드 절을 고치면 그 종목 주문표가 멈추고(매수·매도), M6 문서 본문에 종목 코드를 넣거나 같은 접두어 사본을 만들면 매수 요건 (4)가 풀리며, R-REC1 문서의 EV3 줄을 지우면 충격 사건이 사라져 매수 관문이 풀린다 — 다음 decide에 바로 반영(Q2).
6. 권장: Q1 a(창 + 입구·자동 목록 + 비서 멈춤 의심, **새 예약 작업 없음**), Q2 a.

## 1. "Obsidian 기반 운영"의 세 가지 뜻과 판정
| 뜻 | 판정 | 이유(원문) |
|---|---|---|
| ① 앱이 런타임: 에이전트가 Obsidian 앱(CLI·커뮤니티 REST 플러그인)을 거쳐 조회 | 불합리 | 비서·팀장회의는 파일을 직접 받아 읽음(secretary-daily.txt:7, ceo-weekly-meeting.txt 환경·3)). 앱을 끼우면 한 PC의 GUI가 켜져 있어야 하는 실패 지점만 늘어남. 자동 코어는 주변부 실패에 막히면 안 됨(CLAUDE.md Goal, 프로젝트 지침 7절) |
| ② 기록 원본을 노트로: 상태·정책·결정 일지·연구 기록 JSON과 관제판 DB를 노트로 교체 | 불합리 | (가) 기계 기록은 스키마 검증·추가 전용 스크립트로만 씀(CLAUDE.md Hard safety). 머리말은 깨지기 쉬움 — docs/claude 머리말 263개 중 103개 YAML 오류. (나) 관제판은 휴대폰에서 열리는 공용 DB이고 "사장 기억 대신 한곳"이 목적(dev-dashboard-protocol.md:4), 기한 지난 결정 기본값 처리까지 있음(:41). 무료 조건에서 노트는 휴대폰 열람 불가(Obsidian Sync 유료 $4/월 연 결제·$5/월 월 결제 — obsidian.md/pricing) (다) 보유·현금 기록은 git 밖(.gitignore:45-57) — 노트(docs/claude)는 GitHub로 감 |
| ③ 창: docs/claude를 볼트로 열고 입구·자동 목록을 더함 | 합리적(조건부) | 원본 하나, 새 저장소·서버·예약 작업 없음, 무료. 조건은 4절(고치면 안 되는 파일)·2절 개인정보 |

## 2. 요구별 대응
| 요구 | 이미 있는 것(원문) | 빈칸 → 처방 |
|---|---|---|
| 어디까지 진행 | 관제판 작업별 status·next·updatedAt(dev-dashboard-protocol.md:4). 열린 작업 42(waiting 32·planned 4·paused 3·active 2·decision 1) | 없음 |
| 어디서 중단 | 비서 매일: 결정 기한·재개 가능(date·after만)·막힘·7일 넘게 멈춘 active(secretary-daily.txt:15-19). 주간 check.py R1·R2·R4·R5·R6(:19,51,70,80,87 — 5개) | 이벤트·수동 대기 17 + 보류 3이 어디에도 안 뜸 → Q1 a ⑤ |
| 어떻게 처리 | 관제판 done 작업 doneAt·commit·note + log(dev-dashboard-protocol.md:29,54) | 없음(roadmap.md에서 링크) |
| 로드맵 | 관제판 streams·재설계 문서에 흩어짐. redesign-t4가 정본 3개(SYSTEM·RUNBOOK·DECISIONS)와 docs/claude → archive/ 이동을 맡음(관제판 redesign-t4 doneWhen) | roadmap.md 1장(T4 정본의 첫 판 — T4가 흡수) |
| 라이브러리 | INDEX-auto.md · library/INDEX.md(문서 밖 최신본은 수동, :45) · ops-fixes.md · playbooks/README.md · scheduled-prompts/README.md | library.md 1장 + make-index.py가 연구 자료 목록 자동 생성(Q1 a ④) |
| 팀장·비서가 조회 | 관제판·지정 파일을 읽음 | 입구 노트는 읽게 하지 않음(0절 3) |

## 3. 처음 안(obs-1022)과 달라지는 것
| 항목 | 처음 판단 | 재검토 | 이유 | 원문 |
|---|---|---|---|---|
| 볼트 위치 | 외부 볼트 + 저장소 한 방향 사본 | docs/claude를 그대로 볼트로. 외부 볼트(E:\사업\##금동한\Obsidian\Obsidian)는 사장 개인 메모(일기·좋은 글)용 | 새 사용자 정보: 시스템 기록을 한곳에서. 사본은 근거가 아니고(검토 안정성 V1) 늦음 | 사용자 16:28·17:24 |
| .obsidian 폴더 | 처음엔 저장소 볼트를 버린 이유 | 추적 안 된 채 둠. 커밋(목록 경로만, commit-docs.ps1:42-55)·개발 파이프라인(devpipe.py:1200-1208)을 막지 않음. 자동 코어는 막지 않고 실행 기록 dirty_paths에 이름만 남김(auto_core_reconcile.py:1113-1116,1194-1196). 무시 설정(.gitignore·info/exclude)은 하지 않음 — .gitignore는 보호 경로, info/exclude는 효과가 같아 우회 | 원문 대조 | 같음 |
| 사본 동기화·현황 모음 예약 작업 | 매일 작업 신설 | 없음. 멈춤 의심은 비서가 직접 계산(이미 매일 관제판을 읽음), 연구 자료 목록은 make-index.py(결정론) | REUSE(V3 순서) | secretary-daily.txt:11,17 · make-index.py:1-5 |
| 백업 | (처음 안) OneDrive | docs/claude는 _pending으로 커밋된 파일만 GitHub로(현재 브랜치가 main이 아닐 때 push, 마지막 OK 10/21 23:50). Obsidian에서 새로 쓴 메모는 커밋 전까지 백업 없음 | 원문 대조 | offsite-bak-report.md:4,6 · backup/LATEST.json |

## 4. 고치면 안 되는 파일 (00-home 맨 위에 표시)
| 파일 | 고치거나 이름을 바꾸거나 사본을 만들면 | 원문 |
|---|---|---|
| integrated-stock-cards-v1-2026-10-02.md · watch-card-LITE-2026-10-03.md · watch-card-PWR-2026-10-03.md · watch-card-PLTR-2026-10-17.md | 카드 절 해시 불일치 → 그 종목 주문표 없음(매수·매도 모두) | card-evidence-registry.json card_doc · auto_core_inputs.py:4-7,172-179 |
| m6-relative-comparison-7stock-*.md (2개) | 이름을 바꾸면 매수 요건 (4) 막힘. **본문에 종목 코드를 넣거나 같은 접두어 사본을 만들면 요건 (4) 통과(관문 완화)** — 접두어로 시작하는 md를 모두 읽음 | auto_core_inputs.py:38,195-197 · auto_core_rules.py:987-993 |
| recovery-gate-R-REC1-2026-10-09.md | **EV3 이벤트 줄을 지우면 사용자 지정 충격 사건이 사라져 매수 관문 완화** | auto_core_decide.py:62 · auto_core_rules.py:733-734 · 문서 :71 |
| *-builder-prompt.md (커밋된 개발 지시문) | 개발 실행이 멈춤 | devpipe.py:1360 PROMPT_DIFFERS_FROM_HEAD |
| ceo-weekly-report.md | 회의 실행 중 고치면 그 주 보고 기록 실패. "- 답:" 줄을 직접 쓰면 비서·다음 회의는 결정된 것으로 보지만 Cowork 반영·기본값 기록은 없음 | ceo-weekly-meeting.txt:39 · secretary-daily.txt:16 |
| external-claims-ledger.md | "### EXT" 머리를 바꾸면 그 항목이 주간 보고에서 빠짐(주문 영향 없음) | ceo-weekly/ceo.py:89,350-351 |
- 규칙: 볼트는 기본 읽기 보기. 이름 바꾸기·옮기기·사본 만들기 하지 않음. 고칠 일은 Cowork에 말로. 계좌·주문 화면 캡처와 보유·수량·금액은 볼트에 두지 않음(GitHub로 감).

## 5. 결정 요청 obs-1022b (기한 2026-10-29)
**Q1 Obsidian 창 + 기록 한곳 찾기** — 무응답 = c
- **a) 권장** — ① 사장이 알려 준 시각에 Obsidian 닫기 → docs/claude를 볼트로 등록 → 다시 열기 ② 설정: 새 탭 읽기 보기, 내부 링크 자동 갱신 끔, sync 끔, 일일 노트 끔, 새 노트·첨부·새 캔버스 위치 = ceo-inbox/ ③ 입구 노트 3장(00-home.md · roadmap.md · library.md, 제목 한글) + 지식 문서 3개 1회 사본(docs/claude/knowledge/, 머리말 "사본 — 판단 근거는 claude.ai 프로젝트 원본, as-of·원본 sha256", 바뀌면 Cowork가 갱신) + _pending 커밋(ceo-inbox는 .md 파일만 한 줄씩, 첨부·폴더 경로 금지) + 관제판 redesign-t4 next에 "입구 노트 흡수·archive 이동 때 링크 재확인" 1줄 + dev-dashboard-protocol.md에 "단계가 바뀌면 roadmap.md도 고침" 1줄 ④ make-index.py 출력 1개 추가: INDEX-research-auto.md(chatgpt_종목분석결과의 md·pdf 목록·날짜·링크, 경로의 #는 %23, 첫 실행에서 열리는지 확인) — library/INDEX.md "문서 밖 최신본" 수동 줄을 대신 ⑤ 비서 v1.1 "멈춤 의심(팀 처리)": event·manual 대기는 resume.date ≤ 오늘이면 바로, 날짜가 없으면 updatedAt 7일 초과 시 / paused는 after[] 선행이 모두 열린 목록에 없을 때만(관제판 paused 조회 1번 추가). 표시 추가만(제약 완화 아님). 교체 전 결정론 시험(H1) 결과와 sha256을 보인 뒤 `결정 obs-1022b-sec: 승인` 1줄 + PC 앱 승인 ⑥ CRLF 1회 시험(외부 개인 볼트 시험 파일)
- b) ①~③만(창만)
- c) 안 함
**Q2 자동 코어 입력 문서 보호** — 무응답 = b
- **a) 권장** — 4절 위 3행(md 7개)을 자동 코어가 커밋본으로만 읽거나 미커밋 변경이면 매수 쪽만 막는(매도 비차단) 수정을 권한·한도 경로 작업으로 관제판에 등록(착수는 진행 중 권한 작업 1개 한도 뒤, 설계·Judge는 그때)
- b) 현행 유지(알림만)
- 답 예: `결정 obs-1022b: Q1 a, Q2 a`

## 5-1. "현황 기록이 Obsidian에 남는가" — 기록 원천별 자리
| 기록 | 원본 자리(원문) | Obsidian에서 찾는 법 |
|---|---|---|
| 개발·운영 문서(설계·검토·결정 문서·개발 지시문·해결집·카드·플레이북) | docs/claude | 볼트 자체(원본) |
| 예약 지시문 | 원본 = claude.ai 예약 작업, 사본 = docs/claude/scheduled-prompts(README:3-4) | 볼트(사본) |
| 작업 진행·결정 대기·처리 내역 | 관제판 DB(claude.ai) | 00-home·roadmap의 관제판 링크(휴대폰 겸용). 멈춤 의심은 비서 알림 |
| 주간 운영 요약·예약/Windows 작업 출근부 | docs/claude/ceo-weekly-report.md | 볼트(원본) |
| 통합점검 기록 | 통합점검 대시보드 DB runs — 파일 아님(library/INDEX.md:47) | 00-home 대시보드 링크 |
| 자동 코어·백업·PC 상태·비서·개장 전·시장 메모·개발 실행 | workspace/outputs(폴더 58), 일부 git 밖(.gitignore:45-57) | INDEX-outputs-auto.md(폴더·파일 수·날짜만, 내용 안 옮김) |
| 카드·관심 종목·외부자료 원장 | docs/claude 문서 + card-evidence-registry.json·watchlist-registry.json | 볼트(문서) |
| 종목·옵션·기술 분석, 외부 PDF, SAVE 리포트 | E:\사업\##금동한\chatgpt_종목분석결과(저장소 밖) | INDEX-research-auto.md 목록·링크(파일은 제자리, 기본 앱으로 열림 — 확인 필요) |
| 지식 문서 | claude.ai 프로젝트(원본) · chatgpt md_주식(구판) | docs/claude/knowledge 사본(as-of) |
| 결정 일지 | stock-strategy-system/decision_journal.json(git 밖) | 넣지 않음(보유·계좌 활동, 소비자 없음) |
| 사장 생각·아이디어 | 없음 | docs/claude/ceo-inbox(볼트, 커밋 시 GitHub) — 개인 메모는 외부 볼트 |
| Claude 기억·대화 | claude.ai | 들어오지 않음(세션 결과를 docs/claude에 남기는 규칙이 이미 있음) |

## 6. 하지 않음
관제판·JSON 기록을 노트로 옮기기, 보유·수량·금액·주문표 값을 볼트에 쓰기, 새 예약 작업, Obsidian 플러그인·CLI 연동, 통합점검·자동 코어가 볼트를 읽게 하기, 팀장회의·비서가 입구 노트를 읽게 하기, 옛 문서 머리말 일괄 수정(CRLF·해시), .gitignore·info/exclude 수정.

## 7. 바뀔 조건
- 무료로 휴대폰에서 docs/claude 볼트를 안정적으로 볼 방법 확인 → 관제판 일부를 노트로 옮기는 안 재검토(1절 ②-나).
- CRLF 시험에서 Obsidian이 줄바꿈 유지 → 사장 편집 허용 범위 넓힘(4절 파일은 계속 금지).
- 비서 "멈춤 의심"이 2주 동안 0건 → 표시 빼기 제안.
- Q2 수정 병합 → 4절 "관문 완화" 경고 삭제.
- T4가 docs/claude → archive/ 이동 → 입구 노트·4절 경로 재확인.

## 8. 내장 재검토 기록
- 1회차(16:4x, 13건): 결론을 바꾼 것 6건 — 자동 코어가 docs/claude md 7개를 읽음(본 세션 확인) · 남는 위험 대상 정정 · 비서 안 check.py 재사용 불가 · 비서가 이미 매일 재개·기한·멈춤을 봄 · info/exclude 삭제 · 관제판 id를 obs-1022b로. 문구 7건.
- 2회차(17:2x, 반영분, 13건): 결론을 바꾼 것 4건 — 편집으로 매수 관문이 풀리는 경로(본 세션 확인) → Q2 · 이벤트·수동 대기 17 + 보류 3이 안 뜸(관제판 조회 확인) → 비서 표시 · 비서·팀장회의는 입구 노트를 읽지 않음 · redesign-t4 정본·archive와 겹침. 문구 9건.
- 17:24 추가 요구 반영분 재검토(17:4x, 15건): 결론을 바꾼 것 4건 — ① 현황 노트가 보유·주문표 값을 GitHub로 내보내 git 차단선 우회(.gitignore:45-57 본 세션 확인) → 볼트에 그런 값 금지 ② 주간 팀장회의는 하위 폴더를 안 읽음(ceo.py:29 확인) → 자동 소비자 없음 ③ 멈춤 의심 정의 정정(날짜 지난 event 즉시, paused는 선행 닫힘일 때만) ④ 새 예약 작업 없이 비서 + make-index.py로 가능(REUSE) → "현황 모음" 작업 삭제. 문구 반영: 날짜 덮어쓰기 문제 사라짐, 승인은 H1·sha256 뒤 별도 1줄 + PC 앱 승인, 결정 일지 행 삭제, 링크 # 처리, 원천 표 보강(예약 지시문 원본, 출근부, dev-runs), 머리말·번호 정합.
- 미해결 2: CRLF 저장 동작, 저장소 밖 파일 링크가 기본 앱으로 열리는지(둘 다 Q1 a 실행 중 시험, 그 전엔 읽기 보기).
- 2026-10-22 22:11 CRLF 시험 결과(duet-obs): 개인 볼트 시험 파일(CRLF 4줄, 125 B)을 사장이 한 글자 고쳐 저장 → LF 4줄·CRLF 0(127 B). 7절 "줄바꿈 유지" 조건 미충족 → 사장 편집 허용 범위 넓히지 않음(NO_CHANGE, 읽기 보기 유지, 편집은 ceo-inbox 새 노트만). 저장소 밖 링크 열림 시험은 duet-idx 첫 실행 때.
