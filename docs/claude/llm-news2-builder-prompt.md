---
id: llm-news2-builder-prompt
title: "API 시범 2 — 뉴스 요약 + 이름 지운 그림자 점수(Batch 제출·수거) — llm-news2(llm-news 재시도)"
date: 2026-11-18
class: "general(새 파일만, 코어·정책·주문 경로와 무관). 개발 큐 general: Builder → Judge → READY_TO_MERGE면 Cowork가 dev-merge"
source: "설계 docs/claude/api-pilots-2026-11-06.md 4절 '시범 2'·6절 작업 3, 사전 등록 docs/claude/llm-news-prereg-v1.json(원본)·.md. 개발 큐 등록 승인 = 사장 결정 카드 '시범 1부터 차례로'(카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9E3aPheNEEsLywwbJ1nm476, 2026-11-06 16:44:47 KST, 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH) + 사장 지시 2026-11-18 09:38:04 KST '밀린 ①·② 두 건을 진행'(cmsg_0137MRzn9nuDvvQmVxm6WeX9Lc2UKJUSQre5gQ4dd6nC1j). 등록 조건(6절 작업 3: 작업 2 병합) 충족. Batch가 월 크레딧 적용 대상임은 2026-11-18 09:22 KST Console 결제 화면에서 확인(token-usage-api-credit-review-2026-11-18.md 3절). 시범 켜기는 이 작업 밖(병합 뒤 따로 사장 승인)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장·연구 기록·카드 쓰기 없음 · 계좌·보유 자료를 읽지 않음 · API 키 값을 읽거나 출력하지 않음 · 켜기 파일을 바꾸지 않음"
---

## 재시도 사유 (먼저 읽는다)
- 앞 작업 llm-news(2026-11-18 02:35~03:05 UTC, base d8fd070)는 BLOCKED였다. 구현·시험은 Judge G1~G8 모두 PASS였고, G9 연결표만 FAIL이었다 — 지시문 `## 연결표` 181~183행(허용 경로 밖)이 원인(docs/claude/dev-runs/llm-news.md).
- 연결표는 사장실이 이 지시문에서 고쳤다(Judge min_fixes 3건, 2026-11-18 12:55 KST). 그 밖의 요구·허용 경로·시험은 llm-news와 같다. 처음부터 다시 만든다(앞 worktree를 쓰지 않는다).
- 보고 첫 줄 아래에 '재시도: llm-news2 — 앞 작업 llm-news의 G9 연결표 FAIL(지시문 쪽) 고침'을 적는다.

## 목표
- 사전 등록 v1 그대로, 대상 30종목의 새 뉴스를 하루 한 번 Batch로 보내고(19:30 KST 제출) 개장 전에 받아(22:00·23:00 KST 수거) 두 가지를 남기는 스크립트 `llm_pilot_news.py`를 만든다.
  - 그림자 점수: 이름을 지운 제목+요약에 대한 label(good/bad/unknown). `records.jsonl`에 덧붙이기만 하고 어떤 화면에도 내지 않는다.
  - 표시용 요약: 이름을 그대로 둔 한국어 3줄. `digest.md`에 쓴다. digest에는 label·점수를 쓰지 않는다.
- 이 작업은 시범을 켜지 않는다. `docs/claude/llm-pilots-schedule.json`, 실행기, 공통 모듈, 시범 1은 고치지 않는다.
- 채점기(시작 + 182일)는 이 작업이 아니다. 표본에 드는지(개장 전 수신)는 채점기가 `received_at`으로 판정한다. 이 스크립트는 미국 장 시각·달력을 계산하지 않는다(`zoneinfo`·tzdata를 쓰지 않는다).

## 바꿀 파일 (이 3개만, 모두 새 파일)
- manage-us-stock-strategy/scripts/llm_pilot_news.py
- manage-us-stock-strategy/tests/test_llm_pilot_news.py
- docs/claude/llm-news-report.md (보고)

## 먼저 읽을 것 (고치지 않는다)
- `docs/claude/llm-news-prereg-v1.json`(원본)·`.md`. 이 두 파일은 이 작업을 큐에 올리기 전에 문서 커밋으로 저장소에 들어가 있어야 한다(등록 전제). 없으면 BLOCKED.md를 쓰고 멈춘다(만들지 않는다).
- `manage-us-stock-strategy/scripts/llm_pilot_common.py`: `KEY_ENV`·`MODELS`·`BUDGET_USD_MONTH`·`KST`·`REPO_ROOT`·`llm_dir`·`load_key`·`make_client`·`api_error_label`·`estimate_cost(model, usage, batch=True)`·`append_usage`·`month_spend`·`atomic_write_text`·`write_failed`·`response_text`·`check_message`.
- `manage-us-stock-strategy/scripts/llm_pilot_iccheck.py`: import 방식(24~47행), `EXIT_CODES`(54~65행), 한글을 `\UXXXXXXXX`로 쓰는 방식(67행 주석), `build_request`의 `output_config`(178~200행), `_usage_numbers`·usage 기록 모양, `run_detail`의 순서(키 → 예산 → 요청 → 검사 → 기록), `main`의 한 줄 출력.
- `docs/claude/llm-runner-report.md` (d) 시범 스크립트 약속.
- 시험 선례 `manage-us-stock-strategy/tests/test_llm_pilot_iccheck.py`(가짜 client_factory, 임시 루트).

