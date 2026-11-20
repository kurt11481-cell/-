---
id: cowork-to-room-k3-judge-prompt
title: "cowork-to-room-k3 Judge (읽기 전용, Opus · xhigh)"
date: 2026-11-20
class: "K3 수동 경로 Judge — 파일을 고치지 않는다. 이 지시문은 Builder 지시문을 쓴 세션과 다른 세션(사장실 'K3 검사 기준 쓰기' 스레드)이 썼다"
source: "docs/claude/cowork-to-room-k3-proposal-2026-11-20.md(2판, 0·2·3·4·8·9절) · docs/claude/cowork-to-room-k3-builder-prompt.md · CLAUDE.md 18~45·60~82·99~103·116·119·129~133행(기준 HEAD 22d44cf)"
---

# 할 일
Builder 브랜치 `worktree-cowork-to-room-k3`(기준 22d44cf)의 변경을 J1~J12로 하나씩 판정한다.

판정 대상 고정:
- 먼저 `git merge-base 22d44cf worktree-cowork-to-room-k3`가 22d44cf인지 확인한다(아니면 전체 FAIL).
- 판정은 `git rev-parse worktree-cowork-to-room-k3` **한 커밋**에 대해서만 한다. Builder worktree에 추적 파일의 커밋 안 된 변경이 있으면 전체 FAIL(병합되는 것은 커밋뿐). 시험도 그 커밋의 깨끗한 트리에서 돌린다.
- 보고 끝에 "이 판정은 커밋 <해시>에만 유효, 이후 커밋이 있으면 다시 판정"을 적는다.

읽을 것: 수정안 전문, Builder 지시문, `docs/claude/cowork-to-room-k3-report.md`, `git diff 22d44cf..<판정 커밋>`, CLAUDE.md 원문. Builder 보고서는 길잡이일 뿐 증거가 아니다. 모든 판정은 원문 행(파일:행)이나 이 세션에서 직접 돌린 시험 출력으로 단다. 확인 못 한 것은 "확인 필요"로 적고, 그것에 기대는 항목은 FAIL 쪽으로 판정한다(fail closed).

판정: 항목마다 PASS / FAIL + 근거. FAIL이 하나라도 있으면 전체 FAIL. 수정안 8절에 따라 FAIL이 R1(대조 스레드 apply)에만 걸리면 "R1만 FAIL — R2·R3·R4 판정 별도"로 따로 적는다. J별 R 대응: J2·J4·J5·J9·J12 = R1·R2, J3·J8 = R2, J7 = R3, J10 = R1·R3·R4, J1·J6·J11 = 전체.

# 판정 항목

**J1 범위·삭제 문장.**
- 바뀐 파일이 Builder 지시문 '바꿀 파일' 목록, 보고서, BLOCKED 문서, 그리고 J11의 propose 호출부 `--journal` 추가에 필요한 기존 시험 파일(예: tests/test_cash_flow_evidence.py)뿐인가.
- `.claude/**`, `stock-strategy-system/**`, `workspace/policies/**`, `auto_core.py`, `tools/**`, AGENTS.md, `.gitignore` 변경 0. 스키마는 description만, enum(29행 근처) 불변.
- `git diff -U0 22d44cf..<커밋> -- CLAUDE.md`의 **삭제 줄을 전부 나열**해, 지워진 안전 문장마다 같은 뜻이나 더 좁은 뜻으로 다시 들어갔는지 대조한다. 특히 "never type or guess the code or reuse one"(26~27행), "Before applying, read … broker-snapshot-reconciliation.md"(27~28행), "Never apply for a decision the user did not state"(34행), "One decision covers only the immediately preceding proposal, the same day, once"(39행), 확인이 아닌 것 목록(40~42행). CLAUDE.md 18~24행·43~45행과, 25~42행·116행 근처 밖의 변경은 0.

