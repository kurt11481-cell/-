# SOXX 3:1 분할(11/05 효력) — 회사 시스템 영향 확인 (2026-11-05 22:4x KST, 읽기 전용)

## 결론
- **E가 낮게 잘못 읽히는 일은 없다.** 내일(11/06) 07:45 코어는 SOXX 11/04→11/05 종가 비율(약 0.32)을 분할 방지선에 걸어 V를 "없음"으로 두고, E도 "없음"으로 낸다(fail-closed). HARD_CEILING이 "풀림"으로 바뀌지 않고 band는 UNAVAILABLE이 된다.
- **대신 공식 분할 기록을 넣기 전까지 매일 E 없음 + 매수 막힘이 이어진다.** 그동안 '반등 때 줄이기' 알림은 '줄이기 확인 불가'로 나온다(midterm-1104 A: 그날은 다음 '기한' 점검으로 넘어감).
- **오늘 23:20 개장 전 점검**: 줄이기 알림(0-3)은 오늘 아침 코어 E 2.0154(분할 전 자료)를 써서 영향이 없다. 급락 경보(0-2)는 키움 시세의 전일 종가(base_close_pric)를 분할에 맞춰 줄였는지에 달렸다 — **확인 필요**. 맞추지 않았다면 "SOXX 약 −68%" 거짓 경보 푸시가 1건 갈 수 있다(표시 전용, 매도 신호 아님).

## 근거 (파일:행)
- 분할 방지선: portfolio_exposure.py 49~53행(SPLIT_GUARD 0.5/2.0), 230~239행(종가 비율 ≤ 0.5면 SPLIT_GUARD 표시), 290~300행(표시가 있으면 volatility_available = False).
- E 계산: portfolio_exposure.py 324~328행 `E = max(N, V)`, 둘 중 하나라도 없으면 None. 1386~1388행 V 없음 → FAIL_CLOSED exposure_or_equity_or_v_unavailable. band: 343~352행(N 1.75는 1.85 미만이라 UNAVAILABLE).
- 지표·R-REC1: auto_core_bars.py 28~36행·153~166행(3배 근처 비율 = SPLIT_SUSPECTED) → auto_core_decide.py 637~638행 예외 "분할 의심 — 공식 분할 기록 필요", 그 종목 지표는 '모름'.
- 분할 기록 파일: workspace/outputs/regular-session-closes/corporate-actions.json(git 밖, 10/02 Cowork 작성, MVLL 1건뿐). corporate_actions.py 10~11행 "기록은 Cowork만, 공식 발행사 자료 + 키움 수정주가 표지로".
- 11/03 선례: 코어 fail-closed 날에도 decision.json에 E가 있었다(그날 원인은 가격 없음, V는 있었음). 이번은 V가 없어 E 자체가 없다.

## 막는 방법 (CLAUDE.md 범위 안)
1. **사장이 할 일(내일 06:00~07:40 KST, Cowork)**: Cowork에 "SOXX 3:1 분할 기록 추가해줘"라고 입력. Cowork가 iShares 공식 공지(Form 497)와 키움 usa06012 일봉의 수정주가 표지(dt 20261105, upd_rt 약 −66.667)를 확인해 corporate-actions.json에 MVLL과 같은 형식으로 1건 더한다. 키움 표지는 11/05 정규장이 끝난 뒤(06:00 KST 이후)에야 나온다. 이 사장실 스레드는 docs/claude 밖을 쓰지 않고, 키움 조회도 사장이 그 자리에서 직접 요청할 때만 할 수 있다.
2. 기록이 07:45 전에 들어가면 그날 코어는 정상 계산한다. 늦으면 그날 하루 E 없음 → 다음 날 정상.
3. 오늘 23:20 거짓 경보: 지금 지시문을 바꿀 시간은 없다(예약 변경 승인 절차 필요). 경보가 "SOXX 약 −67~68%"면 분할 때문이니 무시하면 된다.

결론을 바꿀 조건: 키움 일봉이 과거 종가를 수정주가로 다시 내려 저장된 종가 파일 자체가 바뀌는 경우. 이때는 regular_session_close_history.py 186행이 수정 표지 행을 거부해 required_price_missing(11/03과 같은 fail-closed)이 된다. 역시 E가 낮게 읽히지는 않는다.
