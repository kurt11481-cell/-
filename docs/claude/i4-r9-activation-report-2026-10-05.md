# I4 R9 활성화 Builder 보고 — Kiwoom acceptance `45cf1888…` 활성화 (2026-10-05, K3)

- 역할: I4 R9 활성화 Builder(Claude Code, Opus 5.5 xhigh).
- 근거
  - `docs/claude/i4-r6-builder-report-2026-10-05.md` §4-3·§7-1·§7-2
  - `docs/claude/system-review-p4-roadmap-2026-09-30.md` §4 S8(R9·G4)과 §9의 10/5 기록(R8 PASS, 병합 `472d507`, R9 순서 결정)
- 위치: 원본 폴더. worktree는 만들지 않았다. 브랜치는 `codex/master-recovery-expansion`이다.
- HEAD
  - 시작 `472d507`
  - 원본 적용 직전 `b08f341`. 다른 세션이 문서 커밋 1개를 추가했다(`docs/claude/future-tools-roadmap-2026-10-05.md` 1개 파일). 테스트가 읽지 않는 파일이어서 2단계 결과에 영향이 없다고 판단했다(§5-4).
- 권한: `order_authority=false`, `quantity_authority`는 그대로다.
  - 정책 파일의 값은 `false`, pin-scope의 값은 `none`이다.
  - 정책 JSON 비교 결과, 바뀐 경로는 계획한 17곳뿐이다.
- 범위 밖 파일은 diff 0이다: `alert_policy.json`, `SKILL.md`, 코드·테스트, 다른 정책·상태·원장. 테스트 기대값도 바꾸지 않았다.
- 커밋: 아직 하지 않았다. 승인을 요청한다(§7).

## 0. 시작 전 확인 (0단계)

| 확인 | 결과 |
|---|---|
| R7 후보 원시 sha256 | `45cf188892601d61c117519b4d34fc9e6b2ee82074489b8dd9cc0b661ca8bc80` 일치. LF 1, BOM 없음, git status 0줄. 원본 적용 직전에 다시 확인했다(R8 조건 ①) |
| 정책 2개의 `f0bab…` | priority policy 16곳(소문자 15, 대문자 1), source_capabilities 1곳(대문자). 합계 17 |
| 정책 2개의 `45cf…` | 0곳 |
| git status(`workspace/policies`, `workspace/state`, `stock-strategy-system`, `CLAUDE.md`, `manage-us-stock-strategy`) | 0줄 |
| 현재 shadow 지문 | 저장값 = 재계산값 = `628c6081…` |
| `f0bab`가 남는 곳 | pin-scope asset `allowed_drift_predecessor_sha256` 1곳(설계상 남김, R6 §3-3), 옛 calendar 보고서 1개 |

## 1. 계획 (사용자 승인)

- ① 정책 17곳은 원시 바이트에서 64자 해시만 같은 대소문자로 바꾼다.
- ② `migrate_integrated_shadow_cohort.py`로 cohort를 이관한다.
  - 이 스크립트는 지문이 바뀌면 카운터를 검사하지 않는다. 그래서 실행 전에 따로 확인했다. 정수 카운터는 모두 0, 목록은 모두 비어 있음, `baseline_overlay_sessions`는 모두 0, `last_attempt_hash`는 null이어야 한다.
- ③ CLAUDE.md 23~24행을 3행으로 바꾼다. 이어지는 줄의 들여쓰기는 기존처럼 2칸이다.
- 사용자 추가 조건
  1. 커밋할 때 R9 파일만 경로를 지정해 stage한다.
  2. 새 보관 파일도 커밋에 넣는다.
  3. 이관 뒤 `shadow_progress.json`이 CRLF 28줄인지 보고한다. 바뀌었으면 멈추고 묻는다.
- 적용 도구: scratchpad의 `r9_apply.py`(저장소 밖).
  - 단계마다 개수, 경로, 줄바꿈, 권한 필드를 단언한다. 어긋나면 쓰지 않고 멈춘다.
  - 복사본과 원본에 같은 도구를 썼다.

## 2. 복사본 시험 (2단계)

