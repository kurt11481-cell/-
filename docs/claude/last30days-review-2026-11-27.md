# last30days 도입 검토 (2026-11-27 KST)

결론: 🟢 NO_CHANGE — 설치하지 않는다(권고, 사장 결정 아님). 주된 이유는 실익 부족이다. 안전하게 돌릴 수 있는 길(클라우드·키 없음)에서는 Reddit이 막혀 Polymarket·HN·GitHub만 남는데, 이것은 이미 우리 수집과 겹친다. 회사PC에서 돌리면 비밀 읽기·외부 전송·자동 갱신 위험이 더해진다. 아이디어 2개만 기록해 둔다(7절).

## 1. 확인한 범위와 한계
- 대상: github.com/mvanhorn/last30days-skill, 커밋 3fd94654 (2026-11-27 13:06 KST, v4.8.0), MIT 라이선스(LICENSE 확인).
- 읽은 것: README.md, SECURITY.md, CONFIGURATION.md 일부, skills/last30days/SKILL.md, 코드 일부(reddit_keyless.py·stocktwits.py·polymarket.py·http.py). 클라우드 컨테이너에 `git clone --depth 1`만 했다. **설치·실행·시험은 하지 않았다.**
- 코드 전체의 실제 동작, 별 수·관리자 반응 속도는 "확인 필요".
- 선례: 저장소 docs/·docs/claude·프로젝트 파일 tool-review/에 last30days 검토 없음. 가장 가까운 선례는 external-repos-review-2026-10-05.md 50행 C11 "X·Reddit 소셜 채널(Agent-Reach) 거절"과 Agent-Reach 10/25 기각.

## 2. 이 도구가 하는 일 (README·SECURITY.md·CONFIGURATION.md 근거)
- 한 줄: 주제 하나를 주면 지난 30일의 Reddit·X·YouTube·TikTok·HN·Polymarket·GitHub·StockTwits·Yahoo Finance 주가·특허·채용 페이지 등 약 30개 출처(README 표 71~100행)를 동시에 찾아, 추천·좋아요·거래액으로 점수를 매기고 AI가 요약 1장을 쓰는 스킬이다. Claude Code 플러그인·MCP 서버·npx로 설치한다.
- 키 없이 켜지는 것: Reddit·HN·Polymarket·GitHub, 회사 주제면 특허(USPTO)·채용 페이지, 티커 주제면 StockTwits. 나머지는 키·쿠키·외부 CLI 설치나 선택 사용으로 켜진다.
- 투자 쪽 기능: StockTwits 종목 여론, Yahoo Finance 30일 주가 대 S&P 500, Polymarket 확률 줄, 채용·특허 '비밀 신호', DripStack(금융 뉴스레터·애널리스트 글, 키 없음, 선택 사용), watchlist(종목별 정기 감시, 새 발견 때 웹훅, CONFIGURATION.md 934행), `--emit=json` 기계 출력.

## 3. 판단 순서 (지침 8절)
1. **NO_CHANGE — 채택.** 근거는 4~6절.
2. REMOVE/SIMPLIFY — 해당 없음.
3. **REUSE — 이미 있는 것으로 된다.**
   - Polymarket·Kalshi: 시나리오 확률 매일 점검이 이미 직접 읽는다(scenario-odds README 36·111행).
   - X: 외부 정보 수집이 사장 Chrome으로 3계정을 읽는다. X 공식 API는 11/07 사장 결정으로 안 씀.
   - 종목 소식: 주간 관심 명단 재채점 v3.6이 보도자료를 연다. finviz 10종목 수집도 있다.
   - 심리 자료: 심리 단서 5종과 등급표가 이미 있다. 결과는 "등급 1 없음"(psych-1123).
   - 한 번 하는 조사: 스레드의 웹 검색·브라우저 읽기로 같은 일을 한다.
4. REPLACE — 바꿀 대상 없음.
5. ADD — 새로 얻는 것은 Reddit·StockTwits·DripStack·채용·특허뿐이다. Reddit·StockTwits는 커뮤니티라 가설 등급이고, 도구 스스로 StockTwits를 "분석으로 쓰지 말 것, 봇·펌프 소음 흔함"이라 적었다(stocktwits.py 11~12행). 채용·특허는 1차 자료지만 '비밀 신호' 해석은 AI 추정이라 가설 등급이다. 특허는 출원 약 18개월 뒤 공개라(CONFIGURATION.md 706행) 선행성도 제한적이다.

