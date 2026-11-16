# dev-run t2rc-isolate — READY_TO_MERGE

- 시각(UTC): 2026-11-15T07:35:06Z → 2026-11-15T08:00:44Z
- 기준 커밋(base): `92c8546c44601ac2276dc34bd39e8f1a7b321b9e` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **READY_TO_MERGE** · 재시도: 0
- 테스트: 기준선 Ran 3662 · 실패 1 → 변경 후 Ran 3679 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `a984e72a06f45c222bf9636b8ae5572706e15ceae6eef64af96d4806cbd74b57`
- Judge 파일 sha256: `a20ce9249ebec46a72ec39fa16068523fa22e41158d3489698f03b14789eefe4`
- 사유: 없음
- 다음: `.\tools\dev-merge.ps1 t2rc-isolate`

## 바뀐 파일

- `docs/claude/t2rc-check-run.ps1`
- `docs/claude/t2rc-isolate-report.md`
- `docs/claude/t2rc-oracle.py`
- `manage-us-stock-strategy/tests/test_t2rc_isolate.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `docs/claude/t2rc-oracle.py:1273-1274`: 격리 종목은 상태가 ISOLATED가 되고 `continue`로 넘어가며, 이 분기는 `detail[sym]=d` 바로 뒤, `ind is None` 검사 앞에 있음. `:1333-1361` `t1_isolated` 함수. `:1364-1370` `isolated_for_check` 함수. `:1582` 격리 목록 읽기. `:1613`에서 `isolated=isolated`로 넘김. `:19` docstring 한 줄. 남은 TODO나 하드코딩 없음 |
| G2 범위 | PASS | `changed-files.txt:1-4`: 바뀐 파일 4개가 모두 allowed_paths 안. `checks.json:17-22`, `:100` reasons가 빈 목록 |
| G3 주문·체결 추정 | PASS | diff.patch에서 주문 경로 문자열 6종과 권한 표지 4종이 모두 0건(Grep). 새 코드는 파일 읽기만 함(`t2rc-oracle.py:1364-1370`) |
| G4 정책·상태 쓰기, fail-closed | PASS | 새 쓰기 경로 없음. 읽기·JSON 오류나 형식이 틀린 목록은 빈 집합으로 처리되어 지금처럼 전부 대조함(`t2rc-oracle.py:1339-1361`, `:1366-1370`). T1 결과 sha가 어긋나면 그 전에 NOT_CHECKED로 끝남(`:1559-1561`). 코어가 격리 종목 표를 내면 extra_in_core로 MISMATCH가 남(`:1614-1618`, `:1663-1664`) |
| G5 비밀·계좌 | PASS | `t2rc-oracle.py:1364-1370`: T1 result.json에서 `steps.bars.isolated` 종목 코드만 씀. 비밀·계좌 식별자는 읽지도 출력하지도 않음 |
| G6 단언·skip·새 테스트 | PASS | 기존 테스트 변경 없음(`changed-files.txt`). 새 테스트 17건으로 ran 3662 → 3679, skipped 3 → 3, new_failures 없음(`checks.json:5,7,111-116`). 실패 1건은 기준선에 있던 것(`checks.json:4,109`). 새 동작마다 테스트가 있음(`test_t2rc_isolate.py:50,55,61,89,121,126,138,141,169,172,188,193,198,202,222,233,242`). 참고: 보고 2절의 importlib 로드 위치 '28~32행'은 실제 26~30행(`test_t2rc_isolate.py:26-30`). 판정에는 영향 없음 |
| G7 class | PASS | 주문 단계·도구·예산·상한·대조 불변 조건·정지 스위치 변경 없음. quantity_authority 추가 없음(diff Grep 0건). `checks.json:95-96` class general, class_reasons가 빈 목록 |
| G8-1 4개 파일·새 키·권한 표지 | PASS | `changed-files.txt:1-4`. diff에 `res[` 줄 없음. ISOLATED 종목의 detail 키는 role·registry·status뿐(`t2rc-oracle.py:1271,1274`)이라 `circuit_detail` 필터(`:1652`) 안에 들어감. 권한 표지 4종은 diff에 0건 |
| G8-2 circuit_for_session | PASS | `t2rc-oracle.py:1260-1261`: 키워드 전용 인자이고 기본값은 `frozenset()`. replay 호출은 바뀌지 않음(`:2236`). 격리 종목은 `:1274`에서 buy·sell·triggers가 없음. 격리가 아닌 종목은 `:1275-1309` 그대로 |
| G8-3 t1_isolated 형식 | PASS | 오라클 `t2rc-oracle.py:1340-1358`과 decide `auto_core_decide.py:187-206`의 조건이 같음: 비지 않은 list, 키가 정확히 symbol·reason, 대문자에 앞뒤 공백 없음, reason이 str, 중복 없음, 보유·기준 종목 제외. 코어 기준 종목은 SOXX·GRID(`auto_core_decide.py:655`, `auto_core_rules.py:64-65,993`). members 조건이 더해져 있음. 어긋나면 빈 집합 |
| G8-4 sha 대조 뒤 읽기, import 없음 | PASS | `t2rc-oracle.py:1559-1561` NOT_CHECKED 반환이 `:1582` 읽기와 `:1612-1613` 넘김보다 앞. import는 `:28-37` 표준 라이브러리뿐이고 auto_core* 없음 |
| G8-5 C1 guard | PASS | 보고서에 코어 status가 UNK로 적혀 있고 원문과 맞음: `auto_core_decide.py:670-674` 덮어쓰기 → `auto_core_rules.py:539-548` status UNK → `auto_core_decide.py:760`, `:1294-1297`. 코어 status가 OK가 아니어서 `t2rc-oracle.py:1673` core_ok가 거짓 → gap 없음. guard를 그대로 둔 처리가 맞음 |
| G8-6 고정 해시 | PASS | `t2rc-check-run.ps1:16` 새 고정 해시. `test_t2rc_eq_none.py:42-47` 고정 해시 테스트가 들어 있는 test_t2rc*.py 23건 OK(`checks.json:120-127`) |
| G8-7 테스트가 변경을 잡음 | PASS | 함수를 빼면 테스트 1·2·5가 AttributeError로 실패. 격리 분기를 빼면 `test_t2rc_isolate.py:126-137`이 실패. cmd_check 연결을 빼면 `:222-231`이 실패. 대상 테스트 3종 모두 OK(`checks.json:120-145`) |
| G8-8 / G9 연결표 | PASS | 확인한 줄: `t2rc-check-run.ps1:8-11`(InvestmentV2-T2rcCheck 화~토 08:40), `:16`, `:60-63`, `:64-68`(ORACLE_SHA_MISMATCH, exit 3). `auto-core-alert.txt:14,23,47`(⑫ MISMATCH 또는 ERROR). `active-decisions.md:62`(trig id 두 개). `room-digest.txt:12,28`. `test_t2rc_eq_none.py:42-47`. 새 테스트 줄 번호는 보고와 맞음. trig id 3개는 모두 `trig_`로 시작. 지시문의 cmd_check 1447행은 기준 커밋 기준이고, 바뀐 파일에서는 1492행(보고 표는 1492로 고쳐 적음) |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "docs/claude/t2rc-oracle.py:1273-1274,1333-1370,1582,1613"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/t2rc-isolate/changed-files.txt:1-4"}, {"id": "G3", "result": "PASS", "evidence": "diff.patch (order path strings 0 hits); docs/claude/t2rc-oracle.py:1364-1370"}, {"id": "G4", "result": "PASS", "evidence": "docs/claude/t2rc-oracle.py:1339-1361,1366-1370,1559-1561,1614-1618"}, {"id": "G5", "result": "PASS", "evidence": "docs/claude/t2rc-oracle.py:1364-1370"}, {"id": "G6", "result": "PASS", "evidence": "checks.json:4-7,109-116; manage-us-stock-strategy/tests/test_t2rc_isolate.py:50-242"}, {"id": "G7", "result": "PASS", "evidence": "checks.json:95-96; diff.patch (authority marker strings 0 hits)"}, {"id": "G8", "result": "PASS", "evidence": "docs/claude/t2rc-oracle.py:1260-1261,1274,1340-1358,1559-1561,1582,1612-1613,1652,1673,2236; manage-us-stock-strategy/scripts/auto_core_decide.py:187-206,655,670-674,760,1294-1297; manage-us-stock-strategy/scripts/auto_core_rules.py:539-548; checks.json:120-145"}, {"id": "G9", "result": "PASS", "evidence": "docs/claude/t2rc-check-run.ps1:8-11,16,60-68; docs/claude/scheduled-prompts/auto-core-alert.txt:14,23,47; docs/claude/active-decisions.md:62; docs/claude/scheduled-prompts/room-digest.txt:12,28; manage-us-stock-strategy/tests/test_t2rc_eq_none.py:42-47"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-11-16T06:24:07Z
- 병합 커밋: `129eb9e7c5236eba86e9a29aa5f9b6bdd469aa29` · 방식: rebase

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/t2rc-isolate/ 의 원본 기록입니다.)
