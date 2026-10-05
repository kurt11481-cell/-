# e-filing-feed K2 Builder 보고 — SEC 섀도 수집기 감시 명단 교체 (2026-10-05)

- 등급 K2. 지시문: `docs/claude/e-filing-feed-k2-builder-prompt-2026-10-05.md`. 브랜치 `worktree-sec-watchlist`, 커밋·푸시 안 함.
- Kiwoom acceptance pin 재확인: `kiwoom-acceptance-pin-scope.json`에 sec 관련 파일(수집기·규칙·스키마·로케일·ps1) 없음 → K3 아님.
- 주문·정책·상태·journal·작업 스케줄러·`SEC_USER_AGENT`·sec.gov 접속: 모두 건드리지 않음(테스트는 합성 fixture만).

## 바뀐 파일 (git diff --stat, +239 / -43)

| 파일 | 변경 |
|---|---|
| `assets/sec-official-event-intake-rules-v0.1.json` | `corporate_watchlist`=MRVL,NBIS,MU,BE,DELL,PWR,LITE / `holdings` 유지 / `challengers`→`watch`(MU,BE,DELL,PWR,LITE) / PGR·JPM·CME·V의 `root_theses` 삭제 |
| `schemas/sec-official-normalized-events.schema.json` | `portfolio_relevance` enum에 `WATCHLIST` 추가(옛 산출물 호환 위해 `CHALLENGER`도 유지) |
| `scripts/sec_official_event_intake.py` | 명단 검증 함수, `route_materiality`, 대시보드 명단 하드코딩 제거, `run_pipeline` |
| `scripts/sec_scheduled_shadow.py` | `canonical_watchlist()`가 같은 검증 함수 사용 |
| `scripts/run_sec_scheduled_shadow.ps1` | 80행 하드코딩 → 규칙 파일에서 읽는 `Get-CanonicalWatchlist` |
| `tests/test_sec_official_event_intake.py` | 명단 기대값 갱신 + 신규 테스트 9개 |
| `tests/test_sec_scheduled_shadow.py` | 명단 기대값 갱신 + 신규 테스트 2개 |
| `tests/fixtures/sec/company_tickers_exchange.synthetic.json` | MU·BE·DELL·PWR·LITE 합성 행 추가(CIK 9000001~9000005, 이름에 `SYNTHETIC FIXTURE` 표시; 실제 CIK 아님) |

CRLF 유지 확인(`file`): py·ps1·테스트 CRLF 그대로, JSON·fixture는 원래 LF 그대로.

## 동작 변경 요약

1. **`route_materiality`**: 보유(MRVL·NBIS) 경로는 그대로. watch 종목은 `portfolio_relevance="WATCHLIST"`, `decision_impact="WATCH"`(ASSET_REVIEW_REQUIRED 아님). `high_candidate_event_types`(정기보고·shelf·prospectus·6-K·13D/G)와 `material_8k_items`가 있는 8-K는 materiality HIGH, 나머지는 MEDIUM. 8-K 행정 항목(5.07·9.01)만 있는 경우는 지시문에 규정이 없어 옛 challenger와 같게 MEDIUM으로 둠.
2. **키 이름**: `challengers`→`watch`로 바꿈. 이 규칙 파일을 읽는 코드는 intake·shadow뿐이고 `challengers` 키를 읽지 않아 안전. `save_daily_pipeline.py`는 자체 규칙 파일(`save-daily-rules`)을 쓰므로 범위 밖.
3. **하드코딩 제거**: 마크다운 대시보드(PGR/JPM/CME/V 줄·MRVL/NBIS 줄), HTML 요약 6종목 튜플, ps1 비교 문자열 → 규칙 파일 명단. 렌더러는 선택 인자 `rules`를 받고, 없으면 기본 규칙 파일을 읽음(`sec_scheduled_shadow.py`의 호출은 시그니처 변경 없이 동작).
4. **명단 계약 보강(지시문에 없던 부수 변경, 확인 필요)**: 아래 "자기 점검" 때문에 `validated_watchlist_groups()`를 추가함.
5. **`is_routine_prospectus_watch`**: 기존엔 `CHALLENGER`만 "루틴 prospectus 묶음"으로 집계. 이름이 `WATCHLIST`로 바뀌면 집계가 조용히 꺼져 watch 종목 424B가 HIGH 목록으로 쏟아지므로 `WATCHLIST`와 옛 `CHALLENGER`를 둘 다 집계하도록 함(옛 산출물 회귀 `test_19`도 보호).
6. "Direct challenger" 영문 사유 문구 → "Direct watchlist"(표시용).

## 테스트 결과

| 대상 | 전 | 후 |
|---|---|---|
| `test_sec_official_event_intake` | 41개 OK | 50개 OK |
| `test_sec_scheduled_shadow` | 37개, 실패 5(01·05·23·35·37), skip 1 | 39개, 실패 5(**동일 id 01·05·23·35·37**), skip 1 |

