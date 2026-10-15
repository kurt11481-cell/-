---
id: t2rc-judge-prompt-2026-10-15
title: t2-rc M1~M3 · 115행 · 사전 등록 독립 Judge (읽기 전용)
date: 2026-10-14 (초안) · 실행 2026-10-15 07:35 KST 뒤
model: Opus · xhigh · 새 세션(메인 체크아웃, worktree 아님) — 계산기를 만든 Cowork 세션과 다른 세션
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션 · 이유: K3 판정 기준(T2 켜 조건)의 장치 3개와 매도 수량 읽기를 한 번에 판정한다.

너는 이 장치들을 만들지 않은 독립 검토자다. **파일을 고치지 않는다.** 쓰는 파일은 맨 끝의 보고서 1개뿐이다.

## 시작 조건
- `docs/claude/t2rc-rule115-draft-2026-10-15.md`(115행 보완 초안)가 있어야 시작한다. 없으면 보고서에 `VERDICT: HOLD — 115행 초안 없음`만 쓰고 끝낸다.
- 아래 sha256이 다르면 그 파일은 FAIL로 적고, 나머지는 판정한다. 계산기·실행기는 LF 정규화 sha다(`\r\n` → `\n` 뒤 계산).

| 파일 | sha256 |
|---|---|
| docs/claude/t2-rc-preregistration-2026-10-14.md | e798b8c57918d4def49c72bce49def5c83f473e712d19059735dec4ea4ef69d2 |
| docs/claude/t2rc-oracle.py (LF) | 6f0484322212d394d6c297944cabee797062c08e0c131affedddbc566e3435f6 |
| docs/claude/t2rc-check-run.ps1 | cfa0b81e3e4ee0bf92af832c0838515340e0369536ba58aa9a6170c69458b716 |
| docs/claude/t2rc-register-task.ps1 | e03e74e0264e1b4843344720406dc06849b0a54dabbc3b1497c33b6238e80bc4 |
| docs/claude/scheduled-prompts/pending-t2rc/auto-core-alert.txt | f021c4948a85d2c40f45e59767496e302e1c06ddd86a4c2ae7e88b79876a49d8 |
| docs/claude/scheduled-prompts/auto-core-alert.txt (기준 v2.1) | 66548192913d277d46d792bbcc25eebab86a8e53e85815e182a92b9b3b41ba68 |
| docs/claude/t2rc-rule115-draft-2026-10-15.md | 53994635bd1042487958e21981919c14a41d8d9bf7be6dd45dd2e852994dadc9 |
| docs/claude/integrated-check-prompt-v3.12.6-2026-10-15.txt (115행 반영 규칙 파일, LF) | 129f78af973df40a6cac8419c721c0e728293b21e3ed45b0a38dba062cbc071c |
| docs/claude/scheduled-prompts/pending-t2rc/integrated-check-daily.txt (로더 v3.12.6-L+R2) | 915e1966e31ca1d14cab89d953381b4ca5c0b589ea3a93686c8721310741e65f |
| 기준: docs/claude/integrated-check-prompt-v3.12.5-2026-10-14.txt (현행 규칙 파일) | 3e05c8efc1ef256acb82ec1a9c54ecca0485424f6368e40a627e859d18420ffb |
| 기준: docs/claude/scheduled-prompts/integrated-check-daily.txt (현행 로더 사본) | 206782f6584694e8143844b193576ec443438c14d1710f5d0320543998b49312 |

## 읽을 것
1. 사전 등록: docs/claude/t2-rc-preregistration-2026-10-14.md(전체).
2. 기록: docs/claude/t2rc-oracle-report-2026-10-14.md(5절 읽기 선택 14개, 6절 미해결, 8절 매도 재계산 S1~S7, 8-1 남은 위험 S8), docs/claude/t2rc-m2-m3-2026-10-14.md.
3. 원문: 통합 점검 규칙 파일 현행판(10-15 07:35 교체 뒤 판), docs/claude/order-instruction-design-2026-10-06.md(1절·1-1·3절·5절·7절), docs/claude/redesign-t2-builder-prompt-2026-10-10.md(D5~D8, F1~F6), docs/claude/recovery-gate-R-REC1-2026-10-09.md, manage-us-stock-strategy/references/portfolio-exposure-review.md, stock-strategy-system/alert_policy.json(값만).
4. 코어(비교용 — 계산기는 이것을 보지 않고 썼다): manage-us-stock-strategy/scripts/auto_core_tickets.py(매도 후회표·재배치 다리·after_sale), auto_core_decide.py(회로·요건·관문), auto_core_rules.py, portfolio_exposure.py.
5. 자료: workspace/outputs/auto-core/2026-10-13·2026-10-14/decision.json, workspace/outputs/auto-core/replay/prereg1009/replay.json.

## 돌려도 되는 것
- `python -I docs/claude/t2rc-oracle.py selftest --repo .`
- `python -I docs/claude/t2rc-oracle.py check --day 2026-10-14 --repo . --out <임시 폴더>\o1014.json` (10-13도 같은 방식)
- `python -I docs/claude/t2rc-oracle.py replay --replay-json workspace/outputs/auto-core/replay/prereg1009/replay.json --repo . --out <임시 폴더>\orep.json`
- `powershell -ExecutionPolicy Bypass -File docs\claude\t2rc-register-task.ps1 -PlanOnly`
- 금지: t2rc-check-run.ps1 실행(저장소 workspace에 결과를 씀), -PlanOnly 없는 등록, 키움 도구, auto_core.py·run_auto_core.ps1 실행, 커밋·병합, 파일 수정.

