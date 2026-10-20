---
id: r5-align-report
title: R5(고점 −30%) 정의를 S7과 일치 — Builder 보고
date: 2026-10-20
prompt: docs/claude/r5-align-2026-10-20.md 4절 (메인 체크아웃의 커밋 안 된 파일, sha256 3c9138229fd7ef76d634c5b09007874356ead3746f239cf85927ad9ee85f4633)
decision: 사용자 "r5-align: 1" (2026-10-20 08:04 KST)
builder: Cowork (Opus 5.5) — 사용자 요청 "docs/claude/r5-align-2026-10-20.md 의 4절 Builder 지시 블록대로 작업해줘"(2026-10-20 08:06 KST). 결정 4절 권장(Claude Code·새 worktree)과 다름: 코드 변경 0건이라 메인 작업 트리에 새 문서만 추가(보호 파일·코어 파일 무변경)
base: main HEAD bb1f1f9e3ff8f509dc318b303b6df6cd068a174f · 규칙 파일 v3.12.8 f5e4b9c89fd90ead80f3e2064ab4203948f2e27e43ed18f4874c18bbf9223540 · 로더 v3.12.8-L+R2 91c1e762bdf2419153fa66d575811641975062164d5fa5c609b116d8c321ff9b
status: READY_FOR_JUDGE (docs/claude/r5-align-judge-prompt.md)
consumers: 독립 Judge(별도 Claude Code 세션, 결정 5절) · Judge PASS + 사용자 승인 뒤 Cowork 교체(docs/claude/scheduled-prompts/pending-r5-align/README.md) · 교체 뒤 첫 통합 점검·08:50 결과 알림(compare)
weekly_user_touch: 0 (일회성: Judge 시작 1 · 적용 승인 1줄)
order_authority: false
quantity_authority: none
---

# r5-align Builder 보고

결론: 자동 운영 코어는 이미 S7 사건형이라 코드 수정이 없다. 바뀐 것은 통합 점검 규칙 파일 v3.12.9(1·101·134행)와 교체 대기 로더(5곳)뿐이고, 예약 작업은 바꾸지 않았다. 10/20 비교 기록을 손으로 v3.12.9 정의에 맞춘 가정 사본(D 등급)에서는 설명 안 된 차이(B7)가 6건 → 1건(남은 1건은 R5와 무관) — 실제 효과는 교체 뒤 첫 실행에서 확인한다.

## 1. 지시 1 — 코어의 R5 판정: 사건형(S7 사용), 수정 없음

- `auto_core_rules.py` 720~726행 `r5_state`: S7 항목 `status == "REVIEW_OPEN"`일 때만 `review`. 그 밖은 가격으로 `near`(종가 ≤ 0.75×P) / `none`, peak·close가 없으면 `unk`. 0.70×P로 `review`를 만드는 분기가 없다(상수 `R5_REVIEW_FRACTION` 51행은 compare 거리 계산에만 쓰임 — `auto_core_compare.py` 118행).
- 입력: 코어는 decide 안에서 자기 S7을 돌린다(`auto_core_decide.py` 258~263행 `run_s7` — exposure-review 폴더는 읽지 않음, 649~653행 `s7_runner`). 960행 `peaks = {item["symbol"]: item for item in review.get("peak_reviews")}`, 983행 `exposure.peaks[].state = rules.r5_state(item)`. 최신 세션 S7이 아니면 950~951행 `G1_S7_NOT_LATEST_SESSION`.
- 막힘: `auto_core_tickets.py` 248행 — 보유 (추가) 행 ②는 `r5_state(...) == "review"`일 때만 "R5 검토"로 막힘. S7 `add_paused`는 243~244행에서 따로 막힘.
- S7 쪽(`portfolio_exposure.py`): 계산된 항목은 954·957행 status `REVIEW_OPEN`(열린 사건)/`OK`, `pause_add_recommendations = bool(open_events)`. 계산 못 한 항목은 892행 기본값 `NO_BASELINE_PEAK` + `pause_add_recommendations: True`, 또는 `UNVERIFIED`.
- 실데이터(10-19 세션, `workspace/outputs/auto-core/LATEST_DECISION.json` generated_at 2026-10-19T22:45:01Z, mode apply·decision_mode compare): 코어가 쓴 S7 = `auto-core/2026-10-20/s7/2026-10-19/portfolio-exposure-review.20261019T224506138680Z.json`(inputs.s7_review). `exposure.peaks` MVLL·NBIS·SOXL 모두 `near`(close 27.99/170.19/98.675 ≤ 0.70×P), 요건 ② NBIS·SOXL "통과 (E 1.33 · 현금 $12469.19)", MVLL은 "상품 승인 없음"으로만 막힘. 통합 점검이 읽는 S7(`exposure-review/2026-10-19/portfolio-exposure-review.20261019T211602685737Z.json`, 규칙 100행)도 세 종목 status OK·`pause_add_recommendations` false·사건 completed(10-15/10-16/10-14 breach) — 결정 문서 1절 값과 같다.
- 판정: 결정 2절(S7 `pause_add_recommendations`·open_events를 따름)과 같은 사건형 → "다르면 수정" 조건 불충족 → 코드·테스트 추가 없음.