- 알려진 기존 실패 5건은 상태 변화 없음(원인도 동일: `Join-Path` 빈 `$PSScriptRoot` 3건, `SEC_ACCESS_BLOCKED` 종료 코드 1≠7 2건).
- 스키마 감사 `validate_schema_contracts.py`: **PASS**, errors 없음.
- 전체 스위트(서브에이전트): 2434개, FAIL 23·ERROR 283. 대부분 gitignored 산출물 누락(`workspace/outputs/activation/...` 등), 활성 acceptance `45cf1888` 바인딩 불일치, `pypdf` 모듈 없음.
  - **기준선 비교**: 변경 전 HEAD를 `git archive`로 임시 폴더에 풀어 같은 스위트를 돌린 실패 id 집합과 비교 → **이번 변경으로 새로 생긴 실패 0건**(작업 폴더 306개 ⊂ HEAD 410개; HEAD 쪽이 많은 것은 archive에 gitignored 산출물이 없기 때문). 실행 개수 차이(2353 vs 2434)는 정확히 설명하지 못함 — 신규 테스트는 11개뿐이므로 확인 필요.
- ps1: AST 파싱 오류 0, `Get-CanonicalWatchlist`를 격리 실행해 확인(정상 → `MRVL,NBIS,MU,BE,DELL,PWR,LITE`, 파일 없음/빈 목록/키 없음 → `$null`). 래퍼 전체 실행 테스트는 위 기존 실패 때문에 검증 못 함.

## 새로 넣은 테스트
watch 종목 라우팅(8-K 중요/행정, shelf, Form 4), 보유 경로 불변, 미분류 종목 fail-closed, 규칙 명단=현재 대상(PGR·JPM·CME·V 제외), 명단 검증 8가지 깨진 경우, 빈 명단 파이프라인이 네트워크·출력 없이 실패, 대시보드 명단이 규칙에서 나옴, 파이프라인 산출물이 스키마 통과하고 watch 종목은 ASSET_REVIEW_REQUIRED가 아님, 옛 `CHALLENGER` 집계 유지, `canonical_watchlist` 규칙 추종·fail-closed, 옛 명단 실행이 비호환 처리.

## 남은 하드코딩 위치
- `sec_official_event_intake.py` HTML 대시보드 `<h3>MRVL -&gt; MVLL</h3>`와 `SOXL` 행(파생 관계·DEFERRED 표시용, 지시문상 유지). 로케일 `render_dashboard_markdown.43`의 SOXL 문구.
- `root_theses`: MRVL·NBIS만 있고 새 5종목은 **값을 지어내지 않고 비움**(스키마상 빈 배열 허용, 출력은 `[]`). `["UNCLASSIFIED"]`는 필수가 아니어서 쓰지 않음.
- 지시문 범위 밖이라 그대로: `save_daily_pipeline.py`, tactical radar 등의 PGR 언급.

## 확인 필요
1. 새 종목의 실제 CIK 매핑은 fixture로는 확인 불가(합성) — 재가동 첫 실행에서 `company_source_status`로 확인(검토서 6절).
2. watch 종목 prospectus·shelf가 HIGH가 되는 것은 지시문 그대로이나, 루틴 424B는 대시보드에서 집계(별도 묶음)로만 나오고 high 목록엔 안 올라옴(5번). 의도와 맞는지 Judge 확인.
3. 규칙 파일에 `watch` 키가 없거나 명단이 일치하지 않으면 이제 실행 전체가 실패함(`SEC_SOURCE_INVALID`) — 기존 규칙 파일을 손으로 고칠 때 주의.
4. 재가동(작업 스케줄러 사용 설정·`SEC_USER_AGENT`)은 이 작업에 포함하지 않음. 병합·재등록은 Judge 뒤 사용자.
5. 옛 명단(PGR 등)으로 만든 이전 산출물은 `watchlist` 불일치로 비호환 처리되어 첫 실행의 "새 공시" diff는 BASELINE/INCOMPATIBLE로 시작함(테스트로 확인).

## 자기 점검 (fail-open 점검표)
- 명단 파일을 못 읽거나 비었을 때: 파이썬 — 파일 없음은 예외로 종료, 빈 명단·`watch` 누락·미분류·중복·그룹 겹침은 `SEC_SOURCE_INVALID`로 네트워크 호출·출력 폴더 생성 전에 실패(빈 명단이 조용히 0건 PASS가 되던 기존 결함 해소, 테스트 있음). ps1 대체 경로 — 파일 못 읽음/빈 목록이면 `$null`을 돌려 "마지막 정상 결과 없음(BASELINE_ONLY)"으로 처리하고 오래된 결과를 LAST_KNOWN으로 올리지 않음.
- 대체 경로의 권한 상속: 대체 경로는 읽기 전용 요약만 만들며 order_authority=false·execution_quantity=null·automatic_order=false 그대로, 새 권한 필드 없음.
