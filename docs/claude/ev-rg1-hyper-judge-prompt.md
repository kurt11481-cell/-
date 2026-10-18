---
id: ev-rg1-hyper-judge-prompt
title: ev-rg1-hyper 독립 Judge (읽기 전용)
date: 2026-10-17
class: K3 독립 Judge — docs/claude/ev-rg1-hyper-builder-prompt.md의 변경(코어 RG1 + 빅테크 훼손 출처 + 독립 계산기 RG1·실행기 고정값)을 판정
model: Opus · xhigh · 새 세션(메인 체크아웃, worktree 아님) — Builder 세션과 다른 세션
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 키움 주문 도구 금지
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(메인 체크아웃) · 이유: K3 독립 Judge(매수 관문 의미 + 독립 계산기 고정값)

너는 이 변경을 만들지 않은 독립 검토자다. **파일을 고치지 않는다.** 저장소 안에 쓰는 파일은 맨 끝의 보고서 1개뿐이다(예외: 저장소 밖 임시 폴더의 계산기 `--out`·합성 입력 파일). Builder 보고서의 숫자·주장은 위치 안내일 뿐이다 — 판정은 네가 연 원문과 네가 다시 계산한 값으로 한다. 이 판정은 독립 계산기의 새 고정값을 확인하는 "Judge 확인"(t2-rc-preregistration-2026-10-14.md 1절 C1)도 겸한다.

## 읽을 것

1. 지시문: docs/claude/ev-rg1-hyper-builder-prompt.md(메인 체크아웃) — 특히 "새 RG1 규칙" R0~R8, "결정 항목" D1의 기록된 답과 D2 처리. 결정 원문: docs/claude/event-strategy-2026-10-13.md 11-1·11-1a, docs/claude/pre-on-roadmap-review-2026-10-15.md 3절·결정 기록(rrec-k3-timing d). 승인 정의: docs/claude/recovery-gate-R-REC1-2026-10-09.md 37·43행. 사전 등록: docs/claude/t2-rc-preregistration-2026-10-14.md 전문.
2. Builder 보고: .claude/worktrees/ev-rg1-hyper/docs/claude/ev-rg1-hyper-report.md
3. 변경: `git -C .claude/worktrees/ev-rg1-hyper diff`, `git -C .claude/worktrees/ev-rg1-hyper status --porcelain --untracked-files=all`. 대상 — scripts/auto_core_rules.py·auto_core_inputs.py·auto_core_decide.py·auto_core_tickets.py, schemas/auto-core-card-registry.schema.json, references/auto-core-decision.md, docs/claude/card-evidence-registry.json, docs/claude/t2rc-oracle.py, docs/claude/t2rc-check-run.ps1, 새 테스트, (입력만) tests/test_auto_core_decide.py.
4. 읽는 곳(L3): auto_core_compare.py 130~160·265~292, auto_core_decide.py 398~475(알림 상태)·640~660·736·1000~1095, auto_core_replay.py(damage []), score_decision_journal.py 1328~1345·1396 부근, auto_core_tickets.py 210~278, portfolio_exposure.py 1378~1388(D1), references/portfolio-exposure-review.md 27·321행, integrated-check-prompt-v3.12.6-2026-10-15.txt 102행, scheduled-prompts/integrated-check-daily.txt 37·52~72행, scheduled-prompts/event-pre-open-calendar.txt 15행.

## 돌려도 되는 것

- worktree 안에서: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"`("auto_core.py"가 든 명령은 거부되니 이 패턴으로만), `-p "test_score_*.py"`, `-p "test_decision_journal_cards.py"`, `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`, `python docs/claude/t2rc-oracle.py selftest --repo <메인 체크아웃>`. base(메인 체크아웃)에서도 같은 명령으로 비교한다(메인 작업 트리의 커밋 안 된 docs 변경 — 예: PLTR 등록부 항목 — 때문에 생기는 실패는 base·worktree 모두에서 보이는지로 가린다).
- 파일을 쓰지 않는 python으로 재계산·합성 실험(코어 함수와 계산기 함수를 직접 부른다). 계산기 `check`는 `--repo <메인 체크아웃> --out <저장소 밖 임시 파일>`로만, worktree 계산기와 base 계산기 각각 `--day 2026-10-16`·`--day 2026-10-17`(입력 sha 차이로 NOT_CHECKED면 양쪽 `--ignore-input-sha`).
- 금지: 키움 호출(이 판정에 필요 없음), auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행, 커밋·병합, workspace/outputs·stock-strategy-system·정책·예약 작업·관제판 쓰기.

