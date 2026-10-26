---
id: active-decisions
type: index
status: current
as_of: 2026-10-25
summary: "지금도 유효한 사장 결정을 한곳에서 찾는 색인. 보기용 사본 — 원본은 각 문서(열 '원문'). 변경 제안 전에 대상 키워드(예약 작업 이름, 대시보드, 규칙 이름)를 여기서 먼저 검색한다."
consumers: "사장실 코디네이터 · 회사PC 스레드 · 클라우드 스레드(읽기용 사본으로만)"
authority: "order_authority=false · quantity_authority=none · 이 색인은 판단 근거가 아니라 입구. 이 색인과 원문이 다르면 원문이 맞다"
source_decision: "사장 2026-10-25 20:13 KST(스레드 직접 입력) '스레드가 기존 cowork의 \"Q2 a\"를 읽지 못한 것은 심각한 결함임' → 코디네이터 지시"
---

# 현행 결정 색인 (2026-10-25)

## 쓰는 법
1. 무엇을 바꾸자고 제안하기 **전에** 대상 키워드(작업 이름, 대시보드 이름, 규칙 이름, 결정 id)를 이 파일에서 검색한다.
2. 걸리는 항목이 있으면 '조건/만료'와 '하지 않음'을 읽고, 원문 파일·행을 열어 확인한 뒤 제안한다. 부딪히면 제안서 첫 줄에 어떤 결정과 부딪히는지 적는다.
3. 이 색인은 **보기용 사본**이다. 결정 일지·관제판 결정함·결정 문서 원본은 고치지 않았다. 새 결정이 생기면 원본에 먼저 기록하고 이 색인에 한 줄 추가한다(아직 자동 갱신 아님 — 아래 '한계').
4. 표의 행 번호는 2026-10-25 20시대 KST에 grep으로 확인한 값. 행이 밀렸으면 id·문구로 다시 찾는다. 행 없이 '절'만 적은 칸은 그 절을 직접 읽어 확인하지는 않은 것(검색 결과만 봄).

## A. 예약 작업·대시보드·창구 (제안이 가장 자주 부딪히는 곳)

