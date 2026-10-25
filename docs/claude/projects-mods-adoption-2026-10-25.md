---
id: projects-mods-adoption-2026-10-25
title: "Claude Code Projects + Mods 도입 검토 (projects-1025)"
date: "2026-10-25"
status: "제안 · 결정 대기 projects-1025 (기한 2026-11-01, 무응답 = Q1 c · Q2 c 현행 유지)"
class: "제안(문서). 이 문서는 아무것도 켜지 않는다. Q1 a의 본 작업은 권한·한도 변경(K3, 수동 경로) — 권한 작업 칸이 비면 착수(지금 cashflow-api-gap 진행 중)"
authority: "order_authority=false · quantity_authority=none · 키움 주문 도구 금지 · 승인은 사장이 직접 친 메시지만(sc-1022 S4·S7)"
consumers: "사장 · 비서실 · 관제판 secretary-projects · sc-1022 10절 · secretary-1021 8-1 · duet-trial · 주간 팀장회의(법률팀)"
weekly_user_touch: "Q1 a: 일상 0(비서실 그대로) · 1회성: 결정 1줄 + 앱 화면 확인 3가지(3절). Projects 실제 운영(K3 뒤)은 '승인 1건당 그 스레드 열기 +1'이 생길 수 있음 — K3에서 줄이는 방법을 정함"
basis: "사장 원문 2026-10-25 08:47·08:52 · code.claude.com/docs/en/claude-projects.md(조회 2026-10-25 08:5x, 행 번호는 저장 사본 기준) · claude.com/ko/resources/articles/projects-redesigned · PICKIT 'Mods 활용 3가지 세팅 가이드'(Notion, 2026-10-12 확인 기준, 내장 브라우저로 본문 조회) · it-connect Mods 기사 · 회사PC 실측(2절) · CLAUDE.md:27·34·58·115"
---

# Claude Code Projects + Mods 도입 검토 (2026-10-25)

## 0. 결론
1. **Projects는 sc-1022 지침(창구 1개 + 먼저 제시)을 담기에 가장 맞는 공식 그릇이지만, 지금 규칙으로는 비서실을 대신할 수 없다.** PC 일을 하는 Projects 스레드(로컬 스레드)는 "Claude Code 세션"이고(공식 250행), CLAUDE.md는 Claude Code 세션의 apply·결정 일지 쓰기·dev-run/dev-merge를 금지한다(27·34·115행). 승인 장소도 Cowork 대화로 정해져 있다(33·58행, S7). 즉 비서실의 핵심 일(승인 받기·병합·Builder/Judge 띄우기)을 Projects로 옮기는 것 자체가 **권한 규칙 변경(K3)** 이다.
2. 게다가 안전장치가 Projects에서 약해진다: 클라우드 스레드는 저장소 권한 규칙·훅을 안 읽고(57·246·345행) auto mode로 돌며, 로컬 스레드도 auto mode(271행)이고 저장소 deny 23줄은 desktop-commander 셸을 막지 않는다(2절 ⑤).
3. 그래서 권장(Q1 a): **지금은 비서실 유지(창구·실행 NO_CHANGE) + "Projects 운영 규칙"을 K3 안건으로 등록**(권한 작업 칸이 비면 착수, Builder → 독립 Judge → 사장 병합 결정) + 사장이 앱 화면에서 3가지만 확인.
4. **Mods는 "설치하지 않는 규칙"부터(Q2 a).** 가이드의 3가지 세팅(창 두 개 분업 · 현황판 패널 · 모델 나누기)은 Projects·기존 기능과 겹쳐 이익이 없고, 모드는 샌드박스 없이 내 권한으로 돌며 묻지 않고 승인할 수 있다 → 모드 설치 = 권한·한도 변경 등급. 다른 세션 메시지는 '보류'로.
5. 덤으로 찾은 기존 결함 후보: 저장소 deny가 막는 dev-merge·apply·auto_core 실행을 **desktop-commander(MCP 셸)로는 우회할 수 있다**(2절 ⑤). 헤드리스 Builder·Judge에 desktop-commander가 로드되는지는 확인 필요 — K3 안건 ②에 함께 넣는다.

