---
id: r5-align-judge-prompt
title: r5-align 독립 Judge (읽기 전용)
date: 2026-10-20
class: K3 독립 Judge — 통합 점검 규칙 파일 v3.12.9(R5 추가 매수 멈춤 = S7 peak_reviews pause_add_recommendations, 매수 요건 ② 보유 추가 행 완화)와 교체 대기 로더를 판정
model: Opus · xhigh · 새 세션(메인 체크아웃, worktree 아님) — Builder(Cowork 2026-10-20) 세션과 다른 세션
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 키움 주문 도구 금지
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(메인 체크아웃) · 이유: K3 독립 Judge(매수 요건 ② 막힘 해제 조건 변경)

너는 이 변경을 만들지 않은 독립 검토자다. **파일을 고치지 않는다.** 저장소 안에 쓰는 파일은 맨 끝의 보고서 1개뿐이다. Builder 보고서의 숫자·주장은 위치 안내일 뿐이다 — 판정은 네가 연 원문과 네가 다시 계산한 값으로 한다.

## 읽을 것

1. 결정: docs/claude/r5-align-2026-10-20.md(1~4절 — 특히 3절 불변 조건). Builder 보고: docs/claude/r5-align-report.md. 교체 절차: docs/claude/scheduled-prompts/pending-r5-align/README.md.
2. 변경: `diff docs/claude/integrated-check-prompt-v3.12.8-2026-10-19.txt docs/claude/integrated-check-prompt-v3.12.9-2026-10-20.txt`, `diff docs/claude/scheduled-prompts/integrated-check-daily.txt docs/claude/scheduled-prompts/pending-r5-align/integrated-check-daily.txt`, `git status --porcelain --untracked-files=all --` 아래 대상 7개 경로(새 파일이어야 함 — 23:30 문서 커밋 뒤라 안 보이면 `git log --stat -- <경로>`로 그 커밋이 이 7개만 더했는지). 대상: docs/claude/r5-align-2026-10-20.md · r5-align-report.md · r5-align-judge-prompt.md · integrated-check-prompt-v3.12.9-2026-10-20.txt · scheduled-prompts/pending-r5-align/{README.md, integrated-check-daily.txt, integrated-check-prompt-v3.12.9-2026-10-20.txt}. 다른 작업의 M·?? 항목은 범위 밖.
3. 코어·S7 원문: manage-us-stock-strategy/scripts/auto_core_rules.py 720~726행 · auto_core_tickets.py 183~249행 · auto_core_decide.py 258~263·940~990행 · auto_core_compare.py 255~270행 · portfolio_exposure.py 873~960·1350~1390행 · docs/claude/t2rc-oracle.py 1895~1930행.
4. 실데이터: workspace/outputs/auto-core/LATEST_DECISION.json(exposure.peaks·buy_requirements·compare·inputs.s7_review) · workspace/outputs/exposure-review/2026-10-19/ · workspace/outputs/research-records/2026-10-13/·2026-10-20/research-record.json(integrated_check_run).

## 돌려도 되는 것

- `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "<파일>"`로 test_auto_core_rules.py·test_auto_core_compare.py·test_auto_core_tickets.py·test_portfolio_exposure.py·test_portfolio_exposure_fail_closed.py("auto_core.py"가 든 명령은 거부되니 이 패턴으로만).
- 파일을 쓰지 않는 python으로 재계산·compare 재현(auto_core_compare.compare에 LATEST_DECISION과 연구 기록 실행 사본, 등록부는 auto_core_inputs.load_registry).
- 로더 10~19행 heredoc의 계산(LF 정규화 sha256)을 경로만 저장소 상대 docs/claude/integrated-check-prompt-v3.12.9-2026-10-20.txt로 바꿔 실행하고 18행 값과 같은지 확인(로더의 ~/mnt 경로는 Cowork 장치 VM 전용이라 그대로 돌리면 RULES UNREADABLE).
- 금지: 키움 호출, auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행, 커밋·병합, 예약 작업 변경(update_trigger), workspace/outputs·stock-strategy-system·정책·관제판 쓰기.

## 판정 항목 (모두 PASS여야 VERDICT: PASS)

1. 범위: 규칙 파일은 1·101·134행만, 로더는 1·4·12·18·75행만 바뀌었다. 로더 18행 해시 = 새 규칙 파일 LF sha256, 사본 두 개가 바이트 같다. 코드·테스트·스키마·정책·상태·예약 작업 변경 없음.
2. 결정 2절 충족: S7이 이번 기준 세션 것이고 항목 status OK면 R5 멈춤 = 그 항목 `pause_add_recommendations`. 가격 상태(≤0.70×P·≤0.75×P)는 매수를 막지도 풀지도 않는다.
3. 결정 3절 fail-closed: S7 없음·오래됨·종목 없음·status≠OK면 막힘이 유지된다. 어떤 입력에서도 v3.12.8보다 느슨해지는 경우는 "이번 기준 세션의 S7이 그 종목 사건을 completed로 닫은 경우"뿐인가(직전 세션 S7·REVIEW_OPEN·NO_BASELINE_PEAK·UNVERIFIED·P 계산 불가 각각 확인).
4. Builder가 블록·결정보다 엄격하게 정한 3곳(보고 2절)이 결정 취지와 맞고 다른 규칙과 충돌하지 않는가 — 특히 ㉮ "이번 기준 세션" 한정과 100·134행의 "신선"(직전 세션 포함) 정의가 함께 읽힐 때 모순이 없는가.
5. 불변: 트리거 기준(R5 문턱 0.70·0.75)·근거 강도·알림 조건(278행, triggers R5 state는 가격 상태 그대로)·쓰기 범위(173행·로더 절대 금지)·매도 비차단·주문 금지·R-REC1·노출 대역·종목 상한·카드 근거 원칙.
6. 코어와 같은 뜻: `peakReviews.state` 정의가 코어 `exposure.peaks.state`(r5_state)와 compare 규칙(auto_core_compare.py 264행)에서 같은 날 같은 입력이면 B1이 되는가. 10-20 기록으로 재현해 B7 변화를 직접 센다.
7. 지시 1 판정: 코어 R5가 사건형이라 코드 수정이 필요 없다는 결론이 원문과 맞는가. 보고 1절 "미해결 1"의 범위(NO_BASELINE_PEAK 입력 이상만)가 맞는가.
8. 대상 테스트 5파일 실패 0.
9. 교체 절차(README)가 예약 본문 대조·재서명·되돌리기·사전 등록 기록·첫 확인을 갖추고, 사용자 일상 단계를 늘리지 않는다.

## 보고

`docs/claude/r5-align-judge-report.md` 새 파일: 한국어 표 `| # | 항목 | PASS/FAIL | 근거(파일:행 / 재계산 값) |`(위 1~9), 그 아래 "발견"(고칠 최소 항목이 있으면 — 기본 NO_CHANGE), 네가 잰 바뀐 파일 sha256, 마지막 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL`.
