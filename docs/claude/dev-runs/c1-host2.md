# dev-run c1-host2 — NEEDS_APPROVAL

- 시각(UTC): 2026-10-15T05:30:12Z → 2026-10-15T05:51:25Z
- 기준 커밋(base): `3ae958f2671b32b238cb45ade51e420988b9f75a` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: ORDER_MARKER:/api/us/ordr, ORDER_MARKER:kiwoom_order, ORDER_MARKER:order_submit, ORDER_MARKER:ust2000)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3069 · 실패 28 → 변경 후 Ran 3087 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `391960eb99468ab09089a3ea2cf9fb3289a0fc551cf6257a062824490f49335f`
- Judge 파일 sha256: `ad32624750944d4e4f37f02b0daa9d7e9fbde7982b035d08a02d3ce3b325bb4f`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 c1-host2 -ApproveAuthority`

## 바뀐 파일

- `docs/claude/c1-host2-report.md`
- `manage-us-stock-strategy/scripts/host_status.ps1`
- `manage-us-stock-strategy/scripts/register_host_status_task.ps1`
- `manage-us-stock-strategy/tests/test_host_status_static.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | host_status.ps1:156-256에서 점검 7개를 모두 실제로 읽는다. 최상위 필드는 host_status.ps1:286-298, 임시 파일에 쓴 뒤 교체는 :301-310. register_host_status_task.ps1:22-25,67-97. TODO나 하드코딩 없음. PowerShell은 실행하지 못했고 보고서에 그 사실을 적었다(c1-host2-report.md:13). 지시문이 허용한 처리(task-prompt.md:59) |
| G2 범위 | PASS | changed-files.txt:1-4는 새 파일 4개뿐이고 allowed_paths(task-prompt.md:14)와 같다. 수정·삭제 없음(checks.json:23-40). stock-strategy-system 파일은 보호 경로라 해시로 대조하며(devpipe.py:112,752-761) 위반 없음(checks.json:52-53) |
| G3 주문·체결 추정 | PASS | host_status.ps1:1,269-277에 키움·네트워크 호출, 주문 경로, 체결 추정이 없다. ORDER_MARKER 4건(checks.json:43-48)은 모두 test_host_status_static.py:29의 '없어야 함' 검사 문자열이다 |
| G4 정책·상태 쓰기, fail-closed | PASS | 쓰는 곳은 출력 파일 하나뿐이다(host_status.ps1:265,301-310). 실패하면 UNKNOWN(:46-47), 자동 로그인 값이 없으면 WARN(:158-159), 활성 시간이 없으면 UNKNOWN(:206-207), 전원 값을 못 읽으면 UNKNOWN(:189-191). 기본값으로 OK가 되는 경로 없음 |
| G5 비밀·계좌 식별자 | PASS | Winlogon에서는 AutoAdminLogon 하나만 읽는다(host_status.ps1:157, 이름을 지정한 GetValue는 :62). 테스트가 이를 확인한다(test_host_status_static.py:90-99). 호스트 이름과 Windows 사용자 이름(host_status.ps1:252-254,291)은 지시문(task-prompt.md:40-41)이 요구한 값이다 |
| G6 테스트 | PASS | 테스트 18개(test_host_status_static.py:56-213). 대상 테스트 18개 OK, 새 실패 0, 전체 실패 28→28(checks.json:91-108). 단언 약화·skip·expectedFailure 없음. 참고: 작업이 꺼져 있으면 WARN(host_status.ps1:133)은 지시문 밖에서 경고를 하나 더한 것이고, 직접 검사하는 단언은 없다(막는 사항 아님) |
| G7 class | PASS | 주문 단계·주문 도구·예산·상한·승인 상품·대조 불변 조건·kill switch·quantity_authority 중 바뀐 것 없음. order_authority는 $false로만 쓰인다(host_status.ps1:297, register_host_status_task.ps1:61). authority로 올라간 것은 테스트 문자열 때문뿐이라 class_ok=true |
| J-a 파일 4개, 코어 파일 그대로 | PASS | changed-files.txt:1-4. auto_core*.py, run_auto_core.ps1, register_auto_core_task.ps1은 목록에 없다 |
| J-b 읽기 전용·항목별 격리·종료 코드 0 | PASS | 항목마다 Invoke-Check로 감싸 실패는 그 항목만 UNKNOWN이 된다(host_status.ps1:38-49). 레지스트리는 읽기 전용으로 연다(:54). powercfg는 조회 옵션만 쓴다(:85,95). 바깥 catch와 `exit 0`은 :312-315. 호출 cmdlet 허용 목록은 테스트가 확인한다(test:75-83) |
| J-c Winlogon 다른 값 | PASS | Winlogon 읽기는 host_status.ps1:157 한 곳뿐이다. 주석은 "other Winlogon values"로만 쓴다(:12). 금지 토큰(DefaultPassword 포함)과 Winlogon 읽기 1건을 테스트가 확인한다(test:68-73,90-99) |
| J-d status와 자정 넘김 계산 | PASS | 최상위 status는 WARN 먼저, 다음 UNKNOWN, 그 밖은 OK(host_status.ps1:280-281). 활성 시간 수식은 :77-79. 손계산: 22→10은 길이 12, 거리 7이라 7+4=11≤12로 OK. 8→2는 길이 18, 거리 21이라 25>18로 WARN. 테스트 11개 경우(test:141-149)와 맞다 |
| J-e register 범위와 PlanOnly | PASS | 작업 이름은 InvestmentV2-HostStatus 하나뿐이다(register_host_status_task.ps1:22-25). PlanOnly는 :67-70에서 `exit 0`으로 끝나고, 등록(:88)은 그 뒤에 있다. AutoCore 이름이 없음은 테스트가 확인한다(test:183-199) |
| J-f 키움·주문 표지·권한 값 | PASS | 두 .ps1 모두 kiwoom과 주문 이름이 없다(test:202-213). 권한 값은 false로만 쓰인다 |
| J-g 테스트 안 주문 표지 | PASS | 표지 문자열은 test_host_status_static.py:29의 ORDER_NAMES뿐이다. assertNotIn 검사(:207-209)에만 쓰이고 호출이나 경로가 아니다. class_ok=true의 근거 |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/host_status.ps1:156-310; manage-us-stock-strategy/scripts/register_host_status_task.ps1:22-97; docs/claude/c1-host2-report.md:13"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/c1-host2/changed-files.txt:1-4; checks.json:23-40,52-53"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/host_status.ps1:1,269-277; ORDER_MARKER only in manage-us-stock-strategy/tests/test_host_status_static.py:29"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/host_status.ps1:46-47,158-159,189-191,206-207,265,301-310"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/host_status.ps1:62,157,252-254; manage-us-stock-strategy/tests/test_host_status_static.py:90-99"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_host_status_static.py:56-213; checks.json:91-108"}, {"id": "G7", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/host_status.ps1:297; manage-us-stock-strategy/scripts/register_host_status_task.ps1:61; checks.json:43-48 (test absence strings)"}, {"id": "G8", "result": "PASS", "evidence": "J-a changed-files.txt:1-4; J-b host_status.ps1:38-49,54,85,95,312-315; J-c host_status.ps1:12,157; J-d host_status.ps1:77-79,280-281; J-e register_host_status_task.ps1:22-25,67-70,88; J-f test_host_status_static.py:202-213; J-g test_host_status_static.py:29,207-209"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-15T06:00:32Z
- 병합 커밋: `1a0171af8275d678a8c0866759612c1ac4ef4998` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-10-15T06:00:30Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/c1-host2/ 의 원본 기록입니다.)
