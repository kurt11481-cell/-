---
id: ic-record-gaps-1118
title: 통합 점검 기록 어긋남 3건 원인과 재발 방지 안
date: 2026-11-18
status: 완료 — 2절 적용 2026-11-18 12:55 KST(비서실), 첫 실행 11/19 06:40 확인(대시보드 ① = 코어, compare SAME 8/8)
authority: order_authority=false · quantity_authority=none
---

# 통합 점검 기록 어긋남 3건 — 원인과 재발 방지 안

부딪히는 결정(지침 3절): **earn-na**(active-decisions 197행 '확인 못 함은 금지 유지') · **ic-rules-1103**(통합 점검 규칙 개정 절차) · **2026-10-09 승인 묶음**(200행 '규칙 파일을 바꾸려면 지시문 해시도 사용자 승인으로 함께'). 지난 연구 기록은 고치지 않는다.

출처: API 시범 1 채점 docs/claude/llm-iccheck-score.md 4절(11/13 F4 · 11/17 F2 · 11/17 F3).

## 결론

| # | 어긋남 | 원인 | 지금 영향 | 안 |
|---|---|---|---|---|
| 1 | 11/13 PLTR ③ '카드 미수락 표기 확인 필요' | 카드 문서 본문에 수락 전 문구가 남아 있음 | 없음(그날만, 11/14~18 재발 0) | 지금은 그대로, 다음 PLTR 카드 갱신 때 같이 고침 |
| 2 | ① 칸 '통과 (일정 미확인)' | 규칙에 '확인 못 함' 표기 줄이 없음 → 코어 판정과 화면이 다름 | 없음(② 칸에서 모두 막힘). 3배 줄인 뒤 ②가 풀리면 화면은 '통과', 코어는 '막힘'으로 갈라짐 | **수정 권장 — 사장 결정 필요** |
| 3 | R5 기준일 SOXL 10/01 · BE·LITE 10/29 | 오류 아님 — 코어 규칙대로 '처음 대조된 날' | 없음 | 기록만(작은 정의 차이 1개 공개) |

## 1. PLTR '카드 미수락' 꼬리표 (11/13 F4)

- 규칙은 맞다: 명단 파일 cardStatus가 '수락'으로 시작하면 ③을 판정한다(규칙 파일 v3.12.15 48행). PLTR cardStatus = '수락(2026-10-17, 수락 카드 재사용 — 2026-11-07 자동 편입)'(watchlist-registry.json).
- 원인: 통합 점검이 읽는 카드 3절(문서 읽기 ⓓ, 규칙 11행)의 **watch-card-PLTR-2026-11-03.md 66행 A행 칸에 '— 카드 미수락'** 이 남아 있다. v2 초안(11/03)에 쓴 문구를 11/04 09:48 KST 수락(active-decisions 134행) 뒤에 고치지 않았다. 모델이 두 표기가 다르자 '확인 필요'를 붙였다.
- 지금 고치지 않는 이유: 카드 등록부(card-evidence-registry.json PLTR)의 section_sha256이 **문서 전체(H1 절)** 해시다(auto_core_inputs.py 85·174~177행). 66행만 고쳐도 hash_ok가 깨져 코어가 PLTR 카드를 못 쓰게 된다 → 등록부 해시 갱신까지 한 번에 해야 하고, 그건 카드 재수락 세션 일이다.
- 안: **NO_CHANGE(지금)** + 다음 PLTR 카드 갱신(4분기 실적 뒤, valid_until 2027-02-01 전) 때 66행 '카드 미수락'을 지우고 등록부 해시를 같이 갱신한다. 같은 꼬리표가 남은 다른 수락 카드는 없다(watch-card-*·holding-card-* grep: CRWD는 실제 미수락, PLTR v1은 대체됨).
- 바뀔 조건: 11/19 이후 기록에 같은 꼬리표가 다시 나오면 2절 수정에 '카드 본문 수락 표기보다 cardStatus 우선' 한 줄을 묶는다.

## 2. ① 칸 '통과 (일정 미확인)' (11/17 F2) — 결정 필요

