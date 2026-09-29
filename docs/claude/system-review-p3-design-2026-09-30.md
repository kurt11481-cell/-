# 투자_V2 재검토 P3: B안(루프 완결 우선) 대안 설계 (2026-09-30)

- 선행 문서: `docs/claude/system-review-phase1-2026-09-30.md`(§7-3 사용자 결정)
- 범위: P3 대안 설계. 목표 구조, 진행 순서안 비교, I0 상세 설계, I1·I2·I7 설계, I4와 K3 6~9단계 대체안, 변경별 K 등급.
- 방법:
  - 읽기 전용으로 진행했다. 코드·정책·포트폴리오 파일은 수정하지 않았고, 키움 도구는 호출하지 않았다.
  - 서브에이전트 3개가 I0 조정 경로, I1·I2·I7 부품, acceptance 고정 범위를 코드 기준으로 조사했다(파일:행 근거).
  - 핵심 파일(`kiwoom_broker_shadow.py`, `apply_user_confirmed_broker_snapshot.py`, `run_kiwoom_broker_shadow.py`)과 반론 검토의 주요 지적은 직접 확인했다.
  - 초안을 별도 서브에이전트가 반론 검토했고, 결과를 반영했다(§13).
- 권장 설정: Opus · xhigh (여러 파일 설계와 K3 판정).
- 표기: "확인 필요"는 확인하지 못한 항목, "(제안)"은 사용자 승인 전 설계안.

---

## 0. 결론

1. **루프는 한 지점이 아니라 연쇄로 끊겨 있었다.**
   - 조정 도구가 없어 상태 파일이 브로커와 계속 달랐다(D1).
   - 기존 판단 렌더러는 두 조건 때문에 한 번도 성공하지 못했다. `broker_diff_status=MATCH`(`render_beginner_portfolio_report.py:373`)와 브로커 조회 6개 모두 PASS(`:371`, `:375`)다. 두 번째 조건은 미체결 조회가 매번 실패해서 I0만으로는 풀리지 않는다.
   - 대시보드는 승인된 decision plan이 필요한데, plan은 "판단 내용을 지어낼 수 없다"는 이유로 만들어지지 않았다(`workspace/outputs/portfolio-decision-plan-candidates/2026-09-02/…audit.md`: `CANDIDATE_BLOCKED`, `Candidate JSON: NONE`).
   - 수동 분석은 애초에 판단을 하지 않는 preflight였다. `full_holding_analysis_performed`는 코드와 스키마에 `false`로 고정돼 있다(§1).

   따라서 I0(조정)는 판단 입력을 최신으로 만드는 전제다. I1은 기존 렌더러에 기대지 않고, **"판단을 누가 쓰는가"를 루프 안의 명시적 단계로** 넣는다.
2. **권장 진행 순서는 B1이다(§3).** I0를 단독 K3로 먼저 만들고, 코드 없이 하는 카드 파일럿을 병행한다. 그다음 I7/H1 → I1 코드화와 I2 → I4 묶음 K3 순서다.
   - phase1 §7-2에는 "I0와 I4를 함께 설계해 Judge를 한 번에"라고 적었다. 이번 조사에서 새로 확인된 사실 때문에 분리를 권한다.
     - I0가 건드리는 파일은 acceptance 고정 대상이 아니다.
     - acceptance는 런타임 게이트가 아니다.
     - acceptance는 이미 무효 상태다.
   - 분리하면 첫 가치(최신 상태)가 빨리 오고 Judge 범위도 작아진다. 대가는 Judge 2회다.
3. **I0는 "Windows에서 제안 명령 1개 → Cowork 채팅에서 확인"이다(사용자 결정).**
   - 흐름: 키움 조회 전용 Python으로 새 스냅샷을 받아 제안을 만든다(쓰기 없음) → Cowork에서 Claude가 차이 표와 "적용 후 알림 엔진 검사" 결과를 보여 준다 → 사용자가 채팅으로 "확인 <코드>"를 보낸다 → Claude가 적용 명령을 실행해 백업, 원자적 쓰기, 누적 원장 기록을 한다.
   - 새로 만들기보다 재사용한다. 조회·정규화·제안은 이미 있는 `run_kiwoom_broker_shadow.py`(52줄, 8/14 선례 파일을 만든 스크립트)를 쓰고, 확인·적용 부분만 새로 만든다.
   - stage, timing_plan, 체결 기록은 쓰지 않는다.
   - 사용자 확인 없는 적용을 여러 겹으로 막는다: 라이브러리 안의 검사, 제안별 확인 코드, 에이전트 규칙(Cowork 채팅 확인 외 실행 금지), Claude Code 권한 거부 규칙.
4. **I1은 사용자 피드백을 설계 기준으로 삼는다.** 피드백은 "가시성이 낮고, 지나치게 보수적이고 일반적"이었다.
   - 데이터 게이트와 판단을 분리한다. 데이터가 부족한 칸은 "확인 필요"로 표시하되, 판단(ADD/HOLD/TRIM/EXIT, 확신도, 현금 대비)은 항상 낸다.
   - 다만 결정론 규칙이 우선한다. 규칙 결과를 카드에 먼저 싣고, 그와 반대되는 판단은 이유가 붙은 "규칙과 다름" 라벨 없이는 통과시키지 않는다.
   - 코드부터 만들지 않는다. 먼저 카드를 한 번 손으로 만들어 사용자가 평가한다.
5. **I2는 "카드 = 분석 기록"으로 단순화하고, 기존 sidecar를 확장한다.** sidecar에는 해시 체인 원장, horizon 인자, TRIM·EXIT·KEEP_CASH 행동이 이미 있다. 빠진 것은 운영 CLI, 60세션, 벤치마크·현금 비교다. 원장은 Claude의 분석 판단과 사용자의 실제 결정을 따로 기록한다.
6. **I4: 보류 중인 K3 6~9단계는 R6~R9로 대체한다(§8).**
   - 고정 범위를 권한, 데이터 정확성, 상태 쓰기로 좁힌다.
   - `run_manual_portfolio_analysis.py` 안의 보호 기능(가격 부호·시간 규칙, 브로커 비교, 예약 입력 검증, 분석→쓰기 금지 테스트)은 먼저 고정 모듈로 분리한다. 그 뒤 `run_manual` 파일과 acceptance 도구의 고정을 풀고, "깨끗한 커밋 + 커밋 ID + 대상 테스트"로 검증한다.
   - 교착의 직접 원인인 materialize 선행조건("현재 active가 유효해야 함")을 "허용된 드리프트 목록"으로 바꾼다.
7. **새로 찾은 데이터 정확성 구멍 3개**
   - `return_code` 필드가 없어도 성공으로 처리한다(`kiwoom_runtime_bridge.py:137-138`). 계좌 bridge도 이 함수를 가져다 쓴다(`kiwoom_account_readonly_bridge.py:17, 99`).
   - 계좌 수치 변환 `_number`는 음수나 부호를 막지 않는다(`kiwoom_broker_shadow.py:19-25`).
   - `normalize_snapshot`이 예외를 내면 수동 분석이 보유 목록을 빈 값으로 두면서 상태는 `AVAILABLE`로 표시할 수 있다(`run_manual:306-330`).

   I0는 고정되지 않은 계좌 bridge에서 `return_code` 검사를 엄격하게 바꾸고, 음수·부호 검사는 I0 전용 함수로 한다. 공유 함수 `normalize_snapshot`의 계약은 바꾸지 않는다. 세 번째 결함은 `run_manual`이 고정 파일이라 R6에서 고친다.
8. **사용자 결정 4개를 받았다(§10):** B1, Cowork 채팅 확인, 카드는 Cowork에서 작성, 채점 기준은 현금 + SPY.

---

## 1. 이번에 확정된 사실 (P2 보완·정정)

### 1-1. 사용자 확인 (2026-09-30)

- **키움 MCP 주문 gate:** Claude 데스크톱 설정에서 0(비활성)이다. phase1 §5-3이 해소됐다. 도구 목록에는 주문 도구 2개가 계속 보이지만 gate가 막는다.
- **수동 분석 결과 활용:** 실제 매매 판단에 쓰지 않았다. 이유는 "가시성이 떨어지고, 지나치게 보수적이고 일반적인 리뷰"였다.
- **조정 확인 방식:** 분석 때마다 한 번 확인한다.

### 1-2. P2 정정: D2 "전체 보유 분석 0/20"은 실패가 아니라 설계였다

