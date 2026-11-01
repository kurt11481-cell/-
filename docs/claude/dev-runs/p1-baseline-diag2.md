# dev-run p1-baseline-diag2 — FAIL

- 시각(UTC): 2026-11-01T06:00:05Z → 2026-11-01T06:42:55Z
- 기준 커밋(base): `9726677b9da7755b1e1761ff3f5d52d736b58869` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **FAIL** · 재시도: 1
- 테스트: 기준선 Ran 3436 · 실패 283 → 변경 후 Ran 3436 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `None`
- Judge 파일 sha256: `None`
- 사유: judge_fail_after_fix
- 다음: `see docs/claude/dev-runs/p1-baseline-diag2.md`

## 바뀐 파일

- `docs/claude/p1-baseline-diag2-report.md`

## Judge 보고 원문 (1회차 FAIL)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | FAIL | 시작 시점이 틀렸다. 보고서는 2026-10-30T21:15Z 이후로 적었지만(`docs/claude/p1-baseline-diag2-report.md:26`), 33bae7d 기준선(실패 283)은 그보다 약 19시간 앞선 2026-10-30T01:50~01:58Z 실행의 기록이다(`docs/claude/dev-runs/s7-hold-gap.md:3,7`). 또한 False가 나는 지점을 찾지 못했다(보고서:27,31). 다만 읽기만으로 후보를 짚을 수 있었다. |
| G2 범위 | PASS | 바뀐 경로는 보고서 1개이고 allowed_paths 안이다(`changed-files.txt:1`, `checks.json:17-19`, `task-prompt.md:57`). |
| G3 주문·체결 추정 | PASS | 문서만 추가했고 코드 변경이 없다(`diff.patch:1-59`). |
| G4 정책·상태 쓰기, fail-closed | PASS | 쓰기 경로가 없다(`diff.patch:1-59`). 모르는 값은 "확인 필요"로 남겼다(보고서:20,27,36,46). |
| G5 비밀·계좌 | PASS | 비밀이나 계좌 식별자가 없다. 보유 종목과 수량만 인용했다(보고서:11). |
| G6 단언·skip·새 동작 테스트 | PASS | 테스트 변경이 없고 새 실패도 없다. `EXPECTED_FAILURES_INCREASED`도 없다(`checks.json:82,381-382`). |
| G7 class | PASS | 코드·권한·한도 변경이 없다(`checks.json:77-78`). class_ok=true다. |
| G8-1 diff가 보고서 1개 | PASS | `diff.patch:1-5`, `changed-files.txt:1` |
| G8-2 분류별 근거 | FAIL | 표의 시작 날짜와 "볼 방법이 없다"는 설명이 worktree 안의 기록과 어긋난다(보고서:26). 기준선 시각은 `dev-runs/recon-krw.md:3,7`과 `dev-runs/s7-hold-gap.md:3,7`에 있다. 보유 변경은 rev31이고, rev31이 들어간 10/30 07:45 KST 판정 기록이 있다(`s7-hold-gap-2026-10-30.md:15-17`, `ceo-weekly-report.md:297-298`). `:2796`은 `TechnicalTimingConsumerAlignmentTests.compile` 안에 있어서, 그 경로 밖의 ManualStep2TimingTests 4건에는 근거가 없다. 복사 경로도 읽어서 확인할 수 있었는데 "확인 필요"로 남겼다(보고서:36, `.worktreeinclude:1`, `devpipe.py:1051-1055`). |
| G8-3 실패 수 일치 | FAIL | 대시보드 결과가 없고 "약 249"만 있다(보고서:18-20). 파이프라인 기록은 Ran 306, 실패 이름 246건이다(`checks.json:404-653`). (a)는 전체를 약 249로 적었는데 (b)는 약 249에 다른 클래스를 더 얹어 서로 맞지 않는다(보고서:27-28). "255+7"은 이중 계산이다. 7건은 255건 안에 들어 있다(`task-prompt.md:12`, `code-review-pipeline-2026-11-01.md:23`, 보고서:21,46). 출력을 PowerShell로 다시 실행했다는 기록도 지시문 위반이다(보고서:18, `task-prompt.md:31`). |
| G8-4 수정 흔적 없음, 제안만 | PASS | 코드 변경 없이 제안만 있다(보고서:41-47, `checks.json:17-19`). |
| G8-5 (a)~(e)와 표지 | FAIL | 표지는 0건이다(보고서 전체를 Grep해 확인). (b)~(e)도 있다. 그러나 필수인 (a)에 대시보드의 마지막 3줄이 없다(보고서:18). |

