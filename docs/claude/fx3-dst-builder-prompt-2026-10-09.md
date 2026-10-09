---
id: fx3-dst-builder-prompt-2026-10-09
title: FX-1009 fx-3 Builder 지시문 — 서머타임 대비 준비 + 테스트 기준선
date: 2026-10-09
class: K2 (표시 전용 검증 계약, 고정 범위 밖 파일)
plan: docs/claude/fx1009-fix-plan-2026-10-09.md 5-3절 · 부록 A-3
record: docs/claude/fx1009-fx3-record.md
authority: order_authority=false · quantity_authority=none · execution_quantity=null
---

# 사용자가 칠 명령 (PowerShell, 한 줄씩)

```
cd "E:\사업\##금동한\코덱스저장소"
git add docs/claude/fx3-dst-builder-prompt-2026-10-09.md docs/claude/fx1009-fx3-record.md
git commit -m "docs: FX-1009 fx-3 DST preparation record and Builder prompt"
claude --worktree fx-dst
```

Claude Code가 열리면 `/model`로 Sonnet을 고르고 `/effort high`를 입력한 뒤, 아래 "Builder에게 붙여 넣을 지시문" 블록만 붙여 넣는다.

# Builder에게 붙여 넣을 지시문

```text
[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: high · 세션: 새 worktree(fx-dst) · 이유: 대상 파일 1개와 테스트 1개의 K2 변경이고 판단 로직은 없다. Opus 불필요.

FX-1009 fx-3 Builder (K2). 먼저 CLAUDE.md와 docs/claude/fx1009-fx3-record.md, docs/claude/fx1009-fix-plan-2026-10-09.md 5-3절을 읽어라.

배경: manage-us-stock-strategy/scripts/regular_session_close_history.py 의 LABEL_VERIFIED_UTC_OFFSETS = ("-04:00",) 때문에 미국 서머타임이 끝나는 11/2 세션부터 S7 종가가 BAR_LABEL_TIMEZONE_UNVERIFIED_FOR_UTC_OFFSET 로 막힌다. 그런데 키움 30분봉은 2026-04-01 이전을 주지 않아 겨울 표기를 지금 측정할 수 없다(기록 파일 참고). 그래서 이번 Builder는 "-05:00"을 LABEL_VERIFIED_UTC_OFFSETS 에 넣지 않는다. 측정 없이 넣으면 검증 안 된 표기를 검증됨으로 선언하는 fail-open 이다.

0단계 — 테스트 기준선 (A6)
1. test-runner 서브에이전트(Haiku)로 전체 테스트를 돌린다: python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py". 실패·오류의 test id 전체 목록, 총 개수, 실행 시각, git HEAD 해시, Python 버전을 docs/claude/test-baseline-<오늘 날짜>.md 에 적는다. 실패를 고치지 않는다. 이 파일이 이후 모든 Builder의 "새 실패 0" 기준이다.
2. test-runner 출력은 위치 정보일 뿐이다. 파일에 적기 전에 실패 id 개수를 직접 세어 맞춘다.

1단계 — 준비만 (코드 동작은 바꾸지 않는다)
1. 먼저 manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json 에 regular_session_close_history.py 가 없음을 다시 확인한다(10/9 확인: 없음). 있으면 K3 이므로 즉시 중단하고 보고한다.
2. tests/test_regular_session_close_history.py 에 테스트 1개를 더한다: unittest.mock.patch.object 로 rsch.LABEL_VERIFIED_UTC_OFFSETS 를 ("-04:00", "-05:00") 로 바꾼 상태에서 기존 test_early_close_uses_the_bar_before_the_early_close 와 같은 입력(2026-11-27 조기 마감)이 verified=True, unverified_reasons=[] 가 됨을 확인한다. 이 테스트는 "측정 뒤 한 줄만 바꾸면 겨울 세션이 검증됨으로 나온다"는 경로를 미리 증명한다.
3. 기존 test_early_close_uses_the_bar_before_the_early_close 는 그대로 둔다(측정 전에는 겨울 세션이 미확인이어야 한다).
4. scripts/regular_session_close_history.py 는 수정하지 않는다. 주석 한 줄(측정 계획: 2026-11-02 세션 뒤)이 이미 있으니 그대로 둔다.
5. 대상 테스트: python -m unittest discover -s manage-us-stock-strategy/tests -p "test_regular_session_close_history.py" 와 test_portfolio_exposure_fail_closed.py 를 먼저 돌리고, 그다음 전체 테스트가 기준선 대비 새 실패 0 인지 비교한다.

금지: LABEL_VERIFIED_UTC_OFFSETS 에 "-05:00" 추가, 키움 조회·인증·주문 도구, 정책·상태 파일, 고정(pin) 범위 파일 수정, 테스트 약화·삭제, 커밋·푸시(사용자가 한다).

끝에 보고할 것: 변경 파일 목록과 diff 줄 수, 기준선 파일 경로, 대상 테스트 결과, 전체 테스트 새 실패 수, 확인 필요 사항. K2라 별도 Judge는 필요 없다. 사용자가 diff를 확인하고 병합한다.
```

# 11/3 아침 후속 (측정 뒤 한 줄 변경) — 지금 실행하지 않는다

조건: 미국 2026-11-02 세션 종료 뒤(한국 11/3 06:00 이후, 겨울 시간이라 여름보다 1시간 늦다). 순서:

1. 사용자 PowerShell (기존 루틴 ③과 같은 스크립트, SOXX만 우선):
   `workspace/outputs/regular-session-closes/collect_30m.ps1 -Symbol SOXX -Exchange NASDAQ -Newest 20261102 -Oldest 20261102 -Pages 3 -KiwoomProfile 실전계좌`
2. Cowork가 저장된 페이지를 읽고 확인한다(응답을 다시 타이핑하지 않는다): 11/2 정규장 첫 봉이 `20261102093000` 라벨이고 거래량이 그 앞뒤 봉보다 뚜렷이 큰지(4/1 여름 표본 SOXX에서 첫 정규장 봉 라벨이 093000이고 거래량이 약 116만으로 가장 컸다), 마지막 정규장 봉이 `20261102153000` 인지, 시간외 봉 라벨이 160000 이후인지. 맞으면 표기가 미국 동부 현지 시각이다.
3. 맞을 때만 Builder(같은 worktree 또는 새 worktree)에서: LABEL_VERIFIED_UTC_OFFSETS = ("-04:00", "-05:00"), test_early_close_... 의 마지막 두 단언을 verified=True / reasons=[] 로 뒤집고, 0단계 기준선과 비교해 새 실패 0 을 확인한다. 안 맞으면(라벨이 1시간 어긋남 등) "-05:00"을 넣지 않고 사용자에게 보고한다.
4. 11/2 세션 하루는 이 절차가 끝나기 전까지 S7 종가가 "미확인"으로 표시된다(fail-closed, 알려진 한계).
