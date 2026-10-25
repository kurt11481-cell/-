---
id: d6-builder-report
type: report
title: "D6·D3·D11·D12 Builder 보고 (수동 경로)"
as_of: "2026-10-25 KST, worktree-d6-cleanup, 기준 bb11f04, 커밋 안 함"
class: "Builder 보고. 커밋·병합·푸시 없음"
authority: "order_authority=false · quantity_authority=none"
source_decision: "사장 'D5, D8, D6, D3, D11, D12 승인'(2026-10-25 08:46Z) · 지시문 '확인'(08:54Z) · docs/claude/d6-builder-prompt.md"
consumers: "독립 Judge(읽기 전용 별도 세션) · 병합 여부를 정하는 사장"
---

# 결론

CLAUDE.md는 지시문의 7곳만 바뀌었다(5줄 추가·9줄 삭제, `git diff --stat`). Hard safety 절의 차이는 5번 한 줄뿐이다. 새 파일 4개(D3·D11 2개·D12)와 이 보고서를 만들었다. 커밋·병합은 하지 않았다.

# 1. CLAUDE.md 바뀐 곳 7개 (전 → 후)

| # | 위치 | 전 | 후 |
|---|---|---|---|
| 1 | Session hygiene 첫 항목 | `- At task start, state the recommended model/effort in one line: simple = low, routine = medium,` / `  analysis/dev = high, cross-file design / K3 / Judge = Opus xhigh. Ask the user to restart only when authority/limit` | `- Model and effort: Ask the user to restart only when authority/limit` (뒤 3줄 "or Judge work runs on a non-Opus model; … Never suggest switching model mid-session … Effort may change mid-session …"은 그대로) |
| 2 | Session hygiene | `- When the topic changes, tell the user to run /clear; if the task continues but context is long,` / `  suggest /compact at a natural stopping point.` | (삭제) |
| 3 | Session hygiene | `- Talk to the user in Korean, one step at a time, giving the exact command to type.` | (삭제) |
| 4 | Goal | `… Read-only work Cowork can do itself is done, not handed to the user.` | `… Read-only work the session can do itself is done, not handed to the user.` |
| 5 | Hard safety 마지막 항목 | `… never sells. A Cowork session that changes or accepts a card updates` | `… never sells. An interactive session that changes or accepts a card updates` |
| 6 | Working rules | `- Touch budget (2026-10-09 Q2, superseded 2026-10-10 by Goal): routine user touches target 0 except order entry. Every proposal states its weekly user-touch cost and may not add a routine touch. At most 3 active development tasks and 1 authority/limit change in progress at a time.` | `- Concurrency cap: At most 3 active development tasks and 1 authority/limit change in progress at a time.` |
| 7 | Working rules, Doc-only commits | `… when a Cowork session leaves docs/claude/ changes, …` | `… when an interactive session leaves docs/claude/ changes, …` |

- 6번 해석: 지시문대로 "Touch budget" 머리말과 괄호·앞 두 문장을 지우고 "Concurrency cap:" 머리말로 상한 한 문장만 남겼다. 상한 문장은 한 글자도 바꾸지 않았다. "routine user touches target 0"은 Goal 절 16행에 그대로 있다.
- 1번 해석: 첫 문장을 지우면 항목 머리가 "Ask the user …"로 시작해 어색하므로 지시문이 허용한 "- Model and effort:" 머리말만 붙였다. 남은 세 문장은 원문 그대로.
- 편집 방법: 바이트 단위 치환(각 원문이 파일에 정확히 1번 있는지 확인 후 교체). 줄바꿈 CRLF 유지(변경 전 129줄 모두 CRLF, 변경 후 125줄 모두 CRLF). 저장소에는 LF로 저장되고(`git show HEAD:CLAUDE.md` CRLF 0개) core.autocrlf=true라 diff에는 7곳만 나온다.

# 2. 해시

| 대상 | 변경 전 | 변경 후 |
|---|---|---|
| Hard safety 절 (`## Hard safety` ~ `## Kiwoom query rules` 직전, CR 제거 후 18~44행, 각 줄 끝 LF) | `7d60922e76a9fb08a2996bcfae8aff455807cd0c04249645ea78d0491fee8232` (지시문 기대값과 일치) | `4311e88cd19b97c332c7a4d564abb1226a645640f0f1e4a6f65f921db4d448dc` |
| CLAUDE.md 파일 전체(작업 트리 원본 바이트) | `1feb18f5ee10bb5d4e16a5e3a76f6aca4c58cde80e7d0a1fe7d2da62790c8159` (19,093바이트) | `db863a4ba7e8787eddeb96cc233b0a2d38edd761a4fe1adc5f4aee5184392199` (18,555바이트) |

Hard safety 절 diff(`git show HEAD:CLAUDE.md`와 작업 트리, 절만 잘라 비교)는 25번째 줄 하나 — 5번 — 뿐이다. 범위(18~44행)는 변경 뒤에도 같다. 같은 절의 다른 "Cowork" 문구(25·31·33행, 지시문 7-2의 (b) 묶음)는 바꾸지 않았다.

# 3. 새 파일

