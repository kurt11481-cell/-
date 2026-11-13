---
id: code-review-2026-11-13
type: review
status: current
as_of: 2026-11-13
summary: "11/01 리뷰 이후 바뀐 코드(코드 커밋 19개, 2026-11-01 11:44 ~ 11-11 13:03 KST)와 11/01 열린 발견 재확인. 새 발견 7건(상 2·중 2·하 3), 11/01 발견 닫힘 7·열림 6(R-2 포함 7)."
consumers: "사장실(결정 카드) · 개발 큐 지시문 작성 스레드 · 다음 코드 리뷰(이 문서 4절 '읽지 않은 범위'부터)"
authority: "order_authority=false · quantity_authority=none · 읽기 전용 리뷰. 코드·정책·상태·예약 변경 없음. 고치는 법은 개발 큐 제안으로만 적음"
source_decision: "사장 2026-11-13 14:17 KST 사장실 스레드 직접 입력 '회사 시스템 전체 코드 리뷰 해줘'"
---

# 전체 코드 리뷰 2차 (2026-11-13)

- 저장소 코덱스저장소, 브랜치 codex/master-recovery-expansion. 읽은 시점 HEAD e629c22(2026-11-13 14:30 KST).
- 비교 기준점 6b0a248(2026-11-01 직전 마지막 커밋). 코드 커밋 = docs/claude·workspace 밖을 바꾼 커밋 19개(ec621b5 11/01 11:44 ~ 22769dc 11/11 13:03 KST, 병합 커밋 제외) + docs/claude 아래 새 스크립트.
- 계좌 금액·수량은 적지 않는다.

## 0. 결론

- **가장 급한 것 2건(상).**
  1. **H-1** 관심 종목 하나의 30분봉 수집이 실패하면 그날 자동 코어 전체가 멈춘다. 매도 주문표·노출 E·'반등 때 줄이기' 판정까지 사라진다. 11/11에 실제로 일어났다(PLTR, 보유 아님). 11/11 first-collect 수정은 그 원인만 고쳤고, 한 종목 실패가 전체를 멈추는 구조는 그대로다.
  2. **H-2** 개발 파이프라인의 기준선 감시(baseline-watch)는 Python 판이 바뀌면 직전 기준선을 못 찾고 알림만 남긴다. 11/11 기준선은 Python 3.15.2에서 실패 168건(11/07 3.13에서는 0건)이었는데 감시가 잡지 못했다. 지금 도는 qqq-b-core2(11/13 14:30 KST 시작, 3.15.2)는 그 168건 기준선과 비교하므로, pandas 등이 아직 없다면 알림조차 없이 지나간다.
- **중 2건.** 예약 실행기가 PATH의 Python을 의존성 점검 없이 쓴다(M-1 — 11/10 코어 정지·11/11 검토자 실패·H-2의 공통 뿌리). LLM 기록 대조 검토자의 결과를 읽는 곳이 11/07 1일차 뒤로 멈췄고 실패도 보이지 않는다(M-2, 끊김).
- **하 3건.** commit-docs 보호 검사가 목록 줄 글자 그대로만 본다(L-1). 외부 정보 수집 도구가 며칠 멈추거나 자료가 늦으면 데이터 점검을 열지 않고 넘어갈 수 있다(L-2). 07:45 비교기가 LLM 항목 id의 묶음 이름 때문에 급등을 급락으로 센다(L-3, 11/12 1일 3건).
- **11/01 발견.** 닫힘 7(C-1·C-2·RI-1·P-1·CD-1·③-a·③-b), 열림 6(C-3·C-4·P-2·P-3·P-4·R-1) + R-2(하). 다만 P-1은 H-2로, CD-1은 L-1로 남은 구멍이 있다(3절).
- **이번 리뷰에서 바뀌는 것은 없다.** 고치는 법은 2절의 개발 큐 제안이다. 착수 여부는 사장 결정 카드로 묻는다.

## 1. 새 발견 (심각한 순서)

