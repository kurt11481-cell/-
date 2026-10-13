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

## 8. runner-fix 병합 실패와 기준선 오염 (09:30 KST)

- 사용자 `.\tools\dev-merge.ps1 runner-fix -ApproveAuthority` → `DEV-MERGE STOP_INTERNAL_ERROR type=PermissionError`. merge.err: main이 docs 커밋으로 6012f2f → 1e0b511로 움직여 dev-merge가 rebase 경로로 감 → rebase 성공(worktree-runner-fix 1066005, 부모 1e0b511) → 재시험용 기준선 준비 중 임시 worktree `_base-1e0b511c` 삭제에서 WinError 32. 그 worktree는 같은 시각 dev-run cmp-fix가 기준선 전체 시험을 돌리던 곳이다(같은 base라 이름이 같음).
- 영향: cmp-fix 기준선이 오염됨(ran 2547, errors 1034, schema MISSING — 정상은 ran 2944, 실패 28, schema PASS)이고 캐시 `_baseline/1e0b511…-py3.13.15-b2.json`으로 저장됨. 이 캐시를 쓰면 새 실패가 가려진다 → Cowork가 `_baseline/_invalid-20261013/`로 옮김(삭제 아님, README 동봉). cmp-fix 결과는 쓰지 않는다(병합 금지), runner-fix 병합 뒤 새 id로 다시 큐.
- runner-fix worktree는 rebase된 상태로 남음 → `docs/claude/runner-fix-merge-retry-2026-10-13.ps1`: 잠금 해제 대기 → devpipe undo와 같은 복구(reset --keep 8fee428, reset --soft 6012f2f, unstage) → dev-merge 재실행 → 병합되면 예약 작업 daily·decide 1회 실행(수정 검증, 사용자 질문 09:26).
- 파이프라인 결함(보호 경로 tools/** — 수동 경로): dev-merge의 rebase 경로가 dev-run 잠금을 잡지 않고, 기준선 임시 worktree 이름을 base로만 정해 실행 중인 dev-run과 겹칠 수 있다. 그때까지 운영 규칙: **dev-run이 돌고 있으면(_lock 있음) dev-merge를 하지 않는다.** 09:2x Cowork 안내("cmp-fix와 겹치지 않아 지금 병합해도 됨")가 틀렸다.
- 재시도 1(09:40, 복구 스크립트): 잠금 해제(cmp-fix는 00:39Z STOP_RUN_RECORD_CHANGED — 격리한 캐시 때문, 의도대로) → 복구 OK → dev-merge `STOP_DIFF_CHANGED reason=diff_hash`. 원인: rebase·reset 때 git(core.autocrlf)이 Builder가 LF로 쓴 새 파일 2개(runner-fix-report.md, test_auto_core_runner.py)를 CRLF로 다시 써서 바이트가 바뀜. 검증: LF·CRLF 조합 8개 중 (보고서 LF, ps1 CRLF, 시험 LF)만 result.json diff_hash와 일치. Cowork가 두 파일을 LF로 되돌림(내용 동일, diff_hash 일치 확인). 파이프라인 결함 추가: 복구·rebase 경로가 줄 끝을 바꿔 재시도를 막는다.
- 재시도 2(10:00~10:14): 병합 성공 `DEV-MERGE runner-fix MERGED sha=6d5ca15d mode=rebase`. 이어서 실제 예약 작업 1회: InvestmentV2-AutoCore 10:13:51 KST `RUNNER_START … command=daily` → `RUNNER_END exit=0`, InvestmentV2-AutoCoreDecide 10:14:18 → `RUNNER_END exit=0`. **실행 스크립트 수정이 실제 예약 경로에서 확인됨**(Python 자동 탐색).
- 결과는 그대로: daily HOLD(I1 ust21100 코드 2 — 다시 발생), decide HOLD, 주문표 0.
- cmp-fix는 새 id cmp-fix2로 다시 큐(10:2x).

## 9. ust21100 코드 2 — 일시 오류가 아님 (10:20 KST)

- 08:46과 10:13 두 번 모두 코어 브리지(kiwoom_account_readonly_bridge 외부 워커)의 ust21100(10/10~10/13)이 return_code 2. 같은 기간을 kiwoomcli(MCP, 09:06)로 조회하면 return_code 20 "[2000](501724:관련자료가 없습니다)"(정상 "내역 없음").
- 차이 후보(확인 필요): ① 본문 krw_repl_skip_yn — 브리지 ""(빈 값), CLI 기본 "N" ② 브리지 런타임(.env)과 CLI 프로필의 토큰·계좌 차이 ③ 앞선 일별 체결 조회 직후 호출 간격. 키움 명세 예시는 빈 값을 쓰므로 ①도 단정 못 함. 브리지는 return_msg를 저장하지 않는다(계좌번호가 섞일 수 있어 설계상).
- 영향: 매일 daily I1 FAIL → HOLD → 비교 연속 일수가 쌓이지 않고 T1 "켜"도 불가. 자동 운영 막힘 = 심각 결함.
- 브리지 본문 첫 실측: 이 경로(브리지로 ust21100)가 실계좌에서 돈 것은 오늘이 처음이다(10/02·10/10 실측은 MCP CLI).
- 다음: 읽기 전용 진단 1회 — 같은 런타임·같은 본문으로 ust21100을 부르고 return_code와 숫자를 가린 return_msg만 출력, krw_repl_skip_yn "" 대 "N" 비교.

## 10. ust21100 원인 확정 (10:26 KST, 사용자 실행 진단)

| 본문 | return_code | 메시지 |
|---|---|---|
| 브리지 그대로(tp "0", krw_repl_skip_yn "") | 2 | 입력 값 오류[1511: 필수입력 파라미터=krw_repl_skip_yn] |
| krw_repl_skip_yn "N" | 20 | [2000](501724:관련자료가 없습니다) — 정상 "내역 없음" |
| tp "", krw "N" | 2 | 입력 값 오류[1511: 필수입력 파라미터=tp] |

- 원인: 브리지 본문 `krw_repl_skip_yn: ""`. 명세는 선택(required N)이지만 서버는 필수. tp도 필수(지금 "0"이라 문제없음).
- 수정: 지시문 docs/claude/ust21100-fix-builder-prompt.md(본문 한 칸 "N", 회귀 테스트). 권한 경로라 사용자 결정 뒤 큐.
- 같은 위험 점검: ust21150(일별 체결)·ust21610(당일 매매)을 브리지 본문 그대로 부르는 진단 docs/claude/bridge-dated-diag-2026-10-13.py(읽기 전용). ust21610은 체결이 있는 날에만 불려 아직 실계좌에서 돈 적이 없다.
- 기록 실수(Cowork): 이미 커밋돼 비워진 _pending 파일에 경로만 덧붙여, 자동 커밋 5ccc6b7의 메시지가 경로(docs/claude/runner-fix-merge-retry-2026-10-13.ps1)가 됨(내용은 ust21100-diag-2026-10-13.py 1개). 이력은 고치지 않는다. 앞으로 _pending 파일은 매번 첫 줄(메시지)부터 통째로 쓴다.
- `결정 ust21100-fix: 승인` (2026-10-13 10:33 KST, 사용자) — 브리지 ust21100 본문 krw_repl_skip_yn "N" + 회귀 테스트. dev 파이프라인 ust21100-fix(경로 때문에 authority) 큐 10:3x. cmp-fix2 뒤 순서.
- 같은 위험 점검 결과(10:57 KST, 사용자 실행 bridge-dated-diag): 브리지 본문 그대로 ust21150 10/09 return_code 0(1행)·10/12 20 "[2000](571758:해당 계좌의 체결내역이 없습니다.)", ust21610 10/09 0(1행)·10/12 20 "[2000](571758:조회내역이 없습니다.)". 두 조회 모두 정상이고 no-data 문구는 브리지 등록 문구와 같다 → 추가 수정 없음(ust21100-fix 지시문 "추가 실측" = 해당 없음).

## 11. 병합 2건 (11:21 KST)

- `DEV-MERGE cmp-fix2 MERGED sha=9f554fce mode=rebase` — 대조 분류 수정 반영.
- `DEV-MERGE ust21100-fix STOP_BASE_MOVED reason=non_docs_commits` — ust21100-fix(Judge PASS, 본문 한 칸 "N" + 테스트)는 base fcc294b에서 만들어졌는데 그 뒤 cmp-fix2 코드 커밋이 병합됨. 파이프라인은 docs 커밋만 넘어 rebase한다(설계). → 같은 내용으로 ust21100-fix2 큐(11:2x), 병합은 merge-ust21100-fix2-2026-10-13.ps1(끝나길 기다렸다가 병합 → 예약 작업 1회 검증).
- 교훈: 코드를 바꾸는 dev-run 두 개를 연달아 큐에 넣으면 두 번째는 첫 번째 병합 뒤 다시 돌려야 한다. 앞으로는 앞 작업을 병합한 뒤 다음 작업을 큐에 넣는다(또는 파일이 겹치지 않으면 한 지시문으로 묶는다).

## 12. ust21100-fix2 병합과 검증 실행 (11:43~11:44 KST)

- ust21100-fix2: 기준선 정상(ran 2964, 실패 28, schema PASS), 새 실패 0, Judge PASS, diff = 본문 한 칸 "N" + 주석 2줄 + 새 테스트 + 보고서. `DEV-MERGE ust21100-fix2 MERGED sha=1fe378b5 mode=ff` (02:43:28Z).
- 예약 작업 검증: daily 11:43:29 → HOLD, 사유가 바뀜: I1 PASS(거래내역 조회 통과), I2 PASS, **I3 FAIL `CASH_CHANGE_NOT_EXPLAINED:1.47`**. decide 11:43:56 → HOLD(G1_RECONCILE_NOT_OK, G1_S7_FAIL_CLOSED, G1_STATE_NOT_EQUAL_BROKER), 주문표 0.
- I3 내용: 기준(10/09 23:52Z 스냅샷) 주문가능 $12,467.71 → 지금 $12,469.18, 체결 0·현금흐름 0 → 설명 안 된 +$1.47. 거래내역(MCP 10/01~10/13): 10/08·10/09 MVLL 매도 3건만, 마지막 외화예수금잔고 $9,395.21(10/09). 지금 외화예수금 $9,396.68 → 거래내역에 없는 +$1.47(이자·예탁금 이용료 등 추정 — 확인 필요). 불변 조건대로 멈춘 것(정상 동작, 허용 오차 $1.00).
- decide G1_STATE_NOT_EQUAL_BROKER: 상태 파일 현금 $9,395.21(rev 24, 옛 min 정의) vs 브로커 주문가능 $12,469.18. 비교 모드에서는 상태를 자동으로 고치지 않으므로, 사용자 확인 코드 대조 적용 전까지 남는다.

## 13. 현금 +$1.47 원인 검토 (12:4x KST)

결론: **예탁금 이용료(USD, 3분기분)일 가능성이 높다 — 금액 정확 대조는 확인 필요.**

- 키움 안내(사용자 캡처 12:35): 예탁금 이용료는 1·4·7·10월 **두 번째 일요일**에 지급, USD 3개월 평잔 $1,000 이하 연 2.00%, 초과 연 0.45%, 원화대용 설정금액 제외.
- 2026-10의 두 번째 일요일 = **10-11(일)**. I3 기준 스냅샷(10-10 08:52 KST)과 오늘 조회 사이에 든 유일한 지급일이다. 같은 기간 체결·입출금 없음(사용자 확인 + ust21100).
- ust21100(10/01~10/13, 전체·입금)에는 이 입금 행이 없다 → 이 API로는 예탁금 이용료가 보이지 않는다(또는 아직 반영 전). 그래서 코어가 설명하지 못했다.
- 금액 타당성(추정, D): ust21100 행의 외화예수금잔고로 본 3분기 평잔 ≈ $265(7/1~8/3 약 $7, 8/4~ $111, 8/13 $3,264 하루, 8/14~ $64, 8/24~ $519, 9/30 $6). 연 2.00% × 92/365 ≈ $1.33(세전) — 관측 $1.47과 같은 크기. 잔고 감소일(8/24 이후 $519 → 9/30 전 $0) 등 행에 없는 이동이 있어 정확히 맞추지는 못함.
- 판단: I3이 멈춘 것은 설계대로(브로커 기록으로 설명 안 되는 현금 변화는 자동 반영 금지). 원인 자체는 무해한 이자 수입으로 보인다.
- 다음 분기 영향: 지금 USD 잔고 약 $12.5k → 2027-01-10(일) 지급액은 0.45% 기준 약 $14 → 그다음 daily도 I3 HOLD가 거의 확실. 분기마다 사용자 확인 1번(연 4회)이 생긴다.
- 선택지(결정 필요, 기본 NO_CHANGE): ① 그대로 — 지급일 다음 날 HOLD를 사용자 확인 코드로 처리 ② 지급일 다음 첫 실행에서 작은 양(+) 현금 변화를 "예탁금 이용료 추정"으로 표시만(자동 반영 없음, 알림 문구로 이유를 알려 줌) ③ 자동 반영 — 브로커 기록 없는 추정 현금을 상태에 쓰는 것이라 불변 조건(I3) 변경 = K3, 권장하지 않음.
- 오늘 처리: 상태 파일 현금이 rev 24 옛 값($9,395.21)이라 어차피 대조 적용 1회가 필요하다. 그때 +$1.47을 예탁금 이용료로 확인하면 I3·G1이 함께 풀린다(사용자 확인 코드 절차).

### 13-1. 재검토 (사용자 요청 12:42)

- 결정 1(오늘 대조 적용) — **유지하되 효과를 낮춰 잡는다.** 비교 모드 설계상 상태 파일은 사람 경로(확인 코드)로만 바뀌고, compare_streak도 그 사람 기록과 대조한다(auto_core.py compare_streak). I3 기준은 마지막 사람 기록 스냅샷(10/09 23:52Z)이라 적용 전까지 +$1.47이 매일 남는다(아래 결정 2의 API 반영이 없다면). 적용하면 내일 daily의 I3와 decide의 G1_STATE_NOT_EQUAL_BROKER는 풀릴 것으로 본다. **정정**: S7 관문(G1_S7_FAIL_CLOSED)의 사유는 SALE_PROCEEDS_PENDING_CASH_CONFIRMATION·LINE_EVALUATION_ON_HOLD·CASH_FLOW_COVERAGE_GAP·CASH_FLOW_EVIDENCE_MISSING(포트폴리오 노출 검토 11:43)이라, 적용으로 모두 풀린다고 단정 못 함(확인 필요). 오늘 decide는 오늘 daily 결과를 읽으므로 적용해도 오늘 판정은 그대로다.
- 결정 2(분기 처리) — **지금 정하지 않는다(보류, 기본 NO_CHANGE).** 코어는 이미 거래내역 행 중 "이용료·이자"를 FEE_TAX_INTEREST(외부 흐름 아님)로 분류하고, 메모의 "입금"으로 부호를 정해 I3 현금 설명에 더한다(auto_core_reconcile.py 616~640행, 분류표 kiwoom-transaction-history-classification.json). 즉 **키움 API에 이자 행이 나타나기만 하면 지금 코드로 자동 설명된다.** 남은 질문은 API 노출 여부 하나 → 10/14 09:10 Cowork가 MCP로 재조회(사용자 손 0). 끝내 안 나타나면 그때 ②(표시만) 또는 ③(추정 자동 반영 = 불변 조건 변경, K3)를 결정. 다음 지급일 2027-01-10이라 급하지 않다.
- 관련 위험(확인 필요): ust21100 잔고 행으로 보면 8/24 이후 $518.73 → 9/30 전 $0으로 줄었는데 그 이동 행이 없다. 환전·출금이 API에 안 나오는 경우라면 그런 날마다 I3가 멈춘다(안전한 쪽). 사용자에게 9월 달러 이동(환전 등) 여부 확인 요청.
- 사용자 확인(12:49): 9월에 달러를 원화로 환전해 출금했다. ust21100(8/25~9/29, kind fx·all)에는 그 행이 없다 → **이 API는 환전·출금(외부 흐름)을 보여 주지 않는다**(확인된 사례 1건). 영향: 그런 날 I3는 설명 안 된 현금 감소로 멈춘다(안전한 쪽). 다만 cash_flow_evidence는 행이 없으면 NO_EXTERNAL_FLOW로 보므로, 사람 경로로 반영할 때 외부 출금을 따로 신고하지 않으면 S7 HWM·V6 선에서 출금이 손실처럼 보일 수 있다 — 설계 점검 필요(별도 작업, 확인 필요).
- 사용자 결정(12:49): 오늘 대조 적용 진행, 분기 처리 보류.

## 14. 대조 적용 (12:51~12:53 KST, 사용자 확인 코드)

- 사용자 propose 12:51:24(제안 workspace/outputs/reconciliation/20261013T035125Z) → Cowork show(경고 없음, 알림 엔진 검사 통과) → 사용자 "확인 E8877F23"(12:53) → apply: `revision 24 → 25 적용. 백업: stock-strategy-system/backups/portfolio_state.r24.20261013T035325948006Z.json`.
- 바뀐 것: 가용 현금 9,395.21 → 12,469.18(키움 주문가능, 정산 전 SOXL 매도대금 $3,072.51 + 예탁금 이용료 추정 $1.47), 브로커 확인 as_of 2026-10-12. 보유 수량 불변(MVLL 159·NBIS 13·SOXL 53).
- 다음: 사용자 수동 분석 재실행으로 broker_diff_status=MATCH 확인(참조 문서 2절 8). 10/14 06:15 daily에서 I3 기준이 새 기록으로 바뀌어 현금 대조 통과 예상, decide의 S7 관문은 확인 필요.
- 사후 확인(12:54): 사용자 수동 분석 manual-20261013T035402524930Z-90406d895e86 — preflight PASS, VERIFIED_REAL_DATA, **broker_diff_status=MATCH**. 대조 적용 완료.

## 15. 대조 적용 뒤 1회 실행 (12:57 KST, autocore-run-once.ps1)

- daily 12:57:19: **OK**(compare, 사유 없음) — I1·I2·I3 모두 통과. 첫 정상 daily.
- decide 12:57:31: HOLD, 사유는 `G1_S7_FAIL_CLOSED:hwm_line_or_pause_state_missing_or_corrupt,undeclared_cash_flow` 하나(S7: LINE_EVALUATION_ON_HOLD, CASH_FLOW_COVERAGE_GAP·CASH_FLOW_EVIDENCE_MISSING). 이는 관제판 r-cashflow-hold의 알려진 보류(10/7·10/8 사람 대조에 거래내역 증거 없음)로, 비교 모드 동안은 풀리지 않고 T1 "켜" 뒤 첫 코어 기록에서 풀리는 설계다. 주문표 0.
- 대조: cmp-fix2 효과로 BE:false_breakout·exposure:caps가 B7에서 빠짐(B7 6건 = 이미 설명 기록된 LLM_ERROR 4 + CORE_BUG 2). 통합점검 대시보드 runs/2026-10-13 core 갱신(version 3).

## 16. 총자산 현금 정의 수정 병합 (14:1x KST)

- 수동 경로: Builder(worktree t2-equity-cash, Opus xhigh) → 독립 Judge(별도 세션, VERDICT: PASS, docs/claude/t2-equity-cash-judge-report-2026-10-13.md) → 사용자 병합 스크립트(t2-equity-cash-merge-2026-10-13.ps1: 잠금·작업 상태·Judge 판정·sha256 확인 → 커밋 2e59987 → 병합 73e18b4 → 메인에서 test_auto_core* 통과, EQCASH_DONE).
- 효과: 판정의 총자산·N·V6·EV4 현금 = 키움 주문가능(T1 가드 통과) / 실패·누락 시 세 값 최솟값. 결정 기록 exposure.cash_basis로 근거 표시. 2026-10-13 값 기준 N 1.2466(LLM과 같음), EV4 없음.
- 남는 것: 10-13 아침 결정의 옛 ev4_open(10-12 세션)은 소급 수정하지 않음 → R-REC1 RG 통과 전까지 EV4 사건으로 남음(비교 모드, 주문 영향 없음). '켜' 전 회차 ⑪(규칙 파일 1-1 ② 문구 정정)은 그대로 남음.

## 17. 현금 정의 수정 뒤 1회 실행 (14:33 KST, autocore-run-once.ps1)

- daily 14:33:28 **OK**(compare). decide 14:33:56 HOLD — 사유는 15절과 같은 `G1_S7_FAIL_CLOSED:…` 하나(r-cashflow-hold). 주문표 0.
- 새 현금 정의 실데이터 확인(병합 73e18b4): exposure.cash_basis = ORDER_AVAILABLE, 총자산 $27,695.15, N 1.2466(LLM과 같음), 계좌 상태 review → none, ev4_open false. 옛 코드는 결제 전 SOXL 매도대금 $3,072.51을 빼서 총자산을 $24,622.65로 낮게 잡아 접근선 아래로 봤다.
- **16절 정정**: "옛 ev4_open이 EV4 사건으로 남는다"는 틀렸다. 사건 목록은 실행마다 다시 계산되어 10-12 EV4가 사라졌고, 최근 사건은 EV3a 10-08이다.
- 대조: B7 6 → 5건(exposure:N 빠짐). 남은 RREC:RG1은 원인이 바뀌었다 — 코어 unk / LLM 충족. 코어는 r2 R2-4(사건 다음 세션부터 평가 세션까지 모든 세션에 유효 연구 기록 필요, auto_core_rules.py rg1_coverage)에 따라 10-09 세션 기록이 없어 unk(missing_sessions [2026-10-09]). 연구 기록은 10/13(세션 10-12)부터만 있다 → 설계대로의 fail-closed라 코어 결함이 아니고, LLM 규칙 문구에는 이 요구가 없어 LLM 오류로 적을 근거도 없다.
- 영향: auto_core_compare.day_passes는 B7이 모두 LLM_ERROR일 때만 연속 +1. 최근 사건이 EV3a 10-08인 동안(새 사건이 생기거나 60세션이 지나기 전) 매일 이 차이가 남아 **5거래일 대조가 시작되지 못한다**. 지금 판정 영향은 없다(RG2·RG3도 미충족, S7 보류).
- 결정 필요(rrec-rg1-bootstrap): A '켜' 전 회차 ⑪에서 규칙 파일에 RG1 연구 기록 요구 문구를 넣어 LLM도 unk로 판정(코드 변경 없음, 예약 작업 승인 필요, 그 사건 동안 RG1은 매수를 계속 막음 — 새 사건이 생기면 풀림) / B 코어가 첫 연구 기록 이전 세션은 요구하지 않게(EV3 (b)의 ev3b_coverage_start와 같은 방식) 수정 — 매수 관문 의미 변경이라 K3 수동 경로 / C 그대로 두고 새 사건을 기다림. 기록을 소급 작성하는 방식은 기록 시각이 사실과 달라져 제외. Cowork 권장 A.
- 대시보드: runs/2026-10-13 core version 4. 코어 판정 시각 표시를 UTC → KST로 수정(통합점검 페이지 v18) — 03:57(UTC) 표기 때문에 오전 기록처럼 보였던 문제.

### 17-1. 재검토 (15:0x KST, 사용자 요청)

- **rrec-rg1-bootstrap 권장 정정: A 철회 → D(cmp-fix3).** 대조 모듈에 이 경우를 위한 사전 등록 범주가 이미 있다 — B4 RESEARCH_RECORD, detail `RG1_NEEDS_RESEARCH_RECORD`(auto_core_compare.py RREC 게이트·매수 요건 ⑤). 그런데 조건이 오늘 연구 기록 상태(`research_ok`)만 보고 r2 R2-4의 지난 세션 공백(`rg1_coverage.missing_sessions`)은 보지 않아 B7로 떨어졌다. cmp-fix2와 같은 분류 결함이다. 고칠 곳은 대조 분류 조건 하나(cold path)이고, 코어 판정·매수 관문 의미(B)나 통합점검 규칙 문구(A)를 바꿀 이유가 없다. 코어 RG1의 보수적 판정(이 사건 동안 unk)은 그대로 둔다(NO_CHANGE) — 지금은 RG2·RG3도 미충족이라 실제 차이가 없고, 새 사건이 생기면 풀린다. '켜' 시점에 RG1 공백이 유일한 매수 막힘이면 그때 다시 본다.
- 지시문 docs/claude/cmp-fix3-builder-prompt.md 작성(큐에는 사용자 승인 뒤 넣음). 10/14 07:45 decide 전에 병합되면 10/14부터 대조 연속을 셀 수 있다. 연속 일수는 각 날 저장된 대조 블록으로 다시 세므로, 병합 전 날의 RG1 B7은 소급해서 바뀌지 않는다.
- **주문 지시 칸 정정**: OI-20261009-SOXL-2(매도 22주 LOC)는 10/10 대조(r24, SOXL 75→53)로 체결이 확인됐는데 대시보드 주문 문서 결과가 '대기'로 남아 맨 위에 계속 보였다. 원인: 주문 문서 결과를 바꾸는 자동 단계가 없다(Cowork 대조 때 손으로 바꾸는 설계, 10/10에 빠짐). 결과 알림 작업(08:50)도 "이미 있는 문서는 바꾸지 않는다"라서 '켜' 뒤 코어 주문표 결과(decision.outcomes)도 대시보드에 옮겨지지 않는다 → '켜' 전 회차 항목 후보. 조치: 그 문서 결과를 filled로 기록(체결가 확인 필요), 통합점검 v19 — 미국 세션일 다음 날 07:00 KST가 지난 주문은 '넣을 주문'에서 빼고 지난 주문 표에 "결과 대조 필요"로 표시.