- `run_manual_portfolio_analysis.py:467`은 리터럴 `False`를 쓴다. 스키마도 `{"const": false}`다(`schemas/manual-portfolio-analysis.schema.json:320,332`). 모듈 docstring(:2-6)은 "holding-strategy capability 없음"이라고 적고 있다.
- 실제 공백은 **운영 경로에서 판단을 만드는 부품이 한 번도 돌지 않은 것**이다.
  - renderer: MATCH, 브로커 조회 전부 PASS, 장부 수량 일치, run_manifest 바인딩, 같은 세션 overlay를 요구한다(:220, :262, :371-375, :397). 출력 폴더 `phase-a-review`가 없다.
  - dashboard: 승인된 plan이 필요하다(:1421). 출력 폴더가 없고, plan 후보는 `CANDIDATE_BLOCKED`였다.
  - md 리뷰 2건(09-09, 09-10): 만든 스크립트가 없다. 수기나 에이전트가 쓴 것으로 보인다(확인 필요). 09-10의 Decision Support 표는 분류가 전부 `NOT_VERIFIED`였다.
- 보유 종목 baseline은 2026-08-14에 SHADOW로 만들어졌다(약 47일 전). 세 종목 모두 `research_recommendation=REASSESS`, `risk_controller_result=DOWNGRADE`다. 종목별 A~D 증거 등급과 미래 이벤트 날짜는 없다.

### 1-3. 불일치와 데이터 경로

- **불일치 내용:** DIFFERENT 16회 모두 `HOLDINGS_DIFFER`와 `AVAILABLE_CASH_DIFFERS`였다.
  - 수량이 다른 종목은 매번 NBIS 하나였고, 평단은 일치했다.
  - 상태 파일은 전 기간 revision 14, 같은 해시였다.
- **미체결 조회**(`account_open_items`)는 매번 `KIWOOM_API_RESPONSE_ERROR`였다. 그래서 `scope_complete`는 항상 false였다(6개 조회가 모두 PASS여야 true, `kiwoom_broker_shadow.py:67-68`).
- **키움 데이터 경로는 결정론적 Python이다. LLM이 옮겨 적는 방식이 아니다.**
  - 호출 순서: `run_manual` main → `kiwoom_account_readonly_bridge.invoke_account_bridge_batch` → 런타임 venv subprocess → REST(`kiwoom_runtime_bridge.py:340-363`).
  - MCP는 이 경로에 없다.
- **정규화 스냅샷이 저장되지 않는다.** 수동 분석은 `snapshot_hash`, 신선도, `retrieved_at`, `runtime_commit`을 버리고 합산 `as_of`만 남긴다(`run_manual:295-360`).
- **선례(8/14):** 키움 데이터로 CASH_ONLY 적용을 한 번 했다(`workspace/outputs/activation/kiwoom-broker-shadow/20260814-234459-master-revalidation/`).
  - 그 proposal을 만든 스크립트는 저장소에 없다.
  - 결과적으로 현재 상태는 `scope=CASH_ONLY`인데 `holdings_complete=true`다.
  - 적용 함수가 `last_updated_at`을 바꾸지 않아 이 값은 8/12에 머물러 있다.
  - 8/14 적용은 확인 파일(`cash-only-user-confirmation.json`)을 넘겨 라이브러리를 직접 호출하는 방식이었다. 제안의 `unresolved_fields`가 3개(`INCOMPLETE_ACCOUNT_SCOPE`, `OPEN_ORDERS_VISIBILITY_UNKNOWN`, `REALIZED_PNL_VISIBILITY_UNAVAILABLE`) 남은 상태였는데도 적용됐다.
- **상태 파일에는 스키마 검증이 없다.** 쓰는 코드는 `apply_user_confirmed_broker_snapshot.py:85` 하나다. 이 파일에는 CLI가 없다.
- **이미 있는 조회→제안 스크립트:** `run_kiwoom_broker_shadow.py`(52줄)가 조회, 정규화, 제안, 상태 불변 검사, 스키마 검증을 하고 스냅샷과 제안 파일을 쓴다. 8/14 폴더의 `kiwoom_broker_snapshot.shadow.json`과 `reconciliation_proposal.json`이 이 스크립트의 출력이다.
- **알림 엔진은 leveraged 모드다**(`evaluate_alerts.py:1066`).
  - 양수 보유 종목은 정책 `positions`(SOXL·MVLL·NBIS)나 de-minimis 예외와 정확히 맞아야 한다(`:499-516`).
  - SOXL·MVLL 수량은 "기준 수량 − 확정된 tranche"와 같아야 한다(`timing_engine.py:101-106`).
  - 따라서 체결 기록 없이 SOXL·MVLL 수량이 바뀌거나, 전량 매도나 신규 종목이 생기면 알림 엔진이 `STATE_MISMATCH`로 멈춘다.
- **git 제외 설정:** `stock-strategy-system/`에서는 `portfolio_state.json` 등 일부 파일만 제외된다(`.gitignore:27-37`). 새로 만들 백업·원장 경로와 `workspace/outputs/`의 새 폴더(holding-cards, status, reconciliation)는 제외 대상이 아니다(`git check-ignore`로 확인).

### 1-4. acceptance와 재현성

- **acceptance `f0bab…`는 이미 무효다.**
  - 고정된 `run_manual` 해시 `e1e933c2…`는 `7fa30b0` 판이고, 현재 해시는 `baec1640…`이다(`a5e872a` 이후).
  - 테스트 파일 해시도 다르다.
- **런타임 게이트가 아니다.** 검증기는 테스트와 후보 도구에서만 호출된다. 런타임 모듈에서 "acceptance"를 grep하면 docstring 1줄 외에는 0건이다.
- **CI 17건 실패**(materialize 15, v2_6_7 2)가 이 교착과 연결돼 있다(`docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md`).
- **201/343 바이트 불일치는 전부 줄바꿈 차이다.** 작업본은 CRLF, blob은 LF이고, BOM이나 내용 차이는 0건이다.
  - 작업본에는 LF와 CRLF가 섞여 있어, 어떤 체크아웃 방식으로도 두 그룹을 동시에 재현할 수 없다.
  - `.gitattributes`는 없다.

---

## 2. 목표 구조 (B안)

```
[키움 조회 전용 Python]
   ├─► ① 수동 분석 (기존, 변경 없음) ─► 분석 JSON: 데이터·불일치 감지
   └─► ② 조정 제안 (신규, I0, Windows) ─► Cowork 채팅: 차이 표 ─► 사용자 "확인 <코드>"
                                          ─► 적용 명령 ─► portfolio_state.json (유일한 상태 쓰기 경로)
③ 카드 작성 (I1) ◄── 분석 JSON + 상태 + baseline + 공식 이벤트
   ├─ fact pack(결정론) + 판단(Claude) ─► 카드 검증기 ─► 카드 md, 현황판 요약(H2)
   └─► ④ 결정 원장 (I2, append-only) ─► 채점기 5/20/60세션 ─► 다음 카드 "지난 판단 성과"
⑤ 상태 점검 (I7, 읽기 전용) ─► 현황판 알림 창(H1): 상태 나이·불일치·조정 대기
```

- **Hot Path:** ①②③. 짧게 유지하고 실패하면 멈춘다(fail-closed).
- **Cold Path:** ④ 채점기와 ⑤ 표시. 실패해도 ①②③을 막지 않고, 다음 카드에 "채점 대기·실패"로 표시한다.

| 경계 | 규칙 | 강제 방법 |
|---|---|---|
| 분석 → 쓰기 금지 | 수동 분석은 적용 모듈을 import하지 않는다 | 기존 `test_08_forbidden_high_level_entrypoints…` 유지 |
| 상태 쓰기 주체 | 사람의 명시적 확인. Cowork 대화에서 사용자가 해당 제안의 "확인 <코드>"를 직접 보냈을 때만 Claude가 적용 명령을 실행한다 | 네 겹으로 막는다. ① 라이브러리 안의 검사(unresolved·만료·해시): 직접 호출해도 우회되지 않는다 ② 적용 명령의 `--confirm <코드>` 일치 검사와 확인 기록(`method=COWORK_CHAT_USER_MESSAGE`, 확인 시각, 사용자 메시지) ③ 에이전트 규칙(`CLAUDE.md`, `AGENTS.md`): Cowork에서 사용자 확인 메시지가 있을 때만 실행한다. Claude가 코드를 스스로 넣거나 이전 확인을 재사용하지 않는다. 예약 작업, Claude Code, Codex, Judge 세션에서는 실행하지 않는다 ④ Claude Code 권한 거부 규칙: 적용 명령 실행과 상태 파일 직접 편집. ②~④는 규칙과 기록으로 막는 장치다. 사용자가 터미널에 코드를 직접 치는 방식보다 보증 수준이 낮고, 사용자는 편의를 위해 이 절충을 선택했다 |
| 주문 | 없음 | 조회 전용 bridge, `order_authority=false`, 키움 MCP 주문 gate 0(사용자 확인) |
| 판단 → 수량 금지 | 카드에 주문 수량과 주문 의도가 없다 | 카드 스키마에 수량 필드를 두지 않는다. dashboard의 order intent(`proposed_quantity` 정수 ≥1 허용)는 카드 경로에서 쓰지 않는다 |
| 현황판 | 표시 전용이다 | 현황판 db를 상태 입력으로 읽는 코드를 만들지 않는다(현행 유지) |

