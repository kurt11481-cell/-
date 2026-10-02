# S7 키움 CLI 쪽 형식 Builder 지시문 — 종가 이력 스크립트가 kiwoomcli 원본 저장 파일을 읽게 하기 (2026-10-02, K2)

- 목적: `regular_session_close_history.py`의 `parse_page`가 kiwoomcli가 직접 저장한 원본 문서(최상위 `result_list`·`return_code`·`return_msg`)도 읽게 한다. 지금은 키움 MCP 도구가 감싼 형식(`{"result":{…}}`)만 읽는다.
- 배경: S7 병합 뒤 작업 3단계(30분봉 수집)에서 사용자가 Windows 터미널에서 kiwoomcli 출력을 파일로 저장했다(SOXX 27개). `build`가 `PAGE_SHAPE_INVALID`로 거부했다. 표본·픽스처(`soxx_30m_20260930_p1/p2.json`)는 MCP 응답을 저장한 것이라 겉껍데기 `result`가 있었다. 참조 문서 절차("kiwoomcli … 저장")와 파서가 서로 다른 형식을 가정한 것이다.
- 사용자 결정(2026-10-02): 스크립트 수정 K2. 저장 파일을 변환하지 않는다(증거 = kiwoomcli 원본 바이트).
- 성격: K2(검증기 입력 계약). 검사 조건은 약하게 하지 않는다. 별도 Judge 없음(K2 = Builder + 대상 테스트). Cowork가 diff·테스트·실데이터 build로 확인한다. 정책·상태 파일 무변경. `order_authority=false`, `quantity_authority=none`, `execution_quantity=null` 유지.
- 상태: 작성 완료, Builder 미실행.

## 1. 사용자 조작 (Windows 터미널)