- 원본을 scratchpad `r9base`로 `robocopy /E /COPY:DT`로 복사했다.
  - 뺀 것: `.claude/worktrees`, `.runtime-cache`. 넣은 것: `.git`, `.claude/settings.json`.
  - 추적 파일 1,064개가 원본과 원시 바이트까지 같다(누락 0, 불일치 0). git status 73줄도 같고, HEAD는 `472d507`이다.
- `r9base`를 `r9sim`으로 다시 복사하고, `r9sim`에만 ①②를 적용했다.
  - 두 복사본의 차이는 정책 2개, `shadow_progress.json`, 새 보관 파일 1개뿐이다.

| 확인 | `r9base`(활성화 전) | `r9sim`(①② 적용) |
|---|---|---|
| 전체 테스트(서브에이전트, 기본 환경) | `Ran 2452` / failures 9, errors 1 = 10건 | `Ran 2452` / failures 7, errors 1 = 8건 |
| v2_6_7 acceptance 2건 | 실패. 구현 해시 불일치 6개, R6 §6-1과 같음 | **해소** |
| cohort 테스트 `test_provider_authority_change_starts_zero_count_cohort` | 통과(지문 불변) | 통과. 모듈 -v 실행에서 42건 OK |
| 새 실패 | — | **0** |
| 운영 검증기 CLI(후보 기준) | FAIL, 오류 17. 정책·등록부 2 + 15종목(음성 대조) | PASS, 오류 0 |

남은 8건은 기준선과 같은 테스트이고 원인도 같다(환경·상태 의존, R6 §1).
- `test_save_daily_pipeline`: `pypdf` 없음
- dashboard 2건: NBIS 13 ≠ 15
- `test_sec_scheduled_shadow` 01·05·23: `Join-Path`에 `$PSScriptRoot` 빈 값
- `test_sec_scheduled_shadow` 35·37: `SEC_ACCESS_BLOCKED` 종료 코드 1 ≠ 7

## 3. 원본 적용 (3단계)

### 3-1. 파일별 해시와 줄바꿈

- 정규화 해시는 `validate_skill_deployment.normalized_text_sha256`과 같은 방식이다(utf-8-sig, CRLF·CR→LF). 소문자로 적었다.
- 모든 파일이 BOM 없음을 유지했다. 단독 CR은 0이다.

| 파일 | 크기 | 원시 sha256 (전 → 후) | 정규화 sha256 (전 → 후) | 줄바꿈 (전 → 후) |
|---|---|---|---|---|
| `workspace/policies/kiwoom-session-aware-priority-policy.json` | 12397 → 12397 | `a3d2ae10c853af388758260746bc652472196c83571bc150c9d94a116ae114b2` → `d315c3d3326b32519df4fc2791d6c75890ff0887dc54f2542bf10730f40599d1` | 원시와 같음 | LF 109 → 109, CRLF 0 |
| `workspace/policies/source_capabilities.json` | 7856 → 7856 | `19e9a31e0239e3f9ae0ff49a9cba0a2bdf3ddc3db9ff1fe6cef1173a4eea3512` → `351a34959797ccf960a03147d4b580dc77de59548b56f7c386a9224f89d1f660` | 원시와 같음 | LF 171 → 171, CRLF 0 |
| `workspace/state/integrated_shadow/shadow_progress.json` | 918 → 922 | `a37d01c468b8d2884460f6e671f4fc1b9a2b8c21d81add15aff68fd133d18ead` → `24148cd76cd8c8e77badfa85994e462bfb519627e1561d2bed9c0b0d638dec01` | `99399900399f7ef65aed42df038786d69b4aac98f6afcbc11039505573c518ec` → `0bd8bdcda233e716e8bb2408dfd56dbc01e089c2baafc6a7435137837c1dacfb` | **CRLF 28 → 28**, LF만 있는 줄 0 → 0 |
| `workspace/state/integrated_shadow/cohorts/integrated-shadow-628c60818f3beeb2/superseded_progress.json`(새 파일) | — → 1280 | — → `9f84317473f4fd2f0abeee53321dcf1b4e6ec6db7596a0d6b9cedb43dcf6ca04` | — → `4ceb04b5180efa0b1d73c751b1c41fa1d92f2e76746018d3eacba0b2150bfda1` | — → CRLF 36, LF만 있는 줄 0 |
| `CLAUDE.md` | 4440 → 4612 | `92c2f066e36c73c15e4657abae2896ba20b4e07fbfa9d4f57fccc9e05c3bc99b` → `ed5f37b2932a6b19a4e94be4cfde90f7656fd5da983ca578728f8c931a9d208c` | `91ef6affe3b40403319490b75e0b6ce046dda9532ef0566fdfcb4007528affdd` → `01ceafcd4f0e7c067f5f94f792f929f4ebcae19607a1932d1cea633d3ab132e9` | CRLF 58 → 59(1줄 추가), LF만 있는 줄 0 → 0 |
| R7 후보(변경 없음) | 11176 | `45cf1888…8bc80` | 원시와 같음 | LF 1 |

