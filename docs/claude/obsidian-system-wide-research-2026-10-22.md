---
id: obsidian-system-wide-research-2026-10-22
title: "Obsidian 시스템 전체 활용 연구 (obs-sys)"
date: "2026-10-22"
status: "결정됨 — obs-sys Q1 a 완료(23:2x) · Q2 a는 duet-sec 뒤 비서 v1.2 교체 대기"
class: "검토 + 변경 제안. Q1 = docs/claude 새 파일 1개(00-views.base)·00-home 4줄·Obsidian 설정 1개(.obsidian/backlink.json, git 밖). Q2 = 예약 지시문 1건 교체(비서 v1.2, 메모 개수 표시 추가만). 정책·상태·권한·주문·자동 코어 입력 불변"
authority: "order_authority=false · quantity_authority=none · 키움 없음 · 증거 가중 0"
consumers: "사장(Obsidian PC 창) · Cowork 세션(찾기·재개 입구) · 비서 제안(Q2 a일 때 ceo-inbox 새 메모)"
weekly_user_touch: "0 — Q2 a를 켜면 사장이 메모를 쓴 주에만 'ceo-inbox 처리' 1번(메모를 안 쓰면 0) (1회성: 결정 1줄 · Q1 a·b면 Obsidian 닫아도 되는 시각 답 1번 · Q2 a면 비서 교체 승인 1줄 + PC 앱 승인 1번)"
basis: "사장 요청 2026-10-22 '시스템 전체에 Obsidian 적용 연구'(duet-judg 뒤) · 영상 jSFvVxmZQPQ 한국어 자동 자막(PC %TEMP%\\watch-test, 22:51 받음) · obsidian-ops-review-2026-10-22.md · duet-redesign-2026-10-22.md"
---

# Obsidian 시스템 전체 활용 연구 (2026-10-22)

## 0. 결론
1. **영상에 새 기능은 없다.** 입문 강의(볼트·마크다운·링크·백링크·태그·그래프·속성+검색·캔버스·커뮤니티 플러그인)다. 자동화·AI 연동은 도입부에 이름만 나온다(자막 원문).
2. **"시스템 전체"의 범위는 문서층까지다.** Obsidian은 볼트(docs/claude) 안만 본다. 자동 코어 결과·통합점검 기록·보유·결정 일지·관제판은 일부러 볼트 밖에 있다(GitHub 차단선 .gitignore:45-57, 휴대폰 열람, 원본 하나 — obsidian-ops-review 1절·5-1절). 이 경계는 그대로 둔다.
3. **속성 기반 화면은 지금 자료로는 못 쓴다.** docs/claude md 436개 중 머리말이 읽히는 것 179(41%), 깨진 것 106, 없는 것 151. status 칸은 102개에만 있고 값이 자유 문장이라 "current"는 25개뿐(이번 세션 python yaml 집계). 옛 문서 머리말을 고치는 것은 금지(CRLF·해시, obsidian-ops-review 6절, 00-home CRLF 경고).
4. **그래서 쓸 수 있는 것은 "파일 자체 정보"와 "이름 언급"이다.** 파일 이름·폴더·수정 시각은 머리말과 상관없이 Bases가 읽는다(file.name·file.mtime·file.folder — obsidian.md/help/bases/syntax). 문서 345개가 다른 문서의 파일 이름을 글자로 적고 있어(링크는 3개 파일뿐), 백링크 창의 "링크 안 된 언급"이 "이 문서를 언급한 문서"를 손대지 않고 보여 줄 수 있다(obsidian.md/help/plugins/backlinks — "unlinked occurrence of the name of the active note"). 실제로 잡히는지는 확인 필요(5절).
5. 권장: **Q1 a**(문서 아래 언급 목록 켜기 + 보기 파일 1개 + 홈에 찾기 요령, 새 예약 작업 없음) · **Q2 a**(비서가 매일 사장 메모함의 새 메모 **개수만** 알림 — 지금은 사장이 말할 때만 읽혀 "사장 기억 의존"이 남음. 내용은 읽지 않아 주입·노출 위험 없음).