**[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: medium · 세션: 새 worktree `s7-cli-page` · 이유: 함수 1개와 테스트만 고치는 작은 K2, 설계 확정**

1. 새 Windows 터미널에서 입력: `cd "E:\사업\##금동한\코덱스저장소"`
2. 이 지시문을 커밋한다(worktree는 커밋된 HEAD에서 만들어진다).
   `git add docs/claude/s7-cli-page-shape-builder-prompt-2026-10-02.md`
   `git commit -m "docs: S7 CLI page shape builder prompt"`
3. `claude --worktree s7-cli-page`
4. 세션 안에서 `/model`로 Sonnet, `/effort`로 medium을 고른다.
5. 아래 한 줄을 붙여 넣는다.
   `docs/claude/s7-cli-page-shape-builder-prompt-2026-10-02.md 3절 상자 안의 지시를 그대로 따르는 Builder로 일해라. 그 밖의 절은 참고만 한다.`
6. 권한 확인 창
   - 허용: 파일 읽기, `git status`/`log`/`diff`/`show`, python 테스트·해시 계산, worktree 안 파일 쓰기.
   - 거부: 키움 도구 전부, `.env` 읽기, worktree 밖 파일 쓰기, `reconcile_broker_state.py apply`, `portfolio_review_journal.py apply`, 커밋·push·merge.
7. 끝나면 Cowork에 "Builder 완료, worktree s7-cli-page, 새 실패 수 N"만 보낸다.

## 2. Cowork 사전 확인 (2026-10-02, 원본 폴더 읽기 전용)

| # | 사실 | 근거 |
|---|---|---|
| C1 | kiwoomcli 원본 문서: 최상위 키 `result_list`, `return_code`(정수 0), `return_msg` 3개. compact JSON 한 줄 + 끝 CRLF, UTF-8(BOM 없음, `PYTHONIOENCODING=utf-8`). 행 키 9개 순서는 `ROW_KEYS`와 같고, 쪽 끝 표시 `"1f"`는 99·199·299번째 행 | `workspace/outputs/regular-session-closes/pages/SOXX/*.json` 27개(git 제외) |
| C2 | MCP 형태(기존 표본·픽스처): `{"result": {"result_list", "return_code", "return_msg"}}` | `tests/fixtures/regular-session-closes/SOXX/` |
| C3 | 현재 파서는 `document.get("result")`가 없으면 `PAGE_SHAPE_INVALID`. 실측: 원본 폴더로 build → `{"status": "FAIL", "error": "PAGE_SHAPE_INVALID:soxx_30m_20260402_p3.json"}` | `regular_session_close_history.py:152-187` |
| C4 | 같은 27개에 겉껍데기만 씌운 사본(VM 임시 폴더, 원본 무변경)으로 build: OK, 127세션(2026-04-01~2026-10-01), CONTIGUOUS, 달력 ACTIVE, 미확인 0, 9/30 종가 568.2000(표본 15:30 봉과 같음). 겉껍데기 외 차이는 없다 | Cowork 시험 실행 |
| C5 | 수집: `--pages 0`은 HTTP 429(`유량=5, API ID=usa06011`)로 실패해 0바이트. 그래서 3쪽(300봉)씩, 7일 간격으로 나눠 받았다(`workspace/outputs/regular-session-closes/collect_30m.ps1`, git 제외, 요청 사이 3초). 각 파일의 최신 봉은 더 새 파일에 들어 있고, 겹치는 봉 값 충돌은 0 | 같은 폴더 |
| C6 | `regular_session_close_history.py`·`test_regular_session_close_history.py`는 CRLF·ASCII, `references/portfolio-exposure-review.md`는 CRLF·UTF-8 | `file` |

## 3. Builder 지시 (이 상자만 따른다)

```
역할: 투자_V2 Builder (K2). 범위 = regular_session_close_history.py의 parse_page가 kiwoomcli 원본 문서 형태도 받게 하기.
주문·수량 권한 없음. 키움 도구 호출 금지. 비밀(.env*, 토큰, 계좌번호) 읽기 금지.

바꿔도 되는 파일(이것만):
- manage-us-stock-strategy/scripts/regular_session_close_history.py (parse_page와 관련 주석만)
- manage-us-stock-strategy/tests/test_regular_session_close_history.py (새 테스트 추가만, 기존 단언 변경 금지)
- manage-us-stock-strategy/references/portfolio-exposure-review.md ("Routine" 1번 문단만, K0)
- 새 파일 docs/claude/s7-cli-page-shape-builder-report-2026-10-02.md (보고)
그 밖은 고치지 않는다. 특히 run_portfolio_exposure_review.py, 스키마, 픽스처 파일, workspace/policies/*,
alert_policy.json, 상태·원장·journal, 고정 파일 22개. 목록 밖을 바꿔야 하면 멈추고 묻는다.

요구:
R1 받는 문서 형태 두 가지만:
   (a) MCP 형태: 지금과 같다(최상위 "result"가 object).
   (b) CLI 원본 형태: 최상위 object에 "result" 키가 없고 "result_list" 키가 있으면 그 object 자체를 body로 쓴다.
   최상위에 "result"와 "result_list"가 함께 있거나, 최상위가 object가 아니면 PAGE_SHAPE_INVALID.
R2 body 검사는 두 형태에 똑같이: result_list는 비어 있지 않은 list, return_code == 0, 행 검사 전부 그대로.
R3 page sha256은 지금처럼 파일 원시 바이트. 이력 파일 구조·스키마·출력 키는 바꾸지 않는다(형태 표시 필드 추가 없음).
R4 다른 동작(폴더 이름 = 종목, 파일별 최신 봉 무시, 충돌·중복 거부, 달력 권한)은 그대로.
R5 줄바꿈: 각 파일의 기존 CRLF 유지, BOM 없음. 일괄 변환 금지.
R6 문서(K0): Routine 1번에 다음만 더한다 — kiwoomcli 표준 출력을 그대로 파일로 저장한다(UTF-8; Windows에서는
   PYTHONIOENCODING=utf-8 후 cmd 리다이렉트). MCP 응답 저장 형태도 읽는다. --pages 0은 HTTP 429로 실패할 수 있어
   한 번에 3쪽 이하로 나눠 받고 요청 사이를 쉰다. 나눠 받은 파일들은 받은 범위가 서로 겹쳐야 한다(각 파일의 최신 봉은 버려진다).

단계:
0. 기준선: git status, HEAD(이 지시문 커밋이어야 함, 아니면 멈춤), 바꿀 파일 3개의 원시 sha256 기록.
   전체 테스트를 서브에이전트로 1회(실패·오류 ID만 파일로 저장):
   python -m unittest discover -s manage-us-stock-strategy/tests
1. 테스트 먼저(test_regular_session_close_history.py에 추가). 새 데이터 파일은 만들지 않고, 기존 SOXX 픽스처에서
   document["result"]만 compact JSON + 끝 "\r\n"으로 다시 쓴 CLI 형태 파일을 임시 폴더에 만든다.
   U1 CLI 형태 두 파일 → build 결과 sessions(날짜·종가·bar_cntr_tm)가 MCP 형태 픽스처 결과와 같고, page sha256은 각 파일 원시 바이트
   U2 CLI 형태 + return_code 0 아님 → PAGE_RETURN_CODE_NOT_ZERO / result_list 빈 list → PAGE_SHAPE_INVALID
   U3 최상위에 "result"와 "result_list"가 함께 있음, 최상위가 list → PAGE_SHAPE_INVALID
   U4 CLI 형태에서도 행 검사 거부가 같다(쪽 끝 외 위치의 "1f", 행 키 순서 중 대표 1~2개)
   U5 한 폴더에 MCP·CLI 형태가 섞여도 겹치는 봉 값이 같으면 통과, 다르면 PAGE_ROWS_CONFLICT
   고치기 전 코드에서 실패 수를 보고에 적는다.
2. 구현 → 대상 테스트(각각 -p로): test_regular_session_close_history.py, test_s7_calendar_binding.py,
   test_run_portfolio_exposure_review.py, test_portfolio_exposure_judge_fixes.py
3. 전체 테스트를 서브에이전트로 1회 → 0단계 목록과 비교해 "새 실패"만 보고(목표 0).
4. 보고 파일: 바꾼 파일과 diff --stat, 파일별 원시 sha256 전후, 줄바꿈 확인, 테스트 결과, 남은 문제.
   커밋하지 않는다(Cowork 확인과 사용자 승인 뒤).
```

## 4. 이번 범위 밖 (기록만)

- 수집 스크립트 `collect_30m.ps1`은 repo 코드로 넣지 않는다. P4-1 결정(repo 스크립트는 검증·정규화만)과 X6(`kiwoom-readonly-policy.json` 허용 목록에 `usa06011` 없음) 때문이다. git 제외 폴더의 Cowork 도구로 둔다.
- 매 세션 루틴(S7 보고 5.4-9)의 수집 방법 정리는 3단계를 마칠 때 한다.
- `incoming/soxx_30m_20261001_all.json`(429 실패로 생긴 0바이트 파일, git 제외)은 쓰지 않는다.

## 5. 병합 뒤 Cowork 할 일

1. 원본 폴더에서 4종목(SOXX·SOXL·MVLL·NBIS) `build` → `history/<SYMBOL>.close-history.json` 4개 → `verify`.
2. `run_portfolio_exposure_review.py` 기본 실행 → `CLOSE_MISSING`이 사라졌는지와 남은 `NOT_READY` 사유를 확인한다.
3. S7 보고 5.4-3과 이 문서 진행 기록을 갱신한다.

## 6. 진행 기록

- 2026-10-02 Cowork: SOXX `--pages 0` 수집이 429로 실패 → 나눠 받기(3쪽·7일 간격) 27개 성공 → build `PAGE_SHAPE_INVALID` 발견 → 사용자 선택 "스크립트 수정 K2" → 이 지시문 작성.
- 2026-10-02 Cowork: SOXL(NYSE)·MVLL·NBIS(NASDAQ)도 같은 방식으로 27개씩 수집. 4종목 모두 4/1~10/1 127세션, 모든 세션에 15:30 봉 있음, 겹치는 봉 충돌 0, 빈 파일 0. 겉껍데기 사본 시험 build 4종목 OK(CONTIGUOUS, 달력 ACTIVE, 미확인 0). 교차 확인: MVLL 9/30 15:30 봉 종가 35.83 = MVLL 카드 기록 값. 실제 이력 파일은 아직 만들지 않았다(병합 뒤 원본 파일로 build).
- 2026-10-02 Builder 완료(worktree `s7-cli-page`, 새 실패 0). Cowork 확인: 변경은 허용 3개 + 보고 1개, `parse_page` 6줄(두 형식, 둘 다 있으면 거부), CRLF 유지, 대상 테스트 4개 VM 통과, worktree 코드로 실제 원본 쪽 파일 4종목 build 성공(종가가 겉껍데기 사본 시험값과 전부 같음). 사용자 커밋 `855d6cb`, 병합 `09a6298`.
- 2026-10-02 병합 뒤 Cowork(원본 폴더): `history/{SOXX,SOXL,MVLL,NBIS}.close-history.json` 생성(각 127세션, 2026-04-01~10-01, CONTIGUOUS, 달력 ACTIVE, `verify` OK). 노출 점검 기본 실행(결과는 VM 임시 폴더): 종가 이력 4개 OK·`reproduced_from_pages`, `calendar_authority` LOADED, `non_default_inputs` 비어 있음, `CLOSE_MISSING` 없음. 상태·정책·통합 권한 해시 실행 전후 같음.
- 새 막힘: 적용 시작 후보 `NOT_READY`, 사유 `V_UNAVAILABLE:SPLIT_GUARD:MVLL:2026-06-26`. MVLL 원시 종가 6/25 155.95 → 6/26 46.33(비율 0.297). 키움 수정주가 주봉(`usa06012` 계열 `stock-weekly`, adjusted=1, 조회 전용)에서 6/22 주에 `upd_stkpc_tp=3231`, `upd_rt=-66.667` → 3:1 분할로 보인다(공식 발행사 공지는 확인 필요). 현재 코드에는 분할을 "검토 완료"로 처리하는 경로가 없어서, 6/26이 V 창(최대 252세션)에 남는 동안 V는 계속 계산 불가다. 다음: 분할 처리 방식 결정(별도 작업).
- 그 밖의 다른 사유: `S5_NOT_ACTIVATED`, `JOURNAL_MISSING`(적용 시작 기록 전이라 예상된 것).
- 2026-10-02 Cowork: MVLL 분할은 공식 3:1 정분할로 확인했다(GraniteShares 6/12 보도자료·설명서 보충, 키움 수정 표시 `upd_rt -66.667`, MRVL 대조). 사용자 A안 선택 → `s7-split-adjustment-builder-prompt-2026-10-02.md`.