## 4. 적용안 비교
| 안 | 내용 | 판단 |
|---|---|---|
| A 설치 안 함 | 지금 수집 그대로 | **권고** |
| B 1회 격리 시험 | claude.ai 웹 업로드(자동 갱신 없음)나 클라우드 컨테이너에서 키 없이 1회 | 실익 없음. 데이터센터 IP에서는 Reddit 무료 길이 403이라(reddit_keyless.py 309행, 이 컨테이너에서도 reddit.com 차단 화면 확인) HN·Polymarket·GitHub만 남고 우리 수집과 겹친다. 외부 코드 실행이라 개발 큐·사장 카드도 필요 |
| C watchlist 정기 감시 | 보유·관심 종목을 매일 돌림 | 안 됨. 보유 종목 이름이 매일 여러 외부 서비스로 나가고, robots 규칙·예약 변경 승인 대상이며, 웹훅은 공개 https 주소로 보낸다(CONFIGURATION.md 934행) |
| D 아이디어만 차용 | 도구 없이 생각만 가져옴 | 기록만(7절) |

## 5. 투자_V2에 닿는 지점별 위험
| 지점 | 결과 |
|---|---|
| 절대 안전(주문 금지) | 주문 기능 없음. 직접 충돌 없음. |
| 비밀 읽기 금지(.env·토큰) | **충돌.** 스킬이 에이전트에게 실행 때마다 `~/.config/last30days/.env`를 grep하게 하고(SKILL.md 135~136행), 키를 환경변수·.env·키체인·pass에서 찾으며 다른 용도로 넣어 둔 키도 쓴다(SECURITY.md 'Hosted reasoning models'). 브라우저 쿠키는 동의할 때만 읽고, Windows에서는 Firefox만 읽는다(CONFIGURATION.md 100·336행) — 회사PC가 Windows면 Chrome X 로그인은 안 읽힘(회사PC OS는 확인 필요). |
| 외부 전송 | 주제 글이 켜진 모든 출처와 검색(DuckDuckGo·Startpage)·Wikidata·USPTO·채용 사이트로 간다. 보유·관심 종목을 넣으면 **포트폴리오 구성이 여러 외부 서비스로 흘러간다.** Gemini·OpenAI·xAI·OpenRouter 키가 하나라도 있으면 매번 주제와 수집 글을 그쪽에 보낸다. 조사 보고서가 `~/Documents/Last30Days`에 쌓인다. |
| 비용 | 기본 길은 무료. ScrapeCreators(1만 회 무료 뒤 종량제)·Bright Data·Perplexity·Deepline은 키를 넣으면 돈이 나간다. ScrapeCreators 키가 있으면 Reddit 결과가 5건 미만일 때 자동 보충으로 크레딧을 쓴다(SKILL.md 231행). 우리 Claude API 크레딧으로는 못 낸다. |
| 외부 코드 유입 | 첫 설정이 `npx -y @mvanhorn/printing-press-library@0.1.27`로 CLI 4개, macOS면 yt-dlp를 설치한다. 첫 실행 때 Rust 바이너리를 GitHub Releases에서 받고 스킬 판이 오르면 자동 교체한다(해시 대조는 함, CONFIGURATION.md 861행). 키움 MCP·계좌 파일이 있는 회사PC에 검증 안 된 코드가 늘어난다. |
| 자동 갱신 | 권장 설치(마켓플레이스)는 새 판이 나오면 자동 갱신된다. 11/15 하루에 5판이 나올 만큼 자주 바뀐다(CHANGELOG). 우리 예약은 "해시를 적고 실행마다 대조"(지침 4절 ⑧)라서 맞지 않는다. |
| 주입 위험 | 스킬 권한이 Bash·읽기·쓰기이고 남이 쓴 SNS 글을 에이전트 문맥에 넣는다. 키움 도구가 보이는 스레드에서 돌리면 안 된다. |
| robots·접근 규칙 | 우리 정기 수집은 robots 허용 경로만 쓴다(saveticker 선례). 이 도구는 Reddit `.json`이 막히자 브라우저 User-Agent를 흉내 내 다른 주소로 읽고(http.py 2232·2258행), 채용 페이지는 robots가 막아도 읽는 곳이 있다(지금은 Google 1곳, `LAST30DAYS_JOBS_RESPECT_ROBOTS=1`로 끌 수 있음). |
| 닫힌 결정 | X 길(X API·쿠키·xAI·Xquik·xurl)은 모두 11/07 결정이나 비밀 규칙과 부딪힌다. 예외는 `--x-posts`(우리가 Chrome으로 모은 X 글을 넘겨 채점만 시킴)인데 설치가 전제라 기록만 한다. Agent-Reach(X·Reddit 소셜 수집) 10/25 기각과 같은 줄이다. 심리 단서는 등급표 전 매수·매도 근거 인용 금지(psych-1123). |
| 승인 절차 | 플러그인·외부 코드 설치는 개발 큐·사장 승인 경로, 정기 수집은 예약 변경 승인(4절 ①~⑥)과 연결표가 필요. |

