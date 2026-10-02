# S7 달력 연결 Builder 보고 (2026-10-02, K2 + Judge 대기)

- 상태: Builder 완료(1~5단계). 1단계 정지점에서 사용자 "진행"을 받아 이어갔다. 커밋하지 않았다. Judge 대기.
- worktree: `s7-cal-bind`, 브랜치 기준 HEAD `9af9dfc9b22d4316eae23f571365ca5b117ca4e2`(지시문 커밋, 일치)

## 0. 기준선

- `git status`: clean.
- 바꿀 파일 5개의 원시 sha256(worktree, CRLF 체크아웃 상태):

| 파일 | sha256 |
|---|---|
| scripts/run_portfolio_exposure_review.py | `09884e0bd3bdf30202b66dc47e2cbe29b57833db78b108a83f2625d6764940e1` |
| scripts/regular_session_close_history.py | `d577054bed198442118f53022e0b7007770af4055cb234fce7ab50ac5fccbed3` |
| tests/test_run_portfolio_exposure_review.py | `05208482e00b47ec340f522a96796412ef23046bdf579bd6e92bed5d0cc72f92` |
| tests/test_regular_session_close_history.py | `b372fabd5fc149e94740de8dce5cf30b649105cd99adf0b4f40b2c15968bf6a0` |
| tests/test_portfolio_exposure_judge_fixes.py | `cea4936705350c3303e59d2d568781cb2e3ce63a600eecfc0c05894964c1e8a4` |

- 전체 테스트(`python -m unittest discover -s manage-us-stock-strategy/tests`, 서브에이전트 1회): 2228건, 실패 22, 오류 292, 건너뜀 1 (실패·오류 ID 314개, 중복 없음).
- 실패 ID 목록 파일(작업 폴더 밖 scratchpad, `baseline_failures.txt`, 314줄) sha256: `286259c36f8c546eedcaacf20b35a32c352cadacdcdbbe324e8d8de8d881e1be`.
- 기준선 실패는 모두 worktree CRLF 체크아웃 때문에 실제 권한 파일·고정 파일 해시가 맞지 않아서 생긴 것으로 보인다(통합 권한, 키움 acceptance, 대시보드, 주문의도 등). 이번 작업 대상 테스트 3개(`test_run_portfolio_exposure_review`, `test_regular_session_close_history`, `test_portfolio_exposure_judge_fixes`)와 `test_session_authority`는 기준선에서 모두 통과한다. `test_integrated_authority_snapshot`은 기준선에서 38건 실패한다(아래 1.c).

## 1. 조사 (읽기만)

### 1.a 바꿀 곳과 바꾼 뒤의 호출 흐름

**`run_portfolio_exposure_review.py`**
- `:49` `DEFAULT_ACTIVATION` 삭제. 신뢰 루트 상수 `TRUSTED_ROOT = REPO_ROOT`(테스트가 `mock.patch.object`로 바꾸는 seam, 인자·환경변수 없음)를 둔다.
- `:50-51` `CALENDAR_ARTIFACT_ROOT`/`CALENDAR_ARTIFACT_NAME`: 기본 입력 경로 계산에만 쓰이므로 아래 흐름대로 제거 또는 축소.
- `:291-299` `resolve_calendar_path`: activation 읽기를 없앤다.
- `:338-343` 달력 읽기: 아래 흐름으로 교체.
- `:264-288` `resolve_session` 독스트링과 `:267-269`의 "ACTIVE calendar ends 2026-08-29" 문구, `:410` `--calendar` 도움말("default: the ACTIVE artifact")을 R6에 따라 고친다.
- `:371-384` `inputs`에 `calendar_authority` 키 추가(R5).

