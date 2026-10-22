---
id: ops-fixes
type: runbook
status: current
as_of: 2026-10-22
summary: 막혔다가 푼 방법 모음(방법만 — 규칙·권한·판정 아님). 오류 문구로 검색해서 쓴다. 원본은 저장소 docs/claude/ops-fixes.md, 프로젝트 "투자_V2" 문서 claude/ops-fixes.md는 사본.
consumer: 모든 Cowork·Claude Code 세션(막혔을 때 먼저 검색), 주간 팀장회의 법률팀(3회 이상 쓰인 항목 → 플레이북·규칙 후보)
source: 사장 결정 "결정 cs-1022b: 3 a, 5 a"(2026-10-22 14:02), docs/claude/claude-setup-tips-review-2026-10-22.md 6·7절
---

# 해결법 모음 (ops-fixes)

## 쓰는 법
- 막히면 먼저 이 파일에서 **오류 문구 그대로** 검색한다(예: `needs_device_approval`, `8005`).
- 새 항목: 도구 오류·거절·예상과 다른 결과를 **두 번 이상 시도해 풀었을 때** 그 세션 끝에 1항목 추가. 같은 증상이 있으면 새로 쓰지 않고 "확인"에 날짜를 더한다(쓰인 횟수 = 확인 날짜 수).
- 저장소 판을 고치면 프로젝트 문서 사본(claude/ops-fixes.md)도 같이 고친다.
- 60일 동안 확인이 없거나 도구가 바뀐 항목은 제목 앞에 "(옛것)". 확인 3회 이상 항목은 주간 팀장회의 법률팀이 플레이북·규칙 후보로 올린다.
- 금지: 권한·정책·판정을 바꾸는 문장, 비밀 값·계좌 값. 이 파일은 방법만 — 규칙과 부딪히면 규칙이 이긴다.
- 함께 지키는 일(cs-1022b 5 a): 문서를 바꾼 Cowork 세션 끝(_pending 쓸 때)에 `python3 docs/claude/make-index.py` 실행 → docs/claude/INDEX-auto.md·INDEX-outputs-auto.md 갱신(_pending 목록에 두 파일 포함). workspace/outputs 아래 새 폴더를 만들면 README.md 1개(개요·상태·다음 할 일·관제판 작업 id).

## 항목 (증상 · 원인 · 해결 · 하지 말 것 · 근거 · 확인)

### F01 예약 작업 지시문 교체가 `needs_device_approval`
- 원인: PC가 필요한 예약 작업은 PC 데스크톱 앱 서명이 있어야 본문이 바뀐다. 이 호출은 아무것도 바꾸지 않음.
- 해결: 사장에게 "PC 데스크톱 앱에서 이 대화를 열고 '다시 시도'"를 요청 → 같은 본문으로 update_trigger 다시 → PC 승인 창. 교체 뒤 응답 본문을 바이트 대조(F03).
- 하지 말 것: 예약 작업 삭제 후 새로 만들기(실행 기록·PC 연결이 사라짐). 모델 변경은 이 경로로 안 됨.
- 근거: scheduled-prompts/README.md 2026-10-22 06:12 줄, iv-c1c2(2026-10-22). 확인: 2026-10-21, 2026-10-22

### F02 키움 조회 `8005` 인증 오류
- 원인: options에 profile·mode가 없으면 옛 토큰으로 호출됨.
- 해결: 모든 kiwoom_query options에 `"profile": "실전계좌", "mode": "real"`.
- 하지 말 것: auth·login·토큰 재발급(다른 작업 토큰을 무효화). 실패로 기록하고 계속.
- 근거: CLAUDE.md Kiwoom query rules(2026-10-07). 확인: 2026-10-07

### F03 예약 작업 본문이 승인본과 같은지 바이트로 확인하기
- 원인: list_triggers 응답은 화면 글로만 보여 해시를 바로 못 냄.
- 해결: 세션 기록 JSONL(/root/.claude/projects/<프로젝트>/<세션id>.jsonl)을 python으로 읽어 tool_result의 `derived_state.prompt`(현재 본문)와 tool_use의 `input.prompt`(보낸 본문)를 각각 sha256. 파일 쪽은 그대로 sha256.
- 근거: iv-c1c2 교체(2026-10-22 13:3x, 6f65c89b… 일치·1101af45… 일치). 확인: 2026-10-22

