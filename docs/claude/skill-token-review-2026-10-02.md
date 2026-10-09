# 설치된 스킬 전체 재검토: 토큰 최적화 (2026-10-02)

- 상태: **완료(2026-10-02).** 플러그인 3개 끄기와 계정 스킬 2개 제거를 사용자가 직접 실행했고, 나머지는 현재 상태 유지. 최종 상태는 6절.
- 범위: 이 Cowork 세션의 스킬 목록 전체(플러그인 4개 + 기본 제공 + 계정 스킬 13개). 기존 기록은 `external-skills-review-2026-10-02.md` 8절.
- 측정 방식: 목록 한 줄("- 이름: 설명")을 o200k 토크나이저로 센 **근사치**다. Claude 실제 값과 다를 수 있다. 본문(SKILL.md)은 호출될 때만 로드되므로 상시 비용이 아니다(Anthropic 공식 문서: 이름·설명만 시작 시 로드).

## 0. 결론

1. 상시 비용 합계는 약 **4,300 토큰**이다. 이 세션에서는 같은 스킬 목록이 **2번** 붙는 것이 보였다(시스템 프롬프트 1회 + 도구 로드 뒤 메시지 1회). 항상 그런지는 확인 필요.
2. 1단계 권고: 플러그인 3개 끄기(engineering, equity-research, cowork-plugin-management). 약 **1,400 토큰(32%)** 절감. 모두 "Disable plugin" 토글로 되돌릴 수 있다.
3. 2단계 후보: 계정 스킬 중 안 쓰는 것(docx, pptx, google-workspace, learn, morning, import-memory). 약 **1,000 토큰**. 사용 여부는 사용자 답이 필요하다.
4. 내가 만든 계정 스킬 3개(loop-design-check, decision-council, context-layer-audit)는 목록 한 줄이 57~59 토큰이다. 더 줄이면 오작동 위험이 이득보다 크다. NO_CHANGE.
5. 효과는 작다(대화당 수천 토큰). 위험이 낮고 되돌릴 수 있어서 할 만한 정리다. 큰 비용(프로젝트 문서, 지연 로드 도구 이름 목록 등)은 이 검토 밖이며 측정하지 않았다.

## 1. 전체 표 (상시 비용 근사, 투자_V2 관련성, 처리안)

사용 빈도: 이 세션에서는 호출 횟수를 측정할 수 없다. 저장소 md/json 검색에서 아래 플러그인·스킬 이름이 **0건**, 메모리에도 사용 기록이 없다("사용 흔적 없음"). 실제 호출 수는 확인 필요(claude.ai Customize > Plugins의 "You" 수치가 보이면 그것으로).

### 1-1. equity-research 플러그인 (목록 15줄, 약 678)

| 항목 | 토큰≈ | 투자_V2 관련성 | 처리안 |
|---|---|---|---|
| 명령 9개: catalysts, earnings-preview, earnings, initiate, model-update, morning-note, screen, sector, thesis | 130 | 주제는 관련. 단 프로젝트 자체 프로토콜(stock_analysis v2.3, options v2.0)과 증거 규칙이 따로 있음 | 플러그인째 끄기 |
| 스킬 6개: catalyst-calendar 82, earnings-analysis 113, idea-generation 86, initiating-coverage 95, sector-overview 78, thesis-tracker 94 | 548 | 위와 같음. 보고서 8~12쪽, 차트 8~12개, 컨센서스 Bloomberg/FactSet 전제(원문 확인). 이 PC에는 해당 데이터 원천이 없음 | 플러그인째 끄기 |
| (목록에 안 보임) 스킬 earnings-preview, model-update, morning-note | 0(가려짐) | 같은 이름의 명령이 목록에 대신 보임 | 해당 없음 |

### 1-2. engineering 플러그인 (목록 10줄, 약 575)

| 항목 | 토큰≈ | 관련성 | 처리안 |
|---|---|---|---|
| architecture 55, code-review 61, debug 56, deploy-checklist 49, documentation 62, incident-response 63, standup 57, system-design 58, tech-debt 55, testing-strategy 59 | 575 | 낮음. 코드 수정은 Claude Code Builder, 검토는 `development-change-review.md` 절차(K0~K3, 별도 Judge)가 이미 있음. 일반 목적 도구가 같은 영역을 중복 | 플러그인째 끄기 |

### 1-3. cowork-plugin-management 플러그인 (2줄, 약 142)

