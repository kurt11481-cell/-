---
id: integrated-check-v3.12.4-change
title: 통합 점검 v3.12.4 · SAVE 메모 v2.2 변경 기록 (st-1014 B)
date: 2026-10-14
class: K2 (예약 지시문·규칙 파일·기록 전 검증) — 근거 강도·트리거 기준·주문 권한 불변. 매수 쪽만 막는 실적 단서 가드 추가
decision: 사용자 "st-1014: B" (2026-10-14 09:42 KST) — docs/claude/integrated-check-needs-recheck-saveticker-2026-10-14.md 2절
status: 적용됨 2026-10-14 10:26~10:28 KST(사용자 "적용 (권장)") — SAVE updated_at 01:26:31Z, 통합 점검 updated_at 01:28:08Z, 두 교체 모두 "prompt re-signed". 첫 실제 짝 실행 2026-10-15 06:15 → 06:40
authority: order_authority=false · quantity_authority=none · execution_quantity=null
---

# 통합 점검 v3.12.4 · SAVE 메모 v2.2 변경 기록

## 1. 파일과 sha256 (LF)
| 파일 | sha256 | 바이트 |
|---|---|---|
| docs/claude/integrated-check-prompt-v3.12.4-2026-10-14.txt (규칙 파일) | cafec5a43eca9358de006711d627f1e8eb558ef4c38278d4a9f36af672870530 | 92,520 |
| docs/claude/scheduled-prompts/pending-st1014/integrated-check-daily.txt (로더 v3.12.4-L+R1) | b166bad289c4b2b1520d16da81587fc3b895279461e1a6d892dcdf26c4787b2d | 17,293 |
| docs/claude/scheduled-prompts/pending-st1014/save-market-memo.txt (SAVE v2.2) | 7092f03604ab9f9eca598588641904060635ba747860e7c10aab05d294ad9946 | 24,716 |
| 이전 규칙 파일 v3.12.2 | ee098920870bb7195e995f0aa2d0b45c825fea0fbd5a14762d526a8068e41e59 | 82,682 |
| 이전 로더(현행) | ded151f3f2d243634195577c9852e438275e94756dd1557ef4292d158c1e8e1d | 15,690 |
| 이전 SAVE v2.1(현행) | 5e4838171ab3fcbb0a2e940bf43a687e0842ee86f2ade3d0b9b4818aca66aa05 | 11,712 |

v3.12.3 초안(fx-2, 미적용)은 포함하지 않았다. v3.12.3을 적용하려면 v3.12.4 위에 다시 만들어야 한다.

## 2. 바뀐 것
1. 현금(1)·1-1 ②): 주문 가능액 fc_ord_alowa·출금 가능 fc_pymn_alowa는 `overseas accounts cash`(ust21110)에서, 총자산용 외화예수금 fx_entr는 `cash-by-currency`(ust21120)에서 읽는다. 매수 요건 ②는 fc_ord_alowa만 쓰고 다른 칸으로 대신하지 않는다. 근거: 키움 스펙(fc_ord_alowa는 ust21110에만 있음), 2026-10-14 실조회 두 명령 return_code 0.
2. saveticker(6)): 통합 점검은 브라우저를 쓰지 않는다. 06:15 SAVE 작업이 종목 페이지(보유 개별주·MRVL·관심, 지수 ETF·MVLL 제외)를 DOM 글자 추출 스크립트로 읽어 종목별 JSON(해시 대조로 옮겨 적기 오류 차단)과 LATEST_TICKER_LEADS.json을 쓴다. 06:40 점검은 이 파일을 stage해 ROW(표시)·CAND(단서 후보)를 읽고, CAND마다 결과(OFFICIAL·COUNTERPARTY_OFFICIAL·NOT_FOUND·NOT_RELEVANT·SKIPPED_BUDGET)를 대시보드 leads에 남긴다. 확인 상한 6건 + 실적 일정 단서(must).
3. 실적 일정 단서 가드: must = 그 종목이 첫 태그인 실적 일정 기사(정규식 + 결과 기사 제외어). must인데 OFFICIAL이 아니면 그 종목을 미공지로 쓰지 않는다 — 규칙 문장 + 로더 build의 결정론 가드(MRVL→MVLL 포함). 코어는 미공지 아님 = 금지 구간으로 본다(매수 쪽만 막음, p-earn r1과 같음).
4. 기록 전 검증 3: 후보마다 결과 있음, must·must_codes가 파일과 같음, OFFICIAL·COUNTERPARTY_OFFICIAL url은 https이고 뉴스·집계 도메인(deny 목록)이 아님, must는 NOT_RELEVANT·SKIPPED_BUDGET 금지. build도 같은 deny 목록으로 earnings·official_facts url을 거른다.
5. 알림 ⑫: 단서 파일이 오늘·직전 기록 모두 fresh가 아니면 1줄(실적 단서 보호 꺼짐). SAVE 쪽은 묶기 FAILED 2일 연속이면 1줄.
6. 상대 회사 공식 발표: 카드 트리거가 그 상대 회사를 조건으로 적은 경우(U2 TSMC, BE2 Oracle·Blue Owl)만 3)에서 카드대로 판정, 그 밖은 참고. 미확인 보도 state는 바꾸지 않는다.