**`regular_session_close_history.py`**
- `:38` `DEFAULT_ACTIVATION` 삭제, `TRUSTED_ROOT = REPO_ROOT` 상수 추가, `current_time()`(UTC 현재, 테스트 seam) 추가.
- `:71-95` `load_calendar(calendar_path, activation_path)`: 두 번째 인자를 활성 권한 snapshot으로 바꾼다(없으면 None = 검증 안 함 = EXPLICIT). 판정은 "snapshot 있음 AND 파일 원시 sha256 == `snapshot.session.calendar_hash`"이다. 반환 dict에 `identity`(키 구성 그대로, C7)와 별도 최상위 키 `authority_failure`(사유 또는 None)를 둔다.
- 새 함수 `load_production_snapshot(now) -> (snapshot | None, reason | None)`: `load_production_integrated_authority_snapshot(trusted_root=TRUSTED_ROOT, decision_as_of=now, resolved_at=now)`을 호출하고 `IntegratedAuthorityLoadError.reason`을 반환한다. 두 스크립트가 이 함수 하나를 공유한다(R1).
- `:316-318` `main`: `load_calendar(args.calendar, DEFAULT_ACTIVATION)` → `load_calendar(args.calendar, snapshot)`. 출력 JSON에만 `calendar_authority_reason` 추가(이력 파일 calendar 블록은 그대로, C7).

**바뀐 뒤 호출 흐름**
- 실행기: `now` 결정 → `load_production_snapshot(now)` → (1) `--calendar` 없음: 로더 실패면 `ReviewRunError("SESSION_CALENDAR_UNAVAILABLE:<reason>")`, 성공이면 snapshot이 이미 검증한 `session.artifact`로 달력을 만든다(해시 = snapshot 해시, ACTIVE). (2) `--calendar` 있음: 그 파일을 읽어 원시 sha256을 snapshot 해시와 비교, 같으면 ACTIVE, 다르면(또는 로더 실패면) EXPLICIT_ARTIFACT_NOT_ACTIVE. → 이후 `resolve_session`, `load_close_histories`는 그대로(`identity["authority_status"]`만 본다, 이력 파일 값은 믿지 않음).
- 이력 빌더: `--calendar` 파일 읽기 → `load_production_snapshot(current_time())` → 위 판정 → `build_history`는 그대로.

### 1.b 옛 activation 파일에 기대는 기존 테스트와 같은 뜻을 지키는 방법

| 테스트 | 지금 하는 일 | 바꾼 뒤 |
|---|---|---|
| `RunnerCase.setUp` (`test_run_portfolio_exposure_review.py:58-69`) | 임시 activation 파일을 만들고 `DEFAULT_ACTIVATION`을 patch | 임시 trusted root에 통합 권한 픽스처를 만들고 `TRUSTED_ROOT`를 patch. `--calendar`는 root 안의 달력 사본(LF 바이트)을 가리킨다 |
| `:112` `write_history`의 `load_calendar(CALENDAR, self.activation)` | ACTIVE 달력으로 이력 생성 | 같은 달력 사본 + snapshot으로 ACTIVE 이력 생성 |
| `:254-269` 달력이 ACTIVE가 아니면 모든 종가 미확인 | activation의 해시를 0…0으로 바꿈 | 픽스처 통합 권한이 가리키는 달력을 다른 artifact(`d6d1ecd…`, 8/29 달력)로 바꿔 쓴다. `--calendar`로 준 2421eeb7 사본은 EXPLICIT이 되어 같은 단언(`SESSION_CALENDAR_NOT_ACTIVE`, `EXPLICIT_ARTIFACT_NOT_ACTIVE`, 활성화 제안 NOT_READY)이 유지된다 |
| `:271-283` 이력 파일이 스스로 ACTIVE를 주장해도 믿지 않음 | 이력 생성 뒤 activation 해시를 바꿈 | 이력 생성 뒤 픽스처 권한을 다른 달력으로 교체. 같은 단언 유지 |
| `test_regular_session_close_history.py:96-112` | activation 파일 ACTIVE/해시 불일치 | snapshot 일치 → ACTIVE, 불일치·None → EXPLICIT로 같은 뜻 유지(달력 권한 테스트만 고침) |
| `test_portfolio_exposure_judge_fixes.py` | `RunnerCase`를 상속, `--calendar`에 2421eeb7과 d6d1ecd 사용 | 대부분 `RunnerCase.setUp` 변경만으로 동작. d6d1ecd를 `--calendar`로 쓰는 두 테스트(`:262`, `:270`)는 픽스처가 만든 d6d1ecd 사본(LF)을 쓰도록 연결만 바꾼다. 단언(`SESSION_CALENDAR_DOES_NOT_COVER_TODAY:2026-08-29`, `CALENDAR_ENDS_2026-08-29`)은 그대로 |

