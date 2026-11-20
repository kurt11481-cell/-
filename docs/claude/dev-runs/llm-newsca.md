# dev-run llm-newsca — READY_TO_MERGE

- 시각(UTC): 2026-11-20T11:05:24Z → 2026-11-20T11:31:24Z
- 기준 커밋(base): `fbca393e8a7e9eb3d71e979f4f7a8fb7886cd583` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **READY_TO_MERGE** · 재시도: 0
- 테스트: 기준선 Ran 3827 · 실패 2 → 변경 후 Ran 3838 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `b31e125e1b1346adf314a86a26a408512bdc8ed41b6e9db62d6a3a928021c2ae`
- Judge 파일 sha256: `42fee6b66305317b34783a91a2213b09f5d1e426335206c66180306d9ab9bb61`
- 사유: 없음
- 다음: `.\tools\dev-merge.ps1 llm-newsca`

## 바뀐 파일

- `docs/claude/llm-newsca-report.md`
- `manage-us-stock-strategy/scripts/llm_pilot_news.py`
- `manage-us-stock-strategy/tests/test_llm_pilot_news.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `llm_pilot_news.py:72-75`: 상수 2개와 `_FETCH_STATE`가 있습니다. `:328-360`의 `ascii_ca_bundle`은 지시문 그대로 동작합니다(원본이 ASCII면 None, 복사 폴더가 비ASCII면 None, 매 호출 바이트 대조 후 다르면 다시 씀, OSError면 None). `:310-325`는 임시 파일 → `os.fsync` → `os.replace` 순서로 씁니다. `:363-375`의 `default_fetcher`는 `ascii_ca_bundle`을 한 번 부르고, 세션 1개에 `verify=<복사본 경로>`를 주고 `Ticker(symbol, session=...)`를 부릅니다. 하드코딩과 TODO는 없습니다. |
| G2 범위 | PASS | `changed-files.txt:1-3` = allowed_paths 3개. `checks.json:17-21`의 changed_paths도 같은 3개이고 reasons는 비었습니다. 시험 diff는 `test_llm_pilot_news.py:1077` 뒤에 더한 줄뿐입니다. |
| G3 주문·키움·체결 추정 없음 | PASS | diff.patch를 order·kiwoom으로 검색해 0건 |
| G4 정책·상태 쓰기 없음, fail-closed | PASS | 새로 쓰는 곳은 `CA_COPY_DIR/CA_COPY_NAME`과 같은 폴더의 `.tmp`뿐입니다(`llm_pilot_news.py:312,318,348`). 복사에 실패하면 None을 돌려 기존 동작으로 돌아가고, 오류는 지금처럼 fetch-errors.json에 남습니다. 세션 예외는 삼키지 않습니다(`:372-374` → `:403-409`). |
| G5 비밀 없음 | PASS | diff에 .env, 토큰, 계좌, environ 접근이 없습니다(diff.patch 검색 0건). |
| G6 단언 약화 없음, 새 동작마다 시험 | PASS | 기존 시험은 바뀌지 않았고 덧붙이기만 했습니다(diff 116-252행). 새 시험 11개(`test_llm_pilot_news.py:1080-`). checks.json의 new_failures는 [], targets 72 OK, EXPECTED_FAILURES_INCREASED 없음(`checks.json:83-95`). certifi import 실패 분기는 시험이 없지만, 지시문이 시험은 src를 넘기라고 정해 둔 범위입니다. |
| G7 class | PASS (class_ok=true) | 주문 단계, 도구, 예산, 상한, 승인 상품, 대조 불변 조건, 정지 스위치에 변경이 없습니다. quantity_authority 추가도 없습니다(diff 검색 0건). |
| G8-1 허용 파일 3개, CRLF | PASS | 두 기존 파일에서 CR 없는 줄바꿈은 0건이고, 새 줄도 `\r\n`입니다(`llm_pilot_news.py:328`, `test_llm_pilot_news.py:1080`). checks.json reasons는 비었습니다. 보고 (c)의 두 stat이 같습니다(`llm-newsca-report.md:37-48`). |
| G8-2 검증 끄기 없음, 매 프로세스 대조 | PASS | verify에는 `ascii_ca_bundle`이 돌려준 `str(target)`만 들어갑니다(`llm_pilot_news.py:360,374`). 바이트 대조는 `:351-357`에 있고, "있으면 그대로 씀" 지름길은 없습니다. `verify=False`가 없음을 시험이 단언합니다(`test_llm_pilot_news.py` `test_ca_copy_constants_and_no_verify_off`). |
| G8-3 원본이 ASCII면 기존 동작 | PASS | `llm_pilot_news.py:341-342,369-370`. 시험 `test_ascii_ca_bundle_ascii_source_returns_none`(`test_llm_pilot_news.py:1098-1102`)과 `test_default_fetcher_plain_ticker_when_none`이 이를 단언합니다. |
| G8-4 쓰기 범위·docstring, 시험이 ProgramData에 안 씀 | PASS | docstring은 `llm_pilot_news.py:15-18`입니다. `ascii_ca_bundle` 호출 9곳(`test_llm_pilot_news.py:1101-1144`)이 모두 `copy_dir`을 넘깁니다. setUp에서 `contextlib.chdir`로 임시 폴더로 옮깁니다. `default_fetcher` 시험 3개는 `ascii_ca_bundle`을 가짜로 바꾸고 `_FETCH_STATE`를 비웁니다. 기존 시험은 모두 Fetcher 가짜를 씁니다(`:213`, `:1044`). |
| G8-5 출력·종료 코드 그대로, 금지어 없음 | PASS | `fetch_items_detail`, `run_submit`, `EXIT_CODES`, `REASON_KO`는 diff 밖입니다. `test_script_source_contract`(`test_llm_pilot_news.py:1003-1008`)를 포함해 72개가 OK입니다. |
| G8-6 기존 시험 무변경, 보고 (a)~(f), 표지 없음 | PASS | 보고 `llm-newsca-report.md`에 (a)~(f)가 모두 있습니다. 표지 문자열은 검색 0건입니다. 보고가 docstring을 "14~18행"이라 적었는데 실제는 15~18행입니다. 판정에는 영향이 없습니다. |
| G9 연결표 | PASS | ② `llm_runner.py:55`는 news-submit 19:30 줄과 맞습니다. ③ `backlog-review-2026-11-19.md:82-83`은 스레드가 fetch-errors.json을 읽은 줄과 맞습니다. ⑤는 '끊김'으로 적었고 메울 변경과 승인 경로가 있으며, 근거 `llm-news2-builder-prompt.md:186`과 맞습니다. |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_news.py:72-75,310-375"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/llm-newsca/changed-files.txt:1-3; checks.json:17-21"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/llm-newsca/diff.patch (order/kiwoom 0 matches)"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_news.py:312,318,348,358-359,403-409"}, {"id": "G5", "result": "PASS", "evidence": "workspace/outputs/dev-runs/llm-newsca/diff.patch (environ/secret 0 matches)"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_llm_pilot_news.py:1077-1205; checks.json:83-95"}, {"id": "G7", "result": "PASS", "evidence": "workspace/outputs/dev-runs/llm-newsca/diff.patch (quantity_authority 0 matches); checks.json:61-62"}, {"id": "G8", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_news.py:15-18,341-374; manage-us-stock-strategy/tests/test_llm_pilot_news.py:1003-1008,1098-1205; docs/claude/llm-newsca-report.md:1-72"}, {"id": "G9", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_runner.py:55; docs/claude/backlog-review-2026-11-19.md:82-83; docs/claude/llm-news2-builder-prompt.md:186"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-11-20T12:22:29Z
- 병합 커밋: `027e0e4ba7444357140993d7e1f41a288824c099` · 방식: ff

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/llm-newsca/ 의 원본 기록입니다.)