- 정책 2개의 적용 후 원시 해시는 `r9sim`과 같다. 같은 바이트다.

### 3-2. 항목별 결과

- **①**
  - priority policy에서 바뀐 경로: `$.provider_scopes[0..14].acceptance_artifact_hash` 15곳(SOXL, MVLL, NBIS, BE, TOST, NOW, FSLY, SOXX, MRVL, AAPL, IBM, PGR, JPM, CME, V 순)과 `$.acceptance_evidence.session_aware_acceptance_manifest_sha256` 1곳(대문자).
  - source_capabilities에서 바뀐 경로: `$.providers[7].acceptance_artifact_sha256` 1곳(`kiwoom_rest`, 대문자).
  - 적용 뒤 `f0bab`는 0곳, `45cf`는 17곳이다. git numstat은 16/16, 1/1이다.
- **②**
  - 실행 전 확인: 이전 cohort `integrated-shadow-628c60818f3beeb2`의 카운터가 모두 0이고 목록이 모두 비어 있었다. 버린 카운터는 없다.
  - 출력: `COHORT_SUPERSEDED_AND_ZERO_INITIALIZED`, `integrated-shadow-628c60818f3beeb2` → `integrated-shadow-4f11526e20929f11`
  - 새 지문: `4f11526e20929f1193cea70f2777d9b91ccdc1e7d887b38dcb18af7161bc1203`. 계획 때 미리 계산한 값, R6 모의 활성화 값과 같다.
  - `started_at`: `2026-10-05T05:56:10.849983+00:00`
  - 새 `shadow_progress.json`은 키 순서와 개수가 이전과 같다. 0회이고, `promotion_status`는 `EXPLICIT_USER_APPROVAL_REQUIRED`, `order_authority`는 false다.
  - 보관 파일
    - `prior_progress`가 이전 파일 내용과 같다.
    - `superseded_by`는 새 cohort다.
    - `COHORT_SUPERSEDED`, `order_authority=false`다.
    - `superseded-shadow-cohort.schema.json` 검증 오류는 0이다.
  - git diff에서 `shadow_progress.json`은 3줄 바뀌었다(`cohort_id`, `semantic_fingerprint`, `started_at`).
  - **사용자 조건 3: `shadow_progress.json`은 이관 뒤에도 CRLF 28줄 그대로다.** 스크립트가 Windows 텍스트 모드로 쓰기 때문이다.
- **③**
  - CLAUDE.md 23~25행이 아래로 바뀌었다(+3/−2).
  ```
  - Kiwoom acceptance pins the files listed in manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json
    (normalized text hashes). Editing a listed file invalidates the active acceptance: treat it as K3.
    run_manual_portfolio_analysis.py is not pinned; its guards live in pinned manual_data_guards.py and scheduled_input_gate.py.
  ```
  - 문구가 pin-scope와 맞는지 확인했다.
    - `hash_mode`는 `NORMALIZED_TEXT_SHA256`이다.
    - `run_manual`은 고정 목록에 없다.
    - `manual_data_guards.py`와 `scheduled_input_gate.py`는 고정 목록 27개 안에 있다.
  - CLAUDE.md를 읽는 테스트(`test_reconcile_broker_state`의 확인 규칙 문구)는 이 줄과 관계없고 통과했다.

## 4. 원본 검증 (4단계)