## 구현 요구 — llm_pilot_news.py (ASCII만, `scripts/*.py` 언어 계약)

### 1. 상수와 경로
- `PILOT = "news"`. 모델은 `MODELS[PILOT]`만 쓴다(문자열을 다시 적지 않는다).
- `PREREG_REL = "docs/claude/llm-news-prereg-v1.json"`.
- `PREREG_SHA256 = "a8b6f930d7a06ff73f146bfee0236e8f4f6169fbeed7663eacaa4ab43f3262e8"`, `LABEL_PROMPT_SHA256 = "448d2519a4726f600f83e05c750107aaf290756a9c66a6c23d98d59979351db5"`. 이 두 값은 이 지시문에서 그대로 옮긴다. Builder는 해시를 손으로 계산하지 않는다.
- 정규 해시 = `json.dumps(값, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`의 UTF-8 sha256. 지시문 해시 = `label_system_prompt` 글의 UTF-8 sha256.
- `FRESH_HOURS = 24`, `REASON_MAX_CHARS = 200`, `TITLE_MAX_CHARS = 300`, `SUMMARY_MAX_CHARS = 2000`, `LOOKBACK_DAYS = 3`. `max_tokens`는 상수로 두지 않고 사전 등록 `model.max_tokens`에서 읽는다.
- 종목당 기사 수는 자르지 않는다(사전 등록 `item_rule`에 상한이 없다). 제목·요약은 위 글자 수에서 자른다(요청 하나가 커지지 않게 — 설계서 3절 4의 크기 상한을 이 시범에서는 글자 수 자르기로 지킨다. 보고서에 적는다).
- 경로(모두 `llm_dir(root) / "news"` 아래):
  - `records.jsonl` — 그림자 기록(덧붙이기만)
  - `seen.json` — `{item_id: first_seen_at}`(원자적 쓰기)
  - `HALT` — 멈춤 표지(한 줄 이유). 있으면 submit은 아무것도 하지 않는다
  - `<날짜>/submit-started` · `<날짜>/batch.json` · `<날짜>/usage-done` · `<날짜>/collected.json` · `<날짜>/digest.md` · `<날짜>/failed.md`
- 이 스크립트는 `workspace/outputs/llm/` 밖에 쓰지 않는다. 계좌·보유·정책·연구 기록 파일을 열지 않는다.

### 2. 사전 등록 읽기 `load_prereg(root) -> (prereg | None, reason)`
- 파일 없음·JSON 아님·정규 해시가 `PREREG_SHA256`과 다름·지시문 해시가 `LABEL_PROMPT_SHA256`과 다름 → `(None, "PREREG_MISMATCH")`.
- 대상 종목·별칭·가리기 규칙·지시문·스키마·메시지 틀은 모두 이 JSON에서 읽는다. 코드에 종목 목록이나 지시문을 다시 적지 않는다.

### 3. 이름 지우기 `mask_item_text(text, target, prereg) -> str`
- 사전 등록 `masking` 규칙 네 줄 그대로다. 대상 종목 → `[COMPANY]`, 다른 29종목 → `[OTHER]`, URL은 지운다.
- 기호는 대문자 그대로일 때만, 다음 꼴에서만 바꾼다: 거래소 표기 NASDAQ·NYSE(표기의 대소문자·콜론 앞뒤 띄어쓰기·괄호 유무 무관) 뒤의 기호, 괄호 안 기호 하나, `$기호`, `기호.O`, 3글자 이상 대문자 낱말로 홀로 선 기호.
- 별칭은 낱말 단위로 바꾼다. `case_sensitive_aliases`에 든 별칭은 대소문자를 구분하고, 나머지는 구분하지 않는다. 긴 별칭부터 바꾼다('Micron Technology'가 'Micron'보다 먼저).
- 2글자 기호(MU·BE·ON)는 홀로 선 낱말로는 바꾸지 않는다(위 기호 꼴일 때만).

### 4. 기사 가져오기 `fetch_items(symbol, fetcher) -> list | None`
- 기본 fetcher는 `yfinance`를 함수 안에서 import해 `yfinance.Ticker(symbol).news`를 돌려준다. 예외면 None(그 종목 실패로 센다). 시험은 가짜 fetcher만 쓴다.
- 항목 정규화 `normalize_item(raw) -> dict | None`: yfinance 판에 따라 두 꼴이 있다. 둘 다 받는다.
  - 납작한 꼴: `uuid`, `title`, `summary`(없을 수 있음), `providerPublishTime`(초 단위 숫자)
  - 안에 든 꼴: `raw["content"]`의 `id`, `title`, `summary`, `pubDate`(ISO 글)
  - 결과: `{"item_id", "title", "summary", "published_at"}`(published_at은 UTC ISO, 초 단위, 끝 `Z`). id가 없거나 제목이 비었거나 시각을 못 읽으면 None(건너뜀으로 센다).
  - 설치된 yfinance가 실제로 어느 꼴을 주는지는 네트워크 없이 확인할 수 없다. 보고서 (f)에 '실제 꼴은 첫 실행에서 확인 필요'라고 적는다.