`test_regular_session_close_history.py:46`, `:244`와 `test_run_portfolio_exposure_review.py:347`의 `load_calendar(CALENDAR, None)`은 두 번째 인자 의미(None = 검증 안 함)가 같아서 그대로 둔다.

### 1.c 통합 로더 픽스처와 CRLF 영향

- 확인한 사실(읽기만): worktree의 2421eeb7 달력 파일 원시 sha256은 `736556c1…`(CRLF)이고 CRLF→LF로 바꾸면 `2421eeb7…`로 돌아온다. 식별 artifact 3개도 마찬가지다(LF 정규화 시 파일명 해시와 일치). 실제 통합 권한을 worktree에서 로드하면 `INTEGRITY_FAILURE`다. C9와 같다.
- 방법: 테스트 도우미가 임시 root에 `build_combined_activation_manifest`(기존 `test_integrated_authority_snapshot.py` 방식)로 ACTIVE 통합 권한(테스트 cohort ID)을 만든다. artifact 바이트는 디스크에서 읽어 CRLF를 LF로 정규화한 뒤 sha256이 파일명 해시와 같은지 확인하고 복사한다(`git show` 같은 git 호출 없음, 원본 폴더(LF)에서도 같은 코드로 동작). 식별 artifact는 `d8b03aa4…`(기존 테스트가 쓰는 것), 달력은 `2421eeb7…`(필요 시 `d6d1ecd…`)를 쓴다. `activated_at`은 2026-09-23 정도로 두어 테스트 시계(2026-10-01)보다 앞선다.
- 이 도우미는 새 테스트 파일 `test_s7_calendar_binding.py`에 두고 `RunnerCase`가 가져다 쓴다. 기존 `test_integrated_authority_snapshot.py`는 고치지 않는다(기준선에서 이미 38건 실패, 수정 대상 아님).
- 실제 달력·통합 권한 확인은 병합 뒤 Cowork가 원본 폴더에서 한다(지시문 5절).

### 1.d R1~R7 중 코드 현실과 부딪히는 것

1. **R3 `--calendar`와 로더 실패의 조합이 모호하다.** R3은 실행기에서 "로더 실패 → SESSION_CALENDAR_UNAVAILABLE"와 "`--calendar`로 다른 artifact → EXPLICIT"을 둘 다 말한다. `--calendar`를 주고 로더가 실패하면 어느 쪽인지 정해야 한다. 기존 테스트(`judge_fixes`의 8/29 달력 + `--calendar`)는 권한 없이도 EXPLICIT 실행이 가능하다는 것에 기대지 않는다(픽스처 root가 있음). 제안 1개: **`--calendar` 없음 = 로더 실패 시 실패(결과 파일 없음). `--calendar` 있음 = 로더 실패 시 EXPLICIT_ARTIFACT_NOT_ACTIVE로 계속하되(종가 미확인) `inputs.calendar_authority`에 `{"status": "UNAVAILABLE", "reason": <reason>}`을 기록.** 이력 빌더 규칙(로더 실패 → EXPLICIT)과 맞고, 미확인이 눈에 보이며 fail-closed가 유지된다.
2. **R5 `calendar_authority`의 실패 형태**: R5는 성공 때의 4개 키만 말한다. 위 제안 1의 UNAVAILABLE 형태가 필요하다. 이 키는 `inputs`(자유 object)에만 쓰이고 스키마는 바꾸지 않는다(C7).
3. **R1 "쓰는 달력 artifact의 원시 sha256"과 기본 실행**: 기본 실행은 파일을 다시 읽지 않고 로더가 이미 해시 검증한 `snapshot.session.artifact`를 쓴다(이중 읽기 방지, 읽는 순간과 판정 순간의 차이 제거). 결과는 R1과 같다(해시 == snapshot 해시). `snapshot.session.artifact`는 MappingProxyType/tuple로 얼려 있어 schema·semantic 검증 전에 dict/list로 되돌리는 도우미가 필요하다. 이 점만 구현 방식 선택이다.
4. **R4 이력 빌더 시계**: `--now`가 없으므로 모듈 함수 `current_time()`을 seam으로 추가한다(인자 추가 아님, R2 유지).
5. **바꿀 수 있는 파일 목록 밖의 낡은 문구**: `manage-us-stock-strategy/references/portfolio-exposure-review.md:74`가 "달력 권한은 항상 `workspace/policies/session_calendar_activation.json`에서 온다"고 적고 있다. 이 파일은 허용 목록에 없어서 건드리지 않는다. K0 문구 수정으로 Cowork가 병합 뒤 고치길 제안한다(보고 5절 "남은 문제"에도 적는다).
6. R2, R6(주석·도움말은 위 1.a의 곳), R7(기존 줄바꿈 CRLF 유지, 새 파일도 worktree 규칙에 맞춘다)은 충돌 없음.

