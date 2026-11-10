# 독립 재검토 반영 내역 — FM-2 3층 장치(A) · 전진 규칙과 주간 스크립트(B) (2026-11-10)

- 대상: review3/REPORT.md(독립 재검토 전문. 판정 A '고치면 통과', B '고치면 통과').
- 쓴 사람: 사장실 스레드 '미래 주가 예측 모델 만들기'(설계자). 발견마다 원문과 근거 로그를 다시 열어 확인한 뒤 고쳤다.
- 재검토자가 본 원본의 해시: fm3_shadow.py be23d48f… · fm3_weekly.py f774771e… · vixr.py c1c63d81… · MENU.json 5fc75afa… · 규칙 7ccc00da…
- 고친 판의 해시는 layer3.sha256에 적는다. 고친 곳만 다시 본 2차 검토는 review3/REVIEW2.md다.
- 지킨 것: 등록 전에는 vixr.py를 실제 결과와 대조해 채점하지 않았다(기술 점검만 했다). 해시로 고정한 파일(fm1.py · fm2.py · fm2_weekly.py · fetch_weekly.py · 전진 채점 규칙 · 두 사전 등록)은 고치지 않았다.

## A. 3층 장치

| 발견 | 다시 확인한 것 | 고친 것 | 어디 | 확인한 시험 |
|---|---|---|---|---|
| A-1 과거 재현이 매주 다시 실리고 성적이 공개된다 | r_registry.log.txt의 T8(주간 파일 두 개에 replay가 모두 실림) | 재검토의 ⓐ를 골랐다: 과거 재현을 없앴다. T0 전 구간의 짝 비교는 계산하지도 적지도 않는다. 자동 '거두기'도 없앴다. '덜 하는 쪽'이라 시스템이 정했다. 되살리려면 사장 카드다 | fm3_shadow.py score_horizon(forward만 낸다) · fm3_weekly.py cmd_run · 사전 등록문 틀 · 규칙 4절 3번 | fm3_itest.py: 주간 결과 어디에도 replay가 없고, 구간마다 forward와 state만 있다 |
| A-1 덧붙임(내가 찾은 것) | history 종류는 몫을 과거에서도 배우므로 그 값이 과거 성적을 간접으로 보여 준다 | 숨기지 않고 규칙에 적었다. 편입 근거로 쓰지 않고, 보고 고치면 새 도전으로 센다 | 규칙 4절 3번 · 12절 | — |
| A-2 규칙문이 코드·실측과 다른 문장 6곳 | 6곳 모두 원문 대조 | ① '재현 1회' → 재현 자체를 없앰 ② '몫은 1/5에서 시작' → forward만 그렇고 history는 T0에 이미 배운 값 ③ '도전자 코드가 채점에 닿지 못한다' → 다른 프로세스에서 돌지만 격리 장치는 아니라고 고쳐 씀 ④ '숨은 속성 접근 거부' → 금지 구문을 늘리고, 못 잡는 것은 Judge 읽기 점검표로 ⑤ '이득 1% 안팎이면 하한 > 0' → 실측(+1.2%는 4.4%, +4.0%는 47%)으로 바꿈 ⑥ '우연 통과 = 판정 횟수 × 2.5%' → 실측 2.0~8.3%로 바꿈 | 규칙 4·5·7·9·12절 | — |
| A-3 판정 시점을 움직일 수 있다 | r_registry.log.txt의 T3(asof를 거슬러 다섯 번 연속 판정) | ① 분기 비교를 '뒤 분기일 때만'으로, 지난 실행보다 이른 asof는 거부 ② 건너뛴 도전자는 다음에 채점되는 실행에서 본다 ③ 판정 쌍을 등록 때 고정해 LOG.jsonl에 적는다. display를 고쳐도 바뀌지 않는다 ④ 장부(REGISTRY.json)는 LOG.jsonl을 접은 결과와 같아야 한다. 모든 명령이 시작할 때와 쓸 때마다 대조하고, 다르면 멈춘다. 등록 파일 3개의 해시도 매 실행 때 대조한다 | fm3_weekly.py cmd_run · cmd_register(judged_pair) · books_from_log · verify_books · open_books · commit | fm3_weekly.py selftest: 장부를 손으로 고친 9가지가 모든 명령에서 거부되고 rebuild로 되살아남. fm3_itest.py: 이른 asof 거부, 건너뛴 도전자의 다음 실행 판정, 판정 쌍 대조 |
| A-4 52주 도중 탈락의 구간은 쓸 만하지 않다 | t05_rolling.log.txt(60일 중립 더미 27~30% 탈락) | 구간은 토막마다 독립 구간이 4개를 넘을 때부터만 계산한다(20일 65주, 60일 193주). 중간 점검은 20일만 65주부터, 60일은 없다. 탈락 기록 문구를 '중간 점검 … 최종 판정이 아님'으로 | fm3_shadow.py CI_WEEKS · FUT_WEEKS · judge · compare · fm3_weekly.py WHY · REJECTED_HEAD · 규칙 5절 | sim_fut.log.txt(같은 가짜 도전자에 새 규칙을 굴림): 60일 중간 탈락 0. 20일은 복제형 0.8~6.2%, 풀과 많이 다른 더미 9~22%, 이득 +1.2% 더미 1.6%. 통과 비율은 옛 규칙과 같다 |
| A-4 덧붙임 | 20일의 중간 탈락은 옛 규칙(11~23%)에서 조금만 줄었다 | 숫자를 그대로 적었다. 중간 점검은 자리를 일찍 비울 뿐이고 통과에는 쓰지 않는다 | 규칙 5절 · 12절 | 위와 같음 |
| A-5 검정력이 낮고 거짓 통과가 명목보다 높을 수 있다 | t05_rolling.log.txt · t06_post_all.log.txt | 숫자를 규칙에 그대로 적었다(대부분 '구분 안 됨', 이득 0도 2.0~8.3% 통과, 평생 20회 도전이면 우연 통과 0.4~1.6개, 고정판 쌍은 더 무름). Judge 보고 필수 항목에 이득 점추정·발급 비율·낸 곳만의 이득·우연 통과 기대 개수를 넣었다 | 규칙 6절 · 12절 · fm3_shadow.py compare(gain_where_issued) | sim_fut.log.txt |
| A-6 '93% 점검'이 코드에 없다 | fm3_weekly.py 원본에 표시 없음 | 판정 구간 점검을 기록하는 명령을 만들었다. 기록이 없거나 93% 미만인 구간은 처분하지 않는다. 처분할 때가 되면 그날의 숫자를 LOG.jsonl에 적어 두고(held), 점검이 통과로 기록되면 그 숫자로 처분한다. 실패하면 사장 카드 | fm3_weekly.py cmd_interval_check · cmd_run(ci_ok · held · settle) · 규칙 5절 | fm3_itest.py 3·4번째 실행: 처분이 보류되고, 뒤에 그날의 숫자로 처분됨 |
| A-7 도전자 코드가 채점 프로세스 안에서 돌고 정적 검사가 얕다 | bad_demo.log.txt(b26이 판정 함수를 바꿔 대조군까지 후보로 만듦) | ① 도전자 코드는 다른 프로세스에서만 돈다(등록 심사: 새 파이썬 두 개, 주간 계산: 자식 프로세스) ② View는 시작일까지를 잘라 복사한 읽기 전용 자료만 준다 ③ 판정에 쓰는 새 예측은 모든 입력 파일을 그 시작일에서 자른 뒤 계산하고, asof까지의 자료로 계산한 값과 다르면 그 주 채점을 건너뛴다 ④ 금지 구문: 속성 대입, `__` 이름, format, 시계 문자열(now·today), hash·id 등 ⑤ Judge 읽기 점검표 7항 | fm3_shadow.py View · _cut · _stage_one · stage · admit · static_check · 규칙 3절 · 7절 | bad_summary2.log.txt: 나쁜 도전자 28개 모두 등록 심사에서 걸리고 대조군은 통과. plumbing_run1.log.txt: 실제 자료에서 판정용 예측 14,574행(도전자 둘 각각)이 두 계산에서 모두 같음 |
| A-7 남은 것 | 격리 장치는 아니다. 자식 프로세스도 같은 권한으로 돈다 | 규칙에 그대로 적었다. 세션이 새로 쓴 계산 파일의 관문은 Judge의 읽기다 | 규칙 7절 · 12절 | — |
| A-8 등록 심사가 정직한 실수도 놓친다 | bad_demo.log.txt(b04 · b05 · b10 · b15 · b16 · b17) | 심사를 새 파이썬 두 개로: 20종 전체 × 12시점 × 3구간, 다른 프로세스 사이 결정성, 20종 × 5시점 자르기 대조, 폭 비율의 가운데값 0.5~2배, 속도 0.01초, 등록 때 전체 격자 예행(73,476행). asset_extras는 이 판에서 거부 | fm3_shadow.py admit · admit_pass · admit_points · load_challenger | bad_summary2.log.txt · admit_vixr_v5.json(vixr 기술 점검 통과. 실제 결과와 대조 없음) |
| A-9 발급한 예측의 기록이 없다 | 재검토의 XLE 봉 하나 빼기 시험 | 그 주에 처음 나온 시작일의 예측을 파일로 남기고(실행마다 하나, 해시를 LOG.jsonl에), 채점에는 남긴 값만 쓴다. 다시 계산한 값이 다른 개수·제때 못 낸 개수·격자에서 빠진 개수를 report에 올린다. Judge는 보관한 주간 입력으로 다시 계산해 대조한다 | fm3_shadow.py freeze · load_issued · fm3_weekly.py cmd_run · 규칙 5절 · 6절 5항 | fm3_itest.py 6번째 실행: 지난 종가를 고치면 다시 계산한 값은 달라지지만 채점은 남긴 값 그대로 |
| A-10 장부가 덧붙이기 전용이 아니고 막히는 길이 있다 | r_registry.log.txt | ① LOG.jsonl이 기록이고 장부는 그것을 접은 결과다. 장부를 통째로 바꿔치기해 쓰고, 덧붙일 줄을 먼저 적어 둔 뒤 덧붙인다. 도중에 멈추면 다음 명령이 마저 쓴다 ② init은 있는 장부를 덮어쓰지 않는다 ③ 사람용 닫기 명령(close) ④ 12번 연속 건너뛴 도전자는 끝낸다 ⑤ 통과한 구간은 그 주부터 awaiting_judge에 뜬다 ⑥ 판정 구간이 없는 메뉴 항목은 거부 ⑦ 잘린 줄은 닫고 넘어간다 | fm3_weekly.py commit · flush · _append · save_reg · cmd_init · cmd_close · cmd_rebuild · cmd_run | fm3_itest.py: 장부 저장 전 멈춤, 저장과 덧붙이기 사이 멈춤, 닫기, 12번(시험에서는 2번) 건너뜀. fm3_weekly.py selftest |
| A-11 그 밖 | — | 전진 발견 기준을 구간별 최소 표본(104/208주)으로 · 건너뜀 연속은 asof당 한 번 · fm2 캐시가 같은 입력으로 만든 것인지 대조 · 23시 뒤 등록 거부 · 규칙에 없던 설정값을 7절에 적음. 60일 전진 발견이 우연으로 열리는 비율은 208주 기준으로 다시 재지 않았다(확인 필요, 규칙 12절) | fm3_weekly.py FIND_WEEKS · skip_streak · cache_note · cmd_register | fm3_weekly.py selftest · fm3_itest.py |
| A-12 vixr 머리글 | vixr.py 원본 | 머리글에 '7일까지 앞 값을 그대로 쓰고, 더 낡으면 예측 없음'을 적었다. 재검토는 '미국 종목은 당일 VIX를 읽는다고 적고 정의는 그대로'를 권했지만, 나는 더 엄격하게 모든 종목이 전날 VIX를 읽도록 고쳤다(EXTRA_LAG = 1). VIX의 하루 값이 미국 주식 종가 뒤에 정해지기 때문이다. 점수를 보고 고친 것이 아니다(채점한 적이 없다). 정의가 재검토자가 읽은 판과 달라졌으므로 2차 검토가 다시 읽는다 | layer3/menu/vixr.py · MENU.json | admit_vixr_v5.json |
| A-0 정상(그림자 계산) | — | 고치지 않았다 | — | fm3_shadow.py selftest 1번 |

