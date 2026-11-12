# layer3 폴더 안내 — FM-2 3층 장치 (도전자 장부)

- 무엇: 새 전문가 후보(도전자)의 장부와 그림자 채점 결과다. 표시·채점 전용이다. 주문·정책·상태·자동 코어 입력·한도·권한 변경 0.
- 규칙: ../forecast-layer3-rule-2026-11-10.md (고정 기록 ../layer3.sha256).
- 주인: 사장실 스레드 '미래 주가 예측 모델 만들기'. 갱신 주기: 주 1회(주간 실행에 붙여서). 이 안내문 고침: 2026-11-10 22:25 KST, 2026-11-12 15:10 KST(이름 없는 오류 관찰 한 줄, 옵션 받는 시각).
- 편입은 여기서 정하지 않는다. 통과한 구간(주간 결과의 awaiting_judge)은 독립 Judge와 사장 카드를 기다린다.
- 장부(REGISTRY.json · LOG.jsonl · REJECTED.md)와 challengers/ 안의 파일은 손으로 고치지 않는다. 모든 명령이 장부를 LOG.jsonl과 대조하고, 다르면 멈춘다.
- 이 폴더는 네트워크 폴더다. 명령이 드물게 시작하자마자 파일 이름 없는 `FileNotFoundError`로 죽는다(2026-11-10 22:24 KST에 `next`에서 한 번 봤다. 현재 폴더가 잠깐 안 보인 것으로 추정 — 확인 필요). 장부를 쓰기 전이라 바뀐 것은 없다. 10초쯤 뒤 `verify`를 돌리고 같은 명령을 다시 돌린다. 2026-11-12 15:08 KST에는 한 셸 호출 안에서 `verify` 바로 뒤에 이어 붙인 `next`가 두 번 잇달아 이렇게 죽었고, `next`만 따로 새 셸 호출로 돌리니 됐다. 명령은 하나씩 따로 돌린다.
- 한 번에 한 명령만 돌린다. 잠금 장치가 없다. 명령 둘이 겹치면 늦게 쓰려던 쪽이 'books stopped'로 멈추고 장부에는 아무것도 쓰지 않는다(화면 문구에 'had already saved'가 있을 때만 예외 — 아래 rebuild 줄).

## 파일

| 파일 | 무엇 | 누가 쓰나 |
|---|---|---|
| LOG.jsonl | 사건 기록. 덧붙이기만 한다. 장부의 원본이다 | scripts/fm3_weekly.py |
| REGISTRY.json | 발견, 도전자, 상태. LOG.jsonl을 차례로 접은 결과다 | scripts/fm3_weekly.py |
| REJECTED.md | 탈락 기록(이 모형 전용) | scripts/fm3_weekly.py |
| challengers/ | 등록한 계산 파일 사본, 사전 등록문, 심사 결과. 등록 뒤 고치지 않는다 | scripts/fm3_weekly.py register |
| challengers/<id>.issued/ | 그 도전자가 낸 예측. 실행마다 파일 하나. 고치지 않는다 | scripts/fm3_weekly.py run |
| menu/ | MENU.json과 계산 파일. 독립 Judge가 읽고 통과시킨 것만 넣는다 | 이 스레드 또는 주간 실행 세션 |
| runs/ | 주간 그림자 결과 shadow_<asof>.json | scripts/fm3_weekly.py run |
| checks/ | 판정 구간 점검 기록 | scripts/fm3_weekly.py interval-check |

## 주간 실행 순서 (계산은 클라우드에서만)

받는 시각: 13:00~22:00 KST에만 받는다. 미국 장이 열려 있는 동안 받으면 끝나지 않은 하루가 종가처럼 들어올 수 있다.