## 1. Projects에서 투자_V2에 중요한 사실 (공식 문서 claude-projects.md, 행 번호)
| 사실 | 행 | 영향 |
|---|---|---|
| 프로젝트 = 코디네이터 대화 1개 + 일하는 스레드(각자 별도 세션) | 53-54 | 비서실 + 하위 에이전트와 같은 모양 |
| Overview: Ready for review · Waiting on you · Working · Landing · Idle · Resolved / Library · Pull requests · Scheduled tasks | 194-207 | 먼저 제시(지침 ②)의 일부를 기본 기능이 함. 단 Waiting on you는 스레드 승인·실패만 모음 → 관제판 결정함은 못 대신함 |
| 알림은 데스크톱 앱만(브라우저는 점 표시) | 190 | 휴대폰 먼저 알림은 기존 예약 작업 푸시가 계속 맡음 |
| 클라우드 스레드: CLAUDE.md는 읽음, `.claude/settings.json` 권한 규칙·훅·skills·.mcp.json은 안 읽음, auto mode | 57, 244-246, 336-347 | 저장소 deny 미적용 → 코드·운영 금지 |
| 클라우드 스레드는 기본 브랜치에서 시작, PR을 스스로 열 수 있고 auto-fix로 감시, push 권한 필요 | 82, 174-176, 408 | 2절 ①·작업 브랜치 push 충돌 위험(23:30 문서 커밋) |
| 로컬 스레드(Remote Control): PC의 파일·MCP·설정·훅·권한 규칙 사용, 지침은 받고 기억은 안 받음, auto mode, PC 깨어 있을 때만, "Require trusted devices" 켜져 있으면 불가 | 250-275 | 권한 규칙은 걸리지만 auto mode라 묻지 않음. trusted devices를 끄는 것은 보안 완화 |
| 승인 프롬프트는 그 스레드 안에서만 답함, "스레드 나머지 전체 허용" 선택지 있음 | 244-246 | 승인이 스레드마다 흩어짐(S1과 충돌) |
| 지침 16,000자 · 프로젝트 기억(MEMORY.md)은 Claude가 스스로 씀 · 대화로 준 규칙은 "강제 설정 아님" | 240, 283-287 | 기억 저장소가 하나 더 생기고 S4(기억 쓰기 = 사장 직접 메시지)와 충돌 |
| Pause = 스레드·대화·프로젝트 예약 전부 정지 | 390 | LLM 층 비상 정지. Windows 자동 코어는 안 멈춤 |
| 사용량: 요금제 한도 공유, 새 스레드 하루 200개, 새 프로젝트 스레드 기본 Opus high, 추가 사용량 꺼져 있으면 초과 안 함 | 153, 220, 396-410 | 스레드 모델 기본값을 낮춰야 함 |
| 클라우드 샌드박스 복구 실패 시 커밋 안 한 변경 사라짐 · 베타 동안 조직 제어 없음 | 441-442 | 클라우드 산출은 Library 파일로만 |
| "Get started"가 뜨면 기존 claude.ai 프로젝트를 업그레이드 또는 보관 먼저 | 91 | 이 투자_V2 프로젝트의 지식 문서 5개·기억이 어떻게 되는지 원문 없음 → 확인 필요 |