## B. 전진 규칙과 주간 스크립트

해시로 고정한 파일은 고치지 않는다. 절차는 안내문에 적고, 코드는 뒤에 새 파일(fetch_weekly v2 · fm2_weekly v3)과 새 해시 기록으로 만든다. 예약 제안(설계서 8-3절 ⑤) 전에 끝낸다.

| 발견 | 지금 한 것(절차) | 뒤에 할 것(새 판) |
|---|---|---|
| B-1 safe_asof가 진행 중인 미국 장을 거르지 못한다 | '13:00~22:00 KST에만 받는다'를 forecast-ledger.README.md와 layer3/README.md에 적었다 | fetch_weekly v2: 받은 시각과 장 마감을 대조 |
| B-2 최근 null을 '아직 안 채워짐'으로 본다. 11-11은 채권 휴장 | '첫 전진 줄은 safe_asof가 2026-11-11 이후인 첫 실행에서 쓴다. 손으로 고치지 않는다'를 안내문에 적고, 설계서 8-3절의 '11-11이 될 때까지'를 '11-11 이후'로 고쳤다 | fetch_weekly v2: 받은 시각보다 3일 넘은 null은 영구로 본다 |
| B-3 장부의 최신 시작일보다 이른 asof를 받아들인다. 시험용 --forward-start가 남아 있다 | '지난 줄보다 이른 asof로 돌리지 않는다. --forward-start는 쓰지 않는다'를 안내문에 적었다. 3층 실행은 이른 asof를 코드로 거부한다 | fm2_weekly v3: 이른 asof 거부, 늦게 쓴 줄 표시와 합계 제외, 시험 플래그 제거 |
| B-4 풀 트랙 전진 점수도 매주 다시 계산한다 | 주간 입력 폴더를 남기고, Judge가 판정 때 그것으로 다시 계산한다(3층 규칙 6절 5항 · 안내문) | 격자를 날짜에 고정하는 것은 계산법 변경이라 사장 카드 |
| B-5 그 밖(원장 끝줄이 잘리면 멈춤, 포함률 경고가 표시 칸에 없음 등) | 없음 | fm2_weekly v3 과제 목록에 넣었다 |
| B-0 정상(규칙 구현·재채점) | 고치지 않았다 | — |

