---
id: llm-newsca-builder-prompt
title: "API 시범 2 뉴스 — 인증서 묶음 경로를 영문 경로로 넘겨 기사 접속 고치기 — llm-newsca"
date: 2026-11-20
class: "general(기존 시범 스크립트 1개와 그 시험만, 코어·정책·주문 경로와 무관). 개발 큐 general: Builder → Judge → READY_TO_MERGE면 Cowork 또는 사장 dev-merge"
source: "진단 docs/claude/backlog-review-2026-11-19.md:80-87(11/20 19:30 fetch-errors.json 30/30 SSLError curl (77), CA 파일 경로에 한글 사용자 이름). 개발 큐 등록 승인 = 사장 결정 카드 '스크립트에서 고침(개발 큐)'(카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9WPJfBVNfJ7ktcnpBrnjqPf, 2026-11-20 19:56:21 KST, 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH, 사장실 회사PC 스레드 '밀린 검토 3건 결론 내기')"
authority: "권한 표지 4종 줄 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장·연구 기록·카드 쓰기 없음 · 계좌·보유 자료를 읽지 않음 · API 키 값을 읽거나 출력하지 않음 · 켜기 파일을 바꾸지 않음 · 사전 등록 두 파일을 바꾸지 않음 · PC 환경 변수·설치 패키지를 바꾸지 않음"
---

## 목표
- 뉴스 제출 단계의 기사 가져오기(`default_fetcher`, llm_pilot_news.py 300행)가 모든 종목에서 `curl: (77) error adding trust anchors`로 실패한다(2026-11-20 fetch-errors.json 30/30). 원인은 curl_cffi가 쓰는 certifi 인증서 묶음 경로(`C:\Users\<한글 이름>\AppData\Roaming\Python\Python315\site-packages\certifi\cacert.pem`)를 curl이 열지 못하는 것으로 본다.
- 고침: 인증서 묶음 경로가 ASCII가 아니면 같은 내용을 ASCII 경로로 복사하고, 그 경로를 `verify`로 준 curl_cffi Session을 yfinance `Ticker(symbol, session=...)`에 넘긴다. 경로가 이미 ASCII면 지금과 같은 기본 동작(session을 넘기지 않음)을 유지한다.
- **바뀌는 것은 기사 가져오기의 접속 설정과 그에 딸린 CA 복사본 1개 쓰기뿐이다.** 고르기·가리기·요청·점수·기록 사슬·종료 코드·stdout 마지막 줄·fetch-errors.json 모양은 그대로다. 인증서 검증을 끄지 않는다(`verify=False` 금지).

## 바꿀 파일 (이 3개만)
- manage-us-stock-strategy/scripts/llm_pilot_news.py (기존, CRLF — 원래 줄바꿈을 지킨다)
- manage-us-stock-strategy/tests/test_llm_pilot_news.py (기존, CRLF — 원래 줄바꿈을 지킨다. 기존 시험은 고치지 않고 새 시험만 더한다)
- docs/claude/llm-newsca-report.md (새 파일, LF, 보고)

## 먼저 읽을 것 (고치지 않는다)
- `manage-us-stock-strategy/scripts/llm_pilot_news.py` 전체. 특히 `default_fetcher`(300행), `fetch_items_detail`(325행)·`fetch_items`(351행), `run_submit` 6단계, `atomic_write_text` 사용처.
- `manage-us-stock-strategy/tests/test_llm_pilot_news.py`의 `test_script_source_contract`(1003행, 금지어 목록: environ·zoneinfo·subprocess·import requests·urllib·fallbacks·advisor·socket·http.client·auto_core·kiwoom — 주석 포함 어디에도 쓰지 않는다), `Fetcher` 가짜.
- 설치본 사실(2026-11-20 사장실 스레드가 읽음, 참고만): curl_cffi 0.17 `requests/session.py` Session의 `verify`가 문자열이면 `utils.py` 915~922행에서 `CurlOpt.CAINFO`로 쓰인다. yfinance 1.8 `base.py` 82행 `Ticker(ticker, session=None)`, `_http.py` 61행 기본 Session은 `impersonate="chrome"`, `data.py` 136~150행은 curl_cffi Session을 받는다(캐시 세션은 거부).

