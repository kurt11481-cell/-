---
id: redesign-t3b-builder-prompt-2026-10-10
title: 재설계 T3b Builder 지시문 — 개발 파이프라인 속도·정확도 보강(경로 길이 · 기준선 브랜치 · 기준선 동시 실행 · 큐 간격) + Judge 의견 묶음
date: 2026-10-10
status: 확정(2026-10-10 18:1x KST, 첫 시험 t3-trial-1 결과 반영 — 0절)
class: 일반 변경이지만 파이프라인 보호 경로(tools/**)라서 기존 방식 — worktree Builder → 별도 Judge 세션 → 사용자 병합
decision: 사용자 2026-10-10 17:44 KST "다음 작업도 계획해줘"(첫 시험 1회차에서 드러난 3건을 한 번에 묶어 처리) · 재설계 A5(변경 2등급)
evidence: workspace/outputs/dev-runs/t3-trial-prompt-profile-test/(builder-1.err "Filename too long", baseline.json 실패 39) · _baseline/977e6fad…full.err(git_branch minLength 11건) · redesign-t3-judge-report·judge2-report 의견 N1·N2·O3
authority: order_authority=false · quantity_authority=none · execution_quantity=null (개발 절차만. 주문·정책·상태·브로커 무관)
consumers: T3b Builder(worktree t3b) · T3b Judge · 이후 모든 dev-run · 관제판 redesign-t3b
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree `t3b` · 이유: 파이프라인 판정 규칙(기준선·범위 검사)을 바꾸는 보호 경로 변경**

## 0. 시험 결과 반영 (Cowork가 t3-trial-1 결과를 본 뒤 채움)
- t3-trial-1 = **READY_TO_MERGE** (Judge PASS, 새 실패 0, Ran 2670→2678, 재시도 0). 근거: workspace/outputs/dev-runs/t3-trial-1/log.txt·result.json·judge-1.json(is_error=false, subtype=success — 1차 Judge가 걱정한 CLI json 필드는 있음).
- 단계별 시간(KST): 큐 등록 17:41 → 가져감 17:45:04(대기 3.5분) · preflight 2초 · **기준선 7분 25초**(실패 39 = detached) · Builder 30초(11턴) ·
  **검사(대상 + 전체 스위트 + 스키마) 7분 18초** · Judge 37초(11턴) → 합계 15분 55초. 병목 = 기준선 + 전체 스위트(각 약 7분). D3로 기준선 대기가 사라지면
  작은 작업은 약 9분 + 큐 대기.
- 정상 동작 확인: `-p --worktree` 경로·브랜치(worktree-t3-trial-1), 복사 파일 예외(settings.local.json·상태 파일 2개 = 무시 목록, STOP 없음), Builder의 허용 밖 Bash 1건 자동 거절 →
  PowerShell·Grep으로 계속(경계 정상), Judge가 Read·Grep·Glob만으로 파일:줄 근거 작성.
- 새 결함: 없음(1회차 경로 길이 → D1, 기준선 detached → D2는 이미 1절에 있음). 1회차가 남긴 빈 브랜치 `worktree-t3-trial-prompt-profile-test`는 사용자 정리 1줄(7절).

## 1. 목표와 완료 기준 (기계 판정)

| # | 문제(1회차 실측) | 고친 뒤 |
|---|---|---|
| D1 | id 28자 → worktree 경로가 Windows 260자 한도 초과 → `git worktree add` 실패, 7.5분 뒤 STOP_WORKTREE | preflight가 모델·기준선 전에 경로 길이를 계산해 1초 안에 STOP_PREFLIGHT(PATH_TOO_LONG, 허용 최대 id 길이 표시) |
| D2 | 기준선 worktree가 detached HEAD → git_branch 빈 칸으로 테스트 11건이 기준선에서만 실패(39 vs 28) → 그 11건의 회귀를 못 잡음 | 기준선 worktree도 브랜치 위 → 기준선 실패 28(현재 기준), Builder worktree와 같은 조건 |
| D3 | 기준선 전체 스위트 약 7분이 Builder 앞에서 직렬로 돈다(문서 커밋마다 base SHA가 바뀌어 캐시도 자주 빗나감) | 기준선을 Builder와 동시에 돌린다(정확도 그대로, 벽시계 시간만 줄임). 캐시 키는 그대로 base SHA |
| D4 | 큐 확인 15분 간격 → 시작까지 평균 7.5분 대기 | 5분 간격(평균 2.5분) |

- 문서만 바뀐 커밋에서 옛 기준선을 재사용하는 안은 **채택하지 않는다**: 테스트가 docs/claude 파일을 직접 읽는다(watchlist-registry.json, redesign-t1-policy-proposals.json, 여러 설계·보고 .md — tests·scripts grep 2026-10-10). 정확도를 잃는다.
- 함께 묶는 Judge 의견(파이프라인 파일은 고칠 때마다 이 기존 방식을 다시 돌아야 하므로 한 번에): N1 추가 줄 권한 표지, N2 문서 한 줄, O3 메인 체크아웃·run 기록 보호(좁게).
- 완료(Builder 단계): test_dev_pipeline 전부 OK(새 테스트 포함) · 전체 스위트 실패 집합 ⊆ 0단계 기준선 · 테스트 수 감소 0 · 허용 경로 밖 변경 0 · 스키마 PASS · .ps1 ASCII·CRLF·파서 0 · settings.json·.gitignore 변경 0.
- 완료(T3b 전체, 병합 뒤): 다음 파이프라인 작업 1건에서 ① 기준선 실패 = 브랜치 조건 값(현재 28) ② 큐 등록부터 Builder 시작까지 ≤ 6분 ③ 기준선이 Builder와 겹쳐 돈 기록(log 시각).

## 2. Builder 지시 (이 절만 따른다)

~~~
경계: order_authority=false. 키움·kiwoomcli·비밀 금지. workspace/policies/*, stock-strategy-system/*, CLAUDE.md, AGENTS.md, .claude/*, .gitignore 수정 금지.
커밋·병합·push·Windows 작업 등록 실행 금지(스크립트만 고친다). 모델을 부르는 claude -p 금지. dev-run·dev-merge·dev-queue 실행 금지(settings deny).
tools/ 아래 편집은 settings ask라 승인 창이 뜬다 — 사용자가 승인한다.
판단이 필요하거나 범위를 넘으면 BLOCKED.md를 worktree 루트에 쓰고 멈춘다.
줄바꿈: 고치는 기존 파일 CRLF 유지. .ps1은 ASCII. 명령에 auto_core.py 문자열 금지(-p "test_auto_core*").

범위(허용 경로): tools/dev-run.ps1, tools/dev-queue.ps1, tools/register-dev-tasks.ps1, tools/dev_pipeline/{devpipe.py, README.md, judge-prompt.md},
                 manage-us-stock-strategy/tests/test_dev_pipeline.py, docs/claude/redesign-t3b-* (보고). 그 밖은 금지.
                 (dev-merge.ps1·builder-rules.md·authority-paths.txt·commit-docs.ps1·run-docs-commit.ps1은 바꾸지 않는다)

0단계(읽기만, 보고 맨 위): a. 이 worktree(clean) 전체 스위트 기준선 — 실패 id·Ran·skipped(숫자는 원본 출력에서 직접 셈)
 b. 저장소 추적 파일 최장 경로 길이(git ls-files)와 이 PC의 메인 체크아웃 절대 경로 길이(UTF-16 단위)
 c. git worktree add -B 와 git branch -D 동작(문서), Windows에서 MAX_PATH 판정 기준(260, NUL 포함) — 근거 문서
 d. 지금 devpipe의 기준선 경로(ensure_baseline·worktree add --detach 줄)와 dev-run의 기준선→Builder 순서(줄 번호)

D1 경로 길이 preflight (devpipe preflight 검사 1개 추가, 모델·기준선·worktree 생성 전)
 - 필요 길이 = len(메인 체크아웃 절대 경로 + "\.claude\worktrees\" + <id>) + 1 + 기준 커밋 추적 파일 최장 경로(ls-tree -r --name-only <base>, / → \ 같은 길이).
   이 값 > 259이면 STOP_PREFLIGHT reason=PATH_TOO_LONG:<필요 길이>>259:max_id=<허용 최대 id 길이>. 같은 계산을 기준선 임시 worktree 이름에도 적용.
 - 길이는 UTF-16 코드 단위로 센다(한국어 경로 포함). 테스트: 경계값(259 통과·260 거절), 한국어 경로, 최장 경로 계산.
 - README에 "id는 14자 이하 권장(지금 저장소·경로 기준), preflight가 정확히 검사" 한 줄.

D2 기준선 worktree를 브랜치 위로 (devpipe ensure_baseline)
 - `git worktree add --detach` → `git worktree add -B devpipe-base-<sha8> <임시 경로> <base>`. 측정 뒤 그 worktree를 제거하고 `git branch -D devpipe-base-<sha8>`.
   지우는 브랜치는 이 이름 공간(devpipe-base-) + 이번 실행이 만든 것 + base를 가리킬 때만. 다른 브랜치·worktree는 건드리지 않는다.
 - 캐시 키에 기준선 방식 버전을 더해(예: …-py<버전>-b2.json) detached 시절 캐시를 다시 쓰지 않게 한다.
 - 테스트: 임시 git 저장소 픽스처에서 기준선 worktree가 브랜치 위(git branch --show-current ≠ 빈 값)이고, 끝난 뒤 worktree·브랜치가 남지 않음,
   devpipe-base- 밖 브랜치는 그대로.

D3 기준선을 Builder와 동시에 (dev-run.ps1 + devpipe)
 - 순서: preflight → init → [캐시 없으면] 기준선 임시 worktree를 먼저 동기로 만든다(git 잠금 경합 방지) → 기준선 전체 스위트·스키마를 백그라운드
   프로세스로 시작(출력은 지금처럼 cmd /c 리디렉션 바이트 저장) → include 스냅샷 → Builder 1회차 시작 → Builder 끝 → 기준선 끝을 기다림(기존 기준선
   상한 그대로) → check-1. 캐시가 있으면 지금처럼 바로 사용.
 - 기준선 실패·시간 초과는 지금처럼 STOP_BASELINE류(재시도 없음). Builder가 TIMEOUT·BLOCKED·STOP으로 끝나도 기준선 프로세스는 끝까지 기다리거나
   트리 종료하고 임시 worktree·브랜치를 정리한다(남기지 않음). 잠금 해제 전에 정리.
 - 기준선 프로세스는 Builder worktree를 읽거나 쓰지 않는다(경로가 다름). 로그에 BASELINE start/end 시각을 남겨 겹침을 기록한다.
 - 테스트: 순서·대기·정리 로직을 devpipe/정적 검사로(가능한 만큼). 예: 기준선 결과 파일이 없을 때 check가 기다리거나 STOP, 정리 함수가 Builder 실패
   경로에서도 불리는지(정적).

D4 큐 간격 15 → 5분 (register-dev-tasks.ps1)
 - $queueIntervalMinutes = 5. 실행 제한·IgnoreNew·dev-queue 상한 관계(commit-docs 900초 + dev-run 340분 + 5 ≤ 360)는 그대로. 정적 테스트 숫자 갱신.
 - 등록은 하지 않는다(병합 뒤 사용자 1번, 같은 이름 덮어쓰기).

N1 추가 줄 권한 표지 (devpipe, 올리기만)
 - 추가된 줄에서(대소문자 무시): `(watchlist|active_universe|new_buy_instrument)_approved` 뒤 `[:=]` 다음 값이 true ·
   `quantity_authority` 뒤 `[:=]` 값이 none/null/"none"이 아님 · `execution_quantity` 뒤 `[:=]` 값이 null/None/"null"이 아님 → class = authority.
 - 테스트: 각 표지 true/숫자 → authority, false/none/null → general 유지(그 줄만으로는), 내리는 경로 없음.

N2 문서: README "테스트" 줄과 judge-prompt.md에 "expected failures 증가 = 실패(재시도 대상)" 한 줄. judge-prompt.md의 다른 문장은 바꾸지 않는다.

O3 메인 체크아웃·run 기록 보호 (좁게 — 오탐을 만들지 않는 범위)
 a. run.json·baseline 캐시 파일의 sha256을 dev-run 프로세스가 단계마다 기록하고 다음 단계 전에 대조 → 어긋나면 STOP_RUN_RECORD_CHANGED.
 b. Builder 1회차 시작 전과 check 직전에 메인 체크아웃의 `git status --porcelain --untracked-files=no` 중 docs/claude/ 밖 줄 집합과
    workspace/policies/*·stock-strategy-system/*(추적·무시 모두)의 sha256 목록을 비교 → 새로 바뀐 것이 있으면 STOP_MAIN_TOUCHED(재시도 없음).
    시작 전부터 있던 변경은 대상 아님(전후 비교). docs/claude/ 변경과 HEAD 이동(문서 커밋)은 무시.
    단, auto-core가 기록 모드에서 06:15에 상태 파일을 쓰는 것과 겹치면 오탐이 난다 → 그 시각(06:10~06:40 KST)에 걸친 실행이면 b의 상태 파일 비교만
    건너뛰고 로그에 SKIPPED_AUTO_CORE_WINDOW를 남긴다(fail-closed가 아닌 예외임을 보고에 적는다).
 - 테스트: a 변조 → STOP, b 정책 파일 변경 → STOP, docs/claude 변경·문서 커밋 → 통과.

전체: test_dev_pipeline 전부 OK, 기존 settings 검사 테스트 3개 OK, 전체 스위트 실패 집합 ⊆ 0단계 a, 스키마 PASS.
Windows 실측(모델 호출 없이): ① PowerShell 파서 오류 0 ② register-dev-tasks.ps1 -PlanOnly 출력(5분 간격) ③ devpipe 경로 길이 계산을
이 PC 실제 경로로 1번(id 10자·28자 두 값의 결과).
~~~

## 3. 보고 (docs/claude/redesign-t3b-builder-report-2026-10-10.md, 한국어)
1. 0단계 a~d. 2. 바꾼 파일·줄(D1~D4·N1·N2·O3 각각), 테스트 수치(대상·전체·기준선 대비), Windows 실측 원문. 3. Builder 판단 목록. 4. 남는 위험.

## 4. 병합 뒤 배포
1. 사용자: 병합 명령(Cowork 제공) → `powershell -ExecutionPolicy Bypass -File tools\register-dev-tasks.ps1` 1번(5분 간격으로 덮어쓰기).
2. Cowork: 다음 파이프라인 작업 1건에서 1절 완료 기준 ①②③ 확인 → 관제판 redesign-t3b 완료.
3. Cowork(선택, 일회 승인 1번): 06:55 "자동 운영 코어 결과 알림" 지시문에 dev-runs/LATEST.json(병합 대기)·heartbeat(30분 넘게 멈춤) 한 줄씩(Judge 의견 O4).

## 5. 루프 점검 (loop-design-check 요지 — 설계 의견)
- 목표는 판정 가능: 경로 길이 수식, 기준선 실패 수, 큐→Builder 시작 시간, 겹침 로그 시각.
- 경계 그대로: 판정 기준(새 실패 0·테스트 수·범위·보호 경로)은 바뀌지 않고 더 엄격해진다(D2·N1·O3). 파이프라인이 자기 규칙을 고치는 경로는 여전히 없다(보호 경로 → 이 문서처럼 기존 방식).
- 재시도 횟수·자동 병합 없음은 그대로. D3 동시 실행은 정확도를 바꾸지 않고(같은 base·같은 python·같은 브랜치 조건) 기다림만 줄인다.

## 6. Judge 확인 항목 (Cowork가 Builder 뒤 Judge 지시문에 그대로 넣는다)
- K1 범위: 2절 허용 경로 안뿐. settings.json·.gitignore·dev-merge.ps1·builder-rules.md·authority-paths.txt·commit-docs.ps1·run-docs-commit.ps1 변경 0.
- K2 D1: 수식이 UTF-16 길이·NUL·최장 추적 경로·기준선 임시 이름까지 포함하는가. 모델·기준선·worktree 생성 전에 멈추는가. 경계값 테스트.
- K3 D2: 기준선 worktree가 브랜치 위이고, 지우는 대상이 devpipe-base- 이름 공간 + 이번 실행 생성분 + base 가리킴으로 한정되는가. 캐시 키 버전.
  같은 기준선 조건에서 Builder worktree와 실패 집합이 비교 가능한가(detached 시절 11건이 사라졌는지 실측).
- K4 D3: 기준선이 Builder와 겹쳐 돌아도 판정 입력이 같은가(같은 base·python·브랜치 조건), 기준선 실패·시간 초과가 STOP이고, 모든 종료 경로에서
  기준선 프로세스·임시 worktree·브랜치가 정리되는가. git 잠금 경합(worktree 동시 생성)이 없는가.
- K5 D4: 5분 간격, 다른 상한 관계 유지, 등록 스크립트가 두 이름만.
- K6 N1: 추가 줄 표지가 올리기만 하는가. 오탐 범위(예: quantity_authority: "none"은 general)가 맞는가.
- K7 O3: a·b가 실제로 run 기록 변조·메인 정책/상태/추적 파일 변경을 잡고, docs/claude 변경·문서 커밋은 통과시키는가. auto-core 시간대 예외가 상태 파일 비교에만
  좁게 걸리는가(정책·추적 파일 비교는 그대로).
- K8 회귀: 1차·2차 T3 Judge의 J2(자기 규칙 보호)·J3(deny·ask)·J6(병합 조건) 근거가 그대로인가. 전체 스위트 실패 집합 ⊆ 기준선, 테스트 수 감소 0.

## 7. 사용자 조작 (Windows PowerShell — t3-trial-1 병합과 CLAUDE.md 커밋을 먼저 끝낸 뒤)
```
cd "E:\사업\##금동한\코덱스저장소"
.\tools\commit-docs.ps1
claude --worktree t3b --model opus --effort xhigh
```
- 둘째 줄 뒤 `OK … -> <해시>`가 보이면 셋째 줄(지시문이 커밋돼야 worktree에 들어간다).
- Claude Code 첫 메시지:
```
Read docs/claude/redesign-t3b-builder-prompt-2026-10-10.md and follow sections 0-3 exactly (section 6 is what the Judge will check).
```
- tools/ 편집 승인 창이 여러 번 뜨면 승인. 끝나면 Cowork에 "T3b Builder 완료"만.
