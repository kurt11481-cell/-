# 브라우저 조작 도구 4종 + Aside 검토 (2026-11-03 KST)

범위: 웹 README·공식 문서 읽기만. 아무것도 설치·실행하지 않음(회사PC 셸은 읽기 전용, CLAUDE.md 132행 .claude 설정 수정 금지).
요청: 사장 2026-11-03 15:40 KST "다음 도구 설치 및 적용 진행 … aside 브라우저 … claude에서 브라우저를 자유자재로 조작하고 파일을 다운로드 받을 수 있게 연결해줘".

## 결론

| 도구 | 권고 | 한 줄 근거 |
|---|---|---|
| (재사용) Claude in Chrome | **재사용 — 1순위** | 이미 있는 연결. 설치 0. 지금은 연결된 Chrome 0개(15:5x KST 조회) → Chrome 켜고 확장 로그인만 하면 됨 |
| playwright (Playwright MCP) | **추가 가능 — 2순위** | Apache-2.0, 키 불필요. Claude 전용 별도 브라우저(로그인 없는 격리 프로필)라 키움·은행 세션과 분리됨. 다운로드를 정한 폴더로 받기 좋음 |
| Aside | **시범 보류(확인 필요 2건)** | `aside mcp` MCP 서버가 있으나 Windows용 CLI 설치 명령·MCP 도구 목록이 문서에 없음. 사장 로그인 세션 위에서 움직이는 브라우저라 위험이 가장 큼 |
| firecrawl | **보류** | AGPL-3.0, API 키(fc-…) 필요·유료 크레딧, 읽는 주소가 외부 서비스로 감. 웹 읽기는 이미 WebFetch·curl·Chrome으로 됨 |
| agent-desktop | **거절** | 모든 데스크톱 앱(키움 HTS 포함)을 접근성 트리로 클릭·입력. 주문 화면에 닿을 수 있음. 컴퓨터 사용 도구와 중복 |
| ui-ux-pro-max-skill | **보류** | MIT, 디자인 스킬. 브라우저 조작과 무관. 관제판 디자인 규칙(artifact-design-rules-2026-10-14.md)·artifact-design 스킬과 겹침. 저장소 설치는 .claude/** 보호 경로(수동 경로) |

## 그림 — 권하는 연결 순서

```
사장 요청: 브라우저 조작 + 파일 다운로드
   │
   ▼
① 이미 있는 Claude in Chrome 다시 켜기 (설치 없음)
   │   다운로드 폴더를 E:\사업\##금동한\_downloads 로 지정
   ▼
② 부족하면 Playwright MCP 추가 (Claude 전용 격리 브라우저)
   │   --isolated · --output-dir 위 폴더
   ▼
③ Aside는 Windows CLI·MCP 도구 목록 확인 뒤 시범
   │
   ▼
키움 HTS·키움 웹·은행은 어느 브라우저 자동화에도 로그인하지 않음
```

## 안전 검토 (절대 안전 1절과 부딪히는 점)

1. 주문 경로: 브라우저·데스크톱 자동화는 화면에 보이는 버튼을 누를 수 있다. 키움 HTS 창이나 키움 웹에 로그인된 세션이 있으면 주문 화면에 닿는다 → **자동화용 브라우저(프로필)에는 키움·은행·증권 로그인을 하지 않는다.** agent-desktop은 HTS 창 자체를 조작할 수 있어 거절.
2. 비밀: 브라우저 자동화는 파일을 직접 읽지 않지만 file:// 주소로 .env를 열 수 있다 → Claude는 file:// 로 저장소를 열지 않는다(규칙: 비밀 읽기 금지). Playwright MCP의 `--allowed-origins`·`--blocked-origins`는 "보안 경계가 아니다"라고 README 410~412행이 명시 → 막는 수단으로 믿지 않는다.
3. 다운로드: Claude 안전 규칙상 파일 다운로드는 매번 사장 허락(파일 이름·출처·크기) 뒤에 한다. "자유자재"여도 이 한 번 묻기는 남는다.
4. 비밀번호·로그인: Claude는 비밀번호 입력·로그인·CAPTCHA를 하지 않는다. 로그인은 사장이 직접 해 두고 Claude는 그 세션을 쓴다(Chrome·Aside).
5. Aside: 문서상 "Saved password values stay hidden from the AI agent"(docs.aside.com/help/security), 권한은 Settings > Agents의 Allow/Ask/Deny. 사장 구독(Claude·ChatGPT 키)으로 자체 에이전트가 돈다 → 페이지 내용이 모델 회사로 가는지 확인 필요(홈페이지 "Nothing is shared with LLM providers"와 구독 사용 설명이 맞지 않음).
6. 연결 위치: 회사PC Claude 앱에 등록된 MCP(키움 MCP·Desktop Commander)가 이 프로젝트 스레드에 보인다 → Playwright·Aside MCP도 같은 곳(Claude 데스크톱 앱 설정의 MCP)에 넣으면 스레드에 보일 것으로 추정(확인 필요). 키움 MCP는 건드리지 않는다(지침 1절).

## 도구별 사실 (출처)

- ui-ux-pro-max-skill: MIT(LICENSE), 설치 `/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill` → `/plugin install ui-ux-pro-max@ui-ux-pro-max-skill` 또는 `npm i -g ui-ux-pro-max-cli` + `uipro init --ai claude [--global]`. 검색 스크립트는 Python 표준 라이브러리만·네트워크 없음(README 328행, 코드 미확인).
- firecrawl: AGPL-3.0(LICENSE). API 키 가입 필요(README 90행), MCP `npx -y firecrawl-mcp` + FIRECRAWL_API_KEY(292~297행). 무료 한도 확인 필요.
- playwright: microsoft/playwright 본체는 테스트 도구. Claude 연결은 별도 저장소 microsoft/playwright-mcp — `claude mcp add playwright npx @playwright/mcp@latest`(README 101행). 옵션 `--isolated`(436행), `--output-dir`(440행), `--extension`(사장 Chrome에 붙음, 425행). 다운로드 파일이 output-dir에 저장되는지는 확인 필요. 저장소에 이미 Playwright 사용 흔적(docs/claude/ops-fixes.md 87행).
- agent-desktop: Apache-2.0, `npm install -g agent-desktop`, Windows는 권한 허락 없이 같은 권한 수준 앱 조작(README). MCP 아님(CLI). 스냅샷·클립보드에 개인 화면 내용 포함 경고.
- Aside: aside.com, YC 지원 에이전트 브라우저(Chromium), Windows 정식판 2026-09-14(runtimewire·piunikaweb 기사). 개발자 문서 docs.aside.com/help/developers: `aside mcp`, mcp.json 예시 {"command":"aside","args":["mcp"]}, 설치 명령은 macOS curl만 표시 — Windows 설치 확인 필요. Chrome 확장 설치 가능 여부 확인 필요.

## 사장이 직접 할 일 (고른 안에 따라 한 단계씩)

### 안 A — Claude in Chrome 재사용 (추천)
1. 회사PC에서 Chrome을 연다. 자동화용으로 **새 프로필**(예: "Claude용")을 만들고, 이 프로필에는 키움·은행 로그인을 하지 않는다.
2. 그 프로필에 Claude in Chrome 확장을 설치·로그인한다(이미 있으면 켜기만).
3. Chrome 설정 > 다운로드 > 위치를 `E:\사업\##금동한\_downloads`로 바꾸고 "다운로드 전 저장 위치 묻기"는 끈다. (이 폴더는 이미 승인된 E:\사업\##금동한 아래라 스레드가 받은 파일을 읽을 수 있다.)
4. 스레드에 "크롬 켰어"라고 말한다 → Claude가 연결 확인.

### 안 B — Playwright MCP 추가
1. Node.js 설치 확인: 사장 터미널에서 `node -v` (18 이상).
2. Claude 데스크톱 앱 > 설정 > 개발자 > 설정 편집(claude_desktop_config.json)의 mcpServers에 아래를 추가(키움 항목은 그대로 둔다):
   "playwright": {"command":"npx","args":["@playwright/mcp@0.0.x 확인 필요","--isolated","--output-dir","E:\\사업\\##금동한\\_downloads"]}
   (버전은 고정 권장 — 설치 직전 npm에서 최신 번호 확인)
3. Claude 앱 재시작 → 스레드에 "플레이라이트 넣었어".

### 안 C — Aside MCP 시범
1. Aside 앱 > Settings > Developer에서 CLI 설치 버튼이 Windows에서 보이는지 확인(문서 미기재).
2. 보이면 설치 후 표시되는 CLI 경로를 알려 준다 → Claude가 config 한 줄 초안을 만든다.
3. Aside Settings > Agents에서 세션 모드 "Read only" 또는 "Guard", 도구 규칙 기본 "Ask".
4. Aside에는 키움·은행 로그인을 하지 않는다.

## 바뀔 조건
- Aside 문서에 Windows CLI·MCP 도구 목록·다운로드 처리·모델 전송 범위가 확인되면 안 C를 1순위로 올릴 수 있다.
- Claude in Chrome이 Aside(Chromium)에 설치된다는 것이 확인되면 Aside를 안 A 경로로 쓸 수 있다.
- 웹 읽기가 실제로 막힌 사례가 쌓이면 firecrawl 재검토(키는 사장이 직접 넣음).

출처: 각 저장소 raw README·LICENSE(2026-11-03 15:4x KST 수신), docs.aside.com/help/developers·/help/security, aside.com, runtimewire.com·piunikaweb.com 기사(2026-09-14), 기존 선례 /mnt/project-files/tool-review/external-skill-tools-review-2026-10-25.md.
검토 완결: 원문 확인 8/10 · 내장 재검토 0회(설치·변경 없음, 사장 선택만 받음) · 미해결 4(Aside Windows CLI·Aside 모델 전송·Playwright 다운로드 저장 위치·스레드 노출 경로) · 자료 시점 2026-11-03 15:5x KST · 바뀔 조건 위 절.