### F04 `list_triggers`가 몇 건만 주고 끝남
- 원인: 응답에 지시문 전문이 들어가 크기 때문에 2~19건에서 끊김.
- 해결: next_cursor가 없을 때까지 같은 인자로 계속 부른다. 특정 작업만 필요하면 recurring 필터를 쓰고 페이지를 넘긴다.
- 근거: ceo-weekly-meeting 지시문 5), 2026-10-22 조회(5페이지). 확인: 2026-10-17, 2026-10-22

### F05 예약 세션에서 device_bash의 `$HOME/mnt/<폴더>`가 안 보임
- 원인: 예약 실행 세션은 마운트가 없을 수 있음.
- 해결: 예약 작업은 device_list_dir·device_stage_files·device_commit_files만 쓴다(Cowork 대화 세션은 device_bash 가능).
- 근거: auto-core-alert.txt·ceo-weekly-meeting 지시문. 확인: 2026-10-19

### F06 저장소 파일 해시가 매번 다름(CRLF)
- 원인: Windows 저장소가 줄 끝을 CRLF로 바꿀 수 있음.
- 해결: 해시 전에 `tr -d '\r'` 또는 python `b.replace(b'\r\n',b'\n')`로 LF 정규화한 값으로 비교.
- 하지 말 것: 줄 끝 일괄 변환(증거 해시가 원본 바이트를 씀).
- 근거: CLAUDE.md Working rules, 통합 점검 로더 1단계. 확인: 2026-10-22

### F07 키움 해외 시세·일봉 `1903` "종목 정보가 없습니다"
- 원인: 거래소가 틀림.
- 해결: NASDAQ → NYSE → AMEX 순서로 다시.
- 근거: 현황판 마감 정리·관심 명단 재채점 지시문. 확인: 2026-10-10

### F08 키움 연속 조회 `429`
- 해결: 종목마다 `sleep 2`. 큰 결과는 "파일로 저장됨" 경로를 cp로 옮기고 원문을 대화에 붙이지 않는다.
- 근거: 관심 명단 주간 재채점 지시문 4). 확인: 2026-10-17

### F09 `device_commit_files`가 mtime으로 거절
- 원인: stage 뒤 PC 파일이 바뀜(사람이나 다른 작업이 고침).
- 해결: 다시 stage해서 새 내용 위에 병합한 뒤 기록. 
- 하지 말 것: force로 덮어쓰기.
- 근거: device_commit_files 설명, 관심 명단 지시문 7)㉯. 확인: 2026-10-17

### F10 python으로 파일을 다시 쓰다 빈 파일이 됨
- 원인: `open(p,'w', newline=...)`에 잘못된 값(heredoc 안 `'\\r\\n'` 이중 이스케이프) → 파일이 먼저 비워진 뒤 ValueError.
- 해결: 클라우드에서 전체 내용을 만들어 device_commit_files로 쓰거나, 쓰기 전에 원본을 임시 사본으로 복사. CRLF로 쓸 때는 따옴표 heredoc 안에서 `newline='\r\n'`(백슬래시 1개).
- 근거: claude-setup-tips-review-2026-10-22.md 수정 중(2026-10-22 14:0x, 즉시 복구). 확인: 2026-10-22

### F11 폴더 접근 요청이 "auto mode classifier … Cowork Folder Access"로 거절
- 원인: 자동 승인 검사가 넓은 폴더 요청을 막음.
- 해결: 사장이 PC 데스크톱 앱 "폴더 추가"로 직접 연결.
- 하지 말 것: 다른 도구로 우회.
- 근거: cs-1022 5절(2026-10-22 13:57). 확인: 2026-10-22

### F12 Notion 공개 페이지가 WebFetch로 안 열림
- 해결: 내장 브라우저로 열고, 본문이 화면에 안 나오면 javascript로 페이지의 /api/v3/loadPageChunk 응답을 읽는다(값이 value.value로 한 번 더 감싸짐).
- 근거: ext-three-links-review-2026-10-22.md. 확인: 2026-10-22

