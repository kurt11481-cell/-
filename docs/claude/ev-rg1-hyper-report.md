---
id: ev-rg1-hyper-report
title: ev-rg1-hyper Builder 보고 — R-REC1 RG1 공식 테제 훼손(카드 재수락 전 매수 막힘) + 빅테크 훼손 출처 + 계산기 RG1 동반 수정
date: 2026-10-18
prompt: docs/claude/ev-rg1-hyper-builder-prompt.md
class: 권한·한도 변경(K3) — 수동 경로 Builder(이 worktree). 다음: 별도 Judge 세션(docs/claude/ev-rg1-hyper-judge-prompt.md)
revision: Judge 1차 FAIL 수정 반영(2026-10-18, docs/claude/ev-rg1-hyper-judge-report.md sha 307984a3… 항목 6·고칠 최소 항목 1~4, 지시문 끝 "추가 범위") — 10절. 바뀐 파일은 t2rc-oracle.py·t2rc-check-run.ps1(16행)·test_auto_core_rg1_oracle_parity.py·이 보고뿐
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 키움·auto_core.py·dev-run·dev-merge·reconcile apply 실행 없음 · 커밋 없음
---

# 0. worktree HEAD

- worktree `ev-rg1-hyper`, 브랜치 `worktree-ev-rg1-hyper`, HEAD `073582db663633c6c5b860ad5ddcec18b2990f40`.
- 지시문 base `a9ea3382639e17cc7bb0e5057b57c701eef3e6f1`은 HEAD의 조상이다. `git diff --name-only a9ea338 HEAD`에서 docs/claude/ 밖 경로는 0개(그 사이 커밋은 docs/claude만).
- base 해시 확인(변경 전, Windows worktree 바이트): auto_core_rules.py 511c8a13… · auto_core_inputs.py 89666f99… · auto_core_decide.py 2eba6c58… · auto_core_tickets.py 846c3d86… · auto-core-card-registry.schema.json 663c6aaf… · test_auto_core_risk1r.py e2f16d19… — 모두 지시문 8행과 같음. t2rc-oracle.py 원시 af226e0a…(CRLF 2249/2249행) · sha256_lf 5607b09b…(= 실행기 고정값). t2rc-check-run.ps1 원시 4cabb975…(CRLF 117/117행) · sha256_lf 5d3502b9…(= 사전 등록 49행).
- 지시문과 다른 점 1개: 지시문은 "worktree(HEAD)에는 PLTR 항목이 없다"고 했지만 HEAD 073582d에는 커밋 698baf2(10-17)로 PLTR이 들어와 등록부가 10종목이다(PLTR accepted.date 2026-10-17). 영향은 기준선 실패 1건(3절)뿐 — 범위 밖 자료 상태.

# 1. 파일별 바뀐 줄 (git diff --numstat, 추가/삭제)