| 결정 id · 날짜(KST) | 한 줄 내용 | 조건/만료 · 하지 않음 | 대상 | 원문 |
|---|---|---|---|---|
| **board-merge Q1 a · Q2 a** · 2026-10-23 00:20 (00:19의 Q1 c·Q2 b를 대체) | Q1 a = 관제판 HTML 재게시(표시만) + 비서 제안 v1.2가 관제판 briefs 문서 1개를 쓰기 + dev-dashboard-protocol 1줄. Q2 a = 주간 보고까지 합치기를 **사전 등록만** | **Q2 조건**: org-setup 2단계 평가(보고 4회) ⓐ 통과 **그리고** briefs가 2주 연속 월~토 매일 생성 → 그때 주간 팀장회의 v1.5 교체를 **별도 승인**으로 제안. 미충족 = 지금 구조 유지(알림만). Duet 1주 시험이 먼저 통과하면 R5·R6을 따름. 사장이 주간 대시보드를 따로 보길 원하면 조건과 무관하게 유지. briefs 2주 안 생성 실패 2회 이상 → 비서 쓰기 되돌림 | 주간 대시보드(팀장회의), 관제판, 비서 제안 v1.2, 주간 팀장회의 v1.5 | ceo-room-merge-2026-10-22.md:5 · 58-61(Q2 a 조건) · 71-74(바뀔 조건) · 82-86(기록) |
| **dash-1025 B** · 2026-10-25 20:43 KST (사장 스레드 직접 입력) | board-merge '하지 않음' 중 **'주간 대시보드 즉시 폐기'만 대체**: 주간 팀장회의가 대시보드에 쓰는 11-1)을 빼는 v1.4.1(4개 → 3개) | 적용은 별도 `예약 작업 변경 승인: 주간 팀장회의` + PC 승인 창. **적용 완료 2026-10-25 20:56 KST(v1.4.1, updated_at 11:55:59Z, sha a7b12735…, 확인: get_trigger 지시문 머리 v1.4.1)**. 통합점검·현황판 합치기·관제판 이전은 여전히 하지 않음. Q2 a의 v1.5 조건 유효 | 주간 팀장회의 대시보드 | ceo-weekly-v141-proposal-2026-10-25.md · ceo-room-merge-2026-10-22.md:88 |
| 〃 **'하지 않음' 목록** (같은 결정에 묶임) | 아래는 하지 않기로 한 것 | **주간 대시보드 즉시 폐기**(10/25 첫 예약 갱신·보고 4회 평가 중) · **통합점검·미국주식 현황판 합치기**(duet-redesign 3-3 유지) · **관제판 작업 데이터를 비서·팀장회의가 고치기** · **새 예약 작업** · **팀 작업을 예약 작업이 스스로 착수하기**(Duet·Projects 비서 자리) · **관제판을 Dashboard 유형으로 다시 만들기**(편집·결정함 기능 없음). 버린 대안: 주간 대시보드에 비서 일일 보고 넣기 · Cowork가 비서 파일을 관제판에 옮기기 · briefs에 작업 문장 복제(id만) | 예약 작업, 대시보드 4개 | ceo-room-merge-2026-10-22.md:63-65 |
| 〃 제약 완화 ①~④ | 비서 쓰기 범위 확대는 obs-sys-sec 승인 때 적용. ④(ceo-weekly-meeting.txt "관제판 쓰기 금지" 완화)는 Q2 조건 충족 때만 | 이 결정만으로는 지시문·프로토콜을 바꾸지 않음 | secretary-daily, ceo-weekly-meeting, dev-dashboard-protocol | ceo-room-merge-2026-10-22.md:50 · 85 |
| **sc-1022 Q1 a · Q2 a** · 2026-10-23 00:05 | 창구 하나 지침 S1~S7 채택(비서실 1개, 그날 첫 메시지에 1~3줄 먼저 보고, 승인은 바로 앞 제안 1건·1회·같은 날) | **S4: 예약 작업 만들기/바꾸기/지우기, 정책·한도·권한·주문 단계·보호 경로·제약 완화·기억 쓰기를 바꾸는 선택은 카드로 받지 않고 사장이 직접 친 메시지로만**. 운영 시작 +14일에 자체 평가. CLAUDE.md 4곳 반영은 duet-k1 묶음 대기 | 모든 승인류, 예약 작업 변경 | single-channel-redesign-2026-10-22.md:46 (S4) · 122 (기록) |
| **예약 작업 변경 절차** (상시) · 2026-10-09 이후 누적 | 변경 전 H1 시험(옛·새 판을 입력 복사본으로 비교, 외부 호출·쓰기·알림 금지), 검사 항목 수 감소·등급 변경이면 요청 첫 줄에 "제약 완화"(H2). 지시문 sha256·변경 기록을 README에 남김. 사장 직접 승인 + PC 데스크톱 앱 승인("prompt re-signed") | 기존 작업에도 적용(ext-1022b a, 2026-10-22) | 모든 예약 작업 | scheduled-prompts/README.md:5 · 변경 기록 53-67 |
| **예약 작업 변경 승인 문구**(프로젝트 지침 v1.8 4절) · 2026-10-25 | 사장실 스레드에서 `예약 작업 변경 승인: <이름>` 한 줄로 만들기·바꾸기·지우기 허용(A종류=읽기·알림·문서만; B종류=키움 읽기·대시보드 쓰기·점검 약화·코어 입력은 H1+독립 검토 뒤) | 상시 금지(어떤 승인으로도): 주문 관련, 키움 주문 도구·kiwoom_commands, apply·정책/상태 쓰기·auto_core.py 실행, 예약이 예약을 바꾸기, 권한 모드 상향, 연결 폴더 추가. 코어 입력·한도에 닿으면 K3 | 예약 작업 | schedule-dashboard-redesign-2026-10-25.md:94-101, 106-113 · 지침 v1.8은 repo 밖(원문 확인 필요) |
| **schedule-dashboard 결정 1·2** · 2026-10-25 | 결정 1 = 지침을 4절대로 고쳐 예약 변경 허용, 결정 2 = 6절 ①(그날 첫 메시지 보고에 일요일 주간 보고 포함) 오늘 적용·② 4절 반영 뒤 | 6절 ④ 관제판은 **NO_CHANGE**(기계용 장부로 유지, 채팅이 결정 대기를 요약). 사장 답 원문은 이 repo에서 못 찾음 → 지침 v1.8에 반영된 것만 확인 | 프로젝트 지침, 관제판 | schedule-dashboard-redesign-2026-10-25.md:142-145 (제안) · 6절 120-135 · 사장 답 **확인 필요** |
| **org-setup Q1 a · Q2 a · Q3 a** · 2026-10-19 12:38, 이어 "그렇게 해" 12:47 | 4팀+감사실+리스크·권한위원회 / 관제판 주간 점검 작업을 주간 팀장회의(일 09:47)로 바꿔 씀(예약 순증 0) / 매주 1줄 푸시(실행당 1건). 결정 개수 상한 삭제 | 2단계 평가(보고 4회)가 board-merge Q2 조건에 걸림 | 주간 팀장회의 trig_01XvqwKG…, 알림 | company-org-plan-2026-10-19.md:4 · 219-224 · 258 |
| **paperclip-1019 Q1 · Q2 a** · 2026-10-19 23:12 (Q1은 23:07 지시문 승인) | Q1 = 예약 작업 출근부를 주간 팀장회의 v1.3에 포함 / Q2 a = '새로/계속 n주째' 구분 채택(v1.4) | 관제판 paperclip-1019 기록으로 확인(I절) | 주간 팀장회의 | paperclip-review-2026-10-19.md:56-58 · 66 · company-org-plan-2026-10-19.md:265 |
| **duet-1022 Q1 a · Q2 a · Q3 a · Q4 a** · 2026-10-22 18:41 | Q1 입구 노트·정리·R3a 일지 확인 코드 제거(A3 a 이행) / Q2 뼈대 첫 순서 K-1 결정 원장(duet-k1 planned) / Q3 Duet 접속면 계약 + 열리면 1주 시험(duet-trial waiting) / Q4 권한·한도 대기열 duet-q4-coreinput → duet-q4-recon 순서 등록 | Duet이 사장 계정에서 열려야 시험 착수. Duet 경유 불가 결정: 일지 확인·대조 확인·정책/상태·권한 착수·병합(K-5 전까지 Cowork). K-5 올릴지는 사장 답 대기 | Duet, 결정 원장, 권한 대기열 | duet-redesign-2026-10-22.md:12 · 98-103 · 116-124 · duet-interface-contract-2026-10-22.md:5 |
| **duet-sec 승인** · 2026-10-22 19:23 | 비서 제안 v1 → v1.1(멈춤 의심 ㉳) 교체 완료 19:25 | 첫 실행 10/23 09:25 확인 대기였음(확인 결과는 이 repo에서 못 찾음) | secretary-daily trig_01QL11yZ… | secretary-v11-change-2026-10-22.md:5 · scheduled-prompts/README.md:65 |
| **obs-sys Q1 a · Q2 a** · 2026-10-22 23:13 | Q1 볼트 보기(00-views.base 3개, backlink) 완료 23:2x / Q2 비서 v1.2에 ceo-inbox 개수 ㉴ | Q2는 board-merge Q1과 **한 번에** `결정 obs-sys-sec: 승인(비서실 문구 포함, briefs 쓰기 포함)`으로 교체(승인 문구 고정). 비서 v1.2 교체 여부는 이 repo에서 못 찾음(확인 필요) | 비서 제안, 00-home | obsidian-system-wide-research-2026-10-22.md:90-92 · ceo-room-merge-2026-10-22.md:49 |
| **obs-1022b Q1 a** · 2026-10-22 (00-home source_decision = duet-1022 Q1 a ③) | Obsidian 볼트 = docs/claude 읽기 보기, 지식 문서 사본 제외 | 편집은 ceo-inbox/ 새 노트만. 고치면 안 되는 파일 표(00-home) | 00-home, 볼트 | 00-home.md:1-30 · obsidian-ops-review-2026-10-22.md:63-71 |
| **pb-1022 Q1 a · Q2 a** + E1·E2 도입 · 2026-10-22 06:04 | 플레이북 표준(H1/H2 포함) 채택 + 입력 출력칸·반복 실패 처리 2개 | Munder Difflin 도입 안 함. 사장 인터뷰 1회(주제 카드 수락 기준) | 플레이북, 예약 지시문 | delegation-loop-review-2026-10-22.md:83-102 · playbooks/README.md:1 |
| **secretary-1021 a / secretary-daily 승인** · 2026-10-21 20:19/20:23 | 비서 제안 예약(월~토 09:25) 생성, 쓰기 = workspace/outputs/secretary/<날짜>.md 1개 | Projects/Duet 비서 자리와 겹치는 확장은 위 board-merge '하지 않음' | secretary-daily | secretary-agent-idea-2026-10-21.md:153-155 · scheduled-prompts/README.md:62 |
| **skel-1022** (기한 2026-10-29) | Q1 S2+S4+S6 / Q2 S1 사전 등록부터 — **사장 답 기록을 못 찾음** | 무응답 = 전부 NO_CHANGE | 뼈대 후보 | skeleton-review-2026-10-22.md:64-67 · 답 **확인 필요** |
| **yt-dlp 자막 시험 승인** · 2026-10-25 (사장 스레드 직접 입력) | 코덱스저장소 밖 `%USERPROFILE%\yt-dlp-test` venv에 yt-dlp==2026.8.19만 설치, 공개 영상 자막만 받는 1회 시험 — 성공 | 쿠키·로그인·키움·주문·다른 패키지·전역 설치 금지. 시험 외 사용은 별도 승인 | 자막 수집 | yt-dlp-subtitle-procedure-2026-10-25.md |

