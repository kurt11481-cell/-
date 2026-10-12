# dev-run c1-host-status — NEEDS_APPROVAL

- 시각(UTC): 2026-10-12T07:06:56Z → 2026-10-12T07:31:33Z
- 기준 커밋(base): `58cce53bc8d9abd0a2bf3035dee472377a708e27` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: ORDER_MARKER:/api/us/ordr, ORDER_MARKER:kiwoom_order, ORDER_MARKER:order_submit, ORDER_MARKER:ust2000)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 2910 · 실패 28 → 변경 후 Ran 2923 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `1252693e405aeb859f577423e5a5577e9dbf2b09168f27c0486387d02e0a7ec9`
- Judge 파일 sha256: `652f0acedbb816ac6e5099741f3cc7a57c4d4827fb368deec95d390695e2528f`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 c1-host-status -ApproveAuthority`

## 바뀐 파일

- `docs/claude/c1-host-status-report.md`
- `manage-us-stock-strategy/scripts/host_status.ps1`
- `manage-us-stock-strategy/scripts/register_host_status_task.ps1`
- `manage-us-stock-strategy/tests/test_host_status_static.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | host_status.ps1:235-288 — 7개 점검을 모두 실제로 읽음. 최상위 필드와 임시 파일 뒤 교체 방식도 구현됨. register_host_status_task.ps1:21-24,65-96. TODO나 하드코딩 없음. PowerShell은 실행하지 못했고 보고서에 그 사실을 적음(c1-host-status-report.md:20). 지시문 50줄이 허용한 처리 |
| G2 범위 | PASS | changed-files.txt:1-4는 모두 새로 추가된 파일이고 allowed_paths 4개와 정확히 같음. checks.json:23-38에서 수정·삭제는 없음 |
| G3 주문·체결 추정 | PASS | host_status.ps1:7-10에 브로커·네트워크 호출이 없다고 적혀 있음. 주문 경로와 체결 추정 코드 없음. checks.json:41-46의 ORDER_MARKER 4건은 모두 테스트가 검사에 쓰는 정규식 글자(test_host_status_static.py:24-27)이고 주문 코드는 아님 |
| G4 정책·상태 쓰기와 fail-closed | PASS | 쓰는 곳은 workspace\outputs\host-status\LATEST.json(.tmp 거쳐 교체) 하나뿐(host_status.ps1:267-287). 읽지 못하면 UNKNOWN(31-39). 자동 로그인 값이 없으면 WARN(140-142). 전원 값이나 활성 시간이 없으면 UNKNOWN(181, 190-202). 기본값으로 OK가 되는 경로 없음 |
| G5 비밀·계좌 식별자 | PASS | Winlogon에서는 `GetValue("AutoAdminLogon")` 하나만 읽음(host_status.ps1:136-148). 테스트가 확인함(test_host_status_static.py:68-75). 호스트 이름과 Windows 사용자 이름은 지시문 31-32줄이 요구한 값이고 계좌 식별자가 아님 |
| G6 테스트 | PASS | 테스트 13개(test_host_status_static.py:38-166), 자정을 넘는 경우를 포함한 수식 9개 경우 검증(104-130). checks.json:94-106에서 새 실패 0, 대상 테스트 OK, 단언 약화·skip·expectedFailure 없음 |
| G7 class | PASS | 주문 단계, 도구, 예산, 상한, 승인 상품, 대조 불변 조건, kill switch, quantity_authority 중 바뀐 것 없음. `order_authority = $false`(host_status.ps1:263, register_host_status_task.ps1:59). 스크립트가 class를 authority로 올린 이유는 G3의 테스트 정규식 글자 때문뿐이라 class_ok=true |
| J-a 파일 4개, 코어 파일 그대로 | PASS | changed-files.txt:1-4. `auto_core*.py`, run_auto_core.ps1, register_auto_core_task.ps1은 바뀐 목록에 없음 |
| J-b 읽기 전용, 항목별 격리, 종료 코드 0 | PASS | powercfg는 조회 옵션만 씀(host_status.ps1:57-80, 153). 항목마다 Invoke-Check로 UNKNOWN 처리(31-39, 237-243). 바깥 catch와 `exit 0`은 289-292. 상태를 바꾸는 cmdlet 없음(test:53-58) |
| J-c AutoAdminLogon 외 값 | PASS | host_status.ps1:137-139. 주석에도 "other Winlogon values"로만 적음(7, 137). DefaultPassword 글자 없음(test:47-51) |
| J-d status와 자정 넘김 계산 | PASS | host_status.ps1:245-248은 WARN이 먼저, 그다음 UNKNOWN, 그 밖은 OK. 47-55에서 길이 `(E-S+24)%24`, 시작 차이 `(5-S+24)%24`, `차이+4 ≤ 길이`로 계산함. 8→2는 WARN, 22→10은 OK로 손계산 결과와 맞음 |
| J-e register 범위와 PlanOnly | PASS | register_host_status_task.ps1:21-24는 이름 1개만 다룸. 65-68에서 PlanOnly면 등록 전에 `exit 0`. AutoCore 이름 없음(test:134-150). register_auto_core_task.ps1과 구조가 같음 |
| J-f 키움·주문 표지·권한 값 | PASS | 두 .ps1 모두 kiwoom 글자 없음(test:47-51, 159-166). 권한 값은 false로만 쓰임 |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/host_status.ps1:235-288; manage-us-stock-strategy/scripts/register_host_status_task.ps1:21-96"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/c1-host-status/changed-files.txt:1-4; checks.json:23-38"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/host_status.ps1:7-10; ORDER_MARKER hits only in manage-us-stock-strategy/tests/test_host_status_static.py:24-27 (detection regex)"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/host_status.ps1:31-39,140-142,181,190-202,267-287"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/host_status.ps1:136-148; manage-us-stock-strategy/tests/test_host_status_static.py:68-75"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_host_status_static.py:38-166; checks.json:94-106"}, {"id": "G7", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/host_status.ps1:262-263; manage-us-stock-strategy/scripts/register_host_status_task.ps1:59"}, {"id": "G8", "result": "PASS", "evidence": "J-a changed-files.txt:1-4; J-b host_status.ps1:31-39,57-80,289-292; J-c host_status.ps1:136-148; J-d host_status.ps1:47-55,245-248; J-e register_host_status_task.ps1:21-24,65-68; J-f test_host_status_static.py:159-166"}], "min_fixes": []}
```

VERDICT: PASS

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/c1-host-status/ 의 원본 기록입니다.)
