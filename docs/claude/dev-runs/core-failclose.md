# dev-run core-failclose — NEEDS_APPROVAL

- 시각(UTC): 2026-11-02T04:20:15Z → 2026-11-02T04:51:35Z
- 기준 커밋(base): `d88e88feea4e596b8458ccfa27a01780c7334130` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_inputs.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_rules.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_tickets.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_input_guard.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_tickets.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3497 · 실패 29 → 변경 후 Ran 3511 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `62ebbccc6bb22e01b8f8f3c7d12da59d1b516eca1bf9f994d6905dc96c56e8a9`
- Judge 파일 sha256: `5964d157cb3ce899e391aaf2116ae16d773e3ad2b0bdeca86fafdb1b39d16129`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 core-failclose -ApproveAuthority`

## 바뀐 파일

- `docs/claude/core-failclose-report.md`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/scripts/auto_core_inputs.py`
- `manage-us-stock-strategy/scripts/auto_core_rules.py`
- `manage-us-stock-strategy/scripts/auto_core_tickets.py`
- `manage-us-stock-strategy/tests/test_auto_core_input_guard.py`
- `manage-us-stock-strategy/tests/test_auto_core_tickets.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | C-1: `manage-us-stock-strategy/scripts/auto_core_rules.py:71,740-744`, `auto_core_decide.py:575-577`. C-2: `auto_core_tickets.py:1137-1139`. 빈 껍데기, 하드코딩, TODO 없음 |
| G2 범위 | PASS | `changed-files.txt:1-7`이 allowed_paths 7개 안에 있음. 경보 분리(`auto_core_decide.py:581-593`)는 지시문에 없었지만, 없으면 커밋된 문서를 "미커밋 EV3"로 잘못 알리므로 목표에 필요한 변경임. 기존 경보 문구는 그대로이고 새 차단 길도 없음 |
| G3 주문·체결 추정 | PASS | diff.patch 전체에 주문 경로, 키움 주문 도구 호출, 가격 기반 체결 추정 없음 |
| G4 쓰기·fail-closed | PASS | 정책·상태·일지 쓰기 없음. 시험 쓰기는 임시 환경의 `env.docs`뿐임(`test_auto_core_input_guard.py:210`). 문서가 없으면 기존 `CORE_INPUT_MISSING`이 막고(`auto_core_inputs.py:233-234`), 가드 오류에도 사유가 유지됨(`auto_core_inputs.py:250`) |
| G5 비밀 | PASS | 비밀·토큰·계좌 식별자를 읽거나 출력하는 곳 없음. 새로 읽는 실제 파일은 회복 관문 문서뿐임(`test_auto_core_input_guard.py:204`) |
| G6 시험 | PASS | 시험 쪽 변경은 추가와 머리 설명문뿐이고 skip, expectedFailure 없음. 추가 14건(3497→3511, `checks.json:5,163`). `new_failures` 빈 배열(`checks.json:168`) |
| G7 class | PASS | 주문 단계, 도구, 예산, 상한, 종목 상한, 승인 상품, 대조 불변 조건, 정지 스위치, quantity_authority 변경 없음. 이 실행의 class는 authority 그대로임(`checks.json:111`) |
| G8-1 허용 파일 | PASS | `checks.json:17-25`, `task-prompt.md:27-33` |
| G8-2 C-1 | PASS | 조건은 `loose > len(ev3_dates(text))`(`auto_core_rules.py:744`). `EV3_LINE`·`ev3_dates`는 불변(`auto_core_rules.py:69,736-737`). 사유는 `input_block`으로 전달(`auto_core_decide.py:705`, `auto_core_tickets.py:741,823`). 검사(`auto_core_decide.py:575`)가 대기(`auto_core_decide.py:594`)보다 앞이고, 판정한 글과 R-REC1이 쓰는 글이 같음(`auto_core_decide.py:570,698`) |
| G8-3 C-2 | PASS | `held`이고 비중이 없을 때만 차단(`auto_core_tickets.py:1137`). 첫 매수와 비중 있는 보유는 1140행 이후 계산 그대로임. `hold_eval`도 같은 weights를 써서 판정이 갈리지 않음(`auto_core_decide.py:1180`) |
| G8-4 매도·완화 | PASS | `_plan_sell`, `_sell_ticket`, 관문, card_check diff 없음. 기존 매수 차단 사유도 그대로임. C-2는 후보 선택(`auto_core_tickets.py:735-739`) 뒤에 일어나고, 매도표는 sell 쪽 차단만 읽음(`auto_core_tickets.py:1256`) |
| G8-5 단언·시험 분기 | PASS | 시험 6개가 실제 분기를 거침: `test_auto_core_input_guard.py` 200행대 `Ev3ParseTests`, `test_auto_core_tickets.py:753,758,769`. 비중을 뺀 시험과 그대로 둔 시험이 같은 Scenario를 써서 차단 원인이 비중 누락임이 입증됨 |
| G8-6 새 실패 0 | PASS | 실패 29건은 기준선 29건과 같은 수이고 새 실패 0(`checks.json:4,168`). PLTR 레지스트리 실패는 기존 실패임 |
| G8-7 보고서 | PASS | `docs/claude/core-failclose-report.md`에 (a)~(e) 있음. 수량·금액·표지 문자열 grep 0건. 인용한 줄 번호는 원문과 일치함 |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_rules.py:71,740-744; auto_core_decide.py:575-577; auto_core_tickets.py:1137-1139"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/core-failclose/changed-files.txt:1-7; auto_core_decide.py:581-593"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/core-failclose/diff.patch:1-413"}, {"id": "G4", "result": "PASS", "evidence": "auto_core_inputs.py:233-234,250; test_auto_core_input_guard.py:210"}, {"id": "G5", "result": "PASS", "evidence": "test_auto_core_input_guard.py:204; workspace/outputs/dev-runs/core-failclose/diff.patch:1-413"}, {"id": "G6", "result": "PASS", "evidence": "workspace/outputs/dev-runs/core-failclose/checks.json:5,163,168"}, {"id": "G7", "result": "PASS", "evidence": "workspace/outputs/dev-runs/core-failclose/checks.json:111; workspace/outputs/dev-runs/core-failclose/diff.patch:1-413"}, {"id": "G8-1", "result": "PASS", "evidence": "workspace/outputs/dev-runs/core-failclose/checks.json:17-25; task-prompt.md:27-33"}, {"id": "G8-2", "result": "PASS", "evidence": "auto_core_rules.py:69,736-737,744; auto_core_decide.py:570,575,594,698,705; auto_core_tickets.py:741,823"}, {"id": "G8-3", "result": "PASS", "evidence": "auto_core_tickets.py:1137-1140; auto_core_decide.py:1180"}, {"id": "G8-4", "result": "PASS", "evidence": "auto_core_tickets.py:735-739,1256; workspace/outputs/dev-runs/core-failclose/diff.patch:112-125"}, {"id": "G8-5", "result": "PASS", "evidence": "test_auto_core_input_guard.py:200; test_auto_core_tickets.py:753,758,769"}, {"id": "G8-6", "result": "PASS", "evidence": "workspace/outputs/dev-runs/core-failclose/checks.json:4,168"}, {"id": "G8-7", "result": "PASS", "evidence": "docs/claude/core-failclose-report.md:1-73"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-11-02T06:06:28Z
- 병합 커밋: `6aea772ccb456d1f3bfd560cd4507d6681d00200` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-11-02T06:06:25Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/core-failclose/ 의 원본 기록입니다.)