---

## 3. 진행 순서안 비교

| 기준 | **B1. I0 단독 K3 먼저 + 카드 파일럿 병행 (권장)** | B2. I0+I4 묶음 K3 (phase1 서술) | B3. 표시·파일럿 먼저, I0 나중 |
|---|---|---|---|
| 상태 최신화까지 | 가장 빠름. I0 빌드와 Judge만 필요 | 느림. 규칙 모듈 분리, 새 manifest, 정책 교체까지 끝나야 함 | 가장 느림 |
| 쓸 만한 카드까지 | 빠름. 파일럿을 Cowork에서 병행 | 느림 | 가장 빠름. 단, "상태 미조정" 라벨이 붙음 |
| Judge 횟수 | 2회(I0, I4) | 1회(범위 큼) | 2회 |
| 고정 파일 수정 | I0는 없음. 계좌 bridge는 고정 대상이 아니고, 고정된 `kiwoom_runtime_bridge`는 import만 한다(R8에서 I0 테스트 재실행) | 있음(`run_manual` 등) | I0는 없음 |
| 실패 시 영향 | 작음. 쓰기 경로 하나에 집중 | 큼. 한 번에 많이 바뀌어 전부 지연 | 오래된 상태로 판단이 이어짐 |
| CI 17건 실패 | I4까지 남음(알려진 실패로 표시) | 빨리 해소 | I4까지 남음 |

- B1 순서:
  1. I0 빌드(Claude Code 새 worktree)와 I1 파일럿(Cowork, 코드 없음)을 병행한다.
  2. I0 Judge → 사용자 승인 → 첫 실제 조정을 한다.
  3. I7/H1을 만든다(작고 위험이 낮음).
  4. I1 코드화와 I2를 진행한다(파일럿 결과 반영).
  5. I4 묶음 K3(R6~R9)를 진행한다.
- I4 전까지는 `run_manual`과 고정 파일을 수정하지 않는다. I1·I2·I7은 고정 파일 밖에 만든다.

---

## 4. I0 조정 루프 상세 (K3-a)

### 4-1. 사용자 흐름 (분석 때마다 한 번)

1. 지금처럼 수동 분석을 실행한다.
2. 같은 Windows 터미널에서 조정 제안 명령을 실행한다(가칭 `reconcile_broker_state.py propose`, 조회 전용, 상태 쓰기 없음).
   - 키움 런타임이 Windows에 있으므로 이 단계는 Cowork에서 대신 실행할 수 없다.
   - 분석과 제안을 한 명령으로 묶을지는 P4에서 정한다.
3. 결과는 둘 중 하나다.
   - 일치하면 "브로커와 상태 일치. 조정 필요 없음"을 출력하고 끝난다.
   - 다르면 제안 파일을 만들고 "Cowork에서 확인하세요"를 출력한다.
4. Cowork에서 "조정 확인해줘"라고 하면, Claude가 최신 제안 파일을 읽어 아래 표를 채팅에 보여 준다.

```
[조정 제안] 키움 조회 2026-10-01 06:31:04 KST (유효 15분, 06:46까지)
상태 파일: revision 14, 마지막 갱신 2026-08-12 (49일 전)

항목                상태 파일(현재)   브로커(키움)    적용 후
NBIS 수량           a주               b주             b주
NBIS 원가 합계      (현재 값)         -               b × 평단 (파생, 센트 반올림)
가용 현금(USD)      x                 y               y (출금·주문 가능 중 작은 값. 정산 현금 아님)

적용 후 알림 엔진 검사: 통과 / 실패(이유)
바뀌지 않는 것: 단계(stage), timing_plan, 체결 기록, 후보 목록, 화면 표시용 스냅샷
주의: 미체결 주문 조회 실패. 미체결 반영 여부 확인 불가 (상태에 open_orders_verified=false로 기록)
최근 체결(표시): 없음 / 있음(종목·날짜)
적용하려면 채팅에 "확인 7F3A91C2"를 보내 주세요. 적용하지 않으려면 "취소".
```

5. 사용자가 "확인 7F3A91C2"를 보내면, Claude가 적용 명령(`reconcile_broker_state.py apply --confirm 7F3A91C2 --confirmed-via COWORK_CHAT`)을 실행하고 결과를 한 줄로 알린다. 예: "revision 14 → 15 적용. 백업: …/backups/portfolio_state.r14.….json".
   - 코드가 다르거나, 제안이 만료됐거나(조회 후 15분, 정책값), 그사이 상태 파일이 바뀌었으면 적용하지 않는다. 만료면 2단계를 다시 한다.
   - 적용은 이 경우에만 한다. Claude는 코드를 스스로 넣지 않고, 이전 확인을 다른 제안에 재사용하지 않는다.
6. 다음 수동 분석에서 `broker_diff_status=MATCH`가 나오면 완료다.
- 15분 만료가 번거로우면 P4에서 만료 시간 조정(정책 변경, K3)을 검토한다.
- 적용 명령은 Cowork의 Linux VM에서 돈다. 필요한 Python 패키지(예: 스키마 검증 라이브러리)가 VM에 있는지는 확인 필요다. 사용자가 Windows 터미널에서 같은 명령을 직접 쳐도 된다(대체 경로).

### 4-2. 입력: 새로 조회한다

- **조정 명령이 계좌를 새로 조회한다.** 수동 분석 결과는 재사용하지 않는다. 이유는 두 가지다.
  - 수동 분석은 스냅샷 해시, 신선도, 조회 시각을 저장하지 않는다.
  - `run_manual`은 고정 파일이라, 지금 고치면 K3 범위가 커진다.
- **재사용할 것**
  - `run_kiwoom_broker_shadow.py`: 조회 → 정규화 → 제안 → 상태 불변 검사 → 스키마 검증. `main()`을 함수로 나눠 조정 명령이 부른다.
  - 그 안에서 쓰는 `invoke_account_bridge_batch`(조회 전용, 허용목록 `SAFE_FIELDS`)와 `normalize_snapshot`
  - 정책의 최대 나이 900초(`kiwoom-broker-readonly-policy.json`)
- **필수 PASS 조회 (제안)**
  - 잔고 `account_holdings_read`(ust21070)
  - 예수금 `account_deposit_read`(ust21110)
  - 체결 `account_fills_read`(ust21510): 최근 체결을 표에 보여 주기 위해서다.
- **표시만 하는 조회:** 예수금 상세, 미체결, 실현손익.
  - 미체결이 실패하면 "미체결 확인 불가" 경고를 붙이고, 상태와 원장에 `open_orders_verified=false`를 기록한다. 적용은 막지 않는다.
  - 근거: 보유 수량(`poss_qty`)은 미체결 주문과 무관하게 현재 보유분이다. 현금은 브로커가 준 값을 그대로 쓰고, 의미를 정확히 라벨로 붙인다(§4-3).
  - 미체결 조회는 16회 모두 실패했다. 따라서 이 결정은 사실상 "미체결 확인 없이 적용"이다. "무엇이 갖춰져야 상태를 쓸 수 있나"의 의미를 바꾸므로 K3 판정 대상이고, Judge가 반대하면 사용자에게 올린다. 미체결 조회 실패 원인 진단은 별도 K2 항목으로 병행한다.
- **`return_code` 검사 (고정되지 않은 계좌 bridge에서)**
  - 계좌 bridge는 `_sanitize`(`:211-242`)에서 `return_code`를 버리므로, 조정 명령에서 나중에 검사할 수 없다.
  - 그래서 계좌 bridge `_fetch_account_page`(`:99`)가 쓰는 검사를 "필드가 있고 0일 때만 성공"하는 로컬 함수로 바꾼다. 고정 파일 `kiwoom_runtime_bridge`는 고치지 않는다.
  - 이 변경은 수동 분석의 계좌 조회에도 적용된다. 방향은 fail-closed(전보다 UNAVAILABLE이 늘 수 있음)다.
  - 계좌 조회 응답에 원래 `return_code` 필드가 있는지는 확인 필요다. 없으면 Builder가 멈추고 대체 검사 방법을 보고한다.
