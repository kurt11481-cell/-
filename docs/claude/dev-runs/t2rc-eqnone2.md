# dev-run t2rc-eqnone2 — READY_TO_MERGE

- 시각(UTC): 2026-10-25T13:15:08Z → 2026-10-25T13:44:33Z
- 기준 커밋(base): `6937036b8624ba12eb91093471fe579403029183` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **READY_TO_MERGE** · 재시도: 0
- 테스트: 기준선 Ran 3353 · 실패 31 → 변경 후 Ran 3360 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `36ee93048be1ceac7290d9aa0f38452598773d60cde06f3d4972eed7a1370a24`
- Judge 파일 sha256: `2cdb5576a6243a6c30264dec9383f53b212d058128483263d3efb4b44f3435aa`
- 사유: 없음
- 다음: `.\tools\dev-merge.ps1 t2rc-eqnone2`

## 바뀐 파일

- `docs/claude/t2rc-check-run.ps1`
- `docs/claude/t2rc-eqnone2-report.md`
- `docs/claude/t2rc-oracle.py`
- `manage-us-stock-strategy/tests/test_t2rc_eq_none.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `docs/claude/t2rc-oracle.py:1729-1730`에 `if eq is None: return None, eq`를 넣었습니다. 시리즈 없음 분기(1734-1735)와 같은 형태입니다. 호출부 `ticket_check`에도 최소 수정을 넣었습니다(2026-2027). 빈 껍데기, 하드코딩, 남은 TODO는 없습니다. |
| G2 범위 | PASS | `changed-files.txt:1-4`의 4개 경로가 allowed_paths와 정확히 같습니다. `checks.json:17-22`, `checks.json:332`(status OK)도 같습니다. 러너는 16행만 바뀌었습니다(`diff.patch:5-10`). |
| G3 주문·체결 추정 | PASS | 추가된 줄은 `diff.patch:22-23`, `31-32`와 새 시험·보고 파일뿐입니다. 주문 경로나 키움 호출은 없고, 가격 변화로 체결을 추정하는 코드도 없습니다. |
| G4 정책·상태 쓰기와 fail-closed | PASS | 새로 생긴 쓰기 경로는 없습니다. equity가 없으면 다음처럼 막힌 쪽으로 처리됩니다. 노출 점검은 `PRICE_MISSING`이 됩니다(`t2rc-oracle.py:1766-1768`). 보유 종목 매수 요건은 `own_cap`이 참이 되어 막힙니다(`1904`, `1909`). 주문표는 불일치로 세고 `EQUITY_MISSING`을 남깁니다(`2027`). `checks.json`의 ignored 목록에 상태 파일이 보이지만, 이는 gitignore 대상인 worktree 로컬 파일입니다(`.gitignore:31-32`). 이번 변경 코드가 쓴 파일은 아닙니다. |
| G5 비밀 | PASS | 새 시험은 `t2rc-oracle.py`와 `t2rc-check-run.ps1`만 읽습니다(`test_t2rc_eq_none.py:12-13`). `.env*`, 토큰, 계좌번호는 읽지도 출력하지도 않습니다. |
| G6 시험 | PASS | 단언 약화, 삭제, skip, expectedFailure가 없습니다. 새 동작마다 시험이 있습니다(`test_t2rc_eq_none.py:51-77`, `81-86`). 대상 시험 7건 OK, 새 실패 0건입니다(`checks.json:378`, `382-389`). |
| G7 class | PASS | 주문 단계, 예산, 상한, kill switch, quantity_authority는 바뀌지 않았습니다. class는 general이고 class_reasons는 비어 있습니다(`checks.json:326-327`). |
| G8-1 파일 4개 | PASS | `changed-files.txt:1-4` |
| G8-2 판정 로직 불변 | PASS | oracle에는 4줄만 추가됐습니다(`diff.patch:18-32`). 비교 항목과 판정 기준은 그대로이고, 검사 항목도 줄지 않았습니다. |
| G8-3 equity None 처리 | PASS | 호출부 3곳(1766, 1904, 2025)이 모두 예외 없이 처리합니다. 코어도 equity가 없으면 매도·매수 주문표를 만들지 않습니다(`auto_core_tickets.py:1068-1070`, `1129-1131`). 그래서 `should_exist=False`는 코어 규칙과 맞습니다. 코어 주문표가 없으면 누락 표가 생기지 않습니다(`t2rc-oracle.py:1600-1603`). 코어 주문표가 있는데 일치로 잡히지 않는 것은 실제 불일치이므로, 잘못 센 불일치가 아닙니다. |
| G8-4 고정값 | PASS | 러너는 16행 값만 바뀌었고, 해시 비교 로직(61-68행)은 그대로입니다. Judge 도구가 Read·Grep·Glob뿐이라 sha256을 직접 계산하지는 못했습니다. 대신 파이프라인이 실행한 고정값 시험이 통과했습니다(`checks.json:382-389`). 이 시험은 oracle 바이트의 CRLF를 LF로 바꾼 sha256이 16행 값과 같은지 정확히 대조합니다(`test_t2rc_eq_none.py:83-86`). 러너 방식(UTF-8 텍스트를 LF로 바꾼 뒤 해시)은 BOM이 없는 이 파일에서 바이트 방식과 결과가 같습니다. 직전 고정값 6a74f8…이 두 방식에서 같았다는 기록이 있습니다(`rrec-ev4-remove-judge-report.md:32`, `t2rc-oracle.py:113`). 이번 diff는 파일 첫머리를 건드리지 않고 ASCII 줄만 추가했습니다. |
| G8-5 다른 해시 고정 | PASS | 지금 쓰이는 고정값은 `t2rc-check-run.ps1:16` 하나뿐입니다. tools/와 `t2rc-register-task.ps1`에는 해시 고정이 없습니다(검색 0건). 예전 값은 이미 병합이 끝난 일회성 merge 스크립트에만 남아 있습니다(`close-confirm-e-merge-2026-10-21.ps1:19`, `rrec-ev4-remove-merge-2026-10-19.ps1:18`). 이 스크립트들은 지시문의 수정 금지 대상입니다. |
| G8-6 주문·권한 표지 | PASS | 추가된 줄에 `/api/us/ordr`, `ust2000`, `ust2001`, `order_submit`, `quantity_authority`, `kill_switch`가 없습니다(`diff.patch` 추가 줄 전체). |

```json
{"verdict": "PASS", "class_ok": true, "items": [
 {"id": "G1", "result": "PASS", "evidence": "docs/claude/t2rc-oracle.py:1729-1730, 2026-2027"},
 {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/t2rc-eqnone2/changed-files.txt:1-4; diff.patch:5-10"},
 {"id": "G3", "result": "PASS", "evidence": "diff.patch:22-23, 31-32"},
 {"id": "G4", "result": "PASS", "evidence": "docs/claude/t2rc-oracle.py:1766-1768, 1904-1909, 2027; .gitignore:31-32"},
 {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_t2rc_eq_none.py:12-13"},
 {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_t2rc_eq_none.py:51-86; checks.json:378-389"},
 {"id": "G7", "result": "PASS", "evidence": "checks.json:326-327"},
 {"id": "G8-1", "result": "PASS", "evidence": "changed-files.txt:1-4"},
 {"id": "G8-2", "result": "PASS", "evidence": "diff.patch:18-32"},
 {"id": "G8-3", "result": "PASS", "evidence": "docs/claude/t2rc-oracle.py:1600-1603, 2025-2027; manage-us-stock-strategy/scripts/auto_core_tickets.py:1068-1070, 1129-1131"},
 {"id": "G8-4", "result": "PASS", "evidence": "docs/claude/t2rc-check-run.ps1:16, 61-68; manage-us-stock-strategy/tests/test_t2rc_eq_none.py:83-86; checks.json:382-389"},
 {"id": "G8-5", "result": "PASS", "evidence": "docs/claude/t2rc-check-run.ps1:16; docs/claude/close-confirm-e-merge-2026-10-21.ps1:19; docs/claude/rrec-ev4-remove-merge-2026-10-19.ps1:18"},
 {"id": "G8-6", "result": "PASS", "evidence": "diff.patch:22-23, 31-32, 99-188"}
], "min_fixes": []}
```

VERDICT: PASS

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/t2rc-eqnone2/ 의 원본 기록입니다.)