- 요약이 없으면 빈 글로 둔다(`{summary}` 자리에 빈 글).

### 5. 제출 `run_submit(day, *, repo_root, client_factory, fetcher, now, dry_run)`
순서를 지킨다. 각 단계의 실패는 `write_failed(day_dir, <STATUS>, <한국어 이유>)` + 해당 종료 코드다.
1. `news/HALT`가 있으면 `HALTED`(아무것도 쓰지 않음, failed.md도 쓰지 않음).
2. `<날짜>/batch.json` 또는 `<날짜>/submit-started`가 있으면:
   - batch.json 있음 → `ALREADY_DONE`.
   - submit-started만 있음 → `SUBMIT_UNKNOWN`(제출이 됐는지 모른다. 다시 내지 않는다 — 두 번 내는 것보다 하루 비는 쪽).
3. `load_prereg` 실패 → `HALT` 파일을 쓰고 `PREREG_MISMATCH`.
4. `load_key()`가 None → `NO_KEY`.
5. `month_spend(root, PILOT, <그 달>) >= BUDGET_USD_MONTH[PILOT]` → `BUDGET_STOP`. `month_spend`가 예외를 내도 `BUDGET_STOP`(iccheck 369~372행과 같게 — 모르면 막는 쪽).
6. 30종목을 사전 등록 `universe` 순서로 가져온다. 모두 실패(None)면 `FETCH_FAILED`. 일부 실패는 세기만 한다.
7. 고르기: `seen.json`에 없는 item_id만 '처음 본 것'이다. 같은 실행에서 한 item_id가 두 종목에 나오면 먼저 나온 종목의 것으로 한다. 처음 본 것은 모두 `first_seen_at`(= now, KST ISO)을 붙여 seen에 넣을 목록으로 잡는다(파일 쓰기는 8 또는 12에서만). 그 가운데 `now - published_at`이 0 이상 24시간 이하인 것만 보낸다.
8. (dry_run이 아닐 때) 보낼 것이 0건 → `<날짜>/batch.json`을 `{"schema": "llm-news-batch-1", "day", "status": "NO_ITEMS", "items": []}`로 쓰고 `NO_ITEMS`(종료 0). seen.json은 이때도 쓴다.
9. **dry_run**: 1~3은 읽기만 한다(3이 실패해도 HALT 파일을 쓰지 않고 상태만 낸다). 4·5는 건너뛴다. 6·7을 하고, 8로 가기 전에 `llm-news <날짜> DRY_RUN items=<n> symbols_failed=<k>` 한 줄을 내고 끝낸다. 어떤 파일도 쓰지 않는다(seen.json·batch.json·failed.md 포함). 클라이언트를 만들지 않는다.
10. 요청을 만든다. 기사 n번(1부터)마다 두 개:
    - 점수 요청 `custom_id = "L%04d" % n`: `system` = `label_system_prompt`, 사용자 글 = `user_message_template`에 **가린** 제목·요약을 넣은 것, `output_config = {"format": {"type": "json_schema", "schema": <label_schema>}, "effort": "low"}`.
    - 요약 요청 `custom_id = "S%04d" % n`: 이름을 **그대로** 둔 제목·요약, `system`은 '투자 권유·등급·점수 없이 사실만 한국어 3줄로'라는 고정 지시(상수, `\U` 이스케이프), `output_config = {"effort": "low"}`.
    - 둘 다 `model = MODELS[PILOT]`, `max_tokens = MAX_TOKENS`, `messages = [{"role": "user", "content": <글>}]`. `thinking`·`temperature`·`fallbacks`·`stream`·`speed`·`cache_control`·베타 머리말을 넣지 않는다.
    - 가린 글을 다시 검사한다: `mask_item_text`를 가린 글에 한 번 더 돌려 글이 바뀌면(= 규칙상 가려야 할 것이 남음) 그 기사는 보내지 않고 `mask_leak`으로 센다. 사전 등록이 일부러 남기는 꼴(홀로 선 2글자 기호, 대소문자 구분 별칭의 다른 대소문자)은 새는 것이 아니다.
11. `<날짜>/submit-started`를 쓴다(내용 = now). 그다음 `client.messages.batches.create(requests=[{"custom_id": ..., "params": {...}}, ...])`를 **한 번** 부른다. 요청은 dict로 넘긴다.
    - 예외: `getattr(exc, "status_code", None) == 404`면 `HALT` 파일을 쓰고 `MODEL_NOT_FOUND`(`api_error_label`은 클래스 이름과 코드만 줘서 구분에 쓰지 않는다). 그 밖은 `API_ERROR`. 두 경우 모두 submit-started를 지우지 않는다(다시 내지 않음). 예외 문장은 어디에도 쓰지 않는다.
