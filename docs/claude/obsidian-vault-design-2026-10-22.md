---
id: obsidian-vault-design-2026-10-22
title: Obsidian 볼트 — 흩어진 작업 기록·산출물을 한곳에서 보기 (설계안 + 설치·연결 안내)
date: 2026-10-22
status: 대체됨 — obsidian-ops-review-2026-10-22.md(2026-10-22 16:28 새 요구 반영 수정안)
class: 표시·기록 전용. 1단계 = 볼트 폴더만(저장소·정책·상태·예약 작업 변경 없음). 2단계 = 일반 변경(개발 파이프라인 obs-sync — 새 스크립트·등록 스크립트·정적 테스트·Judge, offsite_backup.ps1 복사 원천 추가) + Windows 예약 작업 1개
authority: order_authority=false · quantity_authority=none · 키움 조회·주문 없음 · 증거 가중 0
consumers: 사장(Obsidian 열람·검색·메모). Cowork는 근거로 저장소 원문을 직접 읽고 볼트 사본은 읽지 않는다(사본 = 위치 안내). 3단계 선택 시 비서 제안 예약 작업이 20 사장 메모를 읽음
weekly_user_touch: 0 (열람은 선택). 1회성 = 결정 1줄
summary: Obsidian은 원본을 옮기지 않는 "한곳에서 읽고·찾고·잇는 창". 저장소 문서·종목 분석·외부자료 PDF는 한 방향 사본으로 넣고(정션·저장소 볼트는 버림), 무료 핵심 기능만 쓴다. 개발 칸반은 관제판 그대로, 사장 개인 목표 칸반만 Bases 칸반(1.14 무료 내장).
decision: 대체됨 — obs-1022b(obsidian-ops-review-2026-10-22.md)
---

# Obsidian 볼트 설계안 (2026-10-22)

사용자 요청(2026-10-22 15:46 KST, Cowork): "옵시디언 기능을 시스템 개발 및 운영에 적용할 아이디어 구상… 파편화된 프로젝트 작업 기록 및 산출물을 한곳에 모아 효율적으로 관리" + "설치 및 연결 안내". 15:51: 커뮤니티 글(일지·내일 업무·주간 칸반을 AI로 갱신, 작업 기록 백업으로 세션 복구) 참고. 15:54: **무료 기능만 사용**.

## 0. 결론
1. 설치·볼트 생성은 끝나 있다(1절). "연결"은 프로그램·MCP가 아니라 파일 연결: Claude는 볼트를 평범한 폴더로 읽고 쓴다(Desktop Commander로 이미 닿음 — 폴더 허용 불필요).
2. Obsidian = 원본을 옮기지 않는 열람·검색·연결 창. 원본: 작업 기록 = 저장소 docs/claude, 현황·개발 칸반 = 아티팩트(관제판 등), 사장 메모·개인 목표 = 볼트.
3. 저장소 문서는 한 방향 사본으로 넣는다. 정션과 "저장소를 볼트로 열기"는 버린다(3절).
4. 무료 핵심 기능만(Obsidian 라이선스 "free for all purposes"). 커뮤니티 플러그인·Sync·Publish·지도 보기(Maps 플러그인) 안 씀.
5. 권장 b: 1단계(볼트 뼈대, 오늘 Claude가 직접) + 2단계(매일 23:40 사본 갱신·일지 자동 칸·볼트 백업, 개발 파이프라인). a만 고르면 사장 메모의 PC 밖 백업이 없다.

