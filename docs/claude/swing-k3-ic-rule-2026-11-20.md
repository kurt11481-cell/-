# 통합 점검 규칙 v3.12.19 — 상품 승인 목록에 PLTR·CRWD 추가 (swing-k3 후속)

- 날짜: 2026-11-20 KST
- 근거: 사장 결정 카드 'PLTR·CRWD+등록부 정리' 15:39:42 KST, 착수 직접 입력 16:04:53 KST, 정책 병합 커밋 3815698 18:52 KST(docs/claude/swing-product-approval-k3-2026-11-20.md, swing-k3-judge-report.md PASS), 사장 직접 입력 "멈추지말고 계속 진행해" 18:55 KST.
- 상태: 준비 끝, 적용 전. 적용에는 사장 직접 입력 `예약 작업 변경 승인: 보유·관심 종목 통합 점검` 이 필요하다(지침 4절 ①).

## 왜

자동 운영 코어(auto_core_tickets.py APPROVED_BUY)는 3815698부터 PLTR·CRWD를 신규 매수 승인 상품으로 본다. 통합 점검 규칙 134행 상품 승인 목록에는 아직 없어서, 그대로 두면 아침 점검 표의 PLTR·CRWD 행 ②가 "막힘 — 상품 승인 없음"으로 나와 코어와 어긋난다.

## 바꾸는 것 (두 파일, 그 밖은 그대로)

1. 규칙 파일 새 판 docs/claude/integrated-check-prompt-v3.12.19-2026-11-20.txt
   - v3.12.18과 다른 곳은 134행 한 곳: `PWR·LITE(2026-10-08 사용자 승인)` 뒤에 `·PLTR·CRWD(2026-11-20 사장 결정 swing-k3-1120, 정책 커밋 3815698)` 추가.
   - 줄 수 400 그대로(로더의 줄 번호 구간 54~157·161~173·174~175·176~331·332·334~400 그대로).
   - sha256(LF) e1d0de82cc3adbcca5248062361cb16f6943117c8900066b9d6721714f6505f0, 144,460 B.
2. 로더(예약 지시문) docs/claude/scheduled-prompts/pending-swing-k3-ic-1120/integrated-check-daily.txt
   - 1행 맨 앞에 v3.12.19-L+R2 판 설명, 규칙 파일 경로 5곳 v3.12.18→v3.12.19, 1단계 해시 fed3dc33…→e1d0de82….
   - build·finalize·fix1 구간 해시 그대로(대조 확인).
   - sha256 394d55e09d17bb6e4956478c2df4c031c047f7a6a43713c73fc0c0df206e118d, 42,049 B.

## 확인한 것

- 규칙 파일 안에서 상품 승인 목록이 적힌 곳은 134행 한 곳뿐(4행은 옛 판 이력, 161·165·324행은 '상품 승인 없음' 문구만 씀).
- ④ M6 비교 카드: m6-relative-comparison-7stock-2026-10-17.md에 PLTR 12회·CRWD 1회 나와 grep 기준 통과(코어와 같음).
- 바뀌지 않는 것: 판정 기준·노출 관문·알림 조건·쓰기 범위·이름·일정·모델·폴더·자동 승인.
- 지금은 새 매수가 fail-closed로 멈춰 있어(②의 노출 칸 막힘) 이 변경으로 바로 매수 검토가 열리지 않는다. CRWD는 7/2 4:1 분할 기록이 corporate-actions.json에 없어 코어 주문표가 SPLIT_SUSPECTED로 따로 막힌다(별건).

## 적용 순서

1. 사장 직접 입력 `예약 작업 변경 승인: 보유·관심 종목 통합 점검`.
2. 회사PC 비서실(Cowork) 대화에 한 줄: "보유·관심 종목 통합 점검 예약 작업 지시문을 docs/claude/scheduled-prompts/pending-swing-k3-ic-1120/integrated-check-daily.txt로 교체, 이름·일정·모델·폴더 그대로" → 승인 창.
3. 교체 뒤 예약 본문 sha256 = 394d55e0… 확인, 저장소 scheduled-prompts/integrated-check-daily.txt를 같은 파일로 바꾸고 README 행 추가.
4. 다음 06:40 실행에서 1단계 RULES MATCH, PLTR·CRWD 행 ② 상품 승인 칸이 '없음'으로 막히지 않는지 확인.

## 되돌리기

docs/claude/scheduled-prompts/pending-pick-6c-1119/integrated-check-daily.txt (sha256 90a6fbca…, v3.12.18-L+R2)로 교체. 규칙 파일 v3.12.18(fed3dc33…)은 그대로 남아 있다.

## 사장 결정

- 2026-11-20 19:02:15 KST 사장 직접 입력(사장실 스레드 '스윙 종목 상품 승인 넓히기'): `예약 작업 변경 승인: 보유·관심 종목 통합 점검`. 교체는 회사PC 비서실 대화에서(스레드 update_trigger는 needs_device_approval 선례로 시도하지 않음).
- 2026-11-20 19:05 KST 비서실 교체 완료: update_trigger 응답 "prompt re-signed by 금동한"(updated_at 2026-11-20T10:05:45Z). 넣은 본문 394d55e0…(42,049 B). 이름·일정·모델·폴더 2개·자동 승인 불변. 보관본 scheduled-prompts/integrated-check-daily.txt = 394d55e0…(build·finalize·fix1 MATCH), 옛 판 90a6fbca…는 pending-swing-k3-ic-1120/integrated-check-daily-v3.12.18.txt로 보관. README 행·변경 기록 갱신. 응답 바이트 해시 대조는 못 함(확인 필요) — 11/21 06:40 첫 실행(적용 순서 4번)으로 확인.