## 재검토가 '확인 필요'로 남긴 것

- 미국 장중 봉에 값이 실리는지: 확인하지 못했다. 그래서 받는 시각을 절차로 막았다(B-1).
- 2026-11-11의 ^TNX·^IRX 봉: 11-12에 MANIFEST.json으로 확인한다(B-2).
- 야후가 과거 봉을 끼우거나 빼는 빈도: 모른다. 일어나면 주간 결과의 report에 뜬다(A-9).
- 실제 자료에서의 구간 포함률: 모른다. 판정 구간 점검에서 다룬다(A-6).
- forward 종류의 실제 이력 굴림 모의: 하지 않았다.
- 회사PC 사본과 23:30 커밋, 독립 Judge 절차의 실제 독립성: 첫 등록 날과 첫 판정 때 확인한다.

## 2차 검토(review3/REVIEW2.md)의 발견과 반영 (2026-11-10 밤 KST)

- 2차 검토는 위에서 고친 곳만 다시 봤다. 판정: 3층 장치 '고치면 통과'(판정을 틀리게 만드는 결함은 찾지 못함, 고칠 곳 10건), 주간 실행 절차 문구(B) '통과'.
- 발견마다 코드 원문과 검토자의 시험 기록(review3/reviewer2/logs/)을 다시 확인했다. 10건 모두 사실이었다.
- 고친 뒤 검토자의 확인 시험을 새 코드로 다시 돌렸다(review3/r3check/logs/). 아래 '확인' 칸이 그 기록이다.
- 위 A절 표의 문장 가운데 이 절에서 바뀐 것: A-6의 '그날의 숫자로 나중에 처분'(→ 사람이 정한다), A-7 ③의 '그 주 채점을 건너뛴다'(→ 그 실행에서 끝낸다), A-1(→ history 종류의 몫도 주간 결과에서 뺐다).