| 파일 | +/− | 내용 |
|---|---|---|
| manage-us-stock-strategy/scripts/auto_core_rules.py | +86/−12 | `iso_day`·`damage_release_day`·`uncleared_damage`(R0) 추가, `KST_FIXED`(UTC+9 고정)·`ISO_DAY`. `rrec1`에 `card_accepted_on=None` 키워드 1개. RG1 = U(day_i) 기준(R1), 시간 소멸에 `current["RG1"] is not False`(R2), 닫힘·사건 없음 반환에 `damage_block`(R3), `settle`이 미해제 있을 때만 `rg1_damage`(R8), EV3b `damage_days`는 `damage_source` 없는 사실만(R5). docstring 고침. import `date, timedelta, timezone` 추가. CONSTANTS 불변 |
| manage-us-stock-strategy/scripts/auto_core_inputs.py | +31/−7 | `DAMAGE_DOMAIN_SOURCE = "THESIS_DAMAGE_DOMAIN"`. `load_registry` 결과에 `damage_domains`(소문자, OK 아니면 []). `check_record`: 출처가 sec.gov·그 종목 official_domains가 아니고 root_thesis_damage가 참이며 `damage_domains`에 맞으면 남은 검사를 계속하고 통과 시 `damage_only`(있을 때만 키)로 — 표지 `damage_source`. `load_research`: `damage_only`는 창 안 기록일 때 `damage`에만 |
| manage-us-stock-strategy/scripts/auto_core_decide.py | +35/−2 | `card_accepted_on(check)`(엄격 YYYY-MM-DD)·`portfolio_accepted_on(accepted_on, holdings)`(보유 종목 가장 이른 날, 하나라도 없으면 None). rrec1 호출 2곳에 `card_accepted_on`. `by_symbol` 항목에 `rg1_damage`(있을 때만). `alert_candidates`: 상태 `2:RG1DMG` = "<fact_id,…>|<막힌 종목,…>"(있을 때만), 값이 처음 생기거나 바뀐 날 예외 줄(push 참, 기존 예외 줄 뒤, 종목 코드·fact_id 없음) |
| manage-us-stock-strategy/scripts/auto_core_tickets.py | +3/−0 | 요건 ⑤: unk 가지 다음·open 가지 앞에 `status == "no" and not open` → {"s": "no", "t": "막힘 RG1 공식 테제 훼손(카드 재수락 전)"}(`\u` 이스케이프) |
| manage-us-stock-strategy/schemas/auto-core-card-registry.schema.json | +6/−0 | 최상위 선택 키 `thesis_damage_domains`(array, uniqueItems, 소문자 호스트 pattern, description 1문장). required 불변 |
| docs/claude/card-evidence-registry.json | +1/−0 | `"symbols"` 바로 앞 `"thesis_damage_domains": ["microsoft.com", "abc.xyz", "atmeta.com", "aboutamazon.com"],` 한 줄(CRLF, 들여쓰기 2칸). updated_at·updated_by·rule·symbols 불변 |
| docs/claude/t2rc-oracle.py | +273/−20(Judge 1차 수정 뒤; 1차 +272/−20) | 맨 위 출처 1줄. `validate_facts(…, damage_domains=None)`(③ 사실 표지 — 이 인자는 `load_rrec1_records`만 넘김; Judge 1차 수정: `official`·`marked`를 사슬 전에 구하고 `elif not official and not marked: DOMAIN`, 아래 가지 그대로 — ③ 사실도 남은 검사를 모두 거침, 10절). `strict_day`·`offset_moment`·`rg1_release_day`·`rg1_uncleared`(R0). `rrec1(…, accepted_on=None)`: fact_id 첫 판(기록 순)·RG1 = U(d)·시간 소멸 RG1 "no"면 안 닫힘·사건 없음/닫힘 반환에 R3(rg·reason)·EV3b는 표지 없는 사실만. `load_rrec1_records`(G-1-1 ①~③, rrec1 전용). `cmd_check` env에 `rrec_records`, 요건 ⑤ 호출(`buy_requirements`)이 `env["rrec_records"]`와 `accepted_on=(e.get("accepted") or {}).get("date")`. D1 = c: `lines_open` 정의·`and not lines_open` 삭제 — G2 식을 `g2_buy()`로 옮김(다른 항 글자 그대로, S16에서 부르기 위해). selftest `selftest_rg1_damage`(S1~S9)·`selftest_g2_lines`(S16). `ORACLE_VERSION` 불변, auto_core import 없음 |
| docs/claude/t2rc-check-run.ps1 | +1/−1 | 16행 `$ExpectedOracleSha256` = 9f0e2238…(Judge 1차 수정 뒤 새 계산기 sha256_lf; 1차 판은 88c3365b…)만 |
| manage-us-stock-strategy/references/auto-core-decision.md | +14/−1 | R-REC1 문단에 RG1 규칙(R0~R3·R5·R8·알림), 등록부 계약 문단에 `thesis_damage_domains` 한 문장(영문) |
| manage-us-stock-strategy/tests/test_auto_core_rg1_damage.py | 새 파일 492행 | S1~S9·S6b·S10~S14 |
| manage-us-stock-strategy/tests/test_auto_core_rg1_oracle_parity.py | 새 파일 291행(1차 206행) | 코어↔계산기 대등(S1~S9·시드 경우)·S15 적재 대등 + Judge 1차 수정 3경우(10절) |
| manage-us-stock-strategy/tests/test_auto_core_decide.py | +5/−0 | 미리 허용한 입력 수정 1곳(아래 3절) |
| docs/claude/ev-rg1-hyper-report.md | 새 파일 | 이 보고 |

줄 끝: 모든 기존 파일은 체크아웃된 CRLF 그대로(바뀐 파일 전부 CRLF 줄 수 = LF 줄 수 확인). 새 테스트 두 파일도 이 체크아웃과 같게 CRLF. 스크립트·테스트의 새 줄은 ASCII만(한국어는 `\u` 이스케이프). 작업 중 `sed -i`가 auto_core_rules.py를 LF로 바꾼 것을 곧바로 CRLF로 되돌렸다(1009/1009행).

# 2. 새 규칙 (R0~R8, D1·D2 반영)

