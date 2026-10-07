---
id: kiwoom-repin-judge-report-2026-10-07
type: judge-report
status: current
as_of: 2026-10-07
summary: 키움 acceptance 재고정 후보 835d4f46… 독립 Judge 결과(PASS-WITH-CONDITIONS). 사용자가 Cowork에 붙여 넣은 Judge 최종 보고 원문 그대로.
consumers: [s-token-repin 활성화 단계(8절 8~11), kiwoom-repin-candidate-report-2026-10-07.md 8절, 개발 관제판 s-token-repin]
---

# 키움 acceptance 재고정 후보 Judge 보고 (2026-10-07, 별도 Claude Code 세션, Windows)

지시문: `kiwoom-repin-judge-prompt-2026-10-07.md`. 아래는 Judge 최종 메시지 원문이다(Cowork가 편집하지 않음). 조건 처리 기록은 `kiwoom-repin-candidate-report-2026-10-07.md` 8절.

---

판정: PASS-WITH-CONDITIONS

후보 835d는 Windows에서 다시 만들어도 같은 바이트가 나오고, 내용과 권한 필드가 맞습니다. sim 사본 모의에서 새 실패는 0건이고 v2_6_7 acceptance 2건은 해소됐습니다. 조건은 두 가지입니다: 적용 도구의 -O 실행 시 검사가 빠지는 문제, 그리고 8→9번을 어떤 환경에서 어떤 순서로 실행하느냐입니다.

0. 범위
- 이번 단계의 새 파일은 후보 1개, repin_apply.py, kiwoom-repin 문서 2개뿐입니다(15:29~15:48). 오늘 그 앞의 변경은 docs만 있고 코드·정책·상태는 없습니다.
- 고정 27개 경로, workspace/policies, workspace/state, stock-strategy-system은 HEAD(332a11c)와 diff 0입니다.
- 정책 두 파일은 45cf를 17곳에서 가리킵니다(priority 소문자 15·대문자 1, source 대문자 1, 대소문자 섞인 것 0). 835d는 0곳입니다.

1. 후보 파일: sha 835d4f46…429c, 10077 B, LF 1, CR 0, BOM 없음. 후보 검증기를 원본에서 -B로 다시 돌린 결과 PASS, errors []입니다.

2. 결정성: Windows Python 3.13.15에서 build_candidate_manifest를 메모리 안에서 호출했습니다. 반환 바이트가 후보 파일과 같고 sha도 835d4f46…입니다. 다른 키는 없습니다.

3. 내용
- implementation_hashes 키는 pin scope 27개와 정확히 같고, 27개 값이 모두 현재 정규화 해시와 같습니다. 332a11c(HEAD)의 blob 27개도 정규화 기준으로 같습니다.
- 45cf 대비 바뀐 구현 해시는 kiwoom_runtime_bridge.py와 kiwoom-acceptance-pin-scope.json 2개뿐입니다. predecessor_implementation_drift도 정확히 이 2건이고, pinned 값은 45cf 값, current 값은 현재 값입니다. supersedes_acceptance_sha256는 45cf…입니다.
- 그 밖에 바뀐 키는 모두 설명됩니다:
  - generated_at, repository_base_commit(48798d1→332a11c)
  - 정책 해시 a3d2→d315, 등록부 해시 19e9→351a: 706c940(R9 활성화) 전후 커밋의 해시와 그대로 일치합니다.
  - active manifest f0bab→45cf, pin scope 해시 8f3e→c024
- source_artifacts와 invariants는 바뀌지 않았습니다.
- 바인딩 4개와 pin scope 해시는 현재 정규화 해시와 같습니다. provider_scope 15종목과 순서는 정책과 같습니다.
- 권한: order_authority false, quantity_authority none, execution_quantity null, activation_performed false, candidate_status INACTIVE_SUPERSEDING_CANDIDATE.