| 발견 | 한 일 | 고친 곳 | 확인 |
|---|---|---|---|
| R2-1 규칙 문장이 코드와 다른 곳 20개(틀린 문장 6 · 지나친 약속 12 · 숫자 2) | 모두 고쳤다. 숫자 둘은 sim_fut.log.txt를 다시 읽어 확인했다(우연 통과 기대 0.4~1.7개. 고정판 쌍 20일은 가짜 도전자에 따라 0~12.9%) | 규칙 3·4·5·6·7·8·9·12·13절 | — |
| R2-2 history 종류의 주간 결과에서 T0 전 누적 점수 차이를 정확히 되짚을 수 있다 | history 종류는 몫과 학습 상태(state · om_mean)를 주간 결과 파일과 화면에 싣지 않는다. 판정할 때가 된 날의 숫자 줄(LOG.jsonl의 held · judged)에는 그대로 둔다. '덜 하는 쪽'이라 시스템이 정했다. 매주 보이게 하려면 사장 결정이 필요하다 | fm3_weekly.py shown · cmd_run · 규칙 4절 3번 | t5_state.log: history 도전자의 결과 칸에 "om" 열쇠 없음. forward 도전자는 그대로 보임 |
| R2-3 전날 값 규칙(EXTRA_LAG = 1 또는 미국 밖 종목)에서 값을 하루 당겨 찍는 derive를 자르기 대조가 못 잡는다 | 자르기 대조(등록 심사와 주간 실행)에서, 추가 자료를 전날 값까지만 읽는 종목은 추가 자료를 시작일 전날에서 자른다. 정직한 코드의 값은 그대로다 | fm3_shadow.py asset_context(cut_test) · _stage_one · admit_pass | admit_r2shift1.json: 300행 중 282행 불일치로 탈락. admit_r2shiftcal.json: 222행 불일치로 탈락. admit_vixr.json: 0행(통과. 실제 결과와 대조 없음) |
| R2-4 주간 대조 불일치가 그 주만 건너뛴다 | 불일치를 따로 구분해(CutMismatch) 그 실행에서 도전자를 끝낸다. 아직 그림자인 구간 모두(보류된 구간도), 탈락 기록 '시작일 대조 불일치', report 1줄. '덜 하는 쪽'이라 자동이다 | fm3_shadow.py CutMismatch · stage, fm3_weekly.py cmd_run · WHY | fm3_itest.py(r5c: 끝남, 탈락 기록 1줄, 다른 도전자는 그대로) |
| R2-5 잠금이 없고, 겹친 명령이 사건을 조용히 지우고 장부를 막는다. 최종 판정 시점을 두 번 쓰는 길 | ① commit이 쓰기 직전에 'LOG.jsonl 줄 수 = 읽을 때의 번호, 디스크의 장부도 같은 번호이고 남은 줄 없음'을 보고 아니면 쓰지 않고 멈춘다 ② flush가 같은 번호의 줄 내용이 다르거나 남은 줄이 끝에 이어지지 않으면 멈춘다 ③ 잠금 파일은 두지 않았다(네트워크 폴더와 일회용 컨테이너에서 낡은 잠금이 남는 문제). '한 번에 한 명령만'을 규칙 7·8절과 layer3/README.md에 적었다 | fm3_weekly.py flush · commit · STOPPED | t3_books.log S6: commit 멈춤, LOG 그대로, 판정 시점 안 쓰임. t4_world.log C: 실행이 쓰기 전에 멈춤, 결과 파일 없음, verify 통과 |
| R2-6 금지 구문 점검을 지나가는 수법 6가지 | match 구문 · 바이트 시계 문자열 · mro · numpy 설정 함수(setbufsize · set_printoptions 등) · str · repr · ascii · dir · f-문자열 거부. EXTRA_LAG는 정수만. 못 막는 것(이어 붙인 시계 문자열, `'%s' % V`)은 Judge 점검표 4번과 규칙 12절에 적었다 | fm3_shadow.py BAD_NAMES · BAD_ATTRS · BAD_NODES · static_check · load_challenger | t1_static.log: r2match 거부(.mro, Match). 탐침 14개 가운데 10개 거부(전에는 1개). 남은 4개는 이어 붙인 시계 문자열(못 막음 — 규칙 12절), 값의 `.open` 읽기(numpy에서 파일을 여는 객체로 가는 길 6가지 — DataSource · lib · memmap · genfromtxt · ctypeslib · testing — 는 따로 거부되는 것을 확인했다. 다른 길이 없다는 증명은 아니다), 날짜로 갈라지는 코드(구문이 아니라 시작일 대조와 Judge가 본다), `EXTRA_LAG = 1.0`(구문 점검은 지나가고 load_challenger가 거부한다). admit_r2match.json: static 탈락 |
| R2-7 구간 점검 기록이 규칙보다 느슨하다(실패 뒤 통과를 다시 적으면 풀림 · 보류 뒤 기록도 받음 · 길이별이 아님 · 한 구간만 적으면 다른 구간 통과가 지워짐) | ① 보고서는 판정 구간과 길이를 모두 담아야 기록된다 ② 자동 처분(auto)은 기록된 점검이 모두 통과일 때만. 실패 뒤 통과는 되살리지 않는다 ③ 보류된 판정은 코드가 풀지 않는다. 매주 report에 'PERSON DECISION NEEDED'와 그날 숫자가 읽히는 처분을 올린다 ④ 실패 기록이 있으면 'DECISION CARD NEEDED', 첫 점검 26주 전부터 허용하는 점검이 없으면 예고 | fm3_weekly.py ci_lengths · cmd_interval_check · cmd_run · 규칙 5절 | t3_books.log S3: 한 구간만 담은 보고서 거부. t4_world.log G: 실패(0.91) 뒤 통과(0.95)를 적어도 보류 그대로, 사건 없음. fm3_itest.py 4·5번째 실행 |
| R2-8 같은 asof 지름길이 낡은 계산 폴더를 쓸 수 있다 | 계산을 시작하기 전에 계산 폴더의 INPUTS.sha256을 지운다 | fm3_weekly.py cmd_run | t4_world.log E: 낸 예측 파일과 다른 행 585행 중 0행(전에는 138행) |
| R2-9 도중에 멈춘 뒤의 구멍 셋 | ① rebuild가 남은 줄을 먼저 마저 쓴다(이어지지 않으면 버리고 화면에 적는다) ② init은 장부를 쓴 뒤 REJECTED.md를 만든다. 없으면 다음 명령이 머리글을 만든다 ③ 결과 파일은 장부 뒤에 쓴다. 대조 실패 문구를 쓰기 전후로 나눴다 | fm3_weekly.py cmd_rebuild · cmd_init · ensure_rejected · cmd_run · verify_books | t3_books.log S2: rebuild 뒤 LOG 4줄 · 탈락 기록 1줄(전에는 2줄 · 0줄). S5: init 다시 가능 |
| R2-10 그 밖 | 고친 것: 23시 제한을 심사 뒤에도 본다 · 읽을 수 없는 추가 자료는 그 도전자만 건너뛴다(extra_stale) · run 사건에 코드 해시와 fm2 입력 해시를 적는다. 다음 판으로 미룬 것: REJECTED.md와 LOG.jsonl 대조 · LOG.jsonl 해시 사슬 · 주간 계산 시간 한도 · 거른 주 알림 · 구간 단위 닫기 · 폭 가운데값 띠의 부작용(규칙 12절에 적음) | fm3_weekly.py cmd_register · extra_stale · cmd_run | fm3_weekly.py selftest |
| 내가 찾은 것(검토자의 E 시험을 다시 돌리다) | '예측 없음'으로 남긴 줄이 지금 자료로 계산되면 매주 '다시 계산한 값이 다름(자료 정정?)'으로 보고됐다. 정정이 아니므로 따로 센다(none_kept). 채점은 바뀌지 않는다 | fm3_shadow.py freeze | fm3_shadow.py selftest |