- **I0 전용 입력 검증 (공유 함수 `normalize_snapshot`은 바꾸지 않음)**
  - `normalize_snapshot`이 예외를 내면 수동 분석이 보유 목록을 비운 채 `AVAILABLE`로 표시할 수 있다(`run_manual:306-330`). 그래서 새 검사는 정규화 뒤에 도는 별도 함수로 둔다.
  - 수량이 음수, 비수치, None, 소수면 FAIL. 상태의 수량은 정수다.
  - 평단이 음수, 비수치, None이면 FAIL.
  - 통화가 USD가 아니면 FAIL.
  - 필수 조회 중 가장 오래된 조회 시각이 900초를 넘으면 FAIL. 현재 `broker_snapshot_as_of`는 가장 늦은 시각을 쓰므로(`kiwoom_broker_shadow.py:63-64`) 만료 기준으로 부족하다.
  - 단일 계좌 가정(런타임 `.env`의 한 계좌)은 확인 필요다.

### 4-3. 제안(proposal) 형식

- 기존 키움 전용 `reconciliation_proposal`(`kiwoom_broker_shadow.py:101-122`)을 확장한다.
- 스크린샷용 2.5 스키마(`broker-snapshot-extraction.schema.json`)는 건드리지 않는다. 계좌 마스킹 패턴 필수, `extractor` enum에 KIWOOM 없음, 정수 수량이 키움 입력과 맞지 않는다. 스크린샷 경로는 키움 장애 때의 대안으로 남긴다.
- 새 스키마(제안): `schemas/kiwoom-reconciliation-proposal.schema.json`

| 필드 | 내용 |
|---|---|
| `proposal_id` | 제안 전체 내용의 canonical 해시. 현재는 스냅샷 해시와 revision만 쓴다 |
| `confirm_code` | `proposal_id` 앞 8자리 |
| `source` | `KIWOOM_READONLY_API`. 그 밖에 `snapshot_hash`, `runtime_commit`, 조회별 `retrieved_at`, `expires_at`(= 필수 조회 중 가장 이른 시각 + 900초) |
| `scope` | `HOLDINGS_AND_AVAILABLE_CASH`. 필수·표시 조회별 상태 포함 |
| `expected_state_revision`, `expected_portfolio_hash_before` | 동시 수정 방지 |
| `changes[]` | 종목·항목별 old, new |
| `proposed_patch` | `holdings`(정수), `average_cost_usd`, `position_cost_basis_usd`와 `aggregate_cost_basis_usd`(파생 = 수량 × 평단, Decimal 센트 반올림, 라벨 표시), `available_cash_usd` |
| 현금 의미 | `available_cash_usd` = min(출금가능, 주문가능). 미체결 매수 예약금과 T+1 매도대금 처리가 섞인 "지금 쓸 수 있는 현금"이지 정산 현금이 아니다. 그래서 `cash_verified_scope=available_cash_only`로 기록한다(정책 게이트 `portfolio_policy_gates.py:52-59`가 허용하는 값) |
| `never_touched` | `current_stage`, `timing_plan`, `confirmed_trades`, `pending_candidates`, `broker_display_snapshot`(화면 표시용, 범위 밖), 전략 필드 |
| `post_apply_checks` | 패치한 상태로 알림 엔진 검사(`evaluate_alerts` leveraged 검증, `timing_engine`)를 미리 돌린 결과 |
| `warnings[]` | `OPEN_ORDERS_UNVERIFIED`, `TIMING_PLAN_TICKER_CHANGED`, `POLICY_POSITIONS_MISMATCH` |
| `unresolved_fields` | 비어 있어야 적용 가능 |
| 고정값 | `order_authority=false`, `fill_inference_performed=false`, `quantity_authority=none` |

- **timing_plan 종목(SOXL·MVLL) 수량이 바뀌거나 정책 종목 구성이 달라질 때 (v1 기본값, 제안)**
  - 적용은 허용한다. 상태는 브로커 사실을 따르고, 알림 엔진은 `STATE_MISMATCH`로 멈춘다. 이 멈춤은 "계획이 낡았다"는 정확한 신호이고, 표의 "적용 후 검사"에 미리 보인다.
  - 체결 확인 경로(확정 tranche 기록)와 정책 종목 갱신은 사용자 승인이 필요한 별도 작업이다. **I0-b(K3)**로 따로 설계하고, 순서는 P4에서 정한다.
  - 지금까지 수량이 달랐던 종목은 timing_plan에 없는 NBIS뿐이라, 첫 적용에는 이 경우가 해당하지 않는다.

### 4-4. 적용 경계 (`apply_user_confirmed_broker_snapshot.py` 강화)

- **이미 있는 검사(유지):** proposal 스키마, 확인과 `proposal_id` 일치, revision 일치, 상태 해시 일치(`:47-56`, 적용 시점 재확인 포함), status, source, 보호 파일 이름 거부, 원자적 쓰기.
- **추가하는 검사 — 라이브러리 `apply_confirmed` 안에 넣는다.** CLI에만 두면 8/14처럼 라이브러리를 직접 부를 때 우회된다.
  - 제안이 만료되지 않았다(`expires_at`).
  - `unresolved_fields`가 비어 있다. 이 검사는 스크린샷 경로에도 똑같이 적용된다(더 엄격해지는 방향).
  - `as_of`와 `holdings_complete`는 호출자가 준 값이 아니라 제안에서 가져온다.
- **적용 명령에만 있는 검사:** `--confirm` 코드가 제안의 `confirm_code`와 일치한다. 확인 기록에 `method`(`COWORK_CHAT_USER_MESSAGE` 또는 `USER_TERMINAL`), 확인 시각, 사용자 확인 문구를 남긴다.
- **쓰는 것**
  - `proposed_patch`의 항목
  - `last_confirmed_broker_snapshot`: `source`, `evidence_sha256=snapshot_hash`, `as_of`, `confirmed_at`, `scope`, `holdings_complete`, `cash_verified_scope=available_cash_only`, `open_orders_verified`
  - `last_updated_at`: 현재는 갱신되지 않는 결함이 있다.
  - `state_revision` +1
  - `holding_change_reconciliations`에 1건 추가. 체결로 기록하지 않는다.
- **쓰지 않는 것:** `never_touched` 목록 전체. 체결 가격·시각을 추론하지 않는다.
- **되돌리기 대비**
  - 쓰기 전에 백업한다: `stock-strategy-system/backups/portfolio_state.r{rev}.{ts}.json`.
  - 감사 기록은 덮어쓰지 않는다. 누적 원장 `stock-strategy-system/reconciliation_ledger.jsonl`에 쓰고, 각 줄에 이전 줄의 해시를 넣는다.
  - 상태 파일에는 git 이력이 없으므로 백업과 원장이 유일한 복구 수단이다.
  - 백업과 원장에는 보유·현금 값이 들어간다. 지금은 git 제외 대상이 아니므로 `.gitignore`에 추가하고, `git check-ignore` 테스트로 고정한다.
- **첫 적용 때 바로잡히는 것:** `scope=CASH_ONLY`인데 `holdings_complete=true`인 불일치, `last_updated_at` 8/12.
- **이번 범위 밖:** `current_stage=null`. 브로커로 정할 값이 아니고, 운영 알림 엔진은 leveraged 모드라 `evaluate_alerts.py:1076`에 도달하지 않는다(영향 없음).

### 4-5. 파일과 K 등급

| 변경 | 파일 | K |
|---|---|---|
| 조회·제안 재사용(`main()`을 함수로 분리) | `run_kiwoom_broker_shadow.py` | K3 |
| 제안(`propose`)과 적용(`apply --confirm`)을 나눈 얇은 CLI | `scripts/reconcile_broker_state.py`(신규) | K3 |
| 키움 제안 확장(파생 원가, 현금 의미, 사전 검사), I0 전용 입력 검증 함수 | `kiwoom_broker_shadow.py`(`normalize_snapshot` 계약은 유지) | K3 |
| 엄격한 `return_code` 검사 | `kiwoom_account_readonly_bridge.py`(고정 아님) | K3 |
| 적용 강화(만료, unresolved, 백업, 누적 원장, `last_updated_at`) | `apply_user_confirmed_broker_snapshot.py` | K3 |
| 제안 스키마 | `schemas/kiwoom-reconciliation-proposal.schema.json`(신규) | K3 |
| git 제외 | `.gitignore`(백업, 원장, 새 출력 폴더) | K3 묶음에 포함 |
| 에이전트 규칙(적용은 Cowork에서 사용자 확인 메시지가 있을 때만. 예약 작업·Claude Code·Codex·Judge는 금지) | `CLAUDE.md`, `AGENTS.md` | K3 묶음에 포함 |
| Claude Code 권한 거부 규칙(적용 명령 실행, 상태 파일 직접 편집). Cowork 세션에는 영향 없음 | `.claude/settings.json` | K3 묶음에 포함 |
| 대상 테스트 | `tests/test_reconcile_broker_state.py`(신규), 기존 `test_v2_5_broker_snapshot`, `test_v2_6_broker_beginner`, `test_kiwoom_broker_shadow`, `test_manual_portfolio_analysis`의 test_04·test_08 | K2 |
| 사용법 | `references/broker-snapshot-reconciliation.md`, `SKILL.md` | K0~K1 |
| **건드리지 않음** | `run_manual_portfolio_analysis.py`, `kiwoom_runtime_bridge.py`(고정), 정책 파일 | 없음 |