## B. 승인·창구·규칙(CLAUDE.md) 쪽

| 결정 id · 날짜(KST) | 한 줄 내용 | 조건/만료 · 하지 않음 | 대상 | 원문 |
|---|---|---|---|---|
| **dc-dev Q1 a · Q2 a** · 2026-10-22 15:17 (앞서 cs-1022 "1,2번 전면 도입, 권한을 넓힌다" 13:55) | 일반 변경 병합은 Cowork가 dev-merge 실행(`-ApproveAuthority` 없이) / 권한·한도 수동 경로 Builder·Judge도 사장 승인 뒤 Cowork가 띄움, 병합은 사장 결정 뒤 | 권한 승격 run에 `-ApproveAuthority`는 사장 결정을 현재 대화에서 받은 뒤만 | 개발 파이프라인 | dc-dev-2026-10-22.md:7 · 14-15 · CLAUDE.md:52-66 |
| **D4 b · D2 · D1 a** (진단) · 2026-10-25 08:15Z, 병합 bb11f04 | 사장실 스레드에 사장이 직접 친 메시지를 승인으로 인정(바로 앞 제안 1건·같은 날·1회), 승인류 공식 경로 = 사장 PowerShell 한 줄, 관제판 갱신을 사장실 스레드 허용 | 코디네이터가 옮긴 인용·버튼·카드·예약 턴은 승인 아님. **projects-new의 '승인 이전 중단'(11:32 KST)은 D4 b(17:15 KST 승인, 17:43 병합)보다 먼저라 Change classes 부분은 D4 b가 나중·유효. 효력 원본 = CLAUDE.md:63-66.** apply·일지·정책/상태·decision_mode는 사장실 스레드가 계속 실행 안 함(Q1 아니오, 지침 4절은 CLAUDE.md보다 좁게 스스로 제한한 것) | 승인 장소 | operating-diagnosis-2026-10-25.md:232-240 · CLAUDE.md:58-66 · d124-builder-report.md · 지침 v1.8 원문 대조는 **확인 필요** |
| **Q1 (Claude Code가 apply 실행)** 아니오 · 2026-10-25 08:17Z | Hard safety 현행 유지: reconcile apply·일지 쓰기를 Claude Code·Codex·예약·Judge는 하지 않음 | — | 대조 apply, 결정 일지 | operating-diagnosis-2026-10-25.md:234 · CLAUDE.md Hard safety |
| **D6·D3·D11·D12, N1·N2, D5·D8** · 2026-10-25 08:46Z~09:34Z | CLAUDE.md 문구 정리 병합(96f1e6a, fbdede9), 새 규칙·문서·예약 동결 + archive 후보, 복구 점검 1회 PASS, 세무 1줄 연결, 지침 2절 우선순위 예외·상위 사슬 | D5·D8은 지침 v1.7에 코디네이터가 반영(원문 직접 확인 못 함) | CLAUDE.md, 지침 | operating-diagnosis-2026-10-25.md:232-240 · d6-judge-report.md · n12-judge-report.md |
| **D3 동결** (위와 같은 결정) | **새 규칙·문서·예약을 늘리지 않는다**(동결) + 끝난 작업 archive 이동 후보 목록 | 이 색인 자체가 '새 문서'지만 코디네이터 지시로 만든 입구용(규칙·예약 아님). 동결 범위 해석은 확인 필요 | 전반 | operating-diagnosis-2026-10-25.md:218(D3) · 238 · archive-candidates-2026-10-25.md |
| **projects-new Q1 b · Q2 b** · 2026-10-25 10:18 / 승인 인정 (나)·단계적 효력 아니오 10:33 / 추가 5 Cowork 유지 10:50 | Projects 새 판 설계. **11:32 승인 이전(K3 ①) 중단 — 승인류는 지금처럼 Cowork에 직접 입력, CLAUDE.md 해당 줄 현행 유지. 단 Change classes 승인 인정은 17:43 D4 b 병합(bb11f04)으로 '일부 대체됨'** | 추가 4·6 무응답 = Cowork 유지. 12:24 "전부 예"로 Projects K3 종결·남은 문구는 일반 변경으로 축소, **cf-b2n 병합 승인은 따로 입력** | 승인 장소, 사장실 | projects-new-board-design-2026-10-26.md:5 · 27-37 · 85 · 106-118 · stalled-work-inventory-2026-10-25.md:81-82 |
| **approval-venue 표** · 2026-10-25 10:30Z "권장안대로"(Projects 진단 결정 1·3) | 승인류별 입력 장소 안내표(규칙 변경 없음, 안내만) | 표는 안내, 원본은 CLAUDE.md 줄 | 안내 | approval-venue-table-2026-10-25.md:1-12 |
| **projects-1025** (기한 2026-11-01) | Q1 Projects 운영·Q2 Mods — **사장 답 없음**(Q2 미답) | 무응답 = Q1 c·Q2 c 현행 유지(설치된 모드 없음) | Projects, Mods | projects-mods-adoption-2026-10-25.md:5 · 95-103 · projects-handoff-2026-10-25.md:26 |
| **projects 이사 지시** · 2026-10-25 09:11~09:35 | "새 판: a" — 실행층·점검층 그대로, 소통층·규칙층만 Projects 기준으로. 모든 권한 승인이지만 주문·키움 주문 도구 금지는 불변. 키움 MCP는 사장이 켜 두기로 결정(지침 v1.2) | K3 병합은 Judge 결과를 본 뒤 사장 한 줄 | 소통층 | projects-handoff-2026-10-25.md:12-15 · 23 |
| **자동 코어 5·8번 근거 결정** (아래 C와 겹침) | CLAUDE.md Change classes 항목 전체가 현행 규칙 | — | 개발 변경 등급 | CLAUDE.md:52-71 (Change classes) |
| **관제판 완료 표시 (키움 주문 차단 보강 4건)** · 2026-10-26 11:40 | 키움 주문 차단 보강 4건 완료(병합 c9c0877·5cf97e3, 훅 시험 Bash·Monitor 거절). 확인 필요: 원격 스레드·Cowork 발동 여부 | 훅은 약화하지 않음. 개발 큐 Builder 막힘의 원인은 훅이 아니라 지시문(builder-blocked-diagnosis-2026-10-26.md) | 키움 주문 차단 | kiwoom-block-hook-test-2026-10-26.md:12-24 |

