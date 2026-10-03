# p-earn Independent Judge 지시문 — 실적 금지 구간 개정안 (2026-10-03)

- 대상: `docs/claude/p-earn-earnings-blackout-amendment-2026-10-03.md`(수정안). 성격: K3 수정안 심사. 정책·코드는 아직 바뀌지 않았다. Judge는 파일을 고치지 않는다.
- 기준값: HEAD `25ec82bf1c72` 시점 git blob — `alert_policy.json` `0a40505894935dbc05bd2b13fc4214f2cadc18d3`, `portfolio_exposure.py` `87d2920c471bca205aa113334c3728e6f7e631f4`, `test_portfolio_exposure.py` `0b5cbfba49febd913820801622fe35c9868c91c6`.
- 상태: 작성 완료, Judge 미실행.

## 1. 사용자 조작

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree `judge-p-earn` · 이유: K3 Independent Judge(정책 의미 심사), 파일 수정 없음**

1. 새 Windows 터미널에서 `cd "E:\사업\##금동한\코덱스저장소"`를 입력한다.
2. 문서 2개를 커밋한다(worktree는 커밋된 HEAD에서 만들어진다).
   `git add docs/claude/p-earn-earnings-blackout-amendment-2026-10-03.md docs/claude/p-earn-judge-prompt-2026-10-03.md`
   `git commit -m "docs: p-earn earnings blackout amendment and judge prompt"`
3. `claude --worktree judge-p-earn`을 입력한다.
4. 세션 안에서 `/model`로 Opus, `/effort`로 xhigh를 고른다.
5. 아래 한 줄을 붙여 넣는다.
   `docs/claude/p-earn-judge-prompt-2026-10-03.md 2절 상자 안의 지시를 그대로 따르는 p-earn Judge로 일해라. 그 밖의 절은 참고만 한다.`
6. 끝나면 마지막 "p-earn Judge 판정" 블록만 복사해 Cowork에 붙여 넣는다.

- 권한 확인 창: 파일 읽기, `git log/show/diff/rev-parse/grep`, 읽기 전용 `python`은 허용한다. 파일을 쓰거나 고치려는 요청은 거부한다.

## 2. 붙여넣기용 지시문