검토자가 물은 여섯 가지(D1~D6):

- D1 history 종류의 몫 표시: 가렸다(R2-2). history 종류 자체는 둔다.
- D2 20일 중간 점검: 둔다. '해로움이 뚜렷함'이라는 말은 규칙·탈락 기록 문구에서 뺐다('중간 점검: 상한 < 0').
- D3 보류와 '그날 숫자 고정' 원칙: 둔다. 구멍 둘(R2-7 ①②, R2-5)을 막았다.
- D4 편입 코드가 아직 없는 것: 그대로 둔다. 규칙 12절에 '표시 변경을 적는 명령이 생기기 전에는 표시가 바뀐 뒤 새 도전자를 등록하지 않는다'를 더했다.
- D5 자리 3개 · 도전 2회: 그대로다.
- D6 사람이 정할 일: 실패한 구간 점검을 다시 적어 보류를 푸는 일(이제 자동으로 풀리지 않는다), 미래 자료 의심 도전자를 계속 잴지(자동으로 끝낸다 — '덜 하는 쪽'). 과거 몫을 보이게 하는 일은 사장 결정인데, 가렸으므로 지금은 물을 것이 없다.

A-12의 근거(VIX의 하루 값이 주식 종가 뒤에 정해진다):

- Cboe VIX 안내서: 정규 시간 VIX 계산은 미국 중부 시각 8:30~15:15 — https://cdn.cboe.com/resources/vix_options/VIX_fact_sheet.pdf
- Cboe VIX 산출 방법서: 현물 값은 GTH부터 'Cboe RTH 세션이 끝날 때까지' 계산 — https://cdn.cboe.com/api/global/us_indices/governance/Volatility_Index_Methodology_Cboe_Volatility_Index.pdf
- VIX 선물 명세: https://www.cboe.com/tradable_products/vix/vix_futures/specifications
- 종료 시각을 글자 그대로 적은 지금의 공식 쪽은 찾지 못했다(확인 필요). 틀렸더라도 전날 값을 읽는 쪽이 더 엄격하다.

