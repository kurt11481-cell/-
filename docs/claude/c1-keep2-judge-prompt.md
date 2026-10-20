---
id: c1-keep2-judge-prompt
title: c1-keep2 확인 Judge (읽기 전용) — 10-17 한 날 C1 셈 일회 복원
date: 2026-10-20
class: K3 독립 Judge — 사전 등록 docs/claude/t2-rc-preregistration-2026-10-14.md 1절 C1 초기화(24·50·51행)의 일회 예외, c1-keep(FAIL)의 범위 축소안
model: Opus · xhigh · 새 세션(메인 체크아웃, worktree 아님). c1-keep Judge와 같은 세션이 아니어도 되고 같은 사람이 아니어도 된다
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 키움 주문 도구 금지
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(메인 체크아웃) · 이유: K3 독립 Judge(T2 "켜" 조건 C1 셈)

너는 이 제안을 만들지 않은 독립 검토자다. **파일을 고치지 않는다.** 저장소 안에 쓰는 파일은 보고서 1개뿐이다(복원 사본·출력은 저장소 밖 임시 폴더). 앞선 보고서·README의 숫자는 위치 안내일 뿐이다 — 10-17 재현은 네가 다시 한다.

## 제안(결정 c1-keep2: 10-17, 사용자 2026-10-20 15:46 KST)
실운영 비교 세션 **2026-10-17(실행일, 평가 세션 2026-10-16) 한 날만** C1에 다시 센다(C1 1/10 → 2/10). 조건: 현행 계산기(sha256_lf 6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64)와 현행 메인 체크아웃 코어가 그날 입력으로 그날 결과를 재현한다(허용 차이 = EV4 표지와 그 필드 없음). 10-16·D0·C2·C3·C4·C5·24행 초기화 규칙은 그대로.

## 읽을 것
1. docs/claude/c1-keep-judge-report.md 전문 — 특히 "재현 방법"(그날 판 복원 원천: 그날 decision.json commit_sha의 blob, stock-strategy-system/backups r28 = ddcb987a, 원장 앞 14줄, 일지 앞 6건, 페이지 이름 날짜 ≤ 실행일, 종가 이력 재생성), 항목 2 비교 70칸 정의, 항목 3 커밋 표, N2.
2. docs/claude/c1-keep-2026-10-20/README.md(결정 기록 두 절).
3. 사전 등록 전문(0절 16~19행, 1절 22~26행, 변경 기록 48~52행).
4. workspace/outputs/auto-core/2026-10-17/의 decision.json·t2rc-check.json·s7/.

## 돌려도 되는 것 / 금지
c1-keep Judge 지시문(docs/claude/c1-keep-judge-prompt.md) "돌려도 되는 것"과 같다. 10-17만 다룬다.

## 판정 항목
| # | 항목 | PASS 조건 |
|---|---|---|
| 1 | 계산기 재현(10-17) | 그날 판 복원본에서 `--ignore-input-sha` 없이: input_sha_mismatch []·input_path_mismatch []·verdict MATCH·counts_for_c1 true·historical_self_check false, 원래 t2rc-check.json과 차이 = oracle_sha256·ev4_history뿐(그 밖 차이 키 전부 표로, 부동소수 ≤ 1e-12 허용) |
| 2 | 현행 코어 재현(10-17) | decide 안 S7을 포함한 현행 코어가 낸 candidates·tickets·blocked·buy_requirements 칸 s·evidence basis_met/new_basis_met·shock(EV4 제외)이 그날 decision.json과 70/70 같음 |
| 3 | 사이 변경 | 10-17 decision.json commit_sha..HEAD의 코어·계산기·실행기·정책 커밋을 전부 분류하고, 10-17 결과를 바꾸는 것이 없음(210e951 포함 — 10-16 종가 23,695.43이 옛·새 L2 문턱 모두보다 낮아 S7 멈춤이 같은지 원문으로) |
| 4 | 다른 셈 영향 | C1 누계를 코드로 세는 곳 없음, c3_record·C2·D0·C4·C5 불변(앞 보고서 항목 4를 원문으로 다시 확인) |
| 5 | 사전 등록 정합 | 0절 예외 명시, 사용자 결정 기록(README c1-keep2 절), 한 날 한정, 24행 불변. 적용 문구 1줄 초안(50·51행 초기화 모두 인용) 제시 |
| 6 | 범위·안전 | 보고서 외 쓰기 0(`git status --porcelain` 전후), 권한 표지 불변, 금지 실행 0 |

## 보고서
docs/claude/c1-keep2-judge-report.md 하나만 쓴다. 항목별 PASS/FAIL/NOT_VERIFIED, 원문 위치·재계산 값, 차단 결함, 의견(따로 표시). 마지막 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL`. 하나라도 FAIL·NOT_VERIFIED면 FAIL(기본 처분 NO_CHANGE).
