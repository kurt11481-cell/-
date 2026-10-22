# H1 — 비서 제안 v1 → v1.1 (멈춤 의심) 변경 전 결정론 시험 — 실행 전 기대 차이 (2026-10-22 KST)
입력: 관제판 tasks 스냅샷(2026-10-22 19시대, decision·waiting·blocked·active·paused·planned 42건 — 비서는 planned를 읽지 않으므로 시험에서 제외) + 가짜 이상 사례 X1~X9. TODAY=2026-10-22.
기대 차이(이것 외의 차이는 결함):
D0 ㉮ 결정 · ㉯(주간 보고 — 이 시험 입력 없음, 양쪽 0) · ㉱ 막힘 · ㉲ 오래 멈춤 후보 집합은 옛·새 같다.
D1 새 판에만 ㉳ 멈춤 의심이 생긴다 = (waiting이고 resume.type이 event 또는 manual이며, resume.date가 있으면 date ≤ TODAY, 없으면 updatedAt이 TODAY보다 7일 넘게 앞섬) ∪ (paused이고 after[]가 비어 있지 않으며 after[]의 작업이 모두 열린 목록(decision·waiting·blocked·active·paused)에 없음). paused의 after[]가 비면 표시하지 않는다.
D2 ㉰ 재개 가능: 새 판은 열린 목록에 paused를 더하므로, after[]에 paused 작업이 들어 있는 waiting 작업은 옛 판에서만 ㉰에 뜬다(오탐 제거 — 제약 완화 아님). 그 밖의 ㉰ 차이는 결함.
D3 고르기: 순서 끝에 ㉳가 붙을 뿐 ㉮~㉲ 사이 순서는 같다. 오늘 고른 3건은 ㉳가 4번째 이후라면 같다.
D4 출력: 새 판은 "## 멈춤 의심 (팀 처리)" 절이 추가된다(id · 쉬운 이름 · 조건 · 마지막 갱신). 머리말 items는 고른 id만(형식 같음).
가짜 사례 기대: X1 event date=TODAY → ㉳ · X2 event date=내일 → 아님 · X3 manual 날짜 없음, 갱신 8일 전 → ㉳ · X4 manual 날짜 없음, 갱신 6일 전 → 아님 · X5 paused after=[없는 id] → ㉳ · X6 paused after=[waiting 작업] → 아님 · X7 paused after=[] → 아님 · X8 waiting after=[X5(paused)] → 옛 ㉰ 뜸, 새 ㉰ 안 뜸 · X9 resume 없음 waiting → 양쪽 아무 후보 아님(㉳ 아님).
금지 지킴: 키움·웹 조회, 푸시, 관제판·artifact 쓰기, _pending 쓰기, 예약 실행 없음.