## 판정 항목
1. **독립성:** 계산기가 manage-us-stock-strategy/scripts를 import하지 않는다(import 줄 전체 확인). 코어 함수 구조를 옮겨 적은 흔적이 있으면 위치를 적는다(의견).
2. **M1 재현:** selftest PASS, 10-14 MATCH(counts_for_c1 true), 10-13 NOT_CHECKED(DECIDE_AFTER_0840), 리플레이 REPRODUCED(불일치 0)가 기록과 같다.
3. **M1 읽기 선택 14개(보고서 5절):** 각각 `원문과 맞음/다름 · 코어와 같음/다름`. 다르면 어느 쪽을 고칠지.
4. **매도 읽기 S1~S8(보고서 8절·8-1):** 각각 다음을 적는다.
   - 코어가 실제로 하는 것(파일:줄).
   - 원문에 맞는 읽기 하나.
   - 원문이 정하지 않은 S1(경로 합치는 방식)·S3(최선 후보)·S6(투자 한도)·S8(분야 한도)은 **제안 읽기**와 이유 1줄. 사용자가 적용 승인 때 한 번에 승인한다.
   - 코어와 계산기 중 정한 읽기와 다른 쪽, 고칠 최소 내용.
   - 피해 한도 주장(읽기는 r_max 이하 단계만 바꾼다. Δ·가격·관문·회로는 무관하다)이 코드에서 참인지.
5. **거짓 일치 경로:** 계산기가 "일치"를 잘못 낼 수 있는 길이 있나. 확인할 곳은 다음과 같다.
   - ticket_check의 match 조건
   - c3_record 자격(기록 모드, 판정, 자기 확인 제외, 같은 sha, 그날 모두 일치)
   - NOT_CHECKED 처리
   - 누수 검사
   - 매도 match 허용(새로 생김)
6. **M2:** 실행기와 등록 스크립트(정적 검토)를 다음 기준으로 본다.
   - 실행기 고정값 = 계산기 LF sha.
   - 실패 경로는 모두 ERROR 결과를 쓴다.
   - 쓰는 곳은 t2rc-check.json·LATEST_T2RC_CHECK.json·로그뿐이다.
   - 작업 설정: 화~토 08:40, 15분, Interactive·Limited, IgnoreNew, 깨우지 않음.
   - Windows PowerShell 5.1 호환은 정적으로 본다. 실제 5.1 실행은 확인되지 않았다.
7. **M3:** v2.2와 v2.1을 비교한다(diff).
   - 바뀐 곳: T2RC 파일 받기, ⑫ 불일치·오류·결과 없음 푸시, ⑬ 허락 안 된 주문표 = "주문표 확인 대기 — 입력 금지"·PUSH 줄 빼기·NEXT_USER 다시 쓰기·orders 제외, core.py 셋째 인자.
   - 그 밖은 글자 그대로인지.
   - 허락 규칙이 fail closed인지(파일 없음·다른 날·못 본 주문표 → 허락 안 함).
8. **사전 등록과 일치:**
   - M2 형식 차이를 적는다: 사전 등록의 "예약 작업 + 불일치만 푸시"를 Windows 작업 + 08:50 알림 ⑫로 했고, 오류·결과 없음도 알린다. 더 엄격한지 판정하고, 변경 기록 1줄 문안을 낸다.
   - 그 밖에 숫자·기준을 느슨하게 한 곳이 없는지.
9. **115행 초안(v3.12.5 → v3.12.6 규칙 파일·로더 diff 포함 — 규칙 파일 1·115행, 로더 1·4·12·18·75행만 달라야 함):** K1 문구만인지 본다(매수 불가 상품 + 쪽 state는 계산값 그대로, label만 "매수 불가 상품", 알림 없음). 대조(B1)와 코어 오류 검출이 그대로인지, 다른 행이 바뀌지 않았는지, 규칙 파일 현행판 sha 기준인지.
10. **권한:** 주문 경로 없음, 키움 호출 없음, 정책·상태·일지 쓰기 없음. 권한 표지(order_authority false · quantity_authority none · execution_quantity null) 줄도 확인한다.

## 출력
- 한국어 표 `| 항목 | PASS/FAIL | 근거(파일:줄) |`.
- 고칠 최소 항목(있으면, 고칠 쪽: 코어 = Claude Code Builder / 계산기 = Cowork 새 sha 뒤 이 Judge 범위 재확인).
- **사용자 적용 승인 묶음:** S1·S3·S6·S8 제안 읽기, 사전 등록 변경 기록 문안, 알림 교체, PowerShell 등록 1번, 115행 재서명. 한 줄씩 적는다.
- 마지막 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL`.
- 같은 내용을 **새 파일 하나** `docs/claude/t2rc-judge-report-2026-10-15.md`에 저장한다. 그 밖의 파일은 쓰지 않는다.