### H-1 (상, fail-closed 범위 과다) 한 종목 수집 실패 → 그날 매도·노출·줄이기 판정 전부 없음
- 코드: `manage-us-stock-strategy/scripts/auto_core.py` 350~359행이 종목마다 `collector(...)`를 부른다. 하나라도 실패하면 156행 `StepFailure("BAR_COLLECTION_FAILED:<종목>:<코드>")`가 나고, 364~367행이 run 전체를 FAIL로 끝낸다. 362행 노출 계산도 건너뛴다. 종목 하나의 실패를 따로 받는 경로는 없다(run_auto_core.ps1도 재시도 없음).
- 그 결과 decide가 `T1_NOT_OK`로 HOLD한다(`auto_core_decide.py` 437~440행). HOLD 기록에는 노출 E도 새 주문표도 없다.
- 실제 사례(2026-11-11 KST):
  - `workspace/outputs/auto-core/2026-11-11/result.json` status FAIL, reasons `['BAR_COLLECTION_FAILED:PLTR:1']`. 대조(reconcile)만 돌았다.
  - 같은 날 decision.json status HOLD, reasons `['T1_NOT_OK']`, exposure `{}`, tickets `[]`. t2rc-check는 NOT_CHECKED.
  - `workspace/outputs/pre-open/2026-11-11-events.md` 25행 "줄이기 확인 불가(코어가 노출 E를 계산하지 못함)".
  - PLTR은 보유 종목이 아니라 관심 명단 종목이다.
  - 앞뒤 E: 마지막 E는 11/07 1.9464, 11/10은 실행 자체가 없음(M-1), 11/11은 이 결함, 다음 E는 11/12 2.004·11/13 2.013(HARD_CEILING). **줄이기 판정이 가장 필요한 구간에서 이틀 연속 E가 없었다.**
- 왜 결함인가: CLAUDE.md Hard safety "Missing or stale data stays visible and fails closed", R-REC1 줄 "never blocks sells". 보유하지 않은 한 종목의 자료 실패가 보유 종목 매도와 줄이기 알림까지 막는다.
- 11/11 first-collect(22769dc)는 새 종목 첫 수집 시작일만 고쳤다(`FIRST_COLLECTION_LOOKBACK_DAYS = 150`). 키움 서버 오류·조회 제한 같은 다른 이유로 한 종목이 실패하면 같은 일이 다시 난다.
- 바뀔 조건: 다른 예약 작업이 HOLD 날에 줄이기·매도를 대신 판정하는 경로가 있으면 영향이 줄어든다(찾지 못함).

### H-2 (상, fail-open) 기준선 감시가 Python 판이 바뀌면 꺼짐
- 코드: `tools/dev_pipeline/devpipe.py` 1011~1028행 `previous_baseline()`은 `python`이 같은 기준선만 고른다. 없으면 633행이 `BASELINE_PREV_NONE`을 내고, 94행은 이것을 알림으로만 다룬다(멈춤 아님).
- 실제 사례:
  - `workspace/outputs/dev-runs/_baseline/03721d5f…-py3.13.15-b2.json`(11/07): Ran 3585, 실패 0.
  - `…/_baseline/b2e0f08d…-py3.15.2-b2.json`(11/11 09:02 KST): Ran 3497, 실패 168(오류 167 + 실패 1). 같은 이름 .full.err: `No module named 'pandas'` 164, `numpy` 2, `tzdata` 1, `pypdf` 1. 나뉨 = 대시보드 시험 163 · 불러오기 실패 모듈 4(test_build_market_snapshot·test_save_daily_pipeline·test_v2_6_4_kiwoom_adapter·test_v2_6_5_kiwoom_replay_hardening) · 실패 1(test_os_diagnostic_d_uses_harmless_launcher).
  - first-collect(`dev-runs/first-collect/result.json`)은 reasons `['BASELINE_PREV_NONE']`만 남겼다. 권한 경로라 NEEDS_APPROVAL에서 멈췄고, 사장 `-ApproveAuthority` 병합(11/11 13:03 KST)으로 들어갔다. **기준선이 0 → 168로 뛴 사실은 멈춤 사유로 올라오지 않았다.**
- 영향:
  - 기준선에 이미 실패로 들어간 시험은 "새 실패"로 안 잡힌다(devpipe.py 644행 `evaluate_tests`). 대시보드 시험 163건과 모듈 4개가 회귀를 못 잡는다. 11/01 P-1(기준선 감시 없음)이 다른 길로 다시 열린 것이다.
  - 지금 도는 qqq-b-core2(11/13 14:30 KST, base e629c22, 3.15.2)는 b2e0f08d(같은 3.15.2, 168건)와 비교한다. pandas가 아직 없으면 '늘어남 0'으로 알림도 없다.
