---
id: ev-rg1-hyper-judge2-report
title: ev-rg1-hyper 재판정(Judge 2) — 1차 FAIL(항목 6 계산기 validate_facts ③ 사실 검사 누락) 수정 확인
date: 2026-10-18
prompt: docs/claude/ev-rg1-hyper-judge-prompt.md 맨 끝 "재판정" 절(1~5) — 파일 sha256 3cce6d23105dbf3e2351a68bf8a35dd2957ad9e4f2f3d598705ea13b14686844
first_report: docs/claude/ev-rg1-hyper-judge-report.md — Judge가 잰 sha256 307984a350e1a1f94775669c268bb0811cf0ab6b5b16a0b891c7c4930770d9c7(지시문의 307984a3…와 같음), 마지막 줄 VERDICT: FAIL
fix_scope: docs/claude/ev-rg1-hyper-builder-prompt.md 끝 "추가 범위 — Judge 1차 FAIL 수정"(1~7)
target: .claude/worktrees/ev-rg1-hyper (브랜치 worktree-ev-rg1-hyper, HEAD 073582db663633c6c5b860ad5ddcec18b2990f40 = 메인 HEAD, 커밋 안 된 변경)
class: K3 독립 Judge(읽기 전용) — Builder·1차 Judge와 다른 새 세션, 메인 체크아웃, Opus 5.5 · xhigh
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 키움 호출 없음 · 파일 수정 없음(저장소에 쓴 파일은 이 보고서 1개; 합성 입력·계산기 --out·실험 스크립트는 저장소 밖 스크래치 폴더)
---

# 0. 범위 고정 (재판정 1)

worktree `git status --porcelain --untracked-files=all` = 1차와 같은 13개 경로(M 10 · 새 파일 3). Judge가 Windows worktree 작업 트리 바이트로 잰 sha256을 1차 보고 끝 표와 대조:

| 파일 | 1차 표와 |
|---|---|
| auto_core_rules.py · auto_core_inputs.py · auto_core_decide.py · auto_core_tickets.py · auto-core-card-registry.schema.json · card-evidence-registry.json · references/auto-core-decision.md · test_auto_core_rg1_damage.py · test_auto_core_decide.py (재판정 1의 "10개 파일" — 1차 표 13행에서 계산기·실행기·parity·보고서를 뺀 9개 경로) | **9/9 바이트 같음** |
| docs/claude/t2rc-oracle.py · docs/claude/t2rc-check-run.ps1 · tests/test_auto_core_rg1_oracle_parity.py | 바뀜(수정 대상 — 항목 6·10·14에서 다시 판정) |
| docs/claude/ev-rg1-hyper-report.md | 바뀜(Builder 보고 갱신 — 판정 근거 아님, 위치 안내) |

메모: 재판정 1은 "10개 파일"이라 했지만 1차 표 13행에서 넷을 빼면 9개 경로다. 그 9개가 모두 같으므로 범위 고정 조건은 충족된다. 메인 체크아웃 base: t2rc-oracle.py sha256 = sha256_lf 5607b09b…, t2rc-check-run.ps1 5d3502b9…(1차와 같음, 메인 HEAD 073582d 그대로). 메인 작업 트리의 추적 파일 변경은 Cowork가 고친 지시문 2개(ev-rg1-hyper-builder-prompt.md·ev-rg1-hyper-judge-prompt.md — 추가 범위·재판정 절)뿐이다.

# 판정 표

