# Trading_Skill 자료 검토: 판단 기초자료 활용 여부 (2026-09-30)

- 대상 폴더: `E:\사업\##금동한\chatgpt_종목분석결과\Trading_Skill` (6개 파일)
- 범위: 사용자가 넣은 트레이딩 지식 자료를 투자_V2 판단 기초자료(Knowledge·정책·규칙)로 쓸 수 있는지 검토. 주장 추출 → 사실/해석/가설 분리 → 기존 Knowledge·repo 규칙과 중복·신규 확인 → 적용 위치 제안.
- 방법: 읽기 전용. 원본 파일·코드·정책·Knowledge는 수정하지 않았다. 대조 대상은 프로젝트 Knowledge 3종과 `manage-us-stock-strategy/references/technical-strategy.md`, `trade-timing-validation.md`, `candidate-selection.md`, `evaluation-harness.md`, `scripts/build_market_snapshot.py`, `docs/claude/system-review-p4-roadmap-2026-09-30.md`.
- 분류: K0 (문서만, 런타임 변경 없음)
- 상태: 검토안. 채택 여부는 사용자 결정. 2026-09-30 사용자 지시 반영: 시장 환경 판단은 기존 지침대로 SAVE(saveticker.com) 활용안 검토(§7), `Jay_Swing_AI.pdf`는 외부 자료(사용자 프로젝트 아님). **시스템 반영(2026-09-30, 사용자 결정):** P4 로드맵 §4 S5 "시장 환경 메모"와 G3 기록 항목, §5 대기 5건, 부록 B 첫 메시지, §9 기록.
- 표기: "확인 필요"는 원문·출처로 확인하지 못한 항목.

---

## 0. 결론

1. **6건 모두 지금 Knowledge·정책으로 넣지 않는다.** 증거 등급은 전부 D(가설·외부 주장) 수준이고 Production 규칙 근거가 아니다(RESEARCH_FINDING != PRODUCTION_POLICY).
2. **스윙 매매 원칙은 대부분 이미 있다.** `trade-timing-validation.md`(10/20EMA 레짐, 눌림·돌파 셋업, RVOL 확인, ATR 확장 제한, R 기반 익절, 위험 기반 수량)와 Stock Protocol §21~22가 "공통 분모 9개" 중 6개를 덮는다.
3. **새로 얻을 것은 두 가지뿐이다.**
   - A. **시장 환경(레짐) 판단 공백.** 시스템에는 종목 단위 EMA 레짐만 있고, 지수·breadth·신용 스프레드·변동성 기반 시장 환경 판단이 없다(`build_market_snapshot.py`가 "market breadth, credit spreads … require separate sourced checks"로 비워 둠). 자료 4건이 같은 방향을 가리킨다.
   - B. **검증 방법.** JAY 스윙 AI의 "같은 후보군 무작위 뽑기 대비 채점"은 현재 repo 평가 체계에 없는 비교 기준이다.
4. **지금 할 일은 코드가 아니다.** P4 로드맵상 S8 전 거버넌스 확장 금지이고 현재 우선순위는 보유종목 판단 루프다. A는 카드 파일럿 #2에 SAVE 기반 "시장 환경 메모"를 참고로 적는 것까지 한다. 입력은 카드 날 수동("장 전 주요 뉴스" 텍스트 또는 PDF)이고, 없으면 "미입수"로 진행한다(§7). 수치 레짐 규칙화는 S8 이후 Cold Path 연구로 미룬다.

---

## 1. 자료별 판정