## 구현 요구 (ASCII만, `scripts/*.py` 언어 계약)
1. 상수 `CA_COPY_DIR = Path("C:/ProgramData/InvestmentV2")`, `CA_COPY_NAME = "certifi-cacert.pem"`.
2. 새 함수 `ascii_ca_bundle(src=None, copy_dir=None) -> str | None`. `copy_dir`이 None이면 부를 때 모듈 전역 `CA_COPY_DIR`을 읽는다(기본 인자에 상수를 묶지 않는다).
   - `src`가 None이면 함수 안에서 `import certifi`로 `certifi.where()`를 쓴다(시험은 `src`를 넘겨 certifi 없이 돈다). certifi import 실패면 None.
   - ASCII 판정은 넘겨받은 경로 문자열 그대로에 한다(`resolve`·`absolute`로 바꾸지 않는다).
   - `str(src)`가 ASCII면 None을 돌려준다(= 기본 동작 유지 신호).
   - ASCII가 아니면 `str(copy_dir)`이 ASCII인지 확인(아니면 None), 폴더를 만들고(`parents=True, exist_ok=True`), 원본은 `Path(src).read_bytes()`로 읽는다. 매 호출에서 대상 파일 바이트를 원본과 대조해 다르거나 없을 때만 다시 쓴다("파일이 있으면 그대로 씀" 지름길 금지 — 누구나 쓸 수 있는 폴더라 매 프로세스 원본으로 되돌리는 방어). 쓰기는 `atomic_write_text`가 아닌 바이트 쓰기로 원자적으로 한다(같은 폴더 임시 파일 → `os.fsync` → `os.replace`). 성공하면 대상 경로 문자열을 돌려준다.
   - 어느 단계든 `OSError`면 None(진단은 fetch-errors.json이 이미 남긴다).
   - `import os`를 더한다. `os`는 `os.replace`·`os.fsync`만 쓴다(금지어 environ 때문에 다른 os 속성 금지).
3. 캐시는 모듈 상수 `_FETCH_STATE = {}` 하나로 둔다(키 "bundle"·"session", 키가 없으면 아직 안 부름 — None 결과도 "bundle" 키에 저장). 한 프로세스에서 `ascii_ca_bundle()`은 한 번, 세션도 한 번만 만든다(30종목이 같은 세션).
4. `default_fetcher(symbol)`: `yfinance`를 함수 안에서 import(지금처럼). `ascii_ca_bundle`을 모듈 전역 이름으로 불러(시험 가짜가 먹도록) 경로를 받으면 함수 안에서 정확히 `from curl_cffi.requests import Session` 꼴로 import해 `Session(impersonate="chrome", verify=<경로>)`를 만들고 `yfinance.Ticker(symbol, session=<그 세션>).news`, None이면 지금처럼 `yfinance.Ticker(symbol).news`.
   - `from curl_cffi import requests` 꼴은 금지어 "import requests"에 걸리므로 쓰지 않는다. 주석·docstring에 environment 같은 낱말도 쓰지 않는다("environ" 포함).
   - 세션 만들기·import에서 예외가 나면 그 예외가 `fetch_items_detail`로 올라가 기존처럼 기록된다(따로 삼키지 않는다).
5. 모듈 docstring의 쓰기 범위 문장("Writes only under workspace/outputs/llm/.")에 CA 복사본 1개(`CA_COPY_DIR` 아래 `CA_COPY_NAME`)를 더한다.
6. 다른 경로는 고치지 않는다. 새 네트워크 모듈·환경 변수 읽기 없음. 시험 계약 금지어를 쓰지 않는다.

