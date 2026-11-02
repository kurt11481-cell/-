---
id: basefail-include-builder-prompt
title: "기준선 ② git 밖 지난 파일 11건 — .worktreeinclude·.gitignore Builder (K3)"
date: 2026-11-02
class: "K3 수동 경로(.worktreeinclude·.gitignore 보호 이름). 회사PC worktree Builder(Opus) → 별도 읽기 전용 Judge → 병합은 사장 결정 뒤 사장 PowerShell"
source: "docs/claude/basefail-cleanup-proposal-2026-11-02.md ②, 사장 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9BrPM94W22naif7qV4EC7RF '둘 다 승인, 오늘 진행' 2026-11-02 19:53:58 KST"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 목표
아래 시험들이 개발 큐 worktree에서 git 밖 지난 파일(2026-08 산출물)을 못 찾아 실패한다. devpipe가 기준선 worktree를 만들 때 복사하는 목록(`.worktreeinclude`, tools/dev_pipeline/devpipe.py 1105~1127행·1393행)에 그 파일들의 **정확한 경로**를 더해 고친다. 파일 자체는 git에 넣지 않는다.

대상 시험(기준선 d88e88f 기준 11건):
- test_holding_baseline_observation_audit (setUpClass)
- test_mvll_canonical_volume_lineage (setUpClass)
- test_provider_limitation_audit (setUpClass)
- test_nbis_v3_shadow_activation
- test_nbis_v4_kiwoom_price_authority
- test_portfolio_decision_order_intent
- test_validate_research_packet
- test_portfolio_decision_dashboard
- test_materialize_kiwoom_session_aware_acceptance_candidate

## 바꿀 파일 (이 3개만)
- .worktreeinclude
- .gitignore
- docs/claude/basefail-include-report.md (보고)

## 구현 요구
1. **목록 찾기.** 위 9개 시험 파일을 worktree에서 하나씩 돌린다. FileNotFoundError나 `source artifact missing`, `is_file()` 실패로 드러나는 경로를 모은다. 그 파일을 본 저장소(`E:\사업\##금동한\코덱스저장소`)에서 worktree의 같은 경로로 복사하고 다시 돌린다. 더 나오는 경로가 없을 때까지 되풀이한다.
   - 복사는 본 저장소 → worktree 방향만 한다. 본 저장소 파일은 읽기만 한다.
2. 복사한 파일은 모두 아래 조건을 만족해야 한다.
   - 본 저장소에서 git 추적 밖이다.
   - 경로가 `workspace/outputs/` 또는 `stock-strategy-system/market_snapshot.example.json`이다.
   - 날짜가 2026-08이다.
   - 조건 밖의 파일이 필요하면 복사하지 말고 BLOCKED.md에 적고 멈춘다. 특히 실제 상태 파일(stock-strategy-system/portfolio_state.json 등)과 workspace/state/는 안 된다.
3. `.worktreeinclude` 맨 뒤에 다음을 둔다: 주석 1줄 + 모은 경로를 한 줄에 하나씩(정확한 경로, 별표 없음, 정렬). 기존 2줄은 그대로 둔다.
4. `.gitignore`에 아래 두 줄을 더한다. 둘 다 본 저장소에서 지금 `??`로 보이는 폴더다. 다른 줄은 바꾸지 않는다.
   - `workspace/outputs/lmt-instrument-registry-candidate-prep/`
   - `workspace/outputs/manual-portfolio-analysis/`
5. 모은 경로가 모두 `.gitignore`로 무시되는지 `git check-ignore`로 확인한다. 무시되지 않는 경로가 남으면 BLOCKED.md에 적고 멈춘다.
6. 시험 파일·단언, devpipe 코드, 정책·상태는 바꾸지 않는다.

## 시험 (아래 형식만, 글자 그대로, 파일마다 한 줄)
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "<시험 파일 이름>.py"`

대상은 위 9개다. 기대 결과는 기준선의 실패 11건이 모두 통과하는 것이다. 나머지 실패는 이 9개 파일 안에 없어야 한다. 있으면 보고서에 적는다.

전체 스위트는 돌리지 않는다. git은 status·diff·log·ls-files·check-ignore만 쓴다. 복사는 위 1번에 한해 쓴다.

## 지켜야 할 것
- 위 3개 파일 밖의 tracked 파일은 손대지 않는다. tools/·.claude/·.gitattributes·정책·상태는 금지다.
- 고치는 파일의 줄바꿈을 지킨다.
- 복사한 파일의 내용을 보고서에 옮기지 않는다. 경로와 크기만 적는다.
- 주문·키움·일지·원장·예약과 무관하다. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음. 비밀(.env*·토큰·계좌번호)을 읽지 않는다.
- 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/basefail-include-report.md
- (a) `.worktreeinclude`에 더한 경로와 각 크기(바이트), 합계
- (b) `.gitignore`에 더한 줄
- (c) 시험 9개 각각의 마지막 3줄. 기준선 11건이 통과했는지
- (d) `git status --short` 결과
- (e) `git check-ignore` 확인 결과

수량·금액·주문 표지 문자열은 적지 않는다("표지 없음").