1. forecast-ledger.README.md '만드는 법' 1~2번(자료 받기와 fm2_weekly.py)을 먼저 한다. 아래에서 W는 그때 받은 폴더, asof는 MANIFEST.json의 safe_asof다. 지난 실행보다 이른 asof로는 돌리지 않는다.
2. `python3 -I -B scripts/fetch_extra.py W _VIX _GSPC` — 도전자가 쓰는 추가 자료를 W/extra/에 받는다. 받을 이름은 REGISTRY.json에서 그림자 중인 도전자의 extras 값과, 등록하려는 메뉴 항목의 EXTRAS 값이다.
3. `python3 -I -B scripts/fm3_weekly.py run layer3 W/pool W/idx W/extra <asof> <fm2 캐시 폴더> <도전자 캐시 폴더> layer3/runs/shadow_<asof>.json --jobs 4`
   - fm2 캐시 폴더는 2번 단계의 fm2_weekly.py에 준 것과 같은 폴더다. 같은 입력, 같은 asof로 만든 캐시가 아니면 실행이 멈춘다.
   - 결과 읽기: skipped(건너뛴 도전자와 까닭) · report(사장실에 1줄로 알릴 것) · held(자동 처분이 허용되지 않아 보류된 판정 — 사람이 정한다) · awaiting_judge(통과한 구간 — 규칙 6절로 간다) · events(이번에 바뀐 것) · next_menu(다음에 등록할 메뉴 항목).
   - report에 `PERSON DECISION NEEDED`가 있으면 보류된 판정이 있다는 뜻이다. 사장실에 알리고 사람이 정한다(규칙 5절). `DECISION CARD NEEDED`는 판정 구간 점검이 실패로 기록돼 있다는 뜻이다. 사장 카드로 올린다. `was ended`는 시작일 대조 불일치로 도전자를 끝냈다는 뜻이다.
   - history 종류 도전자의 몫과 학습 상태는 결과에 없다(`not shown`). 과거 성적과 같은 정보이기 때문이다. 계산 폴더의 과거 예측값을 손으로 채점하지 않는다.
   - 결과 파일은 장부를 쓴 뒤에 생긴다. 명령이 `books stopped`로 멈추면 화면 문구를 끝까지 읽는다. 'wrote nothing'이면 장부에는 아무것도 쓰이지 않았다 — 다른 명령이 함께 돌았는지 보고, `verify`가 통과하면 같은 명령을 다시 돌린다. 'had already saved'면 REGISTRY.json만 저장된 채 멈춘 것이다 — `rebuild`를 돌리고(남은 줄을 화면에 적고 뺀다) 같은 명령을 다시 돌린다. 멈춘 실행이 쓴 예측 파일은 같은 asof를 다시 돌리면 덮어쓴다.
   - skipped가 있으면 까닭을 적고 다음 실행에서 다시 본다. 시작일에서 10일이 지나면 그 주의 예측은 '예측 없음'으로 남는다.
4. 결과의 next_menu에 이름이 있으면 `python3 -I -B scripts/fm3_weekly.py register layer3 <이름> W/pool W/idx W/extra <asof> <fm2 캐시 폴더> --jobs 4`
   - KST 23시 전에만 한다. 심사가 23시를 넘겨 끝나도 등록되지 않는다. 등록 심사(약 1분)를 통과하면 등록되고, 다음 날 시작하는 예측부터 판정에 쓴다.
   - 등록 전에는 그 계산 파일을 실제 결과와 대조해 채점하지 않는다.
5. `python3 -I -B scripts/fetch_options.py scripts/inputs/options` — 옵션 시세 스냅샷(아직 읽는 도전자 없음, 모으기만 한다).
   - 13:00~14:00 KST(미국 동부 겨울 시간으로 자정 전)에 받는다. 2026-11-12 15:03 KST(미국 01:03, 장 상태 PREPRE)에 받은 2026-11-11 스냅샷은 호가와 미결제약정이 거의 비어 있다(콜 호가가 있는 행 97/5,487, 미결제약정이 있는 행 106, 내재 변동성이 있는 행 2,623. 마지막 체결가는 5,275행에 있다). 2026-11-10 12:52 KST(미국 22:52, POSTPOST)에 받은 2026-11-09 스냅샷은 6,111행 가운데 5,449행에 콜 호가가 있다. 야후가 밤사이 호가를 비우는 것으로 보인다. 비우는 시각은 확인 필요다(관찰 2회). 서머타임 때는 한 시간 이르다. 2026-11-11 스냅샷은 그대로 둔다(지난 날짜는 다시 받을 수 없다). 그 파일을 읽는 도전자는 호가가 빈 행을 걸러야 한다.