## 시험 (test_llm_pilot_news.py에 새 시험만 더함)
- 임시 폴더의 절대 경로가 ASCII라고 가정하지 않는다(이 PC의 TEMP는 한글 사용자 폴더 아래일 수 있다). `ascii_ca_bundle` 시험은 임시 폴더로 작업 폴더를 옮기고(`contextlib.chdir`, 끝나면 되돌림) 상대 경로(`"src-ascii/cacert.pem"`, `"src-\u00e9/cacert.pem"`, `"copy/"`)를 넘긴다.
- `ascii_ca_bundle`을 부르는 모든 시험은 `copy_dir`을 꼭 넘긴다. `default_fetcher` 시험은 `ascii_ca_bundle`을 꼭 가짜로 바꾼다(`mock.patch.object(MODULE, "ascii_ca_bundle", ...)`)고 `mock.patch.dict(MODULE._FETCH_STATE, {}, clear=True)`로 캐시를 비운다.
- `test_ascii_ca_bundle_ascii_source_returns_none`: ASCII 상대 경로의 원본 → None, 복사 폴더에 아무것도 안 생김.
- `test_ascii_ca_bundle_copies_non_ascii_source`: 비ASCII 이름 폴더에 둔 원본 → ASCII 복사 폴더에 같은 바이트, 돌려준 경로가 ASCII.
- `test_ascii_ca_bundle_skips_rewrite_when_same`: 두 번 불러도 같은 결과, 두 번째는 내용이 같아 다시 쓰지 않음(수정 시각 또는 쓰기 가짜로 단언).
- `test_ascii_ca_bundle_non_ascii_copy_dir_returns_none`: 복사 폴더가 비ASCII → None.
- `test_ascii_ca_bundle_oserror_returns_none`: 복사 폴더 자리에 같은 이름 파일을 미리 둠 → None.
- `test_ascii_ca_bundle_rewrites_tampered_copy`: 복사본 바이트를 바꿔 둔 뒤 다시 부르면 원본 바이트로 되돌아감.
- 가짜 모듈은 `mock.patch.dict(sys.modules, {"yfinance": ..., "curl_cffi": ..., "curl_cffi.requests": ...})`로 시험 안에서만 끼운다.
- `test_default_fetcher_uses_session_when_bundle_given`: `ascii_ca_bundle` 가짜가 경로를 주면 `Session(impersonate="chrome", verify=<경로>)`와 `Ticker(symbol, session=...)`가 불림. 두 종목을 불러도 세션 1번·`ascii_ca_bundle` 1번.
- `test_default_fetcher_plain_ticker_when_none`: `ascii_ca_bundle` 가짜가 None → `Ticker(symbol)`만 불리고 Session은 안 불림.
- Builder 시험 명령(이 글자 그대로): `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot_news*.py"`. 전체 시험은 돌리지 않는다(파이프라인이 한다).
- 모든 시험은 임시 폴더만 쓴다. `C:/ProgramData`에 쓰지 않는다. 네트워크·실제 yfinance·SDK·실제 키 없음.

## 지켜야 할 것
1. 위 3개 파일 밖은 손대지 않는다. 사전 등록 두 파일·`llm-pilots-schedule.json`·`llm_pilot_common.py`·`llm_pilot_iccheck.py`·`llm_runner.py`와 그 시험을 고치지 않는다.
2. 기존 시험을 고치거나 지우지 않는다.
3. 키 값을 읽지 않는다. 비밀(.env*·토큰·계좌번호) 파일을 열지 않는다.
4. 어떤 시범도 켜지 않는다. Windows 작업을 등록·실행·변경하지 않는다. 저장소 루트에 대고 스크립트를 돌리지 않는다(`--dry-run` 포함). pip로 무엇도 설치하지 않는다.
5. 주문·키움·일지·원장·예약·정책·상태와 무관하다. auto_core.py·kiwoomcli 실행 금지. git은 status·diff·log만. commit·push·병합 없음. `python -c` 쓰지 않음.
6. 인증서 검증을 끄는 코드(`verify=False`, `SSL_VERIFYPEER 0`)를 쓰지 않는다.
7. 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/llm-newsca-report.md
- (a) 바꾼 함수(파일:행)와 상수
- (b) 새 시험 이름과 단언 요약, 기존 시험이 그대로임
- (c) 시험 결과 마지막 3줄 · `git diff --stat` · `git diff --ignore-cr-at-eol --stat`
- (d) 바뀌지 않은 것 대조: stdout 마지막 줄·종료 코드·counts·REASON_KO·fetch-errors.json 모양·요청 모양
- (e) 병합 뒤 확인: 다음 19:30 KST 자동 제출 뒤 `workspace/outputs/llm/runner/<날짜>.json`의 news-submit이 SUBMITTED인지, 아니면 `news/<날짜>/fetch-errors.json`의 새 오류. `C:\ProgramData\InvestmentV2\certifi-cacert.pem`이 생겼는지. 여전히 (77)이면 오류 글의 CAfile 경로로 구분한다(사용자 폴더면 복사 실패, ProgramData면 원인 가설이 틀림). 사장 손 없음.
- (f) 확인 필요로 남은 것: 실제 PC에서 curl이 ASCII 경로 묶음으로 접속되는지(첫 실행에서 확인), yfinance 1.8이 쿠키·crumb 요청까지 넘긴 세션만 쓰는지, C:\ProgramData 쓰기 권한(BUILTIN\Users Write 있음 — 2026-11-20 읽기 조회).
- 수량·금액·키 값을 적지 않는다. 주문·권한 표지 문자열도 적지 않고 '권한 표지 4종 줄 변경 없음'이라고만 쓴다.