## 1. 지금 확인한 것 (2026-10-22 15:48~16:20 KST 조회)
| 항목 | 값 | 원문 |
|---|---|---|
| 설치 | Obsidian 1.14.4.0 | C:\Program Files\Obsidian\Obsidian.exe 파일 버전 |
| 볼트 | E:\사업\##금동한\Obsidian\Obsidian 등록, open=true / 내용: .obsidian, 환영합니다!.md, 무제.base(빈 파일) | %APPDATA%\obsidian\obsidian.json · 볼트 목록 |
| 켜진 핵심 플러그인 | bases, daily-notes, templates, canvas, bookmarks, properties, graph, backlink, file-recovery, global-search 등. sync도 켜짐 | .obsidian\core-plugins.json |
| docs/claude 맨 위 폴더 | md 366(머리말 263, CRLF 93, 위키링크 3, .md 상대 링크 0) | 폴더 재집계(16시대) |
| 머리말 YAML | 머리말 263개 중 103개가 YAML 규격 오류(따옴표 없는 값 안의 ": ", 예 autocore-on-decision-2026-10-13.md:3). decision 칸 39개 중 유효 3, tickers 칸 45개 중 유효 28 | PyYAML 재집계 |
| 사본 범위 크기 | docs/claude md(하위 포함, _to_delete 제외) 423개 6.2MiB · chatgpt_종목분석결과 md+pdf 279.8MiB(pdf 131, 같은 이름 .md 캐시 있는 pdf 90) · chatgpt md_주식 md 19개 0.33MiB | 폴더 집계 |
| 옛 지침 사본 | chatgpt md_주식의 헌법 사본은 v1.2.1, claude.ai 프로젝트 같은 이름 문서에는 1.3.0 개정 문구 있음 | 프로젝트 문서 검색 |
| 기존 색인 | make-index.py → INDEX-auto.md, INDEX-outputs-auto.md | make-index.py:1-5 |
| 기존 백업 | InvestmentV2-OffsiteBackup 매일 23:50, OneDrive 날짜별 zip, 마지막 OK 2026-10-21 23:50 | offsite-bak-report.md:6-9 · workspace/outputs/backup/LATEST.json |

## 2. 원칙
- 원본 하나: 볼트 사본은 위치 안내(검토 안정성 V1 — 근거는 저장소 원문).
- 무료만: 핵심 플러그인만. sync 핵심 플러그인은 1단계에서 끈다(구독 없이는 쓰이지 않음, 무료 원칙 표시).
- Cold path: 볼트·동기화가 멈춰도 자동 코어·예약 점검은 그대로. 동기화 실패는 알림 없이 홈에만 보인다(홈의 Bases 1줄: 사본 기록 파일 file.mtime < now() - '1d' 이면 "⚠ 사본 24시간 넘음", 색 없음; a에서는 "사본 1회(as-of)"만). 볼트 백업 실패(잠김·읽기 실패)는 기존 경로 backup_recent WARN → 08:50 알림 ⑮로 보이고, 볼트 폴더가 없으면 missing에만 적힌다.
- 저장소 파일은 Obsidian이 고칠 수 없게(CRLF·바이트 해시 근거 보호, CLAUDE.md Working rules).

## 3. 검토 순서와 연결 방식
- NO_CHANGE: 기록이 저장소·PC 폴더 2곳·claude.ai(프로젝트·아티팩트)에 흩어져 사장이 한곳에서 못 찾음 → 요청 미충족.
- REMOVE/SIMPLIFY: 볼트에 원본을 하나 더 만들지 않는 것이 단순화(개발 칸반·내일 업무는 관제판이 원본).
- REUSE: 기존 백업(offsite_backup.ps1)에 볼트 노트를 원천으로 추가 · INDEX-auto.md(머리말 없는 문서 찾기) · 파일 수정 시각(머리말 오류와 무관) · 관제판.
- REPLACE: 관제판 → Obsidian 칸반 교체는 안 함(원본 하나·휴대폰 열람). Bases 칸반(1.14 무료 내장)은 사장 개인 목표에만.
- ADD(최소): 볼트 뼈대 + 사본 동기화 + 일지 자동 칸.

| 방식 | 장점 | 문제 | 판정 |
|---|---|---|---|
| A 한 방향 사본(robocopy, md·pdf만) | 한 볼트에서 검색, Obsidian이 원본을 못 고침 | 하루 1회 갱신만큼 늦음, 디스크 약 290MiB | **채택** |
| B 정션·심볼릭 링크 | 사본 없음 | Obsidian 공식 도움말 "We strongly advise against using symbolic links" · 데이터 손실·손상 위험 | 버림 |
| C 저장소(또는 docs/claude)를 볼트로 열기 | 실시간 | 저장소에 .obsidian 생김(.gitignore에 없음, 수정은 수동 경로) · 저장 때 CRLF 유지 여부 확인 필요 · 사장 메모가 GitHub push 대상 저장소와 섞임(dual-ai-review-2026-10-20.md:86,106) · 볼트가 둘로 나뉨 | 버림 |