## 1. 영상 기능 → 투자_V2 대응 (검토 순서 NO_CHANGE → REMOVE → REUSE → REPLACE → ADD)
| 영상 기능 | 투자_V2에서 | 판정 | 이유(원문) |
|---|---|---|---|
| 볼트 = 폴더 하나 | docs/claude가 볼트(10/22 22:1x 등록) | NO_CHANGE | duet-1022 Q1 a 실행 기록(obsidian-ops-review 끝 줄) |
| 동기화(유료) | 휴대폰은 관제판·대시보드가 맡음 | NO_CHANGE | 무료 조건(사장 15:54). 영상도 "월 구독 유료"라고 함 |
| 마크다운 쓰기 | 볼트는 읽기 보기, 편집은 ceo-inbox 새 노트만 | NO_CHANGE | Obsidian 저장 시 CRLF→LF(22:11 시험, 00-home) |
| 링크 `[[ ]]`·그래프 뷰 | 링크 있는 파일 3·위키링크 4 → 그래프는 거의 빈 점 | REMOVE(쓰지 않음) | 옛 문서에 링크를 넣는 것은 편집 금지에 걸림. 새 문서만 링크로 쓰면 반쪽 그래프 |
| 백링크 + 링크 안 된 언급 | 파일 이름 언급 345개 문서 | **REUSE — Q1 ①** | 문서를 고치지 않고 "누가 이 문서를 언급했나"가 보임. 설정 1개(.obsidian, git 밖) |
| 태그 `#` | 본문 편집 필요 | REMOVE | 편집 금지 |
| 속성(머리말)+검색 `[key:value]` | 머리말 읽히는 문서 41%, status 자유 문장 | 지금은 쓰지 않음 | 3절 수치. 새 문서 머리말 표준은 T4 정본(redesign-t4)이 맡음 — 거기서 다시 |
| 검색 결과 노트에 넣기(```query```)·검색 연산자 | 종목별 언급 문서 찾기 | **REUSE — Q1 ③(요령만)** | 종목 목록을 노트에 적으면 손으로 맞춰야 하는 두 번째 원본이 됨(duet-redesign R2와 같은 이유) → 목록 노트 없이 00-home에 검색 요령 1줄(`/\bNBIS\b/` 꼴, obsidian.md/help/plugins/search) |
| Bases(데이터뷰 대체, 핵심 기능) | 파일 정보만으로 표 | **REPLACE — Q1 ②** | 커뮤니티 데이터뷰 대신 핵심 Bases(.obsidian core-plugins "bases": true, 이번 세션 확인). 칸은 file.* 만 둔다 — 속성 칸을 표에서 고칠 수 있는지는 도움말에 명시 없음(확인 필요)이라 속성 칸 자체를 넣지 않음 |
| 캔버스 | 시스템 지도 | 지금은 안 함 | 흐름은 관제판·주간 팀장회의 대시보드(휴대폰)가 원본. T4가 문서를 archive/로 옮기면 카드 경로가 끊김(링크 자동 갱신 끔, .obsidian/app.json). ceo-inbox/무제.canvas(빈 파일, 2 B)는 그대로 둠 |
| 템플릿(핵심) | 사장 메모 머리말 고정 | 안 함 | 핵심 템플릿은 자동 적용이 아니라 사장이 메모마다 넣어야 함(obsidian.md/help/plugins/templates) — 반복 손. Q2는 머리말 없이 "ceo-inbox 바로 아래 .md = 새 메모, 처리하면 Cowork가 ceo-inbox/옮김/으로 옮김"으로 판별 |
| 커뮤니티 플러그인(Dataview·Tasks·Excalidraw) | — | 안 함 | Bases·관제판이 대신함. 플러그인 코드는 볼트 파일 쓰기 권한을 가짐(보안 검토 필요, preferences "설치 전 검토") |