미해결 1(기본 NO_CHANGE, 알림만): 코어는 S7 항목에 peak·close가 없으면(`NO_BASELINE_PEAK`·`UNVERIFIED`) `r5_state = unk`이고 248행에서 막지 않는다. `UNVERIFIED`(1368~1369행 → required_price_missing)와 S5 미활성(`NOT_ACTIVATED`, 1355~1356행)은 S7 fail-closed → `pauses.add_recommendations.paused`(1382행) → 243~244행 "S7 추가 멈춤"으로 막힌다. S7에 항목이 없는 보유 종목은 상태 ≠ 브로커일 때 생기는데, 그때는 `G1_STATE_NOT_EQUAL_BROKER`(decide 545~548행)가 모든 후보 사유에 붙어(tickets 721·744·760행) 막힌다. 남는 것은 `NO_BASELINE_PEAK` 사유 `FIRST_RECONCILED_DATE_UNKNOWN`·`NO_SESSION_SINCE_BASIS_DATE`(입력 이상일 때)뿐이고 10-19 파일에는 없다. 그 경우 v3.12.9 통합 점검은 ㉯로 막고 compare에 `R5:<종목>` B7(코어 unk ↔ LLM hit)로 드러나며, 독립 계산기는 이미 `pause_add_recommendations` 또는 `open_events`로 막는다(`docs/claude/t2rc-oracle.py` 1904·1925행 — 주문표가 생기면 t2-rc C2 불일치로도 드러남). 바꿀 근거: 실제 S7 파일에 그런 항목이 나오면 → 248행을 계산기 1904행 정의(`pause_add_recommendations` 또는 `open_events`)에 맞추는 K3 수정(별도 Builder·Judge, 계산기 변경 없음) 후보.

## 2. 지시 2 — 규칙 파일 v3.12.9

파일 `docs/claude/integrated-check-prompt-v3.12.9-2026-10-20.txt`(v3.12.8 바이트 복사 뒤 정확 치환 3건, 각 원문 구절 1회 확인). `diff` 결과 바뀐 줄 = 1·101·134행뿐(두 판 모두 278줄). UTF-8·LF·BOM 없음.

| 행 | 바뀐 내용 |
|---|---|
| 1 | 머리말 맨 앞에 v3.12.9 한 줄(결정·근거·바뀐 곳·"트리거 기준·근거 강도·알림 조건·쓰기 범위 불변") |
| 101 (2-3 ③) | 가격 상태(≤0.70×P "검토 대상(선 아래)", ≤0.75×P "근접")는 ㉮에서는 표시만, ㉯에서는 멈춤 판정에 씀(매도 근거 아님). 추가 매수 멈춤 = ㉮ ②의 S7 evaluation_session이 이번 기준 세션 + 그 종목 항목 있음 + status OK → `pause_add_recommendations` 그대로, ㉯ 그 밖(S7 없음·오래됨·직전 완료 세션의 S7·항목 없음·status≠OK) → `pause_add_recommendations` true이거나 종가 ≤ 0.70×P면 멈춤, P 못 구하면 확인 필요(막힘). 문구(어느 것도 결정 필요로 올리지 않음): S7 열린 사건으로 멈추면 기존 "검토 개시(카드 다시 쓰기 …)", ㉯ 자료 공백으로 멈추면 "R5 추가 매수 멈춤(fail-closed — S7 <세션·없음·status>, 이번 세션 이탈 미확인) · 카드 다시 쓰기 아님", 선 아래인데 멈춤 없으면 "선 아래 · S7 검토 완료(<breach_date>) — 추가 매수 멈춤 없음". 기록: `peakReviews.state` = 멈춤 상태(hit/near/none/unk — 코어 `exposure.peaks.state`와 같은 뜻), `triggers` R5 항목 state = 가격 상태 그대로(알림 ②·반복 억제 v3.12.8과 같음), 멈춤 없으면 label "선 아래 · 멈춤 없음" |
| 134 (3) 요건 ②) | 보유 (추가) 행의 "고점 −30% 검토 개시(R5)" → "R5 추가 매수 멈춤(2-3 ③의 ㉮·㉯ — 이번 기준 세션 S7이고 status OK면 pause_add_recommendations, 그 밖이면 pause_add true 또는 종가 ≤ 0.70×P. ㉮에서는 가격 상태만으로 막지 않는다, v3.12.9)" |