6. 받은 폴더 W를 scripts/inputs/weekly/<asof>/에 남긴다(extra/ 포함). 판정 때 Judge가 이 입력으로 다시 계산한다.
7. 회사PC 사본: layer3/ 폴더 전체(challengers/<id>.issued/ 포함)와 scripts/inputs/options/MANIFEST.jsonl, W의 MANIFEST.json·MANIFEST_EXTRA.json을 docs/claude/forecast-model-1110/에 올리고 docs/claude/_pending/ 목록에 적는다. 올린 뒤 크기와 sha256을 다시 읽어 대조한다. 저장소가 `*.log`를 git에서 빼므로 로그는 `.log.txt`로 올린다.

## 처음 한 번

- `python3 -I -B scripts/fm3_weekly.py init layer3` — 장부(발견 4개, 도전자 0개)를 만든다. 규칙과 코드를 해시로 고정한 뒤에 한다. 장부가 이미 있으면 거부한다.

## 그 밖의 명령

| 명령 | 언제 |
|---|---|
| `fm3_weekly.py verify layer3` | 장부가 LOG.jsonl과 같은지만 본다 |
| `fm3_weekly.py next layer3` | 다음에 등록할 메뉴 항목을 본다 |
| `fm3_weekly.py rebuild layer3` | 명령이 '장부가 LOG.jsonl과 다르다'(books refused)며 멈췄을 때, `verify`가 `books stopped`로 멈출 때, 또는 화면 문구가 rebuild를 돌리라고 할 때. 끝내지 못한 명령이 남긴 줄이 LOG.jsonl 끝에 이어지면 먼저 마저 쓰고, 이어지지 않으면 버리고 화면에 적는다(버린 줄은 사장실 스레드에 적는다). 그다음 LOG.jsonl에서 REGISTRY.json을 다시 쓴다. LOG.jsonl 자체가 상했으면 회사PC 사본(git 기록)에서 되살린다 |
| `fm3_weekly.py interval-check layer3 <점검 결과.json>` | 판정 구간 점검(규칙 5절)을 마친 뒤 한 번. 보고서에는 판정 구간과 길이가 모두 있어야 한다: `{"coverage": {"20": {"65": x, "104": y}, "60": {"208": z}}}`. 값은 0~1의 숫자다(true/false는 받지 않는다). 실패를 기록한 뒤 통과를 다시 기록해도 자동 처분은 돌아오지 않는다(사람이 정한다). 설계는 돌리기 전에 고정하고 독립 Judge가 본다 |
| `fm3_weekly.py close layer3 <도전자> "<누가, 언제, 왜>"` | 사장이 '편입 안 함' 또는 '그만 잰다'로 정했을 때, 보류된 판정(held)을 받아들여 끝내기로 정했을 때만. 사장 결정 없이 쓰지 않는다. 도전자 단위로 닫는다 |
| `fm3_itest.py [작업 폴더]` | 가짜 세계에서 전 과정 시험(약 1분). 코드를 옮긴 뒤 한 번 |

## 하지 않는 것

- 회사PC에서 계산을 돌리지 않는다.
- 편입을 적는 명령은 없다. 수락된 후보는 표시를 바꾸는 코드가 생길 때까지 awaiting_judge에 남는다(규칙 6절).
- 보류된 판정을 풀고 계속 재는 명령도 없다. 필요하면 새 판(새 파일 + 독립 재검토)으로 만든다.
- 지난 줄·지난 파일을 고치지 않는다. 틀린 것이 보이면 고치지 말고 사장실 스레드에 적는다.