## C. 운영 규칙·정책(자동 코어) — 지금도 유효한 것

| 결정 id · 날짜 | 한 줄 내용 | 조건/만료 | 대상 | 원문 |
|---|---|---|---|---|
| **재설계 A1~A7 모두 a** · 2026-10-10 09:27 | 결정론 자동 코어 1순위(A1), FX-1009 동결 해제(A2), 확인 코드 폐지·3-5 불변조건 통과 시 자동 기록(A3), 현금 = 주문 가능액(A4), 변경 2등급·키움 승인 고정 폐지(A5), 관심 명단 주간 재채점 자동 모드·Next 샌디스크 제안 모드(A6), **주문 1단계(주문표)까지만, 2단계는 조건 충족 때 다시 질문**(A7) | 헌법 1.3.0 반영. 루틴 사장 손 0(키움 주문 입력 제외). decision_mode 비교 중 → 사장 "켜" 전까지 주문표 '비교 중' | 전반 | automation-redesign-2026-10-10.md:166-178 · 207 · CLAUDE.md:1-17 |
| **redesign-t2: Q1 a, Q2 b, Q3 c, Q4 a, P-1 적용, P-2 적용** · 2026-10-12 11:21 | 코어 판정 K3 1~5·7~9 채택, 재발행 상한은 그날 기준가 산식(연속 미입력 2회면 닫힘), 1회 크기·하루 건수 관문 없음 | 2회 이상 미입력 처리 포함 | 자동 코어 정책 | redesign-t2-merge-decision-2026-10-12.md:12 · 표 첫 열 Q1~Q4 |
| **R-REC1 회복 관문** · 2026-10-09 02:54 지시 + **rrec-ev4 REMOVE** 2026-10-19 17:45, 병합 승인 20:38, 병합 5d5cf79 | 충격 사건 뒤 노출 증가 매수는 RG1 등을 통과해야 함. EV4(계좌 총액 사건)는 제거됨 | EV3 등 이벤트 줄을 지우면 관문이 풀림(00-home 경고) | 매수 관문 | recovery-gate-R-REC1-2026-10-09.md:4 · rrec-ev4-remove-decision-2026-10-19.md:4 · 67 |
| **기본 처분 R4** · 2026-10-09 Q1 | 사전 등록한 기준 미충족·기한 내 무응답 → NO_CHANGE. 노출·예산을 올리는 기본값 금지 | 사장 질문은 변경 제안일 때만 | 모든 리플레이·규칙 후보 | CLAUDE.md "Default disposition" · ops-dev-touch-reduction-2026-10-09.md:4 (문서는 대체됨, R4만 유효) |
| **SCN-27H1 시나리오 지침** · 2026-10-09 | 시장 전제 B0 = 1H27까지 후반부 강세장(조건부) | **유효 2027-06-30까지** | 카드·M6·발굴 | CLAUDE.md:103 · market-scenario-27h1-2026-10-09.md |
| **상품 승인** · 2026-10-01(BE·MU·NBIS·DELL·AMD·SOXL·TQQQ·DRAM) + 2026-10-08 13:10(PWR·LITE) | 신규 매수 승인 상품. 정책·등록부 반영은 S7 2단계 대기였음 | 반영 상태는 현행 정책 파일로 **확인 필요** | 상품 승인 게이트 | product-approval-PWR-LITE-2026-10-08.md:4 · 49-55 |
| **MVLL 159주 유지** · 2026-10-08 | "20% — 159주 유지, 새 근거가 생기면 그때 다시 카드", 감축 단계 종료. 10/17 재카드 HOLD | **조건부 판단**(영구 매도 금지 아님). 10/22 매도는 recon-hold가 키움 체결 기록으로 본 **사실**이지 결정이 아니며 매도 주체는 문서에서 못 찾음(확인 필요). 보유 원본은 키움(상태 파일은 대조 보류로 옛 값 159) — 실제 0주로 확인되면 '재카드 대상' 표시만 추가 | m6-relative-comparison-7stock-2026-10-08.md:244 · l2-full-review-2026-10-17.md:25 · recon-hold-2026-10-23.md:13 |
| **ev-derisk b** · 2026-10-13 23:25 | 자동 매도 없음, 회복 매수는 R-REC1 | MVLL 줄은 위 별도 항목 | 이벤트 대응 | event-strategy-2026-10-13.md:5 · 159 · recon-hold-2026-10-23.md:14 |
| **위험 예산 1.55** · S7 승인 2026-10-01 | 1.55 = 사용자 승인 위험 예산(검증 통과값이 아님, FX-1009 D3 정정) | 상향은 K3. 2.0~2.2 상향안은 위원회 반대·권고 현행 유지, **사장 결정 기록 못 찾음** | 노출 한도 | loss-limit-review-s5-policy-proposal-2026-10-01.md:8-11 · exposure-ceiling-2.2-review-2026-10-08.md:4 |
| **recon-dt a · cashflow-proof B2-N** · 2026-10-23 08:45 / 09:25 | 체결 날짜를 미국 주문일로 해석(병합 5a289b8) · 거래내역에 없는 출금을 I3에서 인정(착수 승인 10/25 08:12, 병합 승인 12:29, 병합 b2cd42e). 첫 실제 확인 10/27 06:15 대조 | 불변 조건 완화 아님. 출금 증거는 가장 엄격한 형태만 | 대조 | recon-hold-2026-10-23.md:5 · cashflow-proof-options-2026-10-23.md:5 · 77-79 · git log |
| **키움 규칙(상시)** · 2026-10-07 | 읽기 조회는 `profile 실전계좌`+`mode real`, 8005면 인증·토큰 재발급 금지 | — | 모든 키움 조회 | CLAUDE.md "Kiwoom query rules" |
| **상시 사용자 규칙 묶음** | 검토 안정성(2026-10-13) · Haiku 하위 에이전트는 기계 작업만(2026-10-08) · 동시 개발 3 + 권한·한도 1 · docs 변경은 _pending 목록 · 대시보드 HTML 수정 전 라이브판 읽고 디자인 규칙(2026-10-14) · 연결 원칙(2026-10-05) | — | 작업 방식 | CLAUDE.md "Working rules" (87-110행) · artifact-design-rules-2026-10-14.md |
| **예약 지시문 교체 이력**(현행판 원본) | 통합 점검 v3.12.10-L+R2(iv-r1 2026-10-22) · 자동 코어 알림 v2.5(pb-r1) · 월요일 점검 v2.2(monday-gap M1 2026-10-20) · 관심 명단 재채점 v3.4(split-weekly-general 2026-10-23) · Next 샌디스크 v3.2 · 주간 팀장회의 v1.4 · 비서 제안 v1.1 | 현행 해시·모델은 표가 원본 | 예약 작업 | scheduled-prompts/README.md:12-24 (표) · 53-67 (기록) |
| **t2-gate: REMOVE-v2** · 2026-10-26 16:07 KST (사장 스레드 직접 입력; 15:33 REMOVE는 Judge 1차 FAIL로 대체) | T2 "켜" 조건 R2에서 "5거래일 연속" 셈만 뺌. 대신 C1 창(10-17 실행분부터)의 모든 비교일 차이 분류 의무(COMPARED 5일 이상, 계산기 diagnostics·노출 포함, 오라클 결과 없는 날 차이 0 불산입), CORE_BUG 해소 커밋 목록, 대조 OK 연속 5회. R1·C1·C2·C3·C5·R3(사장 "켜") 그대로 | **효력**(Judge 2차 PASS, 효력 조건 1~6·문구 a~d — 결정 문서 1-2절). 지금: 대조 OK 0/5, trig: 차이 4건 미분류, 해소 커밋 목록 없음 → "켜" 판정 불가. decision_mode·노출·권한 불변 | T2 "켜" 판정 | roadmap-fix-decisions-2026-10-26.md 1-1·1-2절 · t2-gate-judge-2.txt · t2-rc-preregistration 55행 |
| **d10: REUSE** · 2026-10-26 15:33 KST (사장 스레드 직접 입력) | SPY 벤치마크 = auto_core.json symbols_extra에 SPY 추가(사장 실행) + 채점기가 수집 이력에서 SPY를 읽는 일반 변경(개발 큐 d10-spy) | SPY는 REFERENCE_ONLY(매매 근거·관문 입력 아님). 키움이 SPY 30분봉을 안 주면 다시 결정 | 주간 채점, 자동 코어 수집 | roadmap-fix-decisions-2026-10-26.md 2절 · d10-spy-builder-prompt.md |

