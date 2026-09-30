# S4 신호 검증 Builder 지시문 (2026-10-01)

- 목적: S3 후보 ①(변동성 비중조절)과 보완한 ②(급락 탈출·2단계 재진입), 그리고 둘의 결합을 walk-forward로 검증한다.
- 선행: `loss-limit-review-s3-crash-recovery-signals-2026-09-30.md` §4·§7, `loss-limit-review-s1-decisions-2026-09-30.md`(1차 -10%, 최대 -20%, 레버리지 상한 1.9배).
- 성격: 연구 러너·결과 추가(런타임·정책·상태 무변경). 결과는 D/C 등급 연구이며 활성화 권한이 없다.

## 실행 방법 (Windows 터미널, 사용자 선택 2026-10-01)

1. Windows 터미널(PowerShell)을 연다.
2. `cd "E:\사업\##금동한\코덱스저장소"`
3. `claude --worktree s4-signals` → 작업 폴더 `.claude\worktrees\s4-signals`, 브랜치 `worktree-s4-signals`가 자동 생성된다(브랜치를 따로 만들지 않는다).
4. 세션 안에서 `/model` → Sonnet, `/effort` → high.
5. 아래 text 블록 전체를 붙여 넣는다(여러 줄 붙여넣기 경고가 뜨면 붙여넣기 선택).
6. 원본 폴더 문서 읽기·데이터 다운로드 권한을 물으면 허용한다.
7. 계획 승인 요청에서 멈추면 Cowork에 붙여 넣어 확인받거나 "진행"이라고 답한다.
8. 끝나면 Cowork에 "Builder 완료, worktree s4-signals, 새 실패 수 N"만 전한다.

(대안: Claude 데스크톱 앱 Code 탭에서 새 세션의 worktree 옵션을 켜도 된다.)