| # | 항목 | PASS/FAIL | 근거(파일:행 / 재계산 값) |
|---|---|---|---|
| 1~5·7~9·11~13·15 | 범위·권한·R0/R1·R2·R3/D2·R5 ③ 출처·R7·④ 골든·D1·실데이터·다른 독자·병합/C1 | 1차 유지 — 바이트 동일 | 0절: 9개 파일 바이트 같음. 계산기 1차→2차 diff가 `validate_facts` 안뿐이라(항목 10) 계산기가 걸린 항목 2(import t2rc-oracle.py:26~35 표준 라이브러리 그대로, 추가 줄 ASCII·CRLF 2502/2502)·7(`validate_facts` 호출 3곳 1407·1435·1556 그대로, `damage_domains`는 1435만)·11(`g2_buy` 1943·`lines_open` 0건 — diff 밖)의 근거도 그대로다 |
| 6 | R4 우선순위·대등 | **PASS** | **원문**: 새 `validate_facts`(t2rc-oracle.py:807~856) — 사슬 전에 `official`(830)·`marked`(831~832: 공식 아님 ∧ root_thesis_damage is True ∧ `damage_domains` 일치)를 구하고 `if host is None: URL`(833~834) → `elif not official and not marked: DOMAIN`(835~836, 공식도 표지도 아님) → SOURCE_KIND(837~838) → WRITTEN_BEFORE_CLOSE(839~840) → WRITTEN_AFTER_DECIDE(841~842) → EVENT_SESSION(843~844, 글자 base 827~834와 같음) → DIRECTION(849~850) → 통과한 사실에만 표지(853~854). 그래서 ③ 사실도 모든 검사를 거친다. 그 뒤 `load_rrec1_records`가 오프셋 없는 기록 제외(1433)·결정 시각·event_session ≤ 기록 세션·summary 200(1436~1438). 코어 check_record(auto_core_inputs.py:258~270: SOURCE_KIND·HOST·EVENT_SESSION(달력·≤ 세션)·ANNOUNCED_AT·SUMMARY)와 받는 집합이 같다. **1차 재현 다시**(1차 Judge 적재 11경우를 스크래치 사본으로 그대로): 토요일 2026-09-12 microsoft.com 훼손 사실 → 코어 [] / 새 계산기 [] (1차 판 계산기 ['DMG-SAT']), source_kind NEWS ③ 사실 → 새 계산기 버림 [](1차 판 ['DMG-KIND']). 요건 ⑤ 끝까지(실험 C, 실제 rrec1·`buy_requirements`): 사건 없음·닫힌 사건 두 세계 모두 토요일 사실 → 코어 status ok·칸 ok = 계산기 reqs[4] ok(1차 FAIL 경로 해소), 대조(같은 사실 event_session 월요일 09-14) → 양쪽 no·`rg1_damage` ['MSFT-SAT']. **기본 호출 동일성**: 고정 시드 20261018 무작위 1,000입력(사실 3,000 · 훼손 도메인 호스트 root 참 499 · 등록부 `thesis_damage_domains` 있음/없음 반반 · URL 없음·http·대문자·유사 호스트·kind·방향·event_session·written_at·decide_at·prev_seen 변형)에서 새 `validate_facts`(인자 없음, `damage_domains=[]` 둘 다) = base 판(메인 5607b09b…) (keep, dropped) **1,000/1,000 같음**. `load_research_history`·`research_record_ok`·`ny_sixteen` 함수 본문과 오늘 사실 호출 줄(1556)이 base와 글자까지 같다 → C7 history·오늘 사실 불변. **③ 적재 대등**(고정 시드 1018, 무작위 300저장소 · 사실 2,175 · 코어가 받은 ③ 312, 스키마 유효 사실만, event_session 같은 날·직전·이전·주말·휴장 평일·기록 세션 뒤, 발표 −04:00/Z/+09:00/결정 뒤, summary 1~201, 호스트 11종): 코어 `load_research` ↔ 새 `load_rrec1_records` 기록 범위·(fact_id, 표지) **300/300 같음**(1차 판 계산기는 89저장소 다름 — 계산기만 받은 ③ 113건: 실험이 1차 결함을 잡는 힘 확인). **rrec1 대등**(1차 Judge 스크립트를 그대로 새 계산기로): 이름 붙은 28경우(S1~S9·S6b + J1~J7: 같은 날 훼손+EV1·EV4 재기준·DS1 반복 중 훼손·W[0] 경계·재수락 경계 a = rel−1/rel/t/t+1·두 사실 중 하나 해제·EV3B 공백+훼손) 불일치 **0/28**, 고정 시드 20261018 300입력×(재수락 없음/있음) **0/600**. 남은 차이는 모두 base부터 있던 것(발견 2 — 1차가 범위 밖으로 둔 것과 같음) |
| 10 | 계산기 고정값 | **PASS** | Judge가 잰 worktree t2rc-oracle.py `sha256_lf`(정의 t2rc-oracle.py:110~113, LF 정규화) = **9f0e2238f2a8238016be5406cd2e195aaf24c232adeda5f1fba3a52cd09b1aae** = t2rc-check-run.ps1:16 `$ExpectedOracleSha256`. 실행기 자체 방식(61~63행: UTF-8 ReadAllText → CRLF→LF → SHA256)을 PowerShell 5.1에서 읽기 전용으로 재현해도 같은 값(실행기 자체는 workspace/outputs에 쓰므로 돌리지 않음). 원시 e41a7903…(CRLF 2502/2502행). **1차 판 대비 diff**: 1차 판 계산기를 바이트 단위로 복원했다(Builder 스크래치 사본 oracle_judge1.py = 새 docstring + 1차 사슬, 여기에 1차 docstring을 되돌리면 sha256_lf **88c3365b…로 정확히 일치** = 1차 Judge가 잰 값). 복원본 ↔ 새 판 diff = `validate_facts` docstring 2줄→3줄(810~812, "goes through the same remaining checks" 구절)과 사슬(1차 828·831~835 → 새 829~836: −6/+6, 주석 1줄 포함)뿐, 그 밖 0줄. 실행기 diff(1차 판 대비) = 16행 1줄(새 값을 88c3365b…로 되돌리면 1차 원시 8a786cbc…와 정확히 같음), CRLF 117/117, ASCII. **selftest**(`--repo` 메인): worktree·base 모두 PASS, fails [], 앵커 5 참, 두 출력 바이트 같음. **실데이터 check**(`--repo` 메인, `--out` 스크래치): 10-16·10-17 기본 = 양쪽 NOT_CHECKED(입력 sha), `--ignore-input-sha` = 양쪽 INFO_MATCH·requirements diffs [] — 4쌍 모두 출력 JSON이 `oracle_sha256`(9f0e2238… vs 5607b09b…) 말고 **완전히 같음** |
| 14 | 테스트 | **PASS** | **parity**: `-p "test_auto_core_rg1_oracle_parity.py"` Ran 7 OK(1차 4 + 새 3). 새 3경우 원문(parity.py:204~288): 토요일 ③ 사실(219~231) — 코어 damage·계산기 `load_rrec1_records` 모두 ['DMG-F1']만, `validate_facts` dropped `[["DMG-SAT", "EVENT_SESSION"]]`, 토요일임을 weekday 5·달력 밖으로 단언; source_kind BLOG(233~243) — 계산기 ['DMG-F1']만·dropped SOURCE_KIND, 코어 damage []·sessions [](기록 전체 무효) + 영문 주석 1줄; 기본 호출(245~287) — 8사실 (keep, dropped) = 상수 `BASE_KEEP`·`BASE_DROPPED`. **단언 세기 확인**: 같은 테스트에 1차 판 계산기를 바꿔 끼우면 앞 두 경우 FAIL(표지 사실이 남음), 기본 호출은 통과(동일성 확인용이라 맞음); `BASE_KEEP`·`BASE_DROPPED`를 base 판 계산기로 Judge가 다시 계산 → 같음. 기존 4경우 불변: 204~288행을 빼면 원시 sha ddbc9898…(1차 표)와 정확히 같다 → 추가만, CRLF 291/291, ASCII. **대상**: worktree `-p "test_auto_core*.py"` Ran 453(1차 450 + 3)·실패 1(`test_auto_core_decide.RegistryTests … (symbol='PLTR')` `['CARD_SECTION_CHANGED', 'CARD_NOT_ACCEPTED_IN_WATCHLIST']` — 1차와 같음)·건너뜀 1, `test_score_*` 66 OK, `test_decision_journal_cards` 36 OK, 스키마 검사 PASS(errors []). **전체 스위트**(test-runner, 로그는 Judge가 grep으로 다시 확인): Ran 3213(1차 3210 + 새 3)·실패 24·오류 9·건너뜀 3. 1차 worktree 로그의 실패·오류 30줄은 **모두 그대로 있고 빠진 것 0**. 더해진 3줄은 `test_dev_pipeline.MainCheckoutTests`(test_docs_change_and_docs_commit_pass · test_policy_state_ignored_and_tracked_changes_stop 하위 2) — 원인: devpipe.py:100 `AUTO_CORE_WINDOW_KST` 06:10~06:40와 1594~1605행이 벽시계로 상태 비교를 건너뛰는데, 전체 스위트가 06:36~06:42 KST에 돌아 창과 겹쳤다(출력 `skipped=SKIPPED_AUTO_CORE_WINDOW`). 창 밖(06:44 KST)에 `-p "test_dev_pipeline.py"`를 다시 돌리면 Ran 120 OK. 이 클래스는 임시 저장소만 쓰고 바뀐 파일을 참조하지 않는다(grep). → 변경 기인 새 실패 0, Ran 감소 없음, 시각을 뺀 실패 집합 = 1차 기준 |