## 판정 항목

| # | 항목 | PASS 조건 |
|---|---|---|
| 1 | 범위 | 바뀐 파일이 지시문 "지켜야 할 것" 1의 목록뿐(+ Cowork가 지시문 "추가 범위"로 허용한 것). 등록부 diff = `thesis_damage_domains` 한 줄뿐(줄 끝 주변과 같음). 실행기 diff = 16행뿐. 기존 테스트 변경 = 미리 허용한 "카드 수락일 입력 + 주석"뿐(단언 변경 0). auto_core_compare·replay·score_decision_journal·portfolio_exposure·예약 지시문·사전 등록·정책 불변 |
| 2 | 권한·안전 | 권한 표지 줄(order_authority·quantity_authority·execution_quantity·kill_switch·ORDER_TICKET_HUMAN_ENTRY) 변경 없음, 주문 경로 없음, 스크립트 ASCII, 줄 끝은 worktree에 체크아웃된 그대로(Windows worktree는 계산기·실행기 포함 CRLF — 일괄 변환 흔적이 없으면 PASS), 커밋 없음, 데이터 파일 쓰기 없음. 계산기가 auto_core*·manage-us-stock-strategy/scripts를 import하지 않음 |
| 3 | R0·R1 RG1 | 코어 rrec1과 계산기 rrec1이 R0 정의(창 W[0]·해제 날 max(event_session, 발표 KST 날짜)·카드 날·**rel ≤ a ≤ d 소급 해제 금지**·미해제 집합·announced_at "Z"/오프셋 읽기·accepted.date 엄격 읽기)를 같게 구현. 사건 날·재기준 전 훼손도 RG1 no(ⓐⓑ). announced_at 없음 → 해제 불가. 카드 항목 없음 → 해제 불가. 포트폴리오(코어만) = 보유 종목 가장 이른 수락일, 하나라도 없으면 해제 불가 |
| 4 | R2 시간 소멸 | 그날 RG1 no면 시간 소멸로 닫히지 않는다(코어·계산기). RG1 unk는 지금처럼 막지 않음. 모두 충족 닫힘 불변 |
| 5 | R3·D2 | 닫힌 사건과 사건 없음(지시문 "D2 처리" — 사용자가 다르게 정해 Cowork가 고쳤으면 그 기록대로)에서 미해제 훼손 → status "no", open False, rg RG1 "no", reasons `RG1_THESIS_DAMAGE:<id>`, `rg1_damage`. 요건 ⑤ 칸이 이 경우 "no"(풀리지 않음) — auto_core_tickets.py 새 가지, 기존 세 가지 출력 글자 불변 |
| 6 | R4 우선순위·대등 | 자료 없음 → EV3B 공백 → R3 → 기존 식 순서가 양쪽 같다. 계산기 rrec1에 들어가는 기록·훼손 사실이 코어와 같다(지시문 G-1-1): 오프셋 없는 announced_at이 든 기록은 기록 전체 제외(코어 스키마 검사 auto_core_inputs.py 224~227행), 사실 단위 결정 시각·event_session ≤ 기록 세션·summary 200자, 같은 fact_id는 기록 날 순 첫 판. 이 정렬이 C7이 읽는 history(1444·1454~1457행)와 오늘 사실 판정을 바꾸지 않는다. 같은 합성 입력(지시문 S1~S8 + 네가 만든 경우 3개 이상: 같은 날 훼손+EV1, 훼손 뒤 EV4 재기준, DS1 반복 중 훼손, 창 경계 W[0], 카드 재수락 경계)에서 코어 칸 `s`와 계산기 reqs[4], RG1 값이 같다 — 다르면 FAIL |
| 7 | R5 ③ 출처 | 등록부 `thesis_damage_domains` 호스트만, root_thesis_damage 참인 사실만 받는다. 받은 사실은 RG1에만 쓰인다: 코어 `facts`·근거·C7·facts_seen·EV3b, 계산기 오늘 사실·C7·new·r_max·EV3b 어디에도 없다(소비처를 네가 grep으로 전수 확인). root_thesis_damage 거짓 → 지금처럼 버림. 키 없는 등록부 → base와 같은 동작. 스키마: 선택 키, 소문자 호스트 패턴, required 불변 |
| 8 | R7 엄격성 | 해제된 사실이 없는 입력에서 새 결과가 base보다 느슨한 경우 0 — 무작위(고정 시드) 합성 입력 200개 이상으로 base 커밋 rrec1(메인 체크아웃 코드)과 worktree rrec1을 함께 돌려 확인. 재수락이 있는 입력 100개 이상에서 재수락 날 전까지 자른 입력의 결과가 해제 없는 결과와 같다(소급 해제 0 — 예: 사건 → 훼손 → 관문 충족 며칠 → DS1 → 재수락이면 결과는 열림·no). 느슨해지는 경우는 재수락 날 이후뿐임을 확인. ③ 사실로 사건 목록·C0·L0가 바뀌는 경우 0. 하나라도 다른 느슨해짐이 있으면 FAIL |
| 9 | ④ 골든 불변 | 훼손 사실이 없는 입력에서 결정·주문표·알림 상태·해시가 base와 같다: test_auto_core_risk1r GOLDEN 수정 없이 통과(Windows), 기존 decide·tickets·rules·compare·replay 테스트 수정 없이 통과(허용된 입력 1건 제외), 알림 상태 `2:RG1DMG`·결과 키 `rg1_damage`는 미해제가 있을 때만 생긴다. RG1DMG 알림은 처음·값이 바뀐 날만 예외 줄(push 참, 비교 모드 포함, 기존 예외 뒤)이고 줄에 종목 코드·fact_id가 없다(알림 지시문 56~60행 기록 모드 필터에 지워지지 않게). 알림 지시문(auto-core-alert.txt)은 바뀌지 않는다 |
| 10 | 계산기 고정값 | 네가 잰 worktree 계산기 sha256_lf(t2rc-oracle.py 108~111행 방식, 원시 바이트가 아니라 LF 정규화) = worktree t2rc-check-run.ps1 16행 값. 계산기 diff가 rrec1·그 호출 인자(1822행 accepted_on)·validate_facts·표지 사실 제외·rrec1 입력의 훼손 사실 검사·합침·(D1에 따라) 1851·1853행·selftest·docstring뿐. selftest PASS(기존 골든·앵커 불변 + 새 RG1 경우). 실데이터 `check` 10-16·10-17: worktree 출력 = base 출력(oracle_sha256 제외) |
| 11 | D1 lines_open (답 c) | `lines_open` 정의(1851행)와 G2의 그 항(1853행)만 지워지고 G2의 다른 항은 그대로. 일지 검토가 끝난 L2 사건(합성 S7 dict)에서 계산기 G2와 코어 pauses가 같은 방향, 열린 L2에서는 양쪽 막힘(pauses.new_buy REVIEW_LINE_OPEN — portfolio_exposure.py 1378~1386행). selftest S16 있음 |
| 12 | 실데이터 | 연구 기록 2026-10-13~최신 root_thesis_damage 사실 수(네가 직접 셈). 코어 rrec1 재계산(평가 세션 2026-10-16) = 10-17 decision.json shock·by_symbol(event 2026-10-16 [EV2, EV4], RG1 no·RG2 no·RG3 no·RG4 ok, status no). 가정 실험(MSFT microsoft.com 훼손 1건, event_session 2026-10-14, 발표 16:05 −04:00): 평가 세션 10-16은 사건 당일이라 RG1은 어차피 no — 해제는 코어 `rg1_damage`(카드 10-04면 [id], 수락일 10-15 사본이면 키 없음)와 계산기 U(t) 함수 값으로 확인, 코어·계산기 같음 |
| 13 | 다른 독자(L3) | 비교(auto_core_compare 270~292): 훼손이 없으면 B 분류 불변, 있으면 RREC:RG1 차이가 날 수 있음을 발견에 적음(통합 점검 규칙 파일 102행 교체 전). 알림 2:RREC 의미 불변. score_decision_journal `_shock_periods`(open 기준) 불변, R3 막힘이 채점에서 rrec1_key NONE(1413~1415행) → DISPLAY_ONLY(873·1710행)로 분류되는 것과 대시보드 runCore.shock에 status가 없어 '닫힘'으로 보이는 것(auto_core_decide.py 1206행)을 발견에 적음(코드 변경 대상 아님). 통합 점검 로더 37행·규칙 파일 102행·개장 전 15행이 병합 뒤 사실과 달라지는 문구를 목록으로 적음(Cowork 교체 대상) |
| 14 | 테스트 | 대상·전체 스위트에서 base 대비 새 실패 0, Ran 감소 없음. 지시문 S1~S14가 있고 주장대로 단언한다(이름만 있고 단언이 약하면 FAIL) |
| 15 | 병합·C1 절차 | 지시문 "병합·고정값 교체·C1 재시작" 절이 사전 등록을 느슨하게 하지 않는다: C1은 병합 뒤 첫 decide부터 0/10, 병합 전 C2 일치는 세지 않음(승인 범위에 있음), 변경 기록에 49행 고정값 넷(계산기·실행기·로더·규칙 파일)이 모두 갱신됨, 실행기 고정값과 계산기는 한 병합으로 함께 바뀜(중간에 ORACLE_SHA_MISMATCH 창이 없음), 병합 시각이 06:15 대조·07:45 decide·08:40 대조·23:30 DocsCommit과 겹치지 않음 |