**J2 카드 탭은 대조·S5 일지 확인이 아님.**
- (a) CLAUDE.md 새 문장이 대조 `확인 <code>`와 line_review_completed·peak_review_card_completed를 **사장이 그 스레드에 직접 친 메시지만**으로 한정하고, 결정 카드 탭을 명시적으로 제외하는가.
- (b) 기존 S7b 카드 항목(card_decision·card_user_decision)의 카드 탭 인정은 그대로인가(넓히지도 좁히지도 않음).
- (c) 확인이 아닌 것 목록(코디네이터·다른 Claude 인용, 다른 스레드·전날 카드, Claude가 닫은 카드, 요약, 예약 턴)이 대조 쪽에도 빠짐없이 있는가.
- (d) CLAUDE.md 밖 문구가 같은 뜻으로 일치하는가: 참조 문서 broker-snapshot-reconciliation.md 2절의 새 스레드 갈래와 155~160행, reconcile_broker_state.py 머리말(7~10행 근처)·help(524행 근처), portfolio_review_journal.py 머리말(15~22행 — 지금 "typed the decision or tapped that thread's decision card … (no code)"), 스키마 description, 로캘, CLAUDE.md 116행 추가 문장, portfolio-exposure-review.md. 한 곳이라도 대조나 새 S5 두 종류에 탭 허용이나 '(no code)'가 걸리게 읽히면 FAIL.
- (e) 스크립트는 탭과 입력을 구별하지 못한다는 한계가 수정안 3절대로 보고서에 적혀 있는가(기록 확인, FAIL 사유 아님).

**J3 S5 활성 기록 제외.**
- s5_activation은 PROJECT_THREAD로 apply(556~558행 근처)와 체인 재검사(`_entry_inconsistency`, 187~191행 근처) 둘 다에서 `PROJECT_THREAD_ENTRY_TYPE_INVALID`인가.
- 허용 목록이 정확히 card_decision·card_user_decision·line_review_completed·peak_review_card_completed 4종인가. 명시 목록이어야 하고, `S5_ENTRY_TYPES` 전체처럼 나중에 생길 종류가 자동 허용되는 형태면 FAIL.
- 손으로 넣은 s5_activation PROJECT_THREAD 항목이 verify에서 잡히는지 시험 출력으로 확인(T8).

**J4 4칸 + 4번째 칸 코드.**
- (a) 형식 검사·4번째 칸 코드 검사가 validation_common.py 한 곳에 있고, 대조 라이브러리와 일지가 같은 함수를 import하는가(복사본 없음). apply_user_confirmed_broker_snapshot.py가 portfolio_review_journal을 import하지 않는가(reconcile_broker_state.py의 기존 user_terminal_rejection import는 그대로 허용).
- (b) 대조 `apply_confirmed` 안(CLI 아님)에서 PROJECT_THREAD일 때 4번째 칸(`split('|', 3)[3]`)만 보고 코드를 찾는가. 1·2·3칸에만 코드가 있으면 거부(T15).
- (c) 새 S5 두 종류도 4번째 칸 코드 필수, 카드 항목은 코드 요구 추가 없음(T9).
- (d) 대소문자·공백 규칙이 기존 `proposal["confirm_code"] in message.upper()`보다 느슨해지지 않았는가.
- (e) 3칸 이하·빈 칸·공백만 있는 칸·2칸 `user_` 없음·3칸 `KST` 끝 없음이 거부되는가(T3). 4번째 칸 안의 추가 `|`는 현행 규칙(portfolio_review_journal.py 244~246행 `split("|", 3)`)대로 허용이며 거부를 요구하지 않는다. 앞 칸에 `|`를 끼워 칸을 밀어도 2·3칸 검사로 거부되는지만 본다.

**J5 기존 경로 불변.**
- 다음이 diff에서 바뀌지 않았는가: COWORK_CHAT_USER_MESSAGE·USER_TERMINAL의 코드 검사(apply 277~281행), USER_TERMINAL의 user_terminal_rejection(reconcile 339~344행), reconcile 362행 코드 대체(USER_TERMINAL만), AUTO_CORE_INVARIANTS 경로(apply_auto_core·auto_core.py 409~410행), 15분 만료(T20), 일지 1시간 만료·해시 체인.
- 기존 시험의 **단언 변경**은 test_auto_core.py 1056·1059행 기대 튜플(새 방법 추가)뿐이어야 한다. propose 호출부에 임시 `--journal` 인자를 더하는 것은 단언 변경이 아니며 허용. `git diff 22d44cf..<커밋> -- manage-us-stock-strategy/tests`에서 삭제·완화된 assert를 전부 나열해 0인지 확인.
- T16(PROJECT_THREAD 4칸 메시지를 COWORK 방법으로 넣으면 현행대로 통과)이 시험으로 기록되어 있는가.