| 항목 | 토큰≈ | 관련성 | 처리안 |
|---|---|---|---|
| cowork-plugin-customizer 60, create-cowork-plugin 82 | 142 | 낮음. 기본 `cowork-plugin`(79)과 실질 중복(2절) | 플러그인 끄기 |

### 1-4. hwpx 플러그인 (1줄, 약 180)

| 항목 | 토큰≈ | 관련성 | 처리안 |
|---|---|---|---|
| hwpx | 180 | 투자_V2와 무관. 오늘(2026-10-02) 갱신된 기록이 있어 다른 용도로 최근에 넣었을 가능성이 있음. `.mcp.json`에 로컬 `uv run hwpx-automation-mcp` 서버 정의가 있음(이 PC에서 실제 실행되는지는 확인 필요) | **유지** (사용자 확인 2026-10-02: 향후 직장 업무용, 투자 프로젝트와 무관) |

### 1-5. GitHub 플러그인 (스킬 0줄)

- 이 세션 스킬 목록·도구 목록에 노출되는 항목이 없다(확인함). 상시 비용 0으로 본다. 연결 정의는 `https://api.githubcopilot.com/mcp/` 하나이고 engineering 플러그인의 github 연결과 같은 주소다. 저장소 쓰기 권한이 걸린 연결이라 사용 안 하면 끄는 편이 안전하다(처리안: 사용자 확인 필요).

### 1-6. 기본 제공 (플러그인 아님, 약 937)

| 스킬 | 토큰≈ | 관련성 | 처리안 |
|---|---|---|---|
| dataviz | 332 | 중간. 현황판·통합 점검 Artifact 대시보드 작업에 쓰임 | 유지 |
| artifact-capabilities | 130 | 중간. 대시보드 자동 갱신 Artifact | 유지 |
| artifact-design 38, artifact-diagramming 46 | 84 | 중간 | 유지 |
| claude-in-chrome | 106 | 중간. saveticker 브라우저 읽기 계획과 연관 | 유지 |
| cowork-plugin | 79 | 낮음. 플러그인 만들기·고치기 | 끄는 방법 확인 필요 |
| explain-usage | 47 | 이번 같은 점검에 유용 | 유지 |
| setup-claude 54, workflow-authoring 50, plugin-authoring 55 | 159 | 낮음 | 끄는 방법 확인 필요 |

### 1-7. 계정 스킬 `anthropic-skills:*` (13개, 약 1,794)

| 스킬 | 토큰≈ | 관련성 | 처리안 |
|---|---|---|---|
| loop-design-check 59, decision-council 57, context-layer-audit 57 (내가 만든 것) | 173 | 높음 | 유지(NO_CHANGE) |
| docs | 246 | 중간. 문서는 Docs 형식이 기본이나 이 프로젝트 기록은 repo md | 유지 |
| pdf | 98 | 중간. SAVE Daily PDF를 읽을 가능성 | 유지 |
| xlsx | 212 | 낮음~중간 | 유지(사용 여부 확인) |
| skill-creator | 70 | 중간. 계정 스킬 수정 시 | 유지 |
| docx 217, pptx 223, google-workspace 213, learn 221, morning 84, import-memory 37 | 995 | 낮음. 프로젝트 흐름에 Word·PPT·Google 파일 작업 흔적 없음. 사용자 확인 2026-10-02: 용도를 인지하지 못함 | **끄기 확정 후보(4단계)** |

### 1-8. 합계 (근사)

| 묶음 | 토큰≈ | 비중 |
|---|---|---|
| equity-research | 678 | 16% |
| engineering | 575 | 13% |
| cowork-plugin-management | 142 | 3% |
| hwpx | 180 | 4% |
| 기본 제공 | 937 | 22% |
| 계정 스킬 | 1,794 | 42% |
| **합계** | **약 4,300** | 100% |

## 2. 중복 확인 (원문 근거)