2차 검토가 '확인 필요'로 남긴 것:

- 야후가 평일 낮(KST 17~22시, 미국 장이 열리기 전)에 그날 봉을 미리 주는지: 2026-11-10 22:00 KST에 한 번 받아 봤다. XLE와 S&P 500의 마지막 봉은 11-09였다(그날 봉 없음). 한 번의 관찰이라 늘 그런지는 확인 필요다. 받은 뒤 날짜를 보는 절차를 forecast-ledger.README.md '지킬 것'에 더했다.
- 야후가 지난 봉을 끼우거나 빼는 빈도 · 판정 구간 포함률(93%) 점검 · 60일 전진 발견이 208주 기준에서 우연히 열리는 비율: 그대로 확인 필요다.
- forward 종류와 보류 경로의 실제 자료 굴림 모의 · 12번 건너뜀 · 23시 제한 · 폭 가운데값 띠: 코드 읽기와 가짜 자료 시험뿐이다.
- vixr 고친 판: 값 바꾸기 시험으로 '전날 값만 읽는다'는 확인됐다. 숫자를 독립적으로 다시 계산하지는 않았다.
- 회사PC 사본과 23:30 커밋 · Judge의 독립성: 운영에서 본다.

## 좁은 확인(review3/REVIEW3.md)의 발견과 반영 (2026-11-10 22시대 KST)

