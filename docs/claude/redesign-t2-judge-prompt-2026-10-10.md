---
id: redesign-t2-judge-prompt-2026-10-10
title: 재설계 T2 독립 Judge 지시문 — 판정 규칙 코드화 · 주문표(주문 1단계) · 일지 자동
date: 2026-10-10
class: 권한·한도 변경(옛 K3) — 독립 Judge
builder_prompt: docs/claude/redesign-t2-builder-prompt-2026-10-10.md (sha256 3e754a271a0d7d76…, Builder가 읽은 main 사본과 같음 — Cowork 확인)
builder_report: .claude/worktrees/t2-core/docs/claude/redesign-t2-builder-report-2026-10-10.md
worktree: .claude/worktrees/t2-core (branch worktree-t2-core, base cd6a56d, 미커밋 — 수정 7 + 새 파일 25)
authority: order_authority=false · execution_quantity=null · 주문표에만 quantity_authority="ORDER_TICKET_HUMAN_ENTRY"
consumers: Cowork(병합 판단·배포) · 관제판 redesign-t2
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(메인 체크아웃, worktree 아님) · 이유: 주문 1단계(수량 권한)를 여는 변경의 독립 검토**

## 사용자 조작 (Windows PowerShell, 한 번)
```
cd "E:\사업\##금동한\코덱스저장소"
claude --model opus --effort xhigh
```
첫 메시지로 이 한 줄만:
```
Read docs/claude/redesign-t2-judge-prompt-2026-10-10.md and follow the Judge section exactly.
```
끝나면 Cowork에 "T2 Judge 완료"만 보낸다.

## Cowork 사전 확인 (2026-10-10 22:4x KST, 참고 — Judge는 다시 확인한다)
- 지시문 sha256 = 3e754a27…(최종본). main의 workspace/policies/auto_core.json·alert_policy.json·decision_journal.json은 Builder 실행 동안 바뀌지 않았다(수정 시각이 그 전).
- 새·바뀐 scripts에서 `/api/us/ordr`·`ust2000`·`ust2001`·`overseas orders`·`kiwoom_order`·`order_submit` 0건.
- 사용자 PC의 리눅스 VM에서 다시 돌림: test_auto_core_* 134 OK(skip 1), test_auto_core 89 OK, test_portfolio_review_journal 14 OK, test_run_portfolio_exposure_review 24 OK, test_portfolio_status 15 OK. test_decision_journal_cards는 VM에서 2건 실패하지만 원인은 VM의 git이 worktree의 Windows 경로 .git 파일을 못 읽는 것(같은 VM의 main base는 30 OK) — **Windows에서 다시 돌려 판정**할 것.
- 등록부 표본: MU 테제 strong + (카드 353줄 "강"), PWR·LITE·DELL 테제 strong +, BE 밸류에이션 weak −. 전 종목 대조는 Judge 몫(K2).