### 4-6. Independent Judge 확인 항목 (I0)

1. 라이브러리를 직접 불러도 unresolved, 만료, 해시 불일치인 제안은 적용되지 않는다.
2. 적용 명령은 코드 불일치, 코드 없음, 다른 제안의 코드에서 적용하지 않는다. 확인 기록에 방법·시각·문구가 남는다. 에이전트 규칙과 Claude Code 권한 거부 규칙이 실제로 들어가 있다.
3. `never_touched` 항목이 적용 전후에 바이트 수준으로 같다.
4. 체결 추론이나 주문 경로가 없다(주문 API id가 허용목록에 없고, `order_authority=false`).
5. 필수 조회 실패, `return_code` 누락, 음수·소수 수량, 900초 초과가 모두 FAIL이다.
6. `normalize_snapshot`의 계약이 바뀌지 않았다. 수동 분석의 동작 변화는 엄격한 `return_code`에 의한 fail-closed 방향뿐이다.
7. 백업과 누적 원장이 쓰기보다 먼저, 또는 원자적으로 남고, git 제외 대상이다.
8. 분석 경로의 import 금지(test_08)가 그대로 통과한다.
9. 적용 후 알림 엔진 검사 결과가 표에 정확히 보인다.
10. 미체결 확인 불가를 "경고 후 적용 허용"으로 한 결정과 현금 의미 라벨이 적절한지 판단한다(반대 의견이면 사용자에게 올림).

### 4-7. 완료·중단 기준

- **완료:** 실제로 한 번 적용한 뒤 다음 수동 분석에서 `broker_diff_status=MATCH`가 나오고, 원장과 백업이 1건씩 생긴다.
- **중단:**
  - 테스트나 Judge에서 확인 코드 우회 경로가 발견된다.
  - 필수 조회가 3회 연속 PASS하지 않는다.

  어느 경우든 적용을 막고 원인을 진단한다.

---

## 5. I1 보유 종목 카드 (판단 품질)

### 5-1. 사용자 피드백 → 원인 → 설계 기준

| 피드백 | 원인(근거) | 설계 기준 |
|---|---|---|
| 가시성이 낮다 | 결과가 깊은 폴더의 큰 JSON이다. md는 수기 2회뿐이다. 사용자가 매일 보는 현황판과 분리돼 있다 | 종목당 1장 카드와 포트폴리오 머리말 5줄. 현황판에 한 줄 요약(H2) |
| 지나치게 보수적이다 | fail-closed preflight가 판단 칸까지 `NOT_VERIFIED`로 덮었다(09-10 표). baseline 세 종목 모두 REASSESS·DOWNGRADE. plan은 "판단을 지어낼 수 없다"며 생성되지 않았다 | **데이터 게이트와 판단을 분리한다.** 게이트는 상태 쓰기와 주문만 막는다. 판단은 항상 낸다(지침 6절: `NO_HARD_RISK => AUTOMATIC_HOLD 금지`, Champion vs Challenger vs Cash). 판단 작성을 루프의 명시적 단계로 둔다 |
| 일반적이다 | baseline이 47일 전이다. 이벤트는 카테고리 코드만 있고 날짜가 없다. 문장에 수치가 없다 | 모든 칸에 숫자, 날짜, 조건을 넣는다. "kill 기준까지 현재 거리"와 "지난 카드 대비 변화"를 필수로 한다 |

- 과도한 보수성을 줄이는 것이 안전 완화를 뜻하지는 않는다. 다음 규칙으로 선을 긋는다.
  - 카드는 분석이고 결정은 사용자가 한다. 주문 수량과 주문 조건은 없다.
  - **결정론 규칙이 우선한다.** hard risk, holding-risk 규칙, timing 규칙의 결과를 카드 맨 위에 싣는다. 이와 반대되는 판단은 "규칙과 다름: 이유"를 붙여야 검증기를 통과한다.
  - **확신도 상한:** 증거 등급이 낮거나 상태가 미조정이면 확신도는 "낮음"까지만 쓴다.
  - **판단 보류는 두 경우에만 허용한다:** 브로커 조회 UNAVAILABLE, 종목 identity 미검증. 그 밖에는 ADD/HOLD/TRIM/EXIT 중 하나를 쓴다.
  - 카드에 쓰는 숫자는 fact pack에 있는 것만 쓴다. 빠진 데이터는 "확인 필요"로 표시하고, 그것이 판단에 주는 영향을 적는다.

### 5-2. 카드 형식 (제안)

**포트폴리오 머리말 (5줄 이내)**

- 결론 3줄. 가장 중요한 행동 하나를 먼저 쓴다.
- 상태: 기준 시각, 조정 여부, 데이터 등급.
- 노출: 현금 비중, 뿌리 thesis별 비중, 레버리지 환산 노출. 예: AI 반도체 = SOXL(3배) + MVLL(MRVL 2배), 네오클라우드 = NBIS. I3를 간이로 흡수한 것이다.
- 이번 주 확인할 것: 날짜가 있는 이벤트.

**종목 카드 (종목당 1장, 칸마다 1~2줄)**

| 칸 | 내용 | 출처 |
|---|---|---|
| 규칙 결과 | hard risk, holding-risk, timing 규칙의 결정론 결과 | 저장소 규칙 엔진(결정론) |
| 판단 | ADD/HOLD/TRIM/EXIT, 확신도(높음·중간·낮음), 한 줄 이유. **공란 불가**(판단 보류는 위 두 경우만) | Claude 작성 |
| 현금·대안 대비 | 이 자리를 현금이나 대안으로 바꾸면 나은가, 왜 | Claude 작성 |
| 숫자 | 비중, 평가손익, 현재가와 기준 시각, 레버리지 | 분석 JSON(`broker_observed_state`, `current_price_evidence`), 상태 |
| thesis | 한 줄, 상태(유효·논쟁·훼손), 지난 카드 대비 변화 | baseline `primary_reason`·`thesis_status` + 갱신 |
| 틀릴 수 있는 이유 | 가장 강한 반론 하나 | baseline `strongest_counter_case` + 갱신 |
| kill 기준 | 수치나 날짜가 있는 조건과 현재 거리 | baseline `invalidation_conditions` + 수치화 |
| 다음 이벤트 | 날짜와 출처 | 공식 출처. 없으면 "확인 필요" |
| 판단이 바뀌는 조건 | "X면 TRIM" 식으로 1~2개 | Claude 작성 |
| 데이터 상태 | 칸별 나이와 등급, 빠진 것과 그것이 판단에 주는 영향 | 결정론 계산 |
| 지난 판단 성과 | 5/20/60세션 결과 | I2 채점기 |

### 5-3. 파일럿 (코드 없음, B1에서 I0 빌드와 병행)

1. 사용자가 수동 분석을 한 번 실행한다.
2. Cowork에서 분석 JSON, baseline, 공식 이벤트를 읽어 카드 3장과 머리말을 쓴다. 저장 위치는 `workspace/outputs/holding-cards/<날짜>/`다. 이 폴더는 git 제외 대상이 아니므로 커밋하지 않는다(코드화 때 `.gitignore`에 추가).
   - I0 전이라 상태 파일이 오래됐다. 그래서 수량은 분석 JSON의 브로커 관측값(키움 실데이터, 표시 전용)을 쓰고 "상태 파일 미조정" 라벨을 붙인다.
3. 사용자가 3단계로 평가한다: 판단에 씀 / 참고만 / 안 씀. 고칠 점도 받는다.
4. 2회 반복한 뒤 코드화할지, 형식을 어떻게 할지 정한다.

### 5-4. 코드화 (파일럿 통과 후, K2)

| 안 | 내용 | 판정 |
|---|---|---|
| a. dashboard의 decision plan 자체를 재사용 | plan 스키마는 `order_intent_terms.proposed_quantity`와 `limit_price`를 허용한다(`portfolio-decision-plan.schema.json:78-100`). `plan_status=CURRENT_APPROVED`면 dashboard LIVE 경로가 열린다(`:1420`, `:1658`) | **비권장. K3.** Claude가 쓴 카드가 승인된 plan이 되는 권한 상승 경로가 생긴다 |
| **a′. plan의 필드 이름만 빌린 별도 카드 스키마** | `positions[action, rationale, thesis_kill, material_risk]`와 `evidence_binding{expected_run_id, expected_decision_as_of}`의 이름·의미를 따른다. `order_intent_terms`, `proposed_quantity`, `limit_price`, `target_weight_pct`는 금지하고, `plan_status`는 두지 않는다 | **권장. K2.** dashboard가 카드를 plan으로 받지 않는다는 거부 테스트를 넣는다 |
| b. `render_beginner_portfolio_report.py` 재사용 | baseline 문장을 렌더한다. 브로커 조회 전부 PASS를 요구해 미체결 조회가 고쳐질 때까지 막힌다 | 비권장. "일반적"이라는 문제를 그대로 재현한다 |
| c. 완전 신규 | 얇은 fact pack 생성기, 카드 검증기, md 렌더러 | a′의 스키마와 함께 필요한 최소분만 |