### 원인
- 결정 earn-na(197행): '확인된 미공지'만 금지 구간이 아니고, **확인 못 함은 금지 유지**.
- 코어는 그대로 막고 있다: 연구 기록 earnings에 그 종목 항목이 없으면 `EARNINGS_DATE_UNVERIFIED`로 막음(portfolio_exposure.py 1075~1091행, fail closed).
- 규칙 파일 133행은 '미공지만으로는 신규 매수를 막지 않는다'만 있고, IR 목록이 비거나 열기 실패로 **확인 못 한 경우 ① 칸에 무엇을 쓰는지 정한 줄이 없다**(실적 단서 경우만 '확인 필요… ① 막힘'이 있음). 그래서 모델이 '일정 미확인'을 미공지처럼 '통과'로 적는다.
- 채점은 11/17 LITE·PLTR 2건을 잡았지만 같은 모양이 더 있다(연구 기록 earnings 항목 없음 + ① '통과'):
  - 11/14 BE·LITE · 11/17 BE·MU·LITE·PLTR · 11/18 BE·MU·LITE·PWR·PLTR.
- 덧붙여 **PLTR·CRWD는 earnings-anchors.json에 없다**(있는 것: PWR·BE·DELL·LITE·MRVL·MU·NBIS). 표 규칙상 이 두 종목은 미공지를 확인해도 finalize가 빼서 VERIFIED 전까지 늘 막힌다(표 maintenance 줄이 예고한 동작).

### 안 (권장 A)
- **A. finalize가 ① 칸을 코어와 같은 뜻으로 덮어씀**: 4단계 finalize에서 최종 earnings(기준표 창 검사 뒤)로 ① 칸을 다시 씀 — VERIFIED면 금지 구간 계산 그대로, NOT_ANNOUNCED가 남았으면 '통과 (미공지 확인)', 항목이 없거나 빠졌으면 **'막힘 — 실적 일정 확인 못 함(코어와 같음, 매수만 막음)'**. 모델 문구에 기대지 않아 재발이 없다. 규칙 파일 133행에도 같은 뜻 한 줄.
- B. 규칙 파일 133행에 문장만 추가 — 싸지만 모델이 또 놓칠 수 있다.
- C. 그대로(NO_CHANGE) — 코어는 맞게 막으므로 실제 주문표 영향은 없다. 다만 화면과 코어가 다른 상태가 남는다(사장 지시 11/03 '기록과 다르거나 이상한 곳이 있으면 안 된다').
- 별건(같이 묶지 않음): PLTR·CRWD 기준일을 earnings-anchors.json에 SEC 원문으로 추가 — 코어 입력을 넓히는 쪽이라 따로 제안.

### 절차(A를 고르면)
1. 초안: 규칙 파일 v3.12.16 + 로더 finalize 몇 줄(docs/claude/scheduled-prompts/pending-ic-earnlabel-1118/).
2. H1 시험: 11/14·17·18 실기록 복사본으로 옛·새 비교(기대 차이 = 위 11건의 ① 칸만 '막힘'으로, 나머지 0). 대시보드 쓰기가 바뀌므로 독립 검토 1회(지침 4절 ④).
3. 승인: 사장 직접 입력 `예약 작업 변경 승인: 보유·관심 종목 통합 점검`(지시문 sha256·diff·일정·모델·폴더·권한 불변·되돌리는 법 첨부) → 비서실 교체 → 첫 실행 확인.
- 점검 약화 아님(더 막는 쪽, 표시만). 코어·정책·카드 등록부 변경 없음.

### 연결표
| 자료 | 읽는 점검 | 바뀌는 행동 | 끊김 알림 |
|---|---|---|---|
| 연구 기록 earnings(finalize 뒤) | 통합 점검 finalize ① 칸 | 대시보드·비서실 매수 요건 ① 표시가 코어와 같아짐 | finalize 실패는 기존 푸시(연결) |
| 코어 earnings_blackout | 07:45 코어 decide | 변경 없음(이미 막음) | 기존(연결) |

## 3. R5 기준일 차이 (11/17 F3) — 오류 아님