| 쌍 | 판정 | 근거 |
|---|---|---|
| equity-research 명령 8개 ↔ 대응 스킬 | **실제 중복(별칭)** | 명령 파일이 231~372 B이고 "Load the `…` skill"만 적혀 있음: catalysts→catalyst-calendar, earnings-preview→earnings-preview, initiate→initiating-coverage, model-update→model-update, morning-note→morning-note, screen→idea-generation, sector→sector-overview, thesis→thesis-tracker. 공식 문서: 채팅에서는 명령이 스킬로 로드됨 |
| equity-research `earnings` 명령 ↔ `earnings-analysis` 스킬 | **부분 중복** | 명령(4.6 KB)이 시기 확인·자료 수집·beat/miss·차트 8~12개를 다시 적고 마지막에 `earnings-analysis`를 호출. 줄 단위 diff는 하지 않음 |
| cowork-plugin-management 2개 ↔ 기본 `cowork-plugin` | **실질 중복** | 기본 스킬 원문이 "새로 만들기"와 "기존 플러그인 고치기" 두 모드를 모두 담고, 참조하는 파일명(component-schemas.md, example-plugins.md, mcp-servers.md, search-strategies.md)이 플러그인 쪽 두 스킬의 references와 같음. 설명의 트리거 문구도 두 설명의 합집합. 본문 줄 단위 diff는 하지 않음 |
| GitHub 플러그인 ↔ engineering의 github 연결 | 연결 주소 중복 | 둘 다 `api.githubcopilot.com/mcp/` |
| anthropic-skills:docs ↔ docx ↔ google-workspace | 중복 아님 | 설명에 서로 쓰지 말아야 할 조건이 명시됨 |
| engineering ↔ 프로젝트 자체 개발 절차 | 영역 중복 | code-review·debug·testing-strategy·architecture가 Builder/Judge/K0~K3 절차와 같은 일을 함. 내용 동일성은 미확인 |

## 3. 끄기·제거 방법 (확인한 것만)

| 대상 | 방법 | 근거 | 비고 |
|---|---|---|---|
| 계정 스킬 | claude.ai 또는 데스크톱 앱 **Customize > Skills**에서 스킬 옆 스위치로 끄기. 삭제는 직접 만든 스킬만: 끈 뒤 "..." 메뉴 > Delete | Anthropic 지원 문서 "Use skills in Claude" | `ListSkills`에서 13개 모두 enabled 표시 |
| 플러그인 | **Customize > Plugins**에서 플러그인을 열고 **Disable plugin** 토글 끄기(다시 켜면 복구). 완전 제거는 메뉴 > **Remove** | Anthropic 플러그인 문서 "Manage installed plugins" | 개인 계정이라 조직 강제 설치(끌 수 없음)는 해당 없을 것으로 보나 확인 필요 |
| 플러그인 안의 스킬 하나만 끄기 | **불가로 보임** | 공식 개요 페이지는 플러그인 단위 토글만 설명. GitHub 이슈 #82424(사용자 요청)가 같은 한계를 지적 | 이슈는 사용자 보고라 재확인 필요 |
| 끄기가 재시작 뒤에도 유지되는지 | **확인 필요** | GitHub 이슈 #92850(사용자 보고): 데스크톱에서 knowledge-work 플러그인(engineering, cowork-plugin-management 포함)의 Disable/Delete가 재시작 뒤 되돌아온다는 보고. 이 계정에서 재현되는지는 미확인 | 끈 뒤 **새 대화**에서 스킬 목록을 열어 확인하는 단계를 둔다 |
| 기본 제공 스킬(cowork-plugin, setup-claude, workflow-authoring, plugin-authoring, dataviz, artifact-*) | **확인 필요** | 계정 스킬 목록(`ListSkills`)에 없음. 토글 위치 미확인 | 이번엔 건드리지 않음 |
| Claude Code 세션 | 계정에 설치한 플러그인은 다음 Code 세션에서 동기화되어 로드된다는 공식 문장 확인. 이 PC의 Builder/Judge 세션에 실제 로드되는지는 **확인 필요** | 플러그인 문서 "Find the plugin in each app" | 로드된다면 끄기의 효과가 Builder/Judge 세션에도 미침 |

## 4. 설치·제거 전 검토 (토큰·보안·기존 결정)

- 토큰: 위 표. 끄기는 목록 줄만 줄이고 본문 로드와 무관하다.
- 보안: equity-research는 hooks 비어 있음(`{"hooks": {}}`), 연결 정의 없음 → 지시문뿐. engineering은 Slack·Linear·Asana·Atlassian·Notion·GitHub·PagerDuty·Datadog·Google Calendar·Gmail 연결 정의가 들어 있으나 이 세션에 연결된 도구는 없음(공식 문서: 플러그인 추가가 연결을 만들지는 않음). hwpx는 로컬 서버 실행 정의가 있음. 이번 단계는 **끄기만** 하므로 새 권한이 생기지 않는다.
- 기존 결정: 커널 §7 NO_CHANGE → REMOVE/SIMPLIFY 순서에 맞음. gstack 선례(전역 설치 없음), 8절 "계정 스킬 3개 설치"와 충돌 없음. `Execution-Authority: NONE`·키움 경계에 영향 없음. 저장소 파일·정책은 바꾸지 않는다.