| 파일 | 성격 | 핵심 주장 | 시점성 | 등급 | 판정 |
|---|---|---|---|---|---|
| `Trading_master_skill.txt` | 요약 메모(작성자 확인 필요). 오닐·와인스타인·쿨라매기·제프 선·본데 공통점 9개 | 시장 상승 시만, 리더(RS)만, 정돈된 조정 후 돌파, 사전 소액 손절·물타기 금지, 거래량 확인, 추격 금지, 위험 기반 수량·집중, MA 이탈까지 보유, 기록·부진 시 축소 | 원칙(시점 무관) | D | 체크리스트 참고. 6개 기존 규칙과 중복, 3개(시장·RS·부진 시 축소)만 신규 후보 |
| `The Complete Trader's Guide …txt` | 링크 1줄(Jeff Sun Substack) | 수치 규칙: 50MA 대비 ATR% 배수 4배 초과 시 진입 금지, 7배 이상 부분 익절, 당일 저가 거리 ATR 60% 이내, RVOL 확인, ADR%로 수량 조절, 하루 신규 3개 상한, breadth(20MA 위 비율·신고/신저·RSP vs SPY) | 원칙 + 운용 수치 | D | 수치 후보 목록으로만 보관. 수치는 요약 도구 추출이라 **원문 대조 확인 필요**. 저자 성과 주장은 검증 안 됨 |
| `Jay_매수타이밍.pdf` | 커뮤니티 글(에펨코리아, 백곰아재, 2026-08-15). TSM·GLW·HPE 차트 | 진입 3유형: ①수평선 돌파 또는 되돌림 재지지, ②상승 후 플랫 구간 하단 매수, ③강한 종목은 다음 날 장 초반 4EMA(4~6EMA) 테스트 매수 | 예시 차트는 과거 시점 | D(커뮤니티 = 가설) | ①은 기존 돌파·눌림 셋업과 같음. ②는 정의 없음. ③은 장중 데이터·주문 전제라 완료 봉 기준 시스템과 맞지 않음. 채택 안 함 |
| `Jay_Swing_AI.pdf` | 외부 개인 프로젝트 설명 10쪽(사용자 프로젝트 아님, 아이디어 참고용) | 전 종목 일봉 10년, 규칙 필터(RS 상위 30%, 10일 고점 돌파, 당일 저가 손절) 후보 9,163건. 성공 = 20거래일 안에 손절 전 +3R. LightGBM 순위가 무작위 200회 중 최고 96회 승(합격선 150). 단순 RS 순위가 140회로 가장 나음. 연도 간 차이(0.5R 이상)가 같은 해 안 선택법 차이(0.04~0.08R)보다 훨씬 큼. 후보 3건 초과인 날 −0.10R, 이하 +0.06R | 2017~2025.6 백테스트, 2025.8 이후 봉인 | D(외부 백테스트, 재현 안 됨) | **방법론 참고 가치 높음.** 결과는 "ML 순위가 무작위를 못 이겼다"는 반증 근거로만 사용 |
| `포트폴리오의_퀄리티를_높이는법.pdf` | BTIG 기술전략 노트 "Deep in the Tranches"(Jonathan Krinsky, 2026-09-20) 10쪽 + 한국어 요약 2쪽 | NYSE 하락 거래량 비중 54%, SPX 고점 −3%, RTY 52주 고점 −5% 초과 동시 발생 12번째(1996~). 과거 11건 RTY 40일 평균 −2.16%·중앙값 −2.10%·상승 비율 45%. CCC 스프레드 9% 초과(2023 이후 최대), CCC−B 6% 초과. RTY/SPX 비율 6월 말 이후 −8%. 소비재 고품질 우위 → "품질 상향". 풋콜 10일 평균 연중 저점권 | 2026-09-18 데이터. **현재 값 재확인 필요** | 출처 있는 기관 리포트. 사건 연구는 n=11로 작음 | 시장 환경 지표 후보 목록으로 보관. 결론(소형·저품질 축소)은 가설 |
| `VIX관련 자료.pdf` | 뉴스레터 번역(LSEG·Vixcentral·GS 차트) + 커뮤니티 주석 차트 9쪽 | VIX 상승·VVIX 매수세·내재 상관(COR3M) 상승, VIX 기간구조는 콘탱고 유지(질서 있는 상승), CTA 단기 임계값 이탈로 VIX "적정가" 25 주장, SPX 1·2·3차 선, GEX 패널, SpotGamma HIRO | 2026-09-10~11 스냅샷. **이미 지난 자료** | D(요약·주석 혼합, 일부 선 정의 없음) | 현재 증거로 사용 불가. 시장 환경 개념 목록(기간구조·VVIX·상관·풋콜)만 참고 |

