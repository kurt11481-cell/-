---
id: first-collect-proposal-2026-11-11
title: 새 종목 30분봉 첫 수집 시작일 고침 — 코어 daily가 PLTR 첫 수집에서 멈춤(11/11)
date: 2026-11-11
class: 권한 경로 버그 수정(auto_core*.py = authority-paths.txt 12행) — 의미상 권한·한도·주문 단계·대조 불변식·킬 스위치 불변
source: 사장실 회사PC 스레드 'QQQ 등록(K3) 먼저 진행' 11/11 08:10 KST 예약 확인
authority: order_authority=false · quantity_authority=none · 주문 경로 없음 · 정책·상태 파일 변경 없음
---

# 새 종목 30분봉 첫 수집 시작일 고침 (first-collect)

## 0. 결론

- 11/11 06:15 KST 자동 코어 daily는 Python 단계를 통과했다(11/10 tzdata 설치 효과). 하지만 `BAR_COLLECTION_FAILED:PLTR:1`로 FAIL했다.
- 원인: 새 종목은 2026-04-01부터 받게 고정돼 있는데, 키움이 지금 PLTR 30분봉을 2026-05-01부터만 준다.
- 수정: 고정 시작일을 "오늘에서 150일 전과 2026-04-01 중 늦은 날"로 바꾼다. 그러면 PLTR과 QQQ가 모두 수집된다.
- 고치지 않으면 코어 daily가 매일 같은 곳에서 멈춘다.

## 1. 사실 (11/11 08:1x~08:5x KST 읽기 전용 확인)

- **로그:** `workspace/outputs/auto-core/logs/auto-core-daily-20261110T211501Z.log`에 `"status": "FAIL", "reasons": ["BAR_COLLECTION_FAILED:PLTR:1"]`, `RUNNER_END exit=1`이 남았다. decide 로그(`auto-core-decide-20261110T224501Z.log`)는 exit 0이지만 결과는 HOLD(`reasons ["T1_NOT_OK"]`)다.
- **멈춘 위치:** 종목은 정렬 순으로 수집된다(auto_core.py:111). BE·DELL·GRID·LITE·MU는 06:15에 갱신됐고 PLTR에서 멈췄다. 그래서 PWR·QQQ·SOXL·SOXX·SPY는 시도하지 못했다. `history/QQQ.close-history.json`도 없다.
- **PLTR이 이제 처음인 이유:** PLTR은 2026-11-07 13:16 KST 관심 명단 주간 자동 갱신에서 들어왔다(커밋 4b0c81d). 11/10 daily는 Python 단계에서 실패했으므로, 11/11이 첫 수집이다.
- **키움 자료가 끝난 곳:** `pages/PLTR/`에는 파일 28개가 저장됐다(20260506~20261111). 가장 오래된 `pltr_30m_20260506_p3.json`은 return_code 0이고 176행이다(보통 300행). 첫 봉은 20260501 04:00이다. 그 앞 요청은 빈 응답이라 거절됐다(`collect_30m.ps1` 63~64행 → exit 1). 그 요청의 exit 코드와 바이트 수는 로그에 남지 않는다(auto_core.py:150-154가 출력을 캡처함). 다만 앞선 28번이 모두 정상이었으므로 인증이나 속도 제한 때문일 가능성은 낮다.
- **다른 종목과 비교:** 10/29까지 처음 받은 종목(BE·SPY·SOXL 등)은 가장 오래된 봉이 모두 20260401 04:00이다(SPY·SOXL 84행, BE 176행). 키움 자료의 시작일은 날마다 하루씩 밀리는 것이 아니라, 달 경계에서 앞으로 옮겨지는 것으로 보인다. 옮겨지는 규칙은 확인 필요다.
- **고정 시작일의 위치:** `manage-us-stock-strategy/scripts/auto_core.py:57` `FIRST_COLLECTION_DAY = date(2026, 4, 1)`. 352행이 이력 없는 종목의 수집 시작일로 이 값을 쓴다.
- **관련 없는 경고:** `POST_APPLY_CHECK_ERROR:LITE: canonical instrument registry record is missing or unverified`는 11/06부터 있던 경고다. 11/09 QQQ 병합(a764e97)과 무관하다.

## 2. 원인

- 새 종목 첫 수집 시작일이 2026-04-01로 고정돼 있다.
- 키움 30분봉 자료의 시작일은 앞으로 옮겨진다. 2026-04-01이 그 범위 밖으로 나간 뒤 처음 추가된 종목이 PLTR이라, 이번에 처음 드러났다.
- 수집 스크립트가 빈 응답을 실패로 처리하는 것(fail-closed)은 맞다. 고칠 것은 시작일뿐이다.