12. `<날짜>/batch.json`을 쓴다: `{"schema": "llm-news-batch-1", "day", "status": "SUBMITTED", "batch_id", "submitted_at"(KST ISO), "prereg_sha256", "counts": {"symbols_failed", "skipped", "mask_leak", "items"}, "items": [{"n", "symbol", "item_id", "published_at", "first_seen_at", "title"}]}`. 그 뒤 seen.json을 쓴다. `records.jsonl`이 없으면 이때 머리줄 한 줄을 써서 만든다(6절 8 — 시작일 = 첫 제출일, 사전 등록 `scoring.when`).
13. 표준 출력 마지막 행: `llm-news <날짜> SUBMITTED items=<n> requests=<2n> symbols_failed=<k>`.

### 6. 수거 `run_collect(day, *, repo_root, client_factory, now, dry_run)`
0. **밀린 수거**: 아래 1~12를 그날(`--day`)에 하기 전에, 앞선 `LOOKBACK_DAYS`일의 폴더 가운데 batch.json이 `SUBMITTED`이고 collected.json이 없는 날을 오래된 순서로 같은 절차(3~11)로 수거한다. 실행기는 칸마다 하루 한 번만 부르므로(`llm_runner.py` 273~277행) 23:00에도 끝나지 않은 배치는 다음 날 수거 때 받는다. 밀린 날의 `received_at`도 실제 받은 시각이다(늦은 수신으로 기록될 뿐 빼지 않는다). 밀린 날이 실패해도 그날 수거는 계속한다. 표준 출력 마지막 행은 그날 것이고 끝에 ` late=<밀린 날 수거 수>`를 붙인다.
1. `<날짜>/collected.json` 있음 → `ALREADY_DONE`.
2. `<날짜>/batch.json` 없음 → `NO_BATCH`(종료 0, failed.md 없음 — 제출이 꺼져 있거나 실패한 날). status가 `NO_ITEMS` → `NOTHING_TO_COLLECT`(종료 0).
3. `load_prereg` 실패 또는 batch.json의 `prereg_sha256`이 `PREREG_SHA256`과 다름 → `HALT` 파일 + `PREREG_MISMATCH`.
4. `load_key()` None → `NO_KEY`.
5. `client.messages.batches.retrieve(batch_id)`의 `processing_status`가 `"ended"`가 아니면 `PENDING`(종료 0, 아무것도 쓰지 않음 — 다음 칸 또는 다음 날 밀린 수거에서 다시 본다). retrieve·results가 예외를 내면 `API_ERROR`(failed.md, 다른 파일은 쓰지 않음, 예외 문장 없음).
6. `client.messages.batches.results(batch_id)`를 끝까지 읽는다. 결과는 순서가 없으므로 `custom_id`로 맞춘다. **받은 시각 `received_at` = 결과를 다 읽은 직후의 now(KST ISO)**(Batch가 끝난 시각이 아니다).
6-1. **사용량을 먼저 남긴다**: `<날짜>/usage-done`이 없으면, 성공한 메시지마다 `estimate_cost(model, usage, batch=True)`를 **따로** 계산해 더한 값과 토큰 합으로 `append_usage` 한 줄을 쓰고 `usage-done`을 쓴다(합친 usage로 한 번에 계산하지 않는다 — 입력 합이 10만을 넘으면 `estimate_cost`가 긴 문맥 단가를 잘못 적용한다, common 310~311행). 줄의 키는 iccheck가 쓰는 usage 줄과 같게 한다(`ts_kst`·`pilot`·`model`·토큰 칸·`batch`·`cost_usd_est`·`status` — iccheck 415행 근처를 읽고 그대로. `ts_kst`가 없으면 다른 시범의 `month_spend`가 깨진다). 아래 7·8에서 멈추더라도 사용량은 이미 남아 있다.
7. 결과마다:
   - `result.type`이 `succeeded`가 아니면(`errored`·`canceled`·`expired`) 세기만 한다. 단 `errored` 건의 오류 종류 글(`getattr`로 방어해서 읽는다)에 `not_found`가 들어 있으면 `HALT` 파일 + `MODEL_NOT_FOUND`로 전체를 멈춘다(Batch에서 모델 오류가 이 꼴로 오는지는 확인 필요 — 보고서 (f)).
   - `check_message(message, MODELS[PILOT])`가 `MODEL_MISMATCH` → 전체를 멈춘다: `HALT` 파일 + `MODEL_MISMATCH`, records.jsonl에 아무것도 덧붙이지 않는다. 다른 값(REFUSAL·MAX_TOKENS·BAD_STOP)은 그 건만 버리고 센다.
   - 점수 건: `response_text(message)`를 JSON으로 읽어 `label`이 세 값 중 하나이고 `reason`이 글이어야 한다. 아니면 버리고 센다. `reason`은 `REASON_MAX_CHARS`자로 자른다.
   - 요약 건: 글을 그대로 쓴다(앞뒤 공백만 정리).