### 안전 확인(조사 범위)
- `run_portfolio_exposure_review`/`regular_session_close_history`는 `alert_policy.json:739`에 이름이 나올 뿐 해시로 고정돼 있지 않다(키움 acceptance 쪽에는 이름 없음). 고정 파일 22개에 들지 않는다는 C6와 일치.
- 이번 단계에서 어떤 파일도 바꾸지 않았다(이 보고 파일 제외).

### 1단계 정지점 뒤 사용자 결정 (2026-10-02, "진행")
- 1.d 제안 1~5 수용. 추가 조건: (가) 실행기에서 `--calendar`가 ACTIVE가 아니면 `non_default_inputs`에 `"calendar"`를 넣는다(테스트 추가). (나) 허용 파일에 `references/portfolio-exposure-review.md`를 더하고 :74 부근 달력 권한 문장과 비표준 입력 목록만 고친다(K0).

## 2. 테스트 먼저 (`test_s7_calendar_binding.py`)

- 새 파일 10건(T1~T7 + 아래 추가분). T1 기본 실행, T2 옛 파일 무시(옛 파일이 다른 달력을 ACTIVE로 적거나 없어도 같음, 소스에 옛 파일 이름·`DEFAULT_ACTIVATION` 없음), T3 로더 실패 5종(권한 파일 없음 / SHADOW / 매니페스트 바인딩과 달력 해시 불일치 / artifact 변조 / `activated_at`이 시계보다 늦음 → `SESSION_CALENDAR_UNAVAILABLE:<reason>`, 결과 파일 없음), T3b(`--calendar` + 로더 실패 → EXPLICIT, `calendar_authority` UNAVAILABLE), T4(다른 artifact → EXPLICIT, 조건 (가) `non_default_inputs == ["calendar"]`와 `[비표준 입력]` 표시), T5(이력 파일이 ACTIVE라고 적어도 권한 달력이 바뀌면 종가 미확인), T6(이력 빌더 ACTIVE / 불일치·로더 실패 4종, 출력 JSON에만 `calendar_authority_reason`, 이력 파일 calendar 키 5개 그대로), `load_calendar` 단위, T7(두 스크립트 도움말에 activation·manifest·trusted·authority 인자 없음, `os.environ`/`getenv` 없음).
- 고치기 전 코드에서 실행(측정 당시 버전): 10건 중 **실패 10(subTest 포함), 오류 6**이고 T7만 통과했다(T7은 "인자가 없다"는 현재 상태를 지키는 보호 테스트). 실패 이유는 모두 옛 activation 파일을 읽어 ACTIVE로 판정하거나 `SESSION_CALENDAR_DOES_NOT_COVER_TODAY`로 멈추는 동작 때문이었다(예: 기본 실행이 8/29 달력으로 멈춤). 측정 뒤 시계 seam 패치에서 `create=True`와 runner 쪽 신뢰 루트 패치를 하나로 정리했다(구현 뒤 거동 동일).
- 픽스처: 임시 root에 통합 권한 매니페스트(ACTIVE, 테스트 cohort `TEST-S7-CALENDAR-BINDING`, `activated_at` 2026-09-23)와 식별 artifact `d8b03aa4…`, 달력 `2421eeb7…`(필요 시 `d6d1ecd…`)를 CRLF→LF 정규화 바이트로 복사한다. 정규화 뒤 sha256이 파일명 해시와 같은지 확인한다. 실제 정책·권한 파일은 읽지도 쓰지도 않는다.