- 회사PC Python 3.15에 pandas 등이 지금 설치됐는지는 **확인 필요**(이 스레드는 Windows Python을 직접 못 봄). qqq-b-core2 기준선 실패 수가 나오면 바로 알 수 있다.
- 바뀔 조건: qqq-b-core2 기준선 실패가 0~1건이면 '지금 가려진 시험'은 없어지고 감시 구멍(판 변경 때 비교 없음)만 남는다.

### M-1 (중) 예약 실행기가 PATH의 Python을 의존성 점검 없이 씀
- 코드: `run_auto_core.ps1` 40~52행, `run_llm_pilots.ps1` 36~47행 — `.venv`·`venv`가 없으면 `Get-Command python.exe`. 등록 스크립트는 `-PythonPath`를 넘기지 않고, 저장소에 .venv·venv가 없다. 시작 전에 필요한 모듈을 확인하지 않는다.
- 같은 뿌리의 사고 3건:
  - 11/10 자동 코어 06:15·07:45 시작 실패(tzdata). import 단계에서 죽어 `auto-core/2026-11-10` 기록이 아예 없다 — auto_core.py 주석 "the scheduled run must always leave a FAIL record"가 지켜지지 않는 경로다.
  - 11/11 07:30 LLM 검토자 `UNEXPECTED (ModuleNotFoundError)`(`workspace/outputs/llm/iccheck/2026-11-11/failed.md`, runner/2026-11-11.json).
  - H-2의 기준선 168건.
- 기본 Python이 바뀔 때마다 다른 예약 작업이 조용히 깨질 수 있다. 같은 python을 쓰는 예약 작업 목록은 **확인 필요**.

### M-2 (중, 끊긴 연결) LLM 기록 대조 검토자 결과를 읽는 곳이 1일차 뒤로 멈춤
- 설계: `docs/claude/api-pilots-2026-11-06.md` 121~126행 — 결과 `workspace/outputs/llm/iccheck/<날짜>/`, 소비자 = 담당 스레드의 10거래일 손 채점 기록 `docs/claude/llm-iccheck-score.md`. 화면 연결 없음.
- 실제: 채점 기록은 1일차(11/07, 발견 6 중 맞음 1)뿐이다(llm-iccheck-score.md 25~27행, 마지막 커밋 03d1c98 11/07 10:00 KST). 11/12(발견 2)·11/13(발견 4, 그중 high 1) 결과가 채점되지 않았다.
- 실패도 보이지 않는다: 11/10 NO_RECORD, 11/11 UNEXPECTED는 failed.md와 runner/<날짜>.json에만 남는다. 예약 지시문(`docs/claude/scheduled-prompts/*.txt`)과 스크립트 어디도 `outputs/llm`을 읽지 않는다.
- 10거래일 합격 판정(≥70% 표시 연결 제안 / <50% 끔)이 제때 나오지 않으면 하루 약 $0.19(usage.jsonl 11/12·11/13)가 결론 없이 나간다. 밀린 날은 2일이라 지금 메우면 된다.

### L-1 (하, fail-open 잔여) commit-docs 보호 검사가 목록 줄 글자 그대로만 비교
- 코드: `tools/commit-docs.ps1` 69~72행(경로 검사는 `^docs/claude/[^/]`와 `..`만), 93~97행(보호 정규식을 목록 줄 글자에 대고 봄), 162행 `git add -- $changed`·168행 `git commit -- $changed`(git이 경로 규칙으로 펼침).
- 그래서 `docs/claude/./constitution-v1.5.0.md`, `docs/claude/constitution*`, `docs/claude/*.md`, `docs/claude/.` 같은 줄은 보호 정규식(`^docs/claude/constitution-v[^/]*\.md$`)에 안 걸리고 HOLD 없이 커밋된다. 다른 관문도 없다(.githooks는 pre-push뿐).
- 지금 _pending에는 이런 줄이 없다. 과거 사례는 못 찾음. 11/01 CD-1을 닫은 cd-guard(06e559c, 병합 ea93ce8)의 남은 구멍이다.