창 W = 평가 세션 t까지 SOXX 60세션(W[0] = 첫 날, 지금과 같음). 훼손 사실 F = 유효 연구 기록의 root_thesis_damage 참 사실(sec.gov·그 종목 official_domains) + 등록부 `thesis_damage_domains` 호스트에서 온 root_thesis_damage 참 사실(표지 `damage_source: THESIS_DAMAGE_DOMAIN`). 해제 날 rel(f) = max(event_session, announced_at의 KST(UTC+9 고정) 날짜) — "Z"는 +00:00, 오프셋 없거나 못 읽으면 rel 없음. 카드 날 a = 후보의 등록부 accepted.date(엄격 YYYY-MM-DD), 코어 포트폴리오 판정은 보유 종목 accepted.date 중 가장 이른 날(보유 종목 하나라도 항목·날짜가 없거나 보유 종목이 없으면 없음). 사실 f는 rel(f) ≤ a ≤ d일 때만 날 d에 해제(소급 해제 없음). 미해제 U(d) = {f : W[0] ≤ event_session ≤ d, 해제 안 됨}. **R1** RG1(i): F 추적 안 함(None) → unk(그대로), U(day_i) 비어 있지 않으면 no, 그 밖은 지금 그대로(2세션·기록 범위) — 사건 날짜와 비교하지 않으므로 사건 날 훼손(ⓐ)·재기준 전 훼손(ⓑ)도 센다. **R2** 모두 충족 닫힘은 그대로, 시간 소멸 닫힘은 그날 RG1이 no면 안 닫힘(unk는 막지 않음). **R3**(D2 처리 = 막는다) 닫힌 뒤나 창 안 사건 없음에서 U(t)가 비어 있지 않으면 status no, open False 그대로, rg RG1 no(다른 관문 값은 있으면 그대로), reasons `RG1_THESIS_DAMAGE:<id 정렬>`; closed_at·events 그대로. **R4** 자료 없음 unk → EV3B 기록 공백 unk → R3 → 지금 결과식(코어 `settle`이 마지막, 계산기는 공백 검사가 사건보다 먼저 — 상태 문자열이 같음). **R5** 사건 목록·EV 종류·C0·L0·DS1·RG2~RG4·EV3B 공백·RG1 기록 범위 불변, EV3b는 표지 없는 사실만. **R6** 해제 = 카드 재수락(rel ≤ a ≤ 판정 날) 또는 창 밖. **R7** 해제 없는 입력에서 더 느슨해지지 않음(3절 S13). **R8** U(t)가 있을 때만 결과·`by_symbol`에 `rg1_damage`, 없으면 dict가 base와 같음. 주문표 요건 ⑤는 open 아님 + status no를 "막힘 RG1 공식 테제 훼손(카드 재수락 전)"으로(fail-open 함정 제거), 알림 `2:RG1DMG`는 값이 바뀔 때만 예외 줄. **D1 = c**: 계산기 G2의 `lines_open` 항 삭제 — 열린 멈춤 선은 `pauses.new_buy`(REVIEW_LINE_OPEN, portfolio_exposure.py 1378~1386행)가 막는다(portfolio-exposure-review.md 27·321행 확인).

# 3. 테스트

| 실행 | 변경 전(기준선) | 변경 뒤 |
|---|---|---|
| `-p "test_auto_core*.py"`(worktree, Windows Python 3.13) | Ran 423 · 실패 1 · 건너뜀 1 | Ran 450 · 실패 1 · 건너뜀 1 → Judge 1차 수정 뒤 Ran 453 · 실패 1(같은 PLTR) · 건너뜀 1 |
| `-p "test_auto_core_rg1_oracle_parity.py"`(Judge 1차 수정 뒤) | — | Ran 7 OK(1차 4 + 새 3) |
| `-p "test_score_*.py"` | (전체 스위트 기준선에 포함) | Ran 66 OK |
| `-p "test_decision_journal_cards.py"` | (전체 스위트 기준선에 포함) | Ran 36 OK |
| 전체 스위트 `-p "test_*.py"`(test-runner 서브에이전트, Haiku) | 수집 3212개(HEAD 사본 — 아래) | Ran 3210 · 실패 21 · 오류 9 · 건너뜀 3(수집 3239개) |
| `t2rc-oracle.py selftest --repo <메인 체크아웃>` | PASS(앵커 5 참) | PASS(앵커 5 참, S1~S9·S16 포함) — Judge 1차 수정 뒤 다시 PASS(fails []) |
| `validate_schema_contracts.py` | — | PASS(errors []) |