## 4. 볼트 구조 (1단계)
```
E:\사업\##금동한\Obsidian\Obsidian\
  00 홈.md                 하나의 입구: 오늘 일지 · 아티팩트 바로가기 · Bases 표 · 사본 시각
  10 일지\YYYY-MM-DD.md     사장 칸(손으로). 2단계부터 템플릿에 ![[10 일지/자동/YYYY-MM-DD 자동]] 줄 추가
  10 일지\자동\YYYY-MM-DD 자동.md   스크립트 전용(2단계, 23:40 생성) — 사장 파일은 열지 않음(동시 편집 충돌 방지)
  20 사장 메모\             생각·아이디어·좋은 글·일기, 개인 목표(status 속성 → Bases 칸반). 첨부\ = 새 첨부 위치(기본값은 볼트 맨 위)
  30 보기\*.base            ① 최근 바뀐 문서(파일 수정 시각) ② 종목별 문서(머리말 유효한 것만) ③ 사장 메모 표·이번 주 목표 칸반
  40 지도\시스템 지도.canvas
  80 템플릿\                일지·사장 메모
  90 사본(읽기 전용)\       docs-claude\ · 종목분석결과\ · chatgpt-구판지침\ · 프로젝트문서(as-of)\
```
- 사본 대상: docs/claude md(하위 포함, _to_delete·__pycache__ 제외), chatgpt_종목분석결과 md·pdf, chatgpt md_주식 md(구판 — 현행은 claude.ai 프로젝트), claude.ai 프로젝트 문서 5개(1단계 1회, as-of 표시).
- 넣지 않음: workspace/outputs(INDEX-outputs-auto.md로 대신), .codex(인증 파일), .env*, workspace/private_inputs, 상태·정책 JSON.
- 90 사본 규칙(홈에 표시): 고친 내용은 다음 동기화에 되돌아감 · **여기 넣은 파일은 다음 동기화에 지워짐(휴지통 없음)** · 이 폴더에서 이름 바꾸기·칸반 끌기 금지.

## 5. Obsidian 기능별 적용 (무료 핵심 기능만)
| 기능 | 투자_V2 적용 | 단계 |
|---|---|---|
| 검색·빠른 열기 | md는 전부 본문 검색(개발 기록·종목 분석·사장 메모). PDF는 이름만 — 본문은 같은 이름 .md 캐시가 있는 것(약 90개)만 | 1 |
| PDF 보기 | 외부자료·SAVE 리포트 PDF를 볼트 안에서 읽기 | 1 |
| Bases 표 | ① 최근 바뀐 문서(세션 재개 입구) ② 종목별 문서(tickers 유효 28/45 — 나머지는 검색) ③ 사장 메모. 결정 기록은 머리말 오류가 많아(decision 유효 3/39) Bases 대신 검색 `decision:`(INDEX-auto.md에는 decision 칸이 없음 — 상태·요약만). 후보: make-index.py에 decision 칸 1개 추가(줄 단위 읽기라 YAML 오류와 무관) | 1 |
| Bases 칸반(1.14) | 사장 개인 "이번 주 목표"(20 사장 메모 status). 개발 작업 칸반은 관제판 | 1 |
| 홈 + 북마크 | 하나의 입구. 아티팩트(현황판·관제판·통합점검·주간 팀장회의) 링크 | 1 |
| 일일 노트 + 템플릿 | 사장 일지 + 자동 칸 끼워 넣기(그날 바뀐 docs/claude 문서·자동 코어 결과 파일 목록) | 1(템플릿) · 2(자동 칸) |
| 캔버스 | 시스템 지도(06:40 통합점검 → 자동 코어 → 주문표 → 일지, 회사 조직) | 1 |
| 그래프·백링크 | 문서 사이 위키링크가 3개뿐이라 지금 효과 작음. 홈·일지가 연결을 만들어 줌 | 1 |
| 파일 복구 | 사장 메모 실수 되돌리기 | 1 |

