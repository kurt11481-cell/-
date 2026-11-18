# dev-run llm-news — BLOCKED

- 시각(UTC): 2026-11-18T02:35:05Z → 2026-11-18T03:05:10Z
- 기준 커밋(base): `d8fd070c5cd163fbca9555a4b0c116115592283d` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **BLOCKED** · 재시도: 1
- 테스트: 기준선 Ran 3689 · 실패 2 → 변경 후 Ran None · 새 실패 0 · skipped 3->None · 스키마 감사 PASS->None
- diff_hash: `None`
- Judge 파일 sha256: `None`
- 사유: Judge min_fixes target docs/claude/llm-news-builder-prompt.md:181-183 (base commit), which is outside allowed_paths; a Builder retry cannot fix it.
- 다음: `see docs/claude/dev-runs/llm-news.md`

## 바뀐 파일

- (없음)

## Judge 보고 원문 (1회차 FAIL)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `llm_pilot_news.py:398-561`에 제출 1~13단계가 있다. `:638-819`는 수거 1~12단계로, 사용량을 먼저 남기고(`:691-718`) 사슬을 검사한 뒤 한 번에 덧붙인다(`:763-797`). 밀린 수거 3일은 `:822-852`, main은 `:857-880`. 빈 껍데기, 하드코딩, 남은 TODO 없음. |
| G2 범위 | PASS | `changed-files.txt:1-3`은 모두 새 파일(A)이고 `task-prompt.md:198`의 allowed_paths 3개와 같다. checks.json `changed_paths`도 3개뿐이다. |
| G3 주문·체결 추정 없음 | PASS | 네트워크는 두 길뿐이다: `default_fetcher`(`:261-264`, yfinance)와 SDK `batches.create/retrieve/results`(`:517`, `:677-685`). diff에 키움, 주문, 체결 추정 코드가 없다. |
| G4 정책·상태 쓰기 없음, fail-closed | PASS | 쓰기는 `news_dir` 아래(`:142-159`)와 `append_usage`(common `:323-328`, `llm/usage.jsonl`)뿐이다. 실패는 모두 닫힌 쪽이다: `month_spend` 예외→BUDGET_STOP(`:437-440`), 사전 등록 불일치→HALT(`:426-428`, `:660-664`), 사슬 깨짐·파일 없음→HALT(`:764-769`). |
| G5 비밀 없음 | PASS | 키는 `load_key()`로만 읽고(`:433`, `:668`) 클라이언트를 만든 뒤 `key = None`(`:514`, `:674`)으로 지운다. 실패 이유에는 예외 클래스 이름과 HTTP 코드만 쓴다(common `:105-110`). 시험 `test_llm_pilot_news.py:875-887`이 모든 파일·출력·요청에 가짜 키가 없음을 단언한다. |
| G6 시험 | PASS | 새 시험 53개, skip·expectedFailure 없음. checks.json targets는 ran 53·OK, `new_failures` []. 전체 실패 2건(scheduler·SOXL 등록부)은 이 diff와 무관하다. |
| G7 class | PASS | 주문 단계, 예산, 상한, quantity_authority 변경 없음. `BUDGET_USD_MONTH`는 읽기만 한다(`:441`). class_ok=true. |
| G8-1 허용 3개·새 파일 | PASS | `changed-files.txt:1-3`. 사전 등록, 켜기 파일, 공통 모듈 변경 없음. |
| G8-2 사전 등록에서만 읽기, 해시 | PASS | `:193-205`가 정규 해시와 지시문 해시를 둘 다 본다. 종목·별칭·규칙은 `:210-249`가 JSON에서 읽는다. 시험 `:269-281`이 저장소 JSON으로 해시를 단언하고, 한 글자를 바꾸면 HALT임을 `:283-297`이 본다. |
| G8-3 가리기, 요청 분리, digest | PASS | 가린 뒤 다시 검사한다(`:490-499`). L/S 요청이 분리돼 있다(`:370-394`). digest에 label이 없다(`:609-625`). 시험 `:395-402`·`:468-491`·`:656-658`. |
| G8-4 하루 create 한 번 | PASS | `:419-423`, `:515-521`. 시험 `:531-561`. |
| G8-5 records | PASS | 칸은 `prereg.record.fields` 순서 그대로다(`:770`, `:792`). 사슬을 검사한 뒤 "a" 모드로 한 번 쓴다(`:767-797`). 같은 줄은 건너뛴다(`:777`). 늦게 받은 결과도 기록한다(시험 `:695-703`). |
| G8-6 멈춤 뒤 HALTED | PASS | 멈추는 곳: 수거 중 not_found·MODEL_MISMATCH(`:724-727`), 제출 404(`:519-520`), 사전 등록 불일치(`:428`, `:664`). 그 뒤 HALTED(`:416-417`). 시험 `:296`·`:560`·`:773`. |
| G8-7 키·요청 표지 | PASS | 금지 키가 요청에 없음(시험 `:389`). 원문 금지어 없음(`:889-894`). |
| G8-8 쓰기 위치, zoneinfo | PASS | 시험 `:881-884`(모든 파일이 `workspace/outputs/llm/` 아래)와 `:892`. |
| G8-9 시험 실효성 | PASS | 가짜 fetcher·client로 각 경로를 실제로 만든다. 기존 시험 변경 없음. 새 실패 0. |
| G8-10 보고서 | PASS | `llm-news-report.md`에 (a)~(g)가 있다. (a)의 행 번호는 실제와 맞다(193·210·252·261·267·299·362·398·566·638·822·857행). 수량·금액·키·표지 없음. |
| G9 연결표 | FAIL | `task-prompt.md:181-183`. 맞는 칸은 1행 ②(`llm_runner.py:55-56` JOBS news-submit/collect와 일치)와 1행 ⑤('끊김'과 메울 변경·승인 경로)뿐이다. 나머지 네 칸은 파일:줄도 '끊김(…)'도 아니다. (1) 1행 ③은 아직 없는 채점기를 이름으로만 적었고 '끊김'·승인 경로가 없다(원문은 `llm-news-prereg-v1.json:243`, `api-pilots-2026-11-06.md:150`). (2) 2행 ③은 '설계서 4절'로만 적었다. 실제 소비자는 자동 읽기가 아니라 사장실이 직접 보는 것이다(`api-pilots-2026-11-06.md:150`). (3) 3행 ⑤의 '실행기 하루 기록 status'는 같은 표 1행 ⑤가 '읽는 예약이 없다(끊김)'고 적은 그 기록이다. 끊김이 연결처럼 보인다. 저장소에도 이 기록을 읽는 예약 지시문이 없다. (4) 3행 ③은 내용이 diff `llm_pilot_news.py:436-442`와 맞지만 이름으로만 적었다. |