블록·결정 문구보다 엄격하게 정한 3곳 — Judge 확인 대상:
1. 블록 "status≠OK면 현행 상태형으로 멈춤"을 그대로 읽으면 `REVIEW_OPEN`인데 종가가 0.70×P 위로 회복한 종목이 풀린다(S7은 멈춤). 결정 2절(S7을 그대로 따름)·3절(fail-closed)에 맞추려고 ㉯에 "`pause_add_recommendations` true여도 멈춤"을 넣었다. S7은 status≠OK인 항목에 늘 true를 쓰므로(892·957행) ㉯는 사실상 "status≠OK면 멈춤"이다.
2. 결정 3절은 "오래됨 = 기준 세션·직전 완료 세션이 아님"(직전 세션 S7은 신선)이다. 그러나 직전 세션 S7은 그 뒤 세션의 새 이탈(첫 이탈·새 고점 뒤 재이탈)을 사건으로 모르므로 `pause_add` false를 따르면 v3.12.8보다 느슨해진다. 실례: 10-13 실행(기준 세션 10-12)이 S7 10-09를 신선으로 썼다(research-records/2026-10-13 `integrated_check_run.account.exposure.s7`). 코어는 최신 세션 S7만 받는다(decide 950~951행). 그래서 ㉮는 "이번 기준 세션의 S7"만, 직전 세션 S7은 ㉯(상태형 포함)로 정했다. ② 노출 칸의 신선 정의(100·134행)는 바꾸지 않았다.
3. `peakReviews.state` 정의를 ③ 안에 넣었다(블록이 이름으로 든 곳은 아님). compare는 이 칸을 코어 `exposure.peaks.state`와 대조한다(`auto_core_compare.py` 259~268행: hit ↔ review/hit, near ↔ near). 정의가 없으면 LLM이 0.70×P 아래를 계속 hit로 써 B7 3건이 남는다(4절 B). 173행(기록 필드 목록)·278행(알림 ②)·171행((d) 종목별 여유)은 그대로다.

표시 문구(판정 아님): 직전 세션 S7 같은 ㉯ 자료 공백 날에 S7이 이미 completed로 닫은 사건을 "카드 다시 쓰기"로 바꿔 사용자 손이 가지 않도록 멈춤 문구를 열린 사건과 자료 공백으로 나눴다.

불변 확인: R5 가격 문턱 0.70·0.75 그대로(트리거 기준), 근거 강도 문장 무변경, 알림 278행 무변경, 쓰기 범위(173행 필드 목록·로더 절대 금지 6행) 무변경, 매도 쪽 문구 무변경. 노출 대역·종목 상한·R-REC1(102행)·카드 근거 원칙 무변경(바뀐 줄이 1·101·134뿐). 위 3곳은 모두 매수 쪽을 더 막는 방향이다.

## 3. 지시 3 — 짧은 지시문(로더) 새 해시 + 변경 기록

