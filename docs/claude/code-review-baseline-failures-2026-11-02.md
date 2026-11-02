---
id: code-review-baseline-failures-2026-11-02
title: "개발 큐 기준선 남은 실패 29건 원인 분류 (읽기 전용)"
date: 2026-11-02
status: "읽기 전용 분류 — 코드·설정·정책·예약 변경 없음. 시험 실행 없음(기존 기준선 기록만 읽음)"
source: "workspace/outputs/dev-runs/_baseline/d88e88fe…-py3.13.15-b2.json·.full.err (computed 2026-11-02 13:32 KST, ran 3497, 실패 20·오류 9, added 0, prev_base 751549f3), 사장 카드 '기준선 실패 29건 분류'(2026-11-02 18:37 KST)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음"
---

## 한 줄 결론
29건은 코드 결함이 아니라 **시험 환경 차이 3가지**에서 나온다. ① 기준선 worktree가 파일을 CRLF로 바꿔 원본 바이트 해시가 어긋남 16건 ② git에 없는 로컬 산출물 파일을 읽음 11건 ③ docs/claude 자료 2건. 가장 값싸고 효과 큰 수정은 ①(`.gitattributes` 한 줄, K3 경로)이다.

## 분류표

| 묶음 | 건수 | 시험 | 원인 근거 |
|---|---|---|---|
| ① CRLF 변환 | 14 | test_v2_6_7_session_aware_kiwoom_priority (InvariantAndContract 13, PriorityAndScope 1) | 시험 97행이 `workspace/research/provider-evidence/kiwoom/**/*.json`의 **원본 바이트** sha256으로 현재 Acceptance(835d4f46…)를 찾는다. 본 저장소 파일은 LF(`git ls-files --eol` = w/lf)이고 해시가 맞는다. 그러나 확인한 worktree 5곳(core-failclose·state-fixture2·baseline-watch·baseline-sticky·_base-76d34dae)에서는 같은 파일에 CR이 들어가 해시가 0f9b9038…로 바뀐다. `.gitattributes`의 `-text`는 `workspace/calendar-authority/artifacts/**`·`workspace/instrument-identity-authority/artifacts/**`만 덮는다(56770fc). |
| ① CRLF 변환(추정) | 2 | test_instrument_identity_authority test_15(VERIFIED 기대 → NOT_VERIFIED), test_materialize_instrument_identity_artifact test_candidate_support…(UNKNOWN_SYMBOL 기대 → INTEGRITY_FAILURE) | 실제 신원 등록부를 읽는 시험이다. worktree와 본 저장소의 바이트가 다른 파일은 `workspace/instrument-identity-authority/source-packets/*/…sources.json` 3개와 `workspace/policies/instrument_identity_activation.json`이다(-text 범위 밖). 무결성 검사가 정확히 어느 파일에서 깨지는지는 **확인 필요**. |
| ② git 밖 파일 | 8 | 오류: test_holding_baseline_observation_audit(setUpClass), test_mvll_canonical_volume_lineage(setUpClass), test_provider_limitation_audit(setUpClass), test_nbis_v3_shadow_activation 1, test_nbis_v4_kiwoom_price_authority 2, test_portfolio_decision_order_intent 1(lmt), test_validate_research_packet 1 | 모두 FileNotFoundError. 읽는 파일 7개(2026-08 날짜의 `workspace/outputs/activation/…`·`workspace/outputs/portfolio-strategy/2026-08-13/…`·`workspace/outputs/lmt-instrument-registry-candidate-prep/…`·`stock-strategy-system/market_snapshot.example.json`)는 회사PC 디스크에는 있으나 git 추적 밖이다. `workspace/outputs/activation/`은 .gitignore 17행. |
| ② git 밖 파일 | 2 | test_materialize_kiwoom_session_aware_acceptance_candidate test_05(오류)·test_12(실패) | 검증기(validate_kiwoom_session_aware_acceptance_candidate.py 277~288행)가 manifest의 source_artifacts 9개를 찾는다. 9개 모두 `workspace/outputs/activation/…`(git 밖)이라 "source artifact missing". |
| ② git 밖 파일 | 1 | test_portfolio_decision_dashboard test_real_historical_grade_b_fixture… | 1504행 `fixture.is_file()` 거짓. 이미 알려진 건(P-1). |
| ③ 문서 자료 | 1 | test_scheduled_prompt_kiwoom_profile test_all_scheduled_prompts… | 시험이 `docs/claude/scheduled-prompts/**/*.txt` 전부를 지시문으로 본다. `pending-cardreuse/diff-v3.2-v3.3.txt`(698baf2, 2026-10-17 23:30 KST)는 비교용 diff인데 kiwoom_query 글자가 있고 profile·mode 줄이 없어 걸린다. |
| ③ 문서 자료 | 1 | test_auto_core_decide RegistryTests (symbol='PLTR') | 등록부(card-evidence-registry.json)의 PLTR `section_sha256`(754e8b5c…)이 카드 문서 절 해시(지금 5217243c…)와 다르다. 카드 문서와 등록부 해시 모두 698baf2 이후 바뀐 적이 없으니 **등록할 때부터 어긋났다**. 원인은 **확인 필요**. 함께 나오는 CARD_NOT_ACCEPTED_IN_WATCHLIST는 PLTR이 관심 명단 members가 아니라 candidates에 있어서이고 정상이다. |

합계 16 + 11 + 2 = 29. 이번 기준선의 added_failures는 0이다(새로 깨진 것 없음).

## 언제부터
- ① v2_6_7 14건은 캐시에 남은 가장 오래된 기준선(2026-10-12 KST)부터 계속 있다. 신원 2건은 10/27 이후 모든 기준선에 있다(그 전은 확인 필요).
- ③ 두 건은 698baf2(2026-10-17 23:30 KST) 뒤부터다.