### L-2 (하) 외부 정보 수집: 며칠 멈추거나 자료가 늦으면 데이터 점검이 열리지 않을 수 있음
- 코드: `/mnt/project-files/info-monitoring/bin/collect.py`(sha256 a19c7273…) 210~213·235~238행에서 발동하면 armed=False로 바꾸고, 480~481행은 발동 '관측일'이 오늘보다 10일 넘게 지났으면 점검을 열지 않는다.
- NFCI(D2) 관측값은 이미 약 7일 늦게 들어온다(11-06 관측이 raw/2026-11-13에 처음 나옴). 그래서 수집이 3~4일만 멈추거나 발표가 늦어도 D2 발동이 '이미 발동' 상태로만 남고 시나리오 점검에 넘어가지 않을 수 있다. 숫자 수집 멈춤 자체는 STALE_STREAK로 보인다.

### L-3 (하, 반복 수동 작업) 07:45 비교기가 묶음 id 때문에 급등을 급락으로 셈
- 코드: `auto_core_compare.py` 184~196행 — LLM 항목 id를 '·'로 나눠 각 조각을 별칭 표의 그룹에 대고, 항목 state를 모든 조각 그룹에 적용한다.
- 11/12 LLM 기록이 급등 항목 id를 "C8+·BE8"(DELL "C8+·DL8", MU "C8+·U8")로 써서 급락 별칭이 crash_alert hit가 되어 B7 3건이 났다. 스레드가 손으로 `redesign-t2-compare-explained.json`에 LLM_ERROR로 적었다.
- 원인은 규칙 문구가 아니라 LLM이다: 규칙 파일 v3.12.13(`integrated-check-prompt-v3.12.13-2026-11-06.txt`) 114·119행은 BE8·DL8·U8을 급락 경보 별칭으로만 둔다.
- 지금까지 1일 3건이라 하로 둔다. 같은 형태가 다시 나오면 연속 일수('켜' 조건 5일, 11/13 decision.json streak 0)를 또 끊는다.

### 참고 (결함 아님, 기록만)
- `auto_core_rules.py` 740~744행 `ev3_parse_reasons`: 느슨한 줄은 '줄 수', 엄격한 쪽은 '날짜 수(중복 제거)'로 센다. 같은 날짜 EV3 줄이 둘이면 매수가 막힌다(안전 쪽 오탐). 지금 R-REC1 문서 EV3 줄은 1개(71행).
- QQQ: `auto_core_tickets.py` 61~62행 APPROVED_BUY·INDEX_ETFS에 QQQ 없음 — qqq-reg-b-proposal-2026-11-12.md 4절이 의도로 밝혔고, 코드 단계 qqq-b-core2가 진행 중. 새 발견 아님.
- 예측 모형 산출(forecast-ledger·layer3)은 회사 전략 점검과 끊겨 있으나, 연결표(forecast-layer3-rule-2026-11-10.md 228행)가 '끊김(승인 묶음과 함께 제안)'으로 이미 드러냈다.

## 2. 개발 큐 제안 (착수는 사장 결정 뒤)

