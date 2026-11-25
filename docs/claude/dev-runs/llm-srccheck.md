# dev-run llm-srccheck — NEEDS_APPROVAL

- 시각(UTC): 2026-11-25T07:30:17Z → 2026-11-25T07:59:20Z
- 기준 커밋(base): `4b2cd355cfa163b5f16d6bb0cfc1c2dba1205298` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: ADDED_LINE:quantity_authority, JUDGE_CLASS_OK_FALSE)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3928 · 실패 5 → 변경 후 Ran 3972 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `579d58aff377367fd540122b90ffcdb10eb528fcbb025c53fe6ee63e167763c2`
- Judge 파일 sha256: `7137d0ef7798de46b336e3bb68f7209624ede0ebc4a058e9e852ba9210eb0bc8`
- 사유: BASELINE_FAILURES_ROSE:113727c5:+2
- 다음: `user decision, then .\tools\dev-merge.ps1 llm-srccheck -ApproveAuthority`

## 바뀐 파일

- `docs/claude/llm-srccheck-report.md`
- `manage-us-stock-strategy/scripts/llm_pilot_srccheck.py`
- `manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py`

## Judge 보고 원문 (1회차 PASS)

Judge 판정을 마쳤습니다. 결과는 **PASS**이고, class_ok는 **false**입니다(G7 줄 참고).

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `llm_pilot_srccheck.py`: 대상 고르기 372-527, 제출 579-660, 판정 676-782, 수거 847-987, main 999. 연구 기록·SEC 칸 이름은 스키마 원문과 같음(`auto-core-research-record.schema.json:22-26,39-49`, `sec-official-normalized-events.schema.json:35-44,49`). 빈 껍데기, TODO, 하드코딩 없음. 시험 44건 OK(`checks.json:95-102`) |
| G2 범위 | PASS | `changed-files.txt:1-3`은 새 파일 3개뿐이고 allowed_paths와 같음. `checks.json:23-24,54` modified·deleted 없음, `checks.json:68` reasons 비어 있음 |
| G3 주문·키움·체결 추정 없음 | PASS | 가져오는 모듈은 argparse·difflib·json·re·sys·datetime·pathlib·llm_pilot_common뿐(`llm_pilot_srccheck.py:26-54`). 네트워크 호출은 `client.messages.batches.create/retrieve/results` 하나(639, 891, 898). 금지어 시험 `test_llm_pilot_srccheck.py:985` |
| G4 정책·상태 쓰기 없음, fail-closed | PASS | 쓰는 곳은 `workspace/outputs/llm/srccheck/` 아래와 `usage.jsonl`뿐(657-658, 871, 939-945). 사용 기록을 못 읽으면 BUDGET_STOP(616-619), seen이 깨지면 UNEXPECTED(490-504). 깨진 파일은 skipped에 남김(380, 439) |
| G5 비밀·계좌 미출력 | PASS | 키는 `load_key()`로만 받아 바로 None으로 지움(611, 625). 오류는 `api_error_label`만 씀(641). 시험 `test_llm_pilot_srccheck.py:922-933` |
| G6 단언 약화·skip 없음, 새 동작마다 시험 | PASS | 새 시험 파일뿐이고 skip·expectedFailure 없음. new_failures [](`checks.json:88`). 대상·제출·수거·파싱·키·소스 계약 시험 44건 |
| G7 class | PASS(class_ok=false) | `test_llm_pilot_srccheck.py:117`의 가짜 연구 기록에 있는 `"quantity_authority": "SENTINEL_NOT_SENT_QUANTITY"`가 문자 그대로 "none/null/false가 아닌 값 추가"에 해당함(`checks.json:62-63` ADDED_LINE:quantity_authority). 이 값은 지시문 `task-prompt.md:87`이 요구한 "보내지 않음" 표식이고, 스크립트는 이 키를 읽지 않음(372-424). 실제 주문·수량 권한, 예산, 상한 변경은 없음 |
| G8-1 허용 파일 3개 | PASS | `changed-files.txt:1-3`. 공통 모듈·pdfcmp·실행기·켜기 파일 변경 없음 |
| G8-2 호스트·경로 규칙, 직접 요청 없음 | PASS | ALLOWED_HOSTS 94-110이 `task-prompt.md:50-51`과 글자 그대로 같음. SEC 경로 112, 차단 낱말 114, 첫 화면 314, 경로 검사 316-320. 시험 `test_llm_pilot_srccheck.py:432-468,985-1006` |
| G8-3 도구 1개, url 글자 대조, 인용 없으면 낮춤, 재시도 없음 | PASS | 도구 정의 541-549, 결과 url 글자 대조 716-734, NO_CITATION 778-780, seen 기록 658. 시험 573-608, 742-758, 905-920, 682-687 |
| G8-4 허용 칸 밖 값 미전송(표식 시험) | PASS | 시험 610-619. 표식 위치: 연구 기록 115-117, SEC 174-176, 그 밖에 77, 95, 106 등 |
| G8-5 모델 고정, 월 상한 선확인, 5건 상한, 멱등 | PASS | 모델 고정 560, check_message 761, 예산 확인 616-621이 생성 639보다 앞, 5건 상한 527, 멱등 595-598. 시험 621-662, 524-542 |
| G8-6 usage 10키, 키 미출력, ASCII, 보고서 (a)~(e) | PASS | usage 기록 847-872, 시험 703-740·789-805·922·985. 보고서 `diff.patch:19-113`에 (a)~(e)가 있고 표지 문자열·URL 목록 없음 |
| G9 연결표 | PASS | `task-prompt.md:112`. ②는 `llm_runner.py:51-52`와 맞음(srccheck-submit 08:10, srccheck-collect 10:10). ③은 `api-pilots-2026-11-06.md:178-179`와 맞음(합격 기준, 소비자). ⑤는 '끊김(…)' 형식에 메울 변경과 승인 경로가 적혀 있음 |