# 발견

## 1. 1차 FAIL 사유 해소 (항목 6)
- 1차 결함: ③ 사실이 if/elif 사슬의 DOMAIN 가지 안에서 통과해 SOURCE_KIND·작성 시각·EVENT_SESSION 검사를 건너뜀(1차 보고 발견 1).
- 수정(1차 보고 "고칠 최소 항목" 1~3, 지시문 추가 범위 1~3): `official`·`marked`를 사슬 앞으로 빼고 DOMAIN 가지를 `not official and not marked`로 바꿈. 아래 가지는 글자 그대로. 결과: ③ 사실이 코어와 같은 검사를 모두 거친다(토요일·휴장일·source_kind 불량 → 버림). 기본 호출(history·오늘 사실)은 `marked`가 늘 거짓이라 base와 같다(무작위 1,000입력·고정 상수 테스트).
- "고칠 최소 항목" 4(재판정 범위)대로 판정했다. 선택 권장 5(b) 호스트 추출은 Cowork가 NO_CHANGE로 정했다(지시문 추가 범위 6, Builder 보고 8(j)).

## 2. 남은 차이 — 모두 base부터 있던 것, 1차 범위 밖(이번 판정의 FAIL 사유 아님)
| 경우 | 코어 | 새 계산기 | 방향 | 비고 |
|---|---|---|---|---|
| ③ URL에 포트(`:443`) 또는 경로 없는 쿼리(`?a=b`) | 받음(`urlsplit().hostname`) | 버림(정규식 `^https://([^/]+)`, 825) | 계산기가 덜 엄격 → 코어는 막고 계산기는 주문표를 기대 → MISMATCH(C1 재시작). 코어 막힘은 유지(fail-open 아님) | 1차 발견 5(b), Builder 8(j) 후속 후보 — 1차 판·새 판 같은 결과 |
| source_kind 열거값 밖인 사실이 든 기록 | 스키마로 기록 전체 무효(기록 범위에서 빠짐) | 그 사실만 버리고 기록 범위로 셈 | 기록 범위 차이(계산기 덜 엄격 쪽 가능) | 표지 없는 사실도 base부터 같음. 통합 점검 로더가 source_kind를 거른다(integrated-check-daily.txt:72 `f['source_kind'] in SK`, 이번 세션 확인) |

