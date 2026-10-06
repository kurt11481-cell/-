# r-sched-b K3 설계 — 예약 런타임 clone에 안 B′ 반영 (2026-10-06, 설계만)

- 관제판 작업: `r-sched-b` ("예약 분석에도 '내역 없음' 제한 풀기")
- 등급: K3(예약 Production 런타임 교체). 이 문서는 설계만 한다. 코드·정책·상태·clone·예약 설정은 바꾸지 않았다.
- 작성: Cowork(Opus). 조사는 모두 읽기 전용(git 조회, 해시 재계산, 파일 읽기)이다. 키움 조회·주문 도구는 쓰지 않았다.
- 권한 불변: `order_authority=false`, `quantity_authority=none`, `execution_quantity=null`.
- 근거: `s1b-plan-b-design-2026-10-03.md` §6·§9, `s1b-plan-b-builder-report-2026-10-04.md`, `handover-system-review-2026-09-30.md` §3, `i4-r9-activation-report-2026-10-05.md`, `system-review-p4-roadmap-2026-09-30.md` §5 보류 표·§9, `system-review-phase1-2026-09-30.md`, `schedule-timing-review-2026-10-05.md`.
- **소비처(이 문서를 읽는 곳)**
  - 관제판 `r-sched-b`(next·doc 칸이 이 문서를 가리킨다)
  - 독립 Judge 세션(§8 전달 사항)
  - Codex 예약 자동화 재개 작업(로드맵 §5 보류 표의 "예약 자동화 재개 전" 항목들과 함께 읽는다)
  - 옵션 A를 고를 때의 Builder 지시문(§6 절차)

## 1. 결론

- **권장: 지금은 clone을 올리지 않는다(NO_CHANGE).** `r-sched-b`는 "Codex 예약 자동화 재개" 묶음으로 넘기고, 재개를 결정할 때 §6 절차로 한 번에 올린다.
- 이유
  1. **clone을 쓰는 예약 작업이 지금 돌지 않는다.** Codex Pre-Open·Post-Close 두 작업 모두 `status = "PAUSED"`(마지막 수정 2026-08-27)다. 활성 Cowork 예약 13개는 clone을 쓰지 않는다(§5). 그래서 "예약 분석에 같은 제한이 남는" 실행은 지금 없다.
  2. **올리는 범위가 안 B′만이 아니다.** clone `41f7b3f`에서 지금 개발 HEAD까지 127커밋, 391파일이 바뀐다(§3). 통합 권한(integrated authority), I0 조정, S7, SEC, acceptance `45cf1888`, 새 shadow cohort가 함께 들어간다.
  3. **단순 checkout으로는 원시 해시 산출물이 깨질 수 있다(§4-2).** 통합 권한 산출물 2개는 원시 sha256으로 검사한다. Windows 기본 줄바꿈 변환(autocrlf=true)으로 checkout하면 해시가 달라져 `INTEGRITY_FAILURE`로 막힌다(fail-closed). 재개 때 함께 검증해야 한 번으로 끝난다.
  4. 재개에는 이것 말고도 막힘이 남아 있다(§5-4: `portfolio_hash` 고정 재설계, Stage 1 실제 예약 실행 등). clone만 올려서는 예약 실행이 생기지 않는다.
- **안 B′ 자체는 수동 경로에서 확인됐다.** 2026-10-06 09:02 KST 수동 분석(`manual-20261006T000228421953Z-6f59e85f595a`)에서 `evidence_grade=GRADE_B`, `preflight_status=PASS`, `decision_quality_eligible=true`, `terminated_by=PROVIDER_NO_DATA_DECLARATION`, `scope_complete=true`를 확인했다(읽기 전용 집계). 설계 §9-8의 "병합 뒤 라이브 1회"에 해당한다.
- 사용자 결정은 §9.

## 2. 확인한 사실 (2026-10-06, 읽기 전용)

