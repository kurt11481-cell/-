# dev-run t2rc-corefix2 — NEEDS_APPROVAL

- 시각(UTC): 2026-10-15T02:50:10Z → 2026-10-15T03:32:20Z
- 기준 커밋(base): `4ed1b5e116187360e59912a0f33165359a1d0605` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_rules.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_tickets.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_risk1r.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_t2rc_corefix.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3047 · 실패 28 → 변경 후 Ran 3069 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `ad02b5974beea09b586774b803fb6e72edcdced27e417bafc0361b6c8ae400e0`
- Judge 파일 sha256: `d07d921f7593188c23a901dae7cd12aca4a1c46869b0db041e17afbffac9d3e6`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 t2rc-corefix2 -ApproveAuthority`

## 바뀐 파일

- `docs/claude/t2rc-corefix2-report.md`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/scripts/auto_core_rules.py`
- `manage-us-stock-strategy/scripts/auto_core_tickets.py`
- `manage-us-stock-strategy/tests/test_auto_core_risk1r.py`
- `manage-us-stock-strategy/tests/test_auto_core_t2rc_corefix.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 다섯 건 모두 실제 코드로 구현됐다. ① SOXX 기준 + GRID는 RG2만: auto_core_decide.py:1042-1046, auto_core_rules.py:870-876. ② 저가 창: rules.py:883. ③ 새 근거: rules.py:698. ④ 재배치 후보: decide.py:1110-1129, auto_core_tickets.py:696-700. ⑤ 매수 card_defined: rules.py:699-704. TODO나 테스트용 하드코딩은 없다. 참고(병합 차단 아님): auto_core_replay.py:141의 R-B oracle은 아직 옛 읽기 `previous_state != "hit"`를 쓴다. 그래서 전 세션이 unk인 날 R-B가 거짓 누수를 낼 수 있다. 이 차이는 코어가 더 엄격한 안전 방향이다. 파일이 allowed_paths 밖이고, R-B는 t2-rc-preregistration-2026-10-14.md:19에서 이미 "미검증"으로 내려가 있다. 보고서 216행은 "replay가 자동으로 같은 규칙을 탄다"고만 적어 이 차이를 빠뜨렸다. Cowork 후속 작업 대상이다 |
| G2 범위 | PASS | changed-files.txt:1-6의 6개 경로가 모두 task-prompt.md:12 allowed_paths 안에 있다. `_sell_gap_sources` 추출(tickets.py:756-773)은 ④에 쓰는 순수 함수다. blocked 순서는 바뀌지 않았다(GOLDEN 7키 불변) |
| G3 주문·키움·체결 추정 | PASS | diff에 주문 경로, 키움 호출, 가격으로 체결을 추정하는 코드가 없다. AUTHORITY는 그대로다(tickets.py:828). 교체 쌍은 `buy_is_ticket: False`이다(tickets.py:1073) |
| G4 쓰기·fail-closed | PASS | 정책·상태·일지에 쓰는 경로는 새로 생기지 않았다. SOXX가 없으면 BENCHMARK_DATA_MISSING이다(rules.py:779-781). 열린 사건에서 GRID가 없으면 RG2가 unk다(rules.py:873-876, 테스트 t2rc_corefix:116). 사건이 없을 때 GRID가 없어도 막지 않는다. 이것은 규칙 파일 v3.12.5:102 "필요한 GRID"와 독립 계산기 t2rc-oracle.py:1032-1033·1038-1053의 읽기와 같고, 보고서 남은 위험에 적혀 있다 |
| G5 비밀 | PASS | diff 전체에 .env, 토큰, 계좌 식별자를 읽거나 출력하는 곳이 없다 |
| G6 테스트 | PASS | 기존 테스트 변경은 test_auto_core_risk1r.py:43 GOLDEN["sell"] 한 값뿐이다. skip이나 expectedFailure는 없다. 새 테스트 22개(test_auto_core_t2rc_corefix.py:59-338)가 항목마다 2개 이상이다. PWR 업종이 A1 전력이라(test_auto_core_tickets.py:385) 변경 전 코드와 구별된다. checks.json:368-377: 대상 405개 OK, new_failures [], schema PASS |
| G7 class | PASS | 상수(C_ONLY_R_CAP·REGRET_BUDGET·관문 기준값), 정책, 승인 상품, 대조 불변 조건, kill switch, quantity_authority 중 바뀐 것이 없다. 다만 경로 때문에 dev-run class는 authority다(checks.json:310). 병합에는 -ApproveAuthority가 필요하다 |
| G8-1 범위·의미 | PASS | 위 G2와 같다. 바뀐 의미는 다섯 가지뿐이다 |
| G8-2 ① SOXX | PASS | 사건·C0·L0·공백 검사는 s = SOXX를 쓴다(rules.py:790-838). DS1은 :858-859, RG3은 :882-887, RG4는 :888-892에서 SOXX를 쓴다. rg2_series(GRID)는 RG2 벤치마크 다리에만 쓴다(:870-876). decide.py:1042은 SOXX, :1046은 rg2_series를 넘긴다. Judge2 메모 2가 바뀐다는 점은 보고서 48행에 있다 |
| G8-3 ② 저가 창 | PASS | 저가는 `range(e + 1, i + 1)`로 이벤트 다음 세션부터 본다(rules.py:883). `start = max(e, last_ds1)`은 종가 2세션 셈에만 쓴다(:882·886). 테스트 :142·:148 |
| G8-4 ③ 새 근거 | PASS | 전 세션이 none·pending일 때만 새 근거다(rules.py:698). 그룹 상태는 none·pending·unk·hit만 나오므로(:413-420·389-401) 빠지는 경우가 없다. basis_met는 그대로다(tickets.py:140). 매도 회로는 basis_met만 본다(:709). 테스트 :171·:178·:183·:186 |
| G8-5 ④ 재배치 | PASS | 셀 (0,2,3,4)은 ①③④⑤다(decide.py:1111, 라벨 순서 tickets.py:888). 상품 승인·자격·시나리오는 :1124-1126에서 거른다. 순위는 :1127-1128로 그대로다. 그날 매도 회로 종목을 빼고 다음 순위를 쓴다(tickets.py:697-700). regret_table(:308-351)은 그대로다. 테스트 :224·:256·:277·:293 |
| G8-6 ⑤ card_defined | PASS | 매수(+)는 그 그룹의 카드 트리거가 오늘 hit일 때만 card_defined다. 매도(−)는 정의만으로 된다(rules.py:699-704). G3 판정은 tickets.py:124다. 테스트 :320·:324·:328·:333 |
| G8-7 골든·안전·테스트 | PASS | risk1r.py:43은 task-prompt.md:20의 값과 정확히 같다. 나머지 7키(:37-40·44-46)는 바뀌지 않았다. test_auto_core_compare_fix는 손대지 않았다(changed-files.txt). 전체 실패 28건은 기준선 28건과 같다(checks.json:4, new_failures []). 권한 표지·주문 경로·정책/상태 쓰기·키움 호출은 없다 |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "auto_core_decide.py:1042-1046,1110-1129; auto_core_rules.py:698,699-704,870-876,883; auto_core_tickets.py:696-700. Note (not a blocker): auto_core_replay.py:141 R-B oracle still counts previous_state != 'hit' as new, so R-B can report a false leak on a day whose previous session is unk (safe direction, outside allowed_paths, R-B already demoted by t2-rc-preregistration-2026-10-14.md:19); report line 216 omits this - Cowork follow-up"}, {"id": "G2", "result": "PASS", "evidence": "changed-files.txt:1-6 within task-prompt.md:12 allowed_paths; auto_core_tickets.py:756-773 pure extraction for item 4"}, {"id": "G3", "result": "PASS", "evidence": "no order path, Kiwoom call or fill inference in diff.patch; auto_core_tickets.py:828 AUTHORITY unchanged, :1073 buy_is_ticket False"}, {"id": "G4", "result": "PASS", "evidence": "no new write path; auto_core_rules.py:779-781 SOXX missing -> unk; :873-876 GRID missing with an open event -> RG2 unk; GRID not needed without an event (rule file v3.12.5:102, t2rc-oracle.py:1032-1033,1038-1053)"}, {"id": "G5", "result": "PASS", "evidence": "diff.patch: no secret or account identifier read/print"}, {"id": "G6", "result": "PASS", "evidence": "test_auto_core_risk1r.py:43 only existing change; test_auto_core_t2rc_corefix.py:59-338 22 new tests; checks.json:368-377 targets 405 OK, new_failures []"}, {"id": "G7", "result": "PASS", "evidence": "no constant/policy/product/invariant/kill-switch/quantity_authority change; dev-run class authority by path only (checks.json:310)"}, {"id": "G8-1", "result": "PASS", "evidence": "changed-files.txt:1-6; only the five meanings changed"}, {"id": "G8-2", "result": "PASS", "evidence": "auto_core_rules.py:790-838,858-859,882-892 on SOXX; :870-876 rg2_series only in RG2; auto_core_decide.py:1042,1046; report line 48 Judge2 memo 2"}, {"id": "G8-3", "result": "PASS", "evidence": "auto_core_rules.py:883 lows from e+1; :882,886 DS1 restarts only the two-close count; tests t2rc_corefix:142,148"}, {"id": "G8-4", "result": "PASS", "evidence": "auto_core_rules.py:698; auto_core_tickets.py:140 basis_met and :709 sell circuit unchanged; tests t2rc_corefix:171,178,183,186"}, {"id": "G8-5", "result": "PASS", "evidence": "auto_core_decide.py:1111,1123-1128; auto_core_tickets.py:697-700,888; regret_table :308-351 unchanged; tests t2rc_corefix:224,256,277,293"}, {"id": "G8-6", "result": "PASS", "evidence": "auto_core_rules.py:699-704; auto_core_tickets.py:124; tests t2rc_corefix:320,324,328,333"}, {"id": "G8-7", "result": "PASS", "evidence": "test_auto_core_risk1r.py:43 equals task-prompt.md:20; :37-40,44-46 unchanged; compare_fix not in changed-files.txt; checks.json new_failures [] (28 = baseline 28)"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-15T03:34:23Z
- 병합 커밋: `ef3bad1b56391d59a0264b5394387306986efd6e` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-10-15T03:34:20Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/t2rc-corefix2/ 의 원본 기록입니다.)