```json
{"verdict": "FAIL", "class_ok": true, "items": [{"id": "G1", "result": "FAIL", "evidence": "docs/claude/p1-baseline-diag2-report.md:11,26,27,31; docs/claude/dev-runs/s7-hold-gap.md:3,7; docs/claude/s7-hold-gap-2026-10-30.md:15-17; manage-us-stock-strategy/scripts/materialize_instrument_identity_artifact.py:36-39"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/p1-baseline-diag2/changed-files.txt:1; checks.json:17-19"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/p1-baseline-diag2/diff.patch:1-59"}, {"id": "G4", "result": "PASS", "evidence": "workspace/outputs/dev-runs/p1-baseline-diag2/diff.patch:1-59; docs/claude/p1-baseline-diag2-report.md:20,27,36,46"}, {"id": "G5", "result": "PASS", "evidence": "docs/claude/p1-baseline-diag2-report.md:11"}, {"id": "G6", "result": "PASS", "evidence": "workspace/outputs/dev-runs/p1-baseline-diag2/checks.json:82,381-382"}, {"id": "G7", "result": "PASS", "evidence": "workspace/outputs/dev-runs/p1-baseline-diag2/checks.json:77-78"}, {"id": "G8-1", "result": "PASS", "evidence": "workspace/outputs/dev-runs/p1-baseline-diag2/diff.patch:1-5"}, {"id": "G8-2", "result": "FAIL", "evidence": "docs/claude/p1-baseline-diag2-report.md:26-28,36; docs/claude/dev-runs/recon-krw.md:3,7; docs/claude/dev-runs/s7-hold-gap.md:3,7; docs/claude/ceo-weekly-report.md:297-298; .worktreeinclude:1; tools/dev_pipeline/devpipe.py:1051-1055"}, {"id": "G8-3", "result": "FAIL", "evidence": "docs/claude/p1-baseline-diag2-report.md:18-21,27-28,46; workspace/outputs/dev-runs/p1-baseline-diag2/checks.json:404-653; workspace/outputs/dev-runs/p1-baseline-diag2/task-prompt.md:12,31; docs/claude/code-review-pipeline-2026-11-01.md:23"}, {"id": "G8-4", "result": "PASS", "evidence": "docs/claude/p1-baseline-diag2-report.md:41-47; workspace/outputs/dev-runs/p1-baseline-diag2/checks.json:17-19"}, {"id": "G8-5", "result": "FAIL", "evidence": "docs/claude/p1-baseline-diag2-report.md:17-18"}], "min_fixes": ["보고서 11·26·51행의 시작 시점을 고친다. 기준선 1e43b43은 2026-10-28T22:35Z 실행(실패 합 31, recon-krw.md:3,7), 33bae7d는 2026-10-30T01:50~01:58Z 실행(실패 283, s7-hold-gap.md:3,7)의 기록이다. 보유 변경은 지금 파일의 rev32가 아니라 rev31(as_of 10/29)이다(s7-hold-gap-2026-10-30.md:15-17, ceo-weekly-report.md:297-298). 26행의 '기록이 범위 밖' '볼 방법이 없다'를 지우고, rev31의 정확한 기록 시각은 원장이 없으므로 '확인 필요'로 둔다. 그에 맞게 51행의 바뀔 조건도 고친다.", "(a)와 (b)의 대시보드 수를 맞춘다. checks.json의 targets 값인 Ran 306, 실패 이름 246건을 출처와 함께 적는다. 클래스별 내역은 ManualTimingEvidenceContractTests 89, ManualCorporateActionClearanceTests 82, ManualKiwoomOnlyTimingTests 51, ManualStep2TimingTests 4, PortfolioDecisionDashboardTests 1, 나머지 5개 클래스 합 19다. failures와 errors 구분을 얻지 못하면 '확인 필요'로 적는다. 재실행이 필요하면 지시문 명령 그대로만 쓰고 PowerShell은 쓰지 않는다.", "보고서 21·46행의 '255+7'을 255건으로 고친다. 7건은 255건 안에 포함된다.", "보고서 27·31행에서 False가 나는 지점을 읽기로 따라간다. 후보 경로는 테스트 신원 등록부 범위에 LITE가 없음(materialize_instrument_identity_artifact.py:36-39, test_integrated_authority_snapshot.py:653) -> _authority_context의 NOT_VERIFIED(run_manual_portfolio_analysis.py:1107-1110) -> partial_reasons 추가(:1657-1660) -> validate_manual_direction_evidence의 False(:981-983)다. resolve_instrument_identity_from_snapshot의 동작을 읽어 맞으면 근거로 적고, 틀리면 틀린 이유를 적는다. BE는 범위 안, LITE는 범위 밖이므로 구분해 적고, '값을 찍어야만 알 수 있다'는 설명과 '기원은 확정' 표현을 고친다.", ":2796 경로 밖의 실패를 따로 다룬다. ManualStep2TimingTests 4건(checks.json:598-601), ManualCliInputWiringTests 등에 대표 테스트의 실패 지점을 적는다. 28행의 UNKNOWN은 실제 이름인 test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan(checks.json:583)으로 바꾸고, 근거가 없으면 UNKNOWN과 이유를 적는다.", "보고서 36행의 '복사 경위 확인 필요'를 .worktreeinclude:1, tools/dev_pipeline/README.md:53, tools/dev_pipeline/devpipe.py:1051-1055를 읽어 해소한다. 그리고 기준선 worktree가 메인의 살아 있는 상태 파일을 복사해 쓰는지를 적는다."]}
```