| 항목 | 결과 | 확인 방법 |
|---|---|---|
| clone HEAD | `41f7b3f821a48b5b2e6d308de4ef4d6e5b92a993`, 브랜치 `main`, 추적 변경 0, 미추적 0 | clone 폴더를 저장소 worktree 정보로 읽음 |
| clone의 정체 | 별도 clone이 아니라 개발 저장소에 **연결된 worktree**다(`.git` 파일 → `코덱스저장소/.git/worktrees/stock-strategy-scheduled`). `.git/config`·객체를 공유한다 | `.git` 파일, `git worktree list` |
| `main` 위치 | `main` = `41f7b3f`. 개발 브랜치는 `codex/master-recovery-expansion`(HEAD `3594527`) | `git rev-parse` |
| 갈라짐 | `41f7b3f`는 개발 HEAD의 조상이 **아니다**. 공통 조상 `bfefbfc`(2026-08-15). `main`에만 있는 커밋 12개(병합 4 + 일반 8). 일반 8개는 모두 개발 브랜치에 같은 패치가 있다(`git cherry` 전부 `-`) | `merge-base`, `cherry` |
| main 쪽 파일 77개 | 개발 HEAD와 내용이 같음 73, 다름 4. 다른 4개(`continuous_improvement_sidecar.py`, `strategy_evolution.py`와 각 테스트)는 개발 브랜치에서 그 뒤에 더 고친 판이다(`7da9df5`, `52fb932`) | blob 비교, `git log` |
| 바뀌는 양 | `41f7b3f..HEAD` 127커밋(첫 부모 109), 391파일, +374,312/−895 | `diff --shortstat` |
| 안 B′ 포함 | `617b693`(구현), 병합 `02d9250`(2026-10-04). 바뀐 코드는 `kiwoom_account_readonly_bridge.py` 1개 + 테스트 | `git show --stat` |
| clone의 브리지 | `terminated_by`·`no_data_declared` 없음(안 A·B′ 없음) | grep |
| 개발 작업 폴더 | 코드·정책은 HEAD와 내용이 같다(줄바꿈 차이만). 실제 내용 변경은 `docs/claude/` 9개뿐 | `diff --ignore-cr-at-eol` |
| Codex 예약 2개 | 둘 다 `PAUSED`. 프롬프트가 clone 경로, 기대 HEAD `41f7b3f…`, `deployment-provenance/current.json` 검증을 고정한다 | `.codex/automations/*/automation.toml` |
| clone 배포 증거 | `current.json`: `runtime_head=41f7b3f…`, `runtime_clean=true`, `semantic_cohort_id=integrated-shadow-246c0aa2eb76b27f`, `counting_enabled=true`, 검증 시각 2026-08-15 | 파일 읽기 |
| 설치된 Codex 스킬 | `~/.codex/skills/manage-us-stock-strategy/SKILL.md`가 `41f7b3f`·HEAD와 정규화 해시가 같다(SKILL.md는 그동안 안 바뀜) | 해시 비교 |

## 3. ① 운영 반영 범위

### 3-1. 옵션

| 옵션 | 내용 | 판단 |
|---|---|---|
| **0. 보류(권장)** | 지금은 아무것도 바꾸지 않는다. `r-sched-b`를 Codex 예약 자동화 재개 묶음에 넣는다. 재개를 결정하면 옵션 A 절차로 올린다 | 지금 영향을 받는 실행이 없다(§5). 재개 막힘(§5-4)과 한 번에 검증한다. 지침 7절 NO_CHANGE 우선 |
| A. 전체 올리기 | clone을 개발 브랜치의 고정 커밋 하나로 옮긴다. 자동화는 계속 PAUSED로 둔다 | 가능하다. 다만 127커밋을 예약 런타임에 넣는 일이라 K3·Judge·리허설이 필요하다(§6). 올려도 재개 전까지 효과가 없다 |
| B. 안 A·B′만 옮기기 | `main`에 브리지 변경만 cherry-pick | **비권장.** clone의 브리지는 이미 HEAD와 다른 옛 판이다(§4-1). clone은 옛 acceptance `d7c1e1d1…`에 묶여 있어 브리지를 고치면 그 acceptance를 다시 판정해야 한다. 세 번째 코드 줄기가 생긴다 |

### 3-2. 옵션 A의 범위