## 2. 시스템 영역별 — Obsidian에서 보이는가
| 영역 | 원본(원문) | Obsidian | 이번 제안 |
|---|---|---|---|
| 개발·검토·결정 문서, 해결집, 플레이북 | docs/claude | 볼트(원본) | Q1 ①② |
| 카드·M6·회복 관문 문서(자동 코어 입력) | docs/claude md 7개(00-home 표) | 볼트, 고치면 안 됨 | Q1 ② "자동 코어가 읽는 문서" 보기 — 수정 시각이 바뀌면 눈에 띔(표시만) |
| 카드 원장·관심 명단 | card-evidence-registry.json·watchlist-registry.json(JSON) | 안 보임(Obsidian은 JSON을 표로 못 읽음) | Q1 ③ 검색 요령으로 종목 이름이 나오는 문서를 찾음(원장 자체는 그대로) |
| 예약 작업 지시문 사본 | docs/claude/scheduled-prompts(README:3-4, 원본은 claude.ai) | 볼트(사본) | Q1 ② 보기 |
| 주간 팀장회의 보고 | docs/claude/ceo-weekly-report.md | 볼트 | 없음 |
| 외부자료 원장 | docs/claude/external-claims-ledger.md | 볼트 | 없음 |
| 자동 코어·비서·개장 전·SAVE·Next 샌디스크 주간 | workspace/outputs(폴더 58, INDEX-outputs-auto.md) | 목록만 | 없음(GitHub 차단선) |
| 통합점검 기록 | 대시보드 DB runs | 링크만(00-home) | 없음 |
| 관제판 작업 | 관제판 DB | 링크만 | 없음(원본 하나) |
| 종목·옵션 분석, 외부 PDF | E:\사업\##금동한\chatgpt_종목분석결과(저장소 밖) | 안 보임 | duet-idx(연구 자료 자동 목록)가 맡음 — 겹치지 않게 Q1 ③은 볼트 안만 |
| 사장 메모 | docs/claude/ceo-inbox | 볼트 | **Q2** — 지금은 읽는 작업 없음(사장이 "ceo-inbox 확인해줘"라고 할 때만, ceo-inbox/README.md). 지금 메모 0개(README·빈 캔버스뿐) |

## 3. 측정 (2026-10-22 23:0x KST, device_bash python, docs/claude 하위 md, .obsidian·__pycache__ 제외)
- md 436(이 문서 제외; 최상위 375, dev-runs 29, library 16, order-instructions 6, scheduled-prompts 6 …). 수정 시각 2026-10-15 00:00 이후 134(dev-runs·_pending 제외; 10/15 23:00 이후로 세면 120 — 재검토가 7×24시간으로 센 121과 같은 범위).
- 머리말: 읽힘 179 · YAML 오류 106 · 없음 151. 칸 빈도 id 174 · consumers 110 · status 102 · title 102 · date 102 · type 77. status 값: current 25 · draft 4 · 나머지 자유 문장.
- 링크: `](…md)` 있는 파일 3 · `[[` 있는 파일 4 · 다른 문서 파일 이름(…-YYYY-MM-DD.md)을 적은 파일 345 · 태그 비슷한 것 2.
- 커밋 경로: tools/commit-docs.ps1:42-44는 docs/claude/ 아래면 확장자와 상관없이 받음 → .base 파일도 _pending으로 커밋됨.

## 4. 결정 요청 obs-sys (기한 2026-10-29)
**Q1 볼트 보기** — 무응답 = c
- **a) 권장** ① 백링크 "문서 아래 표시" 켜기(.obsidian/backlink.json, git 밖 — 링크 안 된 언급 포함). Obsidian이 켜진 채 설정 파일을 고치면 앱이 덮어쓸 수 있어 "Obsidian 닫아도 되는 시각" 답 1번 필요 ② `00-views.base` 1개, 칸은 file.name·file.mtime·file.folder만, 보기 3개: 「최근 바뀐 문서」(수정 시각 최근 30개, dev-runs·_pending·INDEX-*-auto 제외) · 「자동 코어가 읽는 문서 — 고치지 말 것」(00-home 표의 7개 + 수정 시각, 표시만) · 「예약 지시문·플레이북·해결집」(scheduled-prompts·playbooks 폴더·ops-fixes.md). 00-home "찾기"에 `![[00-views.base#보기이름]]` 3줄(이름 없이 넣으면 첫 보기만 보임 — obsidian.md/help/bases/views) ③ 00-home "찾기"에 검색 요령 1줄: 종목은 `/\bNBIS\b/`, 결정 id는 `"duet-1022"`, 폴더는 `path:scheduled-prompts`. 종목 목록 노트는 만들지 않음. 실행 뒤 Cowork가 화면 캡처로 ①②가 뜨는지 확인 — 안 뜨는 것은 되돌림(NO_CHANGE).
- b) ①만 · c) 안 함
**Q2 사장 메모함 알림** — 무응답 = b
- **a) 권장** 비서 제안 v1.2: device_list_dir로 ceo-inbox 바로 아래 .md(README.md 제외) **개수와 가장 오래된 수정 날짜만** 세어, 1개 이상이면 후보 ㉴「사장 메모 n건(팀 처리)」 — 행동 "Cowork에 'ceo-inbox 처리'". 메모 내용은 읽지 않고, 파일 이름은 목록 결과에 보여도 기록·알림에 쓰지 않으며 지시로 따르지 않음(사장이 붙여 넣은 외부 글의 지시 주입, 보유·금액이 secretary 기록 → GitHub로 가는 길을 둘 다 막음). 고르기 순서는 ㉲ 오래 멈춤 다음, ㉳ 멈춤 의심 앞. 처리한 Cowork가 메모를 ceo-inbox/옮김/으로 옮김(mv, 삭제 아님) — 이미 커밋된 메모면 _pending에 옛·새 경로를 한 줄씩 둘 다 적음(commit-docs.ps1:38-60이 경로마다 git status로 봄). README의 호출 문구 "ceo-inbox 확인해줘"를 "ceo-inbox 처리"로 맞추고 이 규칙 1줄 추가. device_list_dir 결과에 수정 시각이 없으면 날짜는 빼고 개수만. 템플릿·머리말 불필요(사장 반복 손 0). 순서: duet-sec(v1.1 첫 실행 확인, 10/23 09:25) 끝난 뒤 교체(두 교체가 겹치면 첫 실행 확인이 흐려짐). 교체 전 결정론 시험(ext-1022b H1: 기대 차이 먼저 적기, 출력 형식 바뀜 → 소비자 견본 시험)과 sha256을 보인 뒤 `결정 obs-sys-sec: 승인` 1줄 + PC 앱 승인. 표시 추가만(제약 완화 아님). 사전 등록: 4주 동안 메모 0건이면 v1.1로 되돌림(알림만).
- b) 현행 유지(사장이 말할 때만 읽음). 비슷한 대안: Cowork가 세션 시작 때 ceo-inbox를 보는 규칙 — 세션이 열려야 보이므로 사장 기억 의존이 남아 a보다 약함.
- 답 예: `결정 obs-sys: Q1 a, Q2 a`