- 실패 1건은 변경 전후 같은 것: `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR')` — `['CARD_SECTION_CHANGED', 'CARD_NOT_ACCEPTED_IN_WATCHLIST']`. HEAD 등록부의 PLTR 항목과 관심 명단 상태(범위 밖 자료). Cowork 기준선(Linux)의 두 번째 실패 `test_auto_core_risk1r …as_before`는 Windows에서는 통과(OS별 값 — hwm-fix 확인과 같음).
- 전체 스위트 기준선: 변경 전에 전체 스위트를 재지 않아서, HEAD를 `git archive`로 스크래치 폴더에 푼 사본(추적 파일만, CRLF)에서 같은 명령으로 쟀다. 이 사본은 git 체크아웃이 아니고 git이 무시하는 상태 파일(stock-strategy-system/portfolio_state.json 등 — worktree에는 생성 때 복사되어 있음)이 없어 Ran 3113 · 실패 28 · 오류 249(246건이 그 상태 파일 FileNotFoundError, 2건 `git ls-files`)로, 수치를 그대로 비교할 수는 없다. 그래서 다음 세 가지로 확인했다.
  - 테스트 ID(discovery, 실행 없이): worktree 3239 = 기준 사본 3212 + 27. 늘어난 27개는 모두 새 두 파일이고, 기준에만 있는 ID는 0개(Ran 감소 없음). Ran 3210 < 3239는 setUpClass 오류가 난 3개 클래스의 테스트가 돌지 않은 탓으로 본다(아래 오류 목록; 클래스별 개수는 세지 않음).
  - worktree 실패 21·오류 9의 ID는 모두 기준 사본에도 실패·오류로 있다. 예외는 `test_evaluate_timing_integration…test_i0b_t1_timing_position_left_in_policy_still_fails_on_anchor_mismatch` 하나로, 기준 사본에서는 상태 파일이 없어 ERROR, worktree에서는 실제 상태 파일(무시 대상, 10-17 06:15 작성)의 "SOXL holdings 53 != anchor less confirmed tranches 75"로 FAIL이 난다. 이 테스트는 바뀌지 않은 evaluate_alerts.py·validate_technical_snapshot.py와 상태 파일만 읽는다(auto_core·등록부·계산기 참조 0건, grep). 그래서 이번 변경과 무관한 자료 상태로 본다. 상태 파일을 기준 사본에 복사해 다시 재려던 명령은 권한에서 거부되어 하지 않았다.
  - worktree 실패 21 = PLTR 등록부 1 · 위 timing 1 · instrument_identity 1 · materialize_instrument_identity 1 · materialize_kiwoom test_12 1 · portfolio_decision_dashboard grade_b 1 · scheduled_prompt_kiwoom_profile 1(docs/claude/scheduled-prompts/pending-cardreuse/diff-v3.2-v3.3.txt) · v2_6_7_session_aware_kiwoom_priority 14. 오류 9 = workspace/outputs의 무시 대상 산출물이 없는 FileNotFoundError 8건(holding_baseline_observation_audit setUpClass, mvll_canonical_volume_lineage setUpClass, nbis_v3, nbis_v4 2건, portfolio_decision_order_intent, provider_limitation_audit setUpClass, validate_research_packet)과 materialize_kiwoom test_05(source artifact missing) 1건. 결론: **새 실패 0**. (전체 스위트는 Judge 1차 수정 뒤 다시 돌리지 않았다 — 추가 범위 4가 정한 재실행 목록에 없고, 수정은 계산기·parity 테스트뿐이며 계산기를 import하는 테스트는 parity 파일 하나다.)
- 새 테스트 27개(`test_auto_core_rg1_damage.py` 23 · `test_auto_core_rg1_oracle_parity.py` 4; Judge 1차 수정으로 parity에 3개 더해 30개 — 10절):
  - S1 사건 날 훼손 → open·no(base 86에서 닫힘·ok) / KST 날짜 재수락 → 86 닫힘·ok · S2 재기준(사건 85) → no(base 91 닫힘) · S3 시간 소멸 → open·no·RG2 ok(base 80 시간 소멸 닫힘) · S4 닫힌(76) 뒤 훼손 → no·open False·`RG1_THESIS_DAMAGE:D4`·closed_at 76 · S5 사건 없음 → no·rg {"RG1": "no"}·`rg1_damage` · S6 해제 경계(a = 미국 날짜 → 막힘, a = KST 날짜 → 해제, a > 평가 세션 → 막힘, announced_at 없음·오프셋 없음·못 읽음 → 막힘, "Z" → +00:00, accepted 형식 불량 → 막힘) · S6b 소급 해제 금지(사건 70·훼손 73·76~78 충족·79부터 DS1·85 재수락 → open·no(RG1 ok, RG2 no), base도 open·no, rel 날 재수락 → 76 닫힘·ok) · S7 W[0] 막힘·W[0]−1 무시 · S8 `portfolio_accepted_on`·`card_accepted_on` 단위 + decide 통합(SOXL만 재수락 → 포트폴리오·SOXL 해제, MU만 막힘, 상태 "…|MU") · S9 MSFT IR 사실 → `load_research` damage에만(표지), facts·facts_seen·근거 official에 없음, 사건 목록 같음(EV3b 없음), root false·등록부 키 없음 → SOURCE_HOST_NOT_OFFICIAL로 버림 · S10 스키마(실제 등록부 통과, 키 없음 통과, 대문자·scheme·경로·점 없음·중복·문자열 실패) · S11 요건 ⑤ 새 문구 + 기존 세 가지 출력 글자 그대로 · S12 알림(처음·값 바뀜만 예외 줄, push 참, 기존 예외 줄 뒤, 종목·fact_id 없음, 같은 값 반복 안 함, 막힌 종목이 늘거나 줄면 한 번 더, 미해제 없으면 상태·줄 없음) · S13 엄격성(시드 60개, base 커밋 a9ea338 규칙으로 잰 (status, open)을 상수 `BASE`로 고정 — base가 ok 아니면 새것도 ok 아님, 사실 없으면 같음; 재수락 날 이전 평가 세션 최대 3개씩 잘라 `card_accepted_on` 있음/없음 결과 dict 완전 일치, 20건 초과를 단언) · S14 훼손 없음 → `rg1_damage` 키·`2:RG1DMG` 없음, by_symbol 키 3개 그대로 · 대등: S1~S9·시드 경우(사건 index ≥ 50인 것)에서 코어와 계산기 status·RG1 일치(재수락 있음/없음 둘 다) · S15 적재 대등(오프셋 없는 사실이 든 기록은 양쪽 모두 기록 범위·사실에서 빠짐, 결정 시각 뒤 announced_at·event_session > 기록 세션·summary 201자 사실은 양쪽 모두 안 씀, 같은 평가 세션 기록 2개의 같은 fact_id는 양쪽 모두 기록 날 순 첫 판, 계산기 C7 history는 그 기록을 그대로 읽음) · ③ 사실은 계산기 `validate_facts` 기본 호출에서 DOMAIN으로 버려짐.