VERDICT: FAIL

## Judge 보고 원문 (2회차 FAIL)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | FAIL | 주 결론과 `:2796` 계열 243건 추적은 원문과 맞다. 그러나 `:2796` 밖 5건의 원인이 틀렸거나 읽기로 판단 가능한데도 UNKNOWN이다. 잔여 실패 추정도 틀렸다(docs/claude/p1-baseline-diag2-report.md:46-47, 68-72, 92) |
| G2 범위 | PASS | changed-files.txt:1, checks.json:17-19. 보고서 1개뿐이다 |
| G3 주문·체결 추정 | PASS | diff.patch:1-6. 문서만 추가했고 주문 경로나 체결 추정 코드가 없다 |
| G4 정책·상태 쓰기, fail-closed | PASS | 코드 변경이 없다. 열지 못한 항목은 "확인 필요"로 표시했다(report:18, 101) |
| G5 비밀·계좌 식별자 | PASS | 보고서에 토큰, 계좌번호, 계좌 식별자가 없다 |
| G6 단언 약화·skip | PASS | 테스트 변경이 없고 새 실패도 없다(checks.json:395-396) |
| G7 class | PASS | checks.json:91-92. class general, 사유 없음. class_ok=true |
| G8-1 diff가 보고서 1개 | PASS | changed-files.txt:1 |
| G8-2 분류별 파일:행 근거 | FAIL | "가격 증거 부재가 직접 원인"(report:70)은 코드와 다르다. 대시보드는 이 가격 항목을 허용한다(scripts/portfolio_decision_dashboard.py:207-211, 224-226). target-2.err:1946의 issues에서 허용되지 않는 것은 RISK_MAPPING_REQUIRED:BE·LITE뿐이다 |
| G8-3 실패 수 일치 | PASS | target-1.err:116-118, target-2.err:3406-3408. FAIL 머리글 249건, `:2796` 243건을 다시 세어 맞았다 |
| G8-4 코드 수정 흔적 없음 | PASS | diff.patch:5-6. 제안만 있다(report:87-93) |
| G8-5 (a)~(e)·표지 | PASS | report:22, 25, 34, 84, 87. 표지 문자열 검색 결과 0건 |

