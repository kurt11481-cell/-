---
id: core-failclose-proposal-2026-11-02
title: "자동 코어 매수 쪽 fail-open 2곳 막기 — K3 수정안 (C-1 잔여·C-2)"
date: 2026-11-02
status: "제안 — 사장 승인 전. 코드·설정·예약 변경 없음"
source: "docs/claude/code-review-core-2026-11-01.md C-1·C-2, coreinput2 병합 db56303(2026-11-01 21:34 KST)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음. 두 수정 모두 매수를 더 막는 쪽(fail-closed)만"
---

## 한 줄 결론
자동 코어가 입력을 못 읽었는데도 매수를 허용하는 길이 2곳 남아 있다. 둘 다 "모르면 매수 막기"로 바꾼다. 매도 쪽은 건드리지 않는다.

## C-1 잔여: 회복 관문 문서의 EV3 줄을 못 읽으면 관문이 열림
- 이미 막힌 부분: coreinput2 병합으로 문서가 **없거나 커밋 안 됐으면** `CORE_INPUT_MISSING`·`CORE_INPUT_UNCOMMITTED`로 매수가 막힌다(auto_core_inputs.py 208~251행 `core_input_guard`).
- 남은 부분: 문서는 있고 커밋도 됐지만 EV3 줄 형식이 바뀐 경우다. `ev3_dates`(auto_core_rules.py 733~734행)가 엄격한 정규식 `EV3_LINE`(69행, `^- 이벤트 YYYY-MM-DD(EV`)만 센다. 그래서 띄어쓰기 하나만 달라져도(예: `- 이벤트 2026-10-08 (EV3`) 날짜가 조용히 0개가 된다. 그러면 R-REC1이 "충격 사건 없음"으로 보고 관문을 연다(decide 687행 `ev3=rules.ev3_dates(recovery_text)`).
- 지금 문서는 정상이다. 71행이 엄격한 형식에 맞고, EV3 날짜는 2026-10-08 1개다.
- 수정(안): 느슨한 패턴(`이벤트` + 날짜 + `EV3`가 한 줄에 있는 목록 줄)으로 센 수가 엄격한 패턴으로 센 수보다 많으면, 사유 `CORE_INPUT_PARSE:EV3`를 더해 매수를 막는다. 사유는 `core_input_guard`와 같은 길로 보낸다(매도 판정에는 들어가지 않음).

## C-2: 보유 종목인데 S7 비중이 없으면 비중 0으로 보고 매수량을 계산
- auto_core_tickets.py 1136~1138행: `current = ctx["weights"].get(symbol, 0)`. weights는 S7 검토 positions에서 비중이 있는 것만 담는다(auto_core_decide.py 1116행).
- 보유(`held`)인데 비중이 빠지면, 이미 가진 양을 0으로 보고 목표까지 전부 더 사는 수량이 나온다(실제보다 큰 매수).
- 실제로 이 길에 닿는지는 **확인 필요**다. 그 전에 REQ·정책 등록·S7 목표 검사에서 걸릴 수 있다. 다만 10/30에 "보유 종목이 S7 범위 밖"인 일이 실제로 있었다(s7-hold-gap-2026-10-30.md).
- 수정(안): `held`이고 weights에 그 종목이 없으면 `CURRENT_WEIGHT_MISSING`으로 그 매수만 막는다. 첫 매수(`held` 아님)는 지금처럼 0에서 시작한다.

## 경로
- 바꿀 파일은 auto_core_rules.py 또는 auto_core_inputs.py, auto_core_tickets.py, 그리고 test_auto_core*.py다. 모두 권한 경로(authority-paths.txt)지만 tools/는 아니다. 그래서 **개발 큐 authority 작업**(coreinput2와 같은 길)으로 간다. Builder Opus → Judge → NEEDS_APPROVAL → 사장 PowerShell `.\tools\dev-merge.ps1 core-failclose -ApproveAuthority`.
- 사장실 한 줄이나 실행 스레드는 필요 없다. 이 스레드가 지시문과 큐 파일을 올린다. 개발 큐 authority 작업은 사용자 결정 기록이 있어야 올릴 수 있으므로(tools/dev_pipeline/README.md 44행), 승인 카드를 받은 뒤에 올린다.
- 되돌리기: 커밋 1개 revert.

## 영향
- 두 수정 모두 매수를 더 막기만 한다. 매도표·매도 판정·수량 권한은 그대로다.
- 정상 날에는 변화가 없어야 한다. 지금 문서 형식과 지금 보유에서는 새 사유가 나오지 않을 것이다(Builder가 시험으로 확인).

## 범위 밖
- C-3(거래소를 NASDAQ로 가정, decide 598~601행)과 C-4(일지 기록 뒤 실패 반복)는 따로 다룬다.

## 정정 (2026-11-02 13:2x KST, 승인 직후 지시문 쓰며 확인)
- "매도 쪽은 건드리지 않는다"는 완전히 정확하지 않다. C-1 사유를 `core_input_guard` 길로 보내면, coreinput2와 같이 그날 **재배치 후보(redeploy_candidate)도 빠진다**. 그래서 그날 매도표의 후회 열·단계·수량이 후보 없는 날처럼 계산되고, 매도표가 안 나올 수도 있다(coreinput2 공개 사항과 같음, auto_core_inputs.py 214~217행 docstring). 매도 판정 규칙 자체는 바뀌지 않는다.
- 이 효과는 EV3 줄 형식이 깨진 날에만 생긴다. 지금 문서에서는 생기지 않는다.
- C-2로 한 종목 매수를 막을 때 재배치 후보가 달라지는지는 Builder가 확인해 보고한다(확인 필요).

## 사장 결정 기록 (2026-11-02)
- 카드: cmsg_0137MRzn9nuDvvQmVxm6WeX9EMzs2Ubs695FXidpAVLkPf (이 스레드가 이 수정안 core-failclose-proposal-2026-11-02에 대해 올린 카드, 질문 "자동 코어 매수 쪽 fail-open 2곳을 막을까요?")
- 고른 항목: "승인, 개발 큐에 올리기" (option_index 0)
- 누른 계정: user_01KuMGKfZu1SBYxtMmg4vAiH (프로젝트 소유자 = 사장)
- 시각: 2026-11-02 13:16:01 KST (harness wake 원문 기준)
- 범위: 이 수정안 1건, 2026-11-02 하루, 1회. 개발 큐 authority 작업 core-failclose. 병합은 별도 사장 결정 + 사장 PowerShell -ApproveAuthority. 위 정정은 병합 결정 전에 사장에게 알린다.