- 기존 테스트 입력 수정(미리 허용한 1곳): `manage-us-stock-strategy/tests/test_auto_core_decide.py` 666~670행 `DamageWindowTests.test_old_damage_fact_keeps_rg1_no` — 픽스처 accepted.date 2026-10-01이 훼손 사실(DAYS[event+2] ≈ 2026-09)보다 뒤라 새 규칙으로 해제되어 (False, 'ok')가 나왔다. 영문 주석 1줄("ev-rg1-hyper: the card must be accepted before the damage fact so it stays uncleared") + 그 테스트의 임시 등록부 파일에서 모든 카드 accepted.date를 DAYS[event](훼손 앞)로 다시 쓰는 4줄. 단언은 그대로, helpers.py 기본값 불변. 그 밖의 기존 테스트 수정 없음(risk1r GOLDEN 포함 고치지 않고 통과).

# 4. 멈춤·범위 문제

멈춘 곳 없음. 지시문 문구와 구현 방식이 다른 곳(결과는 같음 — Judge 확인 대상):
1. G-2 "validate_facts 결과를 쓰는 곳을 모두 찾아 표지 사실을 뺀다": 표지 사실을 만들고 소비처마다 빼는 대신, `validate_facts`가 `damage_domains` 인자를 받았을 때만 ③ 사실을 받게 했고 이 인자는 `load_rrec1_records` 한 곳만 넘긴다. 다른 호출은 지금처럼 DOMAIN으로 버리므로 출력이 base와 글자까지 같다(6절 표).
2. D1 = c: `lines_open` 정의와 `and not lines_open`만 지우는 대신, S16에서 합성 S7로 G2를 부르기 위해 G2 식을 `g2_buy()`로 옮겼다(남은 항 글자 그대로, 호출 결과 값 그대로). `gates_check` 전체는 파일 읽기(t1·reconcile)가 있어 합성 입력으로 부를 수 없다.
3. 기존 테스트 입력 수정은 주석 1줄 + 입력 4줄(3절). 지시문 예상 대상과 같은 테스트.
4. 대등 테스트의 시드 경우는 사건이 index 50 이전인 것을 뺐다: 계산기는 EMA50이 없는 날 루프를 멈추고 모두 unk로 두는 자기 규칙이 있다(1154행, 이번 변경 전부터). 범위 밖 차이.
5. 계산기·코어의 이미 있던 기록 검사 차이(범위 밖, 이번에 고치지 않음): 계산기 최소 검사는 fact_id 패턴(4~80자)·direction "−"(유니코드 빼기) 허용·호스트 추출(정규식, 포트 포함 가능)·record_day가 W[0]이고 평가 세션이 W[0] 전인 경계 기록이 코어와 다를 수 있다. 마지막 경우 같은 fact_id가 경계 기록과 창 안 기록에 다른 판으로 있으면 "첫 판"이 갈릴 수 있다(코어는 경계 기록 판 — event_session < W[0]이라 무시, 계산기는 창 안 판).

# 5. 실데이터 (읽기 전용, 메인 체크아웃 입력, 출력은 스크래치 폴더만)