| 확인 | 결과 |
|---|---|
| 전체 테스트(서브에이전트, 기본 환경) | `Ran 2452` / failures 7, errors 1 = 8건. 실패 목록이 `r9sim`과 같다 |
| 기준(`r9base` 10건) 대비 | 해소 2건(v2_6_7 acceptance), **새 실패 0** |
| acceptance 관련 실패 | **0**. 로그에 `acceptance`, `implementation hash`, `semantic_fingerprint`가 실패로 나오지 않는다 |
| `test_v2_6_7_session_aware_kiwoom_priority` -v | 42건 OK. 지정한 세 테스트 모두 ok |
| `test_materialize_kiwoom_session_aware_acceptance_candidate` -v | 24건 OK. 활성화 뒤에도 깨지지 않는다(R6 §3-3 설계 확인) |
| 운영 검증기 `validate_kiwoom_session_aware_acceptance.py`(후보 manifest, 정책 2개와 각 스키마) | PASS, 오류 0, 종료 코드 0 |
| 스키마 감사 `validate_schema_contracts.py` | PASS, 오류 0 |
| 테스트가 저장소 상태를 바꿨는가 | 아니다. 실행 전후 git status 933줄이 같다 |

**G4 판정:** 아래 네 조건을 모두 충족한다.
- R8 PASS
- 사용자 승인
- 활성화 뒤 전체 테스트에서 acceptance 관련 실패 0
- CLAUDE.md Change classes 문구 갱신

남은 8건은 환경·상태 의존이다. 이 목록은 R6·R8 기준선과 같다.

## 5. 남는 점과 확인 필요

1. **보관 파일의 `reason`이 실제 이유와 다르다.**
   - 이관 스크립트가 `GLOBAL_AUTHORITY_VOLUME_AND_DUAL_RUN_SEMANTICS_CHANGE`를 고정해서 쓴다.
   - 스키마 enum에는 더 맞는 `SESSION_AWARE_KIWOOM_PROVIDER_AUTHORITY_CHANGE`가 있다.
   - 스키마상으로는 유효하다. 이 값으로 판단하는 코드는 없다(grep 확인).
   - 코드와 보관 파일은 범위 밖이어서 고치지 않았다.
   - 제안(K2): S7 2차 이관 전에 스크립트에 `--reason` 인자를 추가한다.
   - 기존 보관 파일들의 `reason`도 일관되지 않다. null 7개, enum 밖 값 2개(`EVENT_COVERAGE_AND_GATE_SEMANTICS_CHANGE`, `APPROVED_MANUAL_TIMING_M1_M5_TRANSITION`)가 있다.
2. **이관 스크립트는 지문이 바뀌면 이전 카운터가 0이 아니어도 보관하고 0으로 시작한다.**
   - 보관 파일에 원래 값이 남으므로 기록이 사라지지는 않는다. 다만 멈추지는 않는다.
   - 이번에는 Builder가 실행 전에 따로 0을 확인했다.
   - S7 2차 이관 때도 같은 확인이 필요하다. 아니면 K2로 가드를 추가한다.
3. **git이 정책 2개에 "LF will be replaced by CRLF" 경고를 낸다(`core.autocrlf=true`).**
   - 커밋은 작업 폴더 바이트를 바꾸지 않는다.
   - 다만 나중에 checkout이나 merge가 이 파일을 다시 쓰면 CRLF가 되어 원시 해시가 바뀐다.
   - shadow 지문과 운영 검증기는 정규화 해시나 내용 비교를 쓰므로 영향이 없다고 본다. 확인은 하지 않았다.
   - R7 후보 파일은 같은 이유로 LF를 유지해야 한다(R8 조건 ①, `test_v2_6_7` helper `:94`).
4. **작업 중 HEAD가 움직였다**(`472d507` → `b08f341`).
   - 다른 세션의 문서 커밋 1개다. 테스트는 `docs/claude/`의 이 파일을 읽지 않는다(grep 확인).
   - 원본 전체 테스트는 `b08f341`에서 돌렸고 결과가 `r9sim`과 같다.
5. **pin-scope의 `allowed_drift_predecessor_sha256`는 여전히 `f0bab…`이다.**
   - 이제 다른 선행과 일치하지 않으므로 드리프트를 하나도 넘기지 못한다(R6 §3-3).
   - 다시 묶으려면 고정 asset을 고쳐야 하므로 K3 경로다.