폴더 `docs/claude/scheduled-prompts/pending-r5-align/`:
- `integrated-check-daily.txt` — 현행 로더(91c1e762…, `pending-rrec-ev4/`와 바이트 같음)에서 바꾼 곳: 1행 머리말, 4·12행 규칙 파일 경로 v3.12.9, 18행 해시 f5e4b9c8… → 75fcd5de…, 75행 writer `integrated-check 06:40 v3.12.9-L+R2`. `diff` 바뀐 줄 = 1·4·12·18·75(선례 v3.12.7→v3.12.8과 같은 자리). 로더 1단계 python을 그대로 실행 → `RULES 98517 bytes … 75fcd5de… MATCH`. 길이 16,563자·22,670바이트 — 운영 중인 관심 명단 재채점 본문 사본(scheduled-prompts/README.md 16행 해시 a809c649…와 같은 파일, 36,988자·50,998바이트 실측)보다 작다.
- `integrated-check-prompt-v3.12.9-2026-10-20.txt` — 규칙 파일 사본(바이트 같음).
- `README.md` — 변경 기록·교체 절차·되돌리기·Judge FAIL 때 새 판 이름.
- writer는 스키마가 빈 문자열만 막는다(`schemas/auto-core-research-record.schema.json` 14행).
- 예약 작업(trig_01YWzNq847nJfNgDUnnukBqP)은 바꾸지 않았다(update_trigger 호출 없음). 예약 본문 = 91c1e762…인지는 이번에 다시 대조하지 못했다(목록 조회 응답이 커서 그 항목까지 읽지 않음, README 11행 기록 = 10-19 20:4x 교체본) — 확인 필요, 교체 절차 ①에서 확인.

## 4. 지시 4 — 테스트·재현

- 대상 테스트(장치 VM Linux Python 3.10, `PYTHONDONTWRITEBYTECODE=1`, 메인 작업 트리): `test_auto_core_rules.py` 43 OK · `test_auto_core_compare.py` 15 OK · `test_auto_core_tickets.py` 59 OK · `test_portfolio_exposure.py` 57 OK · `test_portfolio_exposure_fail_closed.py` 32 OK (합 206, 실패 0). 코드 변경이 없어 변경 전 = 변경 뒤. 테스트가 고정하는 것은 `r5_state` 경계(`test_auto_core_rules.py` 383~386행: REVIEW_OPEN → review, OK·0.75P → near, 0.7501P → none)와 compare R5 거리 경계(`test_auto_core_compare.py` 128~139행, 코어 none ↔ LLM hit의 B2/B7)뿐이다. "status OK이고 종가 ≤ 0.70×P면 near(막지 않음)"와 tickets 248행 ② 막힘 조건은 테스트가 없고 아래 즉석 확인뿐이다 — 테스트 추가는 권한 경로(tests/test_auto_core*.py)라 다음 코어 K3 작업에 묶을 후보.
- 즉석 확인(파일 쓰기 없음): `r5_state({"status":"OK","peak":"100","close":"60"})` = near · REVIEW_OPEN = review · NO_BASELINE_PEAK = unk · 항목 없음 = unk.
- compare 재현(10-20 decide 입력 그대로, `auto_core_compare.compare`, 등록부 status OK, research_ok True):
  - A 기록된 LLM 실행 사본(research-records/2026-10-20 `integrated_check_run`) → B7 6건 `buyReq:DELL:1, buyReq:NBIS:2, buyReq:SOXL:2, R5:MVLL, R5:NBIS, R5:SOXL`, B1 170 = 저장된 decision.compare와 같음.
  - B 가정 사본(D 등급 — LLM 기록을 손으로 고침): peakReviews state = S7 OK·≤0.75×P → near, NBIS·SOXL ② = 통과(두 칸의 막힘 사유는 R5뿐이었음, MVLL은 상품 승인으로 그대로 막힘) → B7 1건 `buyReq:DELL:1`(① 실적 금지 구간, R5 무관), B1 175. 실제 LLM이 v3.12.9를 이렇게 따르는지는 교체 뒤 첫 실행(README ⑦)에서 확인.
- 실행하지 않음: 전체 스위트(코드 무변경), 스키마 감사(스키마 무변경), 키움 조회, auto_core.py·dev-run·dev-merge·reconcile apply.

## 5. 예상 효과와 표시