- 카드 검증기가 확인할 것:
  - run_id와 as_of 바인딩
  - 필수 칸 공란 금지, 판단 보류 사유 제한
  - 규칙 결과와 반대되는 판단에 이유 라벨이 있음
  - 확신도 상한(낮은 증거 등급, 미조정 상태)
  - 카드에 쓴 숫자가 fact pack과 일치
  - 행동 enum
  - 수량·주문 필드 없음
- dashboard 2,734줄을 운영 경로에 올릴지는 파일럿 후 판정한다(확인 필요).
- baseline을 계속 갱신할지, 카드가 대체할지는 코드화 단계에서 정한다(REMOVE 후보).

### 5-5. 판단 작성 위치 (결정: Cowork, §10)

- **Cowork(권장):** 파일에 직접 접근하므로 사용자가 결과를 옮길 필요가 없다. 운영 부담 목표와 맞는다.
- **Chat(현행 라우팅):** "판단·분석 = Chat" 규칙과 맞지만, fact pack을 사용자가 옮겨야 한다. phase1 D5의 중계 문제가 다시 생긴다.
- 종목 전체분석 protocol(Phase 1 → "추론 시작")이 필요한 깊은 분석은 어느 쪽이든 지금처럼 Chat에서 한다.

---

## 6. I2 결정 원장과 사후 채점 (K2)

### 6-1. 기존 부품 판정

| 부품 | 사실 | 판정 |
|---|---|---|
| `validate_decision_record.py`(v2.0) | 분석 역할 3개, trader, risk, gate가 필수다. `final_action`에 EXIT/TRIM이 없다. 운영 JSON 기록은 0건 | 재사용하지 않고 보존. 나중에 I8 은퇴 후보 |
| `evaluate_outcome.py` | horizon, 벤치마크, 가격 수집이 없다. 수익률을 호출자가 넣는다 | 대체 후보 |
| `continuous_improvement_sidecar.py` | 기본 horizon은 1/5/10/20이지만 `evaluate_forward_outcomes`의 인자다(:486-487). `DECISION_ACTIONS`에 TRIM·EXIT·KEEP_CASH 계열이 있다(:41-44). 해시 체인 원장 함수(`append_run_record`, `validate_ledger_chain`, `append_outcome_artifact`, `validate_outcome_ledger_chain`, :410-462)가 있다. TEST_ONLY 제한은 CLI 경로에만 있다(:1057-1058). 벤치마크·현금 비교는 없다. 원장은 0건. `run_manual`이 import한다(:24) | **확장해서 재사용(REUSE).** 운영 CLI, horizon (5, 20, 60), 벤치마크·현금 비교를 추가한다. `run_manual`이 쓰므로 추가만 하고 기존 동작은 바꾸지 않는다 |

### 6-2. 설계 (제안)

- **카드 = 분석 기록, 사용자 결정은 따로.** 카드를 확정하면 종목마다 원장에 1건을 추가한다.
  - 필드: `decision_id`, `decided_at`, `decision_as_of`, `ticker`, `analysis_action`(Claude 카드), `conviction`, `user_decision`(사용자가 실제로 한 결정. 나중에 사용자가 말하면 새 항목으로 추가), `reference_close`(판단 시점 마지막 확정 종가), `benchmarks`, `card_sha256`, `state_revision`, `evidence_grade`.
  - 카드의 ADD/HOLD/TRIM/EXIT는 sidecar `DECISION_ACTIONS`로 대응시킨다(예: HOLD → `HOLD_CORE`, 현금 → `KEEP_CASH`). 대응표는 코드화 때 정한다.
  - sidecar의 해시 체인 원장 함수를 쓴다. 수정하지 않고 추가만 하며, 정정도 새 항목으로 쓴다.
  - 위치는 `stock-strategy-system/decision_journal.json`(제안)이다. 가격과 보유 판단이 들어가므로 `.gitignore`에 추가한다. 기존 sidecar 원장(`workspace/state/continuous_improvement/`)의 git 추적 여부는 확인 필요다.
- **채점기(결정론, Cold Path)**
  - sidecar `evaluate_forward_outcomes`의 시점 규칙(확정 봉만, `observed_at ≤ evaluation_as_of`)을 그대로 쓴다.
  - 5/20/60 미국 거래 세션 뒤 확정 종가를 쓴다. 캘린더는 `session_calendar_activation.json`을 쓴다.
  - 가격은 키움 일봉(등급 B)을 쓴다. 없으면 다른 제공자 가격을 "reference only" 라벨로 쓴다.
  - 분석 판단과 사용자 결정을 각각 채점한다.
  - 결과는 두 숫자로 낸다.
    - 현금 대비: ADD·HOLD는 종목 수익률 − 0%, TRIM·EXIT는 0% − 종목 수익률.
    - 비교 기준 대비: ADD·HOLD는 종목 − 기준, TRIM·EXIT는 기준 − 종목.
- **해석 주의**
  - 30건 이상 쌓이기 전에는 판단 품질 결론을 내지 않는다.
  - 레버리지 ETF는 경로 의존(변동성 손실)이 있으므로 실현 경로 그대로 채점한다.
- **비교 기준(결정):** 현금 0%와 SPY. 기초자산(SOXX, MRVL)은 참고로 표시한다. SPY가 키움 제공 범위(15종)에 있는지는 확인 필요다.

---

## 7. I7·H1 상태 점검과 알림 창 (K1~K2)

- **새 읽기 전용 명령 `portfolio_status.py` (제안).** `run_manual`은 건드리지 않는다.
  - 계산할 것:
    - 상태 `last_updated_at`의 나이
    - `last_confirmed_broker_snapshot.as_of`의 나이
    - 최근 수동 분석 시각과 `broker_diff_status`
    - 최근 조정(원장)
    - 종목별 baseline 나이
    - 최근 카드 날짜
    - 채점 대기 건수
  - 출력: `workspace/outputs/status/latest.json`(git 제외 추가)과 한 줄 요약.
  - 미체결 조회 실패를 별도 항목으로 표시한다. 기존 렌더러가 막히는 원인이기도 하다.
- **현황판 H1:** 보유 종목 표 위에 한 줄을 넣는다. 예: "상태 기준 8/12 (49일) · 브로커 불일치: 조정 대기 · 마지막 카드 없음".
  - 전달 방법은 둘 중 하나다.
    - Cowork 세션이 status 결과를 artifact db에 기록한다.
    - 현황판 예약 작업이 파일을 읽는다(예약 작업의 장치 파일 접근 가능 여부는 확인 필요).
  - 현황판 db는 표시 전용이라는 원칙을 유지한다.
- **H2(카드 요약 행)**는 I1 코드화 뒤에 한다.
- I0 이후에는 `evaluate_alerts.py`의 브로커 스냅샷 신선도 검사(기본 4일)도 자연히 회복된다.

---

## 8. I4 거버넌스 재설계와 K3 6~9단계 대체안 (K3-b)

### 8-1. 근거 요약

- acceptance는 런타임 게이트가 아니고, 이미 무효다(§1-4).
- 교착 원인: 새 acceptance를 만드는 도구와 검증기가 그 manifest에 고정돼 있다. 그리고 15종목 순서가 하드코딩돼 있다(`materialize_…candidate.py:117-122`, `validate_…candidate.py:20-22`).
- 29개 고정 항목 중 상태 쓰기를 지키는 것은 0개다. 계좌 bridge도 고정돼 있지 않다.
- 교착의 직접 원인은 materialize의 선행조건이다. "현재 active acceptance가 유효해야" 새 후보를 만든다(`materialize_…candidate.py:94-107`). 그런데 active는 이미 무효다.
- acceptance-manifest 스키마의 `schema_version`은 1.0, 1.1만 허용한다(`:15`). 새 버전 manifest를 만들려면 스키마도 바꿔야 한다.
- `run_manual`은 혼합 파일이다. 분석·출력 코드와 함께 다음 보호 기능이 한 파일에 있다.
  - 데이터 정확성 규칙: 가격 부호 `_cur_prc_price`(:85-92), 시간대 검사(:66-70), temporal 상태(:1891-1893)
  - 브로커 비교 `compare_broker_and_system`(:395). I0 완료 판정 기준이다.
  - 예약 입력 검증 `validate_scheduled_input`(:2198). dashboard(:1426)가 쓴다.
  - 분석→쓰기 금지 경계 테스트 test_04, test_08. 고정된 테스트 파일 `test_manual_portfolio_analysis.py` 안에 있다.
