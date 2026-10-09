# SCN-27H1 비(非) AI-Capex 섹터 발굴: 사이버보안 · 바이오테크 · 정유 (2026-10-10 KST)

이 문서는 조사 결과이며 매매 권유가 아니다. 주문 가격과 수량은 넣지 않았다.
연결: 이 파일은 호출 세션의 SCN-27H1 discovery 종합 문서(`scn27h1-discovery-2026-10-10/`)가 읽는다. SCN-27H1 트리거 점검(`scn27h1-triggers.py`)은 이 조사에서 실행하지 않았다.

- **공식 수치**: 회사 8-K/6-K/10-Q/10-K와 FDA·EIA 자료를 썼다. 매출 YoY는 공시 원문 또는 SEC XBRL로 계산했다.
- **참고값 [Y]**: 시총, 주가, 52주 고점 대비, 3개월 수익률, EPS 컨센서스는 Yahoo Finance 2026-10-09 종가 기준이다.
  - **NTM P/E**: 컨센서스 FY EPS를 남은 개월 수로 가중한 근사치다.
  - **PEG**: NTM P/E ÷ 다음 회계연도 EPS 성장률(%).
  - **EV/매출**: EV ÷ NTM 매출 근사치.
- **거시 확인 [Y][R1][R3]**:
  - 10년물 금리 5.25%(10/9).
  - 유가: 10/9 선물은 WTI $91.5, 브렌트 $104.2다. 2026-09 현물 평균(EIA)은 WTI $97.31, 브렌트 $114.16으로 차이가 **$16.85**다.
  - 브렌트 약 $125라는 전제는 확인하지 못했다. 현물 기준과 시점이 다를 수 있다(확인 필요).

## 한눈 요약

| 섹터 | 최고 수혜 | 차순위 | 가장 저평가 | 혼잡 |
|---|---|---|---|---|
| 사이버보안 | **CRWD** | FTNT | **S** | CRWD, NET |
| 바이오테크 | **VRTX** | ARGX | **NBIX** (대안 ALNY) | RVMD, ROIV |
| 정유 | **VLO** | MPC | **DINO** (PBF는 함정이라 제외) | PBF, VLO |

---

## 1. 사이버보안

**(a) 2027-06까지 이익 경로**
1. **AI 위협이 보안 수요로 이어진다.**
   - CRWD: 순신규 ARR이 사상 최대인 $333M(+51%)였다. FY27 순신규 ARR 성장 가이던스를 630bp 올려 34%로 제시했다. 회사는 원인으로 "Mythos moment"를 들었다 [C1].
   - PANW: "AI가 보안을 CIO 최우선 과제로 올렸다"고 밝혔다 [C3].
2. **플랫폼화로 ARR·RPO가 늘고 있다.**
   - PANW: NGS ARR $9.10B(+63%, CyberArk 포함), RPO $21.2B(+34%), FY30 NGS ARR 목표 $20B [C3].
   - CRWD: Falcon Flex ARR $2.29B(+101%) [C1].
3. **장비 교체 주기가 진행 중이다.** FTNT 제품 매출 +52%, 빌링 +33% [C5].

**(b) 후보 표** (TENB $4.5B는 $5B 미만이라 제외)