바꾸지 않은 것: 트리거 기준·근거 강도·호재 기준 (a)·기존 알림 ①~⑪·쓰기 범위(점검은 stage=읽기만)·주문 금지. saveticker 값(목표가·옵션·내부자·공매도)은 표시 전용.

## 3. 시험
- 추출 스크립트: 실제 페이지 NBIS·MRVL·MU·BE·DELL·PWR·LITE, 두 가지 화면 배치(옵션 절 앞·뒤)에서 확인. 나이 표기(분·시간·일·달·한 달·일주일·날짜) 처리.
- 해시: JS canon(키 정렬) = Python json.dumps(sort_keys) — 키 순서 뒤섞인 표시·변조 시험 통과.
- 기기 리허설(2026-10-14 10:0x KST): PWR·BE 저장 SAVED, 묶기 LEADS PARTIAL ok 2/7 must 1 → 점검 6)이 PWR 실적 일정 단서를 must로 냄 → 검증 3 OK.
- build 회귀: 오늘 실제 연구 기록 입력으로 이전·새 build 결과 동일(writer만 다름). PWR must NOT_FOUND면 PWR 미공지 제외. 단서 없음·run-doc 없음에서도 정상(NameError 수정 후).
- 검증 3 실패 사례: 집계 사이트 url, must 누락, 후보 누락, 파일 형식 오류, 오래된 파일.

## 4. 독립 검토
별도 에이전트 2회. 1차 PASS-WITH-CONDITIONS(9건) → 반영. 2차 FAIL 1건(build 줄바꿈 오류로 S 미정의 — 실데이터 회귀로 수정 확인), 나머지 수정 확인. 남은 낮은 위험: must 정규식이 일부 표현을 놓치거나 잘못 잡을 수 있음(잘못 잡으면 매수만 최대 7일 막힘), 둘째 태그 기사는 놓침, ⑫는 고장 동안 매일 푸시.

## 5. 적용 순서(사용자 승인 뒤) — 1)~5) 완료 2026-10-14 10:2x KST
1) 규칙 파일 배치(완료 — 새 이름이라 현행 실행에 영향 없음) 2) SAVE 예약 작업 지시문 교체(trig_01VrX6zRZ8XYGeycXBXo1J3D) 3) 통합 점검 예약 작업 지시문 교체(trig_01YWzNq847nJfNgDUnnukBqP) 4) scheduled-prompts 원문·README 표 갱신 5) 관제판 schedules 갱신. 첫 실제 짝 실행: 다음 날 06:15 → 06:40.
되돌리기: 두 예약 작업을 이전 원문(위 해시, git 이력의 scheduled-prompts/integrated-check-daily.txt·save-market-memo.txt)으로 교체. 규칙 파일 v3.12.2는 그대로 남아 있다.
적용 확인: 교체에 넣은 본문 = pending-st1014/ 파일 = scheduled-prompts/ 원문 = 예약 목록 조회 본문(10:3x, sha256 바이트 일치 — 7절).

