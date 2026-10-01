# S7-1 Independent Judge 지시문 — S5 정책 1차 적용(더하기만) 구현 심사 (2026-10-01)

- 대상: worktree `s7-policy`(브랜치 `worktree-s7-policy`, HEAD `08b43a5`)의 **커밋 전 변경**(고친 파일 11개 + 새 파일). Builder 보고 `docs/claude/s7-builder-report-2026-10-01.md`(worktree 안, sha256 `b59ac920…`).
- 근거 문서(원본 폴더, 미커밋): `E:\사업\##금동한\코덱스저장소\docs\claude\s7-builder-prompt-2026-10-01.md` 6절(사용자 결정 P0~P8-6), 7절(Cowork 실측), 8절(1차 구현 지침). S5 제안서 "S5 확정안 r2"·5절·9절(커밋 `08b43a5`).
- 성격: K3 구현 심사. Judge는 파일을 고치지 않는다. 주문·수량 권한 없음.
- Cowork 사전 확인(10-01, 읽기 전용): 정책 키 경로 diff 더함 177·지움 0·바뀜 0(두 새 섹션만), 기존 최상위 순서 유지, 등록부 무변경, 고정 파일(배포 6·acceptance 16) 변경 목록에 없음, 새 테스트 7개 파일 Linux Python 3.10에서 통과, `test_reconcile_broker_state` 1건은 VM git이 worktree 경로를 못 읽어서 난 환경 실패(`git check-ignore`), 픽스처에 실제 계좌 자료 없음(가상 라벨 `9999-0000-11 [TEST_ONLY]`), 표본 픽스처 2개는 Cowork 표본과 해시 동일.
- 기준 해시(worktree): `alert_policy.json` 원시 `8e096514…`, LF `75d37fb0…` / `instrument_registry.json` 원시 `f0c2a342…`, LF `8d11aae8…`(변경 전과 같음) / 기준선 실패 목록 `c1a6e5e0…`.
- 상태: 작성 완료, Judge 미실행.

## 1. 사용자 조작 (Windows 터미널)

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(Builder worktree 폴더에서, 새 worktree 아님) · 이유: K3 구현 독립 심사, 커밋 전 변경을 그대로 봐야 함, 파일 수정 없음**

1. Builder 창은 닫지 말고 그대로 둔다(수정이 필요하면 다시 쓴다). 새 Windows 터미널을 연다.
2. `cd "E:\사업\##금동한\코덱스저장소\.claude\worktrees\s7-policy"`를 입력한다.
3. `claude`를 입력한다(`--worktree` 없이).
4. 세션 안에서 `/model`로 Opus, `/effort`로 xhigh를 고른다.
5. 아래 한 줄을 붙여 넣는다.
   `원본 폴더 파일 E:\사업\##금동한\코덱스저장소\docs\claude\s7-1-judge-prompt-2026-10-01.md 3절 상자 안의 지시를 그대로 따르는 S7-1 Judge로 일해라. 파일을 고치지 마라.`
6. 권한 확인 창: 읽기, git 읽기 명령, python 테스트·해시 계산, worktree 밖 파일 읽기는 허용. 파일 쓰기·수정·삭제, 커밋, 키움 도구는 거부.
7. 끝나면 마지막 "S7-1 판정" 블록만 복사해 Cowork에 붙여 넣는다.

## 2. 판정 뒤 처리

- PASS: Cowork가 커밋 전 확인(표본 픽스처 커밋 승인 U12 포함)을 하나씩 묻고 → Builder 창에서 커밋 → 사용자 병합.
- PASS_WITH_FIXES: Cowork가 Builder 수정 지시를 쓴다 → 같은 Builder 창에서 최소 수정 → 같은 Judge 창에 "수정 재확인, 필수 수정 항목만".
- FAIL: 사용자 결정 항목을 Cowork에서 하나씩 정한다 → Builder 수정 → 재심사.

## 3. 붙여넣기용 지시문

