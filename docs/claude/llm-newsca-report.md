---
id: llm-newsca-report
title: "llm-newsca Builder 보고 — 뉴스 기사 가져오기에 ASCII 경로 CA 묶음 복사본 넘기기"
date: 2026-11-20
prompt: docs/claude/llm-newsca-builder-prompt.md
---

## (a) 바꾼 함수와 상수 (manage-us-stock-strategy/scripts/llm_pilot_news.py)
- 모듈 docstring 쓰기 범위 문장(14~18행): `workspace/outputs/llm/` 아래에 더해, 묶음 경로가 ASCII가 아닐 때 CA 묶음 복사본 1개(`CA_COPY_DIR` 아래 `CA_COPY_NAME`)를 쓴다고 적음.
- `import os`(28행). 쓰는 것은 `os.fsync`(317행)·`os.replace`(318행)뿐.
- 상수 `CA_COPY_DIR = Path("C:/ProgramData/InvestmentV2")`(72행), `CA_COPY_NAME = "certifi-cacert.pem"`(73행), 캐시 `_FETCH_STATE = {}`(75행, 키 "bundle"·"session").
- 새 함수 `_write_ca_copy(target, data)`(310행): 같은 폴더 임시 파일 `certifi-cacert.pem.tmp`에 바이트를 쓰고 → flush → `os.fsync` → `os.replace`. OSError면 임시 파일을 지우고 예외를 다시 올림.
- 새 함수 `ascii_ca_bundle(src=None, copy_dir=None)`(328행):
  - `src`가 None이면 함수 안에서 `import certifi` → `certifi.where()`. ImportError면 None.
  - 넘겨받은 경로 문자열 그대로 ASCII 판정(resolve·absolute 없음). ASCII면 None(기본 동작 유지).
  - `copy_dir`이 None이면 부를 때 모듈 전역 `CA_COPY_DIR`을 읽음. `str(copy_dir)`이 비ASCII면 None.
  - 폴더 만들기(`parents=True, exist_ok=True`) → 원본 `Path(src).read_bytes()` → 대상 바이트를 매번 읽어 대조, 없거나 다르면 `_write_ca_copy`로 다시 씀("있으면 그대로 씀" 지름길 없음).
  - 어느 단계든 OSError면 None. 성공하면 대상 경로 문자열.
- `default_fetcher(symbol)`(363행): `yfinance`는 함수 안 import(그대로). `_FETCH_STATE`에 "bundle"이 없을 때만 모듈 전역 `ascii_ca_bundle()`을 한 번 부름(None도 저장). None이면 지금처럼 `yfinance.Ticker(symbol).news`. 경로면 "session"이 없을 때만 `from curl_cffi.requests import Session` → `Session(impersonate="chrome", verify=<경로>)`를 한 번 만들고 `yfinance.Ticker(symbol, session=<세션>).news`. 세션 만들기·import 예외는 삼키지 않아 `fetch_items_detail`이 기존처럼 기록.
- 인증서 검증을 끄는 코드 없음. 환경 변수 읽기·새 네트워크 모듈 없음. 시험 계약 금지어 없음(`test_script_source_contract` 통과).

## (b) 새 시험 (manage-us-stock-strategy/tests/test_llm_pilot_news.py, 새 클래스 `CaBundleTests` 1080행)
setUp에서 임시 폴더로 `contextlib.chdir`(정리 때 되돌림)하고 상대 경로만 씀. 모든 `ascii_ca_bundle` 호출에 `copy_dir`을 넘기고, `default_fetcher` 시험은 `ascii_ca_bundle`을 가짜로 바꾸고 `_FETCH_STATE`를 `mock.patch.dict(..., clear=True)`로 비우며 가짜 `yfinance`·`curl_cffi`·`curl_cffi.requests`를 `mock.patch.dict(sys.modules, ...)`로 시험 안에서만 끼움. `C:/ProgramData`에 쓰지 않음.
- `test_ascii_ca_bundle_ascii_source_returns_none`: ASCII 원본 → None, 복사 폴더 안 생김.
- `test_ascii_ca_bundle_copies_non_ascii_source`: `src-\u00e9/cacert.pem` → 돌려준 경로 ASCII·`copy/certifi-cacert.pem`, 바이트 같음, 폴더에 임시 파일 남지 않음.
- `test_ascii_ca_bundle_skips_rewrite_when_same`: `_write_ca_copy` 감시(wraps) — 첫 호출 1회 씀, 두 번째 호출은 쓰지 않음, 결과 같음.
- `test_ascii_ca_bundle_non_ascii_copy_dir_returns_none`: 복사 폴더 `copy-\u00e9/` → None, 폴더 안 생김.
- `test_ascii_ca_bundle_oserror_returns_none`: 복사 폴더 자리에 같은 이름 파일 → None, 그 파일 그대로.
- `test_ascii_ca_bundle_missing_source_returns_none`(추가): 원본이 없음 → None, 복사본 안 생김.
- `test_ascii_ca_bundle_rewrites_tampered_copy`: 복사본을 바꿔 둔 뒤 다시 부르면 1회 다시 써 원본 바이트로 되돌아감, 임시 파일 남지 않음.
- `test_default_fetcher_uses_session_when_bundle_given`: 두 종목 호출에 `ascii_ca_bundle` 1회, `Session(impersonate="chrome", verify=<경로>)` 1회, `Ticker("MU", session=<같은 세션>)`·`Ticker("NVDA", session=<같은 세션>)`.
- `test_default_fetcher_plain_ticker_when_none`: `ascii_ca_bundle` 1회, Session 안 불림, `Ticker("MU")`·`Ticker("NVDA")`만.
- `test_default_fetcher_session_error_reaches_fetch_detail`(추가): Session이 예외 → `fetch_items_detail("MU")`가 `kind "exception"`·type·message로 기록, Ticker 안 불림.
- `test_ca_copy_constants_and_no_verify_off`(추가): 두 상수 값, 스크립트에 `verify=False`·`SSL_VERIFYPEER` 없음.
- 기존 시험은 고치거나 지우지 않음(diff는 파일 끝 `if __name__` 앞에 새 클래스 추가뿐).