## 2. 회사PC 실측 (2026-10-25 08:5x~09:1x KST, 이 세션)
- ① GitHub: origin 기본 브랜치 = main, main 마지막 커밋 2026-08-14. 작업 브랜치 codex/master-recovery-expansion은 main보다 441커밋 앞, 마지막 push 2026-10-24 23:30(e1be00e) → 클라우드 스레드가 그냥 시작하면 2개월 전 코드·CLAUDE.md를 읽는다.
- ② git 밖: portfolio_state.json · alert_runtime_state.json · decision_journal.json(.gitignore 31·32·53행) → 클라우드 스레드는 운영 상태를 못 본다.
- ③ Claude Code 2.1.305(Windows `claude --version`). 가이드 기준 Mods 2.1.287 이상 · 세션 메시지 2.1.234 이상(Windows)을 넘음. %USERPROFILE%\.claude\dev-mods 없음(만든 모드 없음).
- ④ 저장소 폴더 `claude mcp list` 이름만: claude.ai 커넥터 5개(Claude Docs·Dropbox·Director's Lookbook·korean-law·Context7) + 플러그인 desktop-commander·hwpx-plugin·design·github. **키움 MCP 없음**(키움은 데스크톱 앱 쪽에만).
- ⑤ 저장소 .claude/settings.json: deny 23줄(dev-run·dev-merge·dev-queue, reconcile apply, auto_core.py, 일지 apply, 상태·일지 수정, .env 읽기, `mcp__*__kiwoom_order_submit` 등) · ask 8줄 · 훅 없음. desktop-commander 도구를 막는 줄은 없음.
- 확인 필요: Claude GitHub 앱 설치 여부 · "Require trusted devices" 상태 · 헤드리스 Builder(dev-run)에 desktop-commander가 로드되는지 · auto mode에서 ask 규칙이 지켜지는지 · sec-default가 개인 Max에서 로드되는지(가이드는 내장 모드로, 기사는 개인 Pro/Max엔 없다고 적음).

## 3. Q1 a로 할 일
| 단계 | 하는 일 | 누가 |
|---|---|---|
| A1 | 앱 화면 확인 3가지(누르지 말고 보기만): ㉠ Code 탭 → Projects를 눌렀을 때 "New project"인지 "Get started"인지, Get started면 목록에 뜨는 기존 프로젝트 이름 ㉡ 설정 → Claude Code의 "Use this computer from your phone…"·"Require trusted devices" 켜짐 여부 ㉢ github.com/settings/installations에 Claude 앱이 저장소를 포함하는지 | 사장(1회) |
| A2 | 관제판 secretary-projects를 "K3 안건 대기(권한 칸 비면 착수)"로 바꿈 | 비서(이 결정 뒤) |
| A3 | K3 안건 "Projects 운영 규칙" 착수(cashflow-api-gap 끝난 뒤): 아래 ①~⑦을 Builder 지시문으로 → 독립 Judge(Opus xhigh) → 사장 병합 결정 | 비서·사장 |
| A4 | K3 병합 뒤에만 1주 시험(5절) | — |

K3 안건 내용(①~⑦):
- ① **승인 장소**: 승인류(결정 일지 apply · 대조 '확인 <코드>' · 정책·상태 변경 · "켜" · 권한 작업 착수·병합 · -ApproveAuthority)를 Projects로 옮길지, 비서실 Cowork에 영구히 남길지. 옮긴다면 portfolio_review_journal.py CONFIRMATION_METHODS 값 추가·"스레드 나머지 전체 허용" 금지·코디네이터가 옮긴 문장/버튼/예약 실행은 승인 아님(S7 유지).
- ② **셸 우회 막기**: desktop-commander 도구 deny(또는 Projects 로컬 스레드 전용 폴더·설정) — 헤드리스 Builder·Judge에도 같은 구멍이 있는지 먼저 확인.
- ③ **auto mode**: 로컬 스레드는 auto mode 끔(공식 271행 — 끄면 프롬프트가 스레드에서 대기) 또는 ask 규칙이 auto mode에서도 지켜짐을 확인.
- ④ **trusted devices**: 로컬 스레드에 필요하면 끄는 것은 보안 완화로 따로 판단.
- ⑤ **GitHub**: 클라우드 스레드는 push 권한이 필요하고 PR을 스스로 열 수 있음 → 작업 브랜치 보호 규칙 또는 저장소 연결 없이(Library 사본) 중 선택, 지침에 "codex/master-recovery-expansion에서 읽기만, push·PR 금지".
- ⑥ **기억 1곳**: 프로젝트 기억에는 위치 안내만, 결정·승인·규칙 저장 금지(S4), 매일 1회 기억 변경 확인.
- ⑦ **사용량**: 스레드 기본 Sonnet 5.5·medium, 동시 3개 이하, K3·Judge만 Opus xhigh. 비상 시 Pause(LLM 층) — 자동 코어 정지는 기존 kill switch.

## 4. 현재 → Projects 대응 (K3 뒤 기준, NO_CHANGE → REMOVE → REUSE → REPLACE → ADD)
| 지금 | 판정 | Projects에서 |
|---|---|---|
| Windows 자동 코어·독립 대조·개발 큐·문서 커밋·백업 | NO_CHANGE | 그대로. Pause와 무관 |
| Cowork 예약 작업(통합점검·SAVE·현황판·비서 09:25 등) | NO_CHANGE | 그대로. 프로젝트 예약(클라우드)으로 옮기지 않음 — PC·git 밖 기록에 못 닿음 |
| 비서실 Cowork 대화 | K3 ① 결과에 따름 | ①에서 승인을 옮기면 REPLACE, 아니면 비서실 = 승인·PC 창구로 유지 |
| 하위 에이전트 검토·조사 | REUSE | 클라우드 스레드 → Library 파일, 비서가 원문 재확인 |
| 일반 코드 변경 = 개발 파이프라인 | NO_CHANGE | 클라우드 PR·"Merge it" 버튼 쓰지 않음(PC 저장소가 원본, 기본 브랜치 낡음, deny 미적용) |
| K3 Builder·Judge | K3 ①·② 결과에 따름 | 로컬 스레드 Builder(Worktree) + 별도 Judge 스레드 가능성 |
| 관제판 결정함·주간 팀장회의·통합점검 주문표·현황판 | NO_CHANGE | Waiting on you는 결정함을 대신 못함 |
| Duet 시험 | NO_CHANGE(대기) | Duet이 열리면 Projects와 비교만 |

## 5. 1주 시험 사전 등록 (K3 병합 뒤에만)
- 통과 = ①~⑤ 모두. 미달·무응답 = 비서실 유지(알림만). 시험 중에도 승인류는 K3 ①에서 정한 장소만.
| # | 확인 | 판정 근거(자기보고 아님) |
|---|---|---|
| ① | 클라우드 스레드가 작업 브랜치 CLAUDE.md를 읽음 | 스레드 transcript의 clone 브랜치 표시 + 인용 줄 |
| ② | 로컬 스레드가 docs/claude에 문서 1개 쓰고 큐·상태 파일은 안 건드림 | 회사PC `git status` |
| ③ | 로컬 스레드에 키움 주문 도구·desktop-commander 없음/거부 | `claude mcp list` 원문 + settings deny 줄 |
| ④ | 코디네이터가 승인류 일을 스스로 하지 않음 | 시험 문장에 대한 코디네이터 답 + 관련 파일 변경 없음(git status) |
| ⑤ | 1주 사용량 | 기존 예약 작업이 한도로 막힌 날 0(예약 실행 기록) |

## 6. Mods 검토 (PICKIT 가이드 3가지 + 기사)
| 세팅 | 가이드 요지 | 판정 | 이유 |
|---|---|---|---|
| ① 창 두 개 분업 | 세션 메시지(기본 기능): /rename → @이름, 글만 전달, 같은 컴퓨터만, 계획은 파일로 | 쓰지 않음 | Projects·개발 파이프라인이 같은 일. 다른 세션 메시지는 도착하면 새 턴을 시작함 → 다른 창이 Builder에게 일을 시키는 통로 |
| ② 작업 현황판 패널 | 내장 현황판 없음, 말로 만든 모드, 터미널·Code 탭 로컬 세션에만 화면(가이드) | 만들지 않음 | Overview·관제판이 맡음. 사장은 PC 터미널을 보지 않음 |
| ③ 일 크기대로 모델 나누기 | turn.step 훅에 잔일 기준을 써야 갈림 | 쓰지 않음 | 스레드 모델 설정·하위 에이전트 model 칸으로 충분. 판단 일이 Haiku로 가면 Haiku 규칙 위반 위험 |
- 보안: 모드는 샌드박스 없이 내 권한 — 파일·키 읽기, 다른 세션에 메시지, 묻지 않고 승인(가이드·기사 공통). deny가 모드를 막는지는 sec-default 로드 여부에 달림 — 확인 필요, 막지 못한다고 보고 판단.
- Q2 a: ㉮ 외부 모드 설치 금지, 직접 만든 모드도 설치 = 권한·한도 변경 등급(사장 승인 + `claude plugin validate`의 hooks:·calls: 검토 + 독립 Judge) ㉯ PC **사용자 설정**(%USERPROFILE%\.claude, 저장소 아님)의 "Messages from your other sessions"(crossSessionInbound)를 hold로 — 제약 강화 쪽, CLAUDE.md:115-116에 따라 사장 승인 뒤 비서가 적용 ㉰ 이익이 분명해지면 1건씩 제안. ㉮는 CLAUDE.md 한 줄(보호 경로)이라 K3 안건과 같은 수동 경로 묶음에 넣음, 그 전엔 이 문서·관제판 규칙으로 적용.

## 7. 결정 요청 projects-1025 (기한 2026-11-01)
**Q1 Projects** — 무응답 = c
- **a) 권장** 비서실 유지 + 3절 A1(화면 확인 3가지) + K3 안건 "Projects 운영 규칙"(①~⑦) 등록, 권한 칸이 비면 착수 → 병합 뒤 5절 시험.
- b) 지금 제한 시험: 저장소 연결 없이 클라우드 스레드 조사·문서만(Library), 승인·PC 일은 비서실. 창구가 2개가 됨(S1 예외), 조사 의뢰마다 프로젝트에 입력 +1.
- c) 현행 유지(Projects 보류, 비서실 그대로).
**Q2 Mods** — 무응답 = c
- **a) 권장** 6절 ㉮ + ㉯(다른 세션 메시지 hold).
- b) ㉮만.
- c) 현행 유지(규칙 없음 — 설치된 모드 없음).
- 답 예: `결정 projects-1025: Q1 a, Q2 a`

