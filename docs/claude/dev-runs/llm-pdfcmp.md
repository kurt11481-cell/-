# dev-run llm-pdfcmp — READY_TO_MERGE

- 시각(UTC): 2026-11-25T00:35:18Z → 2026-11-25T01:04:12Z
- 기준 커밋(base): `113727c5d66bb4d47c081d33e3a5af18121171ed` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **READY_TO_MERGE** · 재시도: 0
- 테스트: 기준선 Ran 3838 · 실패 3 → 변경 후 Ran 3881 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `b03a782e3d922f3fdb1407779e6bce002715d555f7f7a6fda3f265d639422b2c`
- Judge 파일 sha256: `415ea8eb467a9c585608ddbcf6830441bcd081de89cb9a516e400c7872aa9731`
- 사유: BASELINE_FAILURES_ROSE:fbca393e:+1
- 다음: `.\tools\dev-merge.ps1 llm-pdfcmp`

## 바뀐 파일

- `docs/claude/llm-pdfcmp-report.md`
- `manage-us-stock-strategy/scripts/llm_pilot_pdfcmp.py`
- `manage-us-stock-strategy/tests/test_llm_pilot_pdfcmp.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `manage-us-stock-strategy/scripts/llm_pilot_pdfcmp.py:402-496`: 제출 단계. PDF 확인 → 키 → 월 예산 → `<pid>.pdf` 이름으로 올리기 → Batch 1개 → `batch.json` 순서로 진행한다. `:653-827`: 수거 단계. ended 확인 → usage 기록 → 4줄 파싱·인용 확인 → `compare.json`·`compare.md` → 파일 delete → compare 다시 쓰기 순서다. `:192-217`: 분류 지침이 `external-claims-ledger.md:23-26`(규칙 1·3·4)과 같은 뜻이다. TODO나 시험만 통과시키는 하드코딩은 없다 |
| G2 범위 | PASS | `changed-files.txt:1-3`: 새 파일 3개이고 allowed_paths와 같다. `checks.json:22-24`: 수정·삭제 없음 |
| G3 주문·키움·체결 추정 | PASS | 스크립트 전문(`:1-867`)에 주문 경로, 키움 호출, 체결 추정이 없다. 금지어 시험은 `test_llm_pilot_pdfcmp.py:725-739` |
| G4 정책·상태 쓰기, fail-closed | PASS | 쓰기는 `workspace/outputs/llm/` 아래뿐이다(`:491`, `:649-650`, `:731-732`, `llm_pilot_common.py:323-328`·`:369-370`). 없는 PDF·sha 다름 → skipped/HOLD(`:318-344`, `:431-433`). usage를 못 읽으면 BUDGET_STOP(`:441-444`). 결과 없음·오류는 불일치로 센다(`:760-776`) |
| G5 비밀·계좌 식별자 | PASS | 키는 `load_key`에서 factory로만 넘어간다(`:436-450`, `:685-690`). 오류는 `api_error_label`만 기록한다(`:465`, `:473`). 시험 `test_llm_pilot_pdfcmp.py:682-694`: 가짜 키가 stdout·stderr·모든 출력 파일에 없음을 단언한다 |
| G6 단언 약화·skip, 새 동작 시험 | PASS | 기존 시험 변경 없음. skip·expectedFailure 없음(diff.patch). 대상 시험 43개 OK, `new_failures` [](`checks.json:84-97`). 전체 실패 3건은 기준선과 같고 이번 변경과 무관하다 |
| G7 class | PASS | `BUDGET_USD_MONTH`는 읽기만 한다(`:445`). 권한 표지·주문 단계·상한 변경 없음. class_ok=true |
| G8-1 허용 파일 3개만 | PASS | `changed-files.txt:1-3`. 실행기·공통 모듈·켜기 파일·원장·고르기 기록은 바뀌지 않았다 |
| G8-2 정답표 | PASS | 스크립트 `:110,118,126,134,143,151,158,165,173,183`의 sha256과 정답(P01~P05 CAND, P06~P10 R0)이 `task-prompt.md:34-43`과 글자 그대로 같다. 시험 `:741-748`이 지시문 표를 직접 읽어 대조한다 |
| G8-3 한 번만, 8개 미만이면 호출 0 | PASS | `:421-424`: compare 있으면 DONE_ALREADY, batch 있으면 PENDING. `:431-433`: 8개 미만이면 HOLD이고 호출 0. 수거 쪽은 `:669-670`. 시험 `:322-337`, `:372-388` |
| G8-4 외부자료 폴더 읽기만 | PASS | 폴더에는 `is_file`·`stat`·`read_bytes`만 쓴다(`:318-344`). `unlink`는 `llm` 아래 `failed.md` 하나뿐이다(`:394-397`) |
| G8-5 모델 고정·예산·삭제 | PASS | 모델 고정 `:364`, `check_message` `:769`. 대체 모델·advisor·베타가 없다(`:360-380`). 예산 확인(`:440-446`)이 올리기(`:452`)보다 앞이다. 수거 뒤 delete(`:821`) |
| G8-6 키·금지어·ASCII·새 실패·보고서 | PASS | 시험 `:682-694`, `:725-732`. 새 실패 0. 보고서 (a)~(e)는 `llm-pdfcmp-report.md:7-77`에 있다. 권한 표지 문자열·CR 0건(Grep) |
| G9 연결표 | PASS | ② `llm_runner.py:53-54`(pdfcmp-submit 13:10, pdfcmp-collect 15:10/17:10)와 칸 내용이 맞다. ③ `api-pilots-2026-11-06.md:163` "소비자: 이 스레드의 1회 비교 기록"과 맞다. ⑤ "끊김(…)" 형식이고 메울 변경과 승인 경로가 적혀 있다 |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_pdfcmp.py:402-496, :653-827, :192-217 vs docs/claude/external-claims-ledger.md:23-26"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/llm-pdfcmp/changed-files.txt:1-3; checks.json:22-24"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_pdfcmp.py:1-867 (no order/kiwoom/fill inference); tests/test_llm_pilot_pdfcmp.py:725-739"}, {"id": "G4", "result": "PASS", "evidence": "llm_pilot_pdfcmp.py:491, :649-650, :731-732; llm_pilot_common.py:323-328, :369-370; fail-closed :318-344, :431-433, :441-444, :760-776"}, {"id": "G5", "result": "PASS", "evidence": "llm_pilot_pdfcmp.py:436-450, :465, :473, :685-690; tests/test_llm_pilot_pdfcmp.py:682-694"}, {"id": "G6", "result": "PASS", "evidence": "checks.json:84-97 (43 target tests OK, new_failures []); no skip/expectedFailure in diff.patch"}, {"id": "G7", "result": "PASS", "evidence": "llm_pilot_pdfcmp.py:445 (budget constant read only); no authority/limit change"}, {"id": "G8.1", "result": "PASS", "evidence": "changed-files.txt:1-3"}, {"id": "G8.2", "result": "PASS", "evidence": "llm_pilot_pdfcmp.py:110-183 vs task-prompt.md:34-43; tests/test_llm_pilot_pdfcmp.py:741-748"}, {"id": "G8.3", "result": "PASS", "evidence": "llm_pilot_pdfcmp.py:421-424, :431-433, :669-670; tests/test_llm_pilot_pdfcmp.py:322-337, :372-388"}, {"id": "G8.4", "result": "PASS", "evidence": "llm_pilot_pdfcmp.py:318-344, :394-397"}, {"id": "G8.5", "result": "PASS", "evidence": "llm_pilot_pdfcmp.py:364, :769, :360-380, :440-446 before :452, :821"}, {"id": "G8.6", "result": "PASS", "evidence": "tests/test_llm_pilot_pdfcmp.py:682-694, :725-732; docs/claude/llm-pdfcmp-report.md:7-77"}, {"id": "G9", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_runner.py:53-54; docs/claude/api-pilots-2026-11-06.md:163; task-prompt.md:82 cell 5 is a declared break with closing change"}], "min_fixes": []}
```
VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-11-25T02:14:56Z
- 병합 커밋: `f184e564d9743543fa94f1a9595ecf4e960c713e` · 방식: ff

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/llm-pdfcmp/ 의 원본 기록입니다.)
