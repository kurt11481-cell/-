# dev-run event-ctx3 — READY_TO_MERGE

- 시각(UTC): 2026-10-14T00:15:10Z → 2026-10-14T00:55:33Z
- 기준 커밋(base): `1d98bd0ddf887808091f389c24465ad92cb092d4` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **READY_TO_MERGE** · 재시도: 0
- 테스트: 기준선 Ran 3022 · 실패 28 → 변경 후 Ran 3047 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `cff061e641b0d4baa8b726ba9a6b74aae731b61c05c00fb8cad2a3dbd31a2dbf`
- Judge 파일 sha256: `0b56c85615615da92a5579e1267d163e853e991c56a6dbde6e4cdfb7dd9952b5`
- 사유: 없음
- 다음: `.\tools\dev-merge.ps1 event-ctx3`

## 바뀐 파일

- `docs/claude/event-ctx3-report.md`
- `manage-us-stock-strategy/assets/locales/portfolio-exposure-ko-KR.json`
- `manage-us-stock-strategy/references/decision-journal-cards.md`
- `manage-us-stock-strategy/scripts/event_calendar.py`
- `manage-us-stock-strategy/scripts/score_decision_journal.py`
- `manage-us-stock-strategy/tests/test_event_calendar.py`
- `manage-us-stock-strategy/tests/test_score_ticket_outcomes.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 지시문의 착지·노출·문장·CLI가 모두 구현돼 있음 `scripts/event_calendar.py:115,158,228,316,362,418`. 채점기는 주문표마다 이벤트 노출을 붙이고 요약에 두 수를 셈 `scripts/score_decision_journal.py:513,541-543,577,635-636`. 빈 함수·하드코딩·TODO 없음. 실제 `docs/claude/event-calendar.json`의 행 형식과도 맞음 |
| G2 범위 | PASS | 바뀐 경로 7개가 allowed_paths 7개와 정확히 같음(`changed-files.txt:1-7`). 이와 무관한 부수 변경 없음 |
| G3 주문·체결 추정 | PASS | 새로 추가된 줄에 kiwoom·주문 도구·가격으로 체결을 추정하는 코드 없음(diff.patch 검색 0건). 가상 체결 계산은 이번에 건드리지 않은 기존 `_score_ticket` 그대로 |
| G4 정책·상태 쓰기 / 실패를 상태로 남기기 | PASS | event_calendar.py에 파일을 쓰는 호출 없음. 채점기가 쓰는 곳은 기존 `write_report` 하나(`score_decision_journal.py:750-758`). 일정표가 없거나 깨지면 MISSING/INVALID 상태로 남고(`event_calendar.py:115-155`), 행에는 EVENT_CALENDAR_* 상태와 빈 목록, 문장에는 "확인 필요"가 들어감(`event_calendar.py:282-292,316-321`) |
| G5 비밀·계좌 | PASS | .env·토큰·계좌를 읽는 코드 없음. 읽는 것은 결정 파일, 일정표, 로캘, 세션 일정 로더(기존)뿐 |
| G6 단언·테스트 | PASS | 기존 단언 삭제·약화·skip·expectedFailure 없음. 기존 CLI 테스트에는 임시 `--event-calendar` 인자만 추가(`test_score_ticket_outcomes.py:296`). T1~T8이 모두 있음(`test_event_calendar.py:84-360`, `test_score_ticket_outcomes.py:322,355-441`). checks.json: 새 실패 0, 대상 테스트 19/17/36 OK |
| G7 class | PASS | 주문 단계·예산·상한·정지 스위치·대조 조건 변경 없음. 새 줄에 quantity_authority 등 금지 문자열 0건. `"quantity_authority": "none"`은 원래 있던 줄(diff.patch:161, 변경 없는 줄). checks.json class general, class_reasons [] |
| J-a 범위·보호 파일 | PASS | auto_core*·스키마·정책·일지·결정·일정표·도우미 파일 모두 변경 없음(`changed-files.txt`) |
| J-b 기존 채점 값 불변 | PASS | 일정표 None(=변경 전 경로)을 기준으로, 일정표 있음·없음·깨짐 세 경우 각각 새 키를 뺀 보고서와 새 문구를 뺀 렌더 줄이 모두 같은지 비교함(`test_score_ticket_outcomes.py:380-393`). CLI 경로도 정상/깨짐 두 경우를 비교(`:322`). 이벤트 태그는 채점이 끝난 뒤에 붙음(`score_decision_journal.py:635-636`) |
| J-c 착지·경계 | PASS | 경계가 지시대로임: 체결 전 prev < t ≤ F, 밤새 F < t ≤ F1, 5세션 F < t ≤ F5(`event_calendar.py:266-270`). 앞 세션이 없으면 그날 00:00 ET(`:244-245`). 체결 시각은 core_close_at만 씀(`:176-178`). 확인한 경우: 조기 폐장 11/27(`test_event_calendar.py:128`), 휴장 건너뜀 11/25(`:134`), 서머타임 종료 11/2(`:88,115`) |
| J-d 매수/매도 문장 | PASS | 로캘이 매수 "체결 뒤 떠안음", 매도 "체결 뒤 피함"(`portfolio-exposure-ko-KR.json:62-63`). 문장 전체를 그대로 비교하는 테스트 있음(`test_event_calendar.py:200`) |
| J-e 코어와 분리 | PASS | `_score`는 종료 코드만 돌려줌(`auto_core_decide.py:1111-1114`). 결정 dict에는 실패할 때 `journal.score_warning`만 들어감(`:839-844`). decision_identity_hash는 journal 블록을 뺀 값으로 계산(`:857`). 채점은 일지 기록 뒤에 실행. auto_core*.py에는 event_calendar·journal-scores를 읽는 곳이 없음(검색 0건). 일정표가 깨져도 상태로만 남고 exit 0(`test_score_ticket_outcomes.py:322`) |
| J-h 자기 실적 | PASS | 장 전 실적 = 09:00 ET, 장 후 실적 = core_close_at + 1분(`event_calendar.py:212,215`). 실적 자료가 없으면 null(`:200-204`, `test_event_calendar.py:170`). 차이 1건: timing이 없어도 날짜만으로 답이 하나로 정해질 때는 later/earlier로 둔다(`:216-223`, 보고 4번). 논리상 맞는 세분화이고, 문장에는 표시되지 않음 |
| J-f CLI | PASS | CLI는 파일을 쓰지 않음. 실행 전후 임시 폴더 내용이 같은지 비교함(`test_event_calendar.py:299,335`). 결정 파일 없음과 세션 일정 실패는 상태 + exit 0(`event_calendar.py:383,401`). exit 2는 인자 오류뿐(`:427,433`, 테스트 `:354`) |
| J-g ASCII·실제 자료·키 이름 | PASS | 두 스크립트가 ASCII인지 테스트로 확인(`test_event_calendar.py:360`). 새 테스트는 픽스처·임시 파일만 씀. 새 키 이름에 stop·limit·qty·price 없음(`:299` 검사). 관찰(병합을 막지 않음): 범위 밖 기존 테스트 `test_decision_journal_cards.py:639-644`가 `--event-calendar` 없이 main을 불러, 기본 경로의 실제 일정표를 읽기만 함. 그 테스트의 단언은 이 값과 무관함(보고 8번) |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:115,158,228,316,362,418; manage-us-stock-strategy/scripts/score_decision_journal.py:513,541,577,635"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/event-ctx3/changed-files.txt:1-7"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/event-ctx3/diff.patch (no added kiwoom/order/fill-inference lines)"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:115-155,282-292; manage-us-stock-strategy/scripts/score_decision_journal.py:750-758"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:338-360 (reads decision, calendar, locale, session loader only)"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_event_calendar.py:84-360; manage-us-stock-strategy/tests/test_score_ticket_outcomes.py:296,322,355-441; checks.json new_failures []"}, {"id": "G7", "result": "PASS", "evidence": "checks.json class general, class_reasons []; diff.patch:161 is a context line"}, {"id": "G8-J-a", "result": "PASS", "evidence": "workspace/outputs/dev-runs/event-ctx3/changed-files.txt:1-7"}, {"id": "G8-J-b", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_score_ticket_outcomes.py:380-393,322; manage-us-stock-strategy/scripts/score_decision_journal.py:635-636"}, {"id": "G8-J-c", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:244-270,176-178; manage-us-stock-strategy/tests/test_event_calendar.py:88,115,128,134"}, {"id": "G8-J-d", "result": "PASS", "evidence": "manage-us-stock-strategy/assets/locales/portfolio-exposure-ko-KR.json:62-63; manage-us-stock-strategy/tests/test_event_calendar.py:200"}, {"id": "G8-J-e", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:839-844,857,1111-1114"}, {"id": "G8-J-h", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:200-223; manage-us-stock-strategy/tests/test_event_calendar.py:170,184"}, {"id": "G8-J-f", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:383,401,427,433; manage-us-stock-strategy/tests/test_event_calendar.py:299,335,354"}, {"id": "G8-J-g", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_event_calendar.py:299,360; note: manage-us-stock-strategy/tests/test_decision_journal_cards.py:639-644 (outside allowed_paths) reads the default repo calendar read-only, assertions independent"}], "min_fixes": []}
```

VERDICT: PASS

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/event-ctx3/ 의 원본 기록입니다.)
