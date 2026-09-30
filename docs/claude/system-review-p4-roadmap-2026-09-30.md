# 투자_V2 재검토 P4: 로드맵 (2026-09-30)

- 선행 문서: `docs/claude/system-review-p3-design-2026-09-30.md`(§10 사용자 결정), `docs/claude/system-review-phase1-2026-09-30.md`(§1-2 단계, §7-3 결정)
- 범위: B1 순서를 실행 단계로 나눈다. 단계별 작업 위치·모델·K 등급, 완료·중단 기준, Claude Code 지시문, P3가 P4로 넘긴 미결 항목의 결정안.
- 방법:
  - 읽기 전용으로 진행했다. 코드·정책·포트폴리오 파일은 수정하지 않았고, 키움 주문 도구와 계좌 조회는 쓰지 않았다.
  - P3 설계를 실행 순서로 옮기면서 막히는 지점을 코드·설정·설정 가이드로 직접 확인했다(§1).
  - 키움 API 스펙(ust21070)은 스펙 조회 도구로 확인했다.
  - 초안을 별도 서브에이전트가 반론 검토했고(25건), 결과를 반영했다(§10).
- 상태: **승인(2026-09-30, §8).** S0부터 실행한다.
- 권장 설정: Opus · xhigh (K3 단계를 여러 개 묶는 로드맵).
- 표기: "확인 필요"는 확인하지 못한 항목, "(제안)"은 사용자 승인 전 설계안.

---

## 0. 결론

1. **순서는 S0 → (S1 ∥ S1b ∥ S2) → S3 → S4 → (S5 ∥ S6) → S7a → S7b → S8이다(§3).** 게이트는 5개다.
   - G0: 이 로드맵 승인
   - G1: I0 Judge PASS와 사용자 승인 → 승인된 커밋 ID로 병합
   - G2: 첫 실제 조정 뒤 `broker_diff_status=MATCH`
   - G3: 카드 파일럿 2회 중 "판단에 씀" 1회 이상 → I1 코드화
   - G4: R8 Judge PASS와 사용자 승인 → R9 활성화