## D. 아직 열린 결정(답 없음 = 기본값)

| id | 기한 | 무응답이면 | 원문 |
|---|---|---|---|
| skel-1022 | 2026-10-29 | 전부 NO_CHANGE | skeleton-review-2026-10-22.md:64 |
| projects-1025 | 2026-11-01 | Q1 c · Q2 c (현행) | projects-mods-adoption-2026-10-25.md:5 |
| redesign-t2-compare-b7 (2건) | 확인 필요 | 확인 필요 | redesign-t2-compare-b7-2026-10-23.md:5 |
| 진단 D10(SPY 일봉)·D9(헌법 머리글 보류)·D13(분석 경로 현행) | — | 후순위·보류·현행 | operating-diagnosis-2026-10-25.md:212-224 |
| 팀장회의 v1.5 교체 | board-merge Q2 조건 충족 시 | 지금 구조 유지 | ceo-room-merge-2026-10-22.md:58 |

## E. 대체·만료·종료된 결정 (다시 제안하지 않도록)

| 결정 | 상태 | 원문 |
|---|---|---|
| board-merge Q1 c · Q2 b (10/23 00:19) | 00:20 Q1 a·Q2 a로 **대체** | ceo-room-merge-2026-10-22.md:82-83 |
| ops-dev-touch-reduction R1·D1·D2 (2026-10-09) | 재설계 T1·T3로 **흡수**(R4만 유효) | ops-dev-touch-reduction-2026-10-09.md:4 |
| projects-new 문서 본문의 Q1 a 기준 / '승인 이전' 이전(①) | Q1 b로 개정 + 11:32 **중단**, 현행 유지 | projects-new-board-design-2026-10-26.md:5 · 85 |
| 지침 v1.x 4절의 '승인류·예약 변경 불가' | v1.8에서 예약 변경만 조건부 허용으로 바뀜 | schedule-dashboard-redesign-2026-10-25.md:106-113 |
| 관제판 주간 점검 v1.2 (Haiku) | 주간 팀장회의로 **바꿔 씀**(2026-10-19), 이전판은 되돌리기용 보관 | scheduled-prompts/README.md:16 |
| 주간 재채점 v3 → v3.1 → v3.2 → v3.3 → v3.4, 통합 점검 v3.12.x 이전판 | 최신판만 현행. 이전 지시문은 되돌리기용 | scheduled-prompts/README.md:12-24 · 53-67 |
| 진단 D4 b·D2·D1 a · D6·D3·D11·D12 · N1·N2 · cf-b2n · recon-dt · hnd-check · hnd-check2 · rrec-ev4 REMOVE | **병합 끝**(bb11f04 · 96f1e6a · fbdede9 · b2cd42e · 5a289b8 · b6a83e2 · 4ca4940 · 5d5cf79). 새로 제안할 일 없음 | git log (2026-10-25 확인) |
| exposure 상향 2.0~2.2 검토 · crash-exception(예외 0주) · c-rule/c-risk 리플레이 | 위원회 반대·NO_CHANGE 권고. 사장 결정 기록은 못 찾음 → **현행 유지로 읽음, 확인 필요** | exposure-ceiling-2.2-review-2026-10-08.md:4 · crash-exception-review-2026-10-09.md:4 |

## G. 옛 결정 보강 (2026-10-01~10-08, 지금도 자동 코어·카드에 걸리는 것)