6. **R8 한계를 그대로 물려받는다.**
   - 정규장 검증은 11종목이고, PGR·JPM·CME·V는 `f0bab…` 승인을 물려받는다.
   - 08-13/14 증거를 재사용했다(사용자 결정 2d).
   - `test_v2_6_7` helper가 원시 해시에 의존하므로 worktree나 새 clone에서는 판정할 수 없다(R6 §7-3).
7. **다음 cohort 이관.** S7 2차(X15)에서 한 번 더 한다(사용자 순서 결정). 지금 새 cohort는 0회다.
8. **진행 기록.** 로드맵 §9에 R9 기록을 추가하는 일은 이번 범위 밖이어서 하지 않았다. 그 파일에는 다른 세션의 커밋 안 된 변경도 있다. Cowork에서 추가하기를 권한다.
9. **R8의 비차단 K2 보강 제안 4개는 그대로 남는다.**

## 6. 실행 위치와 남긴 파일

- 복사본 `r9base`·`r9sim`, 적용 도구 `r9_apply.py`, 로그(`r9base-full.log`, `r9sim-full.log`, `orig-after-full.log`), 적용 결과 JSON은 세션 scratchpad에 있다. 저장소 밖이다.
- 저장소에서 바뀐 파일은 6개다: 정책 2, `shadow_progress.json`, 새 보관 파일 1, `CLAUDE.md`, 이 보고서.

## 7. 커밋 요청

- stage는 아래 경로만 지정한다(`git add -A`·`git add .`는 쓰지 않음).
  ```
  git add -- CLAUDE.md workspace/policies/kiwoom-session-aware-priority-policy.json workspace/policies/source_capabilities.json workspace/state/integrated_shadow/shadow_progress.json workspace/state/integrated_shadow/cohorts/integrated-shadow-628c60818f3beeb2/superseded_progress.json docs/claude/i4-r9-activation-report-2026-10-05.md
  ```
- 메시지안: `feat(governance): I4 R9 activate Kiwoom acceptance 45cf1888 and start zero-count shadow cohort (K3)`
- push는 하지 않는다.

fail-open 8종을 새 결정 경로마다 대어 봤다: 예.
- 활성 acceptance 바인딩(정책 17곳)
  - Partial: 일부만 바꾸면 운영 검증기가 바인딩마다 FAIL을 낸다(음성 대조에서 17건). 적용 뒤 `f0bab`는 0곳이다.
  - Stale: 08-13/14 증거 재사용과 4종목 승인 승계는 기존 R8 한계로 남겼다. 새로 생긴 Stale 경로는 없다.
  - Missing: 후보, 원천 증거, 구현 파일이 없으면 검증기가 FAIL한다. 코드는 바꾸지 않았다.
  - Unknown·Deny-list·Swallowed: 새 분류나 예외 처리 코드가 없다. 검증은 고정 경로 전체에 대한 허용 목록 방식 그대로다.
  - Fallback: FSLY yfinance 대체와 진단용 shadow의 역할은 바뀌지 않았다. 대체 경로에 권한이 새로 붙지 않았다.
  - Permission widening: 설정·hook·MCP 변경이 없다. 권한 필드는 JSON 비교로 불변을 확인했다.
- cohort 이관
  - 스크립트가 0이 아닌 카운터를 막지 않는 점(§5-2)은 Builder가 실행 전에 따로 확인해서 막았다.
  - 지문 Stale은 테스트가 저장값 = 재계산값으로 막는다.
  - `reason` 라벨이 실제와 다른 점(§5-1)은 판단에 쓰이지 않는다. 기록만 부정확하다.
- CLAUDE.md 문구
  - 고정 대상을 pin-scope 파일 목록으로 가리킨다. 그래서 목록이 바뀌면 문구도 따라간다.
  - 고정되지 않은 공용 helper(R6 §7-5)를 고치는 일은 이 줄로는 K3가 되지 않는다. 다만 위 줄 "K3 production semantics or authority"에 걸린다. 권한이 넓어지지는 않는다.