참고 사항 세 가지(판정을 바꾸지는 않음):
- **G7이 걸린 이유:** 시험 표식 한 줄 때문입니다. 지시문이 요구한 표식이라 고칠 항목은 없습니다. 키 이름을 바꿔 검출기를 피하는 것은 맞지 않습니다. 파이프라인이 이미 이 작업을 authority로 분류했으므로, 병합하려면 사용자가 직접 PowerShell에 `.\tools\dev-merge.ps1 llm-srccheck -ApproveAuthority`를 입력해야 합니다.
- **전체 시험 실패 5건:** 기준선과 같고 새 실패는 0입니다(`checks.json:76-88`). 기준선 쪽 알림 `BASELINE_FAILURES_ROSE`(+2)는 이 diff가 원인이 아닙니다.
- **Builder가 실제 자료 모양을 보지 못함:** Builder는 실제 연구 기록·SEC 산출물을 직접 읽지 못했습니다(보고서 `diff.patch:113`). 칸 이름은 위 스키마 원문으로 다시 확인했습니다.

```json
{"verdict": "PASS", "class_ok": false, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_srccheck.py:372-999; manage-us-stock-strategy/schemas/auto-core-research-record.schema.json:22-49; manage-us-stock-strategy/schemas/sec-official-normalized-events.schema.json:35-49"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/llm-srccheck/changed-files.txt:1-3; checks.json:68"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_srccheck.py:26-54,639"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_srccheck.py:490-504,616-619,657-658,871,939-945"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_srccheck.py:611,625,641; manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py:922-933"}, {"id": "G6", "result": "PASS", "evidence": "workspace/outputs/dev-runs/llm-srccheck/checks.json:88,95-102"}, {"id": "G7", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py:117 (sentinel quantity_authority value required by task-prompt.md:87; checks.json:62-63 ADDED_LINE:quantity_authority) -> class_ok=false by the literal rule; no real authority, budget or limit change"}, {"id": "G8-1", "result": "PASS", "evidence": "workspace/outputs/dev-runs/llm-srccheck/changed-files.txt:1-3"}, {"id": "G8-2", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_srccheck.py:94-114,300-321; task-prompt.md:50-54"}, {"id": "G8-3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_srccheck.py:541-549,658,716-734,778-780; manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py:573-608,742-758"}, {"id": "G8-4", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py:115-117,174-176,610-619"}, {"id": "G8-5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_srccheck.py:527,560,595-598,616-621,639,761"}, {"id": "G8-6", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_srccheck.py:847-872; manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py:703-740,922-933,985-996; docs/claude/llm-srccheck-report.md:19-113"}, {"id": "G9", "result": "PASS", "evidence": "task-prompt.md:112; manage-us-stock-strategy/scripts/llm_runner.py:51-52; docs/claude/api-pilots-2026-11-06.md:178-179"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-11-25T09:17:41Z
- 병합 커밋: `f90cf00558357fbabf0c1a2a26de23e6ce911eac` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-11-25T09:17:38Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/llm-srccheck/ 의 원본 기록입니다.)