- 통합 점검: 요건 ② NBIS·SOXL "통과"(R5 이유 없음), needs·결정 필요에서 "R5 해석 차이" 항목이 빠진다(결정 5절 첫 실행 확인). 오늘 10-20 LLM ② 칸 문구 "해석 차이는 needs 참조"가 그 출처다.
- 통합점검 대시보드(https://claude.ai/artifact/DuS4d8Fa9qZWceBJWjTU6d, 읽기만): "고점 −30% 검토 (R5)" 표가 `state`를 그대로 보여 준다(HTML 1006~1012행) — hit → near로 바뀐다. 고점·종가·기준선 숫자는 그대로라 선 아래 여부는 보이지만, "상태" 칸의 near가 "근접"으로 읽힐 수 있다 — 칸 이름 바꾸기는 별도 표시 작업 후보(K1). "오늘 먼저 볼 것"의 R5 칩은 triggers 가격 상태(hit)라 계속 뜨고, 칩 글자는 label "선 아래 · 멈춤 없음". 페이지 HTML은 바꾸지 않았다.
- compare 연속 일수: 설명 안 된 B7이 있는 날은 0으로 되돌아간다(`auto_core_compare.py` streak). R5 계열 B7이 매일 그 원인이었다. 직전 세션 S7을 받는 날(10-13 같은 날, 10-14~10-20 5회는 같은 세션)은 ㉯로 상태형 막힘이 되어 R5·buyReq ② B7이 다시 생기고 연속 일수가 0이 될 수 있다 — 의도한 fail-closed 비용이다. 대안(직전 세션 S7이라도 '새 이탈이 날 수 없는' 경우 — S7 종가가 이미 선 아래이고 그 사건이 completed — 는 S7을 따름)은 빈도가 낮고 LLM이 따르기 복잡해 채택하지 않았다.
- t2-rc: 코어·계산기 불변이라 C1을 0부터 다시 셀 사유(코어 결함·계산기 수정, 사전 등록 1절 C1)가 없다. 교체 때 사전 등록 변경 기록에 로더·규칙 파일 새 고정값만 1줄(Cowork).
- 매매: 오늘 R-REC1로 모든 매수가 막혀 있어 영향 없음(결정 1절, 10-19 decide ⑤ 8종목 모두 "막힘 미충족 RG1,RG2,RG3"). 매도·주문 경로 무관.

## 6. 바뀐 파일 (모두 새 파일, sha256 = 작업 트리 바이트 = LF)

| 파일 | sha256 |
|---|---|
| docs/claude/integrated-check-prompt-v3.12.9-2026-10-20.txt | 75fcd5deff628549f10a61a7a628e6693107db317e071cd9994f654fc8fb7722 |
| docs/claude/scheduled-prompts/pending-r5-align/integrated-check-prompt-v3.12.9-2026-10-20.txt | 75fcd5deff628549f10a61a7a628e6693107db317e071cd9994f654fc8fb7722 |
| docs/claude/scheduled-prompts/pending-r5-align/integrated-check-daily.txt | 6f65c89b8a18283e5ced365cd058ed871440d9f7ecf1c6b27e3a2decbd4cfff9 |
| docs/claude/scheduled-prompts/pending-r5-align/README.md | e9ffae1a1c2e7ebeab6a62427a949dac0b0705fb575f9420b1d743645a5ba804 |
| docs/claude/r5-align-judge-prompt.md | 3afa05cba4f44765f3b86bdd5d8d098dd49c062f76dc9cbb934776dc470e80cd |
| docs/claude/r5-align-report.md | 이 보고서 |
| docs/claude/_pending/r5-align-builder.txt | 23:30 문서 커밋 목록 |

코드·테스트·스키마·정책·상태·장부·일지·예약 작업·CLAUDE.md·대시보드 페이지 HTML 변경 없음. 키움 호출 없음. 커밋 없음(문서 자동 커밋 목록만 — 선례는 Judge PASS 뒤 커밋했다. 런타임 영향은 없고(로더가 v3.12.8 해시 고정, 예약 불변), Judge가 FAIL하면 고친 판은 v3.12.10 새 이름으로 만든다 — README 변경 기록).

## 7. 멈춤·범위·재검토

- 멈춤 없음. 블록·결정과 다르게 정한 3곳(2절)은 모두 더 엄격한 쪽이며 Judge 판단 대상.
- 내장 재검토 2회(Opus, 원문 직접 열람). 2회차 9건 반영: 101행 가격 상태 문구 충돌 제거 · 134행·머리말·로더 요약에 ㉯ pause_add 분기 · 멈춤 문구 나눔(결론 변경) · 대안 1줄 · Judge 지시문의 git 범위·1단계 경로 · 테스트 범위·길이 출처 문구 · 해시. 1회차 12건 반영: ㉮ 이번 기준 세션 한정(결론 변경) · 코어 S7 경로 · 미해결 1 범위(항목 없음 → G1) · 계산기 동작 · 테스트 범위 문구 · 길이 확인 · 가정 사본 D 표시 · 줄 수 278 · 대시보드 칸 뜻 · 커밋 순서 메모 · Judge 지시문 작성.