## 3. 구현과 대상 테스트

바꾼 것(요약):
- `regular_session_close_history.py`: `DEFAULT_ACTIVATION` 삭제 → `TRUSTED_ROOT`(테스트 seam)·`current_time()`·`load_production_snapshot(now)`·`calendar_from_snapshot()` 추가, `load_calendar(path, snapshot, authority_failure=None)`로 변경(ACTIVE = 로더 성공 AND 원시 sha256 == `snapshot.session.calendar_hash`). 반환 dict에 `authority_failure` 키 추가(이력 파일 `calendar` 블록은 그대로). `main`은 출력 JSON에만 `calendar_authority_reason`을 더한다.
- `run_portfolio_exposure_review.py`: `DEFAULT_ACTIVATION`·`CALENDAR_ARTIFACT_*`·`resolve_calendar_path` 삭제, `load_session_calendar(calendar, now)` 추가(기본 실행은 로더가 검증한 `snapshot.session.artifact` 사용, 실패 시 `SESSION_CALENDAR_UNAVAILABLE:<reason>`), `inputs.calendar_authority` 추가(성공 `{"status":"LOADED", 매니페스트 sha256, cohort, 달력 sha256, 달력 버전}` / 실패 `{"status":"UNAVAILABLE","reason":…}`), 조건 (가) `non_default_inputs`에 `"calendar"`, 낡은 문구·도움말 수정(R6).
- 신뢰 루트 seam은 `regular_session_close_history.TRUSTED_ROOT` 하나다(실행기도 이 모듈의 `load_production_snapshot`을 쓴다). 인자·환경변수는 없다(R2).
- `references/portfolio-exposure-review.md`: 74~77행 문장만 교체(K0, 조건 (나)).
- 테스트 3개: 픽스처 연결과 달력 권한 테스트만 바꿨다(아래 표).

대상 테스트(모두 통과):

| 파일 | 결과 |
|---|---|
| test_s7_calendar_binding.py | 10건 OK |
| test_run_portfolio_exposure_review.py | 17건 OK |
| test_regular_session_close_history.py | 14건 OK |
| test_portfolio_exposure_judge_fixes.py | 29건 OK |
| test_session_authority.py | 41건 OK |
| test_integrated_authority_snapshot.py | 38건 오류 = 기준선과 같은 38건(worktree CRLF 때문, 이번 변경과 무관) |

## 4. 전체 테스트 (서브에이전트 1회) — 새 실패 0

- 실행: 2238건(기준선 2228 + 새 테스트 10), 실패 22, 오류 292, 건너뜀 1. 실패·오류 ID 314개.
- 기준선 목록과 비교: **새 실패 0, 기준선에서 해소된 것 0**. 목록 파일 sha256 `81ef8461…edab`은 기준선 `286259c3…e1be`와 다르지만 정렬 순서에서 한 줄(`test_missing_unapproved_and_invalid_plan_rejected … (status='PROVISIONAL')`)의 위치만 다르고 ID 집합은 같다(정렬해서 `diff` 확인, 일치).
- 마지막에 `--calendar` 도움말 줄 정렬만 고쳤고, 그 뒤 대상 테스트 5개를 다시 돌려 모두 통과했다(전체 실행은 이 한 줄 수정 전 상태).

기존 테스트 단언을 바꾼 것:

| 위치 | 전 | 후 | 이유 |
|---|---|---|---|
| `test_run_portfolio_exposure_review.py` `test_calendar_that_is_not_active_leaves_every_close_unverified` (`:266` 부근) | `non_default_inputs == []`("기본 입력인데도 활성화 제안 불가") | `non_default_inputs == ["calendar"]`와 첫 줄 `[비표준 입력]` 확인 | 사용자 추가 조건 (가). ACTIVE가 아닌 달력은 비표준 입력이다. `NOT_READY` 단언과 종가 미확인 단언은 그대로 |
| `RunnerCase.setUp`, `write_history`, `run_review` 등 | 임시 activation 파일 + `DEFAULT_ACTIVATION` patch, `--calendar CALENDAR`(저장소 달력) | 임시 통합 권한 root + `rsch.TRUSTED_ROOT` patch, `--calendar self.calendar`(LF 사본) | 권한 출처 변경(픽스처 연결). 단언 문장은 그대로 |
| "달력 ACTIVE 아님" 두 테스트의 설정 | activation 해시를 `0…0`으로 | 통합 권한이 다른 달력(`d6d1ecd…`)을 활성화하도록 root 재구성 | 같은 뜻: 이 실행의 달력이 활성 달력이 아니다 |
| `test_portfolio_exposure_judge_fixes.py` FixD | `--calendar`에 저장소 8/29 달력·2026 달력 경로 | 임시 root의 LF 사본 경로(`self.calendar_0829`, `self.calendar`) | 픽스처 연결만. 단언(`DOES_NOT_COVER_TODAY:2026-08-29`, `CALENDAR_ENDS_2026-08-29` 등) 그대로. 8/29 달력은 이제 "옛 ACTIVE"가 아니라 "활성이 아닌 옛 artifact"다 |
| `test_regular_session_close_history.py` `test_calendar_that_is_not_the_active_authority_…` | activation 파일의 ACTIVE / 해시 불일치 | 통합 권한 snapshot 일치 → ACTIVE, 다른 달력 → EXPLICIT | 같은 뜻을 새 권한 출처로 |

## 5. 결과

### 5.1 바꾼 파일과 diff --stat
(커밋하지 않음. 추적 파일 6개 `163 insertions(+), 80 deletions(-)`, 새 파일 2개)

```
 .../references/portfolio-exposure-review.md        | 12 ++-
 .../scripts/regular_session_close_history.py       | 98 +++++++++++++++++-----
 .../scripts/run_portfolio_exposure_review.py       | 55 +++++++-----
 .../tests/test_portfolio_exposure_judge_fixes.py   | 13 ++-
 .../tests/test_regular_session_close_history.py    | 21 +++--
 .../tests/test_run_portfolio_exposure_review.py    | 44 ++++++----
 6 files changed, 163 insertions(+), 80 deletions(-)
?? docs/claude/s7-calendar-binding-builder-report-2026-10-02.md
?? manage-us-stock-strategy/tests/test_s7_calendar_binding.py
```

### 5.2 원시 sha256 전후 (worktree, CRLF)

| 파일 | 전 | 후 |
|---|---|---|
| scripts/run_portfolio_exposure_review.py | `09884e0bd3bdf30202b66dc47e2cbe29b57833db78b108a83f2625d6764940e1` | `3e5060f0fb4264f197b6d389c7c443b30a0f75fc3e1439d7f9e8edbd647b8a09` |
| scripts/regular_session_close_history.py | `d577054bed198442118f53022e0b7007770af4055cb234fce7ab50ac5fccbed3` | `384232a3b5048ff5606ae8bcb91fe3444a0bb9a28939fbec44f0940c69b96083` |
| tests/test_run_portfolio_exposure_review.py | `05208482e00b47ec340f522a96796412ef23046bdf579bd6e92bed5d0cc72f92` | `c1a19cd6d76989d10c04a0f3c8188e8f8726570f49f1c0ec459f67c08a163036` |
| tests/test_regular_session_close_history.py | `b372fabd5fc149e94740de8dce5cf30b649105cd99adf0b4f40b2c15968bf6a0` | `e5d87ba37ade2328a725a683baf23c2254fe230b52c1ec4cf79a857ceba96712` |
| tests/test_portfolio_exposure_judge_fixes.py | `cea4936705350c3303e59d2d568781cb2e3ce63a600eecfc0c05894964c1e8a4` | `00e3fe59a76328c822fff8d3162d09ca78155d2fa5684b130deb524cd20739ab` |
| references/portfolio-exposure-review.md | `782c4ed1a8664474c06523d01d8a415091b635a7cff77d8ee22bfab8af8d4880`(HEAD blob을 CRLF로 환산) | `a847125f53839af862cea3e38884e8b361e06548851c63f030a7732503c1b3a2` |
| tests/test_s7_calendar_binding.py (새 파일) | — | `3edf1d0e34a43830cfabe98d81bf051854d013287f6038dfa428b4b88c292d58` |