- 근거 원문: 대조 원장 stock-strategy-system/reconciliation_ledger.jsonl **rev31(as_of 10/29, 2026-10-30 06:15 KST 적용)** 에서 BE 28주·LITE 9주가 처음 들어오고 MVLL·NBIS가 빠짐. 그 전 rev30(as_of 10/20)에는 BE·LITE가 없다.
- 코어 규칙: 기준일 = max(S7 적용일 10/01, 지금 이어지는 보유의 첫 대조일)(portfolio_exposure.py 949~964행). SOXL은 10/01 전부터 보유 → 10/01, BE·LITE → 10/29. S7 파일 peak_reviews basis_date가 그대로 그렇고, 통합 점검은 규칙 101행대로 그 값을 따랐다.
- 작은 정의 차이(공개): 규칙 101행 대체 문구는 '첫 매수 체결일', 코어는 '첫 대조일'. 실제 매수 체결일은 confirmed_trades에 BE·LITE 매수 기록이 없어 **확인 필요**(10/21~10/29 사이, 대조 보류 기간). 영향 점검(종가 기록): LITE 고점은 10/29 $920.14라 같음. BE는 체결일이 10/28 이전이면 P가 $227.97~$238.77로 올라 선이 $159.58~$167.14가 되지만 11/17 종가 $177.28은 여전히 선 위 — 지금 판정은 같다.
- 안: NO_CHANGE. 바뀔 조건: BE 종가가 $167.14 아래로 가면 두 정의의 판정이 갈릴 수 있으니 그때 다시 본다.

## 4. 2절 진행 — 사장 결정 카드 '진행 (finalize가 덮어쓰기)' 2026-11-18 11:26:12 KST

### 설계 정정(같은 목표, 위치만 바뀜)
대시보드 기록은 4단계(연구 기록·finalize)보다 **먼저** 쓰인다. 그래서 finalize 안에서 고치면 연구 기록 사본만 바뀌고 대시보드는 그대로다. finalize는 손대지 않고, finalize **바로 뒤에** (6) '① 칸 맞춤' 한 단계를 더했다. finalize가 남긴 최종 연구 기록을 읽어 대시보드 buyReq ① 칸만 update로 고친다. 연구 기록·코어 입력은 바꾸지 않는다(K3 대상 아님).

### 바뀌는 것
| 파일 | 지금 | 바꿀 판 |
|---|---|---|
| 규칙 파일 | v3.12.15 (6d6191f0…) | integrated-check-prompt-v3.12.16-2026-11-18.txt (LF sha256 bcee847ac929aaadab01230f9e07500c22f58b4fd45366fd47926533d210f825, 134,011 B) — 1행 판 설명 + 133행 한 문장(확인 못 함 → ① "막힘 — 실적 일정 확인 못 함(코어와 같음, 매수만 막음)") |
| 예약 지시문(로더) | v3.12.15-L+R2 (8beb588e7201ef839311926a027d8e15a0e6ceb0db3dd187e552f93e9fb60011, 34,640 B) | v3.12.16-L+R2 (**598628aaf94693bc7277579ef1d55a7a808e24bfb28087831e3b3704feeedfca**, 39,174 B) — 규칙 경로·해시, 4단계 (6), fix1 구간(sha256 8f64e6d3…), RESUME 4.·② 두 줄 |
- 그대로: build(410027…)·finalize(a6bcd6…) 본문, 연구 기록 형식·writer 칸(v3.12.15-L+R2 그대로), 알림, 코어·정책·카드 등록부. **일정(화~토 06:40)·모델·폴더·권한 모드 불변.**
- 쓰기 범위: 기존 예외 ①(대시보드 runs 같은 날 문서) 안에서 buyReq 한 칸 update뿐 — 넓어지지 않음. 점검 약화 없음(매수를 더 막는 쪽 표시).
- 여기서 맞추지 않는 것: VERIFIED로 지금 금지 구간 안인 종목(133행대로 판정 단계에서 막힘), finalize를 통과한 NOT_ANNOUNCED를 코어가 다른 검사로 막는 드문 경우, 연구 기록 안 integrated_check_run 사본(코어 비교는 이미 B5 '규칙·코드 우선'으로 분류).
- 남은 위험: 로더 39,174 B(지금보다 +4.5 KB) — 예약 지시문 길이 한도는 확인 필요. 맥락 사용 약 +2천 토큰 추정(11/11 실측 여유 약 3만).

### 시험·검토
- H1(pending-ic-earnlabel-1118/h1_test.py, 결과 h1_result.txt): **43/43 PASS**. 되돌리면 옛 판과 바이트 일치, 해시 3구간 MATCH, 11/13·14·17·18 실기록에서 고칠 종목 = 코어 비교(compare.json P_EARN_R1_UNVERIFIED_IS_BLACKOUT) 17건과 같음, 두 번 돌려도 같음, 나쁜 입력 6가지 fail-closed.
- 독립 검토(review-report.md): PASS-WITH-CONDITIONS(필수 2·권장 4) → 6개 모두 반영 → 재확인 **PASS**. 경미 지적 (a) 문구 '오래됨'→'지남·금지 구간일 수 있음', (d) get 파일 경로 명시도 반영.