- **대상 커밋:** 착수 때의 개발 HEAD 중 하나를 전체 SHA로 고정한다. 조건: 그 커밋과 개발 작업 폴더 사이에 `manage-us-stock-strategy/`, `workspace/policies/`, `workspace/state/`, `stock-strategy-system/`, 두 권한 산출물 폴더의 차이가 0(줄바꿈 제외). 2026-10-06 기준 `3594527`이 이 조건을 만족한다(`706c940`·`db723c5`는 8개 파일이 달라 만족하지 않는다).
- **브랜치 방식(사용자 결정 2):** `41f7b3f`가 조상이 아니어서 `main`을 그대로 fast-forward할 수 없다.
  - A1. clone을 대상 SHA로 detached checkout한다. 프롬프트의 "committed `main`" 문구(Codex TOML 2개와 `PREOPEN_/POSTCLOSE_…_PROMPT_EN.md` 2개)를 고쳐야 한다. 앞의 둘은 저장소 밖, 뒤의 둘은 저장소 안 파일이다.
  - A2. 개발 브랜치에서 `git merge -s ours main`(트리는 그대로, `main`의 12커밋을 조상으로만 기록)을 커밋한 뒤 `main`을 그 커밋으로 fast-forward한다. 프롬프트 문구를 그대로 둘 수 있다. 개발 브랜치에 병합 커밋 1개가 생긴다. main 쪽 내용은 §2대로 이미 개발 브랜치에 있으므로 버려지는 변경은 없다(4개 파일은 개발 쪽이 더 새 판).
  - 권장은 A2다. 프롬프트·지시문 문구 변경(K3 텍스트)이 줄어든다. Judge가 판정한다.
- **함께 들어오는 큰 변경(예약 경로에서 처음 돈다):**
  - 통합 권한 스냅샷(`integrated_authority_snapshot.py`, 원시 해시 검사)
  - Kiwoom acceptance `45cf1888…`(고정 27개)와 새 shadow cohort `integrated-shadow-4f11526e20929f11`(0회부터 시작)
  - I0 조정 경로, S7 상태 쓰기 경계, SEC 공식 이벤트 수집, 대시보드·수동 분석 변경
  - 이 변경들은 수동 경로에서 승인·검증됐지만, 예약 경로에서는 한 번도 돈 적이 없다. 8/15 이후 실제 예약 실행 기록은 확인하지 못했다(phase1 §146).
- **바꾸지 않는 것:** 정책 의미, `alert_policy.json`, `portfolio_state.json`, 개발 저장소의 코드·테스트, 권한 3필드, 자동화 PAUSED 상태(올리기와 재개는 별개 결정).

## 4. ② Kiwoom acceptance `45cf1888` 재확인

### 4-1. 결과 (2026-10-06)

| 확인 | 결과 |
|---|---|
| 후보 파일 원시 sha256 | `45cf188892601d61c117519b4d34fc9e6b2ee82074489b8dd9cc0b661ca8bc80` 일치, LF만, git 추적 중(blob도 같은 해시) |
| pin-scope 목록 = 후보 `implementation_hashes` 키 | 같음(27개), `hash_mode=NORMALIZED_TEXT_SHA256` |
| 개발 작업 폴더 27개 정규화 해시 | 27/27 일치 |
| 개발 HEAD blob 27개 정규화 해시 | 27/27 일치 |
| HEAD 정책의 `45cf` 참조 | priority policy 16곳, source_capabilities 1곳(계 17), `f0bab` 0곳. R9 보고와 같다 |
| **clone 27개** | 일치 7, 불일치 7, **파일 없음 13**. 불일치에 `kiwoom_runtime_bridge.py`, `kiwoom_account_readonly_bridge.py`, `kiwoom_broker_shadow.py` 포함 |
| clone 정책의 acceptance | `45cf`·`f0bab` 모두 0곳. **옛 acceptance `d7c1e1d10999…`**(priority 12곳, source_capabilities 1곳)에 묶여 있다 |

- 정규화 방식은 `validate_skill_deployment.normalized_text_sha256`과 같다(utf-8-sig, CRLF·CR→LF).
- 운영 검증기 `validate_kiwoom_session_aware_acceptance.py`도 정규화 해시를 쓴다. 그래서 줄바꿈이 바뀌어도 이 검증은 통과한다.
- 안 B′(브리지)는 `45cf1888`의 고정 27개 안에 있고, 그 해시가 HEAD와 맞는다. 즉 안 B′는 지금 활성 acceptance가 이미 덮는다.

### 4-2. 줄바꿈 위험 (원시 해시)