| 결정 id · 날짜 | 한 줄 내용 | 조건/만료 | 대상 | 원문 |
|---|---|---|---|---|
| **S7 승인 1~7** · 2026-10-01 | ① 채우기 권고 = 미검증 위험 예산의 수익 추구 권고(표시 전용, B 이하) ② R5 고점은 적용일 이후 종가 최고치 ③ 줄이기 순서: 종목 상한 초과(MVLL 포함) → 카드 TRIM·EXIT → SOXL ④ **노출 목표 1.55 유지**(감수 위험을 알고, OOS·shadow 생략) ⑤ **신규 매수 상품 승인 8개**: BE·MU·NBIS·DELL·AMD·SOXL·TQQQ·DRAM(**MVLL·NBIL 미승인**) ⑥ DRAM 종목 상한 0.4배 ⑦ SOXL weakness_10ema 감시·재무장 규칙 은퇴 | 정책 반영은 K3 경로. 상한 변경은 별도 사용자 승인 + Judge. **절대 상한 E ≥ 1.9이면 신규 매수 차단**. 종목 명목 상한 0.4배(MVLL·개별주, SOXL·TQQQ는 E로 관리). MVLL은 **매도 전용** | 노출 한도, 상품 승인, 줄이기 순서 | loss-limit-review-s5-policy-proposal-2026-10-01.md:111-122 · 같은 문서 R2·R3 절 |
| **D4 원가 손실 한도 폐지** · 2026-10-01 | 원가 대비 손실 한도(S8 −20%)를 판정 규칙에서 폐지. −20% 최대 선은 검토선(자동 현금화 없음) | 근거로 다시 쓰지 말 것(L2 재검토 v2가 이걸 근거로 써서 철회됨) | 카드 TRIM 판단 | l2-full-review-2026-10-17.md:9 · 37 · loss-limit-review-s5-prep-decisions-2026-10-01.md:4 |
| **fx-5a A-1·B-1** · 2026-10-09 | 1.55는 1.00·1.32와 우열 미확인 → 위험 선호 값으로 유지(NO_CHANGE), 채우기 기본 대상 SOXL 유지 | S7 2단계 설계 입력 | 노출 한도 | loss-limit-review-s5-policy-proposal-2026-10-01.md:11-12 |
| **관심 명단 D1~D4** · 2026-10-03 | D1 시총 $1T 이상 후보 제외(MU·AMD 예외) · D2 관심(미보유) 슬롯 5개 · D3 처음 2회 제안 후 자동 적용 + 알림 · D4 매주 토요일 재채점 + 매월 첫 토요일 전체 발굴. 관심 편입 ≠ 매수 승인 | 교체 주 1건, 검증 실패 시 변경 없음. 점수표·교체 규칙은 경계 밖 | 관심 명단 주간 재채점 | watchlist-rotation-design-2026-10-03.md:15-20 · 12 |
| **M6 결정 1 철회 · 결정 2 MVLL 159주 유지** · 2026-10-08 | 결정 1(M6 약세) 철회 → 통합 점검은 'M6 미인정'. 결정 2 = MVLL 최종 20%, 159주 유지(위 C절 MVLL 항목과 같은 결정) | 새 근거가 생기면 다시 카드 | M6, MVLL | m6-relative-comparison-7stock-2026-10-08.md '사용자 평가' 절(약 242-244행, 정확한 행은 열어 확인) |
| **wcg-1017 / wl-cand-review a** · 2026-10-17 | PWR 카드 kill 기준 ④ 삭제 · 7종목 M6 10/17 수락 · 수락 카드 재사용 · CRWD 수정주가 → 이후 v3.4에서 전 종목 수정주가 | 카드 판단·관심 명단 변경은 별도 | PWR 카드, 관심 명단 | INDEX-auto.md:383 · m6-relative-comparison-7stock-2026-10-17.md:4 · scheduled-prompts/README.md:67-70 |

## H. 예약 지시문 주석에서 찾은 결정 (2026-10-25 읽음: scheduled-prompts/*.txt 현행 10개의 머리 줄과 규칙 주석)

현행 지시문 원문은 `scheduled-prompts/<이름>.txt`. 아래는 그 머리 줄·주석이 가리키는 결정 중 위 A~G에 없던 것. `pending-*/` 폴더와 `integrated-check-prompt-v*.txt` 이전판은 읽지 않았다.

| 결정 id · 날짜 | 한 줄 내용 | 조건/만료 | 대상 | 원문 |
|---|---|---|---|---|
| **iv-1022 C1 a · C2 a · C3 b** · 2026-10-22 12:41 | C1·C2 = 점검 결과 맨 위 결정 줄·종목별 '참고 추정' 한 줄(표시 전용, 주문표 아님, 코어 입력에서 제외). **C3 b = 현행 유지**: 레버리지(SOXL·MVLL)가 중요 가격선에 닿을 때 '매도 주문표' 목표 리플레이는 하지 않음 | 사장 선호('레버리지는 선에서 매도 주문표')는 규칙 후보로만 기록, 5년 이상 자료를 구하면 다시 연다. 모든 보유 종목은 고점 −30%에서 카드 재작성(C.10) 그대로 | 통합 점검 v3.12.10, 카드 | ceo-interview-card-criteria-2026-10-22.md:67-72 · 82 · scheduled-prompts/integrated-check-daily.txt:1 |
| **t2-rc: B** · 2026-10-14 17:34 (적용 승인 10-15 13:29) | 규칙 파일 115행 '매수 불가 상품'은 state 그대로 두고 label만 바꿈(v3.12.6) | 사전 등록 3절 | 통합 점검 | t2-rc-preregistration-2026-10-14.md:5 · integrated-check-daily.txt:1 |
| **earn-na: a** · 2026-10-14 11:04 | 확인된 미공지는 실적 금지 구간이 아님: earnings-anchors.json 예상일 창 안이면 미공지를 뺌(4단계 finalize) | 확인 못 함은 금지 유지(p-earn 개정 2026-10-03) | 연구 기록 | earnings-not-announced-review-2026-10-14.md:52 · integrated-check-daily.txt:1 |
| **c3-rule: 1** · 2026-10-14 15:40 | 상태형 C3± '유지 중' 정의 1문장 추가(v3.12.5) | — | 통합 점검 규칙 파일 | c3-state-decision-2026-10-14.md:24 |
| **st-1014: B** · 2026-10-14 09:42 | 종목 페이지 단서를 SAVE 메모 v2.2가 모아 LATEST_TICKER_LEADS.json에 쓰고, 통합 점검은 브라우저 대신 이 파일을 읽음(v3.12.4) | — | SAVE 메모, 통합 점검 | integrated-check-v3.12.4-change-2026-10-14.md:6 |
| **2026-10-09 승인 묶음** | "진행, 1A 2A" · 규칙 파일 + 해시 고정 · "매수 가능 현금 = 주문 가능액" · "G6 A안 장중 낙폭 표시" | **규칙 파일을 바꾸려면 지시문 해시도 사용자 승인으로 함께** 바꾼다 | 통합 점검 | integrated-check-daily.txt:1 · 4 |
| **재설계 T2 4단계 승인** · 2026-10-12 | 통합 점검의 연구 기록 쓰기(workspace/outputs/research-records/<날짜>/…)가 07:45 코어 decide가 읽는 유일한 LLM 입력 | 쓰기 예외 1개. 기록이 없거나 무효면 모든 매수 주문표 차단(매도는 아님) | 통합 점검, 코어 | integrated-check-daily.txt:28 · CLAUDE.md Hard safety |
| **monday-gap M1** · 2026-10-20 19:43 | 월요일 점검을 프리마켓 35분 전(미국 동부 월 03:25)으로 당기고 토요일 주문표 재확인(기록 모드만, 매수·매도를 막지 않음, 키움 미사용) 추가 | 첫 실행 10/26 16:25 KST — 비교 모드라 '비교 모드 — 주문표 n건' 기록만 정상 | 월요일 개장 전 점검 | monday-pre-open-check.txt:1 · 관제판 monday-gap |
| **연결 원칙** · 2026-10-05 ("모든 분석 결과는 다른 작업과 연계") · **SAVE E5** 2026-10-01 | 모든 분석·조회·발굴 출력은 다른 작업이 읽는 곳에 쓰고 소비자 1개 이상 명시 / SAVE 메모는 사용자가 PDF를 넣지 않아도 되게 갱신 | 상시 | 모든 예약 작업 | monday-pre-open-check.txt:3 · save-market-memo.txt:3 · analysis-linkage-map-2026-10-05.md |
| **주간 재채점 규칙** (A6 a 2026-10-10 · 유지 보호 ⑧ 2026-10-04) | 자동 모드: 편입·교체·제외를 규칙이 정해 명단에 바로 반영 + 알림. 실행당 편입·교체·제외 합계 ≤ 1건, 분야당 관심 ≤ 2, 동점은 기존 유지. ⑧ 철회 기준 공식 확인이 없으면 S1+S2가 편입 때 이상인 종목은 교체하지 않음('조정 중'). **관심 편입 ≠ 매수 승인**(새 종목 카드는 '자동 작성 초안(미수락)') | 되돌리기는 사용자 지시로 Cowork가(history by "user"). Next 샌디스크는 제안 모드 유지 | 관심 명단 주간 재채점 | watchlist-weekly-rescore.txt:1 · 4 · 5 · 84 · 242 · 312 · next-sandisk-discovery.txt:1 |
| **Q3 a 매주 보고** · 2026-10-19 | 주간 팀장회의는 지난주와 같아도 매주 보고, 스스로 비활성화하지 않음 | board-merge Q2 a 조건이 걸림 | 주간 팀장회의 | ceo-weekly-meeting.txt:3 · 45 |
| **비서 제안 출력 형식** · 2026-10-21 | 각 건 = 종류[사장 결정 / 사장 확인 / 팀 처리] · 쉬운 말 한 문장 · 왜 지금 · 행동 한 줄(answerHint 그대로). 쓰기 = 비서 파일 1개 | briefs 쓰기 추가는 obs-sys-sec 승인 때만(A절) | 비서 제안 | secretary-daily.txt:1 · 23 |
| **ev-calendar-auto: a** · 2026-10-13 22:4x + 10-14 "전략을 자동화 운영 시스템과 결합하라" | 개장 전 이벤트 점검(일정표) 반복 예약, 오늘 주문표 이벤트 노출 줄·빅테크 실적→SOXL S3 판정 요청 | **코어 decide는 일정표를 읽지 않음**(코어의 LLM 입력은 연구 기록뿐) | 이벤트 점검 | event-pre-open-calendar.txt:1 · event-strategy-2026-10-13.md:222 |

