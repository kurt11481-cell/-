import sys,hashlib
SP='/sessions/rcw-01kumgkivae5ucwboovezgjf/mnt/코덱스저장소/docs/claude/scheduled-prompts/'
newsha=hashlib.sha256(open('/sessions/rcw-01kumgkivae5ucwboovezgjf/work/ceo-v1.5.py','rb').read()).hexdigest()
def P(src,dst,reps):
    s=open(src,encoding='utf-8',newline='').read()
    for o,n in reps:
        assert s.count(o)==1,(s.count(o),o[:60]);s=s.replace(o,n)
    open(dst,'w',encoding='utf-8',newline='').write(s);print(dst,len(s.encode()),hashlib.sha256(s.encode()).hexdigest())
P(SP+'ceo-weekly-meeting.txt','/sessions/rcw-01kumgkivae5ucwboovezgjf/work/ceo-weekly-meeting-v1.5.txt',[
("[투자_V2 · 주간 팀장회의 v1.4.1 — 사장 주간 경영보고(관제판 주간 점검 포함). v1.4.1(",
 "[투자_V2 · 주간 팀장회의 v1.5 — 사장 주간 경영보고(관제판 주간 점검 포함). v1.5(2026-11-13 사장 결정 카드 '유지 + 단순화안 작성'(org-stage2-1113), 설계 docs/claude/ceo-weekly-v15-proposal-2026-11-13.md — 결정 답 = 사장실 결정 카드(일 10:05 사장실 결과 모음이 올림), 관제판 R4·R5·R6은 주간 보고에서 뺌(비서 제안이 매일 봄)·R1·R2는 참고(ℹ) 한 줄, 예약 작업 출근부·통합점검 실행 상태는 이상 줄만, 4)㉲ 비서 제안 폴더 이름 목록 1회 → 운영관리 받은 결과 S-OPS-8. 순서·권한·쓰기 범위는 v1.4.1 그대로). v1.4.1("),
("이전 관제판 주간 점검 v1.2의 점검(R1·R2·R4·R5·R6, 3)에서 받는 check.py 그대로)은 이 작업 안에서 계속하고 출력은 보고 7절에 원문 그대로 둔다.",
 "이전 관제판 주간 점검 v1.2의 점검(R1·R2·R4·R5·R6, 3)에서 받는 check.py 그대로)은 이 작업 안에서 계속 돌리고, 보고 7절에는 R1·R2(장부 어긋남) 줄을 원문 그대로 둔다(R4·R5·R6은 비서 제안이 매일 보므로 python이 보고에서 뺀다 — v1.5)."),
("ceo.py = b1f7cc0c8d9d18bafa1e0e0a08e385541ebb0e3588ba059a4950f0c4853d9d74 인지","ceo.py = "+newsha+" 인지"),
(" 이어서 …\\workspace\\outputs\\next-sandisk-weekly — 파일 이름을 모두 nsdw_files로(폴더가 없거나 실패하면 null).",
 " 이어서 …\\workspace\\outputs\\next-sandisk-weekly — 파일 이름을 모두 nsdw_files로(폴더가 없거나 실패하면 null). 이어서 …\\workspace\\outputs\\secretary — 파일 이름을 모두 secretary로(실패하면 null, v1.5)."),
('"nsdw_files": [...]}(값을 모르면','"nsdw_files": [...], "secretary": [...]}(값을 모르면'),
("정렬·번호·⚠ 표시·답 양식·결정의 주관·협조 팀(근거 제안에서)은 python이 만든다.","정렬·번호·⚠ 표시·답 방법(사장실 결정 카드)·결정의 주관·협조 팀(근거 제안에서)은 python이 만든다."),
("판정 규칙(R1·R2·R4·R5·R6, 팀별 지표,","판정 규칙(R1·R2·R4·R5·R6 — v1.5부터 보고에서 세는 것은 R1·R2, 팀별 지표,"),
])
P(SP+'room-digest.txt','/sessions/rcw-01kumgkivae5ucwboovezgjf/work/room-digest-v1.3.txt',[
("[투자_V2 · 사장실 결과 모음 v1.2 (월~토 09:35 · 일 10:05 KST; v1.2 = ",
 "[투자_V2 · 사장실 결과 모음 v1.3 (월~토 09:35 · 일 10:05 KST; v1.3 = 2026-11-13 주간 팀장회의 v1.5(org-stage2-1113) — 일요일 주간 보고 4절의 새 결정 줄(D)을 사장실 결정 카드로 올리고 카드 답을 보고 파일 답 줄 1줄로 기록(5)); v1.2 = "),
("읽기 + 이 스레드에 글 1건(매일).","읽기 + 이 스레드에 글 1건(매일) + 일요일 결정 카드(새 결정이 있을 때만, 5))."),
(" ⑤ 일요일: 주간 보고 마지막 절의 회사 상태·사장님 결정 N건, 4절 결정 대기·답 기한(있으면 그대로), 5절 '⟨새로⟩' 줄(최대 3개), 팀장 제안 중 순위 1.",
 " ⑤ 일요일: 주간 보고 마지막 절의 회사 상태·사장님 결정 N건, 4절 결정 대기·답 기한(있으면 그대로), 5절 '⟨새로⟩' 줄(최대 3개), 팀장 제안 중 순위 1. 마지막 절 4절의 새 결정 줄('- D<n> …' 또는 '- ⚠ D<n> …' 중 바로 아래에 '답:' 줄이 없는 것)은 5)대로 카드로 올리고, 글에는 'D<n> 카드 올림' 한 줄로만 적는다."),
(" 기기 연결·읽기 실패면 \"결과 모음 확인 불가(PC 연결) — 사장실에서 '오늘 결과' 물어 주세요\" 1건.\n",
 " 기기 연결·읽기 실패면 \"결과 모음 확인 불가(PC 연결) — 사장실에서 '오늘 결과' 물어 주세요\" 1건.\n"
 "5) 일요일 결정 카드(v1.3 — 주간 팀장회의 v1.5의 '답 방법 `사장실 결정 카드`'): 3)⑤의 새 결정 줄마다 request_decision 1장(한 실행에 최대 4장, 넘으면 글에 \"외 N건 — 보고 4절\"). 4)의 글을 먼저 올리고 카드를 올린다. 키 = 'ceo-<그 절 날짜> D<n>'(절 머리 '<!-- id: ceo-… -->'와 D 번호). question = \"주간 회의 <키>: <질문 줄여서>\". options 2~4개 = 줄의 '선택지'(a) b) …)를 짧은 이름으로(선택지가 없으면 '권장대로'·'현행 유지'), 각 consequence는 줄의 문구로만 쓰고 끝에 \"(기록용 — 정책·권한·예약 변경 실행은 따로 승인)\"을 붙인다. recommended = 줄의 '권장'과 같은 선택지(모르면 0). 이 스레드에 같은 키 카드가 이미 있으면 다시 올리지 않는다. 카드가 올라가지 않으면 글에 \"<키> 카드 못 올림 — 보고 4절 직접 확인\" 1줄. 무응답은 보고의 기한이 지나면 다음 주 회의가 '기본값 기록'(현행 유지)으로 닫는다.\n"
 "6) 카드 답 기록(이 스레드가 5)의 카드 탭으로 깨어났을 때만 — 예약 실행 때는 하지 않음): 탭 시각이 일요일 09:40~10:05 KST(주간 회의 기록 중)이면 쓰지 않고 \"<키> 답 기록 보류(회의 기록 중) — Cowork 기록 필요\" 1줄. 그 밖에는 ① device_stage_files로 R\\docs\\claude\\ceo-weekly-report.md를 받아 mtimeMs를 적고 ② 그 절(<!-- id: ceo-<날짜> -->)의 'D<n>' 줄 바로 아래에 \"  - 답: <고른 선택지 이름>(<YYYY-MM-DD HH:MM KST>, 사장실 카드)\" 한 줄만 넣은 사본(다른 바이트·줄바꿈은 그대로, 이미 '답:' 줄이 있으면 넣지 않음)을 device_commit_files(expectedMtimeMs = ①의 값, force 금지)로 쓰고 ③ 다시 받아 넣은 한 줄 말고는 ①과 같은지 확인한 뒤 ④ R\\docs\\claude\\_pending\\ceo-answer-<날짜 8자리>-D<n>.txt(1행 \"docs(claude): ceo weekly answer <키> (room card)\", 2행 \"docs/claude/ceo-weekly-report.md\")를 쓰고 ⑤ 이 스레드에 \"<키> 답 기록: <선택>\" 1줄. 쓰기가 거절·실패하면 다시 하지 않고 \"<키> 답 기록 실패 — Cowork 기록 필요\" 1줄. 카드 답은 회의 결정의 기록일 뿐이고, 정책·한도·권한·예약 작업·코드를 실제로 바꾸는 일은 그 일의 승인 절차를 따로 거친다(이 스레드에서 실행하지 않는다).\n"),
("금지: 파일·대시보드·관제판 쓰기,","금지: 파일·대시보드·관제판 쓰기(예외 = 6)의 보고 파일 답 줄 1줄과 _pending 파일 1개),"),
])
