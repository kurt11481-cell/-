---
id: c1-keep-judge-prompt
title: c1-keep 독립 Judge (읽기 전용) — 10-16·10-17 C1 셈 일회 복원
date: 2026-10-20
class: K3 독립 Judge — 사전 등록 docs/claude/t2-rc-preregistration-2026-10-14.md 1절 C1의 초기화(24·50·51행)에 대한 일회 예외
model: Opus · xhigh · 새 세션(메인 체크아웃, worktree 아님)
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 키움 주문 도구 금지
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(메인 체크아웃) · 이유: K3 독립 Judge(T2 "켜" 조건 C1 셈)

너는 이 제안을 만들지 않은 독립 검토자다. **파일을 고치지 않는다.** 저장소 안에 쓰는 파일은 맨 끝의 보고서 1개뿐이다(예외: 저장소 밖 임시 폴더의 복원 사본·계산기 `--out`). Cowork 기록의 숫자·주장은 위치 안내일 뿐이다 — 판정은 네가 연 원문과 네가 다시 계산한 값으로 한다.

## 제안(결정 c1-keep: a, 사용자 2026-10-20 14:51 KST)
병합 0d55b9a(ev-rg1-hyper, 10-18)·5d5cf79(rrec-ev4-remove, 10-19) 때 C1이 0/10으로 초기화되며 버려진 실운영 비교 세션 **2026-10-16·2026-10-17 두 날만** 다시 C1에 센다. 조건: 현행 계산기(sha256_lf 6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64)와 현행 코어가 그날 입력으로 그날 결과를 그대로 재현한다. 효과: C1 1/10 → 3/10. 그 밖의 규칙(C2 병합 전 일치 불산입, C3, D0 10-16, C4·C5 날짜)은 그대로.

## 읽을 것
1. docs/claude/c1-keep-2026-10-20/README.md(방법·결과·한계·결정 기록)와 t2rc-recheck-2026-10-16.json·t2rc-recheck-2026-10-17.json.
2. 사전 등록 docs/claude/t2-rc-preregistration-2026-10-14.md 전문(특히 0절 16~19행, 1절 22~26행, 변경 기록 48~52행).
3. 원래 결과 workspace/outputs/auto-core/2026-10-16/·2026-10-17/의 t2rc-check.json·decision.json(inputs의 경로·sha).
4. 앞선 Judge: docs/claude/rrec-ev4-remove-judge-report.md 항목 3·4·10, docs/claude/ev-rg1-hyper-judge2-report.md(실데이터 항목) — 위치 안내로만 쓴다.
5. 계산기 docs/claude/t2rc-oracle.py: cmd_check 1447~1520·1595~1660, circuit_for_session 1259~1305, c3_record 1660~1690. 코어 manage-us-stock-strategy/scripts/auto_core_tickets.py 715~790(회로·후보), auto_core_inputs.py check_record·load_research, auto_core_replay.py main 397~.

## 돌려도 되는 것
- 저장소 밖 임시 폴더에 계산기가 읽는 파일만 복사한 사본(README "방법")을 만들고, 그날 decision.json inputs의 sha와 같은 판으로 바뀌는 입력(등록부·관심 명단·R-REC1 문서·portfolio_state·카드 문서)을 복원한 뒤 `python docs/claude/t2rc-oracle.py check --day <날> --repo <사본> --out <저장소 밖>`(**--ignore-input-sha 없이**). decision.json 파일 시각은 원본과 같게(touch -r).
- 복원 원천: git 이력(`git show <커밋>:<경로>`)과 .claude/worktrees/*/ 안의 같은 sha 사본. sha가 같은 판을 못 찾으면 그날은 NOT_VERIFIED.
- 코어 재현: auto_core_replay.py가 저장소에 쓰지 않는 읽기 전용 경로로 그날(평가 세션 10-15·10-16, 실행일 10-16·10-17)을 돌릴 수 있으면 출력은 저장소 밖으로만. 아니면 파일을 쓰지 않는 별도 python 프로세스에서 코어 함수를 import해 재계산. "auto_core.py"가 든 명령은 거부되므로 쓰지 않는다. 테스트는 `-p "test_auto_core*.py"`만.
- 금지: 키움 호출, auto_core.py·run_auto_core.ps1·t2rc-check-run.ps1·dev-run·dev-merge·reconcile apply 실행, 커밋·병합, workspace/outputs·stock-strategy-system·docs/claude(보고서 제외)·정책·예약 작업·관제판 쓰기.

## 판정 항목
| # | 항목 | PASS 조건 |
|---|---|---|
| 1 | 계산기 재현 | 두 날 모두 너의 복원본에서 `input_sha_mismatch` []·`input_path_mismatch` []·verdict MATCH·counts_for_c1 true·historical_self_check false. 원래 t2rc-check.json과 비교해 차이가 `oracle_sha256`·`oracle_version`·`ev4_history`·`read_files`·`decision.result_written_at`·`c3` 계산 시점 필드·부동소수 1e-12 이하뿐(차이 키 전부를 표로). README의 재검사 json과도 같은지 확인 |
| 2 | 새 코어 재현 | 현행 메인 체크아웃 코어가 그날 입력으로 낸 결과의 candidates·tickets·blocked·buy_requirements 각 칸 상태(s)·evidence(방향별 basis_met·new_basis_met)·shock(사건 날짜·RG1~RG4·status·open)이 그날 decision.json과 같다. 허용 차이: shock kinds의 "EV4"만 빠짐(rrec-ev4-remove)과 그에 따른 필드 없음. 재현 방법을 못 만들면 NOT_VERIFIED → 이 항목 FAIL(fail closed) |
| 3 | 사이 변경 전수 | `git log --format='%h %ci %s' <10-16 decision.json commit_sha>..HEAD -- manage-us-stock-strategy/scripts docs/claude/t2rc-oracle.py docs/claude/t2rc-check-run.ps1 workspace/policies/auto_core.json stock-strategy-system/alert_policy.json`의 모든 커밋을 나열하고, 각각 항목 1·2가 덮는지 또는 그날 결과와 무관한지 원문으로 분류. 분류 못 한 커밋 0 |
| 4 | 다른 셈 영향 | C1 누계를 코드로 세는 곳이 없음(grep: t2rc-oracle.py·auto_core*·scheduled-prompts·tools — 관제판 next 문구와 ceo.py 210행 인용뿐인지). c3_record(1673행 같은 계산기 sha만 셈)·C2(병합 전 일치 불산입)·D0·C4·C5가 이 제안으로 바뀌지 않음 |
| 5 | 사전 등록 정합 | 제안이 0절 "느슨하게 바꾸지 않는다"의 예외임을 분명히 하고, 사용자 K3 결정(README 결정 기록)이 있으며, 적용 문구가 두 날로만 한정되고 앞으로의 초기화 규칙(24행)을 바꾸지 않음. 적용 문구 초안을 보고서에 1줄로 제시 |
| 6 | 범위·안전 | 이 Judge가 보고서 외 파일을 쓰지 않음(`git status --porcelain` 전후 비교). 권한 표지 변경 없음 |

## 보고서
docs/claude/c1-keep-judge-report.md 하나만 쓴다: 항목별 PASS/FAIL/NOT_VERIFIED와 원문 위치·재계산 값, 차단 결함, 권고(의견은 따로 표시). 마지막 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL`. 항목 하나라도 FAIL·NOT_VERIFIED면 FAIL(기본 처분 NO_CHANGE).