## 6. 이번 작업에서 찾은 운영 사실
- PWR: 2026-10-13 06:55 ET 보도자료로 3분기 실적 10/29 장 전 공지(https://investors.quantaservices.com/news-events/press-releases/detail/406/quanta-services-announces-third-quarter-2026-earnings-release-webcast-schedule). 10/14 연구 기록은 회사 목록 페이지를 보고 NOT_ANNOUNCED로 적었다(정정 10:5x: 페이지는 최신인데 WebFetch로 가져온 목록이 28시간 넘게 오래된 사본 — docs/claude/earnings-not-announced-review-2026-10-14.md). 금지 구간(10/27~10/29)이 아직 아니라 오늘 영향 없음. 다음 실행에서 다시 연다.
- 리허설 산출물: workspace/outputs/save-daily-offline-replay/LATEST_TICKER_LEADS.json(PARTIAL, 수동 리허설)과 web-feed/2026-10-14/ticker-PWR.json·ticker-BE.json·ticker-leads-*.json. 현행 점검은 읽지 않는다. 다음 SAVE v2.2 실행이 덮어쓴다.

## 7. 적용 후 남은 위험 재검토 (2026-10-14 10:35~10:50 KST, 사용자 "남은 위험 검토")
| 위험 | 확인한 것(원문·시각) | 판정 |
|---|---|---|
| 예약 지시문이 보관본과 다를 수 있음 | 예약 목록 조회(10:3x)의 지시문 본문 sha256 = 통합 점검 b166bad2…, SAVE 7092f036… — 보관본과 바이트 일치 | 해소 |
| SAVE가 06:40 전에 끝나지 않음 | 10/14 SAVE 메모 쓰기 06:18:59(web-feed/2026-10-14/memo-0618.md 수정 시각). 페이지 7개 추가 — 수동 미리보기 기준 수 분 | 낮음(첫 실행 시각은 확인 필요) |
| must 단서 과잉·누락 | 오늘 7개 종목 페이지 실측(내장 브라우저, 읽기만): 제목 21개 중 must 1개 = PWR "2026년 3분기 실적 발표 및 웹캐스트 일정 발표"(맞음), 잘못 잡은 것 0 | 낮음 |
| 단서 범위 한계(새로 찾음) | 종목 페이지 최신 뉴스는 3건만 보인다. 뉴스가 많은 종목(MU·MRVL)은 실적일 공지가 하루 안에 밀려날 수 있다 → 그날은 예전 경로(회사 IR 확인)만 남음 | 중간 — 회귀 아님 |
| 단서 파일 오래됨 → 가드 꺼짐 | ⑫(2일 연속일 때만)와 SAVE 2일 연속 실패 알림으로 보임. 꺼지면 예전 동작과 같음 | 낮음 — 회귀 아님 |
| ⑫ 반복 알림 | 로그인 만료 때는 SAVE가 이미 매일 알림 — ⑫는 파일이 아예 안 생길 때만(날짜 기준) | 낮음(소음) |
| 회사 IR 목록 페이지로 쓴 NOT_ANNOUNCED가 틀림(근본 원인) | PWR: 10/13 06:55 ET 공지(10/29 장 전)인데 10/14 기록(06:48 KST 확인)이 NOT_ANNOUNCED(10/13 기록 06:50 KST는 공지 전이라 맞음)(목록 페이지 https://investors.quantaservices.com/news-events/press-releases). 10/14 NOT_ANNOUNCED 나머지 DELL·MRVL·MU·NBIS는 10:4x 검색에서 3분기 일정 공지를 찾지 못함(확인 필요). 지난해 공지 시점: NBIS 2025-10-22, MRVL 2025-11-04 | 중간 — 단서 가드는 saveticker에 보일 때만 막음. 지금은 비교 모드(주문표 입력 대상 아님)라 실제 영향 없음 |

첫 짝 실행 자동 확인: 일회성 예약 "st-1014 첫 짝 실행 확인 (10/15 07:20, 1회)"(trig_01U43du9JKcBJS7E9jaR4Uv8, 컴퓨터 필요, 폴더 코덱스저장소, 자동 승인) — docs/claude/st1014-firstrun-check.py(sha256 2c45088d…1b75, 읽기 전용)로 단서 파일·연구 기록·대시보드 기록을 대조해 PASS|CHECK|FAIL 한 줄 푸시. FAIL 조건: 단서 파일 날짜·상태, 연구 기록 writer, run stLeads.day, lead result 형식, must 미확인 종목의 NOT_ANNOUNCED, 외부 도메인 출처, PWR 아직 NOT_ANNOUNCED. 시험: 10/14 실데이터 FAIL 3(예상대로), 합성 PASS·가드·도메인·형식·writer·누락·현금·파일 없음 11건 의도대로.
남은 개선 후보(미적용, 사용자 결정 필요 — 관제판 earn-na): 재검토 결과 "검색 추가"는 철회, 작년 같은 분기 기준 3주 창 권장(docs/claude/earnings-not-announced-review-2026-10-14.md). 첫 매수 판정(10/16 07:45) 전 결정 권장.