### F13 대시보드 화면 시험에서 저장소 가짜(stub)가 안 붙음
- 원인: Playwright add_init_script는 이동(goto) 때만 실행 — 첫 페이지 set_content에는 안 붙음.
- 해결: `page.goto('about:blank')` 뒤 `set_content`.
- 근거: iv-c1c2 1단계 시험(2026-10-22). 확인: 2026-10-22

### F14 ArtifactData `out_dir`로 받았는데 파일이 없어 보임
- 원인: `<out_dir>/<collection 경로>/<doc_id>.json`으로 하위 폴더에 저장됨.
- 해결: out_dir 아래 collection 이름 폴더(예 tasks/)를 본다.
- 근거: ceo-weekly-meeting 지시문 2), 2026-10-22 관제판 조회. 확인: 2026-10-22

### F15 runs 문서를 node로 시험할 때 JSON 구조가 다름
- 원인: 받은 문서가 `{"data": …}`로 감싸져 있을 때와 아닐 때가 있음.
- 해결: `(o => o.data || o)(…)`(python은 `o.get('data', o)`).
- 근거: iv-c1c2 시험(2026-10-22). 확인: 2026-10-22

### F16 대시보드(관제판·통합점검·현황판)를 고쳐 다시 올리기
- 해결: 먼저 Artifact read로 살아 있는 판을 읽고 그 파일 위에서 고친다. 게시 뒤 버전 id를 기록. 화면 시험은 375·1280px × 라이트·다크, 가로 넘침 0, 다른 칸 글자 동일 비교.
- 하지 말 것: 예전 로컬 사본으로 덮어쓰기. 디자인 규칙 artifact-design-rules-2026-10-14.md 무시.
- 근거: CLAUDE.md Working rules(Artifact page design), iv-c1c2. 확인: 2026-10-22

### F17 예약 지시문 안 스크립트를 AI가 다시 적다 틀림
- 해결: 스크립트를 저장소 파일로 빼고 sha256으로 고정(받은 뒤 `tr -d '\r'` → 해시 → 다르면 실행하지 않음).
- 근거: pb-r1(자동 운영 코어 결과 알림 v2.5, 2026-10-22). 확인: 2026-10-22

### F18 PC에 MCP(예: Desktop Commander)를 깔았는데 이 세션 도구 목록에 안 나옴
- 원인: Claude 앱 창만 닫으면 트레이에 남아 새 MCP 설정을 읽지 않음.
- 해결: 트레이 아이콘 오른쪽 클릭 → 종료 → 앱 다시 열기. 확인은 기기 정보(get_device_info)의 localMcpServers와 ToolSearch "+remote-devices Desktop_Commander".
- 참고: 설치 방법에 따라 같은 서버가 두 번 보일 수 있음(데스크톱 확장 판 + npx 판) — 설정 파일은 하나를 같이 씀.
- 근거: cs-pc-setup(2026-10-22 14:14~14:26). 확인: 2026-10-22

### F19 PC 앱에서 "폴더 추가"를 했는데 이 세션의 connectedFolders가 그대로
- 원인: 확인 필요 — 클라우드 세션(휴대폰·웹에서 시작해 PC에 연결된 대화)에는 PC 앱 폴더 추가가 반영되지 않는 것으로 보임. 세션 안 폴더 요청(device_request_folder_access)은 자동 승인 검사가 거절(F11).
- 해결(대신 쓰는 길): Desktop Commander(allowedDirectories 빈 배열 = 전체)로 PC 파일·PowerShell을 쓴다. 연결 폴더가 꼭 필요한 일(device_stage_files·device_commit_files, 예약 작업 폴더)은 기존 연결 폴더 안에서 한다.
- 하지 말 것: 같은 추가를 반복 요청(사장 손만 늘어남).
- 근거: cs-pc-setup(2026-10-22 14:44·14:47 두 번, get_device_info 변화 없음). 확인: 2026-10-22
