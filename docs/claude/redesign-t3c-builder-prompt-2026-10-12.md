---
id: redesign-t3c-builder-prompt-2026-10-12
title: 재설계 T3c Builder 지시문 — 권한 경로 보강(카드 등록부·auto-core 스키마) + 권한 표지 오탐 줄이기 + CLAUDE.md 키움 승인 고정 문구 정정
date: 2026-10-12
status: 확정(사용자 2026-10-12 "1번 진행")
class: 일반 변경이지만 보호 경로(tools/**, CLAUDE.md) → 수동 경로 — worktree Builder → 별도 Judge 세션 → 사용자 병합
decision: 사용자 2026-10-12 "1번 진행"(T3b 후속 묶음) · 재설계 A5 · 관제판 redesign-t3b 메모 ①·⑧·⑨
base: HEAD 29ad21d · sha256 CLAUDE.md 2d2f914c… · authority-paths.txt b28ab669… · devpipe.py c24ebb1f… · README.md edd6890e… (Builder 시작 때 다시 재서 다르면 BLOCKED.md)
authority: order_authority=false · quantity_authority=none · execution_quantity=null (개발 절차 문서·검사 규칙만. 주문·정책·상태·브로커 무관. 파이프라인이 권한 작업을 "더 잘 잡게" 하는 쪽이며 낮추는 경로는 만들지 않는다)
consumers: T3c Builder(worktree t3c) · T3c Judge · 이후 모든 dev-run · 관제판 redesign-t3c
weekly_user_touch: 이번 1회성 3번(Builder 시작 · Judge 시작 · 병합). 그 뒤 주간 0. 권한 변경 아님 → "권한 변경 1건" 한도 대상 아님.
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: high · 세션: 새 worktree `t3c` · 이유: 보호 경로(파이프라인 판정 규칙) 변경이지만 범위가 좁고 올리기만 하는 변경. Judge는 별도 세션 Opus xhigh.**

## 1. 목표와 완료 기준

| # | 무엇 | 왜 | 고친 뒤(기계 판정) |
|---|---|---|---|
| A | `tools/dev_pipeline/authority-paths.txt`에 `docs/claude/card-evidence-registry.json`과 `manage-us-stock-strategy/schemas/auto-core-*.schema.json` 추가 | T2 병합(756e43e)으로 카드 근거 등록부(주문표 근거)와 auto-core 계약 스키마 7개가 생겼는데, 목록에는 `auto-core-config.schema.json` 1개뿐. 지금은 주문표 근거·연구 기록 계약을 바꾸는 파이프라인 작업이 "일반"으로 통과할 수 있다 | 등록부 1 + 스키마 8(config 포함)이 모두 목록에 걸린다. 목록 밖 스키마(`holding-card`, `automation-delivery-runtime` 등)는 걸리지 않는다 |
| B | N1 오탐 줄이기: `quantity_authority`의 "권한 없음" 값에 `false`·`$false` 추가 | 이 저장소에서 `quantity_authority: false`는 "권한 없음"(스키마 `{"const": false}` 14개 등 — T3b Judge 보고 K6). 지금은 새 줄에 쓰면 사용자 승인(-ApproveAuthority)을 불필요하게 요구 | `quantity_authority: false`·`= $false`·`{"const": false}` 추가 줄 → general. `true`·`"full"`·숫자·그 밖의 값 → 그대로 authority. `execution_quantity`는 바꾸지 않는다 |
| C | 표지 `ORDER_TICKET_HUMAN_ENTRY` 처리 고정 | 주문 1단계(A7 a)의 유일한 non-none 값. 코드는 이미 "none/null이 아닌 값 = authority"라 이 값도 잡는다. 완화하지 않기로 한다(주문표 모듈은 이미 권한 경로, 그 밖에서 새로 쓰이면 사람이 봐야 함) | 코드 변경 0. 테스트로 동작을 고정하고 README·judge-prompt에 한 줄씩 |
| D | CLAUDE.md "Change classes" 절의 낡은 `Transition:` 문구 정정 | 키움 승인 고정(pin)은 T1 병합(510961a)으로 은퇴(`kiwoom-acceptance-pin-scope.json` status = RETIRED). 문구는 아직 "T1 병합 전까지 고정 파일 수정은 활성 acceptance를 무효로 한다"고 말함 | 낡은 3줄이 아래 3.D의 새 문구로 바뀐다. 다른 줄 변경 0 |

- **하지 않는 것(이번 묶음 밖, 이유)**: ③ O3b 오탐 좁히기 — 완화라서 첫 몇 주 빈도를 본 뒤. ② dev-merge↔dev-run 기준선 겹침·④ 파일 교체 경합·⑤ 정리 실패 표시·⑥ max_id 표시 — 오탐/오판을 만들지 않거나 드문 일, 군살 방지. ⑦ 동시 실행 부하 — 다음 파이프라인 작업 때 확인만. N2 문서 줄(`expected failures`) — README:82·judge-prompt:22에 이미 있음. 06:55 알림 예약 작업 변경 — 이 묶음(코드·CLAUDE.md)과 무관. `portfolio_review_journal.py`·`portfolio-review-journal*.schema.json`(T2가 고침)을 권한 경로에 넣을지는 이번에 판단하지 않는다(필요하면 보고 "남는 위험"에 근거와 함께 적고 끝낸다).
- 완료(Builder 단계): `test_dev_pipeline*` 전부 OK(새 테스트 포함) · 전체 스위트 실패 집합 ⊆ 0단계 a · 테스트 수 감소 0 · 허용 경로 밖 변경 0 · 스키마 감사 PASS · `test_reconcile_broker_state*` OK(CLAUDE.md 문구 단언 포함) · .ps1은 건드리지 않음.

## 2. Builder 지시 (이 절만 따른다)

~~~
경계: order_authority=false. 키움·kiwoomcli·비밀 금지. workspace/policies/*, stock-strategy-system/*, AGENTS.md, .claude/*, .gitignore 수정 금지.
커밋·병합·push·Windows 작업 등록 실행 금지. 모델을 부르는 claude -p 금지. dev-run·dev-merge·dev-queue 실행 금지(settings deny).
tools/·CLAUDE.md 편집은 settings ask라 승인 창이 뜬다 — 사용자가 승인한다. 승인이 거절되면 그 파일은 건드리지 않고 BLOCKED.md에 "제안 원문"을 적고 나머지를 마친다.
판단이 필요하거나 범위를 넘으면 BLOCKED.md를 worktree 루트에 쓰고 멈춘다.
줄바꿈: 고치는 기존 파일은 CRLF 유지(일괄 변환 금지). 명령에 auto_core.py 문자열 금지(-p "test_auto_core*").

범위(허용 경로):
  tools/dev_pipeline/authority-paths.txt, tools/dev_pipeline/devpipe.py, tools/dev_pipeline/README.md, tools/dev_pipeline/judge-prompt.md,
  manage-us-stock-strategy/tests/test_dev_pipeline.py, CLAUDE.md(3.D의 한 곳만), docs/claude/redesign-t3c-builder-report-2026-10-12.md (보고).
  그 밖은 금지. (dev-run.ps1·dev-queue.ps1·dev-merge.ps1·register-dev-tasks.ps1·builder-rules.md·commit-docs.ps1·run-docs-commit.ps1은 바꾸지 않는다.)

0단계(읽기만, 보고 맨 위):
 a. 이 worktree(clean) 전체 스위트 기준선 — 실패 id·Ran·skipped(숫자는 원본 출력에서 직접 셈; 전체 스위트는 test-runner 서브에이전트로 돌리고 실패 id만 받되, 숫자는 원본 stderr에서 직접 센다).
    예상: 실패 28(T3b Judge 기준). 다르면 그 차이를 보고하고 계속한다(차이 자체는 이번 변경의 원인이 아님).
 b. base sha256 4개(CLAUDE.md·authority-paths.txt·devpipe.py·README.md)가 머리말과 같은지. 다르면 BLOCKED.md.
 c. 권한 경로 후보 존재 확인: docs/claude/card-evidence-registry.json, manage-us-stock-strategy/schemas/auto-core-*.schema.json(8개 이름 나열).
 d. tests·scripts에서 `kiwoom-acceptance-pin`·`acceptance` 문구를 CLAUDE.md 텍스트로 단언하는 테스트가 있는지 grep(있으면 파일:줄 보고 — 3.D 문구가 그 단언을 깨면 안 된다).

A. authority-paths.txt
 - 파일 끝(기존 "Approved products and new-buy approval" 블록 뒤)에 새 블록을 추가한다(기존 줄은 지우거나 옮기지 않는다):
     # Auto-core order-ticket evidence and contracts (T2, 2026-10-12; evidence: docs/claude/redesign-t2-builder-report-2026-10-10.md)
     docs/claude/card-evidence-registry.json
     manage-us-stock-strategy/schemas/auto-core-*.schema.json
 - 기존 줄 변경 0(추가 줄만). 새 줄은 CRLF, 기존 CRLF 유지.
 - 테스트(test_authority_paths_file 확장 또는 새 테스트): 위 두 패턴이 파일에 있고, 등록부 1 + 스키마 8개(auto-core-card-registry·compare·config·decision·replay·research-record·result·ticket)가
   모두 매치되며, `manage-us-stock-strategy/schemas/holding-card.schema.json`·`automation-delivery-runtime.schema.json`·`docs/claude/watchlist-registry.json`은 매치되지 않는다.
   기존 "각 패턴이 실제 파일에 걸린다" 반복 검사가 새 패턴에도 통과해야 한다.

B. devpipe.py N1 (올리기만 → 정확히는 오탐만 줄임)
 - ADDED_NONE_VALUES["quantity_authority"] = ("none", "null", "$null", "false", "$false"). execution_quantity와 *_approved 규칙은 그대로.
 - 위 상수 위 주석 한 줄: quantity_authority false = 권한 없음(저장소 의미, 근거 docs/claude/redesign-t3b-judge-report-2026-10-10.md K6).
 - 그 밖의 devpipe.py 줄은 바꾸지 않는다. P6 보호 상수 블록(PROTECTED_* 상수)은 바이트 그대로.
 - 테스트(test_dev_pipeline.py 1056~1072 부근 목록을 고친다): `'"quantity_authority": {"const": false}'`를 authority 목록에서 general 목록으로 옮기고,
   `quantity_authority: false`, `quantity_authority = $false`, `"quantity_authority": false`를 general 쪽에 추가.
   authority 쪽에 남는 것: `quantity_authority: true`, `quantity_authority = "full"`, `quantity_authority: 5`, `{"enum": ["none","full"]}`, `execution_quantity: false`(none 값이 아님 → authority 유지).
   REMOVED_LINE 규칙(지운/바꾼 줄에 표지)은 그대로이므로 기존 `quantity_authority` 줄을 고치면 여전히 authority임을 단언하는 기존 테스트가 통과해야 한다.

C. ORDER_TICKET_HUMAN_ENTRY 고정 (코드 변경 0)
 - 테스트 추가: 추가 줄 `"quantity_authority": "ORDER_TICKET_HUMAN_ENTRY"`, `quantity_authority = "ORDER_TICKET_HUMAN_ENTRY"`, `"quantity_authority": {"const": "ORDER_TICKET_HUMAN_ENTRY"}`
   → added_value_reasons가 `ADDED_LINE:quantity_authority`를 낸다(authority). 구분자 없는 산문 줄(CLAUDE.md 형태: `quantity_authority "ORDER_TICKET_HUMAN_ENTRY" ...`)은 매치 없음(이미 그렇다 — 현행 동작 단언).
 - README "권한 경로" 절에 한 줄: `ORDER_TICKET_HUMAN_ENTRY`(주문 1단계 표지)는 `quantity_authority` 값이 none이 아니므로 새 줄에 쓰이면 authority다 — 의도된 동작, 주문표 모듈은 이미 권한 경로.
 - judge-prompt.md G7 항목 끝에 한 구절: "quantity_authority를 none/null/false가 아닌 값(예: ORDER_TICKET_HUMAN_ENTRY)으로 추가하면 class_ok=false". 다른 문장은 바꾸지 않는다.
 - README "권한 경로" 절의 추가 줄 규칙 설명에 B의 false/$false 허용을 한 구절로 맞춘다(`quantity_authority` ≠ none/null → none/null/false).

D. CLAUDE.md (한 곳만)
 - "## Change classes" 절의 아래 3줄(현재 59~61줄)을
     - Transition: the Kiwoom acceptance pin (manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json) is retired
       by redesign T1 and replaced by recording the git commit SHA in every run. Until that change is merged, editing a
       pinned file still invalidates the active acceptance: bundle such edits into the T1 Builder change.
   아래 4줄로 바꾼다(앞뒤 줄은 그대로, 줄 끝 CRLF):
     - Kiwoom acceptance pin: retired by redesign T1 (merged 510961a). manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json
       has status RETIRED and is kept only as the list of formerly pinned files. Editing one of them no longer invalidates an
       acceptance; instead every auto-core run records the git commit SHA and dirty paths, and in apply mode an uncommitted edit to a
       guarded file (the former pin list plus the core's own files) fails before any read (docs/claude/redesign-t1-builder-report-2026-10-10.md F6).
 - CLAUDE.md의 다른 줄 변경 0(115줄 → 116줄). `only from a verified read-only broker snapshot` 문구 유지(test_reconcile_broker_state 단언).
   근거 확인(보고에 파일:줄): pin scope status RETIRED(kiwoom-acceptance-pin-scope.json:52), guarded 집합(auto_core_reconcile.py:1105~1150), T1 보고 F6.
   근거와 문구가 어긋나면 문구를 근거에 맞게 줄이고 판단 목록에 적는다(사실을 만들어 넣지 않는다).

전체: test_dev_pipeline* 전부 OK, test_reconcile_broker_state* OK, test_auto_core* OK(실행만), 전체 스위트 실패 집합 ⊆ 0단계 a, 스키마 감사 PASS.
기계 실측(모델 호출 없이): ① devpipe.parse_authority_patterns + glob_to_regex로 `git ls-files` 전체를 돌려, 추가 전/후 권한 경로에 걸리는 파일 수 차이와 새로 걸리는 파일 목록 출력(기대: 등록부 1 + 스키마 7 = 8개만 늘어남)
          ② devpipe.added_value_reasons로 B·C 줄 샘플 출력.
~~~

## 3. 보고 (docs/claude/redesign-t3c-builder-report-2026-10-12.md, 한국어)
1. 0단계 a~d. 2. 바꾼 파일·줄(A~D 각각), 테스트 수치(대상·전체·기준선 대비), 기계 실측 원문. 3. Builder 판단 목록. 4. 남는 위험.

## 4. 병합 뒤
1. 사용자: Judge PASS 뒤 병합 명령 1번(Cowork 제공). 작업 재등록 불필요(스크립트 .ps1 변경 없음).
2. Cowork: CLAUDE.md sha256·authority-paths 변경 반영 확인 → 관제판 redesign-t3b 메모 ①·⑧·⑨ 처리 표시, redesign-t3c 완료. 카드 등록부·auto-core 스키마를 건드리는 파이프라인 작업은 이제 NEEDS_APPROVAL로 간다는 점을 `docs/claude/library/INDEX.md` 파이프라인 줄에 반영(필요할 때만).
3. 남는 의견(③ O3b, ② dev-merge 겹침, ⑤⑥): 관제판 메모에 그대로 둔다. 첫 몇 주 NEEDS_APPROVAL/STOP_MAIN_TOUCHED 빈도를 본 뒤 한 번에 판단.

## 5. 루프 점검 (loop-design-check 요지)
- 목표 판정 가능: 걸리는 파일 수(+8), 샘플 줄 판정, 테스트 수치.
- 경계: 파이프라인의 판정 입력은 "권한 경로 더 걸림"(A, 올림)과 "false 값 오탐 제거"(B, 의미 일치) 둘뿐이다. B는 `execution_quantity`·`*_approved`·REMOVED_LINE·주문 표지를 건드리지 않는다. 자기 규칙을 스스로 고치는 경로 없음(보호 경로 → 이 문서처럼 수동 경로). 재시도·자동 병합 없음.

## 6. Judge 확인 항목 (Cowork가 Judge 지시문에 그대로 넣는다)
- K1 범위: 2절 허용 경로 안뿐. CLAUDE.md는 3.D 한 곳(+1줄)만. AGENTS.md·settings.json·.gitignore·.ps1 변경 0. CRLF 유지(바뀐 파일 줄바꿈 혼합 0, BOM 없음).
- K2 A: authority-paths.txt는 추가 줄뿐(기존 줄 diff 0). 두 패턴이 등록부 1 + 스키마 8에 걸리고 목록 밖 파일에 안 걸리는가(Judge가 직접 `git ls-files`로 재계산).
- K3 B: 완화가 정확히 `quantity_authority`의 false/$false에만 있는가. `true`·`"full"`·숫자·`execution_quantity: false`·`*_approved`·REMOVED_LINE·주문 표지는 그대로 authority인가. 테스트가 양쪽을 단언하는가. P6 보호 상수 블록이 base와 바이트 같은가.
- K4 C: 코드 변경 0, `ORDER_TICKET_HUMAN_ENTRY` 추가 줄이 authority로 남는다는 테스트, README·judge-prompt 문구가 동작과 맞는가.
- K5 D: CLAUDE.md 문구의 각 사실(RETIRED, 510961a, SHA·dirty 기록, apply 모드 guarded 미커밋 FAIL)이 저장소 근거와 일치하는가. 다른 줄 변경 0. `only from a verified read-only broker snapshot` 유지.
- K6 회귀: 전체 스위트 실패 집합 ⊆ 기준선, 테스트 수 감소 0, test_dev_pipeline 전부 OK, 스키마 감사 PASS. T3·T3b Judge의 J2(자기 규칙 보호)·J6(병합 조건) 근거 유지.
- K7 class: 이 변경이 권한/한도 변경(재설계 A5)에 해당하지 않는가 — 판정 규칙을 더 엄격하게(A) 하거나 의미에 맞게 오탐만 줄이는(B) 것이고 어떤 주문·한도·승인 상품도 바꾸지 않는다. 해당하면 class_ok=false로 쓰고 이유를 적는다.

## 7. 사용자 조작 (Windows PowerShell, 한 번에 한 단계)
1. `cd "E:\사업\##금동한\코덱스저장소"` → `.\tools\commit-docs.ps1` (이 지시문이 커밋돼야 worktree에 들어간다). 끝에 `OK … -> <해시>`가 보이면 다음 단계.
2. `claude --worktree t3c --model opus --effort high`
3. Claude Code 첫 메시지:
```
Read docs/claude/redesign-t3c-builder-prompt-2026-10-12.md and follow sections 0-3 exactly (section 6 is what the Judge will check).
```
4. tools/·CLAUDE.md 편집 승인 창이 뜨면 승인. 끝나면 Cowork에 "T3c Builder 완료"만.