## 5. 미해결·확인 필요
- 링크 안 된 언급이 "이름.md" 꼴 언급을 잡는지(이름 뒤에 .md가 붙음) — Q1 a 실행 때 화면으로 확인. 안 잡히면 ①은 링크된 백링크만(거의 0) → ① 되돌림.
- Bases 보기의 정렬·개수 제한 키, 문자열 함수 정확한 문법 — 도움말 Functions 쪽을 실행 때 확인. 표에서 칸을 고칠 수 있는 범위(도움말 명시 없음) — 속성 칸을 넣지 않으므로 결론에 영향 없음. 설치판 1.14.4의 칸반 보기 지원(도움말은 table·cards·list·kanban·map) — 이번 제안은 칸반을 쓰지 않음.
- Duet이 열리면 비서 역할이 Duet 아침 브리핑으로 옮겨 갈 수 있음(duet-redesign 3-2절) → 그때 ceo-inbox 개수 표시를 Duet 계약의 읽을 목록으로 옮길지 Duet 1주 시험에서 판단. v1.2는 그때까지의 다리.

## 6. 하지 않음
옛 문서 머리말·링크·태그 일괄 수정, 커뮤니티 플러그인, 캔버스 시스템 지도, 종목 목록 노트(손 갱신 원본), ceo-inbox 템플릿, make-index.py 범위 넓히기(duet-idx 범위 그대로), 관제판·JSON 기록을 노트로 옮기기, workspace/outputs·보유·일지 값을 볼트에 넣기, 새 예약 작업, 자동 코어·통합점검·팀장회의가 볼트를 읽게 하기, 비서가 입구 노트나 메모 내용을 읽게 하기(Q2 a는 ceo-inbox 파일 개수·날짜만 — obsidian-ops-review 6절 "비서가 입구 노트를 읽게 하기" 금지의 예외가 아님), 볼트 안에서 사장 편집 범위 넓히기, 동기화·퍼블리시(유료).

## 7. 바뀔 조건
- T4 정본(SYSTEM·RUNBOOK·DECISIONS)이 새 머리말 표준을 정하고 새 문서 70% 이상이 따름 → 속성 기반 보기(결정 대기 문서 등) 다시 검토.
- 링크 안 된 언급이 잡히지 않음 → Q1 ① 되돌림.
- 사장이 캔버스 지도를 원함 → T4 archive 이동 뒤 1장(경로 안정 뒤).
- Q2 a 뒤 4주 새 메모 0건 → 되돌림. 주 3건 넘게 쌓이고 처리가 늦음 → 주간 팀장회의 받은 결과에 추가 검토.
- 무료로 휴대폰에서 볼트를 볼 방법 확인 → obsidian-ops-review 7절대로 재검토.