## 3. 1차 판정 유지 범위 메모
- 항목 1~5·7~9·11~13·15는 0절 바이트 대조로 유지한다. 1차의 비교 B7·통합 점검 문구 차이 목록(1차 발견 4 — 로더 37·72행, 규칙 파일 v3.12.6 102행, 개장 전 15행, recovery-gate 37·43행, CLAUDE.md R-REC1 요약)과 남은 위험(1차 발견 5(a)·(c)·(d))도 대상 파일이 바뀌지 않아 그대로다 — 병합 절차(지시문 175~184행)의 Cowork 교체 대상.
- Builder 보고 7절 sha 값(e41a7903… · 3735492e… · a2a5982f… · sha256_lf 9f0e2238… · 실행기 sha256_lf fcd8977b…)은 Judge가 잰 값과 모두 같다. Builder 보고 3절은 수정 뒤 전체 스위트를 다시 돌리지 않았다고 적었다 — 이번 재판정에서 Judge가 돌렸다(항목 14).

## 4. 남은 위험 · 의견
- (a) 테스트 시각 의존(범위 밖, 이번 변경 무관): `test_dev_pipeline.MainCheckoutTests`는 `utc_now`를 고정하지 않아 06:10~06:40 KST에 돌리면 실패한다. Cowork가 관제판에 후보로 올릴지 정한다(기본 NO_CHANGE).
- (b) 전체 스위트 안의 하위 프로세스 테스트가 worktree에 git 무시 대상 `manage-us-stock-strategy/scripts/__pycache__/`(dual_run_scheduler·validation_common .pyc, 06:42:16)를 만들었다(PYTHONDONTWRITEBYTECODE=1로 돌렸어도 생김 — Builder 보고 10절 05:03과 같은 현상). `.gitignore:25 **/__pycache__/`라 status·병합 경로 목록·sha 표에 영향 없다. "파일 수정 금지"에 따라 Judge는 지우지 않았다 — 지워도 된다.
- 의견: 1차 FAIL 사유는 최소 수정으로 해소됐고 수정은 지시된 세 파일 안에 머문다. 판정 PASS. 다만 이 변경은 K3라 병합은 사용자 승인 1줄 + 병합 스크립트(지시문 "병합·고정값 교체·C1 재시작" 절, Cowork 작성) 뒤에만 효력이 있다. 승인 전 기본 처분은 NO_CHANGE(현행 관문·계산기 고정값 5607b09b… 유지).