## 8. 버린 대안
| 대안 | 버린 이유 |
|---|---|
| 비서실을 바로 Projects로 교체(초안의 1주 시험) | 0절 1·2 — Claude Code 세션 금지 조항·승인 장소 변경이 표시 없이 들어감(제약 완화) |
| 클라우드 스레드로 코드 변경·PR 병합 | deny·훅 미적용, 기본 브랜치 낡음, PC 저장소가 자동 코어 원본 |
| 예약 작업을 프로젝트 예약(클라우드)으로 이전 | PC·키움·git 밖 기록에 못 닿음 |
| 기존 투자_V2 claude.ai 프로젝트를 바로 업그레이드 | 지식 문서·기억 이동 방식 원문 없음 |
| Mods 3가지 설치 | 6절 — 겹침 + 승인 우회 위험 |
| 베타 성숙까지 아무것도 안 함 | c와 같음. 단 A1 확인·K3 설계는 비용이 작고 Projects가 열릴 때 바로 쓰게 해 줌 |

## 9. 바뀔 조건
- A1에서 Get started 목록·trusted devices·GitHub 앱 상태가 확인됨 → K3 ④⑤ 범위 조정.
- 공식 문서에서 클라우드 스레드가 저장소 권한 규칙을 적용하게 바뀜 → 클라우드 코드 변경 재검토.
- sec-default가 개인 Max에서 로드된다는 공식 원문 → 6절 위험 낮춤.
- 키움 MCP가 Claude Code 쪽에 등록됨 → Projects 로컬 스레드 즉시 중지, 재검토.