### 적용 순서
1. 이 문서·규칙 파일·pending-ic-earnlabel-1118/ 커밋(_pending 목록).
2. 사장 직접 입력(이 스레드): `예약 작업 변경 승인: 보유·관심 종목 통합 점검`
3. 비서실이 예약 지시문을 pending-ic-earnlabel-1118/integrated-check-daily.txt로 교체·재서명 → 보관본(scheduled-prompts/integrated-check-daily.txt)·README 갱신.
4. 첫 실행(다음 화~토 06:40) 확인: 연구 기록 RR OK, 보고 끝 '① 칸 맞춤' 줄, 대시보드 ① 칸 = 코어 판정, core 칸 보존.
- **되돌리기**: pending-ic-earnlabel-1118/integrated-check-daily-v3.12.15.txt(8beb588e…)로 교체(규칙 파일 v3.12.15는 저장소에 그대로 있음).

### 승인 기록
- 2026-11-18 11:38:04 KST 사장 직접 입력(이 스레드): "예약 작업 변경 승인: 보유·관심 종목 통합 점검" — 바로 앞 제안(로더 598628aa…, 규칙 v3.12.16 bcee847a…) 1건, 같은 날, 1회.
- 다음: 사장이 회사PC 비서실(Cowork) 대화에 교체 한 줄 입력 + PC 앱 승인 창 → 교체 뒤 get_trigger 본문 해시 대조 → 첫 실행 확인.
- 2026-11-18 12:55 KST 적용(비서실): 사장 직접 지시 12:42 "trig_01YWzNq847nJfNgDUnnukBqP 지시문을 docs/claude/scheduled-prompts/pending-ic-earnlabel-1118/integrated-check-daily.txt로 교체, 이름·일정·모델·폴더 그대로" → update_trigger 응답 "prompt re-signed by 금동한"(updated_at 2026-11-18T03:55:24Z). 넣은 본문 598628aa…(39,174 B). 이름·일정·모델·폴더 2개·자동 승인 불변. 보관본 scheduled-prompts/integrated-check-daily.txt = 598628aa…, build·finalize·fix1 MATCH. 응답 본문 바이트 해시 대조는 못 함(확인 필요) — 11/19 06:40 첫 실행의 1단계 MATCH(bcee847a)·fix1 MATCH·(6) 결과 줄로 확인.
- 2026-11-18 13:0x KST 해시 대조(사장실 회사PC 스레드): get_trigger 응답 prompt 본문 39,174 B·CR 0·sha256 598628aaf94693bc7277579ef1d55a7a808e24bfb28087831e3b3704feeedfca = pending 파일과 바이트 일치. 일정 CRON_TZ=Asia/Seoul 40 6 * * 2-6·모델 claude-sonnet-5-5·폴더 2개·권한 auto·켜짐 불변. 위 '확인 필요' 풀림. 남은 확인 = 11/19 06:40 첫 실행.

### 첫 실행 확인 (2026-11-19 08:0x KST)
- 11/19 06:40 실행: 연구 기록 research-records/2026-11-19 있음(written_at 06:51:52 KST, writer 'v3.12.15-L+R2' — build 해시를 지키려 일부러 그대로 둔 칸, 정상). earnings = DELL·CRWD VERIFIED.
- 규칙 133행 문장이 판정 단계에서 바로 먹혔다: BE·LITE·MU·PWR·PLTR ① = "막힘 — 실적 일정 확인 못 함(코어와 같음, 매수만 막음)", DELL·CRWD = 통과(금지 구간 시작 전), SOXL = 지수 ETF 통과.
- 대시보드 runs 2026-11-19(version 1) ① 칸이 위와 같음 → (6) 고칠 칸 0, update 없음(version 1 그대로). 08:00 시점 core 칸은 아직 없음(08:50 알림이 씀).
- 07:45 코어 비교 compare.json buyReq:*:1 8칸 모두 SAME — 그 전 4일의 B5 P_EARN_R1_UNVERIFIED_IS_BLACKOUT 3~5건 → 0건.
- (6) 단계 보고 원문 줄은 읽지 않음(고칠 칸이 0이라 결과는 같음). 남은 것 없음 — 완료.