## 6. 참고 글의 사용법 → 투자_V2 대응
| 글의 사용법 | 여기서 하는 방식 |
|---|---|
| "오늘 일지 정리해줘" | 2단계 스크립트가 매일 23:40 자동 칸을 씀(LLM 없음, 명령 불필요). Cowork에 "오늘 일지 정리"라고 해도 됨 |
| "내일 업무 정리해줘" | 재개 조건의 원본은 관제판 → 일지에 링크만 |
| "이번주 목표 칸반" | 개발 = 관제판·주간 팀장회의 대시보드 / 사장 개인 목표 = Bases 칸반 |
| 작업 기록 백업 → 세션 복구 | 이미 docs/claude 인계 문서 + 메모리. 볼트의 "최근 바뀐 문서"가 사장용 재개 입구 |
| 다 넣기(일지·생각·좋은 글) | 20 사장 메모(볼트가 원본, GitHub에 안 올라감) |
| Anki | 투자_V2 범위 밖 |

## 7. 단계 · 바뀌는 것 · 사장 손
| 단계 | 내용 | 바뀌는 것 | 사장 손 |
|---|---|---|---|
| 1 (결정 즉시, Claude가 Desktop Commander로) | 폴더 뼈대·홈·템플릿·Bases 3·캔버스 1·사본 1회·프로젝트 문서 5 사본 · 설정: Obsidian 닫기 → 새 탭 읽기 보기, 일일 노트 폴더·템플릿, 새 첨부 위치 = 20 사장 메모\첨부, 내부 링크 자동 갱신 끔, sync 끔 → 다시 열기(사장이 편집 중이 아닐 때) | 볼트 폴더만 | 결정 1줄 |
| 2 (b일 때) | 개발 파이프라인 obs-sync(일반 변경): 동기화 스크립트(원천별 /MIR, 대상이 "90 사본\<원천>" 아래인지 검사, 종료 코드 8 이상 실패, /XO 금지, 한글 경로는 인자) + 일지 자동 칸 + 등록 스크립트(매일 23:40 — DocsCommit 23:30 뒤·OffsiteBackup 23:50 앞, conhost --headless 숨김 실행) + 정적 테스트 + Judge + offsite_backup.ps1 복사 원천에 볼트(맨 위 *.md + 10·20·30·40·80, .obsidian·90 제외) 추가 — 볼트 경로는 저장소 기준 ASCII 상대 경로 `..\Obsidian\Obsidian`(스크립트 ASCII 전용·설정 파일 읽기 금지 테스트, test_offsite_backup_static.py:45; 인자 추가 방식이면 OffsiteBackup 재등록이 들어가 Windows 작업 2개). 큐 전에 활성 개발 작업 수(≤3) 확인. 지시문에 offsite-bak-builder-prompt.md:56의 P7(주문 표지 글자) 주의를 넣음 — NEEDS_APPROVAL이면 dc-dev 절차대로 사장 결정 요청(손 1). READY_TO_MERGE면 Cowork가 병합(dc-dev Q1 a) → robocopy /L(목록만)로 삭제 대상이 "90 사본\<원천>" 안에만 있는지 1회 확인 → 등록 스크립트 -PlanOnly 확인 뒤 등록(이 결정 문구가 승인). 병합 때 연결 지도 1줄·관제판 schedules·library 포인터 | 저장소 스크립트·테스트, Windows 작업 1 | 0 |
| 3 (선택, 나중) | 비서 제안 작업이 20 사장 메모 읽기(지시문 교체 승인) · 새 문서 related 위키링크 · 휴대폰 열람(무료 방법만, 확인 필요) | 지시문 교체 등 | 승인 1줄 |

## 8. 안전·제약 대조
- 주문·키움·정책·상태·권한 무관. 저장소는 읽기만(사본 복사는 원본 쪽에 쓰지 않음, /MIR 삭제는 "90 사본\<원천>" 안에서만).
- 사본은 바이트 그대로(CRLF 변환 없음). 사본을 고치거나 이름을 바꿔도 저장소 원본은 안 바뀜. 볼트 노트 링크 보호를 위해 내부 링크 자동 갱신은 끔.
- 2단계는 일반 변경(새 Windows 작업·스크립트 선례 offsite-bak·c1-host-status와 같은 경로, claude-setup-tips-review-2026-10-22.md:59). 권한 변경 아님.
- 기본 처분: 2026-10-29까지 답이 없으면 c(NO_CHANGE) — 볼트는 지금 상태 그대로, 알림만.

