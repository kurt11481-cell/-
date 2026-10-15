---
id: t2rc-judge3-prompt-2026-10-15
title: t2-rc 독립 Judge 3차 — 2차 FAIL 계산기 4건 재판정 (읽기 전용)
date: 2026-10-15
model: Opus · high · 2차 Judge 세션을 이어 쓰거나 새 세션(메인 체크아웃). 계산기를 고친 Cowork 세션과 다른 세션
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: high · 세션: 2차 Judge 세션 유지(또는 새 세션) · 이유: 2차 10절 4건과 그 영향 범위(1·3·4·6)만 다시 판정한다.

너는 독립 검토자다. **파일을 고치지 않는다.** 쓰는 파일은 맨 끝 보고서 1개뿐이다.

## 시작 조건
- 아래 sha256이 다르면 그 파일은 FAIL로 적고 나머지를 판정한다(모두 LF).

| 파일 | sha256 |
|---|---|
| docs/claude/t2rc-oracle.py | 5607b09b47585a8b0799ae84b93cff434ebecdfc2b30f305607c8641b8f02a26 |
| docs/claude/t2rc-check-run.ps1 | 5d3502b90b3901823e0eded7d196d7c6710b63765bc7d003dc3e1ef313d2df7b |
| docs/claude/t2rc-register-task.ps1 | e03e74e0264e1b4843344720406dc06849b0a54dabbc3b1497c33b6238e80bc4 |
| docs/claude/scheduled-prompts/pending-t2rc/auto-core-alert.txt | eb2b9710d7562b6db831e2d4b98d6185c9e292f8bc028c244e4f636af971e4e2 |
| docs/claude/scheduled-prompts/pending-t2rc/integrated-check-daily.txt | 915e1966e31ca1d14cab89d953381b4ca5c0b589ea3a93686c8721310741e65f |
| docs/claude/integrated-check-prompt-v3.12.6-2026-10-15.txt | 129f78af973df40a6cac8419c721c0e728293b21e3ed45b0a38dba062cbc071c |
| docs/claude/t2-rc-preregistration-2026-10-14.md | e798b8c57918d4def49c72bce49def5c83f473e712d19059735dec4ea4ef69d2 |

## 읽을 것
- 2차 보고 docs/claude/t2rc-judge2-report-2026-10-15.md(0·3·5·6·10절).
- 수정 기록 docs/claude/t2rc-oracle-report-2026-10-14.md 10절.
- 계산기 diff: 2차 판(ae4a1e8e…)은 HEAD에 커밋되어 있다 → `git diff HEAD -- docs/claude/t2rc-oracle.py docs/claude/t2rc-check-run.ps1`(23:30 문서 커밋 뒤면 그 커밋의 부모와 비교).

## 돌려도 되는 것·금지
- 2차와 같다: selftest, check 10-13·10-14·10-15(+ `--ignore-input-sha` self-check), replay, register -PlanOnly, 저장소 밖 스크래치 시험(2차 fmt2 등 재사용 가능). 금지도 같다.

## 판정 항목
1. **2차 10절 1~4:** 항목마다 고침 / 결함.
   - ⅓ 수량: 2차 분리 시험(1~3000, 무작위 20만 건)을 다시 돌려 코어 step_quantity와 0건 차이인지.
   - C1 가드: MATCH만 NOT_CHECKED, MISMATCH는 그대로 C1·⑫로 가는지(apply_gap_guard, counts_for_c1, 알림 v2.2:127).
   - EV4 현금: equity_cash_t2가 사용자 결정 t2-equity-cash·코어 decide:141-163과 같은 값을 내는지. 10-13 self-check 총자산 27,695.1487.
   - C7: `<`, 2차 스크래치 16:00 재현이 이제 코어와 같은지.
2. **새로 생긴 거짓 일치·거짓 허락 길:** 바뀐 4곳에서만 본다.
3. **2차 PASS 항목(코어·알림·독립성·M2·사전 등록·115행·권한)이 이 diff로 뒤집히지 않는지.** 독립성: 새 import 없음.
4. **실행기 고정값 = 새 계산기 sha.**

## 출력
- 한국어 표 `| 항목 | PASS/FAIL | 근거(파일:줄) |`, 고칠 최소 항목.
- 사용자 적용 승인 묶음(2차 11절에서 바뀐 것만).
- 마지막 줄은 정확히 `VERDICT: PASS` · `VERDICT: FAIL` 중 하나.
- 같은 내용을 새 파일 `docs/claude/t2rc-judge3-report-2026-10-15.md` 하나에 저장한다.