- 수동 경로에는 커밋 ID나 dirty 기록이 없다. 예약 경로에는 `verify_current_provenance`(`deployment_provenance.py:137-166`)가 있고, `build_run_manifest.py:71-88`에도 재사용 가능한 선례가 있다.

### 8-2. 새 고정 범위 (제안)

| 구분 | 대상 | 조치 |
|---|---|---|
| 권한 4 | active acceptance, priority policy, provider scope, source registry | 유지. 해시 방식만 줄바꿈 무관으로 바꾼다 |
| 데이터 정확성 | `kiwoom_runtime_bridge`, `kiwoom_provider_preflight`, `session_aware_market_data`, `build_kiwoom_market_snapshot`, `build_kiwoom_session_observation`, `validate_kiwoom_market_snapshot`, 스키마 4개(acceptance-manifest 스키마 포함) | 유지 |
| 신규: 보호 모듈 | `run_manual`에서 분리한 가격 부호·시간대·temporal 규칙, `compare_broker_and_system`, `validate_scheduled_input`과 전용 테스트 | 추가 |
| 신규: 경계 테스트 | test_04·test_08을 옮긴 별도 파일(예: `test_state_write_boundary.py`) | 추가 |
| 신규: 상태 쓰기 | 조정 명령, apply 라이브러리, `run_kiwoom_broker_shadow`, `kiwoom_account_readonly_bridge`, `kiwoom_broker_shadow`, 제안 스키마 | 추가(I0 Judge 뒤) |
| 해제 | `run_manual_portfolio_analysis.py`, `test_manual_portfolio_analysis.py` | 보호 기능을 옮긴 뒤에만 해제. 깨끗한 커밋 + 커밋 ID + 대상 테스트로 검증 |
| 해제 | 도구 4개(materialize, acceptance 검증기, 후보 검증기, `run_kiwoom_session_aware_validation`) | 테스트로 검증. 자기 자신을 고정하는 교착을 없앤다 |
| 원천 증거 9 | 미추적 activation 폴더 | "있으면 검사"를 유지하고 참조(커밋, 경로, 해시)로 기록한다(I9 일부). 코드 사본 추가를 중단한다 |

- **해시 방식:** 코드·문서는 현행 정규화 텍스트 해시를 쓴다. JSON 권한 파일도 raw 해시에서 정규화 해시로 바꾼다.
  - 새 clone이나 `autocrlf=true` 체크아웃에서 f0bab 해시가 바뀌는 문제가 없어진다(`0a7de90c`로 재현 확인됨).
  - `.gitattributes` 추가는 "줄바꿈 일괄 변환 금지" 규칙과 얽히므로 이번 범위에서 뺀다.
- **깨끗한 커밋 기록:** 수동 경로에 `git_commit`, `branch`, 코드 경로(`manage-us-stock-strategy/`) 한정 dirty 여부를 기록한다.
  - dirty 상태로 실행해도 분석은 돌린다. 다만 결과에 `DIRTY_CODE_TREE`로 표시하고, K3 증거로는 쓰지 않는다.
  - Windows `core.autocrlf` 값에 따라 dirty 판정이 달라지므로 확인 필요다.

### 8-3. K3 6~9단계: 기존 vs 대체

| 단계 | 기존 계획(보류 중) | 대체안 (제안) |
|---|---|---|
| 6 | 도구 수정: 구현 드리프트 후속 후보 허용, 15종목 재승인, 테스트가 정책에서 manifest를 찾게 | **R6 Builder**(새 worktree, BOUNDARY_RESET): ① materialize 선행조건을 "허용된 드리프트 목록"으로 바꾼다(기존 6단계 취지 유지). 고정 목록과 15종목은 정책 파일에서 읽고 하드코딩을 없앤다 ② 보호 기능을 모듈로 분리하고 경계 테스트를 옮긴다 ③ 고정 범위를 §8-2대로 바꾼다 ④ acceptance-manifest 스키마에 새 `schema_version`(예: 1.2)을 추가한다 ⑤ `kiwoom_runtime_bridge`의 `return_code` 누락을 FAIL로 바꾼다 ⑥ JSON 권한 해시를 정규화한다 ⑦ 수동 경로 provenance를 기록한다 ⑧ `run_manual`의 정규화 예외 fallback(빈 보유 + `AVAILABLE`)을 `UNAVAILABLE`로 고친다 |
| 7 | 새 INACTIVE 후보 1회 생성, 후보 검증기 PASS | **R7** manifest v2 후보 1회 생성, 검증기 PASS, 전체 테스트(서브에이전트, 17건 해소 확인) |
| 8 | 독립 Judge 1회: 6·7단계, `a5e872a` fail-closed 변경, 08-13/14 증거 재사용 | **R8** Judge 1회: 기존 범위 + "고정 범위 축소가 권한·정확성·상태 쓰기 보호를 약화하지 않았는가" + I0 테스트 재실행(고정된 `kiwoom_runtime_bridge`를 고쳤으므로) |
| 9 | 사용자 승인 후 활성화(priority policy 15행, `acceptance_evidence`, `source_capabilities` 해시 교체) | **R9** 기존과 같다. 추가로 `CLAUDE.md` Change classes의 "run_manual 편집 = K3" 문구를 새 규칙으로 바꾼다 |

- **시점:** I0 완료와 카드 파일럿 뒤, P4에서 정한다. 그 전까지는 다음을 지킨다.
  - `run_manual`과 고정 파일은 수정하지 않는다(현행 K3 유지).
  - CI 17건 실패는 알려진 실패로 표시만 한다. 테스트를 약화하지 않는다.

---

## 9. 변경별 K 등급 총괄

| # | 변경 | K | 비고 |
|---|---|---|---|
| I0 | 조회·제안 재사용, 확인 CLI, 적용 강화, 계좌 bridge `return_code`, 제안 스키마, git 제외, 에이전트 규칙, 권한 거부 규칙 | **K3** | Judge 1회(§4-6) |
| I0-b | 체결 확인 경로(확정 tranche 기록), 정책 종목 갱신 | **K3** | 별도 설계. SOXL·MVLL 수량이 바뀔 때 필요 |
| 미체결 조회 진단 | ust21050 실패 원인 진단 | K2 | 읽기 전용 진단부터 |
| I1 파일럿 | 카드 수기 작성 | 없음 | 코드 변경 없음 |
| I1 코드화 | 별도 카드 스키마(a′), 카드 검증기, 렌더러 | K2 | 고정 파일 밖. plan 자체 재사용(a)은 K3라 비권장 |
| I2 | sidecar 확장(운영 CLI, 60세션, 벤치마크·현금), 결정 원장 | K2 | Cold Path. `run_manual`이 import하므로 추가만 |
| I7 | `portfolio_status.py`(읽기 전용) | K1~K2 | |
| H1 | 현황판 알림 한 줄 | K1 | 표시 전용 |
| H2 | 현황판 카드 요약 행 | K1 | I1 코드화 뒤 |
| I4 | 고정 범위 재설계, 규칙 모듈, `return_code` FAIL, 해시 정규화, provenance | **K3** | R6~R9, Judge 1회 |
| I9 일부 | 원천 증거 참조화, 코드 사본 중단 | **K3** | I4에 포함 |

---

## 10. 사용자 결정 (2026-09-30, P3 통과)

1. **진행 순서: B1.** I0를 단독 K3로 먼저 하고, 카드 파일럿을 병행한다(§3).
2. **I0 확인 방식: Cowork 채팅 확인.** 권장안(터미널 확인 코드)과 다르게 결정됐다. 설계를 다음처럼 바꿨다.
   - 제안은 Windows에서 만들고, 확인과 적용은 Cowork에서 한다(§4-1).
   - 에이전트 규칙을 "적용 금지"에서 "Cowork에서 사용자 확인 메시지가 있을 때만 적용"으로 바꿨다(§2).
   - 절충: 사용자가 터미널에 코드를 직접 치는 방식보다 보증 수준이 낮다. 대신 라이브러리 검사, 제안별 코드, 확인 기록, Claude Code 권한 거부로 보완한다. 사용자 터미널 입력은 대체 경로로 남긴다.
3. **카드 판단 작성 위치: Cowork.** 깊은 종목 분석은 지금처럼 Chat에서 한다(§5-5).
4. **채점 비교 기준: 현금 0% + SPY.** 기초자산은 참고로 표시한다(§6-2).

---