원본 내부 문제(그대로 쓰면 안 되는 이유):

- BTIG 3쪽 표 제목은 "Downside Volume (30 DMA)"인데 본문은 "20 DMA"다. 원본 안에서 불일치.
- BTIG PDF 11~12쪽의 시나리오 확률(50% / 30% / 20%)은 BTIG 원문 1~10쪽에 없다. 요약 과정에서 붙은 수치로 보이며 근거 확인 필요.
- VIX 자료 6~8쪽은 선 이름·기준(1차/2차/3차, 10.55/7.99/5.73 등) 정의가 없다. 8쪽 GEX 패널은 기초자산 확인 필요(SPOT 1072).
- JAY 스윙 AI의 수치는 자체 보고다. 코드·데이터·채점기를 보지 못했다.

---

## 2. 기존 규칙과 대조 (공통 분모 9개 기준)

| # | 주장 | 기존 위치 | 상태 |
|---|---|---|---|
| 1 | 시장이 오를 때만 산다 | 종목 단위 `aligned_downtrend` 신규 매수 거부만 있음. 지수·breadth·신용·변동성 판단 없음 | **공백** |
| 2 | 리더만, RS 먼저 | `candidate-selection.md`에 RS·리더십 필터 없음 | **공백**(신규매수 후보 단계) |
| 3 | 정돈된 조정 후 돌파 | 돌파·수용 셋업(20일 고점 종가 돌파 + 다음 세션 수용), Stock Protocol §18.1 "변동성 수축" | 있음 |
| 4 | 사전 손절, 작게, 물타기 금지 | 진입 전 R 정의, 손절 아래 물타기 금지(§22), 평단 최대손실 경계 | 있음 |
| 5 | 거래량 확인 | 재지지일 RVOL ≥1.0이며 테스트일의 1.2배 이상, 돌파는 승인된 RVOL 확인 | 있음 |
| 6 | 추격 금지 | "20EMA 대비 과도한 ATR 확장 금지"(임계값은 정책 정의) | 있음. Jeff Sun 4배 수치는 후보 |
| 7 | 위험 기반 수량, 소수 집중 | `shares = floor(capital × risk / abs(entry − stop))` + 집중·현금 상한 | 있음. 단 현재 `quantity_authority = none`이라 계산 참고만 |
| 8 | 구조 깨질 때까지 보유(MA 트레일링) | 10/20EMA 종가 트레일링 | 있음 |
| 9 | 기록, 안 될 때 사이즈 축소 | 기록은 S7b 결정 원장·채점기로 계획됨. 성과 연동 축소 규칙 없음 | 부분 |

판단 근거와 관계:

- 시스템 우선순위는 보유종목 ADD/HOLD/TRIM/EXIT다. 위 자료는 대부분 신규 스윙 진입용이라 현재 Hot Path에 직접 닿는 것은 #1(시장 환경)뿐이다.
- `technical-strategy.md` "Keep the active signal set small": 새 지표는 사전 등록한 하나씩 제거 시험과 여러 레짐 walk-forward 통과 전 비활성. ATR% 배수, 당일 저가 거리, RS 순위, breadth 지표 모두 이 절차 대상이다.

---

## 3. 쓸 만한 것

### A. 시장 환경(레짐) 공백

- 같은 방향 자료: 공통 분모 #1, JAY 스윙 AI("무엇을 고르느냐보다 언제 하느냐"), BTIG(breadth·신용), VIX 자료(변동성 구조), Jeff Sun(breadth·지수 ATR 확장).
- 주의: 모두 D등급이고, JAY 결과는 스윙 돌파 후보군 기준이라 보유종목 판단에 그대로 옮길 수 없다.
- 후보 지표(공개 데이터로 재현 가능한 것만, 값은 매번 원본 확인):
  - 지수 추세: SPX·NDX·RTY의 50/200일선 위치와 기울기
  - breadth: 20일선·50일선 위 종목 비율, 52주 신고/신저, RSP/SPY
  - 소형/대형: RTY/SPX(또는 IWM/SPY)
  - 신용: 하이일드·CCC OAS(공식 통계 원본 확인 필요)
  - 변동성: VIX 수준과 기간구조(콘탱고/백워데이션)
