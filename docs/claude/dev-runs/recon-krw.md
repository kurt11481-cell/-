# dev-run recon-krw — NEEDS_APPROVAL

- 시각(UTC): 2026-10-28T22:35:10Z → 2026-10-28T23:01:57Z
- 기준 커밋(base): `1e43b430765411208baeb9724905cb32b6356d16` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/references/broker-snapshot-reconciliation.md, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_reconcile.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py, JUDGE_CLASS_OK_FALSE)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3416 · 실패 31 → 변경 후 Ran 3423 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `059d7619040ce1ffd8b4972f6d643f150caef90fcd3d89eab86f6a4912173db1`
- Judge 파일 sha256: `bd1a5b89003fd88ace29c0491ef9a83da524b42c6436b7daab8e2d84e417a614`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 recon-krw -ApproveAuthority`

## 바뀐 파일

- `docs/claude/recon-krw-report.md`
- `manage-us-stock-strategy/references/broker-snapshot-reconciliation.md`
- `manage-us-stock-strategy/scripts/auto_core_reconcile.py`
- `manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 목표대로 바뀌었다. 상수 `KRW_RISE_TOLERANCE = Decimal("1000")`를 새로 두었고(auto_core_reconcile.py:101-103), 비교는 "증가분 > 1000일 때만 보류"로 바뀌었다(:848). docstring(:811-812)과 참조 문서(broker-snapshot-reconciliation.md:306-308)도 같은 내용으로 고쳐졌다. 하드코딩이나 남은 TODO는 없다. |
| G2 범위 | PASS | 바뀐 파일 4개가 모두 allowed_paths 안에 있다(changed-files.txt:1-4). 코드 변경은 상수, docstring, 비교 1줄뿐이다(diff.patch:20-46). 테스트 파일에는 새 클래스만 추가됐다(diff.patch:53-115). |
| G3 주문·체결 추정 | PASS | 주문 경로, 키움 주문 도구, 가격으로 체결을 추정하는 코드가 diff에 없다(diff.patch 전체에서 주문·권한 표지를 검색해 0건). |
| G4 정책·상태 쓰기와 fail-closed | PASS | 새로 생긴 쓰기 경로가 없다. 원화 값을 읽을 수 없으면 지금처럼 `...:VALUE`로 보류된다(auto_core_reconcile.py:775-777, 바뀌지 않음). 결과 dict 키와 basis 키도 그대로다(:850-856). |
| G5 비밀·계좌 | PASS | 비밀이나 계좌를 읽고 출력하는 코드가 없다. 테스트 자료는 금액과 날짜뿐이다(test_auto_core_reconcile_outflow.py:596-606). |
| G6 단언·skip·새 동작 테스트 | PASS | 기존 테스트는 바뀌지 않았다(:193-196 그대로, diff에 추가만 있음). 새 동작마다 테스트가 있다(:608-649, 7개). checks.json에서 new_failures는 [], 전체 실패 수(9+22)는 기준선 31과 같고, EXPECTED_FAILURES_INCREASED는 없다(checks.json:4,54-55,96). |
| G7 class | PASS (class_ok=false) | 대조 불변 조건 3의 B2-N 증거 요건을 완화하는 변경이다(:848, 참조 문서 :306-308). 그래서 class_ok=false이고 사장 승인 대상이다. 지시문도 authority로 분류했다(task-prompt.md:5). |
| G8-1 diff 대상과 키 | PASS | diff는 `unverified_outflow`, 상수, docstring, 참조 문서, 새 테스트 클래스뿐이다. 사유 문자열(:849)과 dict·basis 키(:850-856)는 바뀌지 않았다. |
| G8-2 경계 | PASS | 1000 이하는 통과한다(경계 포함, test:621-623). 1001 이상은 같은 사유로 보류된다(:625-632). 감소·무변화는 지금처럼 통과한다(:634-639). 기존 120000 보류도 유지된다(:194, :563). |
| G8-3 다른 조건 | PASS | 창, fallback, 0.05 일치, 한도 검사는 바뀌지 않았고 원화 검사보다 먼저 돈다(auto_core_reconcile.py:825-847). ₩9 증가가 있어도 0.05 불일치, 한도 초과, 창 밖은 보류된다(test:641-649). |
| G8-4 반례 탐색 | PASS | 아래 세 경우를 확인했다. 이 변경을 막을 결함은 없다. |
| G8-5 권한·파일·줄바꿈·실패·보고 | PASS | 주문·권한 줄 변경은 없다. CRLF는 유지됐다: 고친 3개 파일 모두 LF만 있는 줄 0, 스크립트 CR 줄 1446. 새 실패도 0이다(checks.json:96). 보고서에 (a)~(d)와 "표지 없음"이 들어 있다(recon-krw-report.md:36,39-46). |

**G8-4 반례 탐색 상세**

- **한 구간 안에서 나눠 입금:** 비교는 base_before와 base_after 두 시점의 차이다. 그래서 여러 번 나눠 들어와도 합이 1000을 넘으면 보류된다(test:627-629에서 500→1501 보류).
- **구간을 넘겨 쪼개기:** 구간마다 원화 ₩1,000 이하 증가가 다시 허용된다. 다만 이 검사는 B2-N 경로에서만 돈다. 그 경로에 들어가려면 1달러가 넘는 달러 출금(R < -1.00)이 원장과 0.05 안에서 맞아야 한다(:842). 원화는 유입으로 인정되지 않고 HWM도 조정되지 않는다(:813). 허용되는 원화 증가는 구간마다 약 $0.7 이하로, 현금 허용 오차 1.00보다 작다(:67). 남은 위험으로 적어 둔다.
- **환전 유입을 1,000원 이하로 위장:** 출금액(-R)은 1달러를 넘는다. 이 돈이 원화로 바뀌었다면 환율이 1달러당 ₩1,000을 넘는 한 원화가 ₩1,000 넘게 늘어 보류된다. 출금 일부만 환전한 경우 잘못 분류되는 금액은 ₩1,000(약 $0.7) 이하로 1.00 허용 오차 안이다. ₩9가 실제로 어디서 왔는지는 확인 필요다(보고서 (a)에 적혀 있다).

참고(고칠 필요는 없음): 보고서에 적힌 테스트 행 범위 "590~643"은 실제로는 592~649다.

```json
{"verdict": "PASS", "class_ok": false, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_reconcile.py:101-103,811-812,848; manage-us-stock-strategy/references/broker-snapshot-reconciliation.md:306-308"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/recon-krw/changed-files.txt:1-4; diff.patch:20-46,53-115"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/recon-krw/diff.patch (no order/authority marker matches)"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_reconcile.py:775-777,850-856"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py:596-606"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py:193-196,608-649; workspace/outputs/dev-runs/recon-krw/checks.json:4,54-55,96"}, {"id": "G7", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_reconcile.py:848 (B2-N reconciliation invariant relaxed -> class_ok=false); task-prompt.md:5"}, {"id": "G8-1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_reconcile.py:849-856"}, {"id": "G8-2", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py:194,563,621-639"}, {"id": "G8-3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_reconcile.py:825-847; manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py:641-649"}, {"id": "G8-4", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py:627-629; manage-us-stock-strategy/scripts/auto_core_reconcile.py:67,813,842"}, {"id": "G8-5", "result": "PASS", "evidence": "workspace/outputs/dev-runs/recon-krw/checks.json:96; docs/claude/recon-krw-report.md:36,39-46"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-29T02:38:16Z
- 병합 커밋: `f8a1ad099b36957916d513360277e9a80dd27eb9` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-10-29T02:38:12Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/recon-krw/ 의 원본 기록입니다.)