2. **지금 할 일은 세 가지다.**
   1. (완료) 이 로드맵과 §8의 결정을 승인했다.
   2. S0: 설계 문서와 `.worktreeinclude`를 커밋한다. 커밋하지 않으면 Claude Code worktree에 설계서와 테스트용 상태 파일이 없다(§1-1, §1-2).
   3. S1(I0 Builder, 부록 A1)을 시작한다. 같은 시기에 S1b(미체결 진단, 부록 A4)와 S2(카드 파일럿 #1, 부록 B)를 진행한다.
3. **P3가 넘긴 미결 항목 5개는 "가장 단순한 쪽으로 시작하고, 측정해서 바꾼다"로 정했다(§2, 제안).** 두 명령 유지, 만료 15분 유지, I0-b는 트리거 방식, 미체결 진단은 P3대로 S1과 병행, I4는 S7b 뒤.
4. **P3 설계를 그대로 실행하면 막히는 지점 12개를 찾았다(§1).** 가장 큰 것은 세 가지다.
   - 키움 제안과 적용 라이브러리의 형식이 맞지 않는다. 해시 방식(원시 바이트 vs canonical), 해시 필드 이름, `bundle_id`·`scope`·`proposed_patch`·revision 필드가 모두 다르다. 지금 그대로는 키움 제안을 적용할 수 없다.
   - `CLAUDE.md`와 `AGENTS.md`는 "사용자 확인 **또는** 검증된 조회 스냅샷"이면 상태를 바꿔도 된다고 적고 있다. I0가 생기면 이 문구가 확인 없는 적용의 근거가 될 수 있다. "스냅샷 **그리고** 해당 제안의 사용자 확인"으로 바꾼다.
   - 확인 코드는 제안 파일에 들어 있다. 코드를 읽을 수 있는 에이전트라면 누구든 그 코드를 넣을 수 있다. 코드만으로는 사람이 확인했다는 증명이 되지 않는다. 실제 증거는 사용자 메시지 기록과 규칙이다. 이것이 P3에서 사용자가 받아들인 절충의 실체다.
5. **남는 위험 중 사용자가 알아야 할 것은 세 가지다(§6).**
   - 미체결 확인 없이 적용한다(Judge 10번). S1b 진단 결과를 Judge에 넘긴다.
   - 시장 가격 경로의 `return_code` 누락 허용은 R6까지 남는다.
   - Cowork 채팅 확인은 터미널 확인보다 보증 수준이 낮다.

---

## 1. P3 설계 보완 (P4 작성 중 확인)

| # | 확인한 사실 | 영향 | 조치 |
|---|---|---|---|
| 1-1 | 설계 문서 3개(phase1, P3, 인계)가 git 미추적이다. worktree는 현재 HEAD에서 만들어지고, 미추적 파일은 복사되지 않는다(`.claude/settings.json` `worktree.baseRef: "head"`, 설정 가이드) | Builder와 Judge가 설계서를 읽지 못한다 | **S0**에서 이 문서를 포함한 4개를 커밋한다 |
| 1-2 | 대상 테스트가 git 제외 파일 2개를 저장소 경로에서 직접 읽는다: `stock-strategy-system/portfolio_state.json`, `alert_runtime_state.json`(예: `test_kiwoom_broker_shadow.py:56-57`, `test_manual_portfolio_analysis.py:1756,1807-1827`) | worktree와 Judge 체크아웃에서는 이 테스트가 처음부터 ERROR가 난다. 그러면 "기준선 대비 새 실패 0"이 상태 불변 테스트 없이도 통과한다 | S0에서 두 파일을 적은 `.worktreeinclude`를 커밋한다. 설정 가이드에 따르면 git 제외 파일 중 여기 적힌 것만 worktree로 복사된다. 복사되지 않으면 원본에서 복사한다(원본은 읽기만) |
| 1-3 | Builder의 커밋 안 된 변경은 Judge worktree에 없다 | Judge가 무엇을 검증할지 정해지지 않았다 | Builder가 worktree 브랜치에 커밋한다(사용자 승인). Judge는 그 커밋을 분리 체크아웃하고, 기준선(merge-base)도 직접 돌려 비교한다 |
| 1-4 | 키움 제안: `file_hash`(원시 바이트)를 `expected_before_hash`에 넣고, `current_state_revision`·`changes`·`verified_scope`를 쓴다(`run_kiwoom_broker_shadow.py:30,37`, `kiwoom_broker_shadow.py:114-122`). 적용: `canonical_hash(state)`를 `expected_portfolio_hash_before`와 비교하고, `bundle_id`·`scope`·`proposed_patch`·`expected_state_revision`을 쓴다(`apply_user_confirmed_broker_snapshot.py:48,51,53,55,63,76-86`) | 키움 제안은 그대로 적용되지 않는다. 8/14에 스크린샷(2.5) 형식의 별도 제안 파일을 만든 이유로 보인다 | 새 제안 스키마에서 필드 이름과 canonical 해시로 통일한다. canonical 해시는 줄바꿈과 무관하므로 Windows 제안 → Linux VM 적용에도 맞는다 |
| 1-5 | 적용 함수는 텍스트 모드로 쓴다(`:27`). Windows에서는 CRLF, Linux VM에서는 LF가 된다 | 적용한 곳에 따라 상태 파일 줄바꿈이 바뀐다. canonical 해시를 쓰면 판정에는 영향이 없다 | Builder가 줄바꿈 방침을 정한다. 상태 파일을 원시 바이트 해시로 비교하는 다른 코드가 있는지 찾아 보고한다 |
| 1-6 | 확인 코드 검사는 P3에서 적용 명령(CLI)에만 있다(P3 §4-4). 라이브러리를 직접 부르면 코드 없이 적용된다 | 8/14 같은 직접 호출에서 코드 검사가 빠진다 | (제안) 라이브러리에도 `confirm_code` 일치 검사를 넣는다. 다만 코드는 제안 파일에 있으므로 이 검사는 **실수 방지용**이다. 최종 방어는 규칙, 권한 거부, 확인 기록이다(§8-3) |
| 1-7 | `CLAUDE.md` Hard safety와 `AGENTS.md:35`: "explicit user confirmation **or** a verified read-only broker snapshot" | I0 뒤에는 "조회 스냅샷이 있으니 확인 없이 적용해도 된다"로 읽힐 수 있다. P3 §2는 사람의 명시적 확인만 허용한다 | 문구를 "검증된 조회 스냅샷 **그리고** 해당 제안에 대한 사용자의 명시적 확인"으로 바꾼다(I0 범위, Judge 14번) |
| 1-8 | Cowork에도 연결 폴더의 `CLAUDE.md` 사본이 전달된다(이 작업 2번째 턴에 시스템 알림으로 들어온 것을 확인). 다만 세션 시작 시점의 사본이다. `AGENTS.md`는 전달되지 않는다 | P3 §2 네 겹 중 ③(에이전트 규칙)은 Cowork에서도 작동한다. 하지만 I0의 문구 변경은 새 작업부터 반영되고, `AGENTS.md` 규칙은 빠진다 | 적용 절차를 `references/broker-snapshot-reconciliation.md`에 넣고, Cowork는 "조정 확인" 요청 때 이 문서를 먼저 읽는다. 같은 규칙을 프로젝트 메모리에도 저장한다(§8-4) |
| 1-9 | worktree에서 만든 실데이터 제안 파일에는 보유·현금 값이 들어간다 | worktree 안 임시 폴더에 두면 커밋에 섞일 수 있다 | 출력은 git 제외 폴더 `workspace/outputs/reconciliation/`에만 쓴다. 커밋 전에 `git status`로 확인한다 |
| 1-10 | VM에서 git 커밋을 하면 잠금·임시 파일(`.git/index.lock`, `tmp_obj_*` 등)이 남는다. VM은 삭제 권한이 없으면 이 파일을 지우지 못한다(`kiwoom-acceptance-pin-diagnosis` 진행 기록) | S0 커밋과 S4 병합을 Cowork에서 하면 정리 작업이 생긴다 | **커밋과 병합은 사용자가 Windows 터미널에서** 명령을 붙여 넣어 실행한다. Cowork는 결과를 읽기 전용으로 확인한다 |
| 1-11 | 적용 명령은 Cowork VM에서 돈다. Claude Code Builder·Judge는 VM에 접근할 수 없다 | VM에서 도는지 아무도 확인하지 않은 채 첫 실제 적용을 하게 된다 | S4에서 첫 적용 전에 Cowork가 VM 사전 확인을 한다: 신규 테스트 실행, 시스템 임시 폴더의 상태 복사본에 적용 1회 |
| 1-12 | P3에 되돌리기 절차가 없다(백업만 있음). "백업을 복사한다"는 라이브러리 검사·revision·원장을 모두 건너뛰는 두 번째 쓰기 경로가 된다 | 복원 방법과 "손상"의 정의가 없다 | v1은 복원 명령을 만들지 않는다. 값이 잘못 적용되면 **새 제안으로 다시 조정**한다(브로커가 기준). 손상(JSON 파싱 실패, 또는 canonical 해시가 원장 마지막 줄의 적용 후 해시와 다름)이 생기면 적용을 멈추고 복원 절차를 따로 설계한다(K3, §5). 백업은 보존한다 |

P3 §12 확인 필요 중 3개는 풀렸고 1개는 일부만 풀렸다.

- **Cowork VM의 Python:** 3.10.12다. 저장소 스키마 검증은 표준 라이브러리로 직접 구현돼 있다(`validation_common.validate_instance`). 실제 동작은 S4 VM 사전 확인에서 본다.
- **SPY:** 키움 수용 범위 15종목(`kiwoom-session-aware-priority-policy.json`: AAPL, BE, CME, FSLY, IBM, JPM, MRVL, MVLL, NBIS, NOW, PGR, SOXL, SOXX, TOST, V)에 없다. v1 채점에서 SPY 가격에는 "reference only" 라벨을 붙인다.
- **기존 sidecar 원장:** git 추적 대상이다(`workspace/state/continuous_improvement/` 12개 파일). 결정 원장을 git 제외 경로에 따로 두는 P3 안이 맞다.
- **`return_code`(일부):** 스펙 ust21070의 응답 예시에는 `"return_code": 0`이 있다. 그러나 응답 필드 표에는 없다. 미체결 조회가 매번 `KIWOOM_API_RESPONSE_ERROR`로 분류된 것은 `return_code`가 0이 아니어야 나는 경로다(`kiwoom_account_readonly_bridge.py:99`). 오류 응답에 필드가 있다는 간접 근거다. 정상 응답 확인은 S1 2단계에서 한다.
- **파생 원가 교차검증:** 허용목록(`SAFE_FIELDS`, `kiwoom_account_readonly_bridge.py:43-46`)에 `evlt_amt`와 `pl_amt`가 있으므로 `evlt_amt − pl_amt`로 할 수 있다. `frgn_stk_book_amt`(매입금액)는 허용목록 밖이다. 쓰려면 허용목록 변경(K3)이 필요하므로 v1에서는 쓰지 않는다.

---

## 2. P3에서 넘어온 미결 항목 결정안 (제안)

| 항목 | P3 위치 | 결정안 | 이유 | 다시 볼 조건 |
|---|---|---|---|---|
| 분석과 제안을 한 명령으로 묶을지 | §4-1 2단계 | **v1은 두 명령.** 사용법 문서에 두 줄을 한 번에 붙여 넣는 블록을 준다 | `run_manual`은 고정 파일이다. 묶음 스크립트를 새로 만들면 I0 Judge 범위가 커진다 | 첫 4회 사용 중 2회 이상 "번거로움" 보고. 그때 묶음 스크립트(K1, 고정 파일 수정 없음) |
| 제안 만료 15분 | §4-1 | **유지(정책값 900초).** 만료되면 제안 명령만 다시 실행한다 | 바꾸면 정책 변경(K3)이다. 다시 실행하는 비용은 명령 한 줄이다 | 첫 4회 중 2회 이상 만료 |
| I0-b 체결 확인 경로 | §4-3 | **트리거 방식.** 필요할 때 설계하고 만든다(K3) | 지금까지 수량이 달랐던 종목은 timing_plan 밖의 NBIS뿐이다. 그 전까지는 알림 엔진의 `STATE_MISMATCH`가 정확한 신호다 | 제안 표에 `TIMING_PLAN_TICKER_CHANGED` 또는 `POLICY_POSITIONS_MISMATCH` 경고가 뜸(S4 분기 참조) |
| 미체결 조회(ust21050) 진단 | §4-2, §11-4 | **S1과 병행(S1b), S3 전에 끝낸다.** K2, 코드 수정 없음 | P3 §4-2가 병행을 정했다. Judge 10번(미체결 확인 없이 적용)의 판단 근거가 된다 | 진단이 길어지면 Judge는 진단 없이 진행하고 결과를 §9에 추가 |
| I4(R6~R9) 시점 | §8-3 | **S7b 뒤** | 목표 우선순위가 판단 품질 > 운영 부담 > 단순화다. I1·I2·I7은 고정 파일 밖에서 만든다 | ① I1·I2가 고정 파일 수정을 요구 ② CI 실패 17건이 새 작업 검증을 가림 ③ 데이터 정확성 결함이 실제 판단을 틀리게 함 |

P3가 "파일럿 뒤" 또는 "코드화 때"로 미룬 것은 G3에서 정한다: dashboard 운영 여부, baseline 대체 여부, 카드 행동 → sidecar `DECISION_ACTIONS` 대응표, 결정 원장 경로.

---

## 3. 전체 순서와 게이트

```
S0 문서·.worktreeinclude 커밋 ─┬─► S1  I0 Builder (Claude Code) ─┐
          [G0]                 ├─► S1b 미체결 진단 (Claude Code) ─┴─► S3 I0 Judge ─► [G1] ─► S4 병합·VM 확인·첫 조정 ─► [G2] ─┐
                               └─► S2  카드 파일럿 #1 (Cowork) ──────────────────────────────────────────────────────────┤
  ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
  ├─► S5 카드 파일럿 #2 ─► [G3] ─┐
  └─► S6 I7 상태 점검·H1 ────────┴─► S7a I1 카드 코드화 ─► S7b I2 원장·채점 ─► S8 I4 R6~R9 ─► [G4]
대기(트리거): I0-b, 복원 절차, H2, 묶음 명령, 만료 조정, SPY 범위, I8, SAVE 입력 3건, 시장 레짐 연구, 신규매수 RS·ATR (§5)
```

| 단계 | 내용 | 작업 위치 | 모델 · 추론 노력 | K | 선행 |
|---|---|---|---|---|---|
| S0 | 설계 문서·`.worktreeinclude` 커밋 | Windows 터미널(사용자) + Cowork 확인 | 이 작업 | K0 | G0 |
| S1 | I0 조정 루프 빌드 | Claude Code, 새 worktree `i0-reconcile` | Opus · xhigh | K3 | S0 |
| S1b | 미체결 조회 진단 | Claude Code, 원본 폴더 새 세션 | Sonnet · high | K2(읽기 전용) | S0 |
| S2 | 카드 파일럿 #1 | Cowork 새 작업 | Sonnet · high | 없음 | S0 |
| S3 | I0 Independent Judge | Claude Code, 새 worktree `judge-i0` | Opus · xhigh | K3 | S1 커밋, S1b 결과 |
| S4 | 병합, VM 사전 확인, 첫 실제 조정 | Windows 터미널 + Cowork 새 작업 | Opus · xhigh(첫 회), 이후 Sonnet · medium | K3 결과 적용 | G1 |
| S5 | 카드 파일럿 #2, G3 판정 | Cowork 새 작업 | Sonnet · high | 없음 | G2 |
| S6 | I7 상태 점검, H1 알림 한 줄 | Claude Code(I7) + Cowork(H1) | Sonnet · high / H1 Sonnet · medium | K1~K2 | G2 |
| S7a | I1 카드 코드화 | Claude Code, 새 worktree `card-v1` | Sonnet · high | K2 | G3, S6 병합 |
| S7b | I2 결정 원장·채점기 | Claude Code, 새 worktree `journal-v1` | Sonnet · high | K2 | S7a 병합 |
| S8 | I4 거버넌스 재설계(R6~R9) | Claude Code, 새 worktree `gov-r6` + Judge | Opus · xhigh | K3 | S7b 병합, 또는 §2 트리거 |

**공통 규칙**

- 모델·추론 노력은 설정 가이드 표를 따른다: 포트폴리오 분석·개발 = Sonnet · high, 여러 파일 설계·K3·Judge = Opus · xhigh.
- **병합 규칙(모든 Builder 브랜치):**
  1. Builder가 worktree 브랜치에 커밋한다(사용자 승인).
  2. 검증한다. K2는 대상 테스트, K3는 Judge PASS다.
  3. 브랜치 끝 커밋이 검증된 커밋 ID와 같은지 확인한다.
  4. 사용자가 Windows 터미널에서 `git merge --no-ff <커밋 ID>`를 실행한다.
  5. Cowork가 결과를 읽기 전용으로 확인하고 §9에 기록한다.
  - 다음 단계 worktree는 병합 뒤에 만든다(`baseRef: head`).
- 단계가 끝나면 새 작업(또는 새 Claude Code 세션)으로 넘어간다. 결과는 §9에 한 줄씩 남긴다.
- 전 기간 금지: 키움 주문 도구, 체결 추론, 테스트 약화. **S8 전까지** 금지: 거버넌스 확장(새 해시 고정·새 acceptance 라벨), 고정 파일 16개 수정.

---

## 4. 단계별 계획

### S0. 설계 문서와 `.worktreeinclude` 커밋 (K0)

- **이유:** §1-1, §1-2.
- **시점:** §8 결정을 §9에 기록한 뒤.
- **할 일**
  1. Cowork가 저장소 루트에 `.worktreeinclude`를 만든다. 내용은 두 줄이다: `stock-strategy-system/portfolio_state.json`, `stock-strategy-system/alert_runtime_state.json`.
  2. 사용자가 Windows 터미널(저장소 폴더)에서 붙여 넣는다. push는 하지 않는다.

```
git add .worktreeinclude docs/claude/handover-system-review-2026-09-30.md docs/claude/system-review-phase1-2026-09-30.md docs/claude/system-review-p3-design-2026-09-30.md docs/claude/system-review-p4-roadmap-2026-09-30.md
git commit -m "docs(claude): system review phase1, P3 design, P4 roadmap; add .worktreeinclude"
```

  3. Cowork가 `git status`와 `git log -1`을 읽기 전용으로 확인한다.
- **완료:** 다섯 파일이 커밋에 들어 있고, staged에 다른 파일이 없다.
- **중단:** staged 목록에 다른 파일이 섞이면 커밋하지 않는다(`git restore --staged <파일>`).

### S1. I0 조정 루프 빌드 (K3)

- **설계:** P3 §4 전체와 이 문서 §1-2~1-12.
- **사용자 조작**
  1. Windows 터미널에서 `cd "E:\사업\##금동한\코덱스저장소"`를 입력한다.
  2. `claude --worktree i0-reconcile`을 입력한다.
  3. 세션 안에서 `/model`로 Opus, `/effort`로 xhigh를 고른다.
  4. 부록 A1을 붙여 넣는다.
  5. Builder가 `return_code` 확인용 조회 승인, 계획 승인, 커밋 승인을 차례로 요청한다. 각각 읽고 승인한다. 멈춤 보고가 오면 Cowork로 가져와 함께 판단한다.
- **완료**
  - worktree 기준선 대비 대상 테스트(부록 A1 1단계 목록)의 새 실패가 0이다. 신규 `test_reconcile_broker_state.py`가 통과한다.
  - 전체 테스트 1회(서브에이전트)에서 worktree 기준선 대비 새 실패가 0이다.
  - 기존 테스트를 바꿨다면 "이전 기대 → 새 기대" 표가 보고서에 있다.
  - `validate_schema_contracts.py`가 PASS다.
  - 고정 파일 16개와 정책 파일의 diff가 비어 있다.
  - 실데이터 제안 1회: 필수 조회 3개 PASS, 제안 스키마 PASS, 상태 파일 sha256 전후 동일.
  - 보고서 `docs/claude/i0-builder-report-<날짜>.md`가 있고, 보유 수량·현금 수치가 없다.
  - worktree 브랜치 `worktree-i0-reconcile`에 커밋됐다.
- **중단(멈추고 보고)**
  - 정상 계좌 응답에 `return_code`가 없다.
  - 고정 파일이나 정책 파일을 고쳐야만 한다.
  - `normalize_snapshot` 계약을 바꿔야만 한다.
  - 실데이터 제안을 3회 시도해도 필수 조회 3개가 한 번도 모두 PASS하지 않는다.
  - 적용 명령이 코드 없음·코드 불일치·다른 제안 코드에서 적용된다. 또는 라이브러리가 unresolved·만료·해시·revision 불일치 제안을 적용한다. 그리고 이를 막을 수 없다.
  - 기존 테스트의 기대를 약하게 바꿔야만 통과한다.

### S1b. 미체결 조회 진단 (K2, 읽기 전용, S1과 병행)

- **사용자 조작:** 새 Windows 터미널에서 저장소 폴더로 이동 → `claude` → `/model` Sonnet, `/effort` high → 부록 A4. 조회 전용 호출을 할 때 승인을 요청하면 확인하고 승인한다.
- **산출:** `docs/claude/open-orders-diagnosis-<날짜>.md`. 원인(확정·추정), 근거, 수정안과 그 K 등급·고정 파일 여부.
- **완료:** 원인을 특정하거나, "키움 측 문제로 추정"과 근거를 남긴다. 결과를 S3 Judge에 넘긴다.
- **중단:** 원인 확인에 주문 API나 주문 도구가 필요하면 즉시 멈춘다.
- **수정은 이 단계에서 하지 않는다.** 수정안이 나오면 K 등급에 따라 별도 단계로 잡는다(§9에 기록).

### S2. 카드 파일럿 #1 (코드 없음, S1과 병행)

- **사용자 조작**
  1. Windows 터미널에서 평소처럼 수동 분석을 한 번 실행한다.
  2. Cowork에서 새 작업을 만들고 모델을 Sonnet · high로 둔다.
  3. 부록 B의 S2 첫 메시지를 보낸다.
  4. 카드를 읽고 평가한다: 판단에 씀 / 참고만 / 안 씀, 고칠 점.
- **Cowork 할 일(P3 §5-1~5-3)**
  - 입력: 오늘 수동 분석 JSON, 상태 파일, baseline(`workspace/research/holding-baselines/`), 공식 출처 이벤트.
  - 출력: `workspace/outputs/holding-cards/<날짜>/`에 머리말 1개와 카드 3장. 커밋하지 않는다.
  - 수량은 분석 JSON의 브로커 관측값을 쓰고 "상태 파일 미조정" 라벨을 붙인다.
  - 판단 규칙: 결정론 규칙 결과를 먼저 싣는다. 반대 판단에는 "규칙과 다름: 이유"를 붙인다. 판단 보류는 브로커 조회 UNAVAILABLE, 종목 identity 미검증 두 경우만 허용한다.
  - **멈춤 가드:** 분석 JSON의 보유 목록이 비었는데 상태가 `AVAILABLE`이면 카드를 쓰지 않는다(P3 §0-7의 셋째 결함). 분석 JSON이 오늘 것이 아니면 수동 분석을 다시 요청한다.
- **알아 둘 점:** 파일럿 #1은 상태가 미조정이라 확신도가 모두 "낮음"으로 묶인다(P3 §5-1 상한 규칙). 평가할 때 감안하고, 상한이 풀린 모습은 #2에서 본다.
- **완료:** 카드 3장과 머리말, 사용자 평가가 §9에 기록된다.

### S3. I0 Independent Judge (K3)

- **사용자 조작**
  1. 새 Windows 터미널에서 `cd "E:\사업\##금동한\코덱스저장소"`를 입력한다.
  2. `claude --worktree judge-i0`를 입력한다.
  3. `/model`로 Opus, `/effort`로 xhigh를 고른다.
  4. 부록 A2를 붙여 넣는다. S1b 진단 문서가 있으면 경로를 함께 알려 준다.
  5. Judge 출력을 Cowork에 붙여 넣는다(§9에 요약 기록).
- **Judge 방식:** 파일을 고치지 않는다. 기준선(merge-base)과 Builder 커밋을 각각 분리 체크아웃해 직접 테스트를 돌려 비교한다. Builder의 자기 보고에 기대지 않는다.
- **판정 항목:** P3 §4-6의 1~10에 아래 5개를 더한다.
  11. 제안 파일 안의 경로가 저장소 상대경로라서, Windows에서 만든 제안을 VM에서 적용할 수 있다.
  12. 제안과 적용이 canonical 해시와 같은 필드 이름으로 통일됐다(§1-4, §1-5).
  13. 커밋된 파일(보고서 포함)에 보유 수량, 현금, 계좌 정보가 없다.
  14. 규칙 문구가 모두 갖춰졌다.
      - `CLAUDE.md`·`AGENTS.md`의 상태 변경 조건이 "스냅샷 그리고 해당 제안의 사용자 확인"이다(§1-7).
      - Cowork 절차 문서에 다음이 적혀 있다: 이번 대화에서 사용자가 "확인 <코드>"를 직접 보냈을 때만 적용한다, 코드를 Claude가 넣지 않는다, 이전 확인을 재사용하지 않는다.
  15. 기존 테스트를 바꿨다면 그 변경이 기대를 약하게 만들지 않았다.
- **FAIL일 때:** Judge 출력을 S1 Builder 세션에 붙여 넣어 최소 수정 → 새 커밋(승인) → 같은 Judge 세션에서 새 커밋으로 다시 확인한다.
- **완료(G1 조건 1):** 최종 PASS와 그 커밋 ID. 10번에 Judge가 반대하면 사용자 결정까지 G1을 보류한다.
- **중단:** 같은 항목이 2회 FAIL하면 Cowork(Opus · xhigh)에서 설계를 다시 본다.

### S4. 병합, VM 사전 확인, 첫 실제 조정

- **선행:** G1 = Judge PASS(커밋 ID) + 사용자 승인. Cowork 새 작업은 Opus · xhigh로 연다(첫 회).
- **4-1. 병합**
  1. Cowork가 `worktree-i0-reconcile` 브랜치 끝 커밋이 Judge PASS 커밋 ID와 같은지 확인한다. 다르면 멈춘다.
  2. 사용자가 Windows 터미널(원본 폴더)에서 `git merge --no-ff <PASS 커밋 ID>`를 실행한다.
  3. Cowork가 읽기 전용으로 확인한다: 바뀐 파일 목록이 Builder 커밋과 같다. 고정 파일 16개는 그대로다. `git status`에 기존 미추적 폴더 외 새 변경이 없다.
- **4-2. VM 사전 확인(Cowork)**
  - VM에서 `test_reconcile_broker_state.py`를 실행한다.
  - 시스템 임시 폴더에 상태 파일 복사본을 두고 적용을 1회 해 본다. 원본 상태 파일은 건드리지 않는다.
  - 둘 다 통과해야 4-4로 간다. 실패하면 Windows 터미널 적용(`--confirmed-via USER_TERMINAL`, P3 대체 경로)으로 바꿀지 사용자와 정한다.
- **4-3. Cowork 규칙 준비:** Cowork는 조정 확인 요청을 받으면 먼저 `references/broker-snapshot-reconciliation.md`를 읽는다. §8-4를 승인받았으면 같은 규칙을 프로젝트 메모리에 저장한다.
- **4-4. 첫 조정(사용자 조작)**
  1. Windows 터미널에서 사용법 문서의 두 줄 블록(수동 분석 + 제안)을 붙여 넣는다.
  2. "조정 필요 없음"이 나오면 끝이다. "Cowork에서 확인하세요"가 나오면 다음으로 간다.
  3. Cowork에서 "조정 확인해줘"를 보낸다.
  4. Claude가 보여 주는 차이 표를 확인한다. 적용하려면 "확인 <코드>", 아니면 "취소"를 보낸다.
  5. Claude가 적용하고 revision과 백업 경로를 한 줄로 알려 준다.
  6. 수동 분석을 다시 돌려 `broker_diff_status=MATCH`를 확인하고 Cowork에 알려 준다.
- **경고 분기:** 제안 표에 `TIMING_PLAN_TICKER_CHANGED`·`POLICY_POSITIONS_MISMATCH` 경고나 "적용 후 알림 엔진 검사 실패"가 뜨면 Claude는 적용하기 전에 알린다. 사용자는 둘 중 하나를 고른다.
  - 적용한다: P3 §4-3 기본값이다. 알림 엔진이 I0-b 전까지 `STATE_MISMATCH`로 멈추는 것을 감수한다.
  - 보류한다: I0-b를 먼저 한다(§5).
- **완료(G2):** MATCH, 원장 1건, 백업 1건(P3 §4-7). NBIS 수량만 다른 경우 "적용 후 알림 엔진 검사"는 통과가 예상된다.
- **중단**
  - 코드 불일치가 아닌 이유로 적용이 거부되면 상태 파일을 건드리지 않고 원인을 진단한다.
  - 상태 파일 손상(§1-12 정의)이 보이면 모든 적용을 멈추고 백업을 보존한다.
  - 필수 조회가 3회 연속 실패하면 적용을 멈추고 진단한다.
- **이후:** 분석할 때마다 4-4의 1~6을 반복한다. 모델은 Sonnet · medium이면 된다.

### S5. 카드 파일럿 #2와 G3 판정

- **할 일:** 조정된 상태로 S2를 반복한다. "상태 파일 미조정" 라벨과 확신도 상한이 풀리고, "지난 카드 대비 변화" 칸이 처음 채워진다.
- **시장 환경 메모(선택, 2026-09-30 추가, 근거: `trading-skill-materials-review-2026-09-30.md` §7~8)**
  - 입력: 카드를 쓰는 날에만 사용자가 SAVE(saveticker.com) "장 전 주요 뉴스" 글 텍스트를 붙여 넣거나 SAVE Daily PDF 경로를 준다. 매일 받지 않는다.
  - PDF면 VM에서 기존 `save_daily_pipeline.py --source <PDF>`를 돌리고, 텍스트면 Cowork가 직접 읽는다. `MARKET_VOLATILITY`·`BANK_CREDIT`·`FED`·`MACRO` 성격의 항목만 고른다.
  - 머리말에 1~2줄로 적는다: 시장 관련 상위 이벤트 1~3건, 48시간 안 일정(공식 일정으로 확인 못 하면 "일정 확인 필요"). 라벨 `EXTERNAL_REFERENCE / 판단 규칙 아님`.
  - **입력이 없으면** "시장 환경: SAVE 미입수"로 적고 카드는 그대로 쓴다. 카드 작성을 막지 않는다.
  - 메모는 종목 판단을 자동으로 바꾸지 않는다. 메모 때문에 판단을 바꿨다면 원문을 확인하고 이유를 적는다. 수치는 공식 통계·키움으로 확인한 것만 쓴다.
  - 하지 않는 것: saveticker.com 자동 조회, 비공개 API 호출, 제3자 수집 확장 설치(검토 문서 §8).
- **G2가 늦어질 때:** S1 시작 뒤 2주가 지나도 G2가 안 되면, 파일럿 #2를 "미조정" 라벨로 먼저 진행하고 G3 판정은 G2 뒤로 미룬다(제안).
- **G3 판정(Cowork)**
  - **통과:** 2회 중 "판단에 씀"이 1회 이상이면 S7a로 간다. 이때 함께 정한다.
    - 카드 형식 확정
    - dashboard를 카드 경로에서 뺄지(P3 권장: a′ 별도 스키마, dashboard 미사용)
    - baseline을 카드가 대체할지(REMOVE 후보)
    - 카드 행동 → sidecar `DECISION_ACTIONS` 대응표
    - 결정 원장 경로(P3 제안: `stock-strategy-system/decision_journal.json`)
  - **함께 기록(통과·미달 공통):** 시장 환경 메모가 판단에 쓰였는가(판단에 씀 / 참고만 / 안 씀), SAVE 미입수 횟수. 메모를 카드 형식에 남길지 여기서 정한다.
  - **미달:** 0/2면 코드화를 보류한다. 원인을 형식, 판단 내용, 데이터로 나눠 정리하고 형식을 고쳐 파일럿 #3을 한다. #3에서도 "판단에 씀"이 없으면 I1 방향을 다시 본다(예: 판단 작성을 Chat 깊은 분석으로 옮김).

### S6. I7 상태 점검과 H1 알림 한 줄 (S5와 병행)

- **I7(K1~K2, 부록 A3)**
  - Claude Code 새 worktree `status-view`, Sonnet · high.
  - 내용: `portfolio_status.py` 읽기 전용 명령(P3 §7). 출력은 `workspace/outputs/status/latest.json`(git 제외)과 한 줄 요약.
  - 완료: 대상 테스트 PASS. 원본 폴더 데이터로 한 번 실행한 결과가 Cowork 수동 확인(상태 나이, 최근 분석 diff, 최근 조정)과 같다. `run_manual`은 그대로다. §3 병합 규칙으로 병합한다.
  - 중단: 고정 파일 수정이 필요한 항목이 나오면 그 항목만 빼고 진행한다.
- **H1(K1)**
  - 선행: I7 병합, 원본 폴더에서 `portfolio_status.py` 1회 실행.
  - Cowork, Sonnet · medium.
  - v1 전달 방법: 분석·조정 세션이 끝날 때 Cowork가 `latest.json`을 읽어 현황판에 반영한다. 예약 작업이 장치 파일을 읽는 방식은 확인 필요라 v1에서 쓰지 않는다.
  - 현황판에는 이미 예약 작업이 쓰는 데이터가 있다. 먼저 현황판을 읽고 기존 표시를 깨지 않게 넣는다. 현황판 db는 표시 전용 원칙을 유지한다.
  - 완료: 현황판 보유 표 위에 "상태 기준 … · 브로커 … · 마지막 카드 …" 한 줄이 보인다.

### S7a. I1 카드 코드화 (K2)

- **선행:** G3 통과와 그때 정한 형식, S6 I7 병합(P3 B1 순서: I7/H1 → I1 코드화).
- **내용(부록 A5):** P3 §5-4의 a′ 별도 카드 스키마, 결정론 fact pack 생성기, 카드 검증기, md 렌더러. 모두 고정 파일 밖에 만든다.
- **완료**
  - 검증기가 다음 7가지를 모두 거부한다: 수량·주문 필드, 판단 공란, 허용 외 판단 보류, 규칙과 반대인데 라벨 없는 판단, 확신도 상한 위반, fact pack과 다른 숫자, run_id·as_of 불일치.
  - fact pack 생성기가 "빈 보유 + AVAILABLE"에서 실패한다.
  - dashboard가 카드를 plan으로 받지 않는다는 거부 테스트가 있다(dashboard는 수정하지 않음).
  - Cowork에서 실제 분석으로 카드를 한 번 만든다. 사용자 평가가 "안 씀"이면 S7b로 가지 않고 형식을 먼저 고친다.
  - §3 병합 규칙으로 병합한다.
- **중단:** dashboard·renderer 등 기존 판단 부품을 고쳐야만 하면 멈추고 보고한다.

### S7b. I2 결정 원장과 채점기 (K2)

- **선행:** S7a 병합.
- **내용(부록 A6):** P3 §6-2. sidecar는 추가만 한다(`run_manual`이 import).
- **완료**
  - 카드를 확정하면 종목별 원장 1건이 추가되고, 해시 체인 검증이 통과한다.
  - 채점기가 "대기(남은 세션 수)"를 정확히 보여 준다. SPY 가격에는 "reference only" 라벨이 붙는다.
  - `test_manual_portfolio_analysis.py` 결과가 기준선과 같다.
  - 원장 경로의 git 제외 테스트가 있다.
  - §3 병합 규칙으로 병합한다.
- **중단:** sidecar 기존 함수의 동작을 바꿔야만 하면 추가 전용 대안을 보고하고 멈춘다.
- **첫 20세션 채점 결과:** 첫 원장 기록 뒤 약 4주.

### S8. I4 거버넌스 재설계 R6~R9 (K3)

- **선행:** S7b 병합, 또는 §2의 I4 트리거.
- **착수 전:** Cowork(Opus · xhigh)에서 부록 A7·A8을 S1~S7 결과에 맞게 갱신한다.
- **R6 Builder(부록 A7):** 새 worktree `gov-r6`, BOUNDARY_RESET_REQUIRED. P3 §8-3 ①~⑧.
  - 첫 단계: worktree에서 원시 해시 테스트를 판정할 수 있는지 확인한다. 2026-09-29 진단 때는 불가해서 원본 폴더에서 진행했다. 불가하면 멈추고 진행 위치를 사용자에게 묻는다.
- **R7:** manifest 후보 1회 생성, 후보 검증기 PASS, 전체 테스트(서브에이전트)에서 acceptance 관련 17건 해소.
- **R8 Judge(부록 A8):** 새 worktree `judge-r8`. 기존 8단계 범위 + "고정 범위 축소가 권한·정확성·상태 쓰기 보호를 약화하지 않았는가" + I0 테스트 재실행.
- **R9:** 사용자 승인 뒤 활성화한다. 범위는 P3대로 기존 15종목이다(SPY 추가는 §5 대기 항목).
- **완료(G4):** R8 PASS, 사용자 승인, 활성화 뒤 전체 테스트에서 acceptance 관련 실패 0, `CLAUDE.md` Change classes 문구 갱신.
- **중단:** 보호 기능을 옮기다 기존 테스트 기대값을 바꿔야 하면 멈춘다(테스트 약화 금지). R8이 2회 FAIL하면 설계를 다시 본다.

---

## 5. 대기 항목 (트리거가 생기면 착수)

| 항목 | K | 트리거 | 할 일 |
|---|---|---|---|
| I0-b 체결 확인 경로, 정책 종목 갱신 | K3 | 제안 표에 `TIMING_PLAN_TICKER_CHANGED` 또는 `POLICY_POSITIONS_MISMATCH` 경고 | Cowork 설계(Opus · xhigh) → Builder → Judge |
| 상태 파일 복원 절차 | K3 | 손상 발생(§1-12 정의) | 원장 기록·revision 규칙을 포함해 설계. 그때까지 적용 중지, 백업 보존 |
| H2 현황판 카드 요약 행 | K1 | S7a 병합 | Cowork |
| 분석 + 제안 묶음 명령 | K1 | 첫 4회 중 2회 이상 "번거로움"(§2) | Claude Code, 고정 파일 수정 없음 |
| 제안 만료 시간 조정 | K3 | 첫 4회 중 2회 이상 만료(§2) | 정책 변경, 사용자 승인 |
| SPY를 키움 수용 범위에 추가 | K3 | G4 뒤, 채점 가격을 등급 B로 올릴 필요가 생길 때 | 새 acceptance 증거가 필요한 범위 확장 |
| 미체결·실현손익 "내역 없음" 처리 | 안 A K2 → 안 B K3 | 안 A: I0 병합(G2) 뒤. 안 B: 안 A로 "없음 선언" 빈도를 몇 회 모은 뒤 | 안 A는 `return_code`·메시지 관측만 추가(게이트 불변). 안 B는 좁은 조건의 "없음"을 빈 PASS로 인정해 `OPEN_ORDERS_UNVERIFIED`를 없앤다. 미체결 `VERIFIED_NONE`이 주문 의도 차단 해제 근거라 K3, Judge 필요(S1b §5) |
| `SKILL.md:130` 문구 정렬("또는" → "그리고") | K3 | Codex 자동화 재개 전, 또는 S8 | `alert_policy.json` 배포 게이트의 skill 해시 재고정과 설치 사본(`~/.codex/skills`) 갱신. 사용자 승인. 그 전까지는 `CLAUDE.md`·`AGENTS.md`·절차 문서가 우선 |
| 예약 런타임 manifest의 `portfolio_hash` 고정 | K2~K3 | 예약 자동화 재개 전 | `runtime_contract_suite.py:113`이 상태 파일 원시 해시를 배포 manifest와 비교한다. 적용할 때마다 값이 바뀌므로 재설계가 필요하다. 지금 예약 자동화는 PAUSED이고 테스트는 순수 함수만 쓴다 |
| 스크린샷(2.5) 경로 제거(REMOVE) | K2~K3(적용 라이브러리를 건드리므로 Judge 권장) | S4(G2) 뒤, I8 은퇴 작업과 묶어서 | 사용자 결정으로 쓰지 않는 경로다. v1은 F1로 적용만 막았다. 스크린샷 전용 코드·스키마·테스트를 걷어낸다. 정확한 범위는 착수 때 확인한다 |
| I0 선택 보강(Judge 2차 권고 ①②) | K3 | 다음 I0 관련 변경 때 함께 | ① 해시 필드 없는 원장 줄을 `chain_ok=False`로 본다(원장 파일을 직접 위조해야 가능한 우회) ② `expires_at`을 "가장 이른 필수 조회 시각 + 최대 나이"로 다시 계산하고 최대 나이를 정책값 900초 이하로 제한한다(재해시 위조는 받아들인 절충) |
| Judge 결과를 파일로 남기기 | K1(규칙 변경) | 결과 복사·붙여넣기 부담이 계속될 때 | 지금은 Cowork가 Claude Code 세션에 직접 요청하거나 결과를 읽을 방법이 없다(2026-09-30 확인: 연결 가능한 세션 없음). Judge가 git 제외 폴더에 판정 파일 1개만 쓰도록 허용하면 Cowork가 직접 읽을 수 있다. `CLAUDE.md`의 "Judge never edits files" 조정이 필요하다 |
| `METADATA_ONLY` 확인 부담과 `holding_change_reconciliations` 누적 | K2 | 첫 4회 사용 뒤 | 거의 매 분석일 확인이 필요하다(S3 16번). 값 변화 없는 적용은 원장에만 남길지 정한다 |
| `unreconciled_holding_changes` 정리 규칙 | K2 | 첫 조정 뒤 | 조정 뒤 이 목록을 비울지 정한다 |
| I8 `validate_decision_record.py`·`evaluate_outcome.py` 은퇴 | K2 | S7b 뒤 30일간 사용 없음 | P6 월간 점검에서 판정 |
| Windows 전용 테스트 실패 6건(PowerShell 5, pypdf 1) | K2 | 새 작업 검증을 가릴 때 | `docs/claude/test-run-latest.md` 참조 |
| 옛 worktree `k2-pin-safe-fixes` 정리 | 없음 | 언제든 | 1단계 변경은 원본 폴더로 옮겨 커밋됐다(`4db8c51`). worktree는 `locked` 상태라 삭제 전 unlock이 필요하다. 삭제는 사용자 승인 |
| SAVE 규칙 파일 보유 목록 정리 | K1 | SAVE Daily PDF를 파이프라인으로 처음 돌리기 전, 또는 HOLDINGS IMPACT 칸을 쓸 때 | `assets/save-daily-rules-v0.1.json`의 holdings가 8월 기준(MRVL 포함)이다. 상태 파일 기준으로 고치거나 상태에서 읽게 한다. 대상 테스트 `test_save_daily_pipeline.py`(VM에서 실행, Windows는 `pypdf` 없음) |
| SAVE 텍스트 입력 어댑터 | K2 | G3에서 시장 환경 메모가 "판단에 씀"이고 텍스트 붙여넣기가 주 경로일 때 | 붙여넣은 "장 전 주요 뉴스" 텍스트를 기존 SAVE 이벤트 스키마로 변환한다. 네트워크 금지(`OFFLINE_REPLAY`) 경계는 유지한다 |
| SAVE 자동 수집 | K2~K3 | SAVE가 공식 피드·API 제공을 확인해 줄 때 | 그 전에는 자동 조회·비공개 API 호출·제3자 수집 확장을 쓰지 않는다(검토 문서 §8, 약관 확인 필요) |
| 수치형 시장 레짐 연구 | Cold Path 연구 | S8(G4) 뒤 | 지수 추세, breadth, 소형/대형 비율, 신용 스프레드, VIX 기간구조 후보를 사전 등록 → 여러 레짐 walk-forward → 같은 후보군 무작위 기준선과 비교한다. 수치는 공식 통계·키움 기준. 검토 문서 §3 |
| 신규매수 후보 RS·ATR 확장 시험 | K2 이상 | 신규매수 흐름을 다시 열 때 | RS 리더십 필터와 50MA 대비 ATR% 배수 상한을 `technical-strategy.md`의 절차(하나씩 제거 시험, 여러 레짐 walk-forward)로 시험한다. 그 전에는 규칙으로 쓰지 않는다. 검토 문서 §2~3 |

---

## 6. 리스크와 남은 확인 필요

### 6-1. 리스크

| 위험 | 위치 | 완화 | 남는 기간 |
|---|---|---|---|
| 미체결 주문 확인 없이 상태를 적용한다 | I0 | 경고, `open_orders_verified=false` 기록, 체결 조회 필수, S1b 진단, Judge 10번 | 미체결 조회 수정까지 |
| 시장 가격 경로가 `return_code` 누락을 성공으로 본다 | `kiwoom_runtime_bridge.py:137-138`(고정) | 카드 가격 칸에 가격 증거 상태를 표시한다. 계좌 경로는 S1에서 엄격하게 바꾼다 | S8 R6까지 |
| `normalize_snapshot` 예외 때 "빈 보유 + AVAILABLE" | `run_manual:306-330`(고정) | S2·S5 가드, S7a fact pack 가드 | S8 R6까지 |
| 확인 코드가 사람의 확인을 증명하지 못한다 | I0 | 사용자 메시지 기록, `CLAUDE.md`·`AGENTS.md` 문구, Claude Code deny, Cowork 절차 문서·메모리, 라이브러리 코드 검사(실수 방지) | 계속(사용자 절충) |
| 파일럿 #1의 확신도가 모두 "낮음"으로 묶인다 | S2 | 평가 때 감안하고 #2와 비교 | S5까지 |
| CI 알려진 실패 17건 | 전체 | 알려진 실패로 표시하고 기준선과 비교 | S8까지 |
| 사용자 중계 부담 | 전체 | 동시 진행은 S1·S1b·S2, S5·S6만. 단계마다 첫 메시지와 명령을 이 문서에 둔다 | 계속 |

### 6-2. 남은 확인 필요

- 정상 계좌 응답(잔고·예수금·체결)에 `return_code`가 있는지 → S1 2단계.
- Claude Code `--worktree`가 `.worktreeinclude`를 따르는지(설정 가이드 기준) → S1 0단계.
- 사용자가 평소 쓰는 수동 분석 명령의 정확한 문자열. 저장소 문서에서 찾지 못했다 → S1 Builder가 사용자에게 묻고 사용법 문서에 적는다.
- 상태 파일을 원시 바이트 해시로 비교하는 다른 코드가 있는지(§1-5) → S1.
- 제안 만료 15분이 Windows → Cowork 흐름에 충분한지 → S4 이후 측정.
- 미체결 조회(ust21050) 실패 원인 → S1b.
- `frgn_stk_book_uv`(평단)에 수수료가 포함되는지.
- 보유 수량으로 `poss_qty`(held)와 `qty`(settled) 중 무엇을 쓸지. P3 제안은 held.
- Windows와 CI 러너의 `core.autocrlf` 값 → S8.
- 현황판 예약 작업이 장치 파일을 읽을 수 있는지 → H1 v2.
- 단일 계좌 가정(런타임 `.env`의 한 계좌).
- dashboard 2,734줄의 운영 적합성 → G3.

---

## 7. 측정 (P5)

| 지표 | 현재(9/30) | 목표 | 측정 시점 | 미달 시 |
|---|---|---|---|---|
| 불일치 감지 → 조정 완료 | 조정 0/16 | 분석한 날 안에 | S4 이후 매 분석 | 2회 연속 당일 미완료 → §2의 묶음 명령·만료 재검토 |
| 상태 나이 | 49일(8/12 기준) | 최근 분석일과 같음 | S6 상태 점검 | H1 한 줄에 경고 표시 |
| 카드 활용(사용자 평가) | 결과 미사용 | 파일럿 2회 중 "판단에 씀" 1회 이상 | G3 | S5 미달 규칙 |
| 결정 원장 | 0건 | 주 1회 이상 | S7b 뒤 4주 | 2주 연속 0건이면 카드 확정 단계의 부담을 점검 |
| 사후 채점 | 0건 | 20세션 첫 결과 | 첫 원장 뒤 약 4주 | 채점 실패는 Cold Path. 다음 카드에 표시 |
| CI 알려진 실패 | acceptance 관련 17건(+ Windows 전용 6건) | acceptance 관련 0건 | G4 | S8 중단 규칙 |

- 판단 품질에 대한 결론은 원장 30건 이상이 쌓인 뒤에만 낸다(P3 §6-2).
- P6 월간 점검(30분, phase1 §1-2)은 S4 완료 뒤 약 한 달에 처음 한다(제안).

---

## 8. 사용자 결정 (2026-09-30, G0 통과)

1·2·3·5는 권장안대로 승인됐다. 4(메모리 저장)는 S4에서 적용 명령이 생긴 뒤 묻는다.

1. **로드맵 승인:** §3의 순서, 게이트 5개, 병합 규칙.
2. **미결 항목 결정안 5개(§2):** 두 명령 유지, 만료 15분 유지, I0-b 트리거 방식, 미체결 진단은 S1과 병행, I4는 S7b 뒤.
3. **P3 보완 설계 3건(§1):**
   - 라이브러리에도 `confirm_code` 검사를 넣는다(§1-6, 실수 방지용).
   - `CLAUDE.md`·`AGENTS.md` 문구를 "스냅샷 그리고 사용자 확인"으로 바꾼다(§1-7).
   - v1은 복원 명령을 만들지 않고, 손상 때는 적용을 멈춘다(§1-12).
4. **Cowork 적용 규칙을 프로젝트 메모리에 저장할지(§1-8).** 문구(제안): "reconcile apply는 이번 대화에서 사용자가 해당 제안의 '확인 <코드>'를 직접 보냈을 때만 실행한다. 코드를 스스로 넣거나 이전 확인을 재사용하지 않는다. 예약 작업에서는 실행하지 않는다. 실행 전에 references/broker-snapshot-reconciliation.md를 읽는다." S4에서 적용 명령이 생긴 뒤 저장한다.
5. **커밋·병합 실행 위치:** Windows 터미널에서 사용자가 실행한다(§1-10). Cowork에서 하려면 잠금 파일 정리를 위해 삭제 권한 승인이 필요하다.

---

## 9. 진행 기록

- 2026-09-30 P4 초안 작성, 반론 검토 반영.
- 2026-09-30 **G0 통과:** 로드맵, §2 결정안 5개, §8-3 보완 3건을 모두 승인했다. 커밋·병합은 사용자가 Windows 터미널에서 실행한다. §8-4 메모리 저장은 S4에서 정한다.
- 2026-09-30 **S0 완료:** 커밋 `6a5a167`(`.worktreeinclude`와 docs 4개, 5개 파일). push 안 함. staged에 다른 파일이 없음을 Cowork가 확인했다.
- 2026-09-30 §1-8 정정(미커밋): `CLAUDE.md`가 Cowork 대화에도 전달됨을 확인했다. 다음 docs 커밋에 포함한다.
- 2026-09-30 **S1 완료:** Builder 커밋 `dfb7f7b`(브랜치 `worktree-i0-reconcile`, 17개 파일). 보고서 `docs/claude/i0-builder-report-2026-09-30.md`.
  - 테스트: 대상 테스트 기준선 대비 새 실패 0, 신규 `test_reconcile_broker_state.py` 48건 통과, 전체 테스트 새 실패 0(worktree 기준선 실패 314건은 줄바꿈으로 인한 원시 해시 불일치), 스키마 감사 PASS, 고정 16개·정책 파일 diff 없음.
  - `return_code`: 정상 응답 3개(잔고·예수금·체결) 모두 있고 값은 0.
  - 실데이터 제안 1회 성공: 경고는 `OPEN_ORDERS_UNVERIFIED` 하나, 적용 후 알림 엔진 사전 검사 PASS. 미체결에 더해 실현손익(ust21630) 조회도 과거 16회 모두 실패였다 → S1b 범위에 추가.
  - 수동 분석 명령: `python manage-us-stock-strategy/scripts/run_manual_portfolio_analysis.py`(인자 없음).
  - `SKILL.md`는 배포 게이트 해시에 묶여 있어 수정하지 않았다(§5 대기).
- 2026-09-30 Builder 세션의 사용자 결정 2건(P3 변경, Judge 확인 대상): ① 값이 같아도 브로커 확인 기록이 오래되면 확인 기록만 갱신하는 제안(`METADATA_ONLY`)을 만든다 ② 원장 밖 상태 변경(`STATE_CHANGED_OUTSIDE_LEDGER`)이 보이면 적용을 거부한다.
- 2026-09-30 Cowork 사전 점검(Judge 판정 아님): 변경 파일에 고정 16개·정책 파일 없음, `CLAUDE.md`·`AGENTS.md` 문구가 "스냅샷 그리고 사용자 확인"으로 바뀜, 추가된 deny 규칙 확인, 커밋 diff에서 금액·계좌번호 패턴 없음.
- 2026-09-30 원가 교차검증 `DIFFERS` 참고: 키움 스펙 ust21070 응답 예시에서도 `evlt_amt − pl_amt`(112,003.75)가 `poss_qty × frgn_stk_book_uv`와 `frgn_stk_book_amt`(둘 다 111,453.32)보다 약 0.49% 크다. `pl_amt`의 기준이 매입금액과 다른 것으로 보인다(수수료 추정, 확인 필요). 파생 원가는 스펙의 매입금액과 맞는다.
- 2026-09-30 **S1b 완료:** `docs/claude/open-orders-diagnosis-2026-09-30.md`(미커밋). 원인(확정, 오늘 재현 2회): 키움이 미체결·당일 실현손익 "내역 없음"을 `return_code=20`으로 돌려주고, 브리지가 0이 아닌 값을 모두 `KIWOOM_API_RESPONSE_ERROR`로 분류한다. 요청 결함은 아니다. 과거 16회도 같은 원인이라는 것은 추정이다(당시 응답이 저장되지 않음). 코드 20은 스펙 오류 코드 표에 없다. 수정안: 안 A 관측 추가(K2), 안 B "없음 선언"을 빈 PASS로 인정(K3). 권고: I0 병합 뒤 그 위에서 A, 빈도를 모은 뒤 Judge와 함께 B.
- 2026-09-30 **S3 1차: FAIL**(커밋 `dfb7f7b`, BASE `6a5a167`). 대상 9개 모듈은 BASE와 같은 ERROR 3건(worktree 줄바꿈)뿐이고 새 실패 0. 2~9, 11~15번 PASS, 10·16·17번 동의.
  - 1번 FAIL: ① 스크린샷(2.5) 제안은 라이브러리에서 코드·방법·메시지 없이 적용된다 ② 호출자가 `now`를 과거로 넘기면 만료 제안이 적용된다.
  - 추가 우회: 라이브러리·CLI에 다른 원장 경로를 주면 원장 검사를 건너뛴다. 원장·백업을 git 추적 폴더에 쓸 수도 있다.
  - 16번 비용: `as_of`가 날짜 단위라 거의 매 분석일 `METADATA_ONLY` 확인이 필요하고, `holding_change_reconciliations`가 하루 1건씩 는다.
  - 17번: 원장 밖 변경을 모두 거부하면 문서화된 정상 편집(체결 기록, strategy_version 수정)에도 걸리고 해제 절차가 없다.
- 2026-09-30 **Judge FAIL 대응 사용자 결정:** F1 = v1에서 2.5 제안 적용을 라이브러리에서 차단. F2 = 만료·`confirmed_at`에 실제 시계 사용(`now`는 미래 쪽으로만). F3 = 원장·백업 경로 인자 제거(상태 경로에서 파생). 17번 = JSON 손상과 "원장 기록 뒤 상태 쓰기 실패"만 거부하고, 그 밖의 원장 밖 변경은 경고 후 사용자 확인으로 적용.
- 2026-09-30 **사용자 결정: 스크린샷(2.5) 경로는 쓰지 않는다.** 계좌 정보는 키움 API로 연계되므로 사용자 계좌 스크린샷은 의미 있는 입력이 아니다. 복잡도를 늘리는 기능은 고려하지 않는다. P3 §4-3의 "스크린샷 경로는 키움 장애 때의 대안으로 남긴다"를 대체한다. 이번 수정은 F1(라이브러리 차단)까지만 하고, 코드 제거는 S4 뒤 별도 REMOVE 작업으로 한다. 키움 장애 때는 그날 조정을 건너뛰고 카드·분석에 "상태 미조정" 라벨을 붙인다.
- 2026-09-30 **S3 FAIL 수정 완료(커밋 대기):** Builder가 같은 worktree에서 F1·F2·F3·17번을 반영했다(9개 파일, 보고서 §12). `test_reconcile_broker_state` 48 → 56건 통과, 관련 3개 모듈 그대로 통과, 전체 테스트 새 실패 0, 스키마 감사 PASS, 고정 16개·정책·`SKILL.md`·상태 파일 diff 없음. 신규·변경 테스트가 옛 코드(`dfb7f7b`)에서는 실패함을 확인했다. Builder 추가 판단 1건(Judge 확인 대상): 원장 밖 변경이 감지됐는데 제안 경고에 없으면 `OUTSIDE_LEDGER_WARNING_NOT_IN_PROPOSAL`로 거부.
- 2026-09-30 **S3 2차: PASS**(커밋 `90a11b8`, BASE `6a5a167`, 새 Judge 세션 `judge-i0-r2`). 1~17번 모두 PASS, 10번 동의. 대상 9개 모듈은 기준선과 같고 신규 56건 통과, 스키마 감사 PASS. 전체 테스트의 새 ERROR 1건은 detached HEAD라 `git_branch`가 비어 나는 것으로, 기준선도 detached면 똑같이 난다(실질 새 실패 0). 고정 16개·정책·`SKILL.md`·2.5 스키마 diff 없음. 1차 우회 3건이 모두 막혔다. Judge는 CLI apply를 직접 실행하지 않고 테스트와 코드 추적으로 판정했다(거부 규칙과 Judge 금지 규칙).
- 2026-09-30 결정 17로 §1-12의 "손상" 정의가 좁아졌다: 적용을 거부하는 것은 JSON 파싱 실패와 "원장 기록 뒤 상태 쓰기 실패"(현재 상태 = 원장 마지막 줄의 before-hash)뿐이다. 그 밖의 원장 밖 변경은 경고 후 사용자 확인으로 적용하고 원장에 기록한다(Judge 권고 ④).
- 2026-09-30 Judge 권고 ③ 반영(미커밋): `references/alert-automation.md:53`의 옛 "또는" 문구를 "스냅샷 그리고 해당 제안의 사용자 확인"으로 바꿨다(고정 파일 아님, K0). `SKILL.md:130`은 여전히 §5 대기.
- 2026-09-30 **G1 통과, S4-1 병합 완료:** 사용자가 Windows 터미널에서 `git merge --no-ff 90a11b8` → 병합 커밋 `5c02146`(부모 `6a5a167`, `90a11b8`). Cowork 확인: 병합 결과 트리가 Judge PASS 커밋 `90a11b8`의 트리와 같다(판정받은 내용 그대로). 바뀐 파일 17개가 Builder 커밋과 같다. push 안 함.
- 2026-09-30 **S4-2 VM 사전 확인 PASS:** Cowork VM(Python 3.10.12)에서 `test_reconcile_broker_state.py` 56건 통과(라이브러리·CLI 적용 경로 포함, 임시 폴더 사용). 실제 상태 파일 해시 전후 동일(`017225ec…`), 원장·백업 파일 생성 없음. 실제 상태 복사본에 적용해 보는 것은 실제 제안과 확인 코드가 있어야 하므로 첫 조정 때 필요하면 한다.
- 2026-09-30 첫 실제 조정(S4-4)은 새 Cowork 작업에서 한다. 병합으로 바뀐 `CLAUDE.md` 적용 규칙이 새 작업을 열 때 반영되기 때문이다(§1-8).
- 2026-09-30 **§8-4 결정: 저장.** Cowork 적용 규칙(이번 대화의 "확인 <코드>"만, 코드 입력·재사용 금지, 예약 작업 금지, 실행 전 절차 문서 읽기)을 프로젝트 메모리에 저장했다.
- 2026-09-30 **S4-4 첫 실제 조정 완료, G2 통과.** 두 번 모두 새 Cowork 작업에서 사용자의 "확인 <코드>" 메시지로 적용했다(`COWORK_CHAT_USER_MESSAGE`).
  - 1차 revision 14 → 15(제안 11:38 KST): 보유 수량 1종목, 파생 원가, 가용 현금, 브로커 확인 기록. 경고는 `OPEN_ORDERS_UNVERIFIED` 하나였고, 적용 후 알림 엔진 검사는 통과했다. 적용 전에 현황판의 키움 조회값(06:12 KST)과 대조해 일치를 확인했다.
  - 적용 뒤 수동 분석(11:50 KST): `DIFFERENT`(`AVAILABLE_CASH_DIFFERS`만). 보유·평단 차이는 해소됐다. 1차 제안 조회 뒤 키움 USD 예수금이 바뀌었다. 원인은 SOXL 배당 입금이다(사용자가 키움 거래내역으로 확인, 환율 환산 아님).
  - 2차 revision 15 → 16(제안 12:35 KST): 가용 현금만.
  - 재분석(12:36 KST, `manual-20260930T033605866426Z-de8c5915d000`): `broker_diff_status=MATCH`. 원장 2건(두 번째 줄이 첫 줄 해시를 이음, 상태 해시 연결 확인), 백업 2건, 상태 파일 JSON 정상·줄바꿈 유지, 원장·백업·제안은 git 추적 밖.
  - G2의 "원장 1건, 백업 1건"은 가용 현금 변동 때문에 2건씩으로 충족했다.
- 2026-09-30 **사용자 결정: 조정 확인 때 사용자 기억과 대조하지 않는다.** 판단 근거는 키움 조회값(제안, 미국주식 현황판)이다. Cowork는 차이 표를 현황판 키움 값과 대조해 보고한다.
- 2026-09-30 S4 관찰(조치 대기):
  - 파생 원가(수량 × 평단, 센트 반올림)가 키움 매입금액보다 1센트 미만~수 센트 작다. 키움 평단이 소수 넷째 자리까지만 오기 때문이다. 개선 후보: 키움 매입금액을 그대로 쓴다(K2 이상, §5 대기).
  - 가용 현금은 장 마감 뒤에도 배당 입금 같은 현금 이벤트로 바뀐다(이번에는 1차 제안 조회 11:38 KST와 적용 뒤 분석 11:49 KST 사이). 배당은 체결이 아니므로 현금만 다른 재조정으로 반영된다. 이런 재조정이 얼마나 자주 필요한지 P5에서 센다.
  - **확인 필요:** 오늘 수동 분석 5회가 모두 `preflight_status=FAIL`이다(hard fail: `ACQUISITION_TIMESTAMP_INVALID`, `AUTHORITY_REVALIDATION_AT_ACQUISITION_CUTOFF_FAILED`, `TEMPORAL_EVIDENCE_VIOLATION`, `acquisition_completed_at` 없음). 첫 적용 전 실행(02:34, 02:37 UTC)부터 같으므로 조정이 원인은 아니다. 9/9~9/17 실행은 PASS였다. 원인은 진단하지 않았다. S5 카드 파일럿 전에 읽기 전용으로 진단한다.
- 2026-09-30 **S4 관찰의 preflight FAIL 진단 완료:** `preflight-fail-diagnosis-2026-09-30.md`(커밋 `b76d5e7`). 원인(확정): 브리지 `_sanitize`가 실패한 계좌 조회(미체결·실현손익, 키움 "내역 없음" `return_code=20`)의 `retrieved_at`을 지워(`52fb932`) 취득 완료 시각(cutoff)이 None이 되고, hard fail 3종이 연쇄로 붙는다. 9/17까지 PASS였던 것은 그 이전 코드 때문이다. 조정은 원인이 아니다.
- 2026-09-30 **K3 설계 결정:** `preflight-fail-fix-design-2026-09-30.md`(커밋 `baea3f5`). 라이브 부모 시계 방식(ADD-T, `run_manual_portfolio_analysis.py` 수정)은 결과가 PARTIAL·UNVERIFIED에 그쳐 S5 목표(확신도 상한 해제)에 미달하고 "S8 전 고정 파일 16개 수정 금지"(§3)와 충돌해 보류한다(S8 R6 선택 항목). 경로는 S1b 안 A(K2) → 빈도 수집 → 안 B(K3, 독립 Judge)다.
  - 사용자 결정: 안 B 착수 기준은 2거래일 이상에 걸쳐 3회 이상 관측. S5는 먼저 진행하고 확신도 상한 해제는 안 B 뒤로 한다.
- 2026-09-30 **S1b 안 A 완료·병합:** 커밋 `98a660b`(사용자가 Windows 터미널에서 `merge --ff-only`). 브리지·감사 스크립트·스키마·신규 테스트 `test_s1b_provider_marks.py`(20건). 고정 파일·정책·상태 파일은 바뀌지 않았다. Builder 기록: `s1b-plan-a-builder-2026-09-30.md`.
  - 병합 후 첫 실제 실행(`manual-20260930T063917375338Z-3c02fdaf2b5f`): 미체결 조회에 `provider_return_code=20`, `no_data_declared=true`. preflight는 FAIL 그대로다(안 A는 관측만 추가하므로 정상). 새 코드로 관측한 횟수는 1회이고, 기준까지 평소 분석 때 쌓는다.
  - **확인 필요:** 안 B로 GRADE_B에 도달하는지는 코드 추론이다(안 B 병합 뒤 라이브 1회로 확정). ET 자정 근처 실행은 `ACQUISITION_SESSION_ROLLOVER`로 FAIL이 되며 이는 올바른 동작이다.

- 2026-09-30 **Trading_Skill 자료 검토 반영(K0):** `trading-skill-materials-review-2026-09-30.md`. 6개 자료는 Knowledge·정책으로 넣지 않고 연구 후보로만 둔다(증거 등급 D, 스윙 원칙 대부분 기존 규칙과 중복). 시장 환경 판단 공백은 S5 "시장 환경 메모"(SAVE, 카드 날 수동 입력, 없으면 "미입수"로 진행)로 먼저 확인한다. saveticker.com 직접 모니터링은 자동 조회 차단(403)과 제3자 확장의 비공개 API 자동 호출 때문에 채택하지 않았다(사용자 결정). 대기 항목 5건을 §5에 추가했다. 코드·정책·Skill 파일 변경 없음.
- 2026-09-30 **S5 카드 파일럿(오늘 2회차 세트) 실행·평가:** `workspace/outputs/holding-cards/2026-09-30-r2/`(머리말 1, 카드 3, 커밋 안 함, 분석 `manual-20260930T112114979550Z-f84117fcf3f5`). 판단: MVLL TRIM 검토 / SOXL HOLD / NBIS HOLD, 확신도 모두 낮음(상한 유지: 증거 UNVERIFIED, 상태는 조정됨 revision 16·MATCH). **사용자 평가: 판단에 씀.** 고칠 점은 받지 않음.
  - 시장 환경 메모(SAVE 9/29자 PDF 입수, SAVE 미입수 0회): 사용자 평가 아직 없음(판단에 씀 / 참고만 / 안 씀 미기록). 메모 때문에 바꾼 판단은 없음.
  - 지난 카드 대비 변화 칸을 처음 채움. 지난 세트(같은 날 07:55 UTC, `2026-09-30/`)의 "9/29 종가"가 확정 종가가 아니라 야간장 값과 같았음을 발견(원인 확인 필요). 판단은 그대로, 손실 한도까지 남은 거리만 달라짐.
  - **미결:** 오늘 두 세트를 각각 파일럿 몇 번째로 셀지 사용자 결정 필요(07:55 UTC 세트는 평가 기록 없음). 이 결정으로 G3의 "2회 중 판단에 씀 1회 이상" 충족 여부가 정해진다. G3 판정은 아직 하지 않음.
- 2026-09-30 **사용자 결정: 파일럿 횟수.** 오늘 07:55 UTC 세트(`2026-09-30/`)를 파일럿 #1(평가 기록 없음), 이번 세트(`2026-09-30-r2/`)를 #2(판단에 씀)로 센다. **G3 통과**(2회 중 "판단에 씀" 1회 이상). #1은 평가가 없어 조건은 #2 하나로 충족됐다. 다음: S7a 진입 전 정할 항목 5개(카드 형식, dashboard, baseline, 행동 대응표, 결정 원장 경로)와 시장 환경 메모 평가를 하나씩 묻는다.
- 2026-09-30 **G3 통과 뒤 결정 1/6 카드 형식:** 현행(머리말 5줄 + 종목 카드 11칸 표)을 그대로 확정한다. S7a 코드화의 기준 형식으로 삼는다. 나머지 5개(dashboard, baseline, 행동 대응표, 결정 원장 경로, 시장 환경 메모 평가)는 하나씩 정하는 중.
- 2026-09-30 **결정 2/6 dashboard:** 카드 경로에서 dashboard를 뺀다. P3 a′ 안대로 plan의 필드 이름·의미만 빌린 별도 카드 스키마를 쓰고, `order_intent_terms`·`proposed_quantity`·`limit_price`·`target_weight_pct`·`plan_status`는 두지 않는다. dashboard가 카드를 plan으로 받지 않는다는 거부 테스트를 S7a에 넣는다(K2).
- 2026-09-30 **결정 3/6 baseline:** 유지한다. 카드의 thesis·반론·kill 기준 칸이 baseline 필드를 입력으로 쓰고 있으므로, S7a 뒤 카드가 이 칸을 스스로 채우는지 확인한 다음 대체(REMOVE) 여부를 다시 판정한다.
- 2026-09-30 **결정 4/6 행동 대응표(카드 → sidecar `DECISION_ACTIONS`):** HOLD→`HOLD_CORE`(카드에 검토 필요 표시가 있으면 `HOLD_REVIEW_REQUIRED`), ADD→`ADD_REVIEW`, TRIM→사유 태그 1개 필수(비중·군집=`TRIM_CONCENTRATION`, 변동성·상품·이벤트=`TRIM_RISK`, 기술=`TRIM_TECHNICAL`, 수익=`TRIM_PROFIT`, 밸류에이션=`TRIM_VALUATION`), EXIT→손실 한도=`EXIT_HARD_STOP`·thesis 훼손=`EXIT_THESIS`, 교체 제안=`ROTATE_REVIEW`, 현금이 나은 경우=`KEEP_CASH`. 예: 오늘 MVLL은 `TRIM_CONCENTRATION`. 코드화(S7b)에서 sidecar 목록을 수정하지 않고 이 표로 대응만 시킨다.
- 2026-09-30 **결정 5/6 결정 원장 경로:** `stock-strategy-system/decision_journal.json`(새 파일). `portfolio_state.json`은 건드리지 않는다. 가격·보유 판단이 들어가므로 S7b에서 `.gitignore`에 추가하고, sidecar의 해시 체인 원장 함수를 수정 없이 쓴다.
- 2026-09-30 **결정 6/6 시장 환경 메모:** 평가 = 판단에 씀(SAVE 9/29자 입수, 미입수 0회). 카드 형식에 남긴다(SAVE가 있는 날만 머리말 2줄, 없으면 "시장 환경: SAVE 미입수"로 적고 카드 작성은 막지 않음). 필수 칸이 아니라 선택 입력이다. 참고: 이번 세션에서 메모 때문에 바뀐 판단은 없다고 기록했으므로(위 S5 항목), 이 평가는 사용자 판단이며 다음 파일럿에서 다시 센다.
- 2026-09-30 **G3 결정 6건 완료.** 카드 형식 현행 확정, dashboard 제외(a′ 별도 스키마), baseline 유지(S7a 뒤 재판정), 행동 대응표 확정, 원장 경로 `stock-strategy-system/decision_journal.json`, 시장 환경 메모 유지. 다음: S6(I7 상태 점검, S5와 병행) 상태 확인 후 S7a 착수.
- 2026-09-30 **S6 I7 병합 완료:** Builder 커밋 254a43a(worktree-status-view, 신규 3 + .gitignore 1줄)를 사용자가 Windows 터미널에서 `git merge --no-ff`로 병합했다(병합 커밋 0ac9212, 부모 6e7c781·254a43a, 변경 4파일 +592). 병합 전 `.git/index.lock` 잔존 파일을 삭제하고 재시도했다(git 프로세스 없음 확인). 대상 테스트 13건 통과(병합 뒤 Cowork에서 재실행). 원본 폴더 실행 결과가 Cowork 수동 확인과 같음: 상태 9/30 03:35 UTC(0일), 조정 원장 2건·revision 16, 브로커 MATCH, 마지막 카드 9/30, 미체결 조회 KIWOOM_API_RESPONSE_ERROR(경고). 고정 16개·정책·상태 파일 변경 0. 전체 스위트 기준선 실패(23 failures + 291 errors)는 worktree 데이터 부재로 추정, 원인 확인 필요. 채점 대기 0은 임시 스키마 가정(`assumed_schema: true`), S7b에서 확정. 다음: H1(Cowork, Sonnet·medium), 그다음 S7a.
- 2026-09-30 **S7a I1 병합 완료:** Builder 커밋 c6fae62(worktree-card-v1, 신규 8 + .gitignore 1줄)를 사용자가 Windows 터미널에서 `git merge --no-ff`로 병합했다(병합 커밋 65117d5, 부모 0ac9212·c6fae62, 변경 9파일 +2699). 병합 뒤 Cowork 확인: fact pack 36·card 65·portfolio_status 13·language_contract 2건 통과, 스키마 감사 PASS, `.gitignore`가 holding-cards 산출물을 무시한다. 고정 16개·dashboard·renderer·정책·상태 파일 변경 0. 전체 스위트는 기준선 대비 새 실패 0(Cowork VM 대조: 에러 295 동일, 기준선 실패 해소 0). 사용자 수용한 Builder 판단: 확신도 상한 해제 등급은 GRADE_A·GRADE_B, ROTATE_REVIEW·KEEP_CASH는 EXIT 사유 태그. 확인 필요(Judge·사용자): ① 정책 레버리지 식의 `NBIL` 표기(NBIS 배수가 결측, 정책 파일이라 미수정) ② timing은 최근 알림 결과가 8/5자라 항상 NOT_EVALUATED ③ 카드 자유 서술 속 숫자는 검증하지 않음 ④ `SKILL.md`에 새 명령 미등록(배포 게이트 해시, P4 §5 대기). 다음: 수동 분석 1회 뒤 Cowork에서 fact pack → 카드 → 검증 → 렌더로 실제 카드 1건을 만들고 사용자가 평가(판단에 씀/참고만/안 씀). '안 씀'이면 S7b로 가지 않고 형식을 먼저 고친다.
- 2026-09-30 **S7a 실제 카드 1건 평가:** 카드 r3(분석 manual-20260930T134453382928Z-be5dbd8ac6b0, decision_as_of 2026-09-30T13:44:53Z; MVLL TRIM/LOW, SOXL HOLD/LOW, NBIS HOLD/LOW, 검증 PASS·렌더 OK)를 사용자가 평가했다: **판단에 씀.** 따라서 형식 수정 없이 S7b 진행 조건 중 카드 수용은 충족. 한계(확인 필요): 이벤트는 파일럿 r2 재사용(재조회 안 함), 9/30 SAVE 미반영, 확신도는 증거 등급 UNVERIFIED·preflight FAIL로 전부 LOW 상한. S7b는 정책 기본 방향·손실한도 재검토(새 Cowork 진행 중) 결과가 나온 뒤 시작한다.
---

## 10. 반론 검토 반영 기록 (2026-09-30)

초안을 별도 서브에이전트가 P3와 코드에 대조해 검토했다(25건). §10 네 결정(B1, Cowork 채팅 확인, 카드는 Cowork, 현금 + SPY)은 뼈대에서 지켜졌다고 판정됐다. 인용한 행 번호와 해시 불일치 지적도 맞다고 확인됐다. 반영한 주요 지적은 아래와 같다. 주요 항목은 직접 다시 확인했다.

- **[실행불가] worktree에 git 제외 상태 파일이 없어 상태 불변 테스트가 처음부터 ERROR가 난다.** → `.worktreeinclude`를 S0에 추가했다(§1-2).
- **[실행불가] `return_code` 검사를 직접 다루는 테스트가 대상 목록에서 빠졌다**(`test_k2_evidence_contract` 등 4개). → A1·A2 목록에 추가하고, 전체 테스트 1회를 완료 기준에 넣었다.
- **[안전] `CLAUDE.md`·`AGENTS.md`의 "또는 조회 스냅샷" 문구.** → §1-7에 반영하고 Judge 14번에 넣었다.
- **[실행불가·안전] 확인 코드 검사가 CLI에만 있어 멈춤 조건이 모호했다.** → 라이브러리 검사를 제안하고(§1-6), 코드가 사람의 확인을 증명하지 못한다는 한계를 명시했다. 멈춤 조건은 CLI와 라이브러리로 나눴다.
- **[실행불가] VM 실행을 Builder가 확인할 수 없다.** → S4에 VM 사전 확인을 넣었다(§1-11).
- **[사실오류] "Cowork는 CLAUDE.md를 읽지 않는다".** → 정정했다. 2번째 턴에 `CLAUDE.md`가 Cowork 대화에 전달되는 것을 확인했다(§1-8).
- **[안전] 백업 복사가 두 번째 쓰기 경로가 된다.** → v1 복원 없음, 손상 정의, 대기 항목으로 옮겼다(§1-12, §5).
- **[결정위반] 미체결 진단을 말없이 S6로 미뤘다**(P3 §4-2는 병행). → S1b로 되돌렸다.
- **[실행불가] `return_code` 실제 확인 방법이 비어 있었다**(`_sanitize`가 버림). → A1 2단계에 방법과 승인 절차를 적었다.
- **[논리] Judge가 Builder 보고서의 기준선에 기댄다.** → Judge가 merge-base를 직접 돌린다.
- **[실행불가] VM 커밋의 잠금 파일, 미병합 브랜치에 기댄 다음 worktree.** → 커밋·병합은 Windows 터미널에서 하고, §3 병합 규칙을 만들었다.
- **[안전] 실데이터 제안 파일이 커밋에 섞일 수 있다.** → git 제외 출력 폴더와 커밋 전 `git status`를 넣었다(§1-9).
- **[실행불가] 라이브러리 만료 검사가 스크린샷 경로 픽스처를 깰 수 있다.** → A1 4a에서 적용 범위를 계획 단계에 정하고, 기존 테스트 변경표와 Judge 15번을 넣었다.
- **[사실오류] 불일치는 해시만이 아니다**(`bundle_id`, `scope`, `proposed_patch`, revision). → §1-4, A1 4b를 고쳤다.
- **[논리] 브랜치 이름으로 병합하면 PASS 뒤 커밋이 섞인다. 첫 제안 경고 분기가 없다.** → 커밋 ID 병합, S4 경고 분기를 넣었다.
- **[결정위반] R9 SPY 추가, A6의 기초자산 표시·키움 일봉 누락, USER_TERMINAL 대체 경로 누락.** → 각각 §5 대기 항목, A6, A1 4i에 반영했다.
- **[논리] S7a가 I7/H1에 의존하지 않았다. G2 지연 대안, 측정할 수 없는 기준(3회 연속, 파일럿 #3 이후, 주관 평가), "거버넌스 확장 금지"와 S8 충돌, 첫 적용 모델.** → 선행 조건, 대안, 기준 문구, "S8 전까지", Opus · xhigh로 고쳤다.
- **[사실오류] 옛 worktree 설명, "확인 필요 4개 해소".** → 정정했다.

---

## 부록 A. Claude Code 지시문

공통 조작: Windows 터미널에서 `cd "E:\사업\##금동한\코덱스저장소"` → 아래 시작 명령 → 세션 안에서 `/model`, `/effort`로 헤더의 설정을 고른다 → 지시문을 붙여 넣는다. A5~A8은 초안이며 착수 전에 Cowork에서 갱신한다.

실행 위치(2026-09-30 확인, 공식 문서 기준): Windows 터미널 CLI 대신 **Claude 데스크톱 앱의 Code 탭**을 써도 된다. 세션이 사용자 PC에서 돌고, 세션마다 worktree 옵션을 켤 수 있으며, `CLAUDE.md`·`.claude/settings.json` 권한 규칙과 `.worktreeinclude`를 따르고, 모델·추론 노력을 고를 수 있다. Builder와 Judge는 각각 새 세션에서 worktree를 켜고 연다. **앱의 브랜치 선택은 `codex/master-recovery-expansion`으로 둔다.** `main`은 예약 런타임용 옛 브랜치(`41f7b3f`)라 현재 브랜치보다 42커밋 뒤처져 있고 서로 갈라져 있다. 앱의 권한 모드는 K3 작업에서 승인을 받을 수 있게 "묻기" 계열로 둔다. 클라우드 세션(claude.ai/code 웹)은 키움 런타임과 미푸시 저장소에 접근할 수 없어 쓰지 않는다. VS Code 확장은 worktree를 직접 만들지 않으므로 권장하지 않는다.

### A1. S1 I0 Builder

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: BOUNDARY_RESET_REQUIRED (새 worktree `i0-reconcile`) · 이유: K3, 유일한 포트폴리오 상태 쓰기 경로를 만든다**

시작 명령: `claude --worktree i0-reconcile`

```text
역할: I0 Builder (K3). 보고는 한국어, 식별자와 명령은 영어로 쓴다.

읽을 것
- docs/claude/system-review-p3-design-2026-09-30.md: §2 경계 표, §4 전체, §10-2
- docs/claude/system-review-p4-roadmap-2026-09-30.md: §1(설계 보완 1-2~1-12), §4 S1·S3, §8(승인된 결정은 §9)
- docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md §2-1(고정 파일 16개)

절대 규칙
- 키움 주문 도구와 주문 API를 쓰지 않는다.
- 원본 폴더의 stock-strategy-system/portfolio_state.json을 쓰지 않는다. apply를 원본 상태 파일에 실행하지 않는다.
  테스트와 시험 적용은 임시 복사본만 쓴다.
- 고정 파일 16개와 정책 파일(stock-strategy-system/alert_policy.json, workspace/policies/*)을 수정하지 않는다.
  run_manual_portfolio_analysis.py도 고정 파일이다.
- normalize_snapshot의 입력·출력 계약을 바꾸지 않는다.
- 계좌번호, 토큰, .env 값, 보유 수량, 현금 금액을 화면에 출력하거나 커밋 파일에 쓰지 않는다.
- 줄바꿈 일괄 변환 금지. 커밋은 내 승인 뒤에만. push 금지.

순서
0. 환경: 이 worktree에 stock-strategy-system/portfolio_state.json과 alert_runtime_state.json이 있는지 확인한다(.worktreeinclude).
   없으면 원본 폴더(E:\사업\##금동한\코덱스저장소)에서 같은 경로로 복사한다. 원본은 읽기만 한다. 복사본이 git 제외 대상인지 git check-ignore로 확인한다.
1. 기준선: 아무것도 고치기 전에 대상 테스트를 실행하고 실패 목록을 기록한다.
   python -m unittest discover -s manage-us-stock-strategy/tests -p "test_kiwoom_broker_shadow.py"
   같은 방식으로: test_v2_5_broker_snapshot.py, test_v2_6_broker_beginner.py, test_manual_portfolio_analysis.py,
   test_k2_evidence_contract.py, test_k2_bridge_evidence_integrity.py, test_v2_6_4_kiwoom_adapter.py, test_broker_visibility_audit.py
   전체 테스트도 서브에이전트로 1회 실행하고 실패 목록만 기록한다.
2. return_code 확인: 기존 조회 경로는 _sanitize에서 return_code를 버린다.
   저장소 밖 임시 스크립트로 계좌 bridge의 하위 조회 함수를 직접 불러 잔고(ust21070)·예수금(ust21110)·체결(ust21510) 응답의
   최상위 키 이름 목록과 return_code 값만 출력한다. 실행 전에 스크립트 내용을 보여 주고 내 승인을 받는다.
   참고: 스펙 예시에는 return_code가 있고, 미체결 조회 오류 분류(kiwoom_account_readonly_bridge.py:99)도 return_code를 전제한다.
   정상 응답에 return_code가 없으면 구현하지 말고 대체 검사안을 보고한 뒤 멈춘다.
3. 계획: P3 §4-5 표 기준으로 파일별 변경과 테스트 목록을 보여 주고 내 승인을 기다린다. 기존 테스트를 바꿔야 하면 계획에 미리 적는다.
4. 구현(P3 §4-2~4-4). 다음을 꼭 포함한다.
   a. 라이브러리 apply_confirmed 안의 검사: unresolved_fields(모든 경로), 상태 해시, revision, 만료, confirm_code(P4 §8-3 승인 시).
      만료 검사의 적용 범위(키움 제안만, 또는 필드가 있으면 필수)를 계획 단계에서 정한다. 스크린샷 경로 픽스처에는 expires_at이 없다.
   b. 제안·적용 형식 통일(P4 §1-4): expected_portfolio_hash_before = canonical_hash(state), bundle_id, scope, proposed_patch, expected_state_revision.
      지금 run_kiwoom_broker_shadow는 file_hash를 expected_before_hash에 넣는다.
   c. 제안 파일 안의 경로는 저장소 상대경로로 쓴다. 제안은 Windows, 적용은 Cowork Linux VM(Python 3.10.12)에서 돈다.
   d. 적용 결과 파일의 줄바꿈 방침을 정하고, 상태 파일을 원시 바이트 해시로 비교하는 다른 코드가 있는지 찾아 보고한다(P4 §1-5).
   e. 원장 각 줄에 적용 후 canonical 해시를 기록한다. propose는 현재 상태 해시가 원장 마지막 값과 다르면 경고 STATE_CHANGED_OUTSIDE_LEDGER를 붙인다.
   f. 제안 출력은 workspace/outputs/reconciliation/<시각>/ 에 쓴다.
   g. .gitignore에 stock-strategy-system/backups/, stock-strategy-system/reconciliation_ledger.jsonl, workspace/outputs/reconciliation/ 을 추가하고 git check-ignore 테스트를 넣는다.
   h. CLAUDE.md Hard safety와 AGENTS.md:35의 "explicit user confirmation or a verified read-only broker snapshot"을
      "a verified read-only broker snapshot AND the user's explicit confirmation of that proposal"로 바꾼다.
      apply는 Cowork에서 사용자의 "확인 <코드>" 메시지가 있을 때만 실행하고, Claude Code·Codex·예약 작업·Judge는 실행하지 않는다고 적는다.
   i. .claude/settings.json deny: apply 명령 실행, stock-strategy-system/portfolio_state.json 편집. 패턴이 우회될 수 있는 한계를 보고서에 적는다.
   j. references/broker-snapshot-reconciliation.md:
      ① Windows에서 수동 분석과 propose를 한 번에 붙여 넣는 두 줄 블록(실제 인자 포함). 수동 분석 명령은 내게 물어서 적는다.
      ② Cowork 확인 절차: 차이 표 형식(P3 §4-1), 확인 규칙(P4 §4 S3 14번), 만료 시 propose만 다시 실행, 되돌리기는 새 제안으로 재조정(P4 §1-12).
      ③ 대체 경로: 사용자가 Windows 터미널에서 apply --confirm <코드> --confirmed-via USER_TERMINAL을 직접 실행하는 방법.
5. 검증: 1단계 목록 + 신규 test_reconcile_broker_state.py + python manage-us-stock-strategy/scripts/validate_schema_contracts.py + 전체 테스트 1회(서브에이전트).
   기준선 대비 새 실패 0. 기존 테스트를 바꿨다면 "이전 기대 → 새 기대" 표를 만든다. 고정 파일 16개와 정책 파일의 diff가 비어 있음을 보인다.
6. 실데이터 제안 1회(읽기 전용): --portfolio-state는 이 worktree의 상태 파일 복사본, 출력은 workspace/outputs/reconciliation/.
   실행 전후 상태 파일 sha256이 같음을 보인다. apply는 실행하지 않는다. 필수 조회가 실패하면 최대 3회까지 다시 시도한다.
7. 보고서 docs/claude/i0-builder-report-<YYYY-MM-DD>.md: 변경 파일, 기준선 대비 테스트, 기존 테스트 변경표, return_code 결과,
   실데이터 제안 결과(PASS/FAIL과 경고 코드만, 수치 없음), P3 §4-6의 1~10과 P4 §4 S3의 11~15 각각의 근거 위치, 남은 확인 필요.
8. 커밋: git status로 보유·현금 값이 든 파일이 staged에 없는지 확인한다. 내 승인 뒤 이 worktree 브랜치에 커밋하고 커밋 ID를 알려 준다.

멈춤 조건(멈추고 보고)
- 정상 응답에 return_code 없음
- 고정·정책 파일 수정이 필요함
- normalize_snapshot 계약 변경이 필요함
- 3회 시도에도 필수 조회 3개가 한 번도 모두 PASS하지 않음
- CLI가 코드 없음·불일치·다른 제안 코드에서 적용되거나, 라이브러리가 unresolved·만료·해시·revision 불일치 제안을 적용하는데 막을 수 없음
- 기존 테스트의 기대를 약하게 바꿔야만 통과함
```

### A2. S3 I0 Judge

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree `judge-i0` (Builder와 다른 터미널) · 이유: K3 Independent Judge**

시작 명령: `claude --worktree judge-i0`

```text
역할: I0 Independent Judge (K3). 저장소 파일을 수정·생성·커밋하지 않는다. 키움 조회를 하지 않는다.
예외: 테스트 실행에 필요한 git 제외 상태 파일 2개가 없으면 원본 폴더에서 복사하는 것만 허용한다.
임시 파일은 시스템 임시 폴더에만 만든다. 보고는 한국어.

1. 기준선: BASE=$(git merge-base worktree-i0-reconcile codex/master-recovery-expansion) 를 구하고 git switch --detach $BASE 로 체크아웃한다.
   대상 테스트(아래)를 실행해 실패 목록을 기록한다.
2. 검증 대상: git switch --detach worktree-i0-reconcile 로 체크아웃하고 커밋 ID를 적는다. 같은 테스트와 스키마 감사를 실행해 1과 비교한다.
   대상 테스트: test_reconcile_broker_state, test_kiwoom_broker_shadow, test_v2_5_broker_snapshot, test_v2_6_broker_beginner,
   test_manual_portfolio_analysis, test_k2_evidence_contract, test_k2_bridge_evidence_integrity, test_v2_6_4_kiwoom_adapter, test_broker_visibility_audit
3. 읽을 것: docs/claude/system-review-p3-design-2026-09-30.md §2·§4(특히 §4-6), docs/claude/system-review-p4-roadmap-2026-09-30.md §1·§4 S3,
   Builder 보고서 docs/claude/i0-builder-report-*.md, (있으면) docs/claude/open-orders-diagnosis-*.md
4. 우회 시도(임시 복사본에서만)
   - 라이브러리 apply_confirmed 직접 호출: unresolved_fields가 남은 제안, 만료된 제안, 해시·revision이 다른 제안 → 모두 거부돼야 한다.
     confirm_code 라이브러리 검사가 들어갔다면 코드 없음·불일치도 거부돼야 한다.
   - 적용 명령(CLI): 코드 없음, 코드 불일치, 다른 제안의 코드 → 모두 거부돼야 한다. 거부 때 상태 파일이 바뀌지 않아야 한다.
5. 고정 파일 16개(docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md §2-1)와 정책 파일의 diff가 $BASE 대비 비어 있는지 본다.
6. 판정 항목: P3 §4-6의 1~10, P4 §4 S3의 11~15.

출력(30줄 이내)
- 커밋 ID, 최종 판정 PASS/FAIL
- 항목 1~15: PASS/FAIL과 근거(파일:행 또는 테스트 이름)
- 10번(미체결 확인 없이 적용, 현금 의미 라벨)에 대한 의견: 동의/반대와 이유(S1b 진단 결과 반영)
- 발견한 우회 경로와 최소 수정 제안
```

### A3. S6 I7 상태 점검 Builder

**[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: high · 세션: 새 worktree `status-view` · 이유: K1~K2 읽기 전용 명령 추가**

시작 명령: `claude --worktree status-view`

```text
역할: I7 Builder (K1~K2). 설계: P3 §7, P4 §4 S6.
규칙: 읽기 전용 명령만 만든다. 고정 파일 16개(run_manual 포함), 정책 파일, 상태 파일을 수정하지 않는다. 커밋은 내 승인 뒤.
1. 기준선 테스트를 기록한다.
2. 계획을 보여 주고 승인을 기다린다.
3. manage-us-stock-strategy/scripts/portfolio_status.py: 상태 last_updated_at 나이, last_confirmed_broker_snapshot.as_of 나이,
   최근 수동 분석 시각과 broker_diff_status, 미체결 조회 상태, 최근 조정(reconciliation_ledger.jsonl), 종목별 baseline 나이,
   최근 카드 날짜, 채점 대기 건수. 입력 경로는 인자로 받는다. 없는 파일은 "없음"으로 표시하고 실패하지 않는다.
4. 출력: workspace/outputs/status/latest.json(.gitignore 추가, check-ignore 테스트)과 한국어 한 줄 요약.
5. tests/test_portfolio_status.py: 항목별 계산, 파일 없음, 오래된 상태 경고.
6. 원본 폴더 데이터로 한 번 실행한 결과를 화면에만 보여 준다(커밋 금지). git status 확인 후 커밋을 요청한다.
```

### A4. S1b 미체결 조회 진단

**[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: high · 세션: /clear 후 (원본 폴더, 새 세션, 코드 수정 없음) · 이유: K2 읽기 전용 진단**

시작 명령: `claude`

```text
역할: 미체결 조회(ust21050, account_open_items)와 실현손익 조회(ust21630) 진단 (K2, 읽기 전용). 코드와 설정을 수정하지 않는다. 주문 API·주문 도구 금지.
배경: 수동 분석 16회 모두 두 조회가 KIWOOM_API_RESPONSE_ERROR였다(P3 §1-3, docs/claude/i0-builder-report-2026-09-30.md §6).
그래서 scope_complete가 항상 false이고 기존 렌더러도 막힌다.
1. kiwoom_account_readonly_bridge.py에서 ust21050 요청 구성(필수 파라미터, 연속조회 헤더)과 오류로 분류하는 조건을 추적한다.
2. 키움 스펙(스펙 조회 도구가 있으면 ust21050, 없으면 references/kiwoom-*.md)과 요청 파라미터를 비교한다.
3. 필요하면 조회 전용 호출 1~2회로 재현한다. 저장소 밖 임시 스크립트를 쓰고, 실행 전에 내용을 보여 주고 승인을 받는다.
   출력은 return_code, return_msg, 최상위 키 이름만. 계좌 정보와 값은 출력하지 않는다.
4. 결과를 docs/claude/open-orders-diagnosis-<YYYY-MM-DD>.md에 쓴다: 원인(확정/추정), 근거, 수정안, 수정안의 K 등급과 영향 파일(고정 여부 포함).
멈춤: 원인 확인에 주문 API가 필요하면 즉시 멈춘다.
```

### A5. S7a I1 카드 코드화 (초안)

**[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: high · 세션: 새 worktree `card-v1` · 이유: K2 카드 스키마·검증기**

```text
역할: I1 Builder (K2). 설계: P3 §5-1~5-4(a′), P4 §4 S7a, G3 결정(P4 §9 진행 기록).
규칙: 고정 파일 16개, portfolio_decision_dashboard.py, render_beginner_portfolio_report.py, 정책 파일, 상태 파일을 수정하지 않는다.
카드에 수량·주문 필드를 두지 않는다. 커밋은 내 승인 뒤.
1. 기준선 테스트 기록. 2. 계획 제시 후 승인 대기.
3. schemas/holding-card.schema.json: plan의 필드 이름(positions[action, rationale, thesis_kill, material_risk], evidence_binding)만 빌린다.
   order_intent_terms, proposed_quantity, limit_price, target_weight_pct, plan_status는 금지.
4. scripts/build_holding_fact_pack.py(결정론): 분석 JSON·상태·baseline·규칙 엔진 결과 → fact pack. 보유 목록이 비었는데 AVAILABLE이면 실패.
5. scripts/validate_holding_card.py: P4 §4 S7a 완료 기준의 7가지 거부.
6. scripts/render_holding_cards.py: 카드 JSON → md(머리말 5줄 + 종목 카드).
7. 테스트: 거부 경우별, dashboard가 카드 파일을 plan으로 받지 않음(dashboard 수정 없이).
8. .gitignore에 workspace/outputs/holding-cards/ 추가와 check-ignore 테스트.
```

### A6. S7b I2 결정 원장·채점기 (초안)

**[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: high · 세션: 새 worktree `journal-v1` · 이유: K2 Cold Path 추가**

```text
역할: I2 Builder (K2). 설계: P3 §6, P4 §4 S7b, G3에서 정한 행동 대응표와 원장 경로(P3 제안: stock-strategy-system/decision_journal.json).
규칙: continuous_improvement_sidecar.py는 추가만 한다(run_manual이 import한다. 기존 함수의 시그니처와 동작 불변).
고정 파일, 정책 파일, 상태 파일 수정 금지. 커밋은 내 승인 뒤.
1. 기준선: test_manual_portfolio_analysis.py와 sidecar 관련 테스트 실패 목록.
2. 계획 → 승인.
3. 결정 원장: G3에서 정한 경로(git 제외). 기존 해시 체인 함수를 쓴다. analysis_action과 user_decision을 따로 기록하고, 정정은 새 항목으로 쓴다.
4. 채점기: horizon (5, 20, 60) 미국 거래 세션, session_calendar_activation.json, 확정 종가만, observed_at <= evaluation_as_of.
   보유 종목 가격은 키움 일봉(등급 B), 없으면 다른 제공자 가격에 "reference only" 라벨.
   비교는 현금 0% 대비와 SPY 대비 두 숫자. SPY는 키움 수용 범위 밖이므로 "reference only" 라벨. 기초자산(SOXX, MRVL)은 참고로 표시.
   채점 실패는 예외 대신 상태로 기록한다(Cold Path).
5. 운영 CLI: append-card(카드 확정 → 종목별 1건), record-user-decision, score.
6. 테스트: 체인 검증, 미래 정보 차단, 세션 계산, TRIM/EXIT 부호, reference only 라벨, git check-ignore.
```

### A7. S8 R6 Builder (초안)

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: BOUNDARY_RESET_REQUIRED (새 worktree `gov-r6`) · 이유: K3 고정 범위·권한 해시 재설계**

```text
역할: I4 R6·R7 Builder (K3). 설계: P3 §8 전체, P4 §4 S8.
규칙: 테스트 기대값을 약화하지 않는다. 권한 파일 4개의 의미를 바꾸지 않는다. 활성화(R9)는 하지 않는다. 커밋은 내 승인 뒤.
0. 이 worktree에서 원시 해시 테스트를 판정할 수 있는지 먼저 확인한다
   (docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md 진행 기록: 이전에는 불가해서 원본 폴더에서 진행했다). 불가하면 멈추고 진행 위치를 묻는다.
1. 기준선: 전체 테스트를 서브에이전트로 실행하고 실패 목록만 기록한다.
2. 계획 → 승인.
3. P3 §8-3 R6 ①~⑧. 보호 기능을 옮길 때마다 "이전 테스트 → 새 테스트" 대응표를 만든다.
4. R7: manifest 후보 1회 생성, 후보 검증기 PASS, 전체 테스트에서 acceptance 관련 17건 해소.
5. 보고서 docs/claude/i4-r6-builder-report-<YYYY-MM-DD>.md, 커밋 요청.
멈춤: 보호 기능 이전 중 기존 테스트 기대값을 바꿔야 함 / 권한 파일 의미를 바꿔야 함.
```

### A8. S8 R8 Judge (초안)

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree `judge-r8` · 이유: K3 Independent Judge**

```text
역할: I4 Independent Judge (K3). 저장소 파일을 수정·생성·커밋하지 않는다.
1. merge-base를 분리 체크아웃해 기준선 전체 테스트(서브에이전트)를 직접 실행한다.
2. git switch --detach worktree-gov-r6, 커밋 ID를 적고 같은 테스트와 I0 대상 테스트를 실행해 비교한다.
3. 기준: docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md §4의 8단계 범위, P3 §8-2·8-3,
   "고정 범위 축소가 권한·데이터 정확성·상태 쓰기 보호를 약화하지 않았는가".
4. Builder의 "이전 테스트 → 새 테스트" 대응표를 옮긴 보호 기능마다 확인한다.
출력(30줄 이내): 판정, 항목별 근거, 약화 발견 여부와 최소 수정 제안.
```

---

## 부록 B. Cowork 새 작업 첫 메시지

| 단계 | 모델 · 추론 노력 | 첫 메시지 |
|---|---|---|
| S2·S5 카드 파일럿 | Sonnet · high | `docs/claude/system-review-p4-roadmap-2026-09-30.md §4 S2(두 번째면 S5)대로 카드 파일럿을 해줘. 수동 분석은 방금 돌렸어.` S5부터 끝에 한 줄 추가: `SAVE: <"장 전 주요 뉴스" 텍스트 붙여넣기 / PDF 경로 / 없음>` |
| S3 Judge 결과 기록 | Sonnet · medium | `P4 로드맵 S3 Judge 결과를 붙여 넣을게. §9에 기록해줘.` + Judge 출력 |
| S4 첫 조정 | Opus · xhigh | `P4 로드맵 §4 S4대로 병합 확인, VM 사전 확인, 첫 조정을 진행해줘. Judge PASS 커밋 <ID>.` |
| 매번 조정 | Sonnet · medium | `조정 확인해줘.` |
| S6 H1 | Sonnet · medium | `P4 로드맵 §4 S6 H1대로 현황판에 상태 한 줄을 넣어줘.` |
| G3 판정 | Sonnet · high | `P4 로드맵 §4 S5의 G3 판정을 하자. 파일럿 평가는 #1 <평가>, #2 <평가>.` |
| S8 착수 전 갱신 | Opus · xhigh | `P4 로드맵 부록 A7·A8을 지금까지 결과에 맞게 갱신해줘.` |

---

## 근거 파일

- **설계·결정:** `docs/claude/system-review-p3-design-2026-09-30.md`(§2, §4~8, §10~12), `docs/claude/system-review-phase1-2026-09-30.md`(§1-2, §1-3, §7-3), `docs/claude/handover-system-review-2026-09-30.md`, `docs/claude/trading-skill-materials-review-2026-09-30.md`(시장 환경 메모·대기 항목)
- **실행 환경:** `CLAUDE.md`(Hard safety, Change classes, Working rules, Session hygiene), `AGENTS.md`(35), `.claude/settings.json`(permissions, `worktree.baseRef`), `.gitignore`(27-37), 투자_V2 Claude 설정 가이드(worktree, `.worktreeinclude`, `/model`, `/effort`)
- **제안·적용 불일치:** `manage-us-stock-strategy/scripts/run_kiwoom_broker_shadow.py`(21-38), `kiwoom_broker_shadow.py`(101-122), `apply_user_confirmed_broker_snapshot.py`(23-86), `validation_common.py`(35-41, 100-108), `kiwoom_account_readonly_bridge.py`(43-46, 84-100)
- **테스트·픽스처:** `tests/test_kiwoom_broker_shadow.py`(56-66), `tests/test_manual_portfolio_analysis.py`(1756, 1807-1827), `tests/test_v2_5_broker_snapshot.py`·`tests/test_v2_6_broker_beginner.py`(추적된 `workspace/outputs/v2_5_shadow/` 픽스처), `tests/test_k2_evidence_contract.py`, `tests/test_k2_bridge_evidence_integrity.py`, `tests/test_v2_6_4_kiwoom_adapter.py`, `tests/test_broker_visibility_audit.py`, `docs/claude/test-run-latest.md`
- **거버넌스:** `docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md`(§2-1 고정 16개, 진행 기록: worktree 줄바꿈, VM 커밋 잠금 파일)
- **범위·원장:** `workspace/policies/kiwoom-session-aware-priority-policy.json`(ticker 15개), `workspace/state/continuous_improvement/`(git 추적 12개)
- **키움 스펙:** ust21070(미국주식 원장잔고확인) 응답 필드 표와 응답 예시
- **git 상태(2026-09-30):** 브랜치 `codex/master-recovery-expansion`, HEAD `a453755`, 미추적 docs 3개, `.worktreeinclude` 없음