## 10. 내장 재검토 기록
- 1회차(2026-10-25 09:0x, 하위 에이전트, 읽기 전용, 10건): 결론 변경 반영 — ① deny 1줄 → 23줄·ask 8줄(본 세션 재확인) ② 로컬 스레드 승인(R2)은 CLAUDE.md:27·34·115 위반 = K3(본 세션 grep 확인) → 비서실 교체 시험 철회, K3 안건으로 ③ desktop-commander deny 우회(본 세션 확인: deny에 desktop 줄 없음) ④ trusted devices·GitHub push/PR·프로젝트 기억 위험 추가 ⑤ crossSessionInbound는 사용자 설정 ⑥ 시험 판정을 자기보고 → 원문, 통과 = 전부, ⑥ 항목 삭제 ⑦ 주간 손 +0 → 실제 운영 시 승인당 +1 가능 ⑧ 대안 b(클라우드만)·"베타 대기" 추가 ⑨ Landing 추가, 가이드 출처 표시. 관제판 조회: 진행 중 권한 작업 cashflow-api-gap(K3, Builder 실행 중) → 새 K3는 대기.
- 2회차: 결론이 바뀐 부분(0절·3절·7절)만 자체 점검 — 기존 제약을 완화하는 항목 없음(K3 안건은 등록만, 기본값 c), 기본값이 권한을 올리지 않음, 일상 손 0.

