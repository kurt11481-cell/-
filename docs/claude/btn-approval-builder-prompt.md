# Builder 지시문: btn-approval — CLAUDE.md 버튼 승인 문구 (수동 경로, K3)

선행 조건(하나라도 없으면 시작하지 않는다. 원본은 워크트리 사본이 아니라 본 저장소 E:\사업\##금동한\코덱스저장소\docs\claude\btn-approval-proposal-2026-10-27.md 의 "결정 기록" 절이다. 워크트리 사본은 옛 커밋이라 그 절이 없을 수 있다): ① 사장이 사장실 스레드에 직접 친 `btn-approval 착수 승인`(같은 날 KST) ② T0 기록(카드 id·선택지·누른 계정 id·시각)이 docs/claude/btn-approval-proposal-2026-10-27.md 결정 기록 절에 있음.
모델: Opus. 작업 위치: 새 워크트리 `btn-approval`(claude --worktree btn-approval). 기준 커밋: 시작 시 HEAD를 보고서에 적는다.
읽을 것: E:\사업\##금동한\코덱스저장소\docs\claude\btn-approval-proposal-2026-10-27.md (2절 원문, 3절 바꿀 문장, 5절 하지 않음).

해야 할 일
1. CLAUDE.md 64~66행(현재 3줄, sha256 9bc62078fba7f199619e1fa61d9669257ef6cae5fccc6f86f2a7e7aa62e43ee9)을 제안서 3절의 7줄로 바꾼다. 시작 전에 이 해시가 맞는지 확인하고, 다르면 멈추고 보고한다.
2. CRLF 유지(바이트 단위 치환, `\n` 개수 = `\r\n` 개수 확인). 일괄 변환 금지.
3. 해시는 원본 CRLF 바이트로 계산한다(Git Bash의 sed|sha256sum은 CR을 떼어 다른 값이 나온다). 예: python -c "import hashlib;L=open('CLAUDE.md','rb').read().split(b'\n');print(hashlib.sha256(b'\n'.join(L[17:45])+b'\n').hexdigest())" (Hard safety 18~45행은 L[17:45], 64~66행은 L[63:66]).
   그 밖의 줄은 한 글자도 바꾸지 않는다. Hard safety 절(18~45행, `sed -n '18,45p' CLAUDE.md | sha256sum` = 8ee8d497aa60590bc7bbbc73380456b1303581afe0216cffffa2732b7ca1f663)이 변경 전후 같은지 계산해 적는다.
4. 권한(주문·한도·예산·주문 단계·승인 상품·대사 불변식·킬 스위치) 확대 표현을 넣지 않는다. 승인 인정 범위는 제안서의 조건(같은 스레드 카드, 하네스 알림 기록 4가지, 사장 계정 id, 바로 앞 제안 1건·같은 날·1회)만.
5. git diff -U0와 바뀐 줄 번호, 변경 전후 CLAUDE.md sha256, "Hard safety 절 변경 없음" 확인을 docs/claude/btn-approval-builder-report.md에 적는다.
6. 커밋·푸시·병합하지 않는다. 테스트 대상 없음(문서만).

끝나면 사장에게 한국어로 3줄: 바뀐 줄 번호, Hard safety 해시 동일 여부, Judge 세션 시작 방법(docs/claude/btn-approval-judge-prompt.md).