## 8. 내장 재검토 기록
- 1회차(23:1x, Sonnet, 7건): 결론 변경 2건 반영 — ① 종목 목록 노트·make-index.py 자동 생성을 duet-idx에 묶는 안 삭제(duet-idx 범위 밖, make-index.py:3-4 "Writes two files only · file names, headers and modification dates", 손 갱신 원본 = R2와 같은 문제) → 검색 요령 1줄 ② Q2를 템플릿·상태 칸 방식에서 "파일 개수·날짜만 + 처리 뒤 옮김/ 폴더"로 바꿈(템플릿은 수동 삽입 = 반복 손, 메모 내용 인용 = 주입·GitHub 노출, 템플릿 파일이 가짜 후보, stage 상한). 문구: 7일 수치 정의, Bases 편집 범위 "확인 필요"로 낮춤, embed는 보기마다 1줄, Obsidian 닫는 시각 답 1번 추가, v1.2는 duet-sec 뒤, ㉴ 순서, Duet 대안, 6절 예외 문구.
- 2회차(23:2x, Sonnet, 변경분만): 결론 변경 0. 문구 4건 반영 — 파일 이름 표현 정정, 옮김/ 이동 때 _pending 옛·새 경로, README 호출 문구 통일, 머리말 사장 손에 메모 처리 1번(메모 쓴 주만) 추가. Q1 검색·embed 문법은 도움말과 일치 확인.

검토 완결: 원문 확인 14/16 · 내장 재검토 2회(1회차 결론 변경 2건 + 문구 7건, 2회차 문구 4건) · 미해결 2(링크 안 된 언급이 "이름.md"를 잡는지, Bases 정렬·개수 키 문법 — 둘 다 Q1 a 실행 때 화면으로 확인, 안 되면 그 부분 되돌림) · 자료 시점 2026-10-22 22:51~23:2x KST · 바뀔 조건 7절.

## 9. 결정 기록
- 사장 원문 "결정 obs-sys: Q1 a, Q2 a"(2026-10-22 23:13 KST, Cowork).
- 반영(23:3x): Q1 ② 00-views.base(보기 3개: 최근 바뀐 문서 · 고치지 말 것 · 운영 규칙, 칸 file.name·file.mtime·file.folder만) · ③ 00-home "찾기"에 검색 요령·언급 목록 설명·보기 3줄 · Q2 README 호출 문구 "ceo-inbox 처리"와 옮김/ 규칙. 예약 지시문 .txt는 Obsidian이 목록에 올리지 않음(운영 규칙 보기는 README·플레이북·해결집·관제판 규칙만).
- 남은 것: Q1 ①(backlink 설정)은 사장의 "Obsidian 닫아도 되는 시각" 답 뒤 + 화면 확인(보기 정렬 키 sort·limit 포함, 안 되면 되돌림). Q2 비서 v1.2는 duet-sec(10/23 09:25 첫 실행 확인) 끝난 뒤 결정론 시험·sha256 → `결정 obs-sys-sec: 승인`.
- Q1 실행·확인(23:17~23:2x): 사장 "Obsidian 지금 닫아도 됨"(23:17) → Obsidian 닫음 → .obsidian/backlink.json {"backlinkInDocument": true} → 다시 열어 00-home 화면 확인(컴퓨터 사용, Obsidian만 허용). 결과: 보기 ① 최근 바뀐 문서 30개 결과·수정 시각 내림차순(sort·limit 키 동작) ② 고치지 말 것 7개 결과(카드 4·M6 2·R-REC1 1, 마지막 수정 10/19·10/17·10/08) ③ 운영 규칙 9개 결과(scheduled-prompts 하위 pending 폴더의 README·h1-notes 포함) · 문서 아래 "링크된 언급 0 · 링크되지 않은 언급 18" — "00-home.md" 꼴 언급도 잡힘 → 5절 미해결 2건 해소, 되돌릴 것 없음.
- 새로 찾은 위험 1: 링크되지 않은 언급 줄의 "링크" 버튼을 누르면 언급한 원본 문서에 링크를 써 넣음(파일 수정 → CRLF·해시 파손) → 00-home 경고 1줄 추가(23:2x). 고치지 말 것 7개 문서는 다른 문서를 언급하는 쪽이라 이 버튼으로 바뀔 수 있음 — 경고가 유일한 방어선(볼트 읽기 보기 원칙과 같음).