# 고칠 최소 항목
없음.

# sha256 (Judge가 잰 Windows worktree 작업 트리 바이트, 2026-10-18 06시대 KST)

| 파일 | sha256 | 1차 표와 |
|---|---|---|
| manage-us-stock-strategy/scripts/auto_core_rules.py | 48433ab8d4c5eae45f9c6e54740e282cf5004807f5ce75842f64ea8cc4fbab4e | 같음 |
| manage-us-stock-strategy/scripts/auto_core_inputs.py | 6e0f2cf1d6302c87612a41fb06b0ddd347eb279aef0f45d5bccd26b013b49201 | 같음 |
| manage-us-stock-strategy/scripts/auto_core_decide.py | 1013da08704fb74d7afb30455403d6d3e31f67d75392e93d1242f3c5cb7448f1 | 같음 |
| manage-us-stock-strategy/scripts/auto_core_tickets.py | 2393fa7b19352fd435846aa67d68604b74ca1d73fb9a0e51b845931433afb8c1 | 같음 |
| manage-us-stock-strategy/schemas/auto-core-card-registry.schema.json | 5b69e590f16542306ba2af88e72d9e3db434e29e50b3b7cfc3834def713c791e | 같음 |
| docs/claude/card-evidence-registry.json | 1654aa0d7a525e167452d62800cb9f80237d29649b95e52f0343498cc83abdb8 | 같음 |
| manage-us-stock-strategy/references/auto-core-decision.md | c47bbc876a12a9263b1d24f6d058131c01ba019a6a0aad7d6ba4c50ad09886a8 | 같음 |
| manage-us-stock-strategy/tests/test_auto_core_rg1_damage.py | d4c8e9a202f145130b404b490caec9d3f41ce4e38285f400eaef32a05a0b4464 | 같음 |
| manage-us-stock-strategy/tests/test_auto_core_decide.py | 0b6866a2f564b5faa342d662df478644dc72ffb85b77f2b8c36412533c98519c | 같음 |
| docs/claude/t2rc-oracle.py | e41a79033a73a4662361a2daeaa79a6c40421069d5e7a889dc353f4e8ba7bb67 (원시, CRLF 2502/2502) | 바뀜(1차 c923d43c…) |
| docs/claude/t2rc-check-run.ps1 | 3735492e3f6a803ee7be4a7ed2251ea2df0499e83270cd7bdaa77ca6c6cff167 (원시, CRLF 117/117) | 바뀜(1차 8a786cbc…) |
| manage-us-stock-strategy/tests/test_auto_core_rg1_oracle_parity.py | a2a5982fc52d887b6d4f214c15ca58bc7b4873d2f9790201caf14e332a4dc4b1 (CRLF 291/291, ASCII) | 바뀜(1차 ddbc9898…) |
| docs/claude/ev-rg1-hyper-report.md | 00ed0a1cee732f2fc100a7303b559e363c6e00537b6d395f1211b6ec50829b24 | 바뀜(1차 bcd0c649…) |

