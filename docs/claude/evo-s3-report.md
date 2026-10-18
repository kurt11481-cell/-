# evo-s3 Builder 보고 (2026-10-18)

- **바뀐 파일**
  - `run_journal_score.ps1`: 78행 `$Object.Keys -ccontains $Name`(대소문자 구분. Dictionary·Hashtable·OrderedDictionary에서 `Contains` 메서드에 기대지 않음). RUNNER_START 뒤 본문 전체를 try로 감쌈. catch는 로그 `RUNNER_FAIL RUNNER_EXCEPTION type=… message=…`(ASCII), `WEEKLY_LATEST.json` FAIL/`RUNNER_EXCEPTION`(기존 `Write-WeeklyLatest` 재사용), 종료 4. 로그와 상태 쓰기는 각각 따로 try라서 두 번째 예외가 로그 줄을 지우지 않음. `$exitCode = -1`로 먼저 두므로 파이썬이 끝나기 전 예외면 exit_code -1. status FAIL인데 종료 코드가 0이면(LEARNING_FAILED + 파이썬 0) 프로세스 종료 1, `exit_code` 필드는 파이썬 코드 그대로. 머리 주석 갱신. 49행 `order_authority` 줄과 보고서 고르기·status·reason·임시 파일 → Move-Item은 그대로(들여쓰기만 바뀜).
  - `host_status.ps1`: 작업 목록에 `InvestmentV2-JournalScore` 추가 + 영어 주석 1줄(ASCII). 검사 id·규칙·종료 코드 불변.
  - `test_journal_score_runner.py`(새): 실행기 **사본**을 임시 폴더에서 Windows PowerShell 5.1로 실행. 가짜 채점기 사용. 경우 1~7 + 텍스트 검사 2개. skip 조건은 `os.name == "nt"` + powershell.exe뿐. 경우 1의 learning 블록은 `counts`·`epochs` 객체와 `buckets` 배열을 포함.
  - `test_host_status_static.py`: 작업 목록 3개 이름 검사 1개 추가. `test_journal_score_task_static.py`는 고치지 않음(깨지지 않음).
- **고치기 전 실행기로 경우 1을 돌린 결과: 확인 못 함.** Builder는 PowerShell을 직접 못 돌리고, 새 테스트는 고친 실행기만 시험함. 원인 확인은 Cowork 재현(PS 7)에 기댐. Judge나 사용자는 병합 전에 `git stash`가 아니라 이전 커밋 실행기 사본으로 경우 1을 한 번 돌려 볼 수 있음.
- **테스트**
  - `test_journal_score_*.py`: Ran 14, skip 0, 실패 0 (새 실행 테스트 7개가 실제로 돎, 약 3.4초).
  - `test_host_status*.py`: Ran 19, skip 0, 실패 0.
  - `test_score_learning*.py`: Ran 52, skip 0, 실패 0.
  - 스키마 감사: PASS.
- **예외 경로(7번)**: 임시 저장소에 `WEEKLY_LATEST.json.tmp` **폴더**를 미리 만들어 실제로 실행함. try 안 WriteAllText와 catch 안 두 번째 쓰기가 모두 실패하는 상황에서 종료 4, 로그 `RUNNER_FAIL RUNNER_EXCEPTION type=`·`message=` 줄, RUNNER_END 없음, `WEEKLY_LATEST.json` 없음을 확인. 시험용 스위치는 넣지 않음. 상태 쓰기만 성공하는 경우(exit_code -1)는 실행 테스트가 없고 코드 읽기로만 확인함.
- **참고(기존 동작)**: OK 실행의 `reason`은 `[string]$Reason` 때문에 null이 아니라 `""`로 저장됨. 바꾸지 않았고 테스트가 이 값을 고정함.
- **남은 위험**
  - 주간 작업을 끄거나 지울 때 같은 변경에서 `host_status.ps1` 목록의 이름을 빼야 함. 안 빼면 ⑭가 화~토 매일 나감.
  - ⑭ 꼬리 문구가 "코어 작업이 안 돌 수 있음"으로 고정이라 JournalScore 항목에도 붙음(작업 이름이 보임).
  - 실행 테스트는 Windows PowerShell 5.1이 있는 곳에서만 돎. 다른 곳에서는 skip되고 텍스트 검사 2개만 돎.
  - 첫 예약 실행(10/25)에서 `WEEKLY_LATEST.json`이 실제로 생기는지는 병합 뒤 Cowork가 확인해야 함.