**[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: high · 세션: 새 worktree `s4-signals` · 이유: K2 수준 연구 러너 추가(런타임·정책 무변경), 설계는 Cowork S3·S4 문서에서 확정**

```text
역할: S4 신호 검증 Builder(연구 전용, K2 수준 절차). 보고는 한국어, 식별자·명령·파일명은 영어.

읽을 것(읽기만):
- E:\사업\##금동한\코덱스저장소\docs\claude\loss-limit-review-s3-crash-recovery-signals-2026-09-30.md
  (S3 아이디어·간이 재현·규칙 정의·스크립트 부록. 원본 폴더의 미커밋 파일이라 절대경로로 읽는다)
- stock-strategy-system/backtests/SOXL_WALK_FORWARD_PROTOCOL_2026-08-05.md
- stock-strategy-system/backtests/walk_forward_soxl_policy_2026-08-05.py
  (재사용: expected_sessions, fetch_treasury, metrics, fold_ranges, regime_label, acceptance, self_test 구조, Nasdaq+Yahoo 수집·검증 방식)
- stock-strategy-system/alert_policy.json의 holding_timing_rules.risk_overlay_rules.dynamic_gross_leverage_cap.activation_gate

절대 규칙:
- 새 파일만 추가한다. alert_policy.json, portfolio_state.json, workspace/policies/*, 기존 backtests 파일,
  승인 매니페스트에 고정된 스크립트(run_manual_portfolio_analysis.py 등)는 수정하지 않는다. 필요해 보이면 멈추고 묻는다.
- 키움 도구(조회·주문 모두)를 쓰지 않는다. 공개 시장 데이터(Nasdaq, Yahoo, FRED DGS3MO)만 쓴다. .env·토큰·계좌번호를 읽지 않는다.
- 기존 파일의 줄바꿈을 바꾸지 않는다.
- 결과를 본 뒤 파라미터·규칙을 바꾸지 않는다. 추가 탐색은 "post-hoc"으로 표시하고 게이트 판정에서 뺀다.
- 결과는 연구(D/C 등급)다. 정책 반영·활성화는 S5 제안 → S6 Judge → S7 사용자 승인 → forward shadow 뒤라고 보고서에 적는다.
- 커밋은 내 승인 뒤 worktree 브랜치에만. push·merge 금지.

단계:
1. 기준선: git status, 기존 테스트 전체 실패 수를 서브에이전트로 1회 확인(실패만 보고).
   python -m unittest discover -s manage-us-stock-strategy/tests
2. 계획 제시 후 내 승인 대기: 추가할 파일, 재사용할 함수, 데이터 수집 방법.
3. 사전 등록: 아래 "사전 등록 내용"을 stock-strategy-system/backtests/SOXL_SIGNAL_WALK_FORWARD_PROTOCOL_2026-10-01.md로
   옮기고, 결과 계산 전에 sha256을 확정해 결과 JSON에 기록한다.
4. 데이터: SOXX(2010-01-04부터)·SOXL(상장일 2010-03-11부터), 보조 QQQ·TQQQ 일봉, 마지막 완료 세션까지.
   가격 처리·체결 계약은 기존 프로토콜을 따른다(Nasdaq 주 + Yahoo 교차확인 + NYSE 달력 완전성 점검).
   Nasdaq이 오래된 구간을 못 주면 그 구간은 "Yahoo 단일 출처"로 표시하고 계속한다.
   수집 실패나 세션 누락이면 멈추고 보고한다(합성·보간 금지).
   원본 CSV와 출처 JSON(해시, 행 수, 불일치 수)을 stock-strategy-system/backtests/soxl_signal_inputs_2026-10-01/에 저장.
5. 러너: stock-strategy-system/backtests/walk_forward_soxl_signals_2026-10-01.py (--self-test, --run).
   self-test 필수: ① 8개 이상 잘린 이력의 신호 = 전체 이력 신호(미래 정보 없음) ② 종가 t 신호 → t+1 시가 체결
   ③ 비용 계산 ④ 폴드 학습 구간이 시험 시작 전에 끝남 ⑤ 갭은 시가로만 체결 ⑥ 시가 누락·0이면 대기 동작 동결.
6. 실행: 긴 로그는 서브에이전트나 파일로 분리.
   결과: soxl_signal_walk_forward_2026-10-01_results.json, SOXL_SIGNAL_WALK_FORWARD_RESULTS_2026-10-01.md(한국어, 결론 먼저, 게이트 표).
7. 기준선 테스트 재확인(실패 수 변화 없음).
8. docs/claude/s4-builder-report-2026-10-01.md에 추가 파일·게이트 결과·확인 필요를 적고,
   마지막 줄에 "Builder 완료, worktree s4-signals, 새 실패 수 N"을 출력한다.

사전 등록 내용:
[공통]
- 신호: 완료된 정규장 종가 t. 체결: t+1 정규장 시가(갭 포함). 비중은 자산 대비 비율(연구용 소수 비중 허용).
- 비용: 체결 비중당 10bp 기본, 20bp·50bp 스트레스. 현금: DGS3MO 시점 이자 + 0% 민감도. 세금·환율 제외.
- 레버리지 상한 1.9배 → SOXL 최대 비중 cap = 0.633, 나머지 현금. 민감도(보고만): cap 1.55배(0.517).
- 폴드: 기존 프로토콜과 동일(학습 24개월, 시험 6개월, 1차 OOS 2021-08-05~2026-08-04 10폴드, 상태 이어붙임).
  보조 OOS(보고만): 2013-08-05~2021-08-04 같은 방식, 그리고 2026-08-05~마지막 완료 세션.
- 각 변형의 상태 기계는 데이터 시작부터 과거 데이터만으로 연속 실행한다. 폴드 경계에서 선택 변형이 바뀌면
  그 변형의 그 시점 목표 비중으로 다음 시가부터 전환한다(비용 반영).
- 폴드별 선택: 학습 구간에서 B0보다 MDD가 나쁘지 않은 변형 중 CAGR 최고(동률: Calmar, 회전율, 더 단순한 규칙).
  기본값 고정(선택 없음) 결과도 함께 보고한다.
[전략]
- B0 기준선: SOXL 비중 0.633 유지, |현재 비중 − 0.633| ≥ 10%p면 다음 시가에 되돌림.
- B1 참고: SOXX 종가 > SMA200이면 0.633, 아니면 0.
- C1 변동성 비중조절: σ20 = SOXL 일간 수익률 최근 20세션 표준편차(t 포함).
  ref = 데이터 시작부터 t까지 σ20의 확장 중앙값(최소 120개). 목표 비중 = cap × min(1, ref/σ20).
  목표와 현재 비중 차이 ≥ 10%p일 때만 다음 시가에 조정.
  이웃 변형(하나씩): 창 15/30, ref = 최근 756세션 중앙값, 조정 폭 5%p/15%p. 매일 조정은 보고만.
- C2 급락 탈출·2단계 재진입(SOXX 신호, SOXL 매매):
  · 탈출(비중 > 0일 때): SOXX 당일 수익률 ≤ −k × (t−1까지 20세션 SOXX 수익률 표준편차),
    또는 SOXX 종가 ≤ (1−d) × ref_high(최근 20세션 최고 종가, 가장 최근 전체 진입일 이전은 제외). 기본 k=2.5, d=10%.
  · 탈출 후: rally_low = 탈출일 종가, rally_day = 0. 종가 < rally_low면 rally_low 갱신, rally_day = 0,
    1단계였으면 0으로 복귀. 아니면 rally_day가 0이고 종가 > 전일 종가면 1, 이미 1 이상이면 +1.
  · 1단계(0 → 절반): rally_day ≥ 4, SOXX 당일 ≥ +g, 거래량 > 전일 거래량 → 비중 0.5 × cap. 기본 g=2.0%.
    1단계 중 −k 급락일이 나오면 0.
  · 2단계(0 또는 절반 → 전체): SOXX 종가 > SMA50 그리고 EMA10 > EMA20 → 비중 cap, 전체 진입일 = t.
  · 이웃 변형(하나씩): k 2.0/3.0, d 8%/12%, g 1.5%/2.5%, 2단계 조건을 EMA10 > EMA20만으로.
- C3 결합: 목표 비중 = C1 목표 × C2 단계 배수(0, 0.5, 1). 기본값만(조합 탐색 금지). 조정 폭 규칙은 C1과 같음.
- 보조(보고만): 같은 규칙을 QQQ 신호 → TQQQ에 적용.
[게이트: 1차 OOS 이어붙인 결과, B0 대비]
- G1: MDD ≥ 5%p 개선, 회복 기간 ≥ 10% 단축, CAGR ≥ B0의 90%(dynamic_gross_leverage_cap activation_gate와 동일).
  기존 프로토콜 기준 1(CAGR +5%p이면서 MDD 악화 ≤ 3%p)도 함께 표시.
- G2: Calmar ≥ +10%.
- G3: 10폴드 중 7개 이상 같은 방향, 약세/고변동 폴드와 강세 폴드를 각각 1개 이상 포함.
- G4: 20bp 통과, 50bp에서 방향 유지, 이웃 변형이 결론을 뒤집지 않음(고립된 최고점 거부).
- G5: 초과수익의 절반 넘게 한 폴드에서 나오지 않음.
- G6: 독립 관찰 20개 이상(C2·C3: 탈출·재진입 사건, C1: 비중이 cap의 80% 미만으로 내려간 구간을
  95% 이상 복귀 뒤 새로 내려간 경우만 따로 셈). 미달이면 "검토 전용".
[추가 보고(게이트 아님)]
- 최악의 하루, 하루 −10%·−20% 이하 일수, 시작일마다 252세션 안에 시작 대비 −10%·−20% 도달 확률.
- SOXX 고점 대비 −25% 이상 급락 구간별: 하락 구간 손익, 바닥 후 60세션 손익, 첫 탈출 시점 낙폭,
  바닥 후 첫 재진입 시점 상승폭, 하락 구간 안 헛재진입 수.
- SOXX 상위 20개 상승일·하락일 보유 여부, 평균 노출, 회전율, 체결 수.
```

## 진행 기록

### 2026-10-01 1단계 기준선 (Builder 보고)

- worktree-s4-signals, HEAD cf17573, git status clean.
- 전체 테스트 2058개 중 실패 23 + 오류 291 = 314건(1 skipped)을 기준선으로 기록. Builder 추정 원인: worktree에서 고정 해시 불일치(INTEGRITY_FAILURE·Kiwoom acceptance 바인딩, 약 280건), 한글 경로 FileNotFoundError 8건, pypdf 미설치 1건 등.
- 별도 확인 항목(S4와 무관): worktree 체크아웃에서 해시 고정 파일 검사가 대량 실패하는지(줄바꿈 차이 가능성), 원본 폴더에서도 같은지. 이후 Builder 작업의 테스트 기준선 해석에 영향.

### 2026-10-01 2단계 계획 검토 (Cowork) — 조건부 승인

승인: `--collect` 추가(수집과 실행 분리), 기존 스크립트 importlib 읽기 전용 재사용, 체결 엔진 예외(0 진입·0 탈출·폴드 전환은 조정 폭 무관), 시작 규칙, C2 처리 순서, 조기 종료일 거래량 fail-closed, 비용 스트레스 때 선택 스케줄 고정, G3·G5·G6 해석, 보고 범위.

결과 전 수정(사전 등록 부록에 기록):
1. C2 "0 → 전체" 직접 경로 삭제. 전체는 1단계(절반)에서만 올라간다(탈출 직후 1세션 휩쏘 방지). "탈출 후 5세션 내 재진입 횟수" 진단은 유지.
2. C2 1단계 중 탈출 조건: −k 급락일 또는 종가 < rally_low(실패한 FTD). ref_high 낙폭 규칙은 전체 단계에서만.
3. 선택은 계열별: C1-WF, C2-WF. C3는 기본값만. 게이트 판정 행: C1-WF, C2-WF, C1 기본, C2 기본, C3 기본. 통합 선택은 보고만.
4. G4: 이웃 과반이 G1·G2 통과면 유지, 기본값만 통과하고 이웃 과반 실패면 고립된 최고점으로 거부. Calmar 최고라는 사실만으로 거부하지 않음.
5. 보조 OOS 2013-08-05~2021-08-04는 같은 방식(계열별 선택 포함), 보고만. 2026-08-05 이후는 기본값만.
6. 데이터: 특별 휴장 2012-10-29·30, 2018-12-05, 2025-01-09와 1/1 토요일 규칙 반영 후 벤더 세션과 대조. Nasdaq·Yahoo 종가 비교는 분할 기준을 맞춘 뒤 허용오차 적용.
7. 사전 등록 파일 sha256은 원본 바이트와 LF 정규화 두 가지로 기록.

참고: S3 문서 부록 스크립트 누락은 Cowork 저장 오류(첫 저장본이 반영됨)였고 2026-10-01 보완. 같은 오류로 S3 §0-5가 옛 문구였던 것도 SOXL 기준(1.55배)으로 고침.

### 2026-10-01 Builder 완료 — Cowork 검증

- worktree `s4-signals`(브랜치 `worktree-s4-signals`, HEAD cf17573, 커밋 없음): 새 파일만 추가, 기존 파일 수정 0건(git status 확인).
- 해시: 프로토콜 원본 `2e6a2d24…94c40`, LF 정규화 `868f0377…c0792`가 sidecar·결과 JSON과 일치. 러너 `5294d17c…5df169` 일치.
- 재실행: `--self-test` 통과(1초). `--run`을 VM 임시 폴더로 다시 돌린 결과 JSON 차이 0건(생성 시각 제외), daily·trades CSV 동일(줄바꿈 정규화 후).
- 독립 대조(S3 Cowork 엔진, Yahoo, 매일 비중 유지, 현금 이자 0%): 같은 1차 OOS에서 보유 33.7%/−73.6%, 변동성 비중조절 33.9%/−58.1% → Builder의 B0 34.1%/−73.5%, C1 32.2%/−58.1%(이자 0%)와 같은 수준. 1년 내 −20% 도달 확률도 64.2% vs 63.4%(B0)로 일치.
- 게이트: 5개 행 모두 gate_failed. C1 기본이 G1·G2·G3·G5와 20bp·50bp는 통과했으나 G4(이웃 2/5)·G6(관찰 12)에서 탈락. C2 CAGR 7.5%(B0 34.6%), C3 13.7%.
- 결론: 신호 채택 없음(NO_CHANGE). 커밋은 사용자 승인 후 Builder가 worktree 브랜치에, 병합은 사용자가 Windows 터미널에서.

### 2026-10-01 병합 완료 — Cowork 확인

- 병합 커밋 `63c9f20` "merge: S4 signal walk-forward research (worktree-s4-signals a618ad6)", 부모 cf17573·a618ad6, 브랜치 codex/master-recovery-expansion.
- 병합된 22개 파일 내용이 a618ad6과 같음(줄바꿈 제외). 프로토콜 원본 sha256 `2e6a2d24…`·LF `868f0377…` 일치. 남은 staged·unstaged 변경 없음. 정책·상태 파일 해시 변화 없음.
- 경위: 첫 병합 시도(2026-09-30 16:01:51 UTC)는 리눅스 형식 색인 기록(uid 1013)을 남긴 비대화형 환경에서 실행돼 커밋되지 않았고 MERGE_HEAD가 빈 파일로 남았다(이 Cowork 대화에서는 병합을 실행하지 않음, 실행 주체 확인 필요). Windows 터미널에서 `git update-index --refresh` → `git merge --abort` → `git merge --no-ff -m ...`로 정상 병합.
- 교훈: 커밋·병합은 Windows 터미널에서만, 메시지는 `-m`으로 넣어 편집기 대기를 피한다. Cowork의 git은 `--no-optional-locks -c core.autocrlf=true` 읽기 전용만.