- 새 계산기 sha256_lf: **9f0e2238f2a8238016be5406cd2e195aaf24c232adeda5f1fba3a52cd09b1aae** (= 실행기 16행 `$ExpectedOracleSha256`, 일치. 계산기 check 출력 `oracle_sha256`도 같은 값). 1차 판 88c3365b… · 메인 base 5607b09b47585a8b0799ae84b93cff434ebecdfc2b30f305607c8641b8f02a26.
- 실행기 sha256_lf: **fcd8977bac37034e7805dda7dd31756b8b6a224c6cdec673d45189c0cd1680a7** (원시 3735492e…). 1차 판 8262212d… · 메인 base 5d3502b90b3901823e0eded7d196d7c6710b63765bc7d003dc3e1ef313d2df7b.
- 병합 스크립트가 쓸 "Judge가 잰 목록·sha256"은 이 표 13행이다.

# 원문 확인 기록
재판정 절·Judge 지시문 전문 · Builder 지시문 전문(추가 범위 1~7 포함) · 1차 Judge 보고 전문(sha 확인) · Builder 보고 전문(위치 안내) · worktree t2rc-oracle.py 105~113·772~856·1393~1440·1930~1945행과 base 805~844행 · 1차 판 복원본 ↔ 새 판 전체 diff · t2rc-check-run.ps1 8~16·58~67행 · parity 테스트 전문 · auto_core_inputs.py 195~329행 · 연구 기록 스키마 official_facts · tools/dev_pipeline/devpipe.py 100·1580~1610행 · test_dev_pipeline.py 787~793(plain_repo = tempfile)·1137~1195행 · integrated-check-daily.txt 72행 · 전체 스위트 로그(새로 잰 것, 1차 worktree 로그와 실패 ID 대조). 실험 스크립트(저장소 밖, 읽기 전용 — 임시 폴더만 씀): 스크래치 exp/judge2_exp.py(A 기본 호출·B 적재 대등·C 토요일 끝까지)·exp/judge2_testpower.py(새 테스트 검출력·상수)·1차 Judge 스크립트 사본 judge_exp_rules.py·judge2_loader.py(1차 judge_exp_loader.py에 계산기 경로 인자만 더함).

VERDICT: PASS
