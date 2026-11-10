# forecast-model-1110 폴더 안내

- 무엇: 미래 주가 예측 모형(FM-1·FM-2)과 재귀적 자기개선 고리의 문서·코드·기록이다. 표시·채점 전용이다. 주문·정책·상태·자동 코어 입력·한도·권한 변경 0.
- 주인: 사장실 스레드 '미래 주가 예측 모델 만들기'. 이 안내문 고침: 2026-11-10 23:52 KST.
- 원본: 사장실 프로젝트 파일 /mnt/project-files/forecast-model-1110/. 계산은 클라우드에서만 한다.
- 사본: 회사PC 코덱스저장소 docs/claude/forecast-model-1110/. 기록용이다. 문서 커밋(매일 23:30 KST)의 git 시각이 '규칙을 먼저 고정하고 자료를 나중에 봤다'는 기록이 된다. 사본에서 계산을 돌리지 않는다. 원본을 고치면 같은 날 사본도 다시 올린다.

## 먼저 읽을 것

1. forecast-model-design-2026-11-10.md — 분석, 시험 결과, 자기개선 설계, 사장 결정 기록(8-2절), 도입 순서(8-3절).
2. forecast-forward-rule-2026-11-10.md — 전진 채점 규칙(고정).
3. forecast-ledger.README.md — 예측 원장 읽는 법과 주간 실행 순서. 돌리기 전에 '지킬 것 네 가지'를 읽는다.
4. forecast-layer3-rule-2026-11-10.md — 3층 장치(새 전문가 후보의 등록과 그림자 검증) 규칙(고정). 실행 순서는 layer3/README.md.

## 사장 결정

- 2026-11-10 11:51:50 KST '이 모형만 4단계까지 자동'. 원문은 설계서 8-2절, 색인은 docs/claude/active-decisions.md의 forecast-fm2-1110 행이다.
- 이 결정에 들지 않는 것: 주문·노출·정책·권한 변경, 회사 전략 점검 연결, 새 예약 작업(작업마다 따로 승인), 사람 없는 자동 편입.

## 고정 파일 (고치지 않는다 — 새 판은 새 파일과 새 해시 기록으로)

| 해시 목록 | 고정한 때(KST) | 담은 것 | 목록 파일의 sha256 |
|---|---|---|---|
| fm1-prereg.sha256 | 2026-11-10 08:54 | FM-1 사전 등록, fm1.py, 입력 5개 | f2c6724d6bfca9c89ba71dd409e4971fcea799e9d08419cd39cc93ca42512cbf |
| fm2-prereg.sha256 | 2026-11-10 10:04 | FM-2 사전 등록, fm2.py, fm1.py, boot_calib.py, 가짜 자료 점검 결과, 입력 25개 | 028bd179b7f2fbe00f5e3df6bc626e41099b52b0737632f96d744fef4cd4040e |
| forward-rule.sha256 | 2026-11-10 11:23 | 전진 채점 규칙, fm2_weekly.py, fetch_weekly.py, fm2.py, fm1.py | 99d392514e8df637e11f9053a7dc51916c52dfb06ee3510016ecd80129832bb8 |
| layer3.sha256 | 2026-11-10 22:23 | 3층 장치 규칙, fm3_shadow.py, fm3_weekly.py, fm3_itest.py, fetch_extra.py, fetch_options.py, 메뉴 1판(MENU.json · vixr.py), fm2_weekly.py, fm2.py, fm1.py | bd8d5a3f2be744238a09fdd261e63e2a33f7759d34015bd22d25c8fd8d5daeab |