8. `records.jsonl`에 덧붙인다(기사 n 순서, 점수가 유효한 건만).
   - 머리줄(첫 줄) = `{"schema": "llm-news-records-1", "start_day": <첫 제출일>, "prereg_sha256": ..., "prev_sha256": ""}`. 첫 `SUBMITTED` 제출 때 만든다(5절 12). 수거 때 파일이 없으면 `RECORDS_BROKEN`으로 본다.
   - 기록 줄의 키는 사전 등록 `record.fields` 10개 **그대로**, 그 순서: symbol, item_id, published_at, first_seen_at, submitted_at, received_at, label, reason, model(응답의 model 값), prev_sha256.
   - `prev_sha256` = 바로 앞 줄(줄바꿈 뺀 UTF-8 바이트)의 sha256. 줄은 `json.dumps(..., ensure_ascii=False, separators=(",", ":"))` + `\n`.
   - 덧붙이기 전에 기존 파일의 사슬을 처음부터 검사한다. 깨져 있으면 `HALT` 파일 + `RECORDS_BROKEN`, 덧붙이지 않는다.
   - 덧붙이기는 한 번의 쓰기로 한다(여러 줄을 한 글로 만들어 `"a"` 모드로 한 번). 기존 줄을 고치거나 지우지 않는다.
   - 늦게 받은 결과도 그대로 덧붙인다(빼거나 다음 날로 미루지 않는다). 표본 판정은 채점기의 일이다.
9. (사용량은 6-1에서 이미 썼다.)
10. `<날짜>/digest.md`: 종목(사전 등록 순서)마다 기사 제목 + 한국어 요약. 요약이 없는 기사는 제목만. **label·reason·점수·'좋음/나쁨' 낱말을 쓰지 않는다.** 맨 아래 한 줄 '표시 전용: 매매 판단·주문과 연결하지 않는다'.
11. `<날짜>/collected.json`: `{"schema": "llm-news-collected-1", "day", "received_at", "labels", "summaries", "errors", "dropped"}`.
12. 표준 출력 마지막 행: `llm-news <날짜> OK labels=<n> summaries=<m> errors=<e> dropped=<d>`.
- 8~11 가운데 어디서 죽어도 다음에 다시 부르면 두 번 덧붙이지 않아야 한다: 덧붙이기 전에 records.jsonl에 같은 `submitted_at`·`item_id` 줄이 이미 있으면 그 건은 건너뛴다.

### 7. main
- 인자: `--phase submit|collect`(필수), `--day YYYY-MM-DD`(없으면 오늘 KST), `--dry-run`.
- 표준 출력 마지막 행은 ASCII `llm-news <날짜> <STATUS> ...`(200자 이내). 예상 못 한 예외는 main이 잡아 `llm-news <날짜> UNEXPECTED`를 찍고 failed.md(UNEXPECTED, 예외 클래스 이름만)를 쓴다. traceback·예외 문장 없음.
- 종료 코드: `UNEXPECTED` = 1(iccheck 501행과 같게). iccheck의 `EXIT_CODES`와 같은 이름은 같은 값. `DRY_RUN` = 0. 새 이름은 `SUBMITTED`·`NO_ITEMS`·`PENDING`·`NO_BATCH`·`NOTHING_TO_COLLECT` = 0, `HALTED`·`PREREG_MISMATCH`·`MODEL_MISMATCH`·`MODEL_NOT_FOUND`·`RECORDS_BROKEN` = 10, `FETCH_FAILED` = 11, `SUBMIT_UNKNOWN` = 12.

### 8. 금지
- `os.environ`을 직접 읽지 않는다(키는 `load_key()`만). 키 값을 어떤 출력·파일·예외에도 싣지 않는다.
- 네트워크는 fetcher(yfinance)와 SDK 클라이언트 두 길뿐이다. `urllib`·`subprocess`·`socket`·`http.client`를 쓰지 않고 `requests` 모듈을 import하지 않는다.
- 계좌·보유·수량·금액 자료를 읽거나 보내지 않는다.
- 요청에 서버 대체 모델·advisor 도구·베타를 쓰지 않는다(설계서 3절).