- 하지 않을 것: 새 엔진·새 상태·점수 합산. 지표 하나가 종목 판단을 자동으로 바꾸게 하지 않는다.

### B. 검증 방법 (JAY 스윙 AI)

- 이미 있는 것: 사전 등록(`portfolio-policy.md`), walk-forward(SOXL 백테스트), 증거 등급.
- 새로 참고할 것:
  1. **같은 후보군 무작위 기준선.** 고른 결과를 같은 날 같은 후보군에서 무작위로 뽑은 결과 200회와 비교하고 합격선을 미리 적는다.
  2. **봉인 구간.** 마지막 기간은 최종 한 번만 연다.
  3. **불합격을 불합격으로 기록.** 합격선 사후 조정 금지.
- 적용 위치 후보: 신규매수 후보 선정(candidate-selection)을 나중에 평가할 때. 보유종목 결정 채점(S7b)은 이미 "현금 + SPY 대비"로 정했으므로 바꾸지 않는다.
- 반증으로서 가치: 학습형 순위 모델이 무작위를 못 이겼고 단순 RS 순위가 더 나았다(자체 보고). 투자_V2에 ML 순위 모델을 추가할 근거가 없다는 쪽의 자료다.

---

## 4. 넣지 않을 것

- VIX·BTIG의 **현재 시장 판단**(VIX 25 적정가, RTY 40일 −2.1%, 시나리오 확률): 9월 중순 스냅샷이고 표본이 작다. 오늘 판단에 쓰려면 현재 값을 원본에서 다시 확인해야 한다.
- 커뮤니티 진입법 ③(장 초반 4EMA 테스트 매수): 장중 데이터와 주문 권한 전제. 현재 시스템은 완료 봉 기준, `order_authority = false`.
- Jeff Sun 수치(4배, 7배, 60%, 하루 3개): 개인 트레이더 경험칙. 검증 전 정책 임계값으로 쓰지 않는다.
- 오닐 7~8% 손절 등 고정 %: 기존 평단 최대손실 경계·기술적 손절 체계와 충돌할 수 있어 대체하지 않는다.

---

## 5. 적용 순서 제안 (로드맵과 맞춤)

| 순서 | 내용 | K | 시점 |
|---|---|---|---|
| 1 | 이 문서 보관(연구 후보 목록) | K0 | 지금 |
| 2 | 카드 파일럿 #2(S5)에 SAVE 기반 "시장 환경 메모"를 참고로 적는다(§7). 카드 날 수동 입력, 없으면 "미입수". 규칙 아님·EXTERNAL_REFERENCE 표시 | K0 | S5 (P4 반영됨) |
| 3 | 시장 환경 지표를 사전 등록 → walk-forward → 무작위 기준선 비교 | Cold Path 연구 | S8 이후 |
| 4 | RS·ATR 확장 수치를 신규매수 후보 선정 규칙 후보로 시험 | K2 이상 | 신규매수 흐름 재개 시 |

---

## 6. 확인 필요

- `Trading_master_skill.txt` 작성 주체. (`Jay_Swing_AI.pdf`는 외부 자료로 확인됨 → 채점기·후보 데이터 재사용 불가, 방법론 아이디어만 참고.)
- Jeff Sun Substack 원문 수치(WebFetch 요약으로만 확인).
- BTIG 표의 20DMA/30DMA 불일치.
- BTIG 요약본 시나리오 확률의 출처.
- 모든 시장 지표의 현재 값(2026-09-30 기준 재수집 전).

## 근거 파일

- 원본: `Trading_Skill/` 6개 파일
- 대조: 프로젝트 Knowledge `stock_analysis_protocol_v2_3.md` §18~22, `fund_manager_system_constitution_v1_2_1.md` §20~24
- repo: `manage-us-stock-strategy/references/technical-strategy.md`, `trade-timing-validation.md`, `candidate-selection.md`, `portfolio-policy.md`, `scripts/build_market_snapshot.py`(1232행), `docs/claude/system-review-p4-roadmap-2026-09-30.md` §3·§4

---

