---
id: new-pc-recovery-procedure
type: runbook
title: "새 PC 복구 절차 1장 (D11)"
as_of: "2026-10-25 KST, 기준 커밋 bb11f04 + workspace/outputs/backup/LATEST.json(2026-10-24 23:50 KST)"
class: "절차 문서. 확인된 사실만 적고 모르는 단계는 '확인 필요'. 주문·권한·정책·상태 변경 없음"
authority: "order_authority=false · quantity_authority=none"
source_decision: "사장 D11 승인(2026-10-25 08:46Z, d6-builder-prompt.md) · 근거 operating-diagnosis-2026-10-25.md 9-2"
consumers: "사장(PC 고장·교체 때) · 사장실 회사PC 스레드(복구 점검 안내) · redesign-t4 RUNBOOK.md 첫 판 입력"
---

# 요점

- 복구 재료는 둘이다: ① GitHub origin의 **백업이 push한 브랜치**(추적 파일), ② OneDrive의 **날짜별 zip**(추적 안 되는 기록 파일). 비밀(.env·토큰·인증)은 어디에도 백업되지 않는다 — 의도된 것이다.
- 복구 중에는 자동 코어가 돌지 않으므로 주문표가 나오지 않는다. 주문표 미입력은 정상 상태이고 안전 쪽이다(operating-diagnosis-2026-10-25.md 3절 사업 연속성 줄).
- 세션(Claude Code·Cowork·예약 작업)은 인증·로그인·토큰 재발급을 하지 않는다(CLAUDE.md Kiwoom query rules). 인증을 다시 세우는 일은 사장 본인 단계다.

# 1. 지금 백업되는 것 (확인된 사실)

| 항목 | 내용 | 근거 |
|---|---|---|
| 작업 | Windows 작업 `InvestmentV2-OffsiteBackup`, 매일 23:50(KST), 제한 30분, Interactive·Limited | manage-us-stock-strategy/scripts/register_offsite_backup_task.ps1:8-10·24 |
| A. push | 현재 브랜치만 `origin`의 같은 이름으로 push. `main`이면 건너뜀("main is PR-only"), 분리 HEAD도 건너뜀. 나가는 커밋 경로에 비밀 같은 이름이 있으면 push 안 함 | offsite_backup.ps1:111-182 |
| B. zip | `%OneDrive%\InvestmentV2-Backup\<KST 날짜>.zip`, 최신 30개 보관. zip 안 경로 = 저장소 기준 상대 경로 | offsite_backup.ps1:15·252·270-292·316-317·346-347 |
| zip 내용 | `stock-strategy-system`의 추적 안 되는 파일(`.tmp_skill_validation/`·`skill-staging/`·숨김 파일 제외) + `workspace/outputs`의 폴더 10개: auto-core, regular-session-closes, research-records, journal-scores, decisions, reconciliation, exposure-review, holding-cards, status, host-status | offsite_backup.ps1:29-31·184-226 |
| 제외 | 비밀 이름 규칙(.env*, *.pem/key/p12/pfx/ppk, credentials*.json, secrets*.json, token(s).json, id_rsa 등)·`/secrets/` 폴더·`auth.json` / `official-event-intake`(약 278MB, 공식 출처에서 다시 받을 수 있음) / `activation` / `dev-runs` / `workspace/private_inputs` | offsite_backup.ps1:24·27-28·42-51; offsite-bak-report.md 복사 대상 줄 |
| 자체 검사 | 압축 뒤 zip을 다시 열어 항목 수 = 복사한 파일 수일 때만 저장. **해시 대조는 하지 않음**. "sync completion not verified"(OneDrive 업로드 완료는 확인 안 함) | offsite_backup.ps1:294-306·235 |
| 결과 파일 | `workspace/outputs/backup/LATEST.json`(schema `backup-status/v1`). 05:50 host_status의 `backup_recent`가 26시간 넘으면 WARN | offsite_backup.ps1:9·349-388; offsite-bak-report.md host_status 줄 |
| 최근 결과 | 2026-10-24 23:50 KST: status OK, push OK(브랜치 `codex/master-recovery-expansion`), zip 822개 = 항목 822개, 4,361,723바이트, 보관 5개, 잠긴 파일 0 | workspace/outputs/backup/LATEST.json(이 세션에서 읽음) |

# 2. 새 PC 복구 순서

각 단계 끝의 [ ]는 확인된 사실이면 근거, 아니면 "확인 필요".