## 시험 test_llm_pilot_news.py
- 모든 시험은 임시 폴더를 루트로 쓴다. 임시 루트에 저장소의 사전 등록 JSON을 복사해 넣는다. 가짜 fetcher·가짜 client만 쓴다(네트워크·SDK·yfinance 불필요). 가짜 키는 `load_key`를 바꿔 치거나 환경에 가짜 값(`fake-key-FOR-TEST-7Q9Z`)을 넣는다.
- 가짜 client: `messages.batches.create(requests=...)`(받은 요청을 기억, id 돌려줌), `retrieve(id)`(`processing_status`), `results(id)`(항목 목록 — `custom_id`, `result.type`, `result.message`(model·stop_reason·content·usage)).
1. **사전 등록 고정**: 저장소 JSON의 정규 해시 = `PREREG_SHA256`, 지시문 해시 = `LABEL_PROMPT_SHA256`. `universe` 30개. 한 글자를 바꾼 복사본 → `PREREG_MISMATCH` + HALT 파일 + create 안 불림.
2. **이름 지우기**(사전 등록 .md '시험' 절 그대로 + 덧붙임):
   - 대상 NBIS, 'Nvidia invests in Nebius' → '[OTHER] invests in [COMPANY]'.
   - 대상 MU: 'Micron Technology (MU)'·'NASDAQ:MU'·'Nasdaq: MU'·'(NASDAQ: MU)'·'$MU'·'MU.O' → 모두 `[COMPANY]`가 되고 'MU' 글자가 남지 않는다. 'micron-scale'은 그대로.
   - 대상 BE: 'to be or not to be'·'Be ready' 그대로, 'Bloom Energy'·'(BE)'·'NYSE: BE' → `[COMPANY]`.
   - 대상 ON: 'on track' 그대로, 'onsemi'·'ON Semiconductor' → `[COMPANY]`. 대상 ARM: 'arm of the company' 그대로, 'Arm Holdings'·'Arm' → `[COMPANY]`.
   - URL이 지워진다. 대상이 AMD일 때 홀로 선 'AMD' → `[COMPANY]`, 같은 문장의 'NVDA' → `[OTHER]`.
3. **요청 모양**: 기사 2건 → 요청 4개(`L0001`·`S0001`·`L0002`·`S0002`), create 1번. 점수 요청: system = 사전 등록 지시문, `output_config.format.schema` = 사전 등록 `label_schema`, effort low, 사용자 글에 대상 기호·별칭 없음. 요약 요청: 이름이 그대로 있고 `format` 없음. 모든 요청에 `thinking`·`temperature`·`fallbacks`·`stream`·`speed` 키 없음, model = `MODELS["news"]`.
4. **고르기**: 이미 seen인 id는 안 보냄 · 25시간 전 발행은 seen에만 들어가고 안 보냄 · 제목 빈 것 건너뜀 · 같은 id가 두 종목에 나오면 한 번만 · 요약 없는 기사는 빈 글 · 제목 301자는 300자로 · 가린 뒤에도 규칙상 가릴 것이 남게 꾸민 기사(가짜 `mask_item_text`로 한 번만 덜 가리게 함)는 `mask_leak` 1로 세고 안 보냄, 'MU'가 홀로 선 기사(대상 MU)는 그대로 보냄 · 두 yfinance 꼴 모두 정규화됨 · 시각을 못 읽는 항목은 건너뜀.
5. **한 번만 냄**: 같은 날 submit 두 번 → create 1번, 두 번째 `ALREADY_DONE`. submit-started만 있는 날 → `SUBMIT_UNKNOWN`, create 안 불림. create가 예외 → `API_ERROR`, 다시 불러도 create 안 불림. 가짜 404(모델 없음) → `MODEL_NOT_FOUND` + HALT.
6. **0건**: 새 기사 없음 → `NO_ITEMS`, create 안 불림, collect → `NOTHING_TO_COLLECT`. 30종목 모두 None → `FETCH_FAILED`.
7. **예산·키·멈춤**: usage.jsonl에 그 달 news 합계가 한도 이상 → `BUDGET_STOP`, create 안 불림. 키 없음 → `NO_KEY`. HALT 파일 있음 → `HALTED`, fetcher도 안 불림.
8. **수거 정상**: 제출 직후 records.jsonl은 머리줄 1줄이고 `start_day` = 제출일. 기사 2건 결과 → records.jsonl 3줄(머리줄 + 2), 줄 키가 사전 등록 `record.fields`와 순서까지 같다, 사슬(각 줄 `prev_sha256` = 앞 줄 sha256)이 이어진다, digest.md에 제목·요약이 있고 `good`·`bad`·`unknown`·`label`·reason 글이 없다, collected.json 있음, usage.jsonl에 batch true 한 줄(`ts_kst` 있음, 비용 = 메시지별 `estimate_cost` 합 — 입력 합이 10만을 넘는 가짜 usage로도 건별 합과 같음을 단언).
9. **수거 상태**: `processing_status` "in_progress" → `PENDING`, 아무 파일도 안 생김. 그 뒤 "ended"로 다시 → OK. collect 두 번 → 두 번째 `ALREADY_DONE`, records.jsonl 줄 수 그대로.
10. **늦게 받음**: now가 23:40 KST인 수거 → 줄이 그대로 덧붙고 `received_at`이 그 시각이다(빼거나 미루지 않음).
11. **이틀·밀린 수거**: 둘째 날 수거 뒤 머리줄은 하나, `start_day`는 첫 제출일, 사슬이 이어진다. 첫날이 PENDING으로 끝났으면 둘째 날 collect가 첫날 것을 먼저 받아 기록하고(`late=1`), 첫날 `received_at`은 둘째 날 시각이다. 4일 전 폴더는 건드리지 않는다.
12. **깨진 기록**: records.jsonl 가운데 줄 한 글자를 바꾼 뒤 수거 → `RECORDS_BROKEN` + HALT, 파일 바이트 그대로.
13. **모델 불일치**: 결과 하나의 model이 `claude-haiku-5-5-latest` → `MODEL_MISMATCH` + HALT, records.jsonl 변화 없음, **usage.jsonl에는 한 줄이 남는다**. errored 건의 오류 종류가 `not_found_error` → `MODEL_NOT_FOUND` + HALT. `claude-haiku-5-5-20261001`은 통과.
14. **건별 실패**: errored 1건·label이 "maybe" 1건·refusal 1건 → 그 건만 빠지고 나머지는 기록, 세기가 맞다. reason 500자 → 200자.
15. **다시 불러도 안전**: collected.json을 지우고 collect를 다시 → records.jsonl에 같은 줄이 두 번 생기지 않고 usage.jsonl 줄도 늘지 않는다(`usage-done`).
15-1. **수거의 다른 길**: batch.json 없음 → `NO_BATCH`(failed.md 없음) · 키 없음 → `NO_KEY` · batch.json의 prereg_sha256이 다름 → `PREREG_MISMATCH` + HALT · retrieve가 예외 → `API_ERROR`, records·usage 변화 없음.
15-2. **dry_run**: submit `--dry-run` → `DRY_RUN items=<n>`, 임시 루트에 `news` 폴더가 생기지 않고 create·클라이언트 생성 없음, 키 없이도 된다. 사전 등록이 틀린 임시 루트에서도 HALT 파일이 생기지 않는다. collect `--dry-run` → API 호출·쓰기 없음.
16. **키 없음·바깥 쓰기 없음**: 임시 루트의 모든 파일·표준 출력에 가짜 키 문자열이 없다. 생긴 파일이 모두 `workspace/outputs/llm/` 아래다. 스크립트 원문에 `environ`·`zoneinfo`·`subprocess`·`import requests`·`urllib`·`fallbacks`·`advisor` 글자가 없다.
17. **main**: `--phase` 없으면 오류 종료. 예상 못 한 예외("secret text") → 종료 1, 출력 `llm-news <날짜> UNEXPECTED`, "secret text" 없음. `month_spend`가 예외 → `BUDGET_STOP`.
- 다른 시험 파일은 바꾸지 않는다. skip 없음.
- **실행 명령은 이 한 줄만, 글자 그대로 쓴다:** `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot_news*.py"`
  - 앞에 환경 변수나 옵션을 붙이지 않는다. 전체 스위트는 파이프라인이 한다.
  - git은 status·diff·log만 쓴다. `python -c`·파이프·pip는 쓰지 않는다.
  - 저장소 루트에 대고 스크립트를 돌리지 않는다(`--dry-run` 포함). 실제 API·yfinance를 부르지 않는다.

