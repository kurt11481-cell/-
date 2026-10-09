# 공식 공시 자동 수집 경로 검토 (관제판 e-filing-feed, 2026-10-05)

- 등급: K0 (읽기 전용 검토). 설치·코드·정책·예약 작업 변경 없음. order_authority=false.
- 출발점: `future-tools-roadmap-2026-10-05.md` §7-2(공시 피드 우선순위 상향), `external-repos-review-2026-10-05.md` §3 A3, `official-source-alt-paths-2026-10-04.md`.
- 방법: WebSearch/WebFetch로 SEC·IR 경로 확인(우회 접근 없음), 저장소 읽기(grep·기존 산출물 manifest).

## 결론

**새로 만들 필요 없음 — 이미 있는 SEC 공시 수집기(REUSE)를 되살리는 안을 권장.**
저장소에 `sec_official_event_intake.py` + `sec_scheduled_shadow.py`(읽기 전용 SEC 섀도, v0.1)가 있고, 사용자 PC의 Windows 작업 스케줄러로 **2026-08-30 ~ 2026-09-26 하루 2회 돌았던 기록**(25일치, 실행 39회, manifest 39건 모두 PASS)이 있다. 9/26 12:30 KST 실행 뒤로 멈췄다. 막힌 것은 기술이 아니라 ① 멈춘 이유 미확인 ② 관심 명단이 옛 목록(MRVL·NBIS·PGR·JPM·CME·V) ③ 통합점검이 이 산출물을 읽지 않음, 세 가지다.

판정: **조건부 채택(REUSE)** — 1단계 사용자 확인(멈춘 이유) → 2단계 K2(명단 갱신) → 3단계 K1(통합점검이 읽기). IR 보도자료 RSS는 **보류**. 현행 WebSearch→WebFetch는 **유지**(보조·대체 경로).

## 1. 경로별 확인 결과 (2026-10-05)

| 경로 | 결과 | 판정 |
|---|---|---|
| SEC 공정 접근 규칙 | 최대 10회/초, User-Agent에 회사명·연락 이메일 선언 요구, 자동화 도구는 정책 범위 안에서만 | 기존 수집기는 1회/초, `SEC_USER_AGENT` 환경변수 → 규칙 안 |
| data.sec.gov submissions(회사별 제출 목록 JSON) | WebFetch로 열림. 단 응답 잘림 + 최신 항목을 8/28로 요약(Micron은 9/30 4분기 실적 발표가 있음) | Claude WebFetch로는 피드로 못 씀(10/4 결론 재확인). 스크립트 파싱은 정상(기존 산출물) |
| sec.gov/Archives/edgar/data/{CIK}/index.json | WebFetch로 열림. 잘림, 최근 항목 7월로 보임 | WebFetch 피드로 못 씀 |
| sec.gov/Archives/edgar/daily-index | WebFetch 403 | Claude 사용 안 함 |
| sec.gov/cgi-bin/browse-edgar(회사별 Atom 피드·최신 공시 피드) | robots.txt `Disallow: /cgi-bin` | 사용 안 함(Claude·스크립트 모두) |
| efts.sec.gov 검색 | 403 (10/4) | 사용 안 함 |
| 문서 URL 직접(sec.gov/Archives/edgar/data/…) | 열림 (10/4), robots `Allow: /Archives/edgar/data` | **유지** — 수치 읽기용 |
| Micron IR RSS (`/rss/news-releases.xml`, `/rss-news-feeds`) | 둘 다 404 | 보류 |
| GlobeNewswire 회사별 RSS 검색 | robots 차단 | 사용 안 함 |
| 키움 OpenAPI(해외) | 공시·뉴스 명령 없음(리서치 `usa24300`만) | 해당 없음 |

## 2. 기존 수집기 (REUSE 후보)