- 이 저장소에는 `.gitattributes`가 없다. clone은 개발 저장소의 `.git/config`를 공유하고, 거기에는 `core.autocrlf`가 없다. Windows 쪽 전역 설정값은 **확인 필요**다(VM git은 true, R6 보고에서 Windows 병합 때 CRLF로 바뀐 것을 재현).
- 원시 sha256으로 검사하는 곳
  - `integrated_authority_snapshot.py:167` 등: `workspace/instrument-identity-authority/artifacts/4664e82b…/…registry.json`, `workspace/calendar-authority/artifacts/2421eeb7…/…calendar.json`. 둘 다 추적 중이고 blob(LF)과 작업 폴더가 같다. **autocrlf=true로 checkout하면 해시가 달라져 `INTEGRITY_FAILURE`.** clone에는 지금 두 파일 모두 없다.
  - 후보 manifest: CRLF가 되면 원시 해시가 `baf992a8…`로 바뀐다. 운영 검증기는 정규화라 영향이 없다. `test_v2_6_7` helper는 원시라 실패한다(R6 §7-3).
  - 배포 증거 `deployment_provenance._sha`: 원시. 다만 clone 안에서 새로 만들므로 만든 뒤 바이트만 고정되면 된다.
- 바이트 재현성(전체 추적 1,073개 대비 지금 작업 폴더 바이트): autocrlf=false checkout이면 687개, true면 442개가 다르다. 두 방식 모두 다른 파일이 61개(실제 내용 변경 docs 9개 포함)다. `workspace/`·`stock-strategy-system/`·`assets/`만 보면 403개 중 152개가 true checkout에서 달라진다.
- 따라서 **"checkout 한 번 + 그대로 신뢰"는 안 된다.** 어느 방식으로 올리든 §6의 G 게이트로 원시 해시 소비처를 하나씩 확인해야 한다. 설계 권장: clone에만 `core.autocrlf=false`(worktree 전용 설정, `extensions.worktreeConfig` 필요)를 적용하는 방식을 리허설에서 먼저 시험한다. `.gitattributes` 추가는 저장소 전체에 영향이 있는 별도 K2/K3 항목으로 둔다.

## 5. ③ 예약 작업 영향

### 5-1. Codex 예약 2개 (clone 사용)

| 작업 | 상태 | clone을 올리면 |
|---|---|---|
| Pre-Open Portfolio Risk Refresh (`automation`) | PAUSED, 평일 09:00 ET | 지금은 영향 없음. 재개하면: 기대 HEAD·`current.json`이 맞지 않으면 `DEPLOYMENT_PROVENANCE_NOT_VERIFIED`로 멈춘다(fail-closed). 맞추면 "키움 읽기 전용 broker Shadow snapshot" 갱신에서 안 B′가 적용된다: 미체결 `scope_complete=true`, `open_orders_verified=true`(설계 §6 shadow 행) |
| Post-Close Portfolio Strategy | PAUSED, 평일 16:30 ET(+T+40/50/60 재시도) | 지금은 영향 없음. 재개하면: `HOLDING_STRATEGY_COMPILE`에서 대시보드 매도 근거가 `VERIFIED_NONE`이 되고, 다른 차단이 없으면 매도 지시가 `ORDER_INSTRUCTION_READY`가 될 수 있다(설계 §6 K3 핵심, 추론). `order_authority=false`, `broker_submission=DISABLED`는 그대로다 |

- 재개 뒤 예약 출력에도 설계 §9-4 운영 규칙이 그대로 적용돼야 한다: SELL READY를 쓰기 전에 키움 미체결·예약주문 화면을 확인한다(기준일·예약주문·주문 유효 기간 세 항목 해소 전까지).
- shadow cohort: clone의 배포 증거는 `integrated-shadow-246c0aa2eb76b27f`, 개발 HEAD의 현재 cohort는 `integrated-shadow-4f11526e20929f11`(0회)다. 올리면 새 cohort 기준으로 다시 센다. 예약 카운터를 옛 cohort에서 옮기지 않는다(보관만).
- 키움 런타임 `E:\사업\##금동한\runtime\Kiwoom-REST-API`는 수동·예약이 함께 쓴다. 10/6 수동 분석의 `runtime_commit`과 후보의 `official_runtime_commit`이 `69642586…`으로 같다. clone을 올려도 이 폴더는 바꾸지 않는다.

### 5-2. Cowork 예약 작업 (활성 13개)

- clone 경로, `41f7b3f`, `run_manual_portfolio_analysis.py`를 참조하는 작업은 **없다**(프롬프트 검색).
- 키움은 로컬 MCP `kiwoom_query`로 직접 조회한다. 예: 통합 점검(화~토 06:40)은 `overseas accounts open-orders`를 직접 읽고 "미체결 있으면 사용자 확인 필요"로 보고한다. 현황판(화~토 09:10)은 `return_code` 0·20을 정상으로 받는다.
- 따라서 clone을 올려도 Cowork 예약 13개에는 영향이 없다.