1. **시간대**: Windows 시간대를 "Korea Standard Time"으로. 작업 등록 스크립트가 이것을 확인한다 [register_offsite_backup_task.ps1:9·29-30].
2. **도구 설치**: Git, Windows PowerShell 5.1(기본 포함), Python, OneDrive 로그인. Python 버전과 설치 경로는 확인 필요. 패키지 목록은 `manage-us-stock-strategy/requirements.txt`·`requirements-eval.txt`가 있다 [git ls-files]. 설치 명령과 가상환경 위치는 확인 필요.
3. **저장소 받기**: origin에서 clone하고, 옛 PC의 마지막 `LATEST.json`의 `push.branch`(10/24 기준 `codex/master-recovery-expansion`)를 checkout한다. 옛 PC를 읽을 수 없으면 origin의 브랜치 목록에서 가장 최근 것을 고른다. 저장소 폴더 경로(지금 `E:\사업\##금동한\코덱스저장소`)를 똑같이 맞춰야 하는지는 확인 필요(경로를 적어 둔 기록 파일이 있을 수 있음).
4. **기록 파일 복원**: OneDrive의 `InvestmentV2-Backup`에서 가장 최근 `YYYY-MM-DD.zip`을 저장소 루트에 푼다(zip 안 경로가 저장소 기준이므로 `stock-strategy-system\…`, `workspace\outputs\…`로 들어감) [offsite_backup.ps1:220·270-292]. OneDrive가 그 zip을 실제로 다 올렸는지는 백업이 확인하지 않으므로, 풀기 전에 zip 크기를 그날 `LATEST.json`의 `copy.bytes`와 비교한다.
5. **백업에 없는 것 다시 세우기**:
   - 비밀·인증(.env, 키움 앱 키·토큰, 기타 자격 증명): 사장 본인이 세운다. 키움 MCP 설치 기록은 manage-us-stock-strategy/references/kiwoom-mcp-local-integration.md 44-56행(설치 원천 `.runtime-cache/…`, 패키지 버전)에 있지만 `.runtime-cache/`는 .gitignore 대상이고 zip에도 없다. **설치·인증 재설정 순서는 확인 필요.** 키움 조회는 프로필 `"실전계좌"`, mode `"real"`을 쓴다(CLAUDE.md Kiwoom query rules).
   - `workspace/private_inputs`(브로커 스냅샷·웹 캡처·현금 흐름 증거 등): 백업 제외. 다시 만드는 방법 확인 필요.
   - `official-event-intake`: 공식 출처에서 다시 받을 수 있다고 적혀 있으나 그 절차·스크립트는 확인 필요.
   - `activation`, `dev-runs` 출력 폴더: 백업 제외. 복구에 필요한지 확인 필요.
   - 환경 변수 `SEC_USER_AGENT`: SEC 섀도 작업이 이 값을 환경 변수에서 읽는다 [register_sec_scheduled_shadow_task.ps1:45]. 값과 설정 위치는 확인 필요. 다른 작업이 요구하는 환경 변수가 더 있는지도 확인 필요.
6. **Windows 작업 다시 등록**(아래 SEC를 뺀 다섯 스크립트에는 계획만 보여 주는 `-PlanOnly` 스위치가 있다 [각 스크립트 grep]):
   - `register_host_status_task.ps1` → `InvestmentV2-HostStatus` 05:50
   - `register_auto_core_task.ps1` → `InvestmentV2-AutoCore` 06:15, `InvestmentV2-AutoCoreDecide` 07:45
   - `register_journal_score_task.ps1` → `InvestmentV2-JournalScore` 일요일 09:20
   - `register_offsite_backup_task.ps1` → `InvestmentV2-OffsiteBackup` 23:50
   - `register_sec_scheduled_shadow_task.ps1` → `GuardedPortfolio-SEC-Shadow-v0.1`(평일 22:00, 화~토 12:30)
   - `tools/register-dev-tasks.ps1` → `InvestmentV2-DocsCommit` 23:30, `InvestmentV2-DevQueue` 5분 간격
   [각 스크립트의 Name/TriggerTime 줄]. 이것이 전체 목록인지(진단 문서는 "Windows 작업 8개"), 그리고 claude.ai 예약 작업(08:40 독립 대조, 06:40 통합 점검 등)이 PC 교체 뒤 다시 연결해야 하는지는 확인 필요.
7. **Claude Code·Desktop Commander·Obsidian 설정**: 확인 필요(설정 파일 위치와 백업 여부 미조사).
8. **복구 확인**: 다음 05:50 `workspace/outputs/host-status/LATEST.json`의 각 항목(특히 `backup_recent`), 다음 06:15 자동 코어 출력, 23:50 백업 `LATEST.json` status OK를 본다. 대조가 HOLD나 FAIL이면 상태는 바뀌지 않고 알림만 나온다(fail-closed) — 그대로 두고 원인을 본다.

# 3. 복구 점검(훈련) — 지금 PC에서 1회

- 스크립트: `docs/claude/restore-hash-check-2026-10-25.ps1`. 최신 zip을 `%TEMP%` 아래 새 폴더에 풀고, 풀린 파일마다 저장소의 같은 파일과 sha256을 비교해 화면에만 출력한 뒤 임시 폴더를 지운다. 저장소·백업 폴더에는 쓰지 않는다.
- 사장 PowerShell 한 줄(저장소 루트에서, 23:50 백업 직후가 가장 깨끗함):
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\docs\claude\restore-hash-check-2026-10-25.ps1`
- 읽는 법: `result=PASS`면 zip이 복구 재료로 온전하다. `DIFF` 줄은 백업 뒤에 그 파일이 다시 쓰였다는 뜻일 수 있다(예: 05:50 이후 LATEST.json) — 줄에 적힌 원본 수정 시각이 백업 시각보다 뒤면 정상. `MISSING_ORIGINAL`은 백업 뒤 지워졌거나 옮겨진 파일. `RESTORE_CHECK_FAIL`은 zip을 못 찾았거나 못 연 것.
- 이 점검은 반복 예약 작업으로 만들지 않는다(D3 동결). 주기는 진단 문서 제안대로 연 1회이고, 기록 위치는 확인 필요.

# 4. 확인 필요 모음

Python 버전·가상환경·설치 명령 · 저장소 경로 고정 여부 · 키움 MCP 설치와 인증 재설정 순서 · private_inputs·official-event-intake·activation·dev-runs 재생성 · Windows 작업 전체 목록 · claude.ai 예약 작업 재연결 · Claude Code·Desktop Commander·Obsidian 설정 · 복구 점검 결과 기록 위치.

바뀔 조건: offsite_backup.ps1의 복사 대상·제외 목록이 바뀌거나, 위 확인 필요 항목 중 하나가 원문으로 확인되면 이 문서를 고친다.