## 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| `C:\ProgramData\InvestmentV2\certifi-cacert.pem`(이 작업이 새로 만드는 복사본) · 뉴스 기사 가져오기 결과 | Windows 작업 InvestmentV2-LLMPilots → `manage-us-stock-strategy/scripts/llm_runner.py:55` news-submit 19:30 KST → 이 스크립트 `default_fetcher` | 사람 단계 — 자동으로 읽는 예약 없음. 사장실 회사PC 스레드가 `news/<날짜>/fetch-errors.json`을 직접 읽음(원문 `docs/claude/backlog-review-2026-11-19.md:82-83`) | `run_submit` 6단계가 가져온 기사를 고르기·요청으로 넘김. 접속이 되면 Batch 제출이 시작돼 그림자 기록·표시용 요약이 쌓임(원문 `docs/claude/llm-news2-builder-prompt.md:186-188`) | 끊김 — 실행기 하루 기록 `workspace/outputs/llm/runner/<날짜>.json` status를 읽는 예약이 없다(`docs/claude/llm-news2-builder-prompt.md:186`과 같은 끊김). 메울 변경: 사장실 결과 모음 예약이 실행기 하루 기록을 읽게 하기 · 승인 경로: 지침 4절 `예약 작업 변경 승인: <이름>`(이 작업 밖) | 연결(제출) · 알림 끊김(기존과 같음) |

기존 산출(records.jsonl·digest.md·usage.jsonl·batch.json·fetch-errors.json)의 연결은 이 작업으로 바뀌지 않는다 — `docs/claude/llm-news2-builder-prompt.md:186-188` 그대로.

## Judge 확인 항목
1. diff가 허용 파일 3개뿐이다. 두 기존 파일의 줄바꿈이 CRLF 그대로다(checks.json 위생에 EOL_CRLF_BROKEN 없음 + 보고 (c)의 두 stat).
2. 인증서 검증을 끄는 코드가 없다. `verify`에는 ASCII 복사본 경로만 들어간다. verify에 넘기기 전에 매 프로세스에서 복사본 바이트를 certifi 원본과 대조한다(다르면 다시 씀). "있으면 그대로 씀" 지름길이 없다.
3. 원본 경로가 ASCII면 기존 동작(session 없음)이 유지된다. 시험이 이를 단언한다.
4. 쓰기는 `CA_COPY_DIR` 아래 `certifi-cacert.pem`과 그 임시 파일(같은 폴더, `os.replace`로 사라짐), 기존 `workspace/outputs/llm/` 아래뿐이다. 모듈 docstring의 쓰기 범위 문장이 이에 맞다. 시험은 `C:/ProgramData`에 쓰지 않는다(모든 `ascii_ca_bundle` 호출에 `copy_dir`, `default_fetcher` 시험은 가짜).
5. stdout 마지막 줄·종료 코드·counts·REASON_KO·fetch-errors.json 모양이 그대로다(기존 시험 무수정 통과). 환경 변수 읽기·새 네트워크 모듈 없음, 금지어 없음.
6. 기존 시험 변경 없음, 새 실패 0. 보고서 (a)~(f) 있음, 표지 문자열 없음.

```dev-run
{"task_id": "llm-newsca", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 80, "builder_timeout_min": 45, "allowed_paths": ["manage-us-stock-strategy/scripts/llm_pilot_news.py", "manage-us-stock-strategy/tests/test_llm_pilot_news.py", "docs/claude/llm-newsca-report.md"], "target_tests": ["test_llm_pilot_news*.py"], "commit_message": "fix(llm-pilot): pass an ASCII-path copy of the certifi CA bundle to the yfinance curl_cffi session so news fetch works under a non-ASCII user profile (llm-newsca)"}
```
