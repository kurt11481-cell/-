# dev-run llm-iccheck — READY_TO_MERGE

- 시각(UTC): 2026-11-06T22:10:07Z → 2026-11-06T22:56:21Z
- 기준 커밋(base): `d8031bb27c43edc31daf34fa6346d182983ea306` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **READY_TO_MERGE** · 재시도: 1
- 테스트: 기준선 Ran 3546 · 실패 0 → 변경 후 Ran 3585 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `540c4e32bbf29a5a531a11c9c8161694a5b312956608c27eec5eb2671a5bca6d`
- Judge 파일 sha256: `edf35d6590503c2429fac37fc3431745680974f78689d93258cf2f8194c25e1a`
- 사유: 없음
- 다음: `.\tools\dev-merge.ps1 llm-iccheck`

## 바뀐 파일

- `docs/claude/llm-iccheck-report.md`
- `manage-us-stock-strategy/requirements-llm.txt`
- `manage-us-stock-strategy/scripts/llm_pilot_common.py`
- `manage-us-stock-strategy/scripts/llm_pilot_iccheck.py`
- `manage-us-stock-strategy/tests/test_llm_pilot_common.py`
- `manage-us-stock-strategy/tests/test_llm_pilot_iccheck.py`

## Judge 보고 원문 (2회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 공통 모듈의 상수·키·클라이언트·금액 지우기·인용 확인·예산·원자적 쓰기·응답 검사가 `llm_pilot_common.py:18-396`에 있습니다. 실행 순서 1~14는 `llm_pilot_iccheck.py:291-478`에 있습니다. `SYSTEM_PROMPT`(70-84)와 `SCHEMA`(86-122)는 지시문과 글자 그대로 같습니다(시험 `test_llm_pilot_iccheck.py:539-561`). 빈 껍데기·하드코딩·남은 TODO는 없습니다. |
| G2 범위 | PASS | `changed-files.txt:1-6`은 모두 새 파일(A)이고, `diff.patch`의 새 파일 표시도 6개뿐입니다. `checks.json:75-83`에서 기존 파일 수정은 없고 새 파일 6개는 allowed_paths와 같습니다. |
| G3 주문·키움·체결 추정 | PASS | 새 스크립트를 검색했을 때 키움·주문·subprocess·네트워크 라이브러리가 없습니다. 걸린 것은 지울 키 이름 `kiwoomtotal`·`kiwoomdiff`(`llm_pilot_common.py:137-138`)뿐입니다. |
| G4 정책·상태 쓰기 / 실패 쪽 닫힘 | PASS | 쓰기는 `llm_dir` 아래뿐입니다(`common.py:73-78, 323-328, 357-370`, `iccheck.py:355-358, 456-477`). 자료가 없거나 깨지면 실패로 끝납니다: NO_RECORD·BAD_INPUT `iccheck.py:312-327`, NO_KEY 363-364, 사용 기록을 못 읽거나 예산 초과면 BUDGET_STOP 369-374·396-400. |
| G5 비밀·계좌 | PASS | 키는 환경 변수 `KEY_ENV`에서만 읽습니다(`common.py:83-88`). 오류 사유에는 예외 이름과 HTTP 번호만 씁니다(`common.py:105-110`, `iccheck.py:388, 413, 500-503`). `.env`·계좌 읽기는 없습니다. |
| G6 시험 | PASS | skip·expectedFailure 0건, 단언 약화 없음(새 파일뿐)입니다. 대상 시험 39개 OK, 새 실패 없음(`checks.json:92-116`). 막지 않는 참고: Builder가 지시문 밖에서 더한 방어 분기 셋은 시험이 없습니다(`iccheck.py:326-327, 387-388, 392-393`). 셋 다 실패로 닫히고, 키를 가리는 함수는 이미 시험된 `api_error_label`을 씁니다. |
| G7 class | PASS | quantity_authority·order_authority·주문 단계·예산·상한 변경 문자열이 0건입니다. `checks.json:85-86`은 class general이고 class_reasons는 비어 있습니다. |
| G8-1 허용 6개, 모두 새 파일 | PASS | `changed-files.txt:1-6` |
| G8-2 키 | PASS | `common.py:91-102`에서 `ANTHROPIC_*` 다섯 변수를 지운 뒤 함수 안에서 import하고, base_url을 공식 주소로, max_retries=1로 고정합니다. 시험: `test_llm_pilot_common.py:315-344`, `test_llm_pilot_iccheck.py:236-241`(모든 경로에서 호출), `test_llm_pilot_iccheck.py:492-503` |
| G8-3 요청 | PASS | `iccheck.py:178-199`: claude-sonnet-5-5, 결정 블록이 앞이고 기록 블록이 뒤, output_config는 format(json_schema)와 effort medium입니다. `iccheck.py:381-400`: count_tokens를 먼저 부르고 150,000 상한, 예산 검사 2회(369-374, 396-400) 뒤에 stream을 부릅니다. 시험 `test_llm_pilot_iccheck.py:290-327, 366-382`에서 금지 키 없음과 호출 순서를 단언합니다. |
| G8-4 금액 지우기 | PASS | account 허용 목록(`common.py:115-125, 213-220`), reconcile 첫 낱말(204-207, 226-230), 숫자 금액 키(126-146, 199-201, 223-225), 가리기 다섯 규칙(155-178)이 있고, 결정 색인 글에도 `mask_text`를 씁니다(`iccheck.py:333`). 시험 `common:117-167`, `iccheck:390-404`가 4321·8765·98.76·98765.43이 보낸 글 전체에 없음을 보입니다. |
| G8-5 인용 확인 | PASS | `common.py:274-284`(앞표시 떼기, 공백 정규화, 6자 이상, 그 행 대조), `iccheck.py:443-451`(앞 10개만, 버린 수 셈). 시험 `common:215-225`, `iccheck:346-348, 406-415` |
| G8-6 쓰기 위치·읽는 곳 | PASS | 결과 파일은 원자적으로 씁니다(`common.py:357-363`). usage.jsonl은 지시문대로 덧붙이기만 합니다(323-328). 저장소에서 `outputs/llm`·`llm_pilot`을 찾았을 때 새 파일과 docs 설계 문서 3개만 나오고, 기존 코드는 이 출력을 읽지 않습니다. |
| G8-7 시험이 실제 경로 실행 | PASS | 각 시험이 임시 루트에 실제 입력을 만들거나 지워 그 경로로 들어갑니다(`test_llm_pilot_iccheck.py:207-224, 252-503`). 네트워크·SDK 없이 돌고, skip이 없고, 기존 시험 변경이 없습니다. |
| G8-8 새 실패 0 | PASS | `checks.json:92-116`: 전체 3585 OK(기준선 3546 + 39), 새 실패 없음, 스키마 감사 PASS |
| G8-9 보고서 | PASS | `llm-iccheck-report.md`의 (a) 10행, (b) 43행, (c) 89행, (d) 108행이 다 있고, 수량·금액·키 값·표지는 없습니다(121행). 막지 않는 참고: 62행 "19개 모두 끝에 assert_no_key_anywhere"는 `test_day_must_be_iso_date`(`test_llm_pilot_iccheck.py:531-534`) 하나에는 맞지 않습니다. 이 시험은 파일을 만들지 않으므로 사소합니다. |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/llm_pilot_common.py:18-396; manage-us-stock-strategy/scripts/llm_pilot_iccheck.py:291-478; tests/test_llm_pilot_iccheck.py:539-561"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/llm-iccheck/changed-files.txt:1-6; checks.json:75-83"}, {"id": "G3", "result": "PASS", "evidence": "llm_pilot_common.py:137-138 (key names only); no kiwoom/order/network code in llm_pilot_*.py"}, {"id": "G4", "result": "PASS", "evidence": "llm_pilot_common.py:73-78,323-328,357-370; llm_pilot_iccheck.py:312-327,362-374,396-400,456-477"}, {"id": "G5", "result": "PASS", "evidence": "llm_pilot_common.py:83-88,105-110; llm_pilot_iccheck.py:388,413,500-503"}, {"id": "G6", "result": "PASS", "evidence": "checks.json:92-116; no skip/expectedFailure in tests/test_llm_pilot_*.py"}, {"id": "G7", "result": "PASS", "evidence": "checks.json:85-86; no authority/limit strings in diff"}, {"id": "G8-1", "result": "PASS", "evidence": "changed-files.txt:1-6"}, {"id": "G8-2", "result": "PASS", "evidence": "llm_pilot_common.py:83-102; tests/test_llm_pilot_common.py:315-344; tests/test_llm_pilot_iccheck.py:236-241,492-503"}, {"id": "G8-3", "result": "PASS", "evidence": "llm_pilot_iccheck.py:178-199,369-411; tests/test_llm_pilot_iccheck.py:290-327,366-382"}, {"id": "G8-4", "result": "PASS", "evidence": "llm_pilot_common.py:115-255; llm_pilot_iccheck.py:330-334; tests/test_llm_pilot_common.py:117-167; tests/test_llm_pilot_iccheck.py:390-404"}, {"id": "G8-5", "result": "PASS", "evidence": "llm_pilot_common.py:274-284; llm_pilot_iccheck.py:443-451; tests/test_llm_pilot_common.py:215-225; tests/test_llm_pilot_iccheck.py:346-348,406-415"}, {"id": "G8-6", "result": "PASS", "evidence": "llm_pilot_common.py:323-328,357-363; llm_pilot_iccheck.py:162-163,355-358,456-477; no reader of outputs/llm outside new files"}, {"id": "G8-7", "result": "PASS", "evidence": "tests/test_llm_pilot_iccheck.py:207-224,252-534; tests/test_llm_pilot_common.py:116-368"}, {"id": "G8-8", "result": "PASS", "evidence": "checks.json:92-116"}, {"id": "G8-9", "result": "PASS", "evidence": "docs/claude/llm-iccheck-report.md:10,43,89,108,121"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-11-07T00:32:11Z
- 병합 커밋: `559efb93775d9ddc66336672b0ac4fdbb3c47854` · 방식: ff

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/llm-iccheck/ 의 원본 기록입니다.)
