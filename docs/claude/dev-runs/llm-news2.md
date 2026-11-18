# dev-run llm-news2 — READY_TO_MERGE

- 시각(UTC): 2026-11-18T04:00:12Z → 2026-11-18T04:33:22Z
- 기준 커밋(base): `8b1cace51c512c12e5209d5e53da5365570d7627` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **READY_TO_MERGE** · 재시도: 0
- 테스트: 기준선 Ran 3689 · 실패 2 → 변경 후 Ran 3739 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `5f0ffe2d57911cf51eafa50cc0b04353087426b84bb8cfea72d62559414313f2`
- Judge 파일 sha256: `4dc5f95786e5cec547afb94ce06af2f87c64ffe8d7b209fdff840e916722293a`
- 사유: 없음
- 다음: `.\tools\dev-merge.ps1 llm-news2`

## 바뀐 파일

- `docs/claude/llm-news-report.md`
- `manage-us-stock-strategy/scripts/llm_pilot_news.py`
- `manage-us-stock-strategy/tests/test_llm_pilot_news.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `llm_pilot_news.py:212` load_prereg(정규 해시·지시문 해시 확인), `:287` 이름 지우기, `:343` 두 가지 yfinance 꼴, `:391-562` 제출 1~13단계 순서대로, `:567` 점수(L)·요약(S) 요청 짝, `:707-903` 수거(6-1 사용량 먼저 남김 `:767-797`, 기록 사슬 검사 `:851`, 한 번에 덧붙이기 `:879-881`), `:913-948` 밀린 수거 3일, `:953` main. TODO·하드코딩 없음(`:910` pass는 failed.md 쓰기 실패를 삼키는 의도된 줄) |
| G2 범위 | PASS | `changed-files.txt:1-3` 새 파일(A) 3개가 allowed_paths와 같음. `checks.json:17-21,53` 수정 0건. 부수 변경 없음 |
| G3 주문·키움·체결 추정 | PASS | diff에 kiwoom·order 경로 없음. 시험 `test_llm_pilot_news.py:852-854`가 원문에 auto_core·kiwoom 글자가 없음을 단언. 네트워크는 fetcher(`:297-300`)와 SDK 클라이언트 둘뿐 |
| G4 정책·상태 쓰기 / fail-closed | PASS | 쓰기는 모두 `llm_dir(root)/news`(`:143-160`)와 `append_usage`(common `:77,323`) 아래. 사용 기록을 못 읽으면 BUDGET_STOP(`:437-440`), records.jsonl이 없거나 깨지면 RECORDS_BROKEN과 HALT(`:613-644`, `:851-853`), seen.json을 못 읽으면 예외로 UNEXPECTED(`:377-380`). 시험 `:840-847`이 쓰기 경로를 단언 |
| G5 비밀·계좌 | PASS | 키는 `load_key()`로만 읽어 factory에만 넘기고 바로 None으로 비움(`:431, :511-512`, `:744-749`). 원문에 environ 없음(`test:852`). 가짜 키가 어떤 파일·출력에도 없음(`test:249-254, :840-843`). 예외 문장은 남기지 않고 `api_error_label`(클래스 이름과 HTTP 코드)만 남김(common `:105-110`) |
| G6 시험 | PASS | skip·expectedFailure 없음(Grep 결과 0건). 지시문 시험 1~17·15-1·15-2가 모두 있음(`test:257-920`). `checks.json:86-95` 대상 시험 50개 OK, `:82` new_failures 없음(전체 실패 2건은 기준선 failure_count 2와 같음, `:4`) |
| G7 class | PASS (class_ok=true) | quantity_authority·예산·상한·주문 단계 변경 없음. `BUDGET_USD_MONTH`는 common `:27`에서 읽기만 함. `checks.json:60-61` class general, class_reasons 없음 |
| G8 Judge 확인 항목 1~10 | PASS | 1: `changed-files.txt`. 2: `:212-227`, `:254-284`(종목 목록은 사전 등록 JSON에서만 읽음), `test:257-266`. 3: `:477-493` 가린 뒤 다시 검사, `test:384-392`, digest에 label 없음(`test:605-606`). 4: `:413-418, :516-518`, `test:459-493`. 5: `:856-881`, `test:587, :694-713, :771-778, :649-656`. 6: `:425, :521, :827`, 그 뒤 HALTED(`test:282, :492, :727`). 7: `test:375, :852`. 8: `test:844-847`, zoneinfo 없음. 9: 가짜 fetcher·client만 사용, `checks.json:82`. 10: 보고 (a)~(g) 있고, 금액·키 값·표지 없음 |
| G9 연결표 | PASS | ②: 1행 `llm_runner.py:55-56`(news-submit 19:30, news-collect 22:00·23:00)이 원문과 같음. 2·3행의 '같은 수거'는 이 1행 인용(`:56`)을 가리키고, 실제로 수거 단계가 digest(`llm_pilot_news.py:884`)와 사용량(`:796`)을 씀. ③: 1행은 '끊김'과 함께 메울 변경·승인 경로를 적었고, 인용한 `llm-news-prereg-v1.json:243`(scoring.when)과 `api-pilots-2026-11-06.md:150`(소비자) 모두 원문과 같음. 2행 `api-pilots:150`도 같음. 3행 `llm_pilot_news.py:436-442`는 diff 547~553행 기준으로 month_spend 예산 검사와 같음. ⑤: 3행 모두 '끊김'과 메울 변경을 적었고, 실행기 하루 기록 경로는 `llm_runner.py:142`와 같음 |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_news.py:212,287,391-562,707-903,913-948"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/llm-news2/changed-files.txt:1-3; checks.json:53"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_llm_pilot_news.py:852-854; llm_pilot_news.py:297-300"}, {"id": "G4", "result": "PASS", "evidence": "llm_pilot_news.py:143-160,437-440,613-644,851-853; test_llm_pilot_news.py:840-847"}, {"id": "G5", "result": "PASS", "evidence": "llm_pilot_news.py:431,511-512,744-749; test_llm_pilot_news.py:249-254,852; llm_pilot_common.py:105-110"}, {"id": "G6", "result": "PASS", "evidence": "test_llm_pilot_news.py:257-920; checks.json:82,86-95"}, {"id": "G7", "result": "PASS", "evidence": "checks.json:60-61; llm_pilot_common.py:27 (read only)"}, {"id": "G8", "result": "PASS", "evidence": "task-prompt.md:190-200 items 1-10 vs llm_pilot_news.py:212-227,413-418,477-493,516-518,856-881; test_llm_pilot_news.py:282,384-392,459-493,587,605-606,694-713,727,844-847"}, {"id": "G9", "result": "PASS", "evidence": "task-prompt.md:186-188 vs manage-us-stock-strategy/scripts/llm_runner.py:55-56,142; docs/claude/llm-news-prereg-v1.json:243; docs/claude/api-pilots-2026-11-06.md:150; diff.patch:547-553 (llm_pilot_news.py:436-442)"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-11-18T04:55:46Z
- 병합 커밋: `905572e66b8d647e3cee38ec70b2a25eff3b124c` · 방식: ff

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/llm-news2/ 의 원본 기록입니다.)
