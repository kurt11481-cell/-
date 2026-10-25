---
id: ceo-weekly-v141-proposal-2026-10-25
type: change-proposal
status: applied (2026-10-25 20:56 KST)
as_of: 2026-10-25
summary: "주간 팀장회의 v1.4 → v1.4.1: 팀장회의 대시보드 갱신(11-1) 단계만 뺀다. 보고는 ceo-weekly-report.md와 사장실 채팅."
consumers: 사장 · 사장실 코디네이터 · 회사PC 스레드
source_decision: "사장 2026-10-25 20:43 KST(스레드 직접 입력) '결정 dash-1025: B' — board-merge Q2 a '하지 않음'의 '주간 대시보드 즉시 폐기'를 사장이 다시 열어 대체함"
authority: "order_authority=false · quantity_authority=none · 이 문서는 제안. 지시문은 아직 바뀌지 않음"
---

# 주간 팀장회의 v1.4.1 변경 제안 (A 종류)

## 1. 한 줄
팀장회의가 사장용 '주간 팀장회의' 대시보드에 데이터를 올리는 11-1) 단계만 뺀다. 이름은 v1.4.1이다(v1.5는 board-merge Q2 a의 주간 보고 합치기용으로 남겨 둠).

## 2. 승인 전 5줄 (지침 v1.8 4절 ②)
1. 지금 지시문 sha256: `5590056c9690dc536e7af9cedd1e87cf75609d02351e1adae675c5df3ff15d7a` (docs/claude/scheduled-prompts/ceo-weekly-meeting.txt, README 기록과 같음). 클라우드에 올라 있는 판과 바이트 단위 일치는 **확인 필요**(머리·핵심 줄 눈 대조만 함, 10/25 get_trigger).
2. 바꿀 지시문 sha256: `a7b1273597c545b5cbb3adf5b8f5479860f7fa84f526d2669937aa4b301c5423` (scheduled-prompts/ceo-weekly-meeting-v1.4.1-draft.txt, 23120 B, LF).
3. 바뀐 곳(5곳, 줄 수 49 → 45): ① 머리 줄 v1.4.1 표기와 결정 인용 ② 절대 금지의 대시보드 줄: "11-1의 두 가지만 쓴다" → "어떤 대시보드도 쓰지 않는다" ③ 11-1) 4줄(㉠~㉣)을 삭제 안내 1줄로 ④ 12) 알림의 "대시보드 갱신 실패" 덧붙임 삭제 ⑤ 출력 (e)의 대시보드 칸 삭제. 나머지(순서·스크립트·권한·알림 1건)는 그대로.
4. 그대로인 것: 일정 일 09:47 KST · 모델 claude-sonnet-5-5 · 폴더 코덱스저장소 · 권한 모드 auto · check.py `1963295f…` · ceo.py `b1f7cc0c…` · 연결 3개.
5. 되돌리는 법: 위 sha `5590056c…`인 ceo-weekly-meeting.txt를 `update_trigger`로 다시 넣는다(PC 승인 창 1회). 적용 때 그 파일을 `pending-ceo-weekly/ceo-weekly-meeting-v1.4.txt`로 복사해 보관한다.

## 3. 효과와 남는 것
- 사장이 볼 화면이 4개에서 3개(통합점검·관제판·현황판)로 줄어든다. 팀장회의 대시보드 페이지는 지우지 않고 마지막 갱신(10/25 09:55)으로 남는다. 읽는 예약 작업은 없다(조사 2절).
- 지침 6절의 첫 메시지 보고가 일요일 주간 보고 1~3줄을 맡는 것은 별개이며 승인 없이 가능하다.
- 첫 확인: 11/1 09:47 실행 뒤 `ceo-weekly-report.md` 갱신 시각과 대시보드 `datasets/weekly.updated` 불변.

## 4. 다음 승인
사장이 이 스레드에 `예약 작업 변경 승인: 주간 팀장회의` 한 줄을 직접 쓰면 `update_trigger`를 호출한다. 이 호출은 PC 승인 창(사장이 직접 클릭)이 필요하다. 승인은 오늘(KST) 1회만 유효하다.

## 5. 부딪히는 결정
board-merge Q2 a '하지 않음'의 "주간 대시보드 즉시 폐기"(ceo-room-merge-2026-10-22.md:65). 사장 결정 dash-1025 B가 이것을 대체한다. ④(제약 완화 중 ceo-weekly-meeting 관제판 쓰기 금지 완화)는 건드리지 않는다.