## 지켜야 할 것
1. 위 3개 파일 밖은 손대지 않는다. 새 파일은 LF로 쓴다. 사전 등록 두 파일은 한 글자도 고치지 않는다.
2. `llm_pilot_common.py`·`llm_pilot_iccheck.py`·`llm_runner.py`·켜기 파일과 그 시험을 고치지 않는다. 공통 모듈에 필요한 것이 없으면 이 스크립트 안에 둔다.
3. 키 값을 읽으려 하지 않는다. 시험은 가짜 키만 쓴다. 비밀(.env*·토큰·계좌번호) 파일을 열지 않는다.
4. 어떤 시범도 켜지 않는다. Windows 작업을 등록·실행·변경하지 않는다.
5. 주문·키움·일지·원장·예약·정책·상태와 무관하다. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음. 주문·권한 표지 문자열을 어떤 파일에도 쓰지 않는다.
6. 사전 등록과 이 지시문이 어긋나 보이면 사전 등록 JSON이 이긴다. 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/llm-news-report.md
- (a) 만든 파일과 주요 함수(파일:행)
- (b) 시험 이름과 각 단언 요약
- (c) 시험 결과 마지막 3줄
- (d) 실행기 약속((d)절) 대조: 인자·마지막 행·두 번 불러도 한 번·failed.md·900초 안(기사 300건 기준 근거)
- (e) 사장님 첫 실행용 줄(새 PowerShell 창, 저장소 폴더): `python manage-us-stock-strategy\scripts\llm_pilot_news.py --phase submit --dry-run`(보낼 건수만 확인, 아무것도 쓰지 않음)
- (f) 확인 필요로 남은 것: yfinance가 실제로 주는 항목 꼴 · Haiku 사고 토큰으로 max_tokens가 모자라는 비율 · 하루 요청 수와 비용 · Batch에서 모델 오류가 create 예외(404)로 오는지 결과 errored로 오는지 · Batch 요청의 `output_config.format`·custom_id 규칙이 실제로 받아들여지는지(첫 실행에서 확인)
- (g) 사전 등록과 다른 점·더한 점: 사전 등록 .md '시험' 절은 '늦게 받은 결과의 표본 표시가 false'를 말하지만 원본 JSON `record.fields`에는 표본 칸이 없다 → JSON을 따라 칸을 만들지 않고 표본 판정은 채점기에 둔다. 더한 것: 기록 사슬이 깨지면 멈춤(RECORDS_BROKEN), 제목·요약 글자 수 자르기, 밀린 수거 3일.

