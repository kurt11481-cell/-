# dev-run decide-gap2 — NEEDS_APPROVAL

- 시각(UTC): 2026-10-22T06:40:11Z → 2026-10-22T07:04:19Z
- 기준 커밋(base): `59c4f4887a8898a4e36fc1f21b74585e67cbbcd6` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: ADDED_LINE:kill_switch, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_decide_interrupt.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3278 · 실패 31 → 변경 후 Ran 3284 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `dddf325312045b08313e0c706c406ce1f4faa0574bed08fad8f06ababfe413c6`
- Judge 파일 sha256: `9301e95b6f35a58a1849ae3b9b9b20995629fe6898fee6b19b06150491637f87`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 decide-gap2 -ApproveAuthority`

## 바뀐 파일

- `docs/claude/decide-gap2-report.md`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/tests/test_auto_core_decide_interrupt.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | auto_core_decide.py:485-489 — 대기 중 KeyboardInterrupt가 들어오면 `interrupted=True`로 대기만 끝냄. :493에서 반환값에 `interrupted` 키 추가. :452-454 — decide() 바깥 except가 FAIL과 `INTERRUPTED:KeyboardInterrupt`를 넣고 :455 `_finish`로 기록. 하드코딩·TODO 없음 |
| G2 범위 | PASS | changed-files.txt:1-3에 있는 세 경로가 모두 task-prompt.md:14 allowed_paths 안. checks.json:109 reasons 비어 있음 |
| G3 주문·체결 추정 | PASS | diff에 주문 경로·키움 주문 도구·가격으로 체결 추정하는 코드 없음. auto_core_decide.py:470 `order_authority: False`, `execution_quantity: None` 그대로. 테스트 test_auto_core_decide_interrupt.py:94-95, :165-166이 이를 단언 |
| G4 정책·상태 쓰기, fail-closed | PASS | 저널 쓰기는 auto_core_decide.py:751 한 곳뿐이고 바뀌지 않음. 바깥 except는 :1281-1282에서 decision.json과 LATEST_DECISION.json만 씀(기존 경로). 중단 후 연구 기록이 없으면 :570-572 research_block으로 매수만 막힘. 테스트 :164는 저널 바이트가 그대로임을 확인 |
| G5 비밀·계좌 | PASS | .env·토큰·계좌번호를 읽거나 출력하는 곳 없음. 테스트는 합성 Env(test_auto_core_decide.py:67-182)만 씀 |
| G6 테스트 | PASS | 기존 테스트 파일 무변경(changed-files.txt). skip·expectedFailure 없음. 새 동작마다 테스트 있음(test_auto_core_decide_interrupt.py:72, :106, :119, :149, :168). checks.json:156 new_failures 없음. 실행 수 3278→3284(+6) |
| G7 class | PASS | 한도·예산·관문·kill switch·quantity_authority 값 변경 없음. checks.json:102 `ADDED_LINE:kill_switch`는 보고서 decide-gap2-report.md:20의 "바꾸지 않았다"는 문장일 뿐 값 변경이 아님 |
| G8-1 diff 최소 | PASS | auto_core_decide.py diff는 대기 try/except, `interrupted` 키, docstring, 바깥 except 하나뿐(+13 −2). RESEARCH_WAIT_UNTIL·RESEARCH_POLL_SECONDS(:64-65)와 게이트·티켓 규칙 무변경 |
| G8-2 매도 경로 차단 없음 | PASS | 테스트 test_auto_core_decide_interrupt.py:86-93 — 매도 티켓이 있고 판정 키가 08:30까지 기다린 실행과 같으며, 매수 티켓 없음, MU 매수 요건 ① no |
| G8-3 대기 밖 중단 → FAIL 기록 | PASS | 테스트 test_auto_core_decide_interrupt.py:149-166 — 예외가 밖으로 새지 않음, decision.json FAIL, LATEST 같음, 스키마 통과, DECIDE_FAIL 알림. :168-177 — 같은 날 재실행은 정상 |
| G8-4 저널·스키마·권한 줄 | PASS | schemas/auto-core-decision.schema.json:27 `"inputs": {"type": "object"}`라 키 추가가 허용되고 스키마는 무변경. :775-777에서 wait 블록은 결정 해시 밖. 주문·권한 줄 변경 없음 |
| G8-5 보고·테스트 | PASS | decide-gap2-report.md:55에 (a) "확인 필요"가 적혀 있고, :56에 (b) 잡을 수 없는 경우, :57에 (c) 더 강한 대안을 하지 않은 이유가 있음. 대상 테스트의 실패 1건(PLTR, test_auto_core_decide.py:1332-1339)은 실제 등록부를 읽는 테스트로 기준선에도 있던 실패이고, 새 실패는 0(checks.json:156) |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:485-493,452-455"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/decide-gap2/changed-files.txt:1-3"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:470"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:751,1281-1282,570-572"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_decide.py:67-182"}, {"id": "G6", "result": "PASS", "evidence": "workspace/outputs/dev-runs/decide-gap2/checks.json:151,156"}, {"id": "G7", "result": "PASS", "evidence": "docs/claude/decide-gap2-report.md:20"}, {"id": "G8", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_decide_interrupt.py:72-95,149-177; docs/claude/decide-gap2-report.md:55-57"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-22T07:05:28Z
- 병합 커밋: `5d6943c6cedcaeedc1aa20fc1bee0b3d94a09118` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-10-22T07:05:26Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/decide-gap2/ 의 원본 기록입니다.)