| 항목 | 내용 (저장소에서 확인) |
|---|---|
| 파일 | `manage-us-stock-strategy/scripts/sec_official_event_intake.py`(1,248줄), `sec_scheduled_shadow.py`(584줄), `run_sec_scheduled_shadow.ps1`, `register_sec_scheduled_shadow_task.ps1`, 계약 `assets/sec-scheduled-shadow-contract-v0.1.json`, 규칙 `assets/sec-official-event-intake-rules-v0.1.json` |
| 접속 범위 | www.sec.gov, data.sec.gov 두 곳만(`ALLOWED_HOSTS`). 요청 수를 manifest에 기록 |
| 일정(계약) | 작업 이름 `GuardedPortfolio-SEC-Shadow-v0.1`, 월~금 22:00 + 화~토 12:30 (한국 시간), 조회 기간 7일 |
| 권한 | 브로커·포트폴리오·정책·주문 경로 없음. order_authority=false, execution_quantity=null |
| 증분 | 직전 실행과 `ticker+accession_number`로 비교 → `scheduled-dashboard.json`의 `new_since_previous_count` |
| 마지막 실행 | 2026-09-26T03:30Z(12:30 KST): 요청 7회 모두 200, 6개 회사 PASS, 7일 창 377건 중 새 69건 |
| 출력 | `workspace/outputs/official-event-intake/sec/<날짜>/<run>/` (normalized-events.json, scheduled-dashboard.json/md/html, run-manifest.json) |
| 각 공시 필드 | form, filing_date, accepted_at, items_if_available(8-K 항목 번호), source_url(문서 URL), materiality |

문제점:
- 명단: 377건 중 353건이 JPM 424B2(채권 발행 설명서) — 옛 명단 탓의 잡음. 현재 대상(MVLL→MRVL, NBIS, 관심 MU·BE·DELL·PWR·LITE)과 다르다.
- SOXL은 `DEFERRED_TO_SECTOR_OR_FUND_SOURCE`(Direxion 공시는 범위 밖). S7 트리거는 계속 WebSearch.
- 테스트: `test_sec_scheduled_shadow` 5건 실패 상태(PowerShell `Join-Path` 빈 `$PSScriptRoot`, `SEC_ACCESS_BLOCKED` 종료 코드 1≠7 — `i4-r9-activation-report-2026-10-05.md`). 실행 자체와의 관계는 확인 필요.

## 3. 웹 접근 제한 규칙 판정 (수집 주체)

1. **Claude(Cowork·예약 점검)는 sec.gov를 bash·python·curl로 가져오지 않는다.** WebFetch가 거부한 곳(browse-edgar, efts, daily-index, GlobeNewswire RSS)은 어떤 방법으로도 쓰지 않는다.
2. **수집 주체 = 사용자 PC의 Windows 작업 스케줄러가 돌리는 저장소 스크립트**, 사용자가 선언한 User-Agent로 SEC가 문서화한 API(data.sec.gov submissions)만 사용. 이는 SEC가 허용한 자동 접근 방식이고, WebFetch가 막힌 곳의 우회가 아니다(data.sec.gov는 WebFetch도 거부하지 않았고 문제는 잘림이었다).
3. Claude는 **로컬 산출물 파일만 읽는다**(device_bash로 json 읽기). 공시 본문 수치는 기존처럼 source_url을 WebFetch로 열어 확인.
4. Claude가 수집기를 직접 실행·등록하지 않는다. 등록·재가동은 사용자가 Windows에서 한다(git 커밋과 같은 원칙).
5. 스크립트에도 robots 차단 경로(/cgi-bin)·RSS 검색 경로를 넣지 않는다.

## 4. 통합점검과의 관계 (중복·대체 범위)

현행 v3.9 지시문 기준 웹 호출 상한: 5) 뉴스 WebSearch 최대 8회, 실적일 점검 종목당 1회(NBIS + 관심 5 = 6회), 7) 원장 확인 최대 3회. 공식 사실은 "SEC EDGAR·IR·보도자료를 WebSearch/WebFetch로 확인".