- 범위: 2차 검토의 발견을 고친 코드 변경만 같은 검토자가 다시 봤다(fm3_shadow.py da12b055… · fm3_weekly.py eb83a1a4… · fm3_itest.py 97ea073a…). 판정은 '통과'다. 막는 결함은 없었고 고칠 곳 6건(중요 1 · 가벼움 5)과 규칙에 적을 설계상 결과 5가지를 냈다.
- 검토자가 돌린 것: vixr 2년치 주간 자르기 대조(6,042행 중 다른 행 0. 전날 값만 읽는 비미국 5종 포함), 장부 탐침 10개, 합성 세계에서 실제 불일치로 끝나는 경로. vixr를 실제 결과와 대조하지는 않았다. 검토자의 스크립트와 로그는 review3/reviewer3/에 있다.
- 발견마다 코드 원문을 다시 확인한 뒤 고쳤다. 고친 파일은 fm3_weekly.py 하나다(eb83a1a4… → 88a63c7e…). fm3_shadow.py · fm3_itest.py · vixr.py · MENU.json은 검토자가 본 그대로다. 바뀐 줄은 review3/r3check/r4_weekly.diff에 있다.

| 발견 | 원문 확인 | 고친 것 | 시험 |
|---|---|---|---|
| R3-1 (중요) 대조 불일치로 끝난 도전자가 다른 구간의 통과 때문에 후보로 남음 | end_if_done이 'pass_to_judge'가 하나라도 있으면 candidate로 적었다 — 맞다 | end_cut_mismatch가 있으면 ended로 적는다. 규칙 5절에 적었다 | selftest: 통과 + 불일치 → ended, 통과 + 구분 안 됨 → candidate, 아직 재는 구간이 있으면 그대로 |
| R3-2 장부를 저장한 뒤 멈췄는데 '아무것도 쓰지 않았다'고 알림 | commit이 save_reg 뒤에 flush를 부른다 — 맞다 | 그 경우의 문구(STOPPED_SAVED: had already saved … run "rebuild")를 따로 두었다. 규칙 8절 · layer3/README.md | selftest: 문구 확인 |
| R3-3 남은 줄의 모양이 깨진 장부에서 rebuild가 죽음 | rebuild가 SystemExit만 받았다 — 맞다 | rebuild가 그 줄을 빼고 장부를 다시 쓴다. 처방에 더해, 다른 명령은 파이썬 오류 대신 'books refused … Run "rebuild"'로 멈춘다 | selftest: 깨진 모양 4가지 |
| R3-4 REJECTED.md가 없어지면 조용히 다시 만듦 | ensure_rejected가 말없이 만들었다 — 맞다 | init 뒤의 장부에서 다시 만들 때 NOTICE 한 줄을 낸다. LOG.jsonl과의 대조는 다음 판(규칙 12절) | selftest |
| R3-5 금지 구문 점검을 지나가는 수법 넷 | 네 탐침을 내가 다시 돌렸다 — 모두 통과(막히지 않음) | 코드는 그대로 두었다. Judge 점검표 4번(규칙 3절)과 12절에 적었다 | — |
| R3-6 구간 점검이 true/false를 숫자로 받음 | float(True)가 1.0이다 — 맞다 | true/false가 든 보고는 기록하지 않는다. 규칙 5절 · layer3/README.md | selftest |
| 설계상 결과 5가지 | close 줄 · awaiting_judge 목록 · 멈춘 실행의 파일(r3check/logs/t4_world.log.txt C)을 원문에서 확인 | 규칙 5절과 8절에 적었다 | — |

