---
id: t2rc-judge2-prompt-2026-10-15
title: t2-rc 독립 Judge 2차 — 1차 FAIL 수정분 재판정 (읽기 전용)
date: 2026-10-15
model: Opus · xhigh · 새 세션(메인 체크아웃) — 계산기를 고친 Cowork 세션·코어 Builder와 다른 세션. 1차 Judge 세션을 이어 써도 된다
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(또는 1차 Judge 세션) · 이유: 1차 FAIL 항목만 다시 판정한다.

너는 독립 검토자다. **파일을 고치지 않는다.** 쓰는 파일은 맨 끝 보고서 1개뿐이다.

## 시작 조건
- `git log --oneline -30`에 코어 수정 커밋 "fix(auto-core): R-REC1 events on SOXX …(t2-rc Judge 2026-10-15)"가 있고 `docs/claude/t2rc-corefix-report.md`가 있어야 한다. 없으면 보고서에 `VERDICT: HOLD — 코어 수정(t2rc-corefix) 병합 전`만 쓰고 끝낸다.
- 아래 sha256(계산기·실행기는 LF 정규화)이 다르면 그 파일은 FAIL로 적고 나머지를 판정한다.

| 파일 | sha256 |
|---|---|
| docs/claude/t2rc-oracle.py (LF) | ae4a1e8eb3efbdb212ae52765fe62b5bb16370c6c3a98dfe45f3a7723f635c16 |
| docs/claude/t2rc-check-run.ps1 | ff853bc32fc00d740a81f94ed340cd94d159dc3ee6c62584839913c0b67807de |
| docs/claude/t2rc-register-task.ps1 | e03e74e0264e1b4843344720406dc06849b0a54dabbc3b1497c33b6238e80bc4 |
| docs/claude/scheduled-prompts/pending-t2rc/auto-core-alert.txt (v2.2 수정) | eb2b9710d7562b6db831e2d4b98d6185c9e292f8bc028c244e4f636af971e4e2 |
| docs/claude/scheduled-prompts/pending-t2rc/integrated-check-daily.txt | 915e1966e31ca1d14cab89d953381b4ca5c0b589ea3a93686c8721310741e65f |
| docs/claude/integrated-check-prompt-v3.12.6-2026-10-15.txt | 129f78af973df40a6cac8419c721c0e728293b21e3ed45b0a38dba062cbc071c |
| docs/claude/t2-rc-preregistration-2026-10-14.md | e798b8c57918d4def49c72bce49def5c83f473e712d19059735dec4ea4ef69d2 |

## 읽을 것
- 1차 보고 docs/claude/t2rc-judge-report-2026-10-15.md(특히 3·4·5·7·11절).
- 수정 기록: docs/claude/t2rc-oracle-report-2026-10-14.md 9절, docs/claude/t2rc-m2-m3-2026-10-14.md 8절, docs/claude/t2rc-corefix-report.md.
- 계산기 diff: `git diff cf2c86c -- docs/claude/t2rc-oracle.py`(1차 때 계산기 6f048432…는 cf2c86c 이후 첫 변경 전 판). 알림 diff: `git diff --no-index`로 1차 판(f021c494…, git 기록)과 비교한다.
- 코어 diff: t2rc-corefix 병합 커밋.

## 돌려도 되는 것
- 1차와 같다: selftest, check 10-13·10-14·10-15(그리고 오늘 decide가 있으면 오늘), replay, register -PlanOnly.
- 금지도 1차와 같다.
- 스크래치(저장소 밖)에서 코어 스키마 형식 주문표를 만들어 계산기를 시험해도 된다. 1차 fmt_demo처럼 저장소 코드를 import하지 않는 방식이면, 계산기 파일을 importlib로 읽어 시험해도 된다.

## 판정 항목
1. **1차 11절 "계산기" 1~12:** 항목마다 고침 / 결함 / 안 함. 11번 권장 중 안 한 것(재발행 원장·등록부 미커밋·진단 표기)은 FAIL 사유인지 의견.
2. **1차 11절 "코어" 1~5:** 코어 diff가 지시와 같은지(5번은 사용자 결정 "t2rc-corefix: 1~4 진행, 5 = b" — 매수만 오늘 hit 기준, 매도는 지금 그대로). 그 결과 코어와 계산기가 같은 읽기가 됐는지. 5 = b가 설계 G3와 다른 점(매도)은 사용자 결정으로 기록됐는지만 보고, 그 자체를 FAIL 사유로 삼지 않는다.
3. **새로 생긴 경로:** 매도 match, C1 가드, c3 누락 조건, C7 10 기록일, EV4 이력, EV3ⓑ 공백. 거짓 일치·거짓 허락 길이 있는지 본다.
4. **실제 코어 주문표 형식 대조:** 관문·가격·D18이 이제 코어 형식과 맞는지. 코어 코드(auto_core_tickets.py 매수·매도 주문표)와 맞대 본다. 남은 차이 2개도 코어와 같은지 확인한다: 센트 반올림 순서, C7 16:00 정각 경계(계산기는 close_at ≤ announced_at).
5. **알림 v2.2 수정:**
   - 넘어온 주문표 허락 검사와 generated_at 일치 조건이 맞는지.
   - 1차 m3demo를 다시 돌려 막히는지.
   - 평일 경로가 그대로인지.
6. **실행기 고정값:** 새 계산기 sha와 같은지.
7. **1차 PASS 항목(독립성·M2·사전 등록·115행·권한):** 바뀐 파일이 그 판정을 뒤집지 않는지.

## 출력
- 한국어 표 `| 항목 | PASS/FAIL | 근거(파일:줄) |`, 고칠 최소 항목.
- 사용자 적용 승인 묶음(1차 12절에서 바뀐 것만).
- 마지막 줄은 정확히 `VERDICT: PASS` · `VERDICT: FAIL` · `VERDICT: HOLD — <사유>` 중 하나.
- 같은 내용을 새 파일 `docs/claude/t2rc-judge2-report-2026-10-15.md` 하나에 저장한다.