## 출력

- 한국어 표 `| # | 항목 | PASS/FAIL | 근거(파일:행 / 재계산 값) |`(위 1~15), 그 아래 "발견"(R7 실험 결과 요약, ③ 소비처 전수 표, 비교 B7·통합 점검 문구 차이, 남은 위험, 의견 — 기본 NO_CHANGE), 고칠 최소 항목(있으면), 바뀐 파일 sha256(네가 잰 작업 트리 바이트 값) + 새 계산기 sha256_lf + 실행기 sha256, 마지막 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL`.
- 같은 내용을 **새 파일 하나** `docs/claude/ev-rg1-hyper-judge-report.md`(메인 체크아웃)에 저장한다. 그 밖의 파일은 쓰지 않는다.

## 재판정 (Judge 1차 FAIL 수정 뒤 — 2026-10-18 추가, Cowork)

1차 보고 docs/claude/ev-rg1-hyper-judge-report.md(sha 307984a3…, FAIL 사유 = 항목 6 계산기 `validate_facts`의 ③ 사실 검사 누락)를 먼저 읽는다. Builder 지시문 끝 "추가 범위 — Judge 1차 FAIL 수정"이 고칠 범위다. 새 세션(메인 체크아웃, Opus · xhigh, Builder·1차 Judge와 다른 세션), 파일 수정 금지는 같다.

1. **범위 고정**: worktree의 10개 파일(1차 보고 끝 sha256 표 중 t2rc-oracle.py·t2rc-check-run.ps1·test_auto_core_rg1_oracle_parity.py·보고서를 뺀 것)이 1차 표와 바이트가 같은지 잰다. 같으면 1차의 항목 1~5·7~9·11~13·15 판정은 유지한다. 다르면 그 파일에 해당하는 항목을 처음부터 다시 판정한다.
2. **항목 6 재판정**: 새 `validate_facts`에서 ③ 사실이 URL → DOMAIN(공식도 표지도 아님) → SOURCE_KIND → 작성 시각 2개 → EVENT_SESSION을 모두 거치는지 원문으로 확인. 1차의 재현(event_session = 토요일 2026-09-12 microsoft.com 훼손 사실)을 다시 돌려 코어·계산기 모두 버리는지, source_kind 불량 ③ 사실을 계산기가 버리는지 확인. `damage_domains` 없는 호출(history·오늘 사실)의 출력이 base 판과 같은지 무작위 고정 시드 입력 200개 이상으로 비교. 1차의 대등 실험(이름 붙은 28경우 + 무작위)을 새 계산기로 다시 돌려 불일치 0.
3. **항목 10 재판정**: 새 계산기 sha256_lf = 실행기 16행 값. 계산기 diff(1차 판 대비)가 validate_facts 사슬뿐. selftest PASS. 실데이터 check 10-16·10-17: worktree 판 = base 판(oracle_sha256 말고).
4. **항목 14 재판정**: parity 파일의 새 경우 3개가 주장대로 단언, `test_auto_core*.py` 새 실패 0(PLTR 1건 그대로), 전체 스위트는 1차 기준과 같은 실패 집합.
5. 출력: 1차와 같은 표 형식(바뀐 항목만 행으로, 나머지는 "1차 유지 — 바이트 동일" 1줄), 바뀐 파일 sha256(네가 잰 값) + 새 계산기 sha256_lf + 실행기 sha256_lf, 마지막 줄 `VERDICT: PASS` 또는 `VERDICT: FAIL`. **새 파일** `docs/claude/ev-rg1-hyper-judge2-report.md`(메인 체크아웃)에만 쓴다. 1차 보고서는 고치지 않는다.