수량·금액·키 값은 적지 않는다. 주문·권한 표지 문자열도 적지 않고 "표지 없음"이라고만 쓴다.

## 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 그림자 기록 `workspace/outputs/llm/news/records.jsonl` | Windows 작업 InvestmentV2-LLMPilots(`register_llm_pilots_task.ps1`) → `llm_runner.py` 55~56행 JOBS 칸 news-submit 19:30·news-collect 22:00·23:00 KST → 이 스크립트 | 끊김 — 182일 채점기는 아직 없다(원문 `docs/claude/llm-news-prereg-v1.json:243` `scoring.when`, `docs/claude/api-pilots-2026-11-06.md:150`). 메울 변경: 182일 채점기 작업(별도 개발 큐 작업) · 승인 경로: 사장 개발 큐 등록 | 없음(그림자). 합격해도 '카드 재검토 알림' 제안까지(별도 승인) — 사전 등록 `scoring.outcomes` | 끊김 — 실행기 하루 기록 `workspace/outputs/llm/runner/<날짜>.json`의 status와 `news/<날짜>/failed.md`·`news/HALT`는 남지만 이를 읽는 예약이 없다. 메울 변경: 사장실 '결과 모음' 예약이 실행기 하루 기록을 읽게 하는 것(예약 작업 변경 승인 경로, 이 작업 밖 — 시범 켜기 제안 때 함께 올린다) | 소비자 예정(시작 + 182일) — 그때까지 화면 연결 없음 |
| 표시용 요약 `news/<날짜>/digest.md` | 같은 수거 | 사람 단계 — 자동으로 읽는 쪽 없음(원문 `docs/claude/api-pilots-2026-11-06.md:150` '사장실 지정 시 표시, 지정 전에는 이 스레드 확인용'). 사장실 지정은 별도 승인 | 없음(표시 전용) | 끊김 — 1행 ⑤와 같은 메울 변경 | 표시만 |
| 사용량 `workspace/outputs/llm/usage.jsonl` 줄(pilot news) | 같은 수거 | 이 스크립트 제출 단계 `month_spend` 예산 검사 — `manage-us-stock-strategy/scripts/llm_pilot_news.py:436-442` | 월 한도에 닿으면 제출 멈춤(`BUDGET_STOP`) | 끊김 — 실행기 하루 기록 status BUDGET_STOP을 읽는 예약이 없다. 1행 ⑤와 같은 메울 변경 | 연결(예산 검사) · 알림 끊김 |

## Judge 확인 항목
1. diff가 허용 파일 3개뿐이고 모두 새 파일이다. 사전 등록 두 파일·켜기 파일·공통 모듈 변화 없음.
2. 대상·별칭·가리기·지시문·스키마를 사전 등록 JSON에서만 읽고, 해시 두 개가 다르면 HALT한다. 시험이 저장소 JSON으로 해시를 단언한다.
3. 점수 요청에 대상 이름·기호가 남지 않는다(가린 뒤 재검사 포함). 요약 요청과 점수 요청이 분리돼 있고 digest에 label이 없다.
4. 한 날 create는 한 번뿐이다(submit-started, ALREADY_DONE, 예외 뒤 재실행 시험).
5. records.jsonl: 키가 사전 등록 `record.fields` 그대로, 사슬 검사 뒤 덧붙이기만, 깨지면 HALT, 다시 불러도 중복 없음, 늦은 수신도 기록.
6. 모델 검사(`check_message`)·404·사전 등록 불일치에서 멈추고 그 뒤 submit이 HALTED다.
7. 키: `load_key`만 쓰고 값이 어디에도 없다. 요청에 대체 모델·advisor·베타·캐시 표지 없음.
8. 쓰기는 `workspace/outputs/llm/` 아래뿐이다. 계좌·보유 자료를 읽지 않는다. `zoneinfo` 없음.
9. 시험이 실제로 각 경로를 만든다(항상 참 단언 아님). 네트워크 없음. 기존 시험 변경 없음. 새 실패 0.
10. 보고서 (a)~(f) 있음. 수량·금액·키 값·표지 없음.

```dev-run
{"task_id": "llm-news2", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 150, "builder_timeout_min": 90, "allowed_paths": ["manage-us-stock-strategy/scripts/llm_pilot_news.py", "manage-us-stock-strategy/tests/test_llm_pilot_news.py", "docs/claude/llm-news-report.md"], "target_tests": ["test_llm_pilot_news*.py"], "commit_message": "feat(llm-pilot): news digest and anonymized shadow labels via Message Batches, submit and collect phases (off by default, llm-news2 - retry of llm-news with fixed linkage table)"}
```