**J6 병합·정책·권한이 새로 생기지 않음.**
- diff 전체에서 0건이어야 하는 것: dev-merge·dev-run·dev-queue·-ApproveAuthority 허용 문장, 정책 파일(alert_policy.json·workspace/policies/*)·decision_mode·order_authority·quantity_authority·한도·주문 도구 관련 새 허용, auto 경로·불변식 I1~I5 변경, `.claude/settings.json` 변경.
- CLAUDE.md 새 문장이 "사장실 스레드는 PROJECT_THREAD_USER_DECISION만 쓰고 COWORK·USER_TERMINAL 방법으로 apply하지 않는다"와 "Codex·예약 LLM·Judge·하위 에이전트·다른 Claude Code 세션은 apply하지 않는다"를 담는가.
- Change classes 절(60~82행)과 Session hygiene 129~133행이 바뀌지 않았는가.
- 새 예외가 '사장실 회사PC 스레드(대화형 프로젝트 스레드)'에만 걸리고, 일반 Claude Code 세션이나 Cowork 하위 작업자로 번지는 문구가 없는가.

**J7 R3 propose 거부.**
- 일지 판정이 **키움 reader 생성·호출 전**에 일어나는가(코드 순서 + T10·T12에서 reader 호출 수 0).
- MISSING = 활성 없음(T18, 조회 1회), CORRUPT·읽기 오류 = 거부(T12), 활성 + 증거 없음 = `CASH_FLOW_EVIDENCE_REQUIRED_AFTER_ACTIVATION`·종료 2·출력 폴더와 상태 불변(T10), 활성 + 증거 = 지금과 같음(T13).
- 거부 판정이 `load_journal`의 status와 `journal_view`의 status **둘 다**를 보는가. journal_view는 load_journal이 OK여도 스스로 CORRUPT(예: MULTIPLE_S5_ACTIVATION_ENTRIES, S5_ACTIVATION_ENTRY_INVALID)를 내며 activation=None을 돌려준다(portfolio_exposure.py 573~581행). 이때를 "활성 없음"으로 통과시키면 FAIL(auto 경로 456행의 `.get("activation") or {}`를 그대로 베낀 경우).
- `--journal` 기본값이 auto 538행 기본값과 같은 경로인가. auto 경로 결과가 바이트 단위로 불변(T14).
- 남는 위험(FAIL 사유 아님, 판정 표에 'R3 우회 가능 여부'로 기록): `--portfolio-state`가 기본 실제 경로인데 기본이 아닌 `--journal`(없는 경로 등)을 넘기면 MISSING으로 증거 없이 제안이 만들어지는지. 거부되거나 제안·show에 일지 경로가 드러나는지, 아니면 문서 규칙("스레드·Cowork는 propose에 `--journal`을 넘기지 않는다")만 있는지, 셋 다 없는지를 적는다.

**J8 R2가 S7 멈춤 해제에 미치는 영향.**
- line_review_completed·peak_review_card_completed는 portfolio_exposure.py 587~588행(journal_view)에서 confirmation_method를 보지 않고 읽힌다. 따라서 스레드 기록 1건이 S7 pauses를 풀 수 있다. 이 범위가 수정안 0절 R2·2-2절과 같은가.
- confirmation_method를 읽는 다른 소비자(`grep -n confirmation_method` — manage-us-stock-strategy/scripts 안 파일들과 docs/claude/*.py, 저장소 전체 검색은 하지 않음)가 새 값으로 깨지거나 다르게 동작하지 않는가.
- T17: 새 두 종류 기록 뒤 load_journal OK, journal_view activation_date 불변.

**J9 상태 파일 쓰기 (Windows 파이썬 vs 회사PC VM 리눅스 파이썬).** 스레드 apply는 VM 리눅스 파이썬(device_bash)으로 Windows 저장소의 연결 폴더 파일을 쓸 수 있다.
- (a) 상태를 담는 4종의 쓰기 줄이 diff에서 바뀌지 않았는가: portfolio_state.json(apply 98~109·321·349행, 기존 줄바꿈 유지), reconciliation_ledger.jsonl(apply 79~95행, 바이너리 추가), backups, decision_journal.json(일지 477~488·598행, 사람 apply는 기본 newline="\n"로 항상 LF). 바뀌었으면 newline 명시나 바이트 쓰기인지 확인. apply_audit(357행)·제안 파일(validation_common.py write_json)의 플랫폼 줄바꿈 차이는 기록만 하고, 어떤 해시에도 들어가지 않는지 확인.
- (b) 원장 체인은 줄 원시 바이트 sha256(apply 62~68·79~85행)이고 `splitlines()` 읽기·`b"\n"` 추가가 불변인가. 상태 해시와 일지 체인은 canonical JSON 기준인가(불변 확인).
- (c) 경로: REPO_ROOT·`DEFAULT_PORTFOLIO_STATE_PATH` 비교(reconcile 352~357행)가 VM 경로(`/sessions/.../mnt/코덱스저장소`)에서도 같은 파일을 가리키는지 코드로 판단.
- (d) 반쪽 적용 위험: 쓰기 순서는 백업 → 원장 추가 → 상태 교체(apply 323~349행)이고, 교체는 mkstemp → replace → unlink다(apply 98~109행, 일지 477~488행). VM 연결 폴더는 삭제가 기본으로 막혀 있어, 덮어쓰기 replace가 실패하면 원장만 쓰이고 상태는 안 바뀌어 `STATE_CHANGED_OUTSIDE_LEDGER`로 이후 apply와 자동 코어 I4가 멈출 수 있다.
- 판정: Judge는 VM 파이썬을 돌릴 수 없다. 연결 폴더 안 임시 폴더에서 VM 파이썬으로 한 T1형 대조 apply와 일지 apply의 출력(덮어쓰기 replace·fsync 성공, .tmp 잔여물 없음, 원장·상태 일치)이 보고서에 원문으로 없으면 '확인 필요'다. 이 경우 CLAUDE.md와 참조 문서에 "사장실 스레드의 apply는 Windows 파이썬(Desktop Commander)으로만 실행" 한정 문장이 있어야 J9 PASS, 없으면 J9 FAIL(R1·R2). 코드 읽기만으로 "한정 문장이 필요 없다"고 결론 내지 않는다. 한정 문장이 있으면, Desktop Commander 경로가 USER_TERMINAL 방법을 쓰지 않는다는 문장(J6)과 충돌하지 않는지도 본다.

**J10 문서 사실성.**
- broker-snapshot-reconciliation.md 159~161행 근처 정정이 settings.json 26~27·44~55행과 맞는가(apply deny는 Bash·PowerShell 도구만, PreToolUse 훅 매처는 device_bash·start_process·interact_with_process에도 걸림). 훅 본문(.claude/hooks/kiwoom_order_block.py)이 무엇을 막는지는 읽어 확인하고, 프로젝트 스레드에서 deny·훅이 실제 발동하는지는 수정안 9절대로 미확인이므로 정정 문장이 이를 단정하면 '확인 필요' 표기를 요구한다.
- 4절 R3 문구("활성 뒤 필수")가 코드와 맞는가. 로캘 5·6·51행과 R3 거부 문구가 있고 JSON이 유효한가.
- R4 한 줄의 기록일 조건이 auto_core_reconcile.py 171~174·198~209·883행 근처(record_time 정의 173행, plan_reads 200~209행)와 뜻이 맞는가.

**J11 시험 재현.** 이 세션에서 직접 돌린다. `__pycache__` 쓰기를 피하려고 `-B`를 붙이고, auto_core.py라는 글자가 든 명령은 막히므로 `-p "test_auto_core*"`로 따로 돌린다.
- `python -B -m unittest discover -s manage-us-stock-strategy/tests -p "test_cowork_to_room_k3.py" -v` → T1~T20이 모두 있고 PASS. T번호 ↔ 시험 이름 대응표를 보고서와 대조(빠진 T번호가 있으면 FAIL).
- 대상 파일: test_reconcile_broker_state·test_approval_human_check·test_cash_flow_evidence·test_portfolio_review_journal·test_decision_journal_cards·test_run_portfolio_exposure_review, 그리고 `-p "test_auto_core*"`.
- 전체: `python -B -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"`.
- 기준 비교: 본 저장소 HEAD가 22d44cf이고 `git status --porcelain -- manage-us-stock-strategy CLAUDE.md`가 비어 있을 때만 거기서 같은 명령으로 기준을 잰다. 아니면 '기준 재측정 확인 필요'로 적고 Builder 보고서 수치를 참고로만 쓴다. 비교는 실패 수가 아니라 **실패한 시험 이름의 집합**으로 하고, 새로 실패한 이름이 0이어야 한다.
- **기본 일지 의존 검사(시험 통과만으로 판정 금지)**: `stock-strategy-system/decision_journal.json`은 .gitignore 53행으로 무시되어 worktree에는 없다. 그래서 worktree에서는 기본 `--journal`이 MISSING(활성 없음)이 되어 기존 시험이 통과해도, 병합 뒤 본 저장소에서는 실제 일지를 읽어 결과가 바뀔 수 있다. tests 폴더에서 `"propose"`를 부르는 모든 곳(기준: test_approval_human_check.py:266, test_cash_flow_evidence.py:312, test_reconcile_broker_state.py:848·886·952)과 새로 생긴 곳을 나열해, 각각 임시 `--journal`을 넘기거나 일지 판정 전에 끝나는지 코드로 확인한다. 하나라도 기본 경로에 기대면 FAIL.
- 시험이 실제 파일을 건드리지 않았는지: 본 저장소의 portfolio_state.json·reconciliation_ledger.jsonl·decision_journal.json·backups의 mtime과 개수를 시험 전후로 비교(내용은 읽지 않음), Builder worktree `git status --porcelain` 전후 동일.

**J12 반대 시험의 실효.**
- T2·T3·T4·T7·T8·T10·T12·T15·T20이 거부 사유 문자열까지 단언하는가(예외가 났다는 것만 보면 FAIL).
- T19가 "형식만 맞춘 위조는 통과한다"를 명시적으로 기록하는가.
- 스레드 방법 4칸 검사가 CLI뿐 아니라 apply_confirmed 직접 호출로도 시험되는가(T3).

# 추가로 볼 것 (FAIL 사유는 아니고 보고서에 적음)
- 수정안 9절 확인 필요 3개와 USER_TERMINAL 대화형 프로세스(Desktop Commander) 통과 여부를 Builder가 그대로 옮겼는가.
- 병합 뒤 사장이 고칠 프로젝트 지침 3·4절 문장이 수정안 2-3절과 같은가. J9 한정 문장이 들어갔으면 지침 3절 문장에도 같은 한정이 필요하다고 적는다(이 Judge는 지침을 고치지 않는다).

# 금지
- 파일 쓰기·고치기·커밋(이 지시문, 보고서, worktree 포함), `git worktree add`·checkout·switch.
- 주문·키움 도구(kiwoom_* 전부), reconcile apply·propose·auto 실행, 일지 apply, auto_core.py 실행.
- .env·토큰·계좌번호 읽기. 실제 stock-strategy-system 파일은 존재·mtime·개수 확인만 하고 내용 읽기·쓰기 금지.
- 관제판 갱신, dev-run·dev-merge·dev-queue.

# 보고
한국어. 판정 표(J1~J12 | PASS/FAIL | 근거 파일:행 또는 시험 출력 | FAIL이면 고칠 것 1줄), 기준·이후 실패 시험 이름 집합, 'R3 우회 가능 여부'(J7), 확인 필요 목록, 판정 대상 커밋 해시와 유효 범위 문장. 보고 마지막 비지 않은 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL`.

# 작성 기록
Fable 조언 1회(추론 노력 high): 지적 8건 모두 원문으로 확인 후 반영(.gitignore 53행, 테스트 propose 호출 5곳, 일지 598행 LF 고정, apply 357행 audit, 원장 원시 바이트 체인 62~68행, journal_view 573~581행 CORRUPT). 4번 (b) 'R3 우회'는 수정안에 없는 요구라 FAIL 사유 대신 남는 위험 기록으로 둠.
