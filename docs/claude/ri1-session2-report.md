---
id: ri1-session2-report
task: ri1-session2 (RI-1, ri1-session 재시도)
date: 2026-11-03
builder: Claude Code (Opus 5.5), worktree worktree-ri1-session2
prompt: docs/claude/ri1-session2-builder-prompt.md
---

# ri1-session2 Builder 보고 — 오늘 리서치 기록의 평가 세션 불일치 시 매수 막기

표지 없음.

## (a) 바꾼 줄

- manage-us-stock-strategy/scripts/auto_core_decide.py:600-604 (추가 5줄, `_run` 안, `today_record = research["today"]` 바로 뒤)
  - 오늘 기록 status가 "OK"이고 `today_record["evaluation_session"] != evaluation_session`(522행 `expected_completed_session`)이면
    `today_record`를 새 dict `{**today_record, status "INVALID", reasons ["RESEARCH_RECORD_SESSION_MISMATCH"], facts [], earnings None, integrated_check_run None}`로 바꾼다.
    원본 dict(research["today"])는 고치지 않는다. dropped·evaluation_session·written_at·record_day_kst(와 있으면 damage_only)는 그대로.
  - 이후 같은 지역 변수를 쓰는 곳: research_ok(605), facts(606), research_block(607), inputs.research_record(610-612),
    earnings(691), compare(723). 옛 dict를 따로 잡아 둔 곳 없음.
  - 기록 없음(MISSING)·INVALID 경로는 조건(status == "OK")에 걸리지 않아 그대로.
  - auto_core_inputs.py(load_research·check_record), R-REC1 window의 research["sessions"]·research["damage"], 매도 쪽, 결과 필드 목록: 변경 없음.
    새 사유 문자열은 기존 `RESEARCH_RECORD_NOT_OK:<reason>` 경로(auto_core_tickets.py:821, :229)로 나간다.
- manage-us-stock-strategy/tests/test_auto_core_decide.py
  - :129, :133-134 — `Env.write_research`에 키워드 `session=None` 추가(기본값은 기존과 같은 LAST; 다른 시험 동작 변화 없음).
  - :521-547 — 새 시험 1개.
- docs/claude/ri1-session2-report.md — 이 보고.

줄바꿈: 두 코드 파일 모두 작업 트리 CRLF 유지(git ls-files --eol: i/lf w/crlf, diff에 줄 전체 변경 없음).

## (b) 새 시험

`ResearchRecordBuyGateTests.test_record_of_another_evaluation_session_blocks_buys_only`

- 같은 입력으로 정상 기록(evaluation_session = LAST) 실행 1회, 그리고 오늘 기록의 evaluation_session을 바로 전 세션 DAYS[-2]로 적은 실행 1회
  (작성 시각은 기존 기본값, 두 세션 모두의 유효 범위 안). 불일치 실행의 decide 평가 세션이 LAST임도 단언.
- (가) `decision["inputs"]["research_record"]["status"] == "INVALID"`
- (나) reasons에 `RESEARCH_RECORD_SESSION_MISMATCH`
- (다) SOXL 매수 막힘 사유에 `RESEARCH_RECORD_NOT_OK:RESEARCH_RECORD_SESSION_MISMATCH`(505~516행 방식: blocked 사유, buy_requirements 칸 "no", 매수 티켓 없음)
- (라) 매도 판정이 정상 기록 때와 같음: 매도 티켓 목록, 매도 후보, 매도 막힘 목록, 보유 SOXL의 evidence sell 판정을 묶어 비교
  (정상 실행 쪽 SOXL sell 판정이 None이 아님을 먼저 단언해 빈 값끼리 비교가 되지 않게 함).
- 수정 전 코드에서는 기록이 OK로 남아 (가)가 실패한다(항상 참 단언 아님). 기존 단언·skip 변경 없음.

## (c) 시험 결과 마지막 3줄

명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"`

```
Ran 595 tests in 166.566s

FAILED (failures=1, skipped=1)
```

- 새 시험은 통과.
- 실패 1건: `RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR')` —
  `['CARD_SECTION_CHANGED', 'CARD_NOT_ACCEPTED_IN_WATCHLIST']`. 이 시험은 저장소의 실제 docs/claude/card-evidence-registry.json·watchlist를
  inputs.card_check로만 읽으며 이번 변경 파일(auto_core_decide.py `_run`)을 거치지 않는다. 실제 등록부 자료 상태에서 오는 기존 실패로 보이며,
  새 실패 여부는 파이프라인 기준선 비교로 확정한다.
- skipped 1건은 기존 것(이번에 skip 추가 없음).

## (d) 운영 기록 영향

확인 필요. workspace/outputs/research-records는 이 worktree에 없고(검색 결과 research-record*.json 0건), 본 저장소 경로 읽기는 이 세션에서
권한 거부되어 최근 기록의 evaluation_session과 그날 평가 세션을 대조하지 못했다. 막혔을 날이 있는지는 Judge 또는 Cowork가
workspace/outputs/research-records/<day>/research-record.json의 evaluation_session과 workspace/outputs/auto-core/<day>/decision.json의
evaluation_session을 읽어 대조해야 한다(읽기만). 이 확인 전에는 "막혔을 날 없음"으로 보지 않는다.
