---
id: basefail-include-report
title: "basefail-include Builder 보고 — 기준선 ② git 밖 지난 파일 11건"
date: 2026-11-02
source: "docs/claude/basefail-include-builder-prompt.md, docs/claude/basefail-cleanup-proposal-2026-11-02.md ②, 사장 결정 카드 2026-11-02 19:53:58 KST, 사장 직접 입력 '기준선 복사 목록 실행해' 21:44:39 KST · 'LMT 포함' 21:57:18 KST"
target: "worktree .claude/worktrees/funny-brahmagupta-57aa0a, 브랜치 worktree-basefail-include, 기준 커밋 c81ac2e, 커밋 없음"
authority: "주문·키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 결론
기준선 실패 11건이 모두 통과했다. 시험 파일 9개 모두 OK다. `.worktreeinclude`에 경로 19개를, `.gitignore`에 2줄을 더했다. 복사한 파일 19개는 모두 git 무시 대상이라 커밋에 들어가지 않는다.

## (a) .worktreeinclude에 더한 경로와 크기
기존 2줄은 그대로다. 그 뒤에 주석 1줄과 아래 19줄을 정렬해 더했다. 별표는 없다. 19개 모두 본 저장소 파일과 sha256이 같고, 본 저장소에서 git 추적 밖이다(`git ls-files` 0건). 날짜는 본 저장소 파일의 수정 날짜(KST)다.

| 바이트 | 날짜 | 경로 |
|---:|---|---|
| 1,934 | 2026-08-05 | stock-strategy-system/market_snapshot.example.json |
| 663,097 | 2026-08-14 | workspace/outputs/activation/holding-valuation-shadow/2026-08-13/kiwoom-finalized-snapshot.json |
| 28,144 | 2026-08-14 | workspace/outputs/activation/holding-valuation-shadow/2026-08-13/session-aware-validation.json |
| 2,011 | 2026-08-14 | workspace/outputs/activation/kiwoom-candidate-primary-replay-hardening/20260814-070450/replay_summary.json |
| 1,402,321 | 2026-08-14 | workspace/outputs/activation/kiwoom-session-aware-priority/20260814-080351/kiwoom_daily_snapshot.json |
| 8,569 | 2026-08-14 | workspace/outputs/activation/kiwoom-session-aware-priority/20260814-080351/kiwoom_extended_hours_snapshot_v2.json |
| 2,212,138 | 2026-08-14 | workspace/outputs/activation/kiwoom-session-aware-priority/20260814-080351/yfinance_replay_evidence.json |
| 134,662 | 2026-08-14 | workspace/outputs/activation/kiwoom-session-aware-priority/20260814-082800/active_provider_smoke_aapl_2026-08-12.json |
| 6,989 | 2026-08-14 | workspace/outputs/activation/kiwoom-session-aware-priority/20260814-082800/fault_injection_results_escalated.json |
| 61,062 | 2026-08-14 | workspace/outputs/activation/kiwoom-session-aware-priority/20260814-082800/finalized_regular_validation_2026-08-12.json |
| 68,260 | 2026-08-14 | workspace/outputs/activation/kiwoom-session-aware-priority/20260814-082800/session_aware_validation.json |
| 8,094 | 2026-08-14 | workspace/outputs/activation/kiwoom-yfinance-five-session/20260813-164437/acceptance_summary.json |
| 1,957 | 2026-08-14 | workspace/outputs/activation/mvll-v2-shadow/20260814-v3/activation-receipt.json |
| 1,890 | 2026-08-14 | workspace/outputs/activation/nbis-v2-shadow/20260814-v4/activation-receipt.json |
| 4,449 | **2026-09-02** | workspace/outputs/lmt-instrument-registry-candidate-prep/lmt-instrument-registry-patch-candidate-v1.json |
| 2,086,795 | 2026-08-30 | workspace/outputs/manual-portfolio-analysis/manual-20260829T153208101909Z-c32341e4e7f3/manual-portfolio-analysis.json |
| 1,141,168 | 2026-08-14 | workspace/outputs/portfolio-strategy/2026-08-13/kiwoom_market_snapshot.json |
| 1,768,507 | 2026-08-14 | workspace/outputs/portfolio-strategy/2026-08-13/yfinance_replay_evidence.json |
| 183,665 | 2026-08-14 | workspace/outputs/portfolio-strategy/2026-08-13/yfinance_shadow_snapshot.json |

합계 19개, 9,785,712바이트. 수정안의 "약 수십 MB(확인 필요)"는 약 9.3MiB로 확인됐다.

## (b) .gitignore에 더한 줄
파일 맨 뒤에 2줄을 더했다. 다른 줄은 바꾸지 않았다.
- workspace/outputs/lmt-instrument-registry-candidate-prep/
- workspace/outputs/manual-portfolio-analysis/

## (c) 시험 결과
지시문 형식 그대로, 두 파일 수정을 끝낸 뒤 한 파일씩 돌렸다. 마지막 3줄은 빈 줄을 뺐다.