1. 연구 기록 2026-10-13~2026-10-17(최신 10-17, 평가 세션 10-12~10-16): official_facts 0건 · root_thesis_damage 0건 · ③ 도메인 호스트 사실 0건.
2. 코어 rrec1 재계산(worktree 코드, 평가 세션 2026-10-16, 봉 = 메인 pages + corporate-actions, 달력 = Production 스냅샷, 연구 기록 = 메인, ev4 = 이전 decide 기록 ev4_open 세션 + 그날 → [10-14, 10-15, 10-16], EV3a = 회복 관문 문서): 포트폴리오 결과 dict가 10-17 decision.json `shock`(by_symbol 제외)과 **완전히 같음**(event 2026-10-16 [EV2, EV4], rg RG1 no·RG2 no·RG3 no·RG4 ok, status no, ev3b_coverage_start 10-12). 8종목(BE·DELL·LITE·MU·MVLL·NBIS·PWR·SOXL) {status, open, rg} 모두 `by_symbol`과 같음. `rg1_damage` 키 없음.
3. 계산기 비교(worktree 판 vs base 판 5607b09b…, `check --day 2026-10-16`·`--day 2026-10-17` `--repo <메인>`): 두 날 모두 NOT_CHECKED(INPUT_SHA_MISMATCH — 그 뒤 registry·watchlist 등이 바뀜)로 `oracle_sha256` 말고 같음 → 양쪽 `--ignore-input-sha`: 두 날 모두 INFO_MATCH, requirements diffs [], 요건 ⑤ 8종목 no, JSON이 `oracle_sha256` 말고 같음. Judge 1차 수정 뒤 판(9f0e2238…)으로 같은 8실행을 다시 함: 기본·`--ignore-input-sha` 모두 base 판과 `oracle_sha256` 말고 같음(INFO_MATCH, requirements diffs []).
4. 가정 실험(합성 MSFT 사실 1건 `https://www.microsoft.com/en-us/investor/TEST`, root_thesis_damage true, event_session 2026-10-14, announced_at 2026-10-14T16:05:00-04:00, 표지 붙임, 실제 봉, SOXL): 카드 2026-10-04 → `rg1_damage` ["TEST-MSFT-CAPEX"], 수락일 2026-10-15 사본 → 키 없음(rel = 10-15 ≤ a ≤ 10-16). 두 경우 모두 status no·open True·rg 그대로, 그 밖 키·사건 목록이 사실 없는 결과와 같음(EV3b 없음). U(t): 코어 `uncleared_damage` ["TEST-MSFT-CAPEX"] / [] · 계산기 `rg1_uncleared` 같은 값.

# 6. 계산기 표지 사실 소비처 (G-2)

| 위치(t2rc-oracle.py) | 쓰는 곳 | ③ 사실 |
|---|---|---|
| `cmd_check` 1555행 `validate_facts(rr, …, prev_seen)` | 오늘 사실 → `res["facts"]`(valid·dropped), `circuit_for_session`(근거·new 표시·r_max), `c7_facts` | 인자 없음 → DOMAIN으로 버림(base와 같음) |
| `load_research_history` 1406행 | `history` → C7 사실(최근 10기록), `research_history` 파일 목록 | 인자 없음 → 버림 |
| `load_rrec1_records` 1434행 `damage_domains=…` | `env["rrec_records"]` → `buy_requirements`의 `rrec1`(RG1 U(d)만; EV3b는 표지 사실 제외) → 요건 ⑤ 상태·`detail[sym]["rrec1"]` | 표지 달고 받음 |

`validate_facts` 사슬(Judge 1차 수정): `official`(sec.gov·그 종목 official_domains)·`marked`(공식 아님 ∧ root_thesis_damage is True ∧ `damage_domains` 일치)를 사슬 전에 구하고 `if host is None: URL` → `elif not official and not marked: DOMAIN` → SOURCE_KIND·WRITTEN_BEFORE_CLOSE·WRITTEN_AFTER_DECIDE·EVENT_SESSION(글자 그대로) — ③ 사실도 남은 검사를 모두 거친다(코어 check_record와 같음). 인자 없는 두 호출은 marked가 늘 거짓이라 base와 같다(10절 고정 입력 단언).
`validate_facts`의 다른 호출은 없다(grep). `detail[sym]["rrec1"]`은 `circuit_detail` 출력 키(role·registry·status·buy·sell·sell_target)에 들지 않는다.

# 7. sha256 (Windows worktree 바이트, 2026-10-18 — Judge 1차 수정 뒤)

| 파일 | sha256 | Judge 1차 표와 |
|---|---|---|
| docs/claude/t2rc-oracle.py | e41a79033a73a4662361a2daeaa79a6c40421069d5e7a889dc353f4e8ba7bb67 (원시 CRLF 2502/2502행) | 바뀜(수정 대상) |
| docs/claude/t2rc-check-run.ps1 | 3735492e3f6a803ee7be4a7ed2251ea2df0499e83270cd7bdaa77ca6c6cff167 (원시 CRLF 117/117행) | 바뀜(16행만) |
| manage-us-stock-strategy/tests/test_auto_core_rg1_oracle_parity.py | a2a5982fc52d887b6d4f214c15ca58bc7b4873d2f9790201caf14e332a4dc4b1 (CRLF 291/291행, ASCII) | 바뀜(추가만) |
| Judge 1차 표의 나머지 10행 = 9개 파일(rules·inputs·decide·tickets·스키마·등록부·references·test_auto_core_rg1_damage·test_auto_core_decide) + 이 보고서 | 9개 파일은 아래 1차 값과 바이트가 같음(수정 뒤 다시 잼, 9/9 일치). 보고서는 추가 범위 7로 갱신(1차 bcd0c649…) | 9개 같음 · 보고서만 바뀜 |

- 새 계산기 sha256_lf = **9f0e2238f2a8238016be5406cd2e195aaf24c232adeda5f1fba3a52cd09b1aae** = 실행기 16행 `$ExpectedOracleSha256`(일치). 실행기 sha256_lf = fcd8977bac37034e7805dda7dd31756b8b6a224c6cdec673d45189c0cd1680a7. 계산기 `check` 출력 `oracle_sha256`도 9f0e2238…(5절 3).

