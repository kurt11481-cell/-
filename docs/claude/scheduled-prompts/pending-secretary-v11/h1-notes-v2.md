# H1 2회차 — 비서 제안 v1 → v1.1(재검토 반영판) 실행 전 기대 차이 (2026-10-22 19시대 KST)
1회차(h1-notes.md, sha256 cb7ab9fb…) 뒤 재검토 반영으로 새 판이 두 군데 바뀜: (a) 열린 목록에 planned도 읽음(id 확인용, 후보 아님) (b) ㉳ 행동 = "조건 확인", k에 K3·권한·한도가 있으면 소개만.
입력: 관제판 tasks 스냅샷 2회차(2026-10-22 19:2x, 이번 세션의 반영 뒤 49건 — decision·waiting·blocked·active·paused·planned) + 가짜 사례 X1~X10. 스크립트가 보는 것은 후보 집합(㉮·㉰·㉱·㉲·㉳)뿐. 고르기 순서(D3)·기록 절(D4)·행동 문구는 지시문 diff로 확인.
기대 차이:
D0 ㉮·㉱·㉲ 집합은 옛·새 같다(㉯는 입력 없음).
D1 ㉳는 새 판에만 — obs-1022b ⑤ 정의 그대로(waiting event·manual: 날짜 있으면 ≤ TODAY, 없으면 갱신 7일 넘게 / paused: after[] 있고 모두 열린 목록에 없음).
D2' ㉰: 새 판은 열린 목록에 paused·planned를 더함 → after[]에 paused 또는 planned 작업이 있는 waiting은 옛 판에서만 ㉰. 실제 관제판에서는 0건 예상(나오면 목록·사유를 적음).
가짜 사례: X1·X3·X5 → ㉳ · X2·X4·X6·X7·X9 → 아님 · X8(paused 선행)·X10(planned 선행) → 옛 ㉰만.
실제 관제판(포인터 = 재검토 에이전트 계산, 실행으로 확인): TODAY 10/22·10/23 ㉳ = {e-new, redesign-t2}. TODAY 10/23 ㉰ = {decide-research-gap, iv-c1c2, r-wd-1022}.
측정만(기대 없음): 갱신이 하나도 없다고 가정한 TODAY 10/26·10/29·11/05의 ㉳ 건수.
금지 지킴: 키움·웹 조회, 푸시, 관제판·artifact 쓰기, _pending 쓰기, 예약 실행 없음.
