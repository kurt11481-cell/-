---
id: policy-a-judge-prompt
title: "policy-a Judge(읽기 전용, Opus) — 정책 묶음 A"
date: 2026-11-26
status: "승인됨(사장 카드 2026-11-26 22:28:38 KST '안1 착수'). Builder 보고 뒤 실행. worktree 경로는 Builder 보고 첫 줄을 따른다. 보완 1(2026-11-26 KST, Builder BLOCKED 뒤 지시문 '테스트' 절 ③ 추가)에 맞춰 1번 고침 · 보완 2(같은 날, (ㄷ) 기준을 주문표 금액으로·(ㄴ) 허용 칸 추가)에 맞춰 1번 다시 고침"
---
너는 파일을 고치지 않는 독립 Judge다. Builder worktree(Builder 보고 docs/claude/policy-a-report.md 첫 줄에 적힌 경로, 브랜치 worktree-policy-a)의 커밋하지 않은 변경을 기준 커밋과 비교해 본다(git -C <worktree> diff --ignore-cr-at-eol, status). 보고는 본 저장소 docs/claude/policy-a-judge-report.md 한 파일에만 쓴다(쓸 수 없으면 자기 worktree의 같은 경로에 쓰고 그 경로를 답에 적는다). 먼저 읽는다: 지시문 docs/claude/policy-a-builder-prompt.md(sha256이 Builder 보고 둘째 줄과 같은지 먼저 본다 — 다르면 FAIL), Builder worktree의 docs/claude/policy-a-BLOCKED.md(멈춘 기록), 제안 docs/claude/policy-a-proposal-2026-11-26.md(2절 사실 표·3절 안 1·9절 결정 기록), Builder 보고, CLAUDE.md Hard safety·Change classes.

1. diff 파일이 허용 파일뿐이다. 기존 테스트 고침은 지시문 '테스트' 절의 세 종류뿐이고 보고 표와 하나씩 맞는다(옛 add_default 동작을 시험하는 곳이 적어도 하나 남음). ③은 지시문에 적힌 8곳(파일::함수)뿐이다. (가)는 diff가 정책 사본을 넣는 줄만 더했고 기대값 줄은 그대로다. (나)는 test_policy_a.py에 1.0 사본으로 옛 기대값(옛 해시 글자 그대로)을 단언하는 짝 시험이 있다. 8곳의 바뀐 칸 표에 SOXL·TQQQ 매수 제안·주문표, S7 채우기 권고·omitted, 그 막음 사유, 딸린 합계·건수, 바뀐 S7 산출을 가리키는 식별자·해시(그 주문표의 종목·수량·가격·금액이 같고, 가리키는 S7 산출의 다른 칸이 표에 있으며 그 칸도 허용 칸뿐일 때만) 밖의 칸이 있으면 FAIL(결정 status 차이는 까닭이 '3배 매수 주문표가 없어짐'일 때만 허용). 정책 지문 칸을 빼고 비교한 곳은 그 키 경로가 정말 정책 지문인지 코드로 본다. 새 단서 3곳은 수치(3배 합·여유·가장 큰 목표·근거 단계 비율·주문표 금액·최소 금액)가 있고, 주문표 금액이 auto_core_tickets.py가 최소 금액 판정에 실제로 쓰는 값(보고에 적힌 행)과 맞으며, 주문표 금액 ≥ 최소 금액인데 주문표가 없는 곳이 없고, 한 곳 이상이 (가)다. 원인이 add_default로 밝혀진 곳은 ①로 적혔고 (가)로 고쳤다. test_policy_a.py에 D.i(i-1~i-3)가 있다. scripts에 정책 주입용 새 코드 없음. tests/s5_exposure_fixtures.py·tests/fixtures/** 무변경.
2. alert_policy.json의 바뀐 곳은 새 3배 상한 키(값 0.10)와 add_default뿐이다. 문턱 1.55·1.85·1.25·1.9, reduce_order(끝 SOXL), single_stock_nominal_cap 0.4, single_stock_cap_exempt, nominal_multipliers, allowed_index_etfs, 권한 표지 줄(order_authority·quantity_authority·execution_quantity·kill_switch·hard_ceiling) 무변경. JSON 파싱·CRLF·들여쓰기 원래대로. auto_core_tickets.py(POLICY_EXPECTED 포함)·schemas/ 무변경. S7 산출 `policy` 칸(portfolio_exposure.py 1539~1543행 부근)에 새 필드 없음.
3. 3배 상한이 '늘리는 종목이 배수 3 이상일 때만' 걸린다: S7 채우기(add_recommendations)·new_buy_within_band·swap_buy_leg 매수 다리 모두 같은 함수로 막히고, 1배 매수·매도·줄이기 권고(1146~1195행 부근)·cap_breaches·fail-closed는 그대로다. 반례를 직접 찾는다: 3배가 이미 10% 위인 날 1배 매수가 막히는가 / 3배 상한이 줄이기 권고나 매도 주문표를 새로 만드는가 / auto_core_tickets.py hold_range가 _plan_buy를 다시 부를 때(785~817행 부근) 이 막음을 우회하는가.
4. 채우기·줄이기 분리가 완전하다: supplement를 읽는 줄이기 쪽 세 곳(portfolio_exposure.py 1165행 부근, run_portfolio_exposure_review.py 527행 부근, manage-us-stock-strategy/scripts 코어 본체 스크립트 163행 부근 — 읽기만, 명령에 그 파일 이름을 넣지 않음) 동작 그대로, 채우기 쪽에서 SOXL이 나오는 길 없음(scripts의 `supplement`·`reduce_order` grep 대조). auto_core_decide.py의 S7 제안 목록에서 basis_met만인 SOXL이 빠지고 new_basis_met 갈래는 그대로.
5. 옛 add_default 값이면 바꾸기 전과 같은 결과(뒤로 맞음) — 테스트로 확인.
6. 새 키가 없거나 틀리면 ExposureError(기본값 없음)이고, 그 경우 코어가 FAIL(auto_core_decide.py 485~487행)로 끝난다는 점을 보고가 적었다.
7. 3배 상한 비중의 분모(S7 equity, portfolio_exposure.py 1370행 부근)와 '그날 코어 표시 비중'(auto_core_tickets.py 185행 부근 rule_file_nominal의 total)의 분모를 대조해 같은지·다르면 차이가 보고에 있는지 본다.
8. 대상 테스트 전부 통과(기준선 밖 새 실패 0, 새 테스트 skip 없음), 스키마 감사 PASS. 가능하면 대상 패턴을 직접 다시 돌린다: `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"` 글자 그대로(auto_core 쪽은 -p "test_auto_core*"), PATH의 python이 3.15이고 tzdata가 없으면 `python` 자리만 `py -3.13`.
9. 정책·scripts의 새 줄에 권한 표지 글자·주문 경로 문자열(`/api/us/ordr`, `ust2000x`, `kiwoom_order`, `order_submit`)이 없다(test_policy_a.py 안에서 값을 읽어 비교하는 키 이름은 허용). 상태·일지·원장·예약·대시보드 쓰기 없음.
10. 연결표 ②③⑤의 원문 행을 저장소에서 대조(고친 뒤 행이 밀렸으면 지적). ⑤의 '알림 경로 확인 필요'가 끊김으로 적혀 있고 막는 장치가 적혀 있다.
마지막 비지 않은 줄은 `VERDICT: PASS` 또는 `VERDICT: FAIL`(FAIL이면 이유 목록 위에).