## 3. 영향

- **코어 daily가 매일 FAIL한다.** 수집 날짜는 그날 날짜에서 7일씩 거꾸로 정해진다(collect_30m.ps1:39-46). 그래서 다음 날에는 날짜가 하루 밀려 저장된 페이지를 다시 쓰지 않고 새로 받는다. 그러다 4/1 쪽 빈 응답에서 다시 멈춘다. 그동안 노출 검토와 비교는 갱신되지 않고, decide는 HOLD로 매수를 막는다.
- **decide 비교 연속일이 0이 됐다.** 11/07에는 5/5였는데, 11/11이 비교되지 않아 다시 세기 시작한다(auto_core_compare.py:331-345). 고친 뒤에도 5일을 다시 쌓아야 한다.
- **QQQ:** QQQ도 새 종목이라 같은 첫 수집을 거친다. PLTR을 고치지 않으면 QQQ 차례가 오지 않는다. 그래서 QQQ 등록 단계 A의 마지막 확인(이력 생성)이 막혀 있다.
- **통합 점검(06:40)은 영향이 없다.** 11/11 실행은 끝까지 돌았다(ic-context 스레드 기록).

## 4. 수정안 (개발 큐 1건, class authority)

**코드 변경**
- `auto_core.py`에 상수 `FIRST_COLLECTION_LOOKBACK_DAYS = 150`을 추가한다.
- 352행을 `oldest = date.fromisoformat(last_session) if last_session else max(FIRST_COLLECTION_DAY, today - timedelta(days=FIRST_COLLECTION_LOOKBACK_DAYS))`로 바꾼다.
- `timedelta` import 1곳을 추가한다.

**150일로 정한 이유**
- 시작일이 매달 1일로 옮겨진다고 보면, 남는 자료는 최소 약 181일이다. 150일이면 31일 이상 여유가 있다.
- 약 105세션이 된다. EMA50·σ60·시나리오 65세션·20세션 고점 계산에 충분하다.

**바꾸지 않는 것**
- 이미 이력이 있는 종목(`last_session`)의 경로.
- `collect_30m.ps1`(빈 응답 = 실패).
- 이력 검증. build_history에는 최소 세션 수나 시작일 조건이 없다(regular_session_close_history.py:195-271).
- 주문·권한 표지.

**고친 뒤 이력 시작일**
- PLTR: 남아 있는 페이지 덕분에 5/1부터.
- QQQ: 약 6/10부터(약 107세션).

**알아 둘 영향**
- QQQ를 보유하게 되면, 공통 창 규칙(portfolio_exposure.py:218-224) 때문에 포트폴리오 V 계산 창 전체가 수익률 약 154개에서 약 105개로 짧아진다. 최소 60 조건은 넘는다.
- `qqq-reg-report.md:84`와 `qqq-reg-judge-report.md:51`의 "QQQ 이력은 4/1부터" 문구는 맞지 않게 된다(기록 문서라 고치지 않고 여기에 적어 둠).

**테스트**
- 기존 테스트 `tests/test_auto_core.py:1313`이 fixture NOW(KST 2026-10-14)의 새 종목 oldest를 "2026-04-01"로 고정하고 있다. 새 규칙에서 이 값은 "2026-05-17"(10/14 − 150일)이다. 이 기대값 한 줄만 바꾸고 단언은 그대로 둔다.
- 새 테스트 `tests/test_auto_core_first_collect.py`는 `base.DailyTests`를 상속하고 `load_tests`를 쓴다(선례 test_auto_core_reconcile_orddt.py:184-231). fixture NOW에서 세 가지를 확인한다.
  - 새 종목 oldest = 5/17
  - 이력 있는 종목 oldest = last_session(전과 같음)
  - FIRST_COLLECTION_DAY를 6/1로 바꾸면(mock) oldest = 6/1(max 확인)
- 다른 날짜로 돌리면 체결 조회 창 14일(auto_core_reconcile.py:83)에 걸려 수집 전에 대조가 FAIL한다. 그래서 fixture NOW를 그대로 쓴다.

**Judge G9**
- 새 산출(출력 파일·알림·화면 칸·예약)이 없으므로 '해당 없음'이다.

## 5. 경로·승인

**올리는 것**
- 지시문 `docs/claude/first-collect-builder-prompt.md`
- 커밋 목록 `docs/claude/_pending/first-collect.txt` (지시문·이 수정안 — 커밋되지 않으면 STOP_PROMPT_NOT_COMMITTED)
- 큐 파일 `docs/claude/_dev-queue/first-collect.txt`