4. 적용 도구: 같은 대소문자 64자 치환, 개수 15+1 / 0+1 = 17, 새 해시 사전 0곳, 크기·CRLF·LF·BOM 불변, JSON 경로 diff 개수, 권한 필드 불변을 단언합니다. --apply가 없으면 쓰지 않고(sim에서 확인), 쓰기 직전에 파일을 다시 읽어 비교합니다. 빠진 점은 아래 발견 1~3입니다.

5. 사본 모의 (scratch)
- base·sim의 추적 파일 1084개가 원본과 원시 바이트까지 같습니다. 누락 0, status 1028줄 동일.
- sim에서 적용 도구 APPLIED 17. 적용 전 카운터는 모두 0이었고, 이관 결과는 COHORT_SUPERSEDED_AND_ZERO_INITIALIZED(a0d3e69e…→2acacfbb…)입니다.
- 운영 검증기: sim에서 835d는 PASS(오류 0), 45cf는 FAIL(포인터 17 + 드리프트 2 = 19). 참고: 현재 운영 상태인 base에서도 45cf는 이미 FAIL입니다(드리프트 2).
- shadow_progress.json은 922 B, CRLF 28, LF만 있는 줄 0입니다. 보관 파일은 CRLF 36, reason SESSION_AWARE_KIWOOM_PROVIDER_AUTHORITY_CHANGE, 이전 카운터 0입니다.
- base·sim 전체 트리(__pycache__ 제외) 차이는 정책 2개, shadow_progress.json, 보관 파일 1개뿐입니다.
- 대상 테스트: base는 v2_6_7에서 FAIL 2건(acceptance)이고 나머지 OK입니다. sim은 5개 모두 OK입니다(42/26/15/3/8). 스키마 감사는 둘 다 PASS입니다.
- 전체 스위트(2521건): base는 failures 135·errors 6, sim은 133·6입니다.
  - base에만 있는 실패: v2_6_7 2건(sim에서 해소).
  - sim에만 있는 실패: 0건.
  - 공통 69건은 모두 test_portfolio_decision_dashboard(NBIS 13≠15, timing NOT_VERIFIED)입니다. 두 사본에서 같으므로 이번 변경과는 무관합니다. 원인은 범위 밖이라 확인 필요입니다.

6. 남은 위험
- (a) 조건 필요. 질문의 전제를 하나 고칩니다. 8~9번 사이에 record_attempt가 돌면 observed_attempts가 1이 됩니다(shadow_acceptance.py:405, :577-582). 그러면 이관은 COHORT_ALREADY_CURRENT가 아니라 CURRENT_SEMANTIC_COHORT_NOT_ZERO로 멈춥니다(migrate…:49-50). fail-closed이고, 이전 카운터가 0이라 잃는 기록은 없으며 보관 파일만 생기지 않습니다. 저장소 안에서 이 CLI를 부르는 예약 설정은 찾지 못했습니다. 저장소 밖 Cowork 예약 설정은 확인 필요입니다. 8→9를 연달아 실행하고 결과를 확인하면 충분합니다.
- (b) 수용 가능. 예약 게이트는 portfolio_decision_dashboard.py:1419의 input_mode == "LIVE_READ_ONLY"에서만 호출됩니다. 수동 경로는 영향이 없습니다. 이 검사(deployment_provenance.py:197-201)는 runtime_repo(clone) 자신의 파일을 비교하므로, 개발 폴더에서 활성화해도 clone은 그대로입니다. clone을 올릴 때 current.json을 새로 만들지 않으면 두 오류로 막힙니다(fail-closed). 이 재생성은 r-sched-b §6 5단계에 이미 들어 있습니다.
- (c) 수용 가능. allowed_drift_for(:372-377)는 835d에 대해 []를 돌려줍니다. 호출처는 materialize :156과 후보 검증기 :546 둘뿐이고, 운영 검증기는 허용 목록을 쓰지 않습니다. sim에서 materialize test_10도 통과했습니다.
- (d) 조건 필요(경미). core.autocrlf=true(Git system gitconfig)이고 .gitattributes는 없습니다. 커밋해도 이 작업 폴더의 LF는 유지되지만, 새 checkout·clone·worktree에서는 CRLF가 되어 원시 해시가 바뀝니다. 운영 코드는 정규화 해시를 쓰므로 영향이 없습니다(validate_…acceptance.py:25, materialize :95). 다만 테스트 helper test_v2_6_7…py:93-94가 원시 file_hash를 써서 0건 매치로 실패합니다. 45cf도 이미 같은 위험을 안고 있습니다.