```text
역할: S7-1 Independent Judge (K3 구현 심사). 대상은 현재 폴더(worktree s7-policy)의 커밋 전 변경이다.
금지: 파일 수정·생성·삭제·이동, 커밋·브랜치 변경, 키움 도구, 주문 도구, .env*·토큰·계좌번호 읽기, 네트워크 조회,
      reconcile_broker_state.py apply, portfolio_review_journal.py apply.
허용: 파일 읽기(worktree 밖은 E:\사업\##금동한\코덱스저장소\ 아래 읽기만), git 읽기 명령(status/diff/show/log/rev-parse/ls-files/check-ignore),
      python 해시·산술, 테스트 실행(PYTHONDONTWRITEBYTECODE=1, 결과 파일을 worktree에 남기지 않음). 긴 전체 테스트는 서브에이전트로.
자기 보고(Builder 보고)는 단서일 뿐이다. diff·코드·테스트 출력으로 확인한다. 없는 수치는 만들지 않는다(확인 필요 / NOT VERIFIED).
보고는 한국어, 식별자는 영어.

0. 기준 확인(다르면 멈추고 보고)
   - HEAD 08b43a5. git status가 "고친 11개 + 새 파일(스크립트 5, 스키마 7, 자산 2, 참고 문서 1, 테스트 8 + 픽스처 폴더, docs/claude 3)"뿐인지.
   - alert_policy.json LF sha256 75d37fb0…, instrument_registry.json LF 8d11aae8…(HEAD와 같음).
   - 읽기: CLAUDE.md, 원본 폴더 docs/claude/s7-builder-prompt-2026-10-01.md 3·6·7·8절, docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md
     "S5 확정안 r2"·5절·9절, docs/claude/s7-builder-report-2026-10-01.md 2·3·4·5절,
     docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md 2-1절, manage-us-stock-strategy/references/broker-snapshot-reconciliation.md.
1. 판정 항목
   J1 더하기만: alert_policy.json을 HEAD와 키 경로로 비교(지움·바뀜 0, 새 섹션 2개만). 등록부 무변경. deployment_gate 6개와
      acceptance 16개 정규화 해시가 HEAD와 같음(validate_skill_deployment.normalized_text_sha256). workspace/policies/ 무변경.
      기존 테스트 파일 무수정. 옛 통제(원가 한도·축소 슬롯·weakness_10ema·재무장)가 그대로 작동하는지.
   J2 권한·출력: 결과 스키마와 코드에 order_authority=false, quantity_authority="none", execution_quantity=null 고정.
      수량·금액·주문 지시 필드 없음, 등급은 정책 alert_grade_mapping(B·C·D)만, 매수 후보를 만들지 않음. 출력은 목표 비중만.
   J3 fail-closed: R0 7개 트리거, "적용 시작" 기록 없음, 달력 비ACTIVE(9월 이후, F1), 봉 표기 UTC 오프셋 미확인(D19),
      원장 사슬 깨짐, 종가·거래내역 증거 공백, 매도 뒤 현금 미확인(D24). 검증된 종가·적용 시작·입출금 증거 없이
      채우기·신규 매수 권고나 선 "통과"가 나오는 경로(fail-open)가 있으면 적는다.
   J4 대조 apply 경로(K3): 신고 블록이 없으면 대조안 바이트·확인 코드·원장 줄이 HEAD 동작과 같은지(테스트 또는 직접 비교).
      블록이 있으면 대조안 해시에 들어가 새 확인 코드가 되는지, apply가 다시 검사하는지, 상태 필드·NEVER_TOUCHED가 그대로인지.
      스키마 버전 문자열을 유지한 것(U11)이 맞는지.
   J5 새 쓰기 경로 decision_journal(portfolio_review_journal.py apply): 확인 코드·사용자 메시지·만료(60분)·사슬·단일 쓰기 경로.
      .claude/settings.json에는 reconcile apply deny가 있지만 이 새 apply의 deny는 없다(Cowork 확인). 병합 전에 같은 방식의
      deny를 더해야 하는지(필수 수정) 병합 뒤 작업으로 둬도 되는지 판정한다.
   J6 사용자 결정 반영: P1(재계산, 사람 확인만 기록), P2(등급표), P3(15:30 봉 종가, "근사 종가", 외부 종가는 차이 표시만),
      P4-1(저장된 쪽만 읽음, 키움 호출 없음), P4-2(가용 세션 최소 60, "짧은 이력"), P6(적용 시작 기록, status 값), P7(K132-G 설정만),
      P8-6(R6 1차 포함, ust21100 증거 파일, 브리지·브로커 정책 무변경)가 코드·정책에 맞게 들어갔는지.
   J7 Builder 기본값 D13~D30: 항목마다 "수용 / 사용자 결정 필요 / 수정 필요". 특히 D17(상한 초과만으로 줄이기 권고 없음),
      D19, D21(적용일 당일 선 판정), D23(환전 포함·일부 신고), D24(매도 뒤 보류), D29.
   J8 r2와 다른 정책 값 5개·r2에 없는 경로 19개가 모두 사용자 결정·지침으로 설명되는지.
   J9 테스트: 새 테스트 7개 파일과 요구 8의 12개 파일을 직접 실행. 전체 테스트는 서브에이전트 1회, 미통과 ID를
      docs/claude/s7-builder-baseline-test-failures-2026-10-01.txt와 비교(새 미통과 0이어야 함). 4.2 대응표에서 5개 이상을 골라
      테스트 본문이 그 사례를 실제로 단언하는지(동어반복·항상 참 아님) 확인한다.
   J10 자료 처리: 실제 표본 픽스처에서 SOXX 2026-09-30 종가로 15:30 봉 종가 568.20을 고르는지(16:00 봉 570.80 아님).
       "1f"를 수정주가로 쓰지 않는지. 거래내역 분류표(assets/kiwoom-transaction-history-classification.json)의 추정 항목(U3).
   J11 개인정보: 테스트·픽스처에 실제 계좌번호·이름·잔고가 없는지, acnt_print가 정리 단계에서 빠지는지, 새 증거·기록·결과 경로가
       .gitignore에 있는지(git check-ignore).
   J12 적대 점검: 잘못된 매수 권고나 선 회피가 가능한 경로를 찾는다. 예: 입금 신고로 HWM 올리기·출금 미신고로 선 피하기,
       증거 파일 편집(해시 재계산 포함), 적용 시작을 자료 준비 전에 기록, 검토 없이 L2 멈춤 해제, 달력·입력 경로 바꿔 끼우기,
       짧은 이력으로 V를 낮게 잡아 채우기, 종목 폴더 바꿔 넣기(F2).

판정 기준: PASS = 그대로 커밋 가능. PASS_WITH_FIXES = 같은 Builder의 최소 수정으로 해소, 사용자 새 결정 없음.
FAIL = 사용자 결정 또는 설계 변경 필요.

출력: 마지막에 아래 블록 하나(45줄 이내). 앞에 긴 설명을 붙이지 않는다.
S7-1 판정
- 기준: HEAD, git status 일치 여부, 정책·등록부 LF 해시
- 최종: PASS / PASS_WITH_FIXES / FAIL
- J1~J12: PASS/FIX/FAIL + 한 줄 근거(파일:행 또는 테스트 이름)
- 테스트: 실행 수·새 미통과 수(전체, 대상)
- 필수 수정(커밋 전, Builder): 번호 목록
- 병합 뒤 작업에 더할 것: 번호 목록
- 사용자 결정 필요: 질문 형태로(없으면 "없음")
```

## 4. 진행 기록

- 2026-10-01 작성(Cowork). Builder 1차 완료(새 미통과 0 보고) 뒤 Cowork 읽기 전용 확인을 거쳐 작성. 정책·상태 원본 무변경.
- 2026-10-02 S7-1 판정 PASS_WITH_FIXES(J3·J5·J10·J12 FIX, 필수 수정 6, 새 미통과 0, 사용자 새 결정 없음). Builder 수정 지시는 `s7-builder-prompt-2026-10-01.md` 9절. 다음은 같은 Judge 창에서 수정 재확인.
- 2026-10-02 S7-1 재확인 PASS(a~g 해소, 해석 5개 수용, 새 미통과 0). 사용자 U12 커밋 승인. 다음은 Builder 커밋 → 사용자 병합.