## Judge
```
너는 독립 Judge다. Builder 보고를 증거로 쓰지 말고 코드·diff·테스트로 직접 확인한다.
파일을 고치지 않는다. 유일하게 쓰는 파일은 판정 보고 docs/claude/redesign-t2-judge-report-2026-10-10.md 하나(메인 체크아웃).
키움 조회·kiwoomcli·auto_core.py(daily·decide)·reconcile_broker_state.py auto/apply·register_auto_core_task.ps1 실행 금지(가짜 데이터 테스트만).
커밋·병합·작업 등록 금지. 정책·상태·일지 파일 쓰기 금지. 비밀(.env*, 토큰, 계좌번호·계좌 라벨·이름) 읽기·출력 금지.
이 세션은 "auto_core.py"가 들어간 명령이 막혀 있다(settings deny): 문자열 검색은 Grep 도구로, 테스트는 -p "test_auto_core*".
대상: git -C .claude/worktrees/t2-core status / diff cd6a56d (CRLF 주의: 줄바꿈 차이만인 파일은 따로 적는다). 기준 지시문:
docs/claude/redesign-t2-builder-prompt-2026-10-10.md(3~6절·부록 A~D, sha256 3e754a27…인지 먼저 확인), 규칙 원문:
docs/claude/integrated-check-prompt-v3.12.2-2026-10-09.txt, docs/claude/order-instruction-design-2026-10-06.md(3·5·7·9-1·10절),
docs/claude/recovery-gate-R-REC1-2026-10-09.md, stock-strategy-system/alert_policy.json(portfolio_exposure_policy 키만).

1부 — 지시문 6절 J1~J16을 항목마다 PASS/FAIL + 근거(파일:줄)로 판정한다(지시문 6절 문장 그대로가 기준).

2부 — 추가 확인
K1 Builder 판단 1~27(보고 5절)을 하나씩 수용/거절. 특히:
   11 매도 간격 출처가 둘이면 목표 비중이 낮은 쪽 · 12 매도 후회 = 현금·후보 경로 중 큰 최대 후회 · 15 Q2 키 없음 = 재발행 없음 ·
   16 결과 분류가 T1 I2와 다르면 G0 실패 · 18 정책 값 교차 검사(POLICY_THRESHOLD_CHANGED) · 22 설정 파일 없음/틀림 = FAIL ·
   24 리플레이 가정 · 26 등록부 옮겨 적기에서 고른 12건.
   23 G-3: S7 줄이기 계획(① MVLL 상한 초과분 → ③ SOXL)대로 SOXL Δ = 20주. 확인할 것 — (a) 설계 7-1(정책 간격 = S7 목표 비중)과 맞는가
   (b) 앞 순서(MVLL)에 매도 근거가 없어 MVLL 주문표가 안 나오는 날에도 SOXL은 20주로 계산된다 → 결과 E가 1.55 위에 남을 수 있다. 이것이
   "덜 파는 쪽"(위험을 늘리지 않음)으로만 틀리는지, 주문표·매도 뒤 경로에 그 사실(앞 순서 미발행)이 표시되는지.
K2 등록부 충실도: docs/claude/card-evidence-registry.json 9종목 전부 — static_evidence의 강도·방향이 카드 "매수 근거 후보 현황" 표 칸과
   같은가(새 판단 0, 기술 신호 미포함), card_triggers의 params가 규칙 파일 정의 줄과 같은가, 절 해시를 보고 4절 계산식으로 다시 계산해 맞는가,
   accepted가 watchlist-registry cardStatus("수락…")·카드 수락 줄과 맞는가. 다른 항목은 줄 번호와 함께 전부 적는다.
K3 회로·관문 순서: 매수 열림이 "새 M만으로 기준 충족 또는 S7 add + ③"뿐이고, 등록부 자격(항목·수락·해시·커밋) 없으면 매수·매도 모두 r_max 0인가.
   G0 전체 단위(미분류·미체결 하나라도 있으면 그날 0)인가. G2b·research_only_strong_r_cap은 키가 있을 때만, 줄이기만 하는가.
K4 decide 실패 경로: 연구 기록 대기 루프가 08:30에서 끝나는가(무한 대기 없음, 가짜 시계 테스트), T1 result 없음·FAIL = HOLD, kill_switch = HOLD,
   프로필 별칭 없음 = 조회 전 FAIL, 같은 날 두 번 = 같은 결과, 결과 스키마 오류 = FAIL.
K5 일지: append_auto_core_entries가 decision_mode apply + 재확인(설정·provenance·head·멱등)에서만 쓰는가. 사람 apply가 AUTO_CORE를 거부하는가.
   _auto_core_inconsistency가 user_message null을 예외 없이 처리하는가. 쓰기 뒤 채점기 실행 실패가 경고로만 남는가. _atomic_write 기본 동작 불변.
K6 결과 분류: 다섯 상태 판정이 ust21150 행(cntr_qty·cntr_uv·frgn_trde_tp·ord_uv·ord_qty)만 쓰는가. "Limit On Close" 외 표기 = changed.
   비교 모드 주문표 분류가 재발행 원장을 바꾸지 않는가.
K7 테스트: Windows에서 -p "test_auto_core*" · test_portfolio_review_journal* · test_decision_journal_cards* · test_run_portfolio_exposure_review* ·
   test_portfolio_status* 를 직접 돌린다. 전체 스위트는 test-runner 서브에이전트로 돌리되 실패 id 집합을 원본 출력에서 직접 세어 기준선
   (보고 1절: 28줄)과 비교한다. 바뀐 기존 테스트 파일이 있으면 assert 삭제·완화 여부. 황금 테스트 G-1·G-2·G-3 값을 테스트 코드에서 확인.
K8 실자료 스모크(읽기 전용, 출력은 임시 폴더): auto_core_replay.py를 main 체크아웃 자료로 2026-07-10~2026-10-09 한 번 돌려 예외 0인지,
   SOXL·NBIS 3세션(회로 열림 1·닫힘 2 — 열림이 없으면 닫힘 3)의 지표·트리거·첫 차단 사유를 손계산(30분봉 페이지에서 직접)과 대조한다.
   리플레이 CLI 이름에는 "auto_core.py"가 없으므로 실행할 수 있다. worktree에는 자료가 없으니 --closes-root는 main의
   workspace/outputs/regular-session-closes, --measurements는 main의 docs/claude/redesign-t2-measurements-2026-10-10.json, --output-root는 세션 임시
   폴더로 준다(workspace/outputs 아래 기존 파일을 덮어쓰지 않는다).

보고 형식(한국어): 맨 위 판정 PASS | PASS-WITH-CONDITIONS | FAIL 한 줄 → 판정표(J1~J16, K1~K8) → 조건(병합 전/비교 모드 중/"켜" 전으로 나눠서)
→ FAIL이면 최소 수정 목록 → 메모. Builder 보고와 다른 사실을 찾으면 따로 적는다.
```