줄바꿈: 기존 파일 6개는 편집 뒤에도 CRLF 전부(LF 단독 줄 0, BOM 없음) 그대로다. 새 파일 2개는 worktree 규칙에 맞춰 CRLF로 썼다.

### 5.3 무변경 확인
- `git status`에 위 8개 외 파일이 없다. `workspace/policies/*`(두 activation 파일 포함), `integrated_authority_snapshot.py`, `session_authority.py`, `session_calendar_artifact.py`, 스키마, `alert_policy.json`, 상태·원장·journal, 고정 파일 22개는 수정·추가·삭제되지 않았다(작업 트리 변경 목록 기준).
- 이 작업에서 키움 도구, 비밀 파일 읽기, 커밋·push, apply 명령은 쓰지 않았다.

### 5.4 남은 문제 (이 지시문 4절 포함)
- X1(옛 파일 `session_calendar_activation.json`과 옛 경로의 8/29 달력)은 그대로다. 정리는 별도 K3.
- X2: 달력 `2421eeb7…`은 2026-12-31까지다. 2027년 첫 세션부터 기본 실행은 `SESSION_CALENDAR_DOES_NOT_COVER_TODAY`로 멈춘다(fail-closed). 12월 중 2027 달력 K3 필요.
- X3: MU·DELL·AMD·TQQQ가 통합 권한의 신원 범위 밖이다(매수 전 별도 K3). 이번 변경은 신원을 쓰지 않는다.
- 이 worktree에서는 실제 통합 권한이 CRLF 때문에 로드되지 않는다(`INTEGRITY_FAILURE`). 실제 자료 확인은 병합 뒤 Cowork가 원본 폴더에서 해야 한다(지시문 5절 1번). 테스트는 임시 root 픽스처만 쓴다. 병합 전에는 실제 권한으로 실행기를 돌려 본 적이 없다.
- 새 정책 결정 아님, 선택 사항: 실행기에서 `--calendar`를 주고 로더가 실패하면 EXPLICIT로 계속한다(사용자 수용 1.d 제안 1). 이때 `inputs.calendar_authority`는 `UNAVAILABLE`+사유다.
- `references/portfolio-exposure-review.md`는 74~77행만 바꿨다. 같은 문서의 66행("ACTIVE production calendar")은 그대로 유효하다.
- 전체 테스트의 기준선 실패 314건은 worktree CRLF 때문으로 보이며, 병합 뒤 원본 폴더(LF)에서 다시 재야 정확하다.
- 병합 전 Judge 확인 요청 포인트: (1) 기본 실행이 파일을 다시 읽지 않고 `snapshot.session.artifact`를 쓰는 점(해시 검증은 로더가 함), (2) `non_default_inputs`에 `"calendar"`가 `"now"`보다 앞에 들어가는 순서, (3) `load_calendar` 시그니처 변경(두 번째 인자 의미: 옛 activation 경로 → snapshot). 이 함수를 쓰는 곳은 두 스크립트와 테스트뿐임을 grep으로 확인했다.

### 5.5 상태
- Builder 완료, worktree `s7-cal-bind`, **새 실패 수 0**. 커밋하지 않았다. 다음은 Judge(별도 세션)와 사용자 승인.
- Judge 판정 PASS (2026-10-02, J1~J9 PASS, 전체 2238건 새 미통과 0)
- 주석: 0·4절 실패 22/오류 292는 Judge 측정 23/291과 구분이 1건 다르다. 미통과 ID 집합은 같다. 원인 NOT VERIFIED