## I. 관제판 DB의 결정 기록 (2026-10-25 20시대 ArtifactData 읽기, 쓰기 없음)

- 규모: tasks 229건(done 182 · waiting 36 · planned 5 · active 4 · blocked 1 · paused 1). `meta/board` 마지막 갱신 2026-10-23 00:15(sc-1022), 가장 늦은 작업 갱신 2026-10-25 12:35(cashflow-api-gap). `decisions` 컬렉션은 없음, `log`는 있음(3건만 열람). **`briefs` 컬렉션이 비어 있음 → board-merge Q1 a는 아직 적용 전.**
- 관제판 안내문 중 `answerHint`는 항상 `결정 <작업 id>: …` 형식(dev-dashboard-protocol.md:40).

| 작업 id · 상태 | 관제판 기록 | 기한 · 무응답이면 |
|---|---|---|
| board-merge (waiting) | Q1 a·Q2 a 결정됨, 비서 v1.2 교체(obs-sys-sec 승인) 뒤 적용 | 10/29 · Q1 c·Q2 b(대체된 기본값) |
| obs-sys (waiting) | Q1 끝, Q2(비서 v1.2) 대기 | 10/29 |
| sc-1022 (active) | Q1 a·Q2 a, 비서실 운영 +14일 평가 | 10/29 |
| dram-cand (waiting) | DRAM 매수 후보 추가 검토 | 10/28 13:00 Cowork 재검토 · **b 현행 유지(NO_CHANGE)** |
| cashflow-api-gap · recon-dt (waiting) | 병합 끝(cf-b2n b2cd42e · recon-dt 5a289b8), 남은 것 10/27 06:15 대조 확인 | 10/30 · 병합 안 함(현행 유지) 기본값은 이미 지남 |
| recon-dt2 (planned) | 주문표 주문일 창도 ord_dt=미국 주문일로(후속) | — |
| split-weekly-general (waiting) | 지시문 v3.4 적용 완료, 첫 실행 확인 대기 | 11/06 · CRWD만 adjusted(옛 기본값, 이미 대체) |
| redesign-t5 (waiting, decide) | 주문 2단계(키움 API 주문 + 휴대폰 승인)로 올릴지 | **무응답 = 현행 유지(1단계)** |
| duet-k1 · duet-r3a · duet-trial · duet-idx (waiting) / duet-q4-coreinput · duet-q4-recon (planned, decide) | A절 duet-1022 후속 | 개발 자리·Duet 개통 조건 |
| f-openshell · c-nextsndk-v2 (waiting, decide) · fx-3 (11/03) · f-evo-loop (11/21) · cal-2027 (12/15) · t2-rc · c-hwm-review (blocked) · s-cbm-pilot (paused) | 각 작업의 next 칸 참조 | 표시한 기한 외 없음 |

관제판에만 원문이 있던 결정(문서에서는 못 찾았던 것):

| 결정 | 날짜(KST) | 내용 | 관제판 근거 |
|---|---|---|---|
| buylow: a | 2026-10-17 08:28 | 매수 방향 = 회복 초기 매수(R-REC1) 유지. 저점 매수(관문 완화, b)는 하지 않음 | tasks/buylow · buylow-direction-review-2026-10-17.md |
| fx-freeze: 해제 | 2026-10-16 | FX-1009 동결(새 규칙 후보·새 리플레이 주제 금지) 해제, CLAUDE.md 동결 1줄 삭제(커밋 0c58852). 보류 입력(cpi-shock-review D1·D2·D4, f-evo-loop 시작)은 사장 요청 때 별도 | tasks/fx-freeze |
| pre-on-fix: a | 2026-10-15 16:32 | '켜' 전 코어 수정 ④①⑥ 한 번에(⑥은 예외 알림). 병합 04f9a85 | tasks/pre-on-fix |
| ev-rg1-hyper: a · 병합 승인 | 2026-10-14 00:28 · 10-18 07:11 | 회복 관문 RG1이 공식 테제 훼손을 잊지 않게 수정, 통합 점검 로더 v3.12.7. 병합 끝 | tasks/ev-rg1-hyper |
| wl-snap-commit: a · duet-judg: J1 a·J2 a·J3 a | 2026-10-17 12:03 · 2026-10-22 22:12 | 변경 없는 주도 주간 판을 커밋 목록에 남김 / 'duet-judg 진행'을 권장안(모두 a)으로 해석 | tasks/wl-snap-commit · tasks/duet-judg |
| 대체됨: obs-1022 → obs-1022b → duet-1022 | 2026-10-22 | obs-1022b Q1 a는 duet-1022 Q1로, Q2는 duet-1022 Q4로 흡수 | tasks/obs-1022b |

