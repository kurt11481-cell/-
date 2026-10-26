# dev-run t2rc-eqnone4 — READY_TO_MERGE

- 시각(UTC): 2026-10-26T02:05:08Z → 2026-10-26T02:31:07Z
- 기준 커밋(base): `4ee8e8b0495e44b37faa66882878a26894589b15` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **READY_TO_MERGE** · 재시도: 0
- 테스트: 기준선 Ran 3378 · 실패 31 → 변경 후 Ran 3384 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `ef97f95e788c5bc85bf1950846cf58a2a25d1d752936ea61d00080771538e5e9`
- Judge 파일 sha256: `d1aef94d031103a8458819a0c41bd7d04ce4513b25cc85c5f38e0b036da38355`
- 사유: 없음
- 다음: `.\tools\dev-merge.ps1 t2rc-eqnone4`

## 바뀐 파일

- `docs/claude/t2rc-check-run.ps1`
- `docs/claude/t2rc-eqnone4-report.md`
- `docs/claude/t2rc-oracle.py`
- `manage-us-stock-strategy/tests/test_t2rc_eq_none.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `weights_now`에 `if eq is None: return None, eq`를 넣었다(docs/claude/t2rc-oracle.py:1729-1730). 호출부 `ticket_check`에도 `EQUITY_MISSING` 가드를 넣었다(2026-2027). 빈 껍데기, 하드코딩, 남은 TODO는 없다. |
| G2 범위 | PASS | changed-files.txt:1-4의 네 경로가 allowed_paths(task-prompt.md:50-53)와 정확히 같다. checks.json:26-32의 ignored 항목은 gitignore 대상 로컬 파일(.gitignore:31-32, 151)과 pycache라서 변경에 들어가지 않는다. |
| G3 주문·체결 추정 | PASS | 추가된 줄(diff.patch:22-23, 31-32, 10)에 주문 경로, 키움 호출, 가격 변화로 체결을 추정하는 코드가 없다. |
| G4 쓰기 경로·fail-closed | PASS | 새로 생긴 쓰기 경로는 없고, 새 시험도 아무것도 쓰지 않는다(test_t2rc_eq_none.py:4, 43-44). equity가 비면 막힌 쪽으로 처리된다. 노출 점검은 `PRICE_MISSING`(t2rc-oracle.py:1766-1768)이 된다. 보유 종목 매수 요건은 N_oracle None과 `own_cap`=True로 막힌다(1898-1909). 이미 나온 주문표는 불일치로 세고 `EQUITY_MISSING`을 남긴다(2027, 2115). |
| G5 비밀 | PASS | 새 시험은 oracle과 runner 두 파일만 읽는다(test_t2rc_eq_none.py:16-17). .env*, 토큰, 계좌번호는 읽지도 출력하지도 않는다. |
| G6 시험 | PASS | 단언 약화·삭제·skip 추가가 없다. 새 시험 6개가 통과했고 새 실패는 0이다(checks.json:94, 97-105). EXPECTED_FAILURES_INCREASED도 없다(checks.json:95). (c)는 정적 시험이며, 지시문이 허용한 방식이고 이유도 보고서에 적혀 있다(task-prompt.md:24, report:30). |
| G7 class | PASS | 주문 단계·도구·예산·상한·승인 상품·대조 불변 조건·kill switch를 바꾸지 않았다. quantity_authority 추가도 없다(diff.patch 전체에서 해당 표지 검색 0건). |
| G8-1 변경 4개 | PASS | changed-files.txt:1-4 |
| G8-2 판정 로직 불변 | PASS | oracle diff는 추가 4줄뿐이고 삭제는 없다(diff.patch:18-32). 비교 항목, 허용 오차, `diffs`는 그대로다. |
| G8-3 equity None 처리 | PASS | 시리즈 없음 분기와 같은 형태다(1730 vs 1735). 호출부는 세 곳 모두 예외 없이 처리한다(1766, 1904/1909, 2025-2027). 코어도 equity가 비면 매수·매도 주문표를 만들지 않는다(auto_core_tickets.py:1068-1070, 1129-1131). 따라서 `should_exist=False`는 코어 규칙과 맞고, 누락 표가 잘못 생기지 않는다(t2rc-oracle.py:1601-1603). 코어 주문표가 있는데 불일치로 잡히면 실제 불일치다. 보고서의 줄 번호 "1902~1907"(report:20)은 실제 1904-1909와 조금 어긋나지만 내용에는 영향이 없다. |
| G8-4 고정값 | PASS | 러너는 16행만 바뀌었고 비교 로직(t2rc-check-run.ps1:61-68)은 그대로다. Judge 도구가 Read·Grep·Glob뿐이라 sha256을 직접 계산하지는 못했다. 대신 파이프라인이 직접 돌린 시험이 통과했다(checks.json:97-105). 이 시험은 oracle 바이트의 CRLF를 LF로 바꾼 sha256과 16행 값을 assertEqual로 비교한다(test_t2rc_eq_none.py:43-47). 계산 방식은 oracle 자체의 `sha256_lf`(t2rc-oracle.py:110-113)와 같다. 이 방식과 러너의 PowerShell 계산이 같은 값을 낸다는 것은 앞선 Judge가 확인했다(rrec-ev4-remove-judge-report.md:32). 이번 diff는 첫 줄을 건드리지 않고 ASCII 줄만 추가했다. CRLF도 2490줄 전부 유지된다(Grep으로 `\r` 없는 줄 0건). |
| G8-5 다른 고정 위치 | PASS | 새 값은 러너 16행에만 있다. 옛 값 6a74f813…은 이미 끝난 일회용 merge 스크립트(close-confirm-e-merge-2026-10-21.ps1:19, rrec-ev4-remove-merge-2026-10-19.ps1:18)와 기록 JSON·md에만 남아 있다. tools/와 t2rc-register-task.ps1에서는 검색 결과가 0건이다. test_auto_core_rg1_oracle_parity.py:27은 경로만 쓴다. 운영 코드에 러너 해시를 고정한 곳도 없다. |
| G8-6 주문·권한 표지 | PASS | diff.patch에서 `/api/us/ordr`, `ust2000`, `ust2001`, `order_submit`, `quantity_authority`, `kill_switch`를 검색한 결과 0건이다. |

```json
{"verdict": "PASS", "class_ok": true, "items": [
 {"id": "G1", "result": "PASS", "evidence": "docs/claude/t2rc-oracle.py:1729-1730, 2026-2027"},
 {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/t2rc-eqnone4/changed-files.txt:1-4; .gitignore:31-32,151"},
 {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/t2rc-eqnone4/diff.patch:10,22-23,31-32"},
 {"id": "G4", "result": "PASS", "evidence": "docs/claude/t2rc-oracle.py:1766-1768, 1898-1909, 2027, 2115"},
 {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_t2rc_eq_none.py:16-17"},
 {"id": "G6", "result": "PASS", "evidence": "workspace/outputs/dev-runs/t2rc-eqnone4/checks.json:94-105"},
 {"id": "G7", "result": "PASS", "evidence": "workspace/outputs/dev-runs/t2rc-eqnone4/diff.patch (no authority markers)"},
 {"id": "G8-1", "result": "PASS", "evidence": "workspace/outputs/dev-runs/t2rc-eqnone4/changed-files.txt:1-4"},
 {"id": "G8-2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/t2rc-eqnone4/diff.patch:18-32"},
 {"id": "G8-3", "result": "PASS", "evidence": "docs/claude/t2rc-oracle.py:1601-1603, 1730, 1735, 1766-1768, 1904-1909, 2025-2027; manage-us-stock-strategy/scripts/auto_core_tickets.py:1068-1070, 1129-1131"},
 {"id": "G8-4", "result": "PASS", "evidence": "docs/claude/t2rc-check-run.ps1:16, 61-68; manage-us-stock-strategy/tests/test_t2rc_eq_none.py:43-47; workspace/outputs/dev-runs/t2rc-eqnone4/checks.json:97-105; docs/claude/t2rc-oracle.py:110-113; docs/claude/rrec-ev4-remove-judge-report.md:32"},
 {"id": "G8-5", "result": "PASS", "evidence": "docs/claude/t2rc-check-run.ps1:16; docs/claude/close-confirm-e-merge-2026-10-21.ps1:19; docs/claude/rrec-ev4-remove-merge-2026-10-19.ps1:18; manage-us-stock-strategy/tests/test_auto_core_rg1_oracle_parity.py:27"},
 {"id": "G8-6", "result": "PASS", "evidence": "workspace/outputs/dev-runs/t2rc-eqnone4/diff.patch (marker search 0 hits)"}
], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-26T02:33:53Z
- 병합 커밋: `c1a6a6e452f5aac4f99b2c11ec3ef64355e26416` · 방식: ff

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/t2rc-eqnone4/ 의 원본 기록입니다.)