| # | 고칠 것 | 경로·변경 등급 | 바뀌지 않는 것 |
|---|---|---|---|
| 1 | H-1: 보유 종목·기준 지수(SOXX 등 노출 계산에 쓰는 것)가 아닌 종목의 수집 실패는 그 종목만 '자료 없음'으로 두고(그 종목 매수 막힘·알림 1줄) run을 계속한다. 보유·기준 지수 실패는 지금처럼 FAIL | 개발 큐. auto_core.py는 권한 경로라 `-ApproveAuthority` 병합. Judge 확인 항목에 '실패 종목 매수 0건'·'보유 종목 실패는 FAIL 유지' 시험 | 매수 문턱·한도·권한·주문 방식 |
| 2 | H-2: `previous_baseline`이 같은 Python 판을 못 찾으면 가장 가까운 조상 기준선(판 무관)과 비교하고, 10건 이상 늘면 STOP_BASELINE_REGRESSED | tools/** = 파이프라인 보호 경로 → K3 수동 경로 | 기준선 계산 방식 |
| 2-a | H-2 환경: 회사PC Python 3.15에 `manage-us-stock-strategy/requirements*.txt` 설치(또는 .venv 고정) | 코드 변경 아님 — 사장 터미널 한 줄(결정 뒤 정확한 줄 안내) | — |
| 3 | M-1: run_auto_core.ps1·run_llm_pilots.ps1 시작 전에 필요한 모듈 import 점검 → 실패 시 이름 있는 실패 줄 + 기존 알림 경로, 코어는 그날 FAIL 기록을 남김 | 개발 큐(실행기 파일 등급은 파이프라인이 정함) | 실행 시각·권한 |
| 4 | M-2: 채점은 시범 담당 스레드가 이어서 한다(코드 아님). 실패 노출은 사장실 결과 모음이 runner/<날짜>.json의 실패 줄을 읽게 | 예약 작업 변경(사장 직접 입력 승인) | 검토자 출력·표시 전용 성격 |
| 5 | L-1: 목록 줄에 `* ? [ ]`·`/./`·끝의 `/.`가 있으면 STOP, 보호 검사는 `git status --porcelain`이 펼친 실제 파일 이름으로 | tools/** → K3 수동 경로 | 커밋 시각·HOLD 방식 |
| 6 | L-2: 늦게 안 발동도 점검을 열고 '늦게 발견' 표시(10일 제한을 '수집일' 기준으로) | 클라우드 도구 수정(info-monitoring 담당 스레드) | D1·D2 문턱 |
| 7 | L-3: 통합 점검 규칙 파일에 '급등 항목 id에 급락 별칭을 붙이지 않는다' 1줄 | 예약 작업 변경. 다시 나올 때 묶어서 | 코어 판정 |

## 3. 11/01 리뷰 발견 재확인

| id | 11/01 내용 | 지금 | 근거 |
|---|---|---|---|
| C-1 | R-REC1 문서 없음·서식 변경 시 충격 이벤트 조용히 사라짐 | 닫힘 | 6aea772 core-failclose(rules 740~744) + db56303 coreinput2(inputs 234 `CORE_INPUT_MISSING`). 커밋된 편집은 못 막음(00-home 경고 그대로) |
| C-2 | 보유 종목 S7 비중 없으면 0으로 계산 | 닫힘 | auto_core_tickets.py 1138 `CURRENT_WEIGHT_MISSING` |
| C-3 | 거래소 모르면 NASDAQ 가정 | 열림(변화 없음, 하) | auto_core_decide.py 636, auto_core_replay.py 424 |
| C-4 | 일지 기록 뒤 실패 시 같은 세션 반복 FAIL | 열림(변화 없음, 하) | decide 761행 주석 그대로. 푸는 절차 문서 여부 **확인 필요** |
| RI-1 | 리서치 기록 평가 세션 대조 없음 | 닫힘 | 7f4bbad, decide 603 `RESEARCH_RECORD_SESSION_MISMATCH` |
| P-1 | 기준선 실패 늘어도 경보 없음 | 닫힘 → **H-2로 다시 열림**(Python 판 변경 때) | cb5c5d4·4dbb6d8, devpipe.py 1011~1028 |
| P-2 | safety-ci가 작업 브랜치에서 안 돎 | 열림(변화 없음) | .github/workflows/safety-ci.yml 3~6행, 6b0a248 뒤 .github 커밋 없음 |
| P-3·P-4 | 주문 차단 hook·Builder 시험 파일 실행 범위 | 열림(K3 안건, 변화 없음) | 6b0a248 뒤 .claude 커밋 없음. judge-prompt.md 변경은 G9 연결표 1줄뿐 |
| CD-1 | commit-docs가 권한 문서도 커밋 | 닫힘 → 남은 구멍 L-1 | 06e559c(병합 ea93ce8) |
| R-1 | B2-N 예외가 늘며 조건이 넓어짐, 조합 시험 없음 | 열림 | ba99ad5 postapply-d4가 사후 점검 오류를 또 걸러냄(승인된 예외). 조합 시험을 더한 커밋 못 찾음 |
| R-2 | 0.05 USD·1.00 USD 기준 문서 대조 | 열림(하, 변화 없음) | — |
| ③-a | diff txt 기준선 실패 | 닫힘 | ffff60d |
| ③-b | PLTR 등록부 해시 | 닫힘 | 11/05 기준선부터 실패 0(11/07 03721d5f…json 0건), 11/11 실패 목록에도 PLTR 없음 |

## 4. 읽은 범위 · 읽지 않은 범위
- 읽음(diff 전부): auto_core.py · auto_core_decide.py · auto_core_inputs.py · auto_core_rules.py · auto_core_tickets.py · regular_session_close_history.py · reconcile_broker_state.py · alert_policy.json·auto_core.json·instrument_registry.json 변경 · commit-docs.ps1(1~180) · devpipe.py 기준선 비교부(615~660·1011~1035) · llm_runner.py 전체 · llm_pilot_iccheck.py 60~300 · run_*.ps1 Python 선택부 · collect.py 신호부(186~520) · auto_core_compare.py 160~230.
- 실제 산출 확인: auto-core 11/10~11/13, pre-open 11/05~11/12, llm/runner·iccheck 11/07~11/13, dev-runs 기준선 2개·first-collect 결과.
- 읽지 않음(다음 리뷰 몫): 예측 모형 스크립트 fm1·fm2·fm3_*(약 3,800행, 자체 review2·review3 있음), strategy1101·s44 리플레이(일회성 연구), llm_pilot_common.py 본문, devpipe.py 기준선 외 변경, 시험 파일, 통합 점검 지시문 v3.12.13·v3.12.14 본문(114·119행만 봄).

## 5. 재검토 기록
- 독립 재검토 1회(일반 하위 에이전트, 읽기 전용, 회사PC 원문 대조). 반영 8건:
  - H-1 E 날짜(앞뒤 → 11/07 뒤 이틀 공백)
  - H-2 'NEEDS_APPROVAL에서 멈췄으나 기준선 사유 없음'으로 정정, 진행 중인 qqq-b-core2 추가
  - M-1 '11/10 FAIL 기록 없음' 추가
  - M-3 → L-3 하향(11/03·11/13 항목은 다른 원인, 규칙 문구는 원인 아님)
  - L-1 행 번호·커밋 정정, `docs/claude/.` 추가
  - L-2 발동 조건 정정(관측일 기준, NFCI 7일 지연)
  - 머리말 커밋 범위(ec621b5부터 19개)·HEAD 정정
  - 3절 행 번호 정정
- 재검토 뒤 바뀐 결론: M-3 등급(중 → 하). 바뀐 부분만 이 스레드가 원문으로 다시 확인함(first-collect result.json, 규칙 파일 114·119행, explained.json 11/03 항목, ec621b5).

검토 완결: 원문 확인 26/27 · 내장 재검토 1회(반영 8건) · 미해결 2(H-2 현재 설치 상태, C-4 절차 문서 — 확인 필요) · 자료 시점 2026-11-13 14:40 KST · 바뀔 조건 각 발견의 '바뀔 조건' 줄, 그리고 qqq-b-core2 기준선 실패 수

## 6. 사장 결정 기록
- 2026-11-13 14:40:53 KST, 사장 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9PCF1dsnNAnGfBH91YwoK3p("코드 리뷰에서 나온 고칠 것을 어디까지 착수할까요?"), 고른 항목 '급한 2건 + 실행기 점검 착수'(option A), 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH(프로젝트 소유자), 사장실 회사PC 스레드 '회사 시스템 전체 코드 리뷰 (11/13)'.
- 범위: 2절 #1(H-1)·#3(M-1) 개발 큐, #2(H-2) K3 수동 경로, #2-a Python 3.15 패키지 설치(사장 터미널 한 줄 — 14:4x KST 안내). M-2·L-1·L-2·L-3은 기록만.
- 순서: qqq-b-core2(진행 중, docs/claude 밖 변경)가 병합된 뒤 #1+#3을 큐에 올린다(동시에 올리면 나중 병합이 STOP_BASE_MOVED). #2는 권한 변경 동시 1건 상한 때문에 그다음. #2는 K3라 이 카드는 착수 방향만이고, 실행 당일 수정안 id를 단 카드를 다시 받는다(CLAUDE.md Change classes: 카드가 수정안 id를 담아야 함).
- 병합은 각자 사장 `-ApproveAuthority`·PowerShell 한 줄. 이 카드는 병합 승인이 아니다.