## 실제 운영 영향
- ①·②: 본 저장소(자동 코어가 도는 곳)에서는 파일이 LF이고 로컬 파일도 있다. 그러니 **운영 판정에는 영향이 없을 것**이다. 다만 본 저장소에서 이 시험들이 실제로 통과하는지는 이 스레드가 시험을 돌리지 않아 **확인 필요**.
- 대신 개발 큐는 이 시험들로 회귀를 못 잡는다. 키움 우선순위·종목 신원 권한 시험 16건, setUpClass 오류로 통째로 빠지는 3개 클래스(시험 메서드 22+3+4 = 29개, 실패 수에는 3건으로만 잡힘)가 여기에 해당한다.
- ③ PLTR: 자동 코어는 보유 종목과 members만 검사한다(auto_core_decide.py 677~678행). PLTR은 candidates라 지금은 영향이 없다. 그러나 PLTR이 members로 편입되면 그날 PLTR 매수는 CARD_SECTION_CHANGED로 막히고 "Cowork 등록부 확인" 예외가 1회 뜬다. 매수를 막는 쪽(fail-closed)이다.

## 고칠 것 (제안, 사장 결정 전)
1. **① `.gitattributes` 보강 (추천 1순위)**. `workspace/research/provider-evidence/** -text`, `workspace/instrument-identity-authority/** -text`를 넣고, 필요하면 원본 바이트로 해시되는 policies 파일도 넣는다. `.gitattributes`는 보호 이름(devpipe.py 121~123행)이라 **K3 수동 경로**다(선례 56770fc). 본 저장소 파일은 이미 LF라 바뀌지 않는다. 기대 효과는 기준선 실패 16건 감소다(확인 필요: 신원 2건). 되돌리기는 커밋 1개 revert.
2. **③-a diff 파일 정리**. diff 파일을 `.txt`가 아닌 이름으로 바꾸거나 scheduled-prompts 밖으로 옮긴다. docs/claude 변경이지만 이름 바꾸기는 삭제 권한이 필요하다. 그래서 사장 OK 뒤 한다. 1건 감소.
3. **③-b PLTR 등록부 해시**. 등록부는 권한 경로다. 어긋난 원인을 먼저 확인해야 한다. 그다음 Cowork 등록부 갱신과 사장 결정으로 고친다. PLTR이 members로 편입되기 전에만 하면 된다.
4. **② 로컬 산출물 의존 11건**. state-fixture2처럼 시험 전용 fixture로 바꾼다. 다만 원본에 계좌 보유·평가 값이 들어 있을 수 있다(특히 holding-valuation·broker 계열, **확인 필요**). 그래서 원본 복사는 하지 않고 합성 fixture로만 만든다. 파일이 여럿이라 작업이 가장 크다. test_portfolio_decision_order_intent는 권한 경로라 authority 작업이 된다.

## 범위 밖
- `.worktreeinclude`는 Builder worktree에 `stock-strategy-system/portfolio_state.json`·`alert_runtime_state.json`을 복사한다. 그래서 ②를 그 목록에 더하는 방법은 P-1(실제 상태 의존)을 되살린다. 추천하지 않는다.

## 갱신 (2026-11-02 19:3x KST, gitattr-bytes 병합 뒤)
- ① 수정 병합: 52bbe81(2026-11-02 19:28:56 KST). 이 병합으로 16건 중 **14건만** 회복했다. 다음 기준선의 예상 실패는 15건이다(29 − 14). 회사PC git 설정은 `core.autocrlf=true`로 확인됐다(실행 스레드 보고).
- **새 묶음 ④ 옛 구현 해시 요구 2건**:
  - 시험: test_v2_6_7 `test_extended_provider_scope_candidate_validates_without_activation`(310행), `test_guarded_priority_requires_locked_acceptance_manifest`(425행).
  - 원인: 두 시험은 검증기 결과가 `[]`이기를 기대한다. 그런데 검증기가 현재 Acceptance(835d4f46, 2026-10-07)에 적힌 구현 파일 해시를 아직 대조하고, 그 뒤 바뀐 구현 파일 10개가 `implementation hash mismatch`로 나온다(validate_kiwoom_session_aware_acceptance.py 76행, …_candidate.py 262~275행). 본 저장소도 같다.
  - 규칙과 어긋남: CLAUDE.md 83~86행에 따르면 키움 acceptance pin은 T1(510961a, 2026-10-10)로 폐지됐다. 구현 파일을 고쳐도 acceptance가 무효가 되지 않는다. 시험과 검증기는 폐지 전 기준에 머물러 있다.
  - 운영 영향: 이 검증기는 Acceptance 후보 만들기 스크립트와 시험에서만 부른다. 자동 코어와 예약 지시문에서는 부르는 곳이 없다(grep). 그래서 운영 판정 영향은 없을 것이다(확인 필요: 다른 수동 절차에서 쓰는지).
  - 고치는 법(안): 두 가지 중 하나다. (가) 검증기가 pin-scope `status=RETIRED`이면 구현 해시를 대조하지 않게 한다. (나) 두 시험이 구현 해시 어긋남은 따로 다루게 한다. 둘 다 기존 검사나 단언을 풀어 주는 쪽이라 사장 결정이 먼저 필요하다. 바꿀 파일(검증기·시험)은 authority-paths.txt에도 보호 경로에도 없다. 그래서 결정 뒤에는 개발 큐 일반 작업으로도 갈 수 있다(K3가 꼭 필요한지는 확인 필요).
  - 판단: 운영 영향이 없고 2건뿐이라 급하지 않다. ②(로컬 파일 11건) 정리 때 함께 다루는 것을 추천한다.