**실행 조건**
- Builder는 opus로 돌고, 대상 테스트만 실행한다.
- 결과는 NEEDS_APPROVAL(authority)로 나온다.

**승인**
- 착수: 이 수정안에 대한 사장 승인 1회(CLAUDE.md 카드 승인 조건, 같은 날 1회).
- 병합: 결과를 보고한 뒤 사장 결정을 받는다. 사장이 대화형 PowerShell에서 `.\tools\dev-merge.ps1 first-collect -ApproveAuthority`를 실행한다(README 11·44·70행).

**일정**
- 다음 코어는 11/12 06:15 KST다. 그 전에 병합되면 그 실행에서 PLTR·QQQ 이력이 생긴다.
- QQQ의 거래소 조회(usa10098) 결과는 확인 필요다. 다음 실행에서 확인한다.

## 6. 착수 결정 기록

- **승인:** 사장 직접 입력 "승인", 2026-11-11 08:33:23 KST.
  - 메시지 cmsg_0137MRzn9nuDvvQmVxm6WeX9AoExH6Bh3qYWxDUHUSr6Wm
  - 계정 user_01KuMGKfZu1SBYxtMmg4vAiH(금동한)
  - 스레드: 사장실 회사PC 'QQQ 등록(K3) 먼저 진행'
- **무엇에 대한 답인가:** 바로 앞 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9JBa6CKDbXEwkcprBLUPd52.
  - 질문: "PLTR 첫 수집에서 멈춘 코어, 수집 시작일 고침을 착수할까요?"
  - 수정안 id: first-collect-proposal-2026-11-11
  - 고른 항목: '착수 — 시작일 고침'(0번)
  - 카드는 탭이 아니라 이 직접 입력으로 닫았다.
- **승인 범위:** 개발 큐 작업 first-collect를 한 번 올리는 것까지(class authority, Builder opus). 병합은 결과 보고 뒤 사장이 `-ApproveAuthority`로 한다.
- **경로 확인:** auto_core*.py는 권한 경로(authority-paths.txt 12행)이고, 보호 경로(README 52행)에는 없다. 그래서 개발 큐로 갈 수 있다. 선례는 ust21100-fix2와 ri1-session2다.
- **큐에 올리기 전 Opus 재검토(CLAUDE.md V5, 08:4x KST):**
  - 원인 판정은 맞았다.
  - 지시문 수정 5건을 반영했다.
    - 키움 자료 시작일 문구를 '달 경계에서 옮겨짐'으로 고침
    - 3절의 '저장 페이지를 건너뜀'을 '날짜가 밀려 다시 받음'으로 고침
    - 영향 3건 추가
    - _pending 추가
    - 테스트를 fixture NOW와 mock으로 바꿈(11/11·5/1 날짜는 대조 창에 걸려 수집까지 못 감)
  - 남은 확인 필요는 둘이다: QQQ 거래소 조회 결과, 그리고 빈 응답 요청의 실제 반환 코드.

## 6-2. 실행·병합 기록

- **개발 큐:** 11/11 08:55:11 KST 시작, 09:27:27 끝. 결과는 NEEDS_APPROVAL, Judge PASS(2회차), 새 실패 0, 테스트 3497 → 3501, base b2e0f08. 1회차는 보고서 문장에 권한 표지 이름이 들어가 G8 FAIL이었고, 코드는 같다.
- **diff 확인:** 이 스레드가 workspace/outputs/dev-runs/first-collect/attempt-2/diff.patch를 직접 읽었다. 바뀐 곳은 다음과 같다.
  - auto_core.py: timedelta import, 상수 FIRST_COLLECTION_LOOKBACK_DAYS = 150과 주석, 352행 else 쪽.
  - test_auto_core.py:1313 기대값 4/1 → 5/17, 주석 1줄 추가.
  - 새 테스트 4개.
- **병합 결정·병합:** 사장이 결과 안내를 받은 뒤 대화형 PowerShell에서 `.\tools\dev-merge.ps1 first-collect -ApproveAuthority`를 직접 실행했다. 커밋은 22769dc(2026-11-11 13:03:56 KST). 사장 보고는 "병합 완료"(13:04:04 KST)다. 병합 뒤 저장소에서 auto_core.py:60·356, test_auto_core.py:1314, 새 테스트 파일이 있는 것을 확인했다.
- **첫 실행 확인:** 11/12 06:15 KST 코어에서 PLTR·QQQ 이력이 생성됐는지, QQQ 거래소 조회가 됐는지 본다. 확인은 08:10 KST에 예약해 두었다.

## 7. 되돌리기

병합 커밋을 `git revert`한다. 이미 받은 pages·history 파일은 읽기 전용 수집 결과라 그대로 둬도 된다.