## 11. 다음 단계 (제안, 미승인)

1. §10 결정을 반영해 P4 로드맵을 쓴다. 단계별 완료·중단 기준과 Claude Code 지시문을 포함한다.
2. 코드 없이 바로 할 수 있는 것: I1 파일럿. 사용자가 수동 분석을 한 번 실행하면 Cowork에서 카드를 쓴다.
3. I0 Builder는 P4 승인 뒤 Claude Code 새 worktree에서 한다. 지시문 앞에는 `[Claude Code 실행 권장]` 헤더를 붙인다. Builder의 첫 단계는 계좌 조회 응답에 `return_code` 필드가 있는지 확인하는 것이다(§12).
4. 병행 후보: 미체결 조회(ust21050) 실패 원인 진단(K2, 읽기 전용). I0-b(체결 확인 경로)의 설계 시점은 P4에서 정한다.

### 지표 (phase1 §1-3 보완, 목표값은 제안)

| 지표 | 현재 | P5 목표 |
|---|---|---|
| 불일치 감지 → 조정 완료 | 조정 0/16 | 분석한 날 안에 |
| 상태 나이 | 49일 | 최근 분석일과 같음 |
| 카드 활용(사용자 평가) | 결과 미사용 | 파일럿 2회 중 "판단에 씀" 1회 이상 |
| 결정 원장 | 0건 | 주 1회 이상 |
| 사후 채점 | 0건 | 20세션 첫 결과 |

---

## 12. 확인 필요

- 계좌 조회 응답(잔고, 예수금, 체결)에 `return_code` 필드가 원래 있는지. 없으면 엄격한 검사 방식을 바꿔야 한다.
- Cowork의 Linux VM에서 적용 명령이 도는지(Python과 스키마 검증 패키지).
- 제안 만료 15분(정책값)이 Windows → Cowork 확인 흐름에 충분한지.
- `frgn_stk_book_uv`(평단)에 수수료가 포함되는지.
- 보유 수량의 의미: `poss_qty`(held)와 `qty`(settled) 중 상태에 어느 것을 쓸지. 제안은 held.
- 미체결 조회(ust21050)가 매번 `KIWOOM_API_RESPONSE_ERROR`인 원인.
- 파생 원가를 `evlt_amt - pl_amt`로 교차검증할 수 있는지. 현재 정규화 단계에서 두 필드를 버린다.
- Windows와 CI 러너의 `core.autocrlf` 값.
- 현황판 예약 작업이 장치 파일을 읽을 수 있는지.
- 단일 계좌 가정(런타임 `.env`의 한 계좌).
- dashboard 2,734줄의 운영 적합성.
- SPY가 키움 제공 범위에 있는지.
- 기존 sidecar 원장(`workspace/state/continuous_improvement/`)이 git 추적 대상인지.
- 09-09, 09-10 실행 폴더의 추가 파일과 md 리뷰를 누가 썼는지.
- 8/14 CASH_ONLY 적용용 제안(`cash-only-reconciliation-proposal.json`)과 확인 파일을 만든 방법. 조회·제안 파일 2개는 `run_kiwoom_broker_shadow.py` 출력이다.

## 13. 반론 검토 반영 기록 (2026-09-30)

초안을 별도 서브에이전트가 코드와 대조해 검토했다. 핵심 사실(`full_holding_analysis_performed` 고정, `return_code` 처리, `scope_complete` 조건, 적용 함수 결함, acceptance 해시 드리프트, 줄바꿈 원인)은 맞았다. 지적 14건 중 반영한 것은 아래와 같고, 주요 항목은 직접 코드로 다시 확인했다.

- **[안전] 라이브러리 직접 호출로 확인 우회.** 8/14 선례가 실제로 그랬다(unresolved 3개 상태로 적용). → 검사를 라이브러리 안으로 옮기고, 에이전트 규칙과 Claude Code 권한 거부 규칙을 추가했다(§2, §4-4).
- **[논리] `return_code`는 계좌 bridge `_sanitize`에서 버려진다.** 조정 명령에서 검사할 수 없다. → 고정되지 않은 계좌 bridge에서 엄격한 검사로 바꾸도록 수정했다. B1의 독립성은 유지된다(§4-2).
- **[안전] 공유 함수 `normalize_snapshot`을 바꾸면 수동 분석이 "빈 보유 + AVAILABLE"로 표시될 수 있다.** → I0 전용 검증 함수로 분리하고, fallback 결함은 R6에 넣었다(§0-7, §4-2, §8-3).
- **[누락] 알림 엔진(leveraged 모드)의 종목·tranche 일치 검사.** → 적용 전 사전 검사를 표에 보이고, 체결 확인 경로는 I0-b로 분리했다(§1-3, §4-3).
- **[안전] 미체결 확인 불가 허용과 현금 의미.** → 체결 조회를 필수로 올리고, `open_orders_verified=false`를 기록한다. 현금 라벨을 `available_cash_only`로 정정했다(§4-2, §4-3).
- **[과장] 렌더러는 MATCH만으로 풀리지 않는다**(전 조회 PASS 필요). → §0-1과 §5-4를 정정했다.
- **[K등급] plan 자체 재사용은 권한 상승 경로라 K3다.** → 별도 카드 스키마(a′, K2)로 바꿨다(§5-4).
- **[논리] "판단은 항상 낸다"와 "결정론 규칙 우선"의 충돌.** → 규칙 결과 우선, 확신도 상한, 판단 보류 사유 제한, 분석 판단과 사용자 결정 분리를 추가했다(§5-1, §5-2, §6-2).
- **[K등급] `run_manual` 고정 해제는 브로커 비교, 예약 입력 검증, 경계 테스트 보호를 약화한다.** → 이 기능들을 먼저 고정 모듈로 옮긴 뒤 해제하도록 수정했다(§8-1~8-2).
- **[논리] acceptance 스키마 버전 제한과 materialize 선행조건 누락.** → R6에 추가했다(§8-3).
- **[누락] 기존 부품 재사용.** `run_kiwoom_broker_shadow.py`와 sidecar의 해시 체인 원장·horizon 인자·행동 목록. → I0와 I2를 재사용 중심으로 바꾸고, §6-1을 정정했다.
- **[누락] git 제외.** 새 백업·원장·출력 폴더가 제외 대상이 아니다. → `.gitignore` 항목과 검사 테스트를 I0 범위에 넣었다.
- **[누락] 수량 정수 강제, 원가 계산, 만료 기준 시각, `aggregate_cost_basis_usd`와 `broker_display_snapshot` 처리.** → §4-2, §4-3에 반영했다.
- **[사실오류] `current_stage` 영향 경로와 "적용 시점 해시 재확인은 신규" 서술.** → leveraged 모드라 영향이 없다는 점과, 해시 재확인은 기존 검사라는 점으로 정정했다.

## 14. 근거 파일

- **조정 경로:** `manage-us-stock-strategy/scripts/`의 `kiwoom_broker_shadow.py`(19-25, 35-98, 101-122), `run_kiwoom_broker_shadow.py`(1-52), `apply_user_confirmed_broker_snapshot.py`(23-91), `build_broker_reconciliation_proposal.py`, `kiwoom_account_readonly_bridge.py`(14-18, 84-99, 211-242, 245-295), `kiwoom_runtime_bridge.py`(137-138, 340-363), `run_manual_portfolio_analysis.py`(295-429, 467, 1722, 1935), `portfolio_policy_gates.py`(52-59), `evaluate_alerts.py`(409-417, 499-516, 1066), `timing_engine.py`(101-106), `.gitignore`(27-37)
- **판단·기록:** `render_beginner_portfolio_report.py`(220, 262, 371-375, 397), `portfolio_decision_dashboard.py`(1420-1426, 1658, 2362-2392), `schemas/portfolio-decision-plan.schema.json`(78-100), `validate_decision_record.py`, `evaluate_outcome.py`, `continuous_improvement_sidecar.py`(40-44, 410-462, 486-487, 1057-1058), `workspace/research/holding-baselines/*`
- **거버넌스:** `workspace/research/provider-evidence/kiwoom/2026-08-29/f0bab…/…superseding-candidate.json`, `validate_kiwoom_session_aware_acceptance.py`(16-90), `materialize_…candidate.py`(104-122), `deployment_provenance.py`(137-166), `build_run_manifest.py`(71-88), `docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md`(98-145)
- **산출물:** `workspace/outputs/manual-portfolio-analysis/*`(필드 집계만), `workspace/outputs/portfolio-decision-plan-candidates/2026-09-02/…audit.md`, `workspace/outputs/activation/kiwoom-broker-shadow/20260814-234459-master-revalidation/`(파일 구성만)
- **규칙:** `AGENTS.md`(35), `CLAUDE.md`, 프로젝트 지침 6·7절