```json
{"verdict": "FAIL", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_news.py:398-561,638-852,857-880"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/llm-news/changed-files.txt:1-3; task-prompt.md:198"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_news.py:261-264,517,677-685"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_news.py:142-159,426-428,437-442,764-769; llm_pilot_common.py:323-328"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_news.py:433,514,668,674; manage-us-stock-strategy/tests/test_llm_pilot_news.py:875-887"}, {"id": "G6", "result": "PASS", "evidence": "workspace/outputs/dev-runs/llm-news/checks.json:88-96 (ran 53 OK, new_failures [])"}, {"id": "G7", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_news.py:441 (BUDGET_USD_MONTH read only); no quantity_authority in diff"}, {"id": "G8", "result": "PASS", "evidence": "items 1-10: llm_pilot_news.py:193-205,490-499,419-423,515-521,566-586,763-797,724-727; test_llm_pilot_news.py:269-297,389,395-402,531-561,695-703,764-773,875-894; docs/claude/llm-news-report.md (a)-(g)"}, {"id": "G9", "result": "FAIL", "evidence": "workspace/outputs/dev-runs/llm-news/task-prompt.md:181-183 (row1 col3, row2 col3, row3 col3 and col5 not file:line nor 끊김; row3 col5 contradicts row1 col5); llm_runner.py:55-56 row1 col2 ok"}], "min_fixes": ["연결표 1행 ③(task-prompt.md:181): 아직 없는 182일 채점기를 '끊김 — 메울 변경: 182일 채점기 작업 · 승인 경로'로 적고 원문 행 llm-news-prereg-v1.json:243, api-pilots-2026-11-06.md:150을 붙인다", "연결표 2행 ③(task-prompt.md:182): '설계서 4절'을 api-pilots-2026-11-06.md:150으로 바꾸고, 자동 읽는 쪽이 없으므로 '사람 단계' 또는 '끊김(사장실 지정 전 — 메울 변경·승인 경로)'으로 적는다", "연결표 3행 ⑤(task-prompt.md:183): 실행기 하루 기록은 읽는 예약이 없으므로(1행 ⑤와 같음) '끊김 — 1행 ⑤와 같은 메울 변경'으로 적고, 3행 ③에 diff 원문 행 manage-us-stock-strategy/scripts/llm_pilot_news.py:436-442를 붙인다", "고칠 곳은 지시문 docs/claude/llm-news-builder-prompt.md:181-183(기준 커밋, allowed_paths 밖)이다. Builder의 세 파일(스크립트·시험·보고서)은 고칠 것이 없다. Builder 재시도로는 고칠 수 없으므로 Cowork가 지시문 연결표를 고친 뒤 다시 판정한다"]}
```
VERDICT: FAIL

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/llm-news/ 의 원본 기록입니다.)