검토 완결: 원문 확인 9/11(공식 문서·영상 설명 3·가이드·기사·CLAUDE.md·settings.json·git·mcp list; 미확인 = 기존 프로젝트 업그레이드 결과, sec-default 개인 요금제 로드) · 내장 재검토 2회(반영 10건) · 미해결 5(2절 확인 필요 — A1·K3 ②③에서 확인, 그 전엔 Projects 미사용으로 보수적) · 자료 시점 2026-10-25 08:47~09:1x KST · 바뀔 조건 9절.

## 11. 결정 기록
- 사장 원문(2026-10-25 09:11 KST, Cowork 비서실, 직접 친 메시지): "Projects는 \"창구 1개 + 비서가 먼저 제시\" 지침에 가장 잘 맞는 기능이므로 현재 시스템의 상위 버전이다. 따라서 현재 시스템을 \"Claude Code projects\"로 이사한다. 이를 위한 모든 권한 승인." → 7절 권장(Q1 a 보류형) 대신 **이사 진행**으로 읽음. Q2(Mods)는 답 없음.
- 범위(S7·Hard safety 그대로): 주문·키움 주문 도구 금지는 이 승인으로도 안 바뀜. K3 안건(3절 ①~⑦)은 Builder → 독립 Judge까지 진행 가능, 병합은 Judge 결과를 본 뒤 사장 한 줄(-ApproveAuthority 포함). 보안 설정(trusted devices 등)·앱 화면 조작은 사장이 직접.
- 09:12 사장: Claude Code 처음이라 설정법 단계별 안내 요청. 09:15 화면: "프로젝트 업그레이드 — 이 프로젝트들이 보관됩니다: 환경영향평가·투자_V2(로컬 폴더는 아직 업그레이드할 수 없습니다)" [나중에]/[프로젝트 2개 보관].
- 09:1x 사장 선택 "백업 후 보관(권장)" → 백업 완료: E:\사업\##금동한\투자_V2_옛프로젝트_백업_2026-10-25\ (지침·문서 5·기억 5, 해시 12개 PC 대조 일치). 환경영향평가는 이 세션에서 못 읽어 백업 안 함.
- 09:24 "프로젝트 2개 보관" 완료(화면 알림) · 반복 예약 작업 3개 확인 — 켜짐·코덱스저장소 폴더 그대로(보관 영향 없음). 09:27 새 프로젝트 "투자_V2 사장실" 생성(컨텍스트 비움). 09:33 스레드 모델 Sonnet 5.5·중간, 코디네이터 Opus 5.5·낮음 확인. 지침 v1 = docs/claude/projects-instructions-v1.md(임시 안전 껍데기).
- 09:35 사장 "새 판: a" — 실행층(자동 코어·키움 읽기 전용·대조·결정 일지·정책)·점검층(예약 작업)은 유지, 소통층(비서실·비서 제안·결정함·Duet)·규칙층(CLAUDE.md Cowork 조항·승인 장소·S1~S7·기억)은 Projects 기준으로 새로. 순서: ① 지금 v1 + 회사PC 연결 ② 주간 사용량 초기화(10/26 11:00) 뒤 "Projects 새 판" 설계 문서(새 프로젝트 첫 일) ③ 사장 승인 뒤 K3 하나로 Builder → 독립 Judge → 병합 결정.