## 9. 설치·연결 안내 (한 단계씩)
- 설치: 끝남(1.14.4). 볼트 생성: 끝남. 추가 설치 없음.
- Claude ↔ 볼트: 파일로 연결(이미 닿음).
- 저장소 ↔ 볼트: 한 방향 사본(1단계 1회, 2단계 매일).
- 사장이 할 일: ① 결정 1줄 ② (1단계 뒤) Obsidian 왼쪽 "00 홈" 클릭.

## 10. 결정 요청 obs-1022 (기한 2026-10-29, 무응답 = c)
- a) 1단계만(사장 메모 PC 밖 백업 없음, 사본은 1회 as-of) · **b) 1+2단계(권장 — 병합 뒤 Cowork가 Windows 작업 1개를 -PlanOnly로 확인하고 등록, 이 답이 그 승인)** · c) 안 함
- 관제판 결정함에 obs-1022(deadline 2026-10-29, default c)로 올려 둠 — 기한이 지나면 다음 관제판 갱신 세션이 c를 기록(dev-dashboard-protocol.md:41).
- 답 예: `결정 obs-1022: b`

## 11. 바뀔 조건
- Obsidian이 저장 때 CRLF를 유지하고 폴더 정션을 공식 지원한다고 확인 → 3절 B·C 재검토(사본 없앨 수 있음).
- 사장이 볼트를 쓰지 않는다고 말함 → 2단계 작업 끄기 제안.
- Obsidian이 머리말 YAML 오류 문서도 속성으로 보여 줌(1단계 뒤 화면 확인) → 결정 기록 Bases 표 추가.
- 휴대폰에서 볼트 열람 요구 → 무료 동기화 방법 따로 검토.

## 12. 내장 재검토 기록
- 1회차(2026-10-22 16시, 3-1 지시문, 17건): 결론을 바꾼 것 4건 — ① 2단계 변경 경로(플레이북·"저장소 코드 아님" → 일반 변경 개발 파이프라인, 선례 offsite-bak-builder-prompt.md:5, setup-tips:59) ② 볼트 백업 새로 만들기 → 기존 offsite_backup.ps1 원천 추가, a의 백업 공백 명시 ③ "무료 칸반 없음" 오류 → Bases 칸반 1.14 내장(obsidian.md/help/bases/views), 지도는 Maps 플러그인이라 뺌 ④ Bases 결정·종목 표 → 머리말 YAML 오류(103/263, decision 유효 3/39, tickers 28/45 — 본 세션 PyYAML 재집계)로 결정 표 뺌. 문구 반영 13건: /MIR 위험·링크 자동 갱신 끔, 매시 → 매일 23:40 숨김 실행(register-dev-tasks.ps1:10-11), 폴더 허용 삭제(DC로 닿음), 연결 규칙·소비자 문구, 실패 표시, 일지 자동 칸 별도 파일, PDF 본문 검색 안 됨(obsidian.md/help/plugins/search), 구판 지침 표시·프로젝트 문서 사본, 기한, 심볼릭 링크 인용 범위(파일 링크 항목이라 삭제), 수치 범위, 바뀔 조건 측정, 설정 쓰기 순서.
- 2회차(2026-10-22 16시대, 반영분만, 11건): 결론을 바꾼 것 0건. 문구 반영 11건 — 볼트 경로를 ASCII 상대 경로로(인자 추가 시 작업 2개) · 백업 실패는 기존 08:50 알림 경로로 보임 · 볼트 맨 위 *.md·첨부 위치 · P7 주의와 NEEDS_APPROVAL 시 손 1 · 등록 승인 범위를 b 문구에 명시 · robocopy /L 1회 확인 · 24시간 경고를 Bases 수식으로(색 없음) · 자동 일지 파일 이름 분리 · INDEX-auto에 decision 칸 없음(후보: make-index.py 칸 추가) · 맨 위 폴더 수치 재집계 · 관제판 결정함 등록.