발견
1. [M] repin_apply.py:48-76 — 검사가 모두 assert라 python -O나 PYTHONOPTIMIZE에서 사라집니다. scratch 미니 사본에서 틀린 old 해시와 비16진 new 값 zz로도 APPLIED 17을 출력하고 정책 16곳을 덮어썼습니다. 최소 조치: 맨 앞에 if not __debug__: sys.exit(2)를 넣고 new를 [0-9a-f]{64}로 검사합니다. 고치지 않을 경우 -O 없이 실행하고 PYTHONOPTIMIZE가 비어 있는지 확인합니다.
2. [L] repin_apply.py:72-76 — 두 번째 파일 재확인이 첫 파일을 쓴 뒤에 있고 쓰기가 원자적이지 않습니다. 중간에 실패하면 포인터가 갈린 상태가 남습니다(검증기가 fail-closed로 잡음). 최소 조치: 쓰기 전에 두 파일을 모두 재확인합니다. 실패하면 git checkout -- <정책 2개>로 복구합니다.
3. [L] repin_apply.py:52-64 — 대소문자 섞인 해시를 세지 않고, 바뀐 경로는 개수만 단언합니다. 현재 대소문자 섞인 것 0곳이고, sim 경로도 15 scopes + acceptance_evidence + providers[7]로 확인했습니다. 수용합니다.
4. [L] migrate_integrated_shadow_cohort.py:30 — newline을 지정하지 않아 OS 줄바꿈으로 씁니다. Windows에서만 CRLF 28이 유지됩니다(sim 확인). 9번은 Windows Python으로 실행하고 실행 후 CRLF 28을 확인합니다.
5. [L] (a)의 경로 — 9번 결과가 COHORT_SUPERSEDED_AND_ZERO_INITIALIZED이고 보관 파일이 있으며 test_provider_authority_change_starts_zero_count_cohort가 통과하는지 확인합니다.
6. [L] (d)의 경로 — 커밋 뒤 git ls-files --eol로 후보가 i/lf w/lf인지 확인합니다. .gitattributes에 workspace/research/provider-evidence/kiwoom/** -text를 넣는 안은 제안만 하고 만들지 않았습니다. 넣는다면 별도 K2/K3 항목입니다.

활성화 전 사용자가 할 일: 발견 1을 고친 뒤 후보를 LF 그대로 커밋해 i/lf w/lf를 확인하고, 8번(확인 모드 → --apply) 직후 9번을 Windows 터미널에서 실행해 cohort·보관 파일·CRLF 28을 확인합니다. 발견 1을 고치지 않을 경우, 커밋 전에 -O 없이 실행하고 PYTHONOPTIMIZE가 비어 있는지 확인합니다.

자기 점검
- Cowork 보고서는 증거로 쓰지 않았습니다. 8·9번 절차가 서로 충돌하지 않는지 대조만 했고, 모든 사실은 파일·코드·재실행으로 확인했습니다.
- 확인하지 못한 것: 저장소 밖 Cowork 예약이 shadow를 기록하는지, Cowork VM의 PYTHONOPTIMIZE 값, dashboard 공통 실패 69건의 원인.
- 원본 폴더 쓰기 0: 15:50 이후 수정된 파일 없음(.pyc 포함), git status 1028줄 그대로, HEAD 332a11c. 키움 접속, 토큰·.env 읽기, 커밋은 하지 않았습니다.