## 7. 시장 환경 판단: SAVE(saveticker.com) 활용안 (2026-09-30 추가)

### 7-1. SAVE가 무엇이고 기존 지침에서 어디에 있나

- SAVE(세이브티커)는 미국 증시 한국어 뉴스·시황 브리핑·리포트·경제 캘린더·알림 서비스다(운영 Fivelines, 오선의 미국 증시 라이브). 대부분 Reuters·Bloomberg·WSJ 등의 재서술이다.
- repo에는 이미 **SAVE Daily v0.1 파이프라인**이 있다: `manage-us-stock-strategy/scripts/save_daily_pipeline.py`(OFFLINE_REPLAY, 네트워크 금지), 규칙 `assets/save-daily-rules-v0.1.json`, 스키마 3종, 테스트 `test_save_daily_pipeline.py`.
  - SAVE Daily PDF → 이벤트 정규화 → 보유·도전자 종목, Root Thesis(`MARKET_VOLATILITY`, `BANK_CREDIT` 등) 연결 → "SAVE DAILY PORTFOLIO RADAR".
  - 권한 표기: `SAVE Authority: EXTERNAL_REFERENCE` — 외부 연구·이벤트 발견 출처, canonical 아님. 일정이 충돌하면 `일정 자동 사용: NO`.
- Kernel §5 기준: 매크로 수치 = 공식 통계, 가격 = 키움(없으면 외부 가격은 참고), 재서술·커뮤니티 = 가설. SAVE는 이 틀에서 **발견·맥락 출처**다.

### 7-2. 판정

- **SAVE로 할 수 있는 것(채택 권장):**
  1. 시장을 움직이는 이벤트·내러티브 파악(연준, 금리, 신용 스트레스, 에너지, 변동성 관련 뉴스) — 기존 파이프라인의 `MARKET_VOLATILITY`, `BANK_CREDIT`, `FED`, `MACRO` 이벤트.
  2. 다가오는 일정 위험(FOMC, CPI, 고용, 주요 실적) — 기존 `NEXT 48 HOURS` 칸.
- **SAVE로 하지 않을 것:**
  - 시장 환경 "판정"을 SAVE 단독으로 내리는 것. 판단을 바꾸는 주장은 원문 링크로 확인한다.
  - SAVE에 적힌 수치를 그대로 판단 근거로 쓰는 것. 매크로 수치는 공식 통계, 가격은 키움에서 확인한다.
  - breadth·신용 스프레드·VIX 기간구조 같은 수치형 레짐 측정. SAVE가 이런 지표를 제공하는지 확인하지 못했다(사이트 직접 조회 403, 확인 필요). 수치형 레짐은 §5의 S8 이후 연구로 둔다.
- 새 코드·새 엔진 없이 기존 파이프라인을 재사용하는 안이라 로드맵(S8 전 거버넌스 확장 금지)과 충돌하지 않는다(REUSE).

### 7-3. 카드 파일럿 #2(S5)에서 쓰는 방법 (K0, 수동) — P4 §4 S5에 반영됨

1. 카드를 쓰는 날에만 사용자가 SAVE 입력을 준다. 매일 받지 않는다.
   - SAVE "장 전 주요 뉴스" 글 텍스트를 붙여 넣거나,
   - SAVE Daily PDF가 있으면 연결 폴더 경로를 준다.
2. PDF면 Cowork가 VM에서 기존 파이프라인을 돌린다: `python3 manage-us-stock-strategy/scripts/save_daily_pipeline.py --source <PDF 경로> --expected-report-date <YYYY-MM-DD>`
   - 2026-09-30 VM에서 `test_save_daily_pipeline.py` 30건 OK(1건 skip). Windows Python은 `pypdf`가 없어 실패한다(`test-run-latest.md`).
   - 텍스트면 Cowork가 직접 읽고 시장 관련 항목만 고른다(연준, 금리, 물가·고용, 신용, 변동성, 에너지).
3. 머리말 "시장 환경" 1~2줄:
   - 시장 관련 상위 이벤트 1~3건(제목, 원문 링크 여부)
   - 48시간 안 주요 일정(공식 일정으로 확인 못 하면 "일정 확인 필요")
   - 라벨 `EXTERNAL_REFERENCE / 판단 규칙 아님`