### 5-3. 지금 영향 정리

- 옵션 0: 영향 0.
- 옵션 A(PAUSED 유지): 실행 영향 0. clone 폴더 내용과 `current.json`만 바뀐다. 개발 저장소 쪽은 A2를 고르면 병합 커밋 1개와 `main` ref가 바뀐다.

### 5-4. Codex 예약 재개 전에 따로 풀어야 할 것 (이 작업 범위 밖, 기록)

1. `runtime_contract_suite.py:113`의 `portfolio_hash` 원시 해시 고정. 상태 파일에 적용할 때마다 깨지므로 재설계가 필요하다(로드맵 §5 보류 표, K2~K3).
2. `SKILL.md:130` 문구 정렬과 `alert_policy.json` 배포 게이트의 skill 해시 재고정, 설치 사본 갱신(로드맵 §5, K3).
3. Stage 1 실제 예약 장 마감 실행 1회(`docs/production-readiness.md`). 8/15 이후 등급 A 예약 실행 기록은 확인하지 못했다.
4. 두 자동화가 PAUSED된 이유(phase1 §384, 확인 필요).
5. 이 문서 §4-2의 줄바꿈 방식 결정.

## 6. 옵션 A 절차 (선택 시, K3)

전제: 사용자 결정, 이 설계에 대한 독립 Judge PASS, 자동화 PAUSED 유지. 모든 단계에서 `alert_policy.json`, `portfolio_state.json`, `workspace/policies/*`는 diff 0이다.

0. **고정:** 대상 커밋 SHA(§3-2 조건 확인), 브랜치 방식(A1/A2), 줄바꿈 방식을 계획서에 적고 승인받는다.
1. **리허설(저장소 밖 scratch 복사본):** 대상 커밋을 선택한 줄바꿈 방식으로 별도 폴더에 checkout하고, 아래 G1~G6을 모두 돌린다. 키움 호출 없음, 쓰기는 scratch 안에서만.
   - G1. 고정 27개 정규화 해시 = 후보 `implementation_hashes`
   - G2. `validate_kiwoom_session_aware_acceptance.py`(후보, 정책 2개와 스키마) PASS
   - G3. 통합 권한 산출물 2개 원시 sha256 = 폴더 이름의 해시. 통합 권한 스냅샷 로드가 `INTEGRITY_FAILURE` 없이 된다
   - G4. 원시 해시 소비처 전수 목록(`hashlib.sha256(...read_bytes())`/`file_hash` 사용처 중 추적 파일을 읽는 곳)을 만들고 각각 일치 확인
   - G5. 대상 테스트: `test_s1b_plan_b_no_data_pass`, `test_s1b_provider_marks`, `test_k2_bridge_evidence_integrity`, `test_v2_6_7_session_aware_kiwoom_priority`, `test_kiwoom_broker_shadow`, `test_reconcile_broker_state`. 전체 스위트는 서브에이전트로 돌려 개발 원본 기준선(R9 §4: failures 7, errors 1)과 실패 목록을 대조. 새 실패 0
   - G6. 스키마 감사 `validate_schema_contracts.py` PASS
2. **브랜치(A2일 때만, 사용자가 Windows 터미널에서):** 개발 브랜치에 `git merge -s ours main` 커밋 → 트리가 대상 SHA와 같은지(`git diff --stat` 0) → `main` fast-forward. push 없음.
3. **clone 반영(사용자가 Windows 터미널에서):** clone에서 대상 커밋으로 checkout. `git status` 0줄.
4. **clone 검증:** G1~G4, G6을 clone에서 다시 돌린다. 리허설과 결과가 같아야 한다.
5. **배포 증거:** 옛 `current.json`을 같은 폴더에 시각 이름으로 보관하고, `deployment_provenance.py`로 새 `current.json`을 만든다. `runtime_head`=대상 SHA, `runtime_clean=true`, 정책 해시, `provider_scope_hash`, `semantic_cohort_id`=개발 HEAD cohort를 확인한다.
6. **Codex TOML 2개:** 기대 HEAD 문자열만 대상 SHA로 바꾼다(A1이면 "committed main" 문구도). `status = "PAUSED"`는 그대로 둔다. 이 파일은 Codex 앱 설정이므로 사용자가 고치거나 Cowork가 사용자 승인 뒤 고친다.
7. **보고서:** `docs/claude/r-sched-b-builder-report-<날짜>.md`. 바뀐 것: clone HEAD, `current.json`, TOML 2개, (A2면) 병합 커밋·`main` ref.
8. **구현 Judge(별도 세션, 읽기 전용).**
9. **완료 기준(관제판 `doneWhen` 수정안):** "clone이 대상 SHA이고 G1~G6이 통과하며 배포 증거가 검증된다. 예약 실행에서의 확인(preflight PASS, `terminated_by`)은 재개 작업으로 넘긴다."
- **되돌리기:** clone을 `41f7b3f`로 되돌리고 보관한 `current.json`과 TOML 기대 HEAD를 복원한다. PAUSED 상태라 영향받는 실행이 없다. A2의 병합 커밋은 트리를 바꾸지 않으므로 그대로 두어도 된다.