1차(Judge 1차가 잰 값과 같았던 표 — 수정 대상 셋은 위 값으로 대체됨):

| 파일 | sha256 |
|---|---|
| manage-us-stock-strategy/scripts/auto_core_rules.py | 48433ab8d4c5eae45f9c6e54740e282cf5004807f5ce75842f64ea8cc4fbab4e |
| manage-us-stock-strategy/scripts/auto_core_inputs.py | 6e0f2cf1d6302c87612a41fb06b0ddd347eb279aef0f45d5bccd26b013b49201 |
| manage-us-stock-strategy/scripts/auto_core_decide.py | 1013da08704fb74d7afb30455403d6d3e31f67d75392e93d1242f3c5cb7448f1 |
| manage-us-stock-strategy/scripts/auto_core_tickets.py | 2393fa7b19352fd435846aa67d68604b74ca1d73fb9a0e51b845931433afb8c1 |
| manage-us-stock-strategy/schemas/auto-core-card-registry.schema.json | 5b69e590f16542306ba2af88e72d9e3db434e29e50b3b7cfc3834def713c791e |
| docs/claude/card-evidence-registry.json | 1654aa0d7a525e167452d62800cb9f80237d29649b95e52f0343498cc83abdb8 |
| docs/claude/t2rc-oracle.py | c923d43c749da85581d390eb9e52fd3c730b63874816d1d10116d2aca8fd9501 (원시 CRLF) |
| docs/claude/t2rc-check-run.ps1 | 8a786cbcdfdb6a8e4443a1e8f9e00ae3744ed2ebcd74d7bd4ba605aa936d4209 (원시 CRLF) |
| manage-us-stock-strategy/references/auto-core-decision.md | c47bbc876a12a9263b1d24f6d058131c01ba019a6a0aad7d6ba4c50ad09886a8 |
| manage-us-stock-strategy/tests/test_auto_core_rg1_damage.py | d4c8e9a202f145130b404b490caec9d3f41ce4e38285f400eaef32a05a0b4464 |
| manage-us-stock-strategy/tests/test_auto_core_rg1_oracle_parity.py | ddbc98988e1ddbb31039fba715c28ef34881d60f4fa314759840fbd7b4f258c2 |
| manage-us-stock-strategy/tests/test_auto_core_decide.py | 0b6866a2f564b5faa342d662df478644dc72ffb85b77f2b8c36412533c98519c |

- (1차) 계산기 sha256_lf 88c3365b… · 실행기 sha256_lf 8262212d… — Judge 1차 수정으로 위 9f0e2238… · fcd8977b…로 바뀜. 사전 등록 49행 고정값(계산기 5607b09b… · 실행기 5d3502b9…)은 병합 뒤 Cowork가 새 값으로 갱신.

# 8. 남은 위험

- (a) 같은 KST 날짜 안에서 발표보다 먼저 한 재수락은 날짜 단위라 해제로 본다.
- (b) 잘못된 훼손 사실도 카드 재수락 전까지 매수를 막는다(예외 손 1번/종목, 알림 `2:RG1DMG`로 보임). 매도는 막지 않는다.
- (c) 통합 점검 규칙 파일·로더가 교체되기 전에는 포트폴리오 RG1이 통합 점검 판정과 달라 비교 B7 "RREC:RG1"이 날 수 있다(훼손 사실이 있을 때만).
- (d) 관심 카드 수락은 코어가 관심 명단 cardStatus로, 해제는 등록부 accepted.date로 본다 — 두 기록이 어긋나면 해제가 늦거나 빠를 수 있다.
- (e) `thesis_damage_domains` 목록 변경은 K3(스키마 description에 적음).
- (f) D1 = c: 일지 검토가 끝난 L2(멈춤 표지 없음)에서 계산기 G2가 코어와 같아진다(S16). 열린 L2 멈춤은 `pauses.new_buy`로 계속 false.
- (g) 표시만 달라지는 곳(fail-open 아님): 채점기는 R3 막힘을 shock.open False라 rrec1_key NONE(score_decision_journal.py 1413~1415행) → DISPLAY_ONLY(1709~1710행)로 분류하고, 대시보드 runCore.shock에는 status가 없어(auto_core_decide.py 1239행) 막힘인데 '닫힘'으로 보인다 — 요건 ⑤ 칸과 알림 `2:RG1DMG`에는 막힘으로 보인다.
- (h) KST 아침 재수락은 한 세션 늦게 풀린다(a ≤ d, a = KST 날짜, d = 미국 세션 날짜).
- (i) 4절 5의 이미 있던 기록 검사 차이(경계 기록의 fact_id 판)는 코어·계산기 RG1이 갈릴 수 있는 남은 경로다 — 같은 fact_id를 다른 판으로 다시 쓰는 일이 드물어 낮음. 갈리면 MISMATCH(엄격 쪽)로 보인다.
- (j) 후속 후보(NO_CHANGE, Judge 1차 발견 5(b)): 호스트 추출이 다르다 — 계산기 정규식 `^https://([^/]+)`, 코어 `urlsplit().hostname`. 포트·경로 없는 쿼리가 든 URL에서 갈리며 base부터 있던 차이로, 오늘 사실·C7에도 영향이 있다. 훼손을 60세션 붙잡아 영향이 커지므로 Cowork가 관제판에 별도 후보로 올린다.
- (k) 알림 ⑦은 push 줄 최대 3개(auto-core-alert.txt 61~62행)라 기록 모드에서 앞선 줄이 3개 이상인 날 `2:RG1DMG` 줄은 "외 N건"으로 접히고, 상태는 저장되어 다음 날 다시 울리지 않는다(Judge 1차 발견 5(c)). 막힘 자체는 요건 ⑤로 유지 — 표시 위험.