4. **입력이 없으면** "시장 환경: SAVE 미입수"로 적고 카드는 그대로 쓴다(보조 경로 장애가 핵심 판단을 막지 않는다).
5. 메모가 종목 판단을 자동으로 바꾸지 않는다. 메모 때문에 판단을 바꿨다면 원문을 확인하고 이유를 적는다.
6. G3 판정 때 "메모가 판단에 쓰였는가"와 미입수 횟수를 기록하고, 카드 형식에 남길지 정한다.

### 7-4. 사용 전 확인 필요

- 규칙 파일의 보유 종목 목록이 8월 기준(`MRVL, MVLL, NBIS, SOXL`)이다. 현재 `portfolio_state.json` 보유는 `MVLL, NBIS, SOXL`이다. PDF 경로의 HOLDINGS IMPACT 칸만 영향을 받고, 시장 환경 메모(시장 성격 이벤트)에는 영향이 없다. 정리는 P4 §5 대기 항목(K1).
- SAVE에 공식 피드·API 제공 여부 문의(자동 수집의 선행 조건).
- saveticker.com 이용약관(개인 분석용 보관·자동 처리 허용 범위).

---

## 8. saveticker.com 뉴스 직접 모니터링 검토 (2026-09-30, 사용자 요청)

- 요청: PDF 대신 saveticker.com 뉴스를 직접 모니터링하는 대안.
- 확인 결과
  - 공식 API·RSS: 검색으로 찾지 못했다(확인 필요).
  - 자동 조회: `/`, `/news`, `/robots.txt` 모두 403. 사이트가 자동 조회를 막는다. 우회 조회는 하지 않는다.
  - 공개 제3자 도구 GitHub `destory1984/saveticker_filter`(MIT): Edge/Chrome 확장 + Python 알림 스크립트. 원문 요약 확인(WebFetch 요약 기준, 설치 전 원문 직접 대조 필요):
    - `manifest.json`: 권한 `storage, downloads, downloads.ui, alarms`, 호스트 `saveticker.com`, `127.0.0.1:18765`.
    - `hook.js`: 페이지의 fetch/XHR 응답 중 `/api/news/list`, `/api/news/top-stories`의 `news_list`를 가로챈다(자체 요청 없음).
    - **`content.js`: 사용자 로그인 쿠키(`credentials: "include"`)로 `/api/news/list`를 직접 호출하고 최대 30페이지를 0.5초 간격으로 넘긴다.** README의 "화면 응답만 관찰" 설명과 다르다.
    - `background.js`: 1분 주기 감시, 멈추면 탭 새로 고침, 로컬 `127.0.0.1:18765/ping` 보고, 일별 CSV(`time_kst, created_at, title, title_en, source, tickers, labels, url, id`) 저장. 외부 전송은 없음.
- 판정: **채택하지 않음(사용자 결정).**
  - 실제 동작이 사용자 계정으로 하는 비공개 API 자동 반복 조회라 약관 위반·계정 제한 위험이 있다.
  - 원시 뉴스 흐름은 잡음이 많아 시장 환경 메모에는 정리된 하루치 요약보다 효율이 낮다.
  - 운영 목표(자동화는 감지·표시·알림만, 복잡도 억제)와 제3자 코드 설치 위험에 비해 이득이 검증되지 않았다.
- 대신: 카드 날 수동 입력 + 미입수 허용(§7-3). 실시간 확인은 SAVE 앱 키워드·경제지표 알림을 사람이 본다. SAVE가 공식 피드를 제공하면 P4 §5 "SAVE 자동 수집"으로 다시 검토한다.
- 출처: [saveticker_filter](https://github.com/destory1984/saveticker_filter), [SAVE 앱](https://apps.apple.com/us/app/save-%ED%88%AC%EC%9E%90%EC%9D%98-%EB%AA%A8%EB%93%A0-%EC%86%8C%EC%8B%9D-%EC%9D%B4%EC%A0%9C-%ED%95%9C-%EA%B3%B3%EC%97%90%EC%84%9C/id6751139540)