## 5. 처리안 요약과 진행 순서

| 단계 | 내용 | 절감≈ | 되돌리기 | 상태 |
|---|---|---|---|---|
| 1 | engineering 플러그인 끄기 → 새 대화에서 목록 확인 | 575 | 토글 다시 켜기 | 완료(사용자 보고 2026-10-02). 서버 목록(ListPlugins)에서 사라짐 확인. 새 대화 목록·재시작 뒤 유지는 확인 필요 |
| 2 | equity-research 플러그인 끄기 → 확인 | 678 | 같음 | 완료(사용자 보고 2026-10-02, 서버 목록에서 사라짐 확인, 유지 여부는 확인 필요) |
| 3 | cowork-plugin-management 플러그인 끄기 → 확인 | 142 | 같음 | 완료(같은 방식으로 확인) |
| 4 | 계정 스킬 6개 중 사용자가 제거한 것: google-workspace, learn (끄기 스위치는 사용자 화면에 없고 제거만 있었음) | 434 | 되돌리는 방법 확인 필요 | 완료 후 보류. 나머지 4개(docx, pptx, morning, import-memory)는 현재 상태 유지 |
| 5 | hwpx 유지(직장 업무용 예정). GitHub 플러그인은 용도 확인 필요 | 0 | - | hwpx 결정 완료, GitHub 미결정 |
| - | 내 계정 스킬 3개 설명 줄이기 | 약 50 미만 | - | 하지 않음 |

- 1단계가 재시작 뒤에도 유지되는지(이슈 #92850)를 먼저 확인한 뒤 2단계로 간다. 유지되지 않으면 이후 단계를 멈추고 보고한다.
- 한 달쯤 뒤 불편한 점(필요한 스킬이 없다)이 있으면 토글로 다시 켠다.

## 6. 최종 상태 (2026-10-02, 사용자 결정 "현재 상태 유지")

| 항목 | 결과 | 확인 방법 |
|---|---|---|
| engineering, equity-research, cowork-plugin-management 플러그인 | 끔(약 1,395토큰 감소). 새 대화·재시작 뒤 유지 여부는 확인 필요 | 서버 플러그인 목록(ListPlugins)에서 사라짐 |
| 계정 스킬 google-workspace, learn | 사용자가 제거(약 434토큰 감소). 되돌리는 방법은 확인 필요 | 계정 스킬 목록(ListSkills)에서 사라짐 |
| 계정 스킬 docx, pptx, morning, import-memory | 그대로 켜져 있음. docx는 사용자가 제거했다고 했으나 목록에 남아 있었음(최종 조회에서도 enabled) | ListSkills |
| hwpx, GitHub 플러그인 | 그대로 둠 | ListPlugins |
| 내 계정 스킬 3개, pdf, xlsx, docs, skill-creator, 기본 제공 스킬 | 그대로 둠 | ListSkills |

- 합계: 약 1,830토큰 감소(상시 4,300 → 약 2,480, 근사). 이 세션의 목록은 시작 시점에 고정되어 있어 실제 반영은 새 대화에서 확인한다.
- 정정: 계정 스킬 화면에 끄기 스위치가 없고 제거만 있는 사용자 화면이 확인됨. 3절의 "스위치로 끄기" 설명(공식 문서 기준)은 이 화면과 맞지 않는다.
- 남은 확인 필요: 새 대화에서 3개 플러그인 항목이 정말 사라졌는지, docx가 목록에 남은 이유, 제거한 스킬의 복구 방법, 기본 제공 스킬을 끄는 위치.

## 출처

- Anthropic 지원 문서, Use skills in Claude: https://support.claude.com/en/articles/12512180-use-skills-in-claude
- Anthropic 문서, Plugins overview(Manage installed plugins, Find the plugin in each app): https://claude.com/docs/plugins/overview
- Anthropic 문서, Agent Skills overview(메타데이터 상시 로드, 본문은 트리거 시): https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- GitHub 이슈(사용자 보고): https://github.com/anthropics/claude-code/issues/82424 , https://github.com/anthropics/claude-code/issues/92850
- 로컬 원문(클라우드 작업공간에 동기화된 플러그인 파일): equity-research `commands/*.md`, `skills/*/SKILL.md`, `hooks/hooks.json`; engineering `.mcp.json`; cowork-plugin-management `skills/*/references`; hwpx `.mcp.json`
