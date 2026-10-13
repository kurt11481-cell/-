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

## 5. 알림 v2.1 변경점 (적용 2026-10-13 09:05 KST, trig_01D5KxMSJgbeRG1ZL5ox3Fna, 시각·모델·주기 불변)

- 읽기: device_bash 금지 → device_list_dir(R) → device_stage_files(LATEST.json, LATEST_DECISION.json, 오늘 decision.rerun-*.json) → 클라우드 python(read.py, 인자 = TODAY·stagedPath).
- 날짜: 클라우드 `TZ=Asia/Seoul date +%F` 값만(TODAY). read.py가 다시 계산해 다르면 MISMATCH 알림.
- 연결 실패: 60초 뒤 1회 재시도, 그래도 실패면 "알림 불가(컴퓨터 연결 안 됨)".
- 대시보드 core 옮기기·알림 조건 ①~⑪은 v2 그대로(⓪ 날짜 불일치만 추가).
- 원문: docs/claude/scheduled-prompts/auto-core-alert.txt (sha256 66548192913d…). 오늘 파일로 read.py·core.py 실행 확인(TODAY OK, T1·D FRESH).

## 6. 오늘 수동 실행 결과 (비교 모드, 주문·상태 파일 변경 없음)

- daily 08:46~08:59 KST: HOLD. 30분봉 10종목 OK(10/12까지 134세션 연속), 노출 OK. 계좌 거래내역 조회 ust21100(10/10~10/13)이 KIWOOM_API_RESPONSE_ERROR 코드 2 → I1 FAIL → I2·I3 FAIL, CASH_FLOW_EVIDENCE_NOT_READ. 대조 연속 0.
- 브로커 스냅샷: 보유 MVLL 159·NBIS 13·SOXL 53 = 상태 파일과 같음(수량 일치). SOXL 결제 기준 75주는 이전 매도 22주가 결제 전이라서다(매도 결제 예정 $3,072.51). G1_STATE_NOT_EQUAL_BROKER는 **현금** 차이 — 상태 현금 $9,395.21(결제 기준) vs 브로커 주문가능 $12,469.18(결제 전 매도대금 포함). 정의 차이는 redesign-t2-compare-b7-2026-10-13.md. (09:00 사용자 보고의 'SOXL 수량이 상태 파일과 다름'은 잘못 — 09:20 정정)
- decide 08:59: HOLD, 주문표 0. G1_RECONCILE_NOT_OK, G1_S7_FAIL_CLOSED(노출·자산·고점선·현금흐름 확인 불가), G1_STATE_NOT_EQUAL_BROKER. 연구 기록 OK. 06:40 LLM 점검과 비교 차이 8건(설명 필요), 연속 0/5.
- 대시보드: 통합점검 대시보드 runs/2026-10-13 core 칸 반영(Cowork, 09:04, version 2).
- 다음: ust21100 코드 2 원인 확인(7절).

## 7. ust21100 오류 코드 2 확인 (2026-10-13 09:06 KST)

- 같은 조회를 MCP로 다시 함(읽기 전용, profile 실전계좌·mode real, 10/10~10/13 전체): return_code 20 "[2000](501724:관련자료가 없습니다)" — 브리지가 "내역 없음"으로 통과시키는 정상 응답. 요청 형식 결함은 아님.
- 08:46 실행 때 코드 2의 뜻: 확인 필요(브리지는 return_msg를 저장하지 않음 — 계좌번호 포함 가능). 저장소 기록에 코드 2 전례 없음. 일시 오류로 보이나 단정하지 않는다.
- 조치: 이번에는 코드 변경 없음(NO_CHANGE). 내일 06:15 실행이 재시도다. 같은 코드 2가 다시 나오면 재시도 대상 분류(retryable_failure_types) 검토를 별도 작업으로 올린다.
- 참고: 거래내역(10/10~10/13)에 행이 없으므로, 브로커의 SOXL 보유 53주·결제 기준 75주 차이는 거래내역(결제 기준)에 아직 잡히지 않은 상태로 보인다(확인 필요). 체결은 브로커 체결 기록으로만 판단한다.
- runner-fix: 큐 09:02 → dev-run 시작 09:05(Builder attempt 1).