## 7. 남는 위험 / 확인 필요

1. Windows git의 `core.autocrlf` 실제 값(확인 필요). 줄바꿈 방식 결정에 필요하다.
2. 관제판 `r-sched-b`의 완료 기준 "예약 작업 실행에서 … GRADE_B"는 맞지 않을 수 있다. 예약 실행은 `VERIFIED_SCHEDULED → GRADE_A`로 분류된다(`strategy_evolution.py:196`, 추론). §6-9 수정안을 제안한다.
3. clone이 개발 저장소에 연결된 worktree라는 점. VM에서 `git worktree list`가 `prunable`로 표시하는 것은 VM이 Windows 경로를 못 찾아서다(추론). **VM에서 `git worktree prune`을 실행하면 clone 등록이 지워질 수 있으니 실행하지 않는다.**
4. 갈라진 4개 파일은 개발 쪽이 더 새 판이라고 판단했다(커밋 기록 기준). 의미 비교는 Judge가 확인한다.
5. 127커밋 중 예약 경로에서만 쓰이는 코드(`dual_run_scheduler`, `runtime_contract_suite` 등)가 개발 이후 바뀐 내용과 맞는지는 리허설(G5)에서만 드러난다.
6. 원시 해시 소비처 전수 목록(G4)은 아직 만들지 않았다. 이 문서는 통합 권한 2개, 후보 manifest, 배포 증거만 확인했다.

## 8. Judge 전달 사항

- 판정 대상: §1 권장(옵션 0)의 타당성, 그리고 옵션 A를 고를 때 §6 절차가 K3 경계를 지키는지.
- 질문
  1. 자동화 PAUSED 상태에서 옵션 0이 fail-open을 남기지 않는가(지금 clone 코드로 도는 실행이 정말 없는가: TOML 2개와 Cowork 예약 13개 근거)
  2. A2(`merge -s ours`)가 main 쪽 변경을 잃지 않는가(§2 갈라짐 근거)
  3. §4-2 줄바꿈 위험과 G3·G4로 충분한가, 빠진 원시 해시 소비처가 있는가
  4. 새 cohort로 다시 세는 처리와 `counting_enabled=true`가 재개 전 잘못 세지 않는가
  5. 재개 뒤 `ORDER_INSTRUCTION_READY`가 예약 출력에 나올 때 운영 규칙(설계 §9-4)이 예약 출력에도 보이는가(표시 확인은 재개 작업에서)
- Judge는 파일을 고치지 않는다. 판정은 사용자가 전달한다.

## 9. 사용자 결정

- **결정 1:** 옵션 0(보류, 권장) / A(전체 올리기, PAUSED 유지) / B(비권장)
- **결정 2(A일 때):** 브랜치 방식 A2(권장) / A1
- **결정 3:** 관제판 `r-sched-b` 처리
  - 옵션 0이면: 상태를 `waiting`, 재개 조건을 "Codex 예약 자동화 재개 결정"으로 바꾸고, 완료 기준을 §6-9 수정안으로 바꾼다
  - 옵션 A면: 다음 단계를 "독립 Judge(이 문서)"로 바꾼다

**사용자 결정 (2026-10-06):** 결정 1 **옵션 0(보류)**. 결정 2는 해당 없음. 결정 3: 관제판 `r-sched-b`를 `waiting`으로 바꾸고, 재개 조건은 "Codex 예약 자동화 재개 결정", 완료 기준은 §6-9 수정안으로 바꿨다. clone·코드·정책·예약 설정은 바꾸지 않았다. Codex 예약 재개를 결정하면 §5-4 항목과 함께 이 문서 §6 절차로 진행하고, 그 전에 독립 Judge(§8)를 받는다.
