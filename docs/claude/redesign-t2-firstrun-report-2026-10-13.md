---
id: redesign-t2-firstrun-report-2026-10-13
title: 재설계 T2 첫 운영일(2026-10-13) — 예약 실행 실패 원인·결정·수정
date: 2026-10-13
status: 수정 진행 중(runner-fix 큐 대기, 알림 v2.1 적용)
---

## 1. 무슨 일이 있었나 (KST)

| 시각 | 작업 | 결과 | 근거 |
|---|---|---|---|
| 06:15 | InvestmentV2-AutoCore (daily) | RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND | workspace/outputs/auto-core/logs/auto-core-daily-20261012T211501Z.log |
| 06:40 | 통합 점검(trig_01YWzNq847nJfNgDUnnukBqP) | 연구 기록 정상 작성 06:57:49 | workspace/outputs/research-records/2026-10-13/research-record.json |
| 07:45 | InvestmentV2-AutoCoreDecide (decide) | RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND | auto-core-decide-20261012T224501Z.log |
| 08:46 | 사용자 수동 실행 docs/claude/redesign-t2-firstrun-2026-10-13.ps1 (-PythonPath 지정) | 진행 중 → 6절 | auto-core-daily-20261012T234614Z.log, env-diag-20261013.txt |
| 08:50 | 알림(trig_01D5KxMSJgbeRG1ZL5ox3Fna) | 파일 읽기 실패, 날짜 10/12로 잘못 표시 | 사용자 전달 출력 |

## 2. 원인

### 2-1. 06:15·07:45 — 실행 스크립트 변수 충돌 (확정)

- `manage-us-stock-strategy/scripts/run_auto_core.ps1` 47~49행 `$command = Get-Command python.exe ...`가 `[string]$Command` 인자와 같은 변수다(PowerShell 변수 이름은 대소문자 무시). CommandInfo가 문자열로 바뀌고 `.Source`가 비어 `$PythonPath`가 빈 값 → `PYTHON_RUNTIME_NOT_FOUND`.
- 재현: pwsh에서 같은 구조 → `type=String value=pwsh source=[]`.
- 환경은 정상: env-diag-20261013.txt — 사용자 PATH에 Python 3.13, kiwoomcli 있음, PowerShell 프로필 없음, 작업 5개 모두 Interactive/Limited.
- 같은 패턴 정적 검사: 추적 .ps1 13개 중 이 파일만 해당.

### 2-2. 08:50 알림 — 예약 세션 폴더 읽기 방식·날짜

- 예약 세션에서 `device_bash`의 `$HOME/mnt` 폴더가 보이지 않음 → 결과 파일 0개 읽음.
- 날짜를 UTC(10/12)로 잡음. 10/13 폴더는 한국 날짜 기준 오늘 폴더(수동 실행이 만듦)로 정상.

## 3. 결정 기록

- "결정 runner-fix: 승인" — 2026-10-13 08:58 KST, 사용자. 범위: run_auto_core.ps1 변수 이름 변경 + 회귀 테스트(test_auto_core_runner.py). dev 파이프라인 authority(경로 때문) → 병합 `.\tools\dev-merge.ps1 runner-fix -ApproveAuthority`.
- "결정 redesign-t2: 예약 작업 변경 승인(알림 v2.1)" — 2026-10-13 08:58 KST, 사용자. 범위: 알림 작업 프롬프트 v2 → v2.1(읽기 방식·KST 날짜). 시각·모델·주기 불변.

## 4. 수정

- runner-fix: 지시문 docs/claude/runner-fix-builder-prompt.md. 수동 실행이 끝난 뒤 큐에 넣는다(실행 중 메인 체크아웃 변경으로 STOP_MAIN_TOUCHED 방지). 내일 06:15 전 병합 필요.
- 알림 v2.1: docs/claude/scheduled-prompts/auto-core-alert.txt 갱신(5절).

## 5. 알림 v2.1 변경점

(아래 7절 적용 기록 참조)

## 6. 오늘 수동 실행 결과

확인 중.