## J. 주문표 설계 (order-instruction-design-2026-10-06.md와 관제판 oi-*·r-* 작업, 2026-10-25 읽음)

문서 머리는 `draft (K3 제안 · 적용 안 함)`로 남아 있지만, 계산·주문표 부분은 2026-10-10 재설계로 흡수됐다. **이 문서의 규칙을 그대로 현행으로 읽지 말 것.**

| 항목 | 현재 상태 | 원문 |
|---|---|---|
| 주문 지시서 K3(oi-k3) | **흡수: redesign-t2** — 주문표 계산기는 T2, 주문 2단계 결정은 redesign-t5(현행 유지 = 1단계) | tasks/oi-k3 · automation-redesign-2026-10-10.md 10절 |
| 봉인 SHADOW 시범·'내 결정 먼저 기록' (oi-pilot-1·2) | **폐지(A1)** — 주문표 자동 채점으로 대체. 시범 결과: OI-20261008-MVLL-2 결론 '지시 없음', 사장 결정 3/3 일치, 평가 '판단에 씀' | tasks/oi-pilot-2 · order-instruction-design-2026-10-06.md:347 |
| R-NE1 미입력 규칙 | 흡수 — 미입력 분류는 코어 다음 날 결과 분류에 포함 | tasks/r-ne1 · order-instruction-design:199 |
| R-RI1 재발행 상한 고정 | **철회**(2026-10-09 17:21 사용자 A: 재발행 매수 상한 = 새 기준가 × (1+0.5σ)). 이후 redesign-t2 Q2 b로 첫 상한 제한도 없앰 | tasks/r-ri1 · order-instruction-design:193 · redesign-t2-merge-decision-2026-10-12.md |
| 주문가 옵션 층 O1~O4 | 2026-10-07 사용자 승인 → 재설계로 **표시 전용**으로 좁힘(거래 근거·가격 산식 입력 아님) | order-instruction-design:231 · CLAUDE.md "Option layer" |
| 주문마다 위원회 열기(2026-10-08 "적용") | **대체됨** — 위원회는 정책·한도·권한 변경에만 | order-instruction-design:127 · CLAUDE.md "Council" |
| 이벤트 날 상단 지정가 R-EV1 | 규칙 후보 등록(2026-10-07), 시범 5회 이상 뒤 판정이었으나 시범이 폐지됨 → 판정 경로 **확인 필요** | order-instruction-design:247 |
| 단계 변경 원칙 | "시스템은 자기 권한을 스스로 넓히지 않는다. 단계 변경은 매번 사용자 승인 + 독립 Judge" | order-instruction-design:333 |
| 사장이 직접 낸 개별 주문 결정(기록) | UD-20261007-MVLL-1: MVLL ② 119주 LOC $37.77(2026-10-07) — 이 매도로 보유가 278주→159주(M6 10/8 결정 2의 배경, 산술은 확인 필요) · OI-20261009-SOXL-2: "B 22주 진행. 예외 유지"(2026-10-09 08:03). 주문은 사장이 키움에서 직접 입력 | tasks/d-order-panel · order-instructions/OI-20261009-SOXL-2.md:3 |
| 현재 주문표 | decision_mode가 compare인 동안 '비교 중' 표시, 사장 "켜" 전까지 입력 대상 아님 | CLAUDE.md:5-8 |

## F. 한계 — 빠뜨렸을 수 있는 범위 (확인 필요)

- **읽은 범위**: docs/claude 약 536개 중 위 표에 인용한 문서와 grep 결과(`결정 <id>: Q.. a` 형태 약 50건 중복 포함, '하지 않음/바뀔 조건' 절 머리, status 줄). **전수 정독이 아님.** 옛 결정 중 S7 승인 1~7·관심 명단 D1~D4·M6/MVLL은 G절에 보강했다. **사장 결정(2026-10-25 20시대): 시스템 검토 P3/P4와 이벤트 전략(event-strategy)은 해당 주제를 다룰 때 채운다** — 지금은 상태 줄과 인용한 행만 봤다. loss-limit S5 D1~D3·D5~D7 개별은 S7 승인 1~7(G절)로 갈음했다. 예약 지시문 주석·관제판 DB·주문표 설계는 H·I·J절에 채웠다.
- **읽지 못한 원본**: ① 관제판 `log` 컬렉션 대부분(I절은 tasks 229건 기준) ② Cowork 대화 속 결정(이 프로젝트 스레드는 Cowork 대화를 못 읽음) ③ 프로젝트 지침 v1.8 원문(repo 밖) ④ claude.ai 예약 작업의 실제 현재 지시문(repo 보관본과 같은지는 README 해시 표 기준) ⑤ 결정 일지(stock-strategy-system/decision_journal.json — 이 색인 범위 밖, 원본 불가침) ⑥ ceo-weekly-report.md 본문(선택 행 외) ⑦ `scheduled-prompts/pending-*/`와 `integrated-check-prompt-v*.txt` 이전판의 주석 ⑧ order-instructions/OI-* 본문(머리 줄만) ⑨ library/research.
- **grep으로 못 잡는 형식**: "결정 <id>: 승인"이 아니라 "그렇게 해", "전부 예", "권장안대로"처럼 문장으로 낸 승인은 일부만 잡았다.
- **자동 갱신 아님**: 새 결정이 생겨도 이 파일은 저절로 바뀌지 않는다. 갱신 담당(지침 v1.9, 코디네이터 보고 2026-10-25): 결정을 원본에 기록한 세션이 같은 세션에서 이 색인에도 한 줄 추가, 아침 보고 때 색인에 빠진 새 결정 문서를 1줄 알림(지침 원문 직접 확인은 못 함).
- **어긋남 2건은 2026-10-25 사장 승인으로 정리함**: ① 승인 장소는 D4 b가 나중·유효(B절 해당 두 줄) ② MVLL은 결정(조건부)과 체결 사실로 분리(C절). 남은 확인 필요: MVLL 10/22 매도 주체, 지침 v1.8 원문 대조.