# 9. 하지 않은 것

커밋·푸시, 예약 작업·관제판·사전 등록 문서·알림/통합 점검 지시문·CLAUDE.md 수정, 정책·상태·장부·일지·workspace 쓰기, 키움 호출, auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행 — 모두 없음. 병합·고정값 교체 효력·C1 재시작은 Judge PASS 뒤 Cowork·사용자 몫(지시문 "병합" 절).

# 10. Judge 1차 FAIL 수정 (2026-10-18, 지시문 끝 "추가 범위")

- 근거: docs/claude/ev-rg1-hyper-judge-report.md(sha256 307984a350e1a1f94775669c268bb0811cf0ab6b5b16a0b891c7c4930770d9c7, `VERDICT: FAIL`) 항목 6·고칠 최소 항목 1~4를 원문으로 읽음. 수정 전에 13개 파일 sha256이 Judge 1차 표와 모두 같음을 확인했다.
- 고친 줄(t2rc-oracle.py `validate_facts`, 수정 뒤 829~836행): 주석 1줄 + `official = host is not None and any(... doms)` + `marked = host is not None and not official and f.get("root_thesis_damage") is True and any(... damage_domains)` + `if host is None: URL` → `elif not official and not marked: DOMAIN`. 그 아래 SOURCE_KIND·WRITTEN_BEFORE_CLOSE·WRITTEN_AFTER_DECIDE·EVENT_SESSION 가지는 글자 그대로. docstring에 "goes through the same remaining checks" 한 구절. 그 밖의 계산기 줄은 바뀌지 않음(diff +273/−20, 1차 +272/−20).
- 재현(스크래치 사본에 수정 전 사슬을 되돌려 같은 입력): 토요일 event_session ③ 사실과 source_kind "BLOG" ③ 사실을 수정 전 사슬은 둘 다 받고(keep), 수정 뒤 사슬은 각각 `EVENT_SESSION`·`SOURCE_KIND`로 버린다.
- 테스트(test_auto_core_rg1_oracle_parity.py `LoaderParityTests`에 추가만, 기존 4경우 불변):
  - `test_domain_fact_on_a_non_session_day_is_dropped_by_both` — microsoft.com ③ 사실, event_session 2026-09-05(토): 코어 `load_research` damage와 계산기 `load_rrec1_records` 모두 그 사실이 없음(남는 것은 표지 없는 DMG-F1뿐), 계산기 `validate_facts` dropped `[["DMG-SAT", "EVENT_SESSION"]]`.
  - `test_domain_fact_with_an_unknown_source_kind_is_dropped` — source_kind "BLOG": 계산기는 그 사실만 버림(`SOURCE_KIND`), 코어는 스키마 enum으로 기록 전체 무효(damage []·sessions []) — 영문 주석 1줄 "record-level difference already there, out of scope".
  - `test_default_call_matches_the_base_calculator` — `damage_domains` 없는 기본 호출: 고정 입력 8사실(공식·다른 호스트·나쁜 kind·비거래일·http·나쁜 방향·직전 세션 본 것/안 본 것(U+2212 빼기))에서 새 `validate_facts` (keep, dropped) = base 계산기(5607b09b…)로 잰 상수 `BASE_KEEP`·`BASE_DROPPED`(base 사슬은 테스트에 옮겨 적지 않음).
- 다시 잰 결과: parity Ran 7 OK · `test_auto_core*` Ran 453 · 실패 1(PLTR, 그대로) · selftest PASS · 실데이터 check 10-16·10-17 worktree 판 vs base 판 `oracle_sha256` 말고 같음(기본 NOT_CHECKED, `--ignore-input-sha` INFO_MATCH·requirements diffs []).
- 범위 밖으로 둔 것: Judge 발견 5(b) 호스트 추출 → 8절 (j) NO_CHANGE · 5(c) 알림 ⑦ 3줄 접힘 → 8절 (k).
- 덧: 테스트 실행 중 생긴 무시 대상 `manage-us-stock-strategy/scripts/__pycache__/`(dual_run_scheduler·validation_common .pyc, 05:03)는 지웠다(추적 파일 아님).