| 시험 파일 | 기준선 실패 | 마지막 3줄 |
|---|---:|---|
| test_holding_baseline_observation_audit | 1 | `-----` / `Ran 22 tests in 0.004s` / `OK` |
| test_mvll_canonical_volume_lineage | 1 | `-----` / `Ran 3 tests in 0.164s` / `OK` |
| test_provider_limitation_audit | 1 | `-----` / `Ran 4 tests in 0.011s` / `OK` |
| test_nbis_v3_shadow_activation | 1 | `-----` / `Ran 4 tests in 0.022s` / `OK` |
| test_nbis_v4_kiwoom_price_authority | 2 | `-----` / `Ran 16 tests in 0.046s` / `OK` |
| test_portfolio_decision_order_intent | 1 | `-----` / `Ran 73 tests in 3.353s` / `OK` |
| test_validate_research_packet | 1 | `Ran 3 tests in 0.008s` / `OK` / `Self-test passed` |
| test_portfolio_decision_dashboard | 1 | `-----` / `Ran 306 tests in 164.435s` / `OK` |
| test_materialize_kiwoom_session_aware_acceptance_candidate | 2 | `-----` / `Ran 26 tests in 3.063s` / `OK` |

기준선 11건은 모두 통과했다. 이 9개 파일 안에 다른 실패는 없다. 같은 기준 커밋에서 파일을 복사하기 전에는 위 11건이 그대로 실패했다. 전체 스위트는 지시문대로 돌리지 않았다.

## (d) git status --short
```
 M .gitignore
 M .worktreeinclude
?? docs/claude/basefail-include-report.md
```

## (e) git check-ignore 확인
`git check-ignore -v -- <경로 19개>`의 종료 코드는 0이고, 19개 모두 무시 대상이다.

| 규칙 | 개수 |
|---|---:|
| .gitignore:17 `workspace/outputs/activation/` | 13 |
| .gitignore:39 `stock-strategy-system/market_snapshot*.json` | 1 |
| .gitignore:73 `workspace/outputs/portfolio-strategy/` | 3 |
| .gitignore:160 `workspace/outputs/lmt-instrument-registry-candidate-prep/` (새 줄) | 1 |
| .gitignore:161 `workspace/outputs/manual-portfolio-analysis/` (새 줄) | 1 |

## 지시문과 다른 점
1. **LMT 후보 파일 날짜.** 이 파일은 2026-09-02 11:46 KST에 만들어졌고, 파일 안 prepared_at도 2026-09-02다. 지시문의 "2026-08" 조건 밖이라 복사하지 않고 BLOCKED.md를 쓴 뒤 멈췄다. 사장이 직접 입력 "LMT 포함"(cmsg_0137MRzn9nuDvvQmVxm6WeX9Lv1nPMw9QVKLgCs6RULcte, 계정 user_01KuMGKfZu1SBYxtMmg4vAiH, 2026-11-02 21:57:18 KST)으로 정했다. 그 뒤 복사했고, BLOCKED.md는 지웠다. 이 파일은 계좌·현금·수량 칸이 없다(이름 grep 0건). 수정안 17행 "모두 2026-08"은 이 파일에 대해서는 틀렸다.
2. **멈춘 순서.** LMT를 찾은 뒤 바로 멈추지 않고, 사장에게 결정을 한 번만 묻기 위해 나머지 시험의 목록 찾기를 조건 안 파일로 끝냈다. 두 대상 파일은 사장 입력 뒤에 고쳤다.
3. **manual-portfolio-analysis 폴더.** 지시문과 수정안은 이 폴더가 `??`라고 적었지만, 본 저장소에서 `??`는 lmt 폴더뿐이다. 이 경로는 원래 .gitignore 146행으로 무시되고 있었다. 지시문대로 줄을 더했고, 해는 없다. 뒤에 나온 규칙이 우선하므로 위 (e)에는 161행으로 표시된다.
4. **lmt 폴더의 다른 파일.** 본 저장소 그 폴더에는 validate_lmt_registry_candidate.py(5,102바이트)도 있다. 복사하지 않았다. 새 .gitignore 줄 때문에 이 파일도 `??`에서 사라진다.
5. **worktree.** 원격 연결에서는 작업 폴더를 새로 고를 수 없어 이 실행 스레드의 worktree에서 Builder를 했다(gitattr-bytes와 같은 방식). 브랜치를 `claude/funny-brahmagupta-57aa0a`(41f7b3f)에서 `worktree-basefail-include`(c81ac2e)로 만들어 옮겼다. 이 명령은 지시문의 git 허용 목록 밖의 준비 단계다.
6. **복사 외 읽기.** Acceptance 835d4f46 manifest에서 source_artifacts의 경로 칸만 PowerShell로 뽑았다. LMT 파일은 머리 12행과 날짜·계좌 관련 이름 grep으로 읽었다. 복사 파일 내용은 이 보고서에 옮기지 않았다.
7. **줄바꿈.** 두 파일은 worktree에서 CRLF이고 고친 뒤에도 CRLF만 있다(.worktreeinclude CRLF 22·LF 0, .gitignore CRLF 161·LF 0). git에는 LF로 들어간다. include_candidates는 줄마다 strip()해 줄바꿈 영향이 없고, `#` 줄을 건너뛴다(tools/dev_pipeline/devpipe.py 1393~1401행).
8. **보호 경로.** stock-strategy-system/market_snapshot.example.json은 보호 접두어 안이지만 include_snapshot에 들어가므로, sha256이 같으면 위반이 아니다(devpipe.py 775~784행). 그 파일을 Builder가 고치면 지금처럼 보호 위반으로 멈춘다.

표지 없음.