| 티커 | 시총[Y] | 최근 분기 매출 YoY(공식) | 최신 가이던스(공식) | ~2027-06 촉매 | NTM P/E · EV/매출[Y] | 내년 EPS 성장[Y] | PEG | 고점 대비 · 3M[Y] | 자사주(공식) | 주요 위험 |
|---|---|---|---|---|---|---|---|---|---|---|
| **CRWD** | $278B | +26% (FQ2'27) [C1] | ▲ FY27 순신규 ARR 성장 34% | FQ3 실적 12월 초(미공지), FY28 첫 가이던스 2027-03(통상) | 182x · 38x | +28% | 6.5 | -2.5% · +45% | 잔여 $1.3B(7/31) [C2] | 초고배수 |
| **PANW** | $339B | +34% (FQ4'26, 인수 포함) [C3] | FY27 첫 가이던스: 매출 +23~24%, NGS ARR +22~23%(둔화) | FQ1'27 실적 11월(미공지) | 99x(FY27 가이던스 EPS) · 22x | FY27 +9%(FY28은 데이터 불일치) | >10 | -1.4% · +25% | 잔여 $1.0B, 2026-12-31 만료 [C4] | 인수 통합과 희석 |
| **FTNT** | $142B | +26% (Q2) [C5] | ▲ FY26 매출 +19%로 상향 | Q3 실적 **10/28(공식)** [C6] | 52x · 15x | +9.5% | 5.5 | 0% · +21% | 잔여 $766M, 상반기 $973M 매입 [C7] | 교체 주기 고점 |
| **ZS** | $37.6B | +25% (FQ4'26, 유기 ARR +20%) [C8] | FY27 ARR +16.6~17.4%, 10/6 재확인 [C9] | FQ1'27 실적 11월 말(미공지) | 46x · 8.3x | +15% | 3.1 | **-31.5%** · +62% | 공시 프로그램 없음 | 유기 성장 둔화 |
| **RBRK** | $25.2B | +38% (FQ2'27) [C10] | ▲ 전 지표 상향 | FQ3 실적 12월(미공지) | 179x · 12.6x | +53% | 3.4 | -2.6% · +46% | 공시 프로그램 없음 | GAAP 적자 |
| **S** | $9.2B | +21% (FQ2'27) [C11] | ▲ FY27 매출과 영업이익 상향 | FQ3 실적 12월(미공지) | 63x · **6.0x** | +44% | **1.4** | 0% · +42% | $200M 승인(2025-05), 잔여 확인 필요 [C12] | CRWD·MSFT와 경쟁 |

**(c) 최고 수혜와 차순위**
- **최고 수혜 CRWD**: 공식 이익 모멘텀이 가장 강하다.
  - 순신규 ARR이 +51%로 가속했고, 가이던스 상향 폭이 가장 컸다.
  - 비GAAP 영업이익은 $372M으로 +46%다 [C1].
  - 10/6 고점에 근접해 있다.
- **차순위 FTNT**:
  - 매출 +26%, 비GAAP EPS +41%, FY26 매출 가이던스 상향 [C5].
  - 10/28 공식 실적일이 있고, 10/9 52주 신고가를 냈다.
  - 배수(52x)가 CRWD보다 낮다.

**(d) 가장 저평가: S**
- 섹터 6종 중간값과 비교: EV/매출 6.0x(중간값 14.0x), PEG 1.4(약 4.5), NTM P/E 63x(약 81x).
- 매출 +21%, ARR +22%이고 가이던스를 올렸다 [C11].
- 함정 점검: GAAP EPS는 아직 -$0.27이다. 성장이 둔화하면 낮은 배수가 굳을 수 있다.
- CHKP는 P/E 12x로 더 싸지만 매출 성장이 +1.3%[Y]다. SCN이 선호하지 않는 가치·로우베타형이다.

**(e) 혼잡**
- **CRWD**: P/E 182x, EV/매출 38x, 12개월 +114%. 최고 수혜 종목과 겹치므로 진입 시점 위험이 있다.
- **NET**: P/E 225x, EV/매출 34.5x, 매출 +36% [C15].
- 참고: OKTA는 12개월 +144%인데 FY27 매출 성장 가이던스는 10~11%다 [C13].

**(f) SCN이 틀릴 수 있는 이유와 상관**
- **틀릴 이유**: 연준이 금리를 올리고 10년물이 5.25%다. 이 섹터의 중간값 P/E는 약 81x로 장기 듀레이션 자산이라, 종료 위험 1번(금리 급등)에 가장 민감하다. 2026-02과 04월에는 'AI가 보안을 대체한다'는 우려로 급락한 전례가 있다 [C14].
- **상관**: 1년 일간수익률 기준 CIBR–SOXX 상관은 0.27이다. SOXX 최악 10일(평균 -6.4%)에 CIBR은 평균 -0.06%였다(계산[Y]). 평소 동반 하락 위험은 낮거나 중간이다. 다만 금리 충격이 오면 같이 빠질 위험이 크다.

---

## 2. 바이오테크 (대형 제약은 구분: LLY는 시총 $1.05T라 제외, ABBV $490B는 '대형 제약'이라 표에서 제외)

**(a) 2027-06까지 이익 경로**
1. **신약 출시 매출**
   - ARGX: Vyvgart 매출 $1.52B(+60%), 순이익 $472M(+93%) [B1].
   - BBIO: Attruby 매출 $222M [B2].
   - INSM: Brinsupri 가이던스를 $1.25~1.40B로 상향 [B3].
   - RVMD: daraxonrasib(Rasonque) 2026-08-26 FDA 승인 [B4].
2. **2027-06 이전 FDA 결정일(PDUFA)**
   - BBIO: BBP-418 2026-11-27, encaleret 2027-05-08 [B2].
   - VRTX: povetacicept 2026-11-30 [B5].
   - REGN: cemdisiran 2026-11 [B6].
   - EXEL: zanzalintinib 2027-03-03(12/3에서 연장) [B7].
3. **3상 결과 일정**
   - ARGX: EMPASSION(MMN) 2026년 4분기, ADVANCE-NEXT(ITP) 2027년 상반기 [B1].
   - VRTX: AMPLITUDE 중간분석 2027년 초 [B5].

**(b) 후보 표**

| 티커 | 시총[Y] | 최근 분기 매출 YoY(공식) | 최신 가이던스(공식) | ~2027-06 촉매 | NTM P/E · EV/매출[Y] | 내년 EPS 성장[Y] | PEG | 고점 대비 · 3M[Y] | 자사주(공식) | 주요 위험 |
|---|---|---|---|---|---|---|---|---|---|---|
| **VRTX** | $129B | +12% [B5] | ▲ FY26 매출 $13.1~13.2B로 상향 | pove PDUFA **11/30/2026**, AMKD 중간분석 2027년 초 | 26x · 8.5x | +24% | 1.1 | -8.5% · +6% | 잔여 $2.6B [B8] | CF 매출 집중 |
| **REGN** | $77B | +17% [B6] | 매출 가이던스 없음 | cemdisiran PDUFA 2026-11, 사노피 계약 개정(선급금 $1.0B, 10/1) [B9] | 14.5x · 3.8x | **-10%** | 해당 없음 | -11.9% · +13% | 잔여 $2.5B [B6] | EYLEA 계열 -12% |
| **ARGX** (Nasdaq ADS) | $51.5B | 제품 매출 +60% [B1] | 매출 가이던스 없음 | ALKIVIA 성공(8/17 보도 [B17]), EMPASSION 2026년 4분기, ADVANCE-NEXT 2027년 상반기 | 26x(애널리스트 3명, 신뢰 낮음) · P/S 8.5x(Q2 연환산 계산) | +86%(신뢰 낮음) | 0.3(신뢰 낮음) | -22.6% · -6.5% | 공시 프로그램 없음 | FcRn 경쟁 |
| **BBIO** | $12.8B | **+120%** (SEC 계산) | 매출 가이던스 없음 | **PDUFA 11/27/2026, 5/8/2027**, infigratinib 2027 중반 출시 목표 [B2] | 적자 · 9.9x | 흑자 전환 예상 | 해당 없음 | -27% · -21% | $500M 승인(2026-05) [B10] | PDUFA 이진 위험 |
| **EXEL** | $14.9B | +11% [B11] | ▼ FY26 매출 $2.50~2.55B로 하향(8/5) | zanza PDUFA **3/3/2027** [B7] | 14.6x · 4.9x | +19% | 0.8 | 0% · +8% | 잔여 $598M(~2027-12) [B12] | 카보잔티닙 의존 |
| **NBIX** | $14.5B | +39%(인수 포함, 인그레자 +15%) [B13] | ▲ 인그레자 FY26 $2.825~2.875B로 상향 | 2027-06까지 공식 일정 촉매는 확인 필요(3상 2건 진행 중) | **12.4x · 3.3x** | +16% | 0.8 | -23% · -18% | 잔여 $266M [B14] | 인그레자 집중 |

**(c) 최고 수혜와 차순위**
- **최고 수혜 VRTX**:
  - 매출 가이던스를 공식 상향했다.
  - 11/30 PDUFA와 2027년 초 중간분석 일정이 있다.
  - 9/3에 52주 신고가를 냈고 현재 고점 대비 -8.5%다 [B5].
- **차순위 ARGX**:
  - 공식 이익 모멘텀이 가장 강하다(매출 +60%, 순이익 +93%).
  - 2027년 상반기까지 등록 임상 결과가 2건 나온다.
  - 다만 3개월 -6.5%로 추세가 약하다.
- BBIO는 촉매가 3건으로 가장 많다. 그러나 적자이고 3개월 -21%여서 '촉매 대기' 후보로 둔다.

**(d) 가장 저평가: NBIX**
- 흑자 바이오 9종(VRTX·REGN·AMGN·GILD·EXEL·NBIX·ALNY·BIIB·UTHR) 중간값과 비교: NTM P/E 12.4x(중간값 17.1x), EV/매출 3.3x(4.9x), PEG 0.8.
- 인그레자 가이던스를 올렸다 [B13].
- **이진 위험 점검**: 상업 제품이 3개라 단일 임상 이진 위험은 낮다. 대신 인그레자가 매출의 75%라 집중과 약가 위험이 있다.
- 대안 ALNY: PEG 0.5로 더 낮다. 그러나 7/30 TTR 가이던스를 $200M 내렸고 고점 대비 -53%라 추세가 회복되지 않았다 [B15].

**(e) 혼잡**
- **RVMD**: 12개월 +303%, 시총 $41B, EV/매출 37x, 적자.
- **ROIV**: 12개월 +116%, 매출이 거의 없다.

**(f) SCN이 틀릴 수 있는 이유와 상관**
- **틀릴 이유**: 주도력이 이미 식고 있다. XBI는 8/19 고점 대비 -9%, 3개월 -0.7%다(연초 대비 +26%, 9/15 [B16]). 9월 신고가는 VRTX·REGN·AMGN 같은 저베타(0.15~0.4) 대형주가 이끌어 SCN의 '하이베타' 선호와 맞지 않는다. FDA 심사 연장도 위험이다(EXEL 사례).
- **상관**: 1년 기준 XBI–SOXX 상관 0.35, IBB 0.26이다. SOXX 최악 10일에 XBI는 +0.05%였다(계산[Y]). 동반 하락 위험은 낮거나 중간이다.

---

## 3. 정유 (DK $4.6B, PARR $4.3B는 **$5B 미만**이라 표에서 제외)

**(a) 2027-06까지 이익 경로**
1. **크랙 스프레드**
   - 10/9 선물로 계산한 근사치[Y]: NYMEX 3-2-1 약 $62/bbl, 디젤 크랙 약 $107/bbl.
   - EIA(10/6): 9월 소매 디젤 $6.29/gal, 동부 증류유 재고는 5년 평균보다 32% 낮다.
   - EIA는 크랙이 내려가겠지만 2027년까지 역사적 평균 위에 머문다고 본다 [R1][R2].
2. **가동률**
   - EIA: 7~8월 97%, 9월 95%, 10월 92%(정비), 2027-06 95% 전망 [R3].
   - 회사별: MPC 94%, PSX 96%, CVI 98% [R4][R6][R9].
3. **미국 원유 할인**: 브렌트–WTI 차이가 9월 $16.85다. EIA는 10월 $11, 2027-06 $4로 좁혀질 것으로 본다 [R3].
4. **자사주**
   - VLO: 잔여 $1.4B에 7/16 신규 $5.0B 승인 [R11].
   - MPC: 잔여 $6.1B [R4].
   - PSX: 7/29 $10B 증액 [R7].

**(b) 후보 표** (정유사는 이익 가이던스를 내지 않는다. 매출 YoY는 유가 상승 효과라 EPS를 함께 적었다)

| 티커 | 시총[Y] | 최근 분기 매출 YoY · EPS(공식) | 최신 가이던스(공식) | ~2027-06 촉매 | NTM P/E (2027E · 2025 실적 기준)[Y] | 내년 EPS 성장[Y] | PEG | 고점 대비 · 3M[Y] | 자사주(공식) | 주요 위험 |
|---|---|---|---|---|---|---|---|---|---|---|
| **VLO** | $127B | +49% · 조정 EPS $12.54(전년 보고 EPS $2.28) [R5] | 이익 가이던스 없음, 환원율 59% | Q3 실적 **10/22(공식)** [R10], St. Charles FCC 3분기 가동 | 9.9x (10.3x · 42x) | -14% | 해당 없음 | -0.3% · +50% | 잔여 $1.4B + 신규 $5.0B [R11] | 크랙 정상화 |
| **MPC** | $130B | +54% · EPS $17.73(전년 $3.96) [R4] | 없음 | Q3 실적 **11/3(공식)** [R12] | 8.6x (8.9x · 43x) | -14% | 해당 없음 | -0.5% · +55% | 잔여 $6.1B [R4] | 크랙 정상화(MPLX가 완충) |
| **PSX** | $114B | +53% · 조정 EPS $9.41(1Q26 $0.49) [R6] | 없음, 부채 $6.6B 감축 | Q3 실적 10/28(보도) [R13] | 10.3x (10.6x · 44x) | -9% | 해당 없음 | 0% · +43% | +$10B 증액, 잔여 약 $11.7B(계산) [R7] | 환원보다 부채 감축 우선 |
| **DINO** | $21.8B | +53% · 조정 EPS $5.31(전년 보고 $1.10) [R8] | 배당 5% 인상, 분리 후 환원 50% 목표 [R8] | Q3 실적 **10/28(공식)** [R14], 윤활유 사업 분리(시점 확인 필요) | **8.4x (8.9x · 24x)** | -22.5% | 해당 없음 | 0% · +50% | 잔여 $208M [R15] | 이익 감소폭 큼 |
| **PBF** | $10.2B | +56% · EPS $7.54(전년 -$0.05) [R16] | 없음 | Q3 실적 **10/29(공식)** [R17], Martinez 정비 3분기 말 | 4.5x (4.9x · 2025 적자) | -27% | 해당 없음 | -4.1% · +49% | 약 $0.73B(계산) [R18] | 고비용, 적자 이력 |
| **CVI** | $6.0B | +55% · 조정 EPS $0.34 [R9] | 없음 | Q3 실적(일정 미확인) | 16.7x (15.5x · 2025 적자) | +51% | 0.3 | 0% · **+79%** | 공시 프로그램 없음 | 지배주주(Icahn), 비료 부문 |

**(c) 최고 수혜와 차순위**
- **최고 수혜 VLO**:
  - 공식 이익 모멘텀: 조정 EPS $12.54로 전년 보고 EPS의 약 5.5배이고, 현금 환원은 $2.6B다.
  - 7/16 신규 자사주 $5B를 승인했다.
  - 10/22에 업종 첫 Q3 실적을 낸다.
  - 신고가에 근접해 있다 [R5][R10][R11].
- **차순위 MPC**:
  - R&M 마진 $36.33/bbl(전년 $17.58), 환원 $2.8B, 잔여 자사주 $6.1B.
  - 미드스트림 EBITDA $1.78B가 크랙이 내려갈 때 완충 역할을 한다 [R4].

**(d) 가장 저평가: DINO**
- NTM P/E 8.4x로 6종 중간값 9.3x보다 낮다.
- 2025 실적 기준 P/E는 24x로, MPC·VLO·PSX의 42~44x보다 낮다. 이익 고점 함정을 걸러도 가장 덜 비싸다.
- 윤활유 사업 분리와 50% 환원 목표가 촉매다 [R8].
- **함정 점검**: 2027 컨센서스 EPS가 -22.5%다. 크랙이 EIA 전망대로 내려가면 P/E가 오른다.
- PBF는 P/E 4.5x로 가장 싸 보이지만 함정이라 제외했다. 2025년에 적자(EPS -$4.13)였고, 2027E가 -27%이며, 커버하는 애널리스트가 4명뿐이다. 전형적인 크랙 피크 함정이다.

**(e) 혼잡**
- **PBF**: 12개월 +192%.
- **VLO**: 12개월 +173%로 최고 수혜와 겹친다.
- 업종 전체: CRAK 12개월 +82%, 9월에 전 종목이 52주 신고가를 냈다.

**(f) SCN이 틀릴 수 있는 이유와 상관**
- **틀릴 이유**: 이익의 뿌리가 '경기 강세'가 아니라 중동 공급 차질이다(호르무즈 제약, 사우디 동서 송유관 공격, EIA [R1]).
  - EIA는 브렌트가 $111(10월)에서 $84(2027-06)로, 도매 디젤이 $4.61에서 $3.00/gal로 정상화된다고 본다 [R3].
  - 그러면 2027 이익이 줄어든다(컨센서스 -9~-27%).
  - SCN 종료 위험인 '유가 $100 재상회'는 정유에는 오히려 호재다. 헤지 성격이 있다.
- **상관**: 1년 기준 CRAK–SOXX 상관 0.11, VLO -0.04다. SOXX 최악 10일에 CRAK은 -0.34%였다(계산[Y]). AI Capex와 동반 하락할 위험은 낮다. 단, 경기 침체형 수요 충격은 예외다.

---

## 출처 (날짜는 공시·발표일)

- **[Y]**: Yahoo Finance quoteSummary/chart, 2026-10-09 종가, 참고값. 상관과 3-2-1 크랙은 이 데이터로 계산했다.
- **[C1]** CRWD 8-K, 2026-08-26: https://www.sec.gov/Archives/edgar/data/1535527/000153552726000029/crwd-20260826xex991.htm
- **[C2]** CRWD 10-Q, 2026-08-27: https://www.sec.gov/Archives/edgar/data/1535527/000153552726000031/crwd-20260731.htm
- **[C3]** PANW 8-K, 2026-09-01: https://www.sec.gov/Archives/edgar/data/0001327567/000132756726000019/ex991q426earningsrelease.htm
- **[C4]** PANW 10-K, 2026-09-10: https://www.sec.gov/Archives/edgar/data/1327567/000132756726000023/panw-20260731.htm
- **[C5]** FTNT 8-K, 2026-07-29: https://www.sec.gov/Archives/edgar/data/1262039/000126203926000018/ftntq2-2026ex991.htm
- **[C6]** FTNT Q3 일정 공지, 2026-10-02: https://finviz.com/news/398289/fortinet-to-announce-third-quarter-2026-financial-results
- **[C7]** FTNT 10-Q, 2026-07-30: https://www.sec.gov/Archives/edgar/data/1262039/000126203926000021/ftnt-20260630.htm
- **[C8]** ZS 8-K, 2026-09-03: https://www.sec.gov/Archives/edgar/data/1713683/000171368326000156/zs-07312026_991.htm
- **[C9]** ZS Investor Day 8-K, 2026-10-06: https://www.sec.gov/Archives/edgar/data/1713683/000171368326000200/zsinvestordaypressrelease.htm
- **[C10]** RBRK 8-K, 2026-08-27: https://www.sec.gov/Archives/edgar/data/1943896/000194389626000055/rubrikinc-991pressrelease7.htm
- **[C11]** S 8-K, 2026-08-27: https://www.sec.gov/Archives/edgar/data/1583708/000158370826000052/sentineloneq227exhibit991.htm
- **[C12]** S 10-Q, 2026-08-28: https://www.sec.gov/Archives/edgar/data/1583708/000158370826000055/s-20260731.htm
- **[C13]** OKTA 8-K, 2026-08-26: https://www.sec.gov/Archives/edgar/data/1660134/000166013426000068/okta-7312026_ex991.htm
- **[C14]** Vontobel, 2026-04-20: https://markets.vontobel.com/en-ch/blog/128013/anthropics-new-ai-model-worries-cybersecurity-sector
- **[C15]** NET 8-K, 2026-08-06: https://www.sec.gov/Archives/edgar/data/1477333/000147733326000053/q226exhibit991.htm
- **[B1]** ARGX 6-K, 2026-07-23: https://www.sec.gov/Archives/edgar/data/0001697862/000169786226000033/a04earningspressreleasehy.htm
- **[B2]** BBIO 8-K, 2026-08-10: https://www.sec.gov/Archives/edgar/data/1743881/000174388126000026/bbio-20260630xex991.htm
- **[B3]** INSM 8-K, 2026-08-06: https://www.sec.gov/Archives/edgar/data/1104506/000114036126031502/ef20079469_ex99-1.htm
- **[B4]** AJMC(FDA 승인 보도), 2026-08-26: https://www.ajmc.com/view/daraxonrasib-clears-fda-as-first-ras-targeted-pancreatic-cancer-drug
- **[B5]** VRTX 8-K, 2026-08-03: https://www.sec.gov/Archives/edgar/data/875320/000087532026000256/ex-991_q22026.htm
- **[B6]** REGN 8-K, 2026-07-30: https://www.sec.gov/Archives/edgar/data/872589/000087258926000023/exhibit991q22026.htm
- **[B7]** OncLive(EXEL PDUFA 연장), 2026-09-11: https://www.onclive.com/view/fda-extends-review-period-for-zanzalintinib-plus-atezolizumab-nda-in-pretreated-mcrc
- **[B8]** VRTX 10-Q, 2026-08-04: https://www.sec.gov/Archives/edgar/data/875320/000087532026000259/vrtx-20260630.htm
- **[B9]** REGN 8-K, 2026-10-06: https://www.sec.gov/Archives/edgar/data/872589/000110465926113895/tm2627077d1_8k.htm
- **[B10]** BBIO 10-Q, 2026-08-10: https://www.sec.gov/Archives/edgar/data/1743881/000174388126000027/bbio-20260630.htm
- **[B11]** EXEL 8-K, 2026-08-05: https://www.sec.gov/Archives/edgar/data/939767/000093976726000096/exel20260630exhibit991.htm
- **[B12]** EXEL 10-Q, 2026-08-05: https://www.sec.gov/Archives/edgar/data/939767/000093976726000098/exel-20260703.htm
- **[B13]** NBIX 8-K, 2026-07-30: https://www.sec.gov/Archives/edgar/data/914475/000091447526000035/q2-2026xearningsrelease.htm
- **[B14]** NBIX 10-Q, 2026-07-31: https://www.sec.gov/Archives/edgar/data/914475/000091447526000037/nbix-20260630.htm
- **[B15]** ALNY 8-K, 2026-07-30: https://www.sec.gov/Archives/edgar/data/1178670/000117867026000060/alny2026q2earningsrelease.htm
- **[B16]** Stocktwits(XBI), 2026-09-15: https://stocktwits.com/news-articles/markets/equity/biotech-midweek-pulse-xbi-loses-steam-hot-2026-stocks-catalysts-watch/cZtYGZfRB2R
- **[B17]** Clinical Trials Arena, 2026-08-17: https://www.clinicaltrialsarena.com/newsletters/argenxs-stock-rises-on-phase-iii-autoimmune-myositis-victory
- **[R1]** EIA STEO, 2026-10-06: https://www.eia.gov/outlooks/steo/
- **[R2]** EIA STEO 석유제품: https://www.eia.gov/outlooks/steo/report/petro_prod.php
- **[R3]** EIA STEO 데이터(Table 2, 4b): https://www.eia.gov/outlooks/steo/xls/STEO_m.xlsx
- **[R4]** MPC 8-K, 2026-08-04: https://www.sec.gov/Archives/edgar/data/1510295/000151029526000060/mpcq22026earningsrelease.htm
- **[R5]** VLO 8-K, 2026-07-30: https://www.sec.gov/Archives/edgar/data/1035002/000162828026050822/a6302026exh9901earningsrel.htm
- **[R6]** PSX 8-K, 2026-08-05: https://www.sec.gov/Archives/edgar/data/1534701/000153470126000030/psx-2026630_ex991.htm
- **[R7]** PSX 10-Q, 2026-08-05: https://www.sec.gov/Archives/edgar/data/1534701/000153470126000032/psx-20260630.htm
- **[R8]** DINO 8-K(실적 + 전략 전환), 2026-07-28: https://www.sec.gov/Archives/edgar/data/1915657/000191565726000046/dinoex99106-30x2026.htm , https://www.sec.gov/Archives/edgar/data/1915657/000191565726000046/dinoex992strategictransform.htm
- **[R9]** CVI 8-K, 2026-07-29: https://www.sec.gov/Archives/edgar/data/1376139/000137613926000038/exhibit991-cviq22026earnin.htm
- **[R10]** VLO Q3 일정 공지: https://finviz.com/news/389791/valero-energy-corporation-to-announce-third-quarter-2026-earnings-results-on-october-22-2026
- **[R11]** VLO 10-Q, 2026-07-30: https://www.sec.gov/Archives/edgar/data/1035002/000162828026050937/vlo-20260630.htm
- **[R12]** MPC Q3 일정 공지: https://finviz.com/news/393371/marathon-petroleum-corp-to-report-third-quarter-financial-results-on-november-3-2026
- **[R13]** PSX Q3 일정(보도): https://scanx.trade/stock-market-news/companies/phillips-66-announce-q3fy26-results-october-28/51136462
- **[R14]** DINO Q3 일정 공지: https://finviz.com/news/394489/hf-sinclair-corporation-third-quarter-2026-earnings-release-and-conference-webcast
- **[R15]** DINO 10-Q, 2026-07-30: https://www.sec.gov/Archives/edgar/data/1915657/000191565726000057/dino-20260630.htm
- **[R16]** PBF 8-K, 2026-07-30: https://www.sec.gov/Archives/edgar/data/1534504/000153450426000029/a991pressreleaseq2-26.htm
- **[R17]** PBF Q3 일정 공지: https://finviz.com/news/396193/pbf-energy-to-release-third-quarter-2026-earnings-results
- **[R18]** PBF 10-Q, 2026-07-30: https://www.sec.gov/Archives/edgar/data/1534504/000153450426000030/pbf-20260630.htm