| 파일 | 내용 | 확인 |
|---|---|---|
| docs/claude/archive-candidates-2026-10-25.md (D3) | 이동 후보 64개(약 0.87MB)를 묶음별로, 파일마다 마지막 커밋·크기·문서 링크 수, 공통·묶음별 "이동 안 하면 비용". 후보에서 뺀 것과 이유, 동결 한 문단, 확인 필요 3건 | 추적 파일 전체에서 이름 참조를 다시 셈: 64개 모두 코드·테스트·예약 지시문(.txt)·사전 등록·주간 보고·로드맵·홈·scheduled-prompts 참조 0건. builder-prompt 61개는 00-home.md:21 보호 표 때문에 제외. 이동·삭제는 하지 않음 |
| docs/claude/new-pc-recovery-procedure.md (D11) | 백업 구성(offsite_backup.ps1 줄 근거), LATEST.json 위치와 10/24 결과, 제외 항목, 새 PC 복구 8단계, 복구 점검 사용법. 모르는 단계는 "확인 필요"(10개 항목 모음) | 인증은 세션이 재발급하지 않음(CLAUDE.md Kiwoom query rules)을 명시. SEC 작업이 환경 변수 `SEC_USER_AGENT`를 쓴다는 사실을 등록 스크립트 45행에서 찾아 넣음 |
| docs/claude/restore-hash-check-2026-10-25.ps1 (D11) | 최신 `YYYY-MM-DD.zip`을 `%TEMP%` 새 폴더에 항목별로 풀고(경로 이탈 차단) 저장소의 같은 파일과 sha256 대조, 화면 출력만, 임시 폴더 삭제. 종료 코드 0 PASS / 1 REVIEW / 2 FAIL | ASCII 확인(비 ASCII 줄 0). Windows PowerShell 5.1로 **가짜 저장소·가짜 zip(scratchpad)에서만** 실행: PASS 경로(2/2 일치, 최신 zip 선택, LATEST.json 요약 출력), DIFF·MISSING_ORIGINAL 경로, zip 폴더 없음(FAIL, exit 2), 임시 폴더 남음 0. 실제 OneDrive 백업과 실제 저장소에는 돌리지 않음 |
| docs/claude/tax-pretax-note-2026-10-25.md (D12) | 한 문단: 주문표·현행 점수는 세전, 세후는 승인된 세금 가정이 있을 때만. portfolio-policy.md 99-100행, capital-redeployment.md 34-35행 원문 인용. 세율·공제는 "확인 필요". 새 규칙 없음 | 코어·채점 코드의 "tax" grep(대조기 현금 흐름 분류뿐), 승인된 세금 가정 grep 0건 |
| docs/claude/d6-builder-report.md | 이 보고 | — |

새 파일은 저장소 관례대로 CRLF로 맞췄다.

# 4. 지시문과 다르게 적은 것 (원문 확인 결과)

- **capital-redeployment.md 줄 번호**: 지시문은 33-34행이지만 원문의 해당 문장은 34-35행이다(34행 "If cost, slippage, and tax", 35행 "assumptions are not approved, show gross proceeds and `ASSUMPTION_REQUIRED`."). D12 노트는 34-35행으로 인용했다.

# 5. 하지 않은 것과 이유

| 하지 않은 것 | 이유 |
|---|---|
| 커밋·병합·푸시, `_pending/` 파일 작성 | 지시문 C절. `_pending`은 메인 체크아웃 23:30 자동 커밋 대상이라 병합 전 쓰면 안 됨 |
| 5번 외 Hard safety 변경(25·31·33행 Cowork 문구 등) | 지시문 C절. 7-2 (b) 묶음은 D4 결정 뒤 |
| D5·D8(프로젝트 지침) | 이 묶음이 아님(지시문 머리) |
| CLAUDE.md의 다른 Cowork 문구(변경 후 기준 46·52-58·92·102-105·118-119행)와 관제판 항목(121행) | 7곳 밖. 7-2 (b) 묶음이거나 별도 판정 대상 |
| archive 실제 이동·builder-prompt 보호 표 개정 | D3 범위는 읽기 전용 목록 |
| 복구 점검을 실제 백업에 실행, 반복 예약 작업 만들기 | 실행은 사장 PowerShell 한 줄(새 PC 복구 절차 3절). 반복 작업은 D3 동결 |
| 관제판 갱신 | Builder 범위 밖. 병합 뒤 사장실 스레드가 갱신 |
| 새 규칙·권한(주문·한도·예산) 표현 변경 | 지시문 C절. 6번의 상한 문장은 글자 그대로 |

# 6. Judge가 확인할 것 (제안)

1. `git diff bb11f04 -- CLAUDE.md`가 위 7곳뿐인지, 각 문구가 지시문 A절과 같은지.
2. Hard safety 해시 전/후를 다시 계산(CR 제거, 18~44행, 각 줄 끝 LF)하고 차이가 5번 한 줄인지.
3. 6번이 상한 문장을 바꾸지 않았는지(권한·한도 표현 불변), 1번이 남겨야 할 세 문장을 지우지 않았는지.
4. 새 문서 4개의 인용 줄 번호를 원문과 대조, restore-hash-check 스크립트가 저장소·백업 폴더에 쓰지 않는지(쓰기는 `%TEMP%` 임시 폴더뿐).
5. archive 후보 64개 중 살아 있는 소비자가 있는 파일이 없는지(표본 대조).

검토 완결: 원문 확인 — CLAUDE.md 전체, Hard safety 해시 재계산, 근거 문서 operating-diagnosis 전체, offsite_backup.ps1 전체, LATEST.json, 등록 스크립트 6개 줄, references 2개 줄, 참조 스캔(추적 1,711개) · 내장 재검토 0회(Builder 보고, 결정 요청 없음 — 판정은 독립 Judge) · 미해결: D3 3건·D11 10건·D12 1건(각 문서의 "확인 필요") · 자료 시점 2026-10-25 KST, bb11f04 · 바뀔 조건: Judge가 7곳 밖 차이나 Hard safety의 다른 차이를 찾으면 되돌림.