```json
{"verdict": "FAIL", "class_ok": true, "items": [
{"id": "G1", "result": "FAIL", "evidence": "report:46-47,68-72,92. :2796 외 5건의 원인은 scripts/portfolio_decision_dashboard.py:215-228, 330, 243, 602-606 읽기로 판별된다"},
{"id": "G2", "result": "PASS", "evidence": "changed-files.txt:1, checks.json:17-19"},
{"id": "G3", "result": "PASS", "evidence": "diff.patch:1-6"},
{"id": "G4", "result": "PASS", "evidence": "diff.patch:1-6, report:18,101"},
{"id": "G5", "result": "PASS", "evidence": "report 전체에 토큰·계좌번호·계좌 식별자 없음"},
{"id": "G6", "result": "PASS", "evidence": "checks.json:395-396"},
{"id": "G7", "result": "PASS", "evidence": "checks.json:91-92"},
{"id": "G8-1", "result": "PASS", "evidence": "changed-files.txt:1"},
{"id": "G8-2", "result": "FAIL", "evidence": "report:70과 scripts/portfolio_decision_dashboard.py:207-211,224-226, workspace/outputs/dev-runs/p1-baseline-diag2/attempt-1/target-2.err:1946이 어긋남"},
{"id": "G8-3", "result": "PASS", "evidence": "attempt-1/target-1.err:116-118, attempt-1/target-2.err:3406-3408"},
{"id": "G8-4", "result": "PASS", "evidence": "diff.patch:5-6, report:87-93"},
{"id": "G8-5", "result": "PASS", "evidence": "report:22,25,34,84,87; 표지 문자열 검색 0건"}
], "min_fixes": [
"report:70의 '가격 증거 부재가 직접 원인이다'를 고친다. BLOCKED_CANONICAL_PRICE_REQUIRED는 _manual_local_timing_row_scope가 허용하고(scripts/portfolio_decision_dashboard.py:207-211), MISSING_VERIFIED_CANONICAL_PRICE와 FINALIZED_BAR 계열은 _manual_local_timing_gate가 허용한다(:224-226). target-2.err:1946의 issues에서 허용되지 않는 것은 RISK_MAPPING_REQUIRED:BE·LITE뿐이다. 그래서 _holding_timing_projection이 :330에서 빈 값을 돌려주고 holding_timing_evidence가 붙지 않는다(:1903-1905).",
"report:46-47, 68-69, 71-72의 UNKNOWN을 읽기 근거로 해소하고 표도 고친다. :2441·:2487은 위 경로로 timing_status가 NOT_VERIFIED가 된다(:619). :2511은 행의 값과 기대값이 모두 없어 SWING_TIMING_CONSUMED_INPUT_MISMATCH가 나지 않는다(:749-751). CLI :2636은 :243에서 게이트가 False라 legacy_direction이 성립하지 않고 :602-606에서 DEFERRED가 된다. CLI 경로의 LITE 매핑 부재는 :1504-1506과 workspace/policies 안에 LITE가 없다는 점으로 적는다. 분류는 실상태 BE·LITE에 따른 EXTERNAL_FILE로 하되, 다르게 판단되면 그 근거 파일:행을 적는다.",
"report:92의 기대 효과에서 'Step2 가격 증거 계열, CLI 1건'을 잔여 후보에서 뺀다. 별개 원인으로 남는 것은 fixture 1건뿐이다. report:99의 바뀔 조건과 report:101의 미해결 목록·개수도 맞춘다.",
"report:60의 '어느 쪽이 먼저 걸리는지는 실행하지 않아 확인하지 못했다'를 고친다. 같은 함수에서 :981-983이 :991보다 앞이므로 partial_reasons 검사에서 먼저 False가 된다. 뒷받침 근거로 Step2 경로의 canonical_gate_blockers에 DIRECTION_SCOPE_INPUTS_NOT_VERIFIED가 없다는 점(target-2.err:1946, scripts/portfolio_decision_dashboard.py:1312-1313)을 적는다. 이 경로는 신원을 모의로 쓰므로 검증기가 통과한다는 뜻이고, 신원 경로만 다른 K3 쪽 LITE 추적과 맞는다.",
"report:30, 32의 249 대 246, 286 대 283 '확인 필요'를 해소한다. tools/dev_pipeline/devpipe.py:579가 실패 이름을 집합으로 모으므로 같은 이름표가 합쳐지고, failure_count는 그 이름 수다(:1650, :1877). 두 차이가 모두 3건이라는 점도 적는다.",
"report:26, 30, 73의 checks.json 줄 번호를 고친다. 지금 checks.json은 2회차 산출물이라(:2, :674 utc 06:27:17Z) :660의 06:08:06Z가 없고, 실패 이름 목록 등도 14줄 밀렸다(지금 :401-409, :419-664, :597, :667). checks.json은 회차마다 다시 써지므로 줄 번호 대신 시험 이름과 attempt-1/*.err로 인용한다."
]}
```

VERDICT: FAIL

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/p1-baseline-diag2/ 의 원본 기록입니다.)