## (c) 시험 결과와 diff
명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot_news*.py"`
```
Ran 72 tests in 1.018s

OK
```
`git diff --stat`
```
 manage-us-stock-strategy/scripts/llm_pilot_news.py |  76 +++++++++++-
 .../tests/test_llm_pilot_news.py                   | 131 +++++++++++++++++++++
 2 files changed, 205 insertions(+), 2 deletions(-)
```
`git diff --ignore-cr-at-eol --stat`
```
 manage-us-stock-strategy/scripts/llm_pilot_news.py |  76 +++++++++++-
 .../tests/test_llm_pilot_news.py                   | 131 +++++++++++++++++++++
 2 files changed, 205 insertions(+), 2 deletions(-)
```
두 stat이 같음 = 두 기존 파일의 CRLF 유지(편집 뒤 두 파일 모두 CR 없이 끝나는 줄 0). 이 보고 파일은 새 파일(LF)이라 위 stat에 없음.

## (d) 바뀌지 않은 것 대조
- stdout 마지막 줄(`_line`)·종료 코드(`EXIT_CODES`)·`counts`(symbols_failed·skipped·mask_leak·items)·`REASON_KO`·fetch-errors.json 모양(`_write_fetch_errors`)·요청 모양(`build_requests`)·고르기·가리기·기록 사슬: 코드 변경 없음. 기존 시험(`test_exit_codes_and_korean_text`, `test_main_submit_and_collect_lines`, fetch 오류 시험들 등) 무수정 통과.
- `fetch_items_detail`·`run_submit`은 손대지 않음. 바뀐 것은 `default_fetcher`의 접속 설정과 CA 복사본 1개 쓰기뿐.
- 권한 표지 4종 줄 변경 없음.

## (e) 병합 뒤 확인 (사장 손 없음)
- 다음 19:30 KST 자동 제출 뒤 `workspace/outputs/llm/runner/<날짜>.json`의 news-submit이 SUBMITTED인지, 아니면 `workspace/outputs/llm/news/<날짜>/fetch-errors.json`의 새 오류를 본다.
- `C:\ProgramData\InvestmentV2\certifi-cacert.pem`이 생겼는지 본다.
- 여전히 `curl: (77)`이면 오류 글의 CAfile 경로로 구분: 사용자 폴더 경로면 복사 실패(`ascii_ca_bundle`이 None — 쓰기 권한·certifi import 확인), `C:\ProgramData\...`면 "한글 경로가 원인" 가설이 틀림.

## (f) 확인 필요
- 실제 PC에서 curl이 ASCII 경로 묶음으로 접속되는지(첫 실행에서 확인).
- yfinance 1.8이 쿠키·crumb 요청까지 넘긴 세션만 쓰는지(지시문의 설치본 사실은 참고만, 이 작업에서 설치본을 열어 보지 않음).
- `C:\ProgramData` 쓰기 권한(지시문: BUILTIN\Users Write 있음 — 2026-11-20 읽기 조회). 이 작업은 PC에서 실행하지 않아 확인하지 않음.
- 동시에 두 프로세스가 복사본을 쓰면 같은 임시 파일 이름을 씀(`os` 속성 제한으로 pid를 넣지 않음). 실패하면 None → 기본 동작으로 돌아가며 진단은 fetch-errors.json에 남음.