```text
역할: p-earn Independent Judge (K3, 수정안 심사). 대상은 docs/claude/p-earn-earnings-blackout-amendment-2026-10-03.md 이다. 정책·코드 변경은 아직 없다.
금지: 저장소 파일 수정·생성·삭제·커밋·브랜치 변경, 키움 도구, 주문 도구, .env*·토큰·계좌번호 읽기, 네트워크 조회.
허용: 파일 읽기, git 읽기 명령(log/show/diff/rev-parse/ls-files/grep), 읽기 전용 python(해시, JSON 읽기, 저장소 모듈을 import해 함수만 호출 — 파일 쓰기 없음).
없는 수치·사실은 만들지 않는다(확인 필요 / NOT VERIFIED). 보고는 한국어, 식별자는 영어.

0. 기준 확인 (다르면 차이를 보고하고 멈춘다)
   - HEAD에 수정안과 이 지시문이 있다. HEAD가 25ec82bf1c72의 자손이고, 그 사이 변경이 docs/claude 문서 2개 추가뿐인지 git diff --stat 25ec82bf1c72 HEAD 로 확인한다.
   - git rev-parse HEAD:stock-strategy-system/alert_policy.json = 0a40505894935dbc05bd2b13fc4214f2cadc18d3
   - git rev-parse HEAD:manage-us-stock-strategy/scripts/portfolio_exposure.py = 87d2920c471bca205aa113334c3728e6f7e631f4
   - git rev-parse HEAD:manage-us-stock-strategy/tests/test_portfolio_exposure.py = 0b5cbfba49febd913820801622fe35c9868c91c6

1. 읽을 것
   - 수정안 전체(결론, 1~9절).
   - stock-strategy-system/alert_policy.json: 539줄 주변(holding_timing_rules.new_buy_activation), 790~820줄(portfolio_exposure_policy의 earnings_* 키), policy_version 키들, deployment_gate.
   - manage-us-stock-strategy/scripts/portfolio_exposure.py: exposure_config, earnings_blackout(759~785), increase_blockers(871~892), 리뷰 생성 함수에서 earnings·buy_session·generated_at이 넘어가는 경로.
   - manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py: --earnings 처리(397, 464 부근).
   - manage-us-stock-strategy/tests/test_portfolio_exposure.py 400~450줄.
   - docs/claude/integrated-stock-cards-v1-2026-10-02.md 8절 1·10번, "사용자 결정 (2026-10-02)" 절.
   - docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md R3(30~36줄), 9절(559줄~).
   - manage-us-stock-strategy/references/portfolio-exposure-review.md 26줄, manage-us-stock-strategy/references/development-change-review.md "Fail-open patterns".
   - CLAUDE.md, workspace/policies/event_risk_policy.json, docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md(고정 파일 목록).

2. 직접 확인
   a. 수정안 1절 C1~C9가 사실인가. 특히 earnings_date_unverified, earnings_blackout_single_stocks, treat_as_blackout를 읽는 코드가 scripts에 정말 없는지 git grep으로 확인한다.
   b. 현행 earnings_blackout 구간(index-2 ~ index+1, BEFORE_OPEN은 index, 시각 모름은 AFTER_CLOSE와 같음)을 코드와 기존 테스트로 확인하고, 3절 D2 영문 문구가 이것과 동작상 같은지 판정한다.
   c. 3절 diff가 다른 키·섹션을 건드리지 않는지, 최상위 policy_version·strategy_version·deployment_gate가 그대로인지, portfolio_exposure_policy.policy_version 문자열을 참조하는 코드·테스트·스키마가 없는지 확인한다.
   d. portfolio_exposure.py와 run_portfolio_exposure_review.py가 Kiwoom acceptance 고정 목록이나 deployment_gate 해시 대상에 없는지 확인한다.
   e. 2절 개정 규칙의 각 결정 경로(VERIFIED / NOT_ANNOUNCED / 그 밖)를 Fail-open patterns 5종에 하나씩 대어 본다.

3. 판정 질문 (수정안 8절) — 각각 PASS / FAIL / 조건부 + 근거(파일:줄)
   J1 결정 1 반영: 확인된 미공지만 통과하고 그 밖은 모두 금지인가.
   J2 fail-open: 허용 목록 방식인가, 모르는 상태·형식 결함·오래된 확인·미래 시각이 모두 금지로 가는가, 5절 테스트가 이를 고정하는가.
   J3 D2 문구와 현행 코드 구간의 동작 일치.
   J4 "평가 세션 16:00 ET 이후 확인" 기준의 충분성(공지 뒤 2세션 안 발표 위험을 어떻게 볼지). 근거가 없으면 확인 필요로 둔다.
   J5 범위: 권한(order_authority·quantity_authority·execution_quantity)·다른 매수 게이트·최상위 버전·deployment_gate 무변경, 고정 스크립트 미포함.
   J6 S5 확정안 본문을 두고 개정 메모만 붙이는 방식이 문서 충돌을 남기지 않는가.

4. 출력 (마지막에 이 블록 하나)
p-earn Judge 판정
- 결론: PASS | CONDITIONAL_PASS | FAIL
- 기준 확인: 일치 / 불일치(내용)
- J1~J6: 판정 · 근거 한 줄씩
- 필수 수정(번호): 없으면 "없음"
- 권고(선택):
- 확인 못 한 것:
- 자기 점검: fail-open 5종을 각 결정 경로에 대어 봤다 — 예/아니오(이유)
```

## 3. 다음 단계 (참고)

- PASS 또는 CONDITIONAL_PASS: Cowork가 조건을 수정안에 반영한 뒤 사용자 승인 문구를 받는다(수정안 6절 3단계).
- FAIL: Cowork가 필수 수정을 반영한 수정안을 다시 만들고, 같은 worktree에서 Judge를 다시 돌린다.