| 일 | 피드로 대체? |
|---|---|
| 8-K(1.01 계약, 2.02 실적, 2.03 채무, 3.02 주식 발행, 7.01·8.01 보도자료 첨부)·S-3/424B(증자·ATM, N3)·Form 4/144 "새로 나왔나" 찾기 | **대체** — 로컬 파일에서 새 공시만 확인 |
| 공시 수치 읽기(계약 금액·가이던스) | 대체 안 됨 — source_url WebFetch 1회(찾기 검색은 줄어듦) |
| 8-K 없이 나오는 IR 보도자료(일부 계약·제품 발표), 실적 발표일 공지 | 대체 안 됨 — WebSearch 유지 |
| SOXL(Direxion), TSMC(해외 발행사, S2·S3·U2) | 대체 안 됨 |

- 토큰 절감: **확인 필요(실측 없음)**. 재가동 뒤 5회 실행의 WebSearch 횟수를 v3.9 기록과 비교해 정한다.
- 이익(토큰 외): 8-K·증자 공시 놓침 감소, 공시 시각(accepted_at)이 남아 "호재 뒤 하락" 기준 시각이 정확해짐. 자동 감시 단계(roadmap §7-3 ③)의 입력이 됨.

안전 규칙(fail-open 점검표 적용):
- 피드가 오래됐거나(마지막 실행 36시간 초과 — 기준값은 제안) 실패하면 "새 공시 없음"으로 보지 않는다 → "공시 피드 오래됨"을 적고 현행 WebSearch로 대체(대체 경로가 피드의 권한을 물려받지 않음).
- 피드 실패는 점검 상태 ㉠~㉥(불완전)에 넣지 않는다(Cold Path가 Core 판정을 막지 않게). 표시만.
- 피드의 공시 목록은 "새 공시가 있다"는 사실까지만. 호재·악재 판정은 문서 본문 확인 뒤 기존 기준 (a) 그대로.

## 5. 판정과 다음 단계

| 단계 | 내용 | 등급 | 누가 |
|---|---|---|---|
| 1 | 9/26 뒤 멈춘 이유 확인: Windows 작업 스케줄러에서 `GuardedPortfolio-SEC-Shadow-v0.1` 상태(사용 안 함/삭제/오류)와 `SEC_USER_AGENT` 환경변수 존재 | 확인(변경 없음) | 사용자(Cowork가 단계 안내) |
| 2 | 규칙 파일 명단을 현재 대상으로 교체(MRVL·NBIS·MU·BE·DELL·PWR·LITE, PGR·JPM·CME·V 제외), 관련 테스트 기대값 확인, 재가동 | K2 | Claude Code Builder → Judge → 사용자 병합·재등록 |
| 3 | 통합점검 v3.10: 최신 `scheduled-dashboard.json`·`normalized-events.json`을 읽어 "새 공시" 줄 표시, 신선도 규칙, 실패 시 현행 대체 | K1 | Cowork 초안 → 사용자 승인 → 예약 작업 교체 |
| 4 | 5회 실행 뒤 WebSearch 횟수·놓침 비교로 유지/수정 결정 | K0 | Cowork |

- 명단 동기화: 관심 명단(`watchlist-registry.json`)이 바뀌면 규칙 파일도 바꿔야 한다. 자동 동기화는 넣지 않고(복잡도), 3단계에서 "명단 불일치"를 표시만 한다.
- 보류: IR 보도자료 RSS(회사별 제공 여부 확인 필요, Micron은 404), daily-index.
- NO_CHANGE 대안: 지금처럼 WebSearch만 유지. 비용은 매 실행 검색과 놓침 위험.

## 6. 확인 필요