- 이 여섯 곳은 검토자가 보지 않은 변경이다. 한 번 더 검토를 돌리지 않았다. 판정이 '통과'였고, 변경이 검토자의 처방 그대로이거나 그보다 좁기 때문이다(처방에 없던 것은 R3-3의 'books refused' 문구 하나). 자체 시험과 확인 시험 전체를 최종 코드로 다시 돌렸다: 자체 시험 2종 · 전 과정 시험(itest OK) · 금지 구문 탐침(14개 중 10개 거부) · 장부 시험(t3) · 합성 세계 시험(t4 · t5) · 등록 심사 4건(가짜 도전자 셋 탈락, vixr는 기술 심사 통과 — 자르기 대조 300행 중 다른 행 0, 실제 결과와 대조 없음) · 나쁜 도전자 28개 모두 탈락, 대조군 1개 통과. 기록은 review3/r3check/logs_final/에 있다(나쁜 도전자 요약은 review3/bad_summary3.log.txt, 전 과정 시험은 review3/itest_final.log.txt, vixr 심사 결과는 review3/admit_vixr_v6.json).
- 좁은 확인이 확인하지 못했다고 적은 것: 23시 제한의 재확인과 12번 건너뜀 종료는 코드 읽기뿐이다 · 대조 불일치와 보류가 겹친 경우는 따로따로만 돌려 봤다.
