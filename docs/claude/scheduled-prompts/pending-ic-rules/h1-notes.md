# H1 기대 차이 (실행 전 기록, 2026-11-02 KST)
T1 1단계 규칙 확인: 옛 로더+옛 규칙 = MATCH, 새 로더+새 규칙 = MATCH, 새 로더+옛 규칙 = MISMATCH, 옛 로더+새 규칙 = MISMATCH. 출력 형식 같음.
T2 build: 같은 run-doc(10/31 실제 integrated_check_run + 가짜 core 칸 + estimate)·parts로 옛/새 실행 → 새 판 결과에서 integrated_check_run.core만 없음, writer만 v3.12.11, 그 밖 키·값 동일(written_at 제외). core 없는 run-doc이면 옛/새 integrated_check_run 같음.
T3 PRIOR: 10/30·10/31 기록 사본 + 가짜 깨진 폴더 → PWR-20261029-q3-8k가 [10-30 false],[10-31 true] 두 판으로 나옴, 깨진 폴더는 PRIOR-SKIP, DAY 이후 폴더는 안 읽음, 11개 넘으면 최근 10개만.
T4 코어 의미(코어 코드 불변, 함수 직접 호출): 옛 규칙(같은 id 두 판) → 10/31 decide에서 PWR + 강 근거 0개(첫 판 false). 새 규칙(-v2) → + 강 근거 1개(PWR-…-v2). 내림(true→false, -v2 false)은 + 0개 그대로·새 − 근거 안 생김(kind 같으면).
T5 연구 기록 검증 정규식: "-v2"·"-v10" 접미사 id가 build 검사(73행)를 통과, 80자 넘으면 빠짐(기존과 같음).

# H1 결과 (2026-11-02 KST, 클라우드 사본 — 키움·웹·푸시·관제판·대시보드·_pending·예약 실행 없음)
T1 PASS: 옛+옛 MATCH · 옛 로더+새 규칙 MISMATCH · 새 로더+옛 규칙 MISMATCH · 새+새 MATCH(LF·CRLF 둘 다) · 파일 없음 RULES UNREADABLE.
T2 PASS: 10/31 실제 run 사본 + 가짜 core 칸 + estimate → 옛 build는 integrated_check_run에 core를 남김, 새 build는 뺌. core 없는 run이면 옛/새 차이는 writer 한 칸뿐. estimate는 둘 다 뺌. finalize 블록 바이트 같음(sha256 d0a69b1e…).
T3 PASS: 지난 기록 12개 + 깨진 JSON 1 + 오늘 뒤 1 + 파일 없는 폴더 1 → 최근 10개 파일 폴더만(코어 load_research 창과 같은 고르기), 깨진 것은 PRIOR-SKIP, 오늘 뒤는 안 읽음. PWR-20261029-q3-8k가 [10-30 false],[10-31 true] 두 판으로 나옴.
T4 PASS(기대대로) — 코어 함수 official_evidence(원문 그대로 꺼내 실행) + load_research의 setdefault 합치기:
  올림(false→true): 옛 규칙 + 근거 0 → 새 규칙(-v2) + 근거 1 = 독립 계산기와 같은 쪽(10/31 MISMATCH 해소 방향). **매수 회로가 열릴 수 있게 됨 = 매수 막힘 완화(H2 '제약 완화')**
  내림(true→false): 옛·새 모두 10/31 근거 0(첫 판은 10/30에 이미 셈) — 차이 없음.
  kind 바뀜(revenue→guidance, −): 옛 − 근거 0 → 새 − 근거 1(매도 쪽 근거 늘어남).
T5 PASS: "-v2"·"-v10" id 정규식 통과, 81자는 빠짐 → 지시문에 '80자 넘으면 줄임' 1문장 넣음.
LLM 문장 부분(51행·125/126행 트리거 판정·174행 core 붙이기·㉰ 판 비교)은 시험 대상 아님 → 교체 뒤 첫 실행 확인으로 대신(H1 ③).

# 독립 검토 반영 뒤 재시험 (2026-11-02 KST)
검토(Opus, 읽기 전용) 판정 PASS(수정 후). 반영: N11·N12 함께 성립 금지·$20M 문턱 아님 / N12 kind 안내 삭제 / 174행 재시도 때 core 다시 붙이기·get 파일 경로 / -vN은 코어 셈 여부가 바뀔 때만(B 문구 좁힘) / PRIOR 창 9개(코어 07:45 창 = 오늘+9) / 알림 ⑤에 새 ID 안 넣음 명시 / 머리말에 제약 완화.
재시험: T1 새+새 MATCH·새 로더+옛 규칙 MISMATCH · T2 core 빠짐·writer v3.12.11 · T3 앞선 파일 폴더 9개만 · 스키마 fact_id 패턴 ^[A-Za-z0-9._:-]{4,80}$ (-v2 통과, 저장소 schemas 38행) · 독립 계산기 t2rc-oracle.py는 오늘 사실을 그날 기록(1550행 validate_facts(rr…))과 이전 decide facts_seen(1546행)으로 셈 = 코어와 같은 '새 사실' 규칙.