- 문서 커밋 확인(2026-11-10 23:51 KST): 6a7d1ec(2026-11-10 23:30:11 KST — 결정 기록과 앞의 닻 3개) · 66bbc34(2026-11-10 23:30:16 KST — 3층 장치와 layer3.sha256). 커밋 안에서도 닻 4개의 sha256이 위 표와 같다. 전체 번호는 설계서 8-2절에 있다.
- results.sha256은 결과·통계 파일의 해시 모음이다. 결과가 늘면 다시 쓰므로 고정 닻이 아니다.
- 해시는 LF 줄바꿈 바이트 기준이다. 사본을 대조할 때는 `git show <커밋>:<경로> | sha256sum`으로 본다. Windows에서 줄바꿈이 바뀐 작업 파일로 재면 다르게 나올 수 있다.
- 3층의 메뉴(layer3/menu/)는 항목이 늘 수 있다. layer3.sha256에 적힌 것은 1판의 값이다. 그 뒤의 메뉴 상태는 등록할 때마다 layer3/LOG.jsonl의 registered 사건(menu_sha256)에 남는다.
- 3층 장부(layer3/의 LOG.jsonl · REGISTRY.json · REJECTED.md · challengers/ · runs/ · checks/)는 매주 늘어나는 기록이라 고정 파일이 아니다. 손으로 고치지 않는다(layer3/README.md).

## 재검토 기록

| 곳 | 무엇 |
|---|---|
| review2/ | 2차 독립 재검토(FM-2 코드·결과)의 근거와 내 재확인 기록 |
| review3/REPORT.md | 3차 독립 재검토 전문 — 3층 장치(A)와 전진 규칙·주간 스크립트(B) |
| review3/RESPONSE.md | 발견마다 무엇을 어떻게 고쳤는지. 고친 곳만 다시 본 검토의 발견은 끝의 절에 있다 |
| review3/REVIEW2.md | 고친 곳만 다시 본 검토(2차)의 전문 |
| review3/REVIEW3.md | 2차 검토의 발견을 고친 코드만 좁게 다시 본 확인의 전문 |
| review3/의 로그와 스크립트 | 규칙 12절 숫자의 근거(t05 · t06 · sim_fut), 나쁜 도전자 시험(bad_summary2, 최종 코드는 bad_summary3), 전 과정 시험(itest), 과거 자료 배관 점검(plumbing), vixr 기술 심사 결과(admit_vixr) |
| review3/reviewed_v1/ · reviewed_v2/ · reviewed_v3/ | 재검토자가 읽은 옛 판(1 = 첫 검토, 2 = 고친 곳만 다시 본 검토, 3 = 좁은 확인이 읽은 fm3_weekly.py). 보관용이고 쓰지 않는다 |
| review3/reviewer/ · reviewer2/ · reviewer3/ | 재검토자의 작업 파일 가운데 스크립트·로그·나쁜 도전자(첫 검토 · 2차 · 좁은 확인) |
| review3/r3check/ | 2차 검토의 발견을 고친 뒤 내가 돌린 확인 시험의 스크립트·로그(logs/), 좁은 확인 뒤 최종 코드로 다시 돌린 기록(logs_final/), 검토자에게 준 변경 내역(r3_*.diff)과 그 뒤의 변경(r4_weekly.diff) |

## 사본에 없는 것과 이름이 다른 것

- scripts/inputs/ — 입력 자료(약 33MB). 원본 폴더에만 있다. 파일마다의 sha256은 위 해시 목록과 results.sha256에 있다. 옵션 시세 스냅샷은 목록(scripts/inputs/options/MANIFEST.jsonl)만 사본에 있다.
- review2/reviewer/ — 2차 독립 재검토자의 작업 파일 34개. 원본 폴더에만 있다.
- review3/의 reviewed_v1/ · reviewed_v2/ · reviewed_v3/ · reviewer/ · reviewer2/ · reviewer3/ · r3check/ — 원본 폴더에만 있다.
- 로그: 저장소가 `*.log`를 git에서 빼므로 사본의 로그는 `.log.txt`다. review2/verify2.log는 사본에서 review2/verify2.log.txt다(내용과 sha256은 같다). review3/ 바로 아래와 r3check/ · reviewer2/ · reviewer3/의 로그는 원본에서도 `.log.txt`다(reviewer/ 안은 검토자가 쓴 이름 그대로다).
- 캐시 폴더, `__pycache__`.

## 실행할 때 (클라우드에서만)

- `python3 -I -B`로 돌린다. `-B`가 없으면 해시 고정 폴더에 `__pycache__`가 써진다.
- 주간 실행 순서는 forecast-ledger.README.md '만드는 법'과 layer3/README.md에 있다. asof는 받은 자료의 MANIFEST.json에 있는 safe_asof만 쓴다.
- 자료는 13:00~22:00 KST에만 받는다(미국 장이 열려 있는 동안 받지 않는다).