- ~~수집기가 9/26 뒤 멈춘 이유~~ → 확인됨(2026-10-05 사용자 화면): 작업 상태 "사용 안 함", 마지막 실행 2026-09-26 12:30:00 결과 0x0(정상 완료), 실행 계정 "사용자가 로그온할 때만 실행". 고장이 아니라 꺼져 있음. 누가·왜 껐는지는 기록 없음.
- 실행 환경: 수집기는 Windows 본체에서 돌았음(manifest 기록). Cowork VM의 sec.gov 접속은 시험하지 않음(필요 없음 — 3절 원칙).
- 규칙 파일 명단을 바꾸면 깨지는 테스트 범위(Builder가 확인).
- NBIS·LITE 등 새 대상의 CIK 매핑이 `company_tickers_exchange.json`에서 되는지(실행으로 확인).
- 보유·관심 종목 IR의 RSS 제공 여부(종목별).

## 출처

- https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data (10회/초, User-Agent 선언, 일일 인덱스 매일 밤 갱신)
- https://www.sec.gov/robots.txt (`Disallow: /cgi-bin`, `Allow: /Archives/edgar/data`)
- https://www.sec.gov/about/rss-feeds (회사별 피드 = cgi-bin 검색 경로)
- https://www.globenewswire.com/news-release/2026/09/30/3372366/0/en/micron-technology-inc-reports-record-fiscal-fourth-quarter-and-full-year-2026-results.html (Micron 9/30 실적 — submissions 요약 오류 판별용, 검색 결과 제목 기준)
- 저장소: 2절 파일, `workspace/outputs/official-event-intake/sec/2026-08-30`·`2026-09-26` run-manifest.json, `docs/claude/integrated-check-prompt-v3.9-draft-2026-10-05.txt` 5)·62~64행, `docs/claude/i4-r9-activation-report-2026-10-05.md`

## 진행 기록
- 2026-10-05: 검토 작성(Cowork, K0). 설치·코드·예약 작업 변경 없음. 관제판 e-filing-feed → 결정 대기.
- 2026-10-05: 1단계 확인 — 작업 스케줄러에서 "사용 안 함" 상태, 9/26 마지막 실행 정상(0x0).
- 2026-10-05: 사용자 결정 = 채택(REUSE). 끈 기억 없음. 2단계 Builder 지시문: e-filing-feed-k2-builder-prompt-2026-10-05.md. 재가동은 K2 병합 뒤.
- 2026-10-05: K2 Builder 완료(worktree-sec-watchlist, 미커밋). Cowork 확인: 변경 8파일(+239/−43), 줄바꿈 보존, pin 범위 밖, test_sec_official_event_intake 50개 OK·test_sec_scheduled_shadow 39개 OK(PowerShell 14개는 VM에서 건너뜀)·스키마 감사 PASS 재실행. 추가 변경 2건(명단 검증 fail-closed, WATCHLIST 증권신고서 묶음 집계)은 안전 방향이라 별도 Judge 없이 K2 기준으로 통과 판정. 다음: 사용자 커밋·병합 → 작업 스케줄러 사용.
- 2026-10-05: 사용자 병합(0f1d2fb) 확인, 작업 스케줄러 "사용" 전환(사용자). 첫 실행 22:00 KST — Cowork 22:15 확인 예약.
- 2026-10-05 22:16: 재가동 첫 실행(13:00Z=22:00 KST) PASS — 요청 8회 모두 200, 7종목 PASS, CIK 매핑 정상(MU 723125·BE 1664703·DELL 1571996·PWR 1050915·LITE 1633978·MRVL 1835632·NBIS 1513845), 7일 창 18건(중요 2: MU 8-K 9/30 항목 2.02·9.01, NBIS 6-K 10/1), JPM 잡음 사라짐. 비교 상태 PREVIOUS_RUN_INCOMPATIBLE(옛 명단 — 예상된 기준선). e-filing-k2 완료, e-filing-k1 재개 가능.
- 2026-10-05 23:3x: e-filing-k1 — 통합점검 v3.11 적용(번호 정정: v3.10은 '개장 전 기록 읽기'로 먼저 적용됨). 변경안 integrated-check-v3.11-change-2026-10-05.md, 사용자 결정 = 검색 유지·피드 대조만(생략은 5회 뒤 v3.12), 신선도 24시간. 저장된 지시문 31,152자 초안과 일치. 다음: 10/6 06:40 첫 실행 확인.