## 6. 연결표 (지침 8절 — '들인다면' 기준)
| 칸 | 내용 | 상태 |
|---|---|---|
| 자료 | last30days 요약(Reddit·StockTwits = 가설 등급, 채용·특허 = 1차 자료 + AI 해석은 가설) | 끊김(설치 안 함) |
| 읽는 점검 | 없음. 후보는 외부 주장 원장(external-claims-ledger.md) 기록, 관심 카드 재검토의 가설 칸 | 끊김 |
| 바뀌는 행동 | 없음. 가설 자료는 매수·매도·노출을 바꿀 수 없다. 바꾸려면 §20 사전 등록 시험 → 사장 승인 | 끊김('의도적 없음'은 사장 결정이 있어야 함) |
| 끊김 알림 | 도구에는 실패 신호가 있다(`LAST30DAYS_STRICT_EXIT`면 종료코드 3, source_status, `doctor --postmortem`). 그 신호를 받아 사장에게 알리는 우리 쪽 점검이 없다 | 끊김 |

끊김을 메울 승인 경로(쓰기로 할 때만): ① 외부 코드 1회 격리 시험 = 사장 카드 → 개발 큐(Builder·Judge) ② 정기 수집 = 외부 정보 수집 새 판 제안 + `예약 작업 변경 승인` ③ 매매 반영 = 등급표 사전 등록 → 독립 검수 → 사장 카드. 지금은 셋 다 권하지 않는다.

## 7. 기록해 둘 아이디어 2개 (도구 없이, 지금은 착수 안 함)
1. **채용·특허 = 카드 재검토 때 가설 한 줄.** 보유·관심 종목 카드 재검토 때 그 회사 공식 채용 페이지·USPTO 공개 검색에 새 분야가 보이면 외부 주장 원장에 가설로 한 줄 적는다(robots 허용일 때만). 특허는 18개월 늦으니 '실적 전 신호'로 기대하지 않는다.
2. **참여도 함께 적기.** 외부 정보 수집의 X 글에 좋아요·재게시 수를 함께 적어 두면 나중에 '많이 퍼진 주장'만 골라 볼 수 있다. 바꾸려면 수집 새 판 제안 + 예약 변경 승인.
- 두 아이디어 모두 지금은 읽는 점검·바뀌는 행동·끊김 알림이 끊김이다. 착수 제안 때 칸마다 채우고, '표시 전용'은 사장이 정해야 '의도적 없음'이 된다.
- 참고 출처: DripStack(금융 뉴스레터 검색, 키 없음)은 유일하게 새로운 금융 출처다. 약관·robots 확인 필요, 가설 등급.

## 8. 결론을 바꿀 조건 (1줄)
지금 수집이 못 잡는 신호(예: 보유 종목 관련 Reddit·DripStack 글)가 실제 판단을 바꾼 사례가 생기고, 판 고정·`LAST30DAYS_ENGINE=python`·쿠키 끔·외부 LLM 키 없음·자동 갱신 끔으로 격리 실행할 수 있으면 B안부터 다시 본다.

## 9. 확인 필요
- 코드 전체의 실제 네트워크·파일 접근
- Reddit·StockTwits·DripStack 이용 약관 원문
- 회사PC OS(Windows면 Chrome 쿠키 안 읽힘)
- 별 수·관리자 반응 속도

재검토 기록: 조언(Fable) 1건 — 결론 바뀜 0 · 정정 8+사소 5 반영 · 미반영 0 (작업자 약 178k 토큰, 약 3분 15초)
