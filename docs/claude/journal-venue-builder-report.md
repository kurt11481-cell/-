# journal-venue Builder 보고서 (수동 경로, K3) — 2026-10-27 15:35 KST

- 지시문: docs/claude/journal-venue-builder-prompt.md · 선행 조건: 제안서 8절 착수 승인(카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9CJui6QdNHHdMyncKi3Pvon, 15:27:32 KST) + T0 verify OK 확인함.
- 모델: Opus. 워크트리: `.claude/worktrees/journal-venue`, 브랜치 `worktree-journal-venue`, 시작 HEAD **3542b10**.
- 커밋·푸시·병합 안 함. .claude/settings*.json, decision_journal.json, 정책·상태 파일 손대지 않음. apply는 임시 파일 테스트에서만.
- 보고서 위치: 본 저장소 docs/claude/에 쓰려 했으나 Claude Code 훅이 "기본 체크아웃 쓰기"를 막아, 이 워크트리의 docs/claude/journal-venue-builder-report.md 에 둔다.

## 상태: 부분 완료 — 6번(CLAUDE.md) 막힘

CLAUDE.md 바이트 치환을 실행하려 했으나 Claude Code 자동 모드 분류기가 **"Self-Modification"** 으로 거부했다. 우회하지 않고 멈췄다.
CLAUDE.md는 워크트리에서 **바뀌지 않았다**(sha256 그대로). 코드·스키마·테스트(2~5번)는 끝났다.
6번을 하려면 사장이 결정해야 한다: ① 사장이 이 권한을 허용하고 Builder가 CLAUDE.md만 다시 하거나, ② 사장이 아래 "6번 예정 문안"을 직접 넣는다.
CLAUDE.md 문장 없이 병합하면 Hard safety 34행("Claude Code … never apply")과 코드가 어긋나므로, **6번 전 병합 금지**를 권한다.

## 1. 시작 해시 (원본 CRLF 바이트, 각 행은 끝 \r\n 포함)
| 구간 | 기대(지시문) | 실측 | 결과 |
|---|---|---|---|
| CLAUDE.md 전체 | 460ac219b052…40df | 460ac219b052b98817f0848a01c202860868a963a7c0c93baad6efc70f8340df | 일치 |
| 18~45행 | 8ee8d497aa60…f663 | 8ee8d497aa60590bc7bbbc73380456b1303581afe0216cffffa2732b7ca1f663 | 일치 |
| 29~34행 | f0938237d2b3…81ee | f0938237d2b3902c7ff110f1d69b7147d6877692686482c3ce0baaa6168681ee | 일치 |
| 108행 | c5953526e61b…7c84 | c5953526e61b02b0ebf2a68a5d03b1a621e5e224bc45e18780e31cae6e307c84 | 일치 |

변경 후: CLAUDE.md는 바뀌지 않아 위 값 그대로(전체 460ac219…40df, 18~45행 8ee8d497…f663).

## 2. 바뀐 파일 (git diff --numstat, 모두 CRLF 유지·\n 수 = \r\n 수, 스크립트 ASCII 유지)
| 파일 | +/- | 내용 |
|---|---|---|
| manage-us-stock-strategy/scripts/portfolio_review_journal.py | +25 −4 | docstring 20~22행 새 경로 1항목; 71~74행 `PROJECT_THREAD_METHOD`·CONFIRMATION_METHODS 추가; 187~190행 체인 검사에서 이 방법만 코드 검사 대신 4칸 검사; 238~243행 `project_thread_message_valid`; 553~556행 apply 같은 분기; 889~890행 CLI가 이 방법에도 --user-message 필수 |
| manage-us-stock-strategy/schemas/portfolio-review-journal.schema.json | +2 −2 | 4행 description 1문장, 29행 enum에 `PROJECT_THREAD_USER_DECISION` (필드 추가 없음) |
| manage-us-stock-strategy/tests/test_portfolio_review_journal.py | +87 | `ProjectThreadDecisionTests` 6개 |

sha256(변경 후): journal.py 6ea53b80387a339e914cceeafbf5d5047eb7ee237ec0588afed0ca529687985e · schema 4ea21febc9b7cb2d0cd8d0a256a43405b90291de5c3e72568bbe1e5e5fc0a6f9 · test c6374fb8fe3e4c189fa108b7ca4d6eb6a9d3ebe765e55d150c895c5f3dbc8647

바꾸지 않은 것: USER_TERMINAL 콘솔 검사, COWORK 코드-포함 검사, AUTO_CORE 검사(`_auto_core_inconsistency`, AUTO_CORE는 여전히 CONFIRMATION_METHODS 밖), confirm_code 일치·entry_id 접두 검사, 제안 1시간 만료, order_authority false / quantity_authority none.
4칸 검사: `message.split("|", 3)` 결과 4칸, 각 칸 strip 뒤 비어 있지 않음(원문 칸 안의 `|`는 허용). 계정 id 형식·시각 형식은 검사하지 않는다(지시문 범위: "4칸, 빈 칸 없음"). → Judge 확인 항목.

## 3. 테스트 (대상 파일만, 전체 스위트 안 돌림)
- test_portfolio_review_journal.py: **20개 OK** (기존 14 + 새 6: 코드 없는 메시지 통과·verify OK, 4칸 누락/빈 칸/빈 메시지/None 거부, 틀린 코드 거부, COWORK·USER_TERMINAL은 코드 없는 메시지 계속 거부·AUTO_CORE 거부, 손편집 시 CORRUPT, CLI apply→verify)
- 바뀐 코드를 쓰는 파일: test_decision_journal_cards.py 36 OK, test_approval_human_check.py 28 OK
- test_auto_core_decide.py 69개 중 **1 실패**: `RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches`(PLTR: CARD_SECTION_CHANGED, CARD_NOT_ACCEPTED_IN_WATCHLIST). 변경 없는 HEAD 3542b10 사본(git archive)에서도 똑같이 실패 → **기존 실패, 이번 변경과 무관**(실제 카드 레지스트리 데이터).
- 중간에 ScriptHygieneTests(스크립트 ASCII 전용)가 한국어 주석 때문에 실패 → 주석을 ASCII("CEO-office company-PC project thread")로 바꿔 통과.
- validate_schema_contracts.py: PASS.

## 4. confirmation_method 읽는 곳 (git grep, *.py *.json *.ps1)
- score_decision_journal.py: confirmation_method를 읽지 않음(grep 0건) → 새 값이 빠지거나 거부되지 않음. 수정 없음.
- auto_core.py:227: 대사 원장(reconciliation ledger)의 `AUTO_CORE_INVARIANTS` 거르기. 결정 일지 아님 → 무관.
- apply_user_confirmed_broker_snapshot.py:30·277, reconcile_broker_state.py:296: 대사 쪽 자체 CONFIRMATION_METHODS. **바꾸지 않음**(대조 `확인 <코드>` 불변).
- 테스트: test_auto_core.py:1056·1059는 대사 모듈 값만 고정(영향 없음), test_auto_core_decide.py:1253은 AUTO_CORE가 일지 방법 밖인지 확인(여전히 통과).
- 그 밖에 일지 항목을 확인 방법으로 거르는 코드 없음.

## 5. 6번 예정 문안 (적용 안 됨 — 사장 결정 대기)
34행 다음에 5행 삽입(34행 원문은 그대로):
```
  Exception, 사장실 회사PC 스레드 (interactive Claude Code project thread; journal-venue 2026-10-27): the user's own decision
  message typed in that thread, or the user's own tap on a decision card that thread posted (the four record items in
  Change classes), is the confirmation; the same session runs propose -> apply -> verify with that proposal's own code,
  `--confirmed-via PROJECT_THREAD_USER_DECISION` and user_message `<message or card id> | <account id> | <KST time> |
  <verbatim text or card option>`. One decision covers only the immediately preceding proposal, the same day, once.
```
108행(삽입 뒤 113행): `is accepted in Cowork, record` → `is accepted in Cowork or in the 사장실 회사PC 스레드, record`.
대조 apply·정책/상태·decision_mode·.claude 문장은 그대로. 치환 스크립트: 실행 안 됨(분류기 거부).

## 5-1. 6번 적용 (2026-10-27 16:0x KST, 사장실 회사PC 스레드가 파일 도구로 워크트리 사본에만)
- 근거: 사장 카드 탭 15:38 KST "허용 — Builder가 다시"(cmsg_0137MRzn9nuDvvQmVxm6WeX97aLysY2fsHBv3pcgsti6pC), 15:58 KST 직접 입력 "자동으로 유지한다.", 16:00 KST 카드 탭 "이 스레드가 워크트리에"(cmsg_0137MRzn9nuDvvQmVxm6WeX9AHftwUHPE6zSrLp7ZJkBRe), 모두 계정 user_01KuMGKfZu1SBYxtMmg4vAiH. 자동 모드 분류기가 막은 편집을 다른 도구로 한 것임을 사장이 알고 고름.
- 문안: 위 5절 그대로(34행 뒤 5행 삽입, 108행→113행 "or in the 사장실 회사PC 스레드").
- 확인: \n 135 = \r\n 135(CRLF 유지), UTF-8 디코드 OK. 본 저장소 CLAUDE.md와 비교해 1~34행·(본 35~45 = 새 40~50)·나머지 행 모두 동일, 바뀐 곳은 삽입 5행과 113행뿐. 본 저장소 CLAUDE.md는 그대로(460ac219…40df).
- 변경 후 sha256: CLAUDE.md 전체 fdc14b56f4f2a76c7bdfa6916ced865477e9797dd269ed0cf1a6e46894735a96 · Hard safety 새 구간 18~50행 c958bbc9e42b8781d03f2e6702bdddf54864264ab0074f9bd725afa9bbcf80ea.
- 테스트는 다시 돌리지 않음(CLAUDE.md는 테스트 입력 아님, 3절 결과 유지). Judge가 필요하면 실행.

## 6. git diff -U0 (코드·스키마·테스트)
```diff
diff --git a/manage-us-stock-strategy/schemas/portfolio-review-journal.schema.json b/manage-us-stock-strategy/schemas/portfolio-review-journal.schema.json
index b0720ee..944ae63 100644
--- a/manage-us-stock-strategy/schemas/portfolio-review-journal.schema.json
+++ b/manage-us-stock-strategy/schemas/portfolio-review-journal.schema.json
@@ -4 +4 @@
-  "description": "Hash-chained entries appended by portfolio_review_journal.py apply after the user's confirmation code. HWM, line breaches and pauses are recomputed and never stored here. Card entries (card_decision, card_user_decision) are records to score later, never orders: for them review_id is the card sha256 and evaluation_session is the decision session. Scores are never stored here. Redesign T2 F7: the auto-core appends core_decision, order_ticket and ticket_outcome entries in recording mode with confirmation_method AUTO_CORE, confirm_code null and user_message null (review_id = the decide record's canonical hash, user_confirmed_at = the write time); portfolio_review_journal.py checks that a null code and message appear only on AUTO_CORE entries.",
+  "description": "Hash-chained entries appended by portfolio_review_journal.py apply after the user's confirmation code. HWM, line breaches and pauses are recomputed and never stored here. Card entries (card_decision, card_user_decision) are records to score later, never orders: for them review_id is the card sha256 and evaluation_session is the decision session. Scores are never stored here. Redesign T2 F7: the auto-core appends core_decision, order_ticket and ticket_outcome entries in recording mode with confirmation_method AUTO_CORE, confirm_code null and user_message null (review_id = the decide record's canonical hash, user_confirmed_at = the write time); portfolio_review_journal.py checks that a null code and message appear only on AUTO_CORE entries. journal-venue: PROJECT_THREAD_USER_DECISION entries are the user's decision in the CEO-office company-PC project thread; their user_message is '<message or card id> | <account id> | <KST time> | <verbatim text>' and need not contain the confirm_code.",
@@ -29 +29 @@
-          "confirmation_method": {"enum": ["COWORK_CHAT_USER_MESSAGE", "USER_TERMINAL", "AUTO_CORE"]},
+          "confirmation_method": {"enum": ["COWORK_CHAT_USER_MESSAGE", "USER_TERMINAL", "PROJECT_THREAD_USER_DECISION", "AUTO_CORE"]},
diff --git a/manage-us-stock-strategy/scripts/portfolio_review_journal.py b/manage-us-stock-strategy/scripts/portfolio_review_journal.py
index 724c9a3..90cc8f4 100644
--- a/manage-us-stock-strategy/scripts/portfolio_review_journal.py
+++ b/manage-us-stock-strategy/scripts/portfolio_review_journal.py
@@ -19,0 +20,3 @@ apply   append the entry. Run apply only in Cowork after the user typed "confirm
+        journal-venue: --confirmed-via PROJECT_THREAD_USER_DECISION is run by the CEO-office company-PC
+        project thread in the session where the user typed the decision or tapped that thread's decision card;
+        user_message is "<message or card id> | <account id> | <KST time> | <verbatim text or card option>" (no code).
@@ -68 +71,4 @@ CARD_ENTRY_TYPES = (JOURNAL_CARD_DECISION, JOURNAL_CARD_USER_DECISION)
-CONFIRMATION_METHODS = ("COWORK_CHAT_USER_MESSAGE", "USER_TERMINAL")
+# journal-venue: the user's decision in the CEO-office company-PC project thread (typed message or that thread's
+# card tap) is the confirmation itself; its user_message holds the four harness fields instead of the code.
+PROJECT_THREAD_METHOD = "PROJECT_THREAD_USER_DECISION"
+CONFIRMATION_METHODS = ("COWORK_CHAT_USER_MESSAGE", "USER_TERMINAL", PROJECT_THREAD_METHOD)
@@ -181 +187,4 @@ def _entry_inconsistency(entry: dict[str, Any], decisions: dict[str, dict[str, A
-    if code not in entry["user_message"].upper():
+    if entry["confirmation_method"] == PROJECT_THREAD_METHOD:
+        if not project_thread_message_valid(entry["user_message"]):
+            return "PROJECT_THREAD_MESSAGE_INVALID"
+    elif code not in entry["user_message"].upper():
@@ -228,0 +238,8 @@ def _entry_inconsistency(entry: dict[str, Any], decisions: dict[str, dict[str, A
+def project_thread_message_valid(message: Any) -> bool:
+    """journal-venue: "<message or card id> | <account id> | <KST time> | <verbatim text>", no empty field."""
+    if not isinstance(message, str):
+        return False
+    fields = message.split("|", 3)
+    return len(fields) == 4 and all(field.strip() for field in fields)
+
+
@@ -536 +553,4 @@ def apply_proposal_entries(*, journal_path: Path, proposal: dict[str, Any], conf
-    if not isinstance(message, str) or proposal["confirm_code"] not in message.upper():
+    if confirmation["confirmation_method"] == PROJECT_THREAD_METHOD:
+        if not project_thread_message_valid(message):
+            raise JournalError("PROJECT_THREAD_MESSAGE_INVALID")
+    elif not isinstance(message, str) or proposal["confirm_code"] not in message.upper():
@@ -869 +889,2 @@ def cmd_apply(args: argparse.Namespace) -> int:
-        if args.confirmed_via == "COWORK_CHAT_USER_MESSAGE" and not (args.user_message or "").strip():
+        if args.confirmed_via in ("COWORK_CHAT_USER_MESSAGE", PROJECT_THREAD_METHOD) and not (
+                args.user_message or "").strip():
diff --git a/manage-us-stock-strategy/tests/test_portfolio_review_journal.py b/manage-us-stock-strategy/tests/test_portfolio_review_journal.py
index 56419dd..56a3d90 100644
--- a/manage-us-stock-strategy/tests/test_portfolio_review_journal.py
+++ b/manage-us-stock-strategy/tests/test_portfolio_review_journal.py
@@ -398,0 +399,87 @@ class LastEntryRecomputeTests(unittest.TestCase):
+
+class ProjectThreadDecisionTests(unittest.TestCase):
+    """journal-venue: the user's decision in the 사장실 회사PC thread is the confirmation (no code in the message)."""
+
+    MESSAGE = "cmsg_TEST | user_TEST | 2026-10-27 15:27:32 KST | 카드 탭: 기록"
+
+    def setUp(self) -> None:
+        self.tmp = Path(tempfile.mkdtemp(prefix="review_journal_thread_"))
+        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
+        self.path = self.tmp / "decision_journal.json"
+        review = not_activated_review()
+        self.proposal = journal_module.build_proposal(
+            entry_type="s5_activation", payload=journal_module.activation_payload(review), review=review,
+            journal=journal_module.load_journal(self.path), now=NOW)
+
+    def apply(self, message, *, method: str = journal_module.PROJECT_THREAD_METHOD, code: str | None = None) -> dict:
+        return journal_module.apply_proposal(journal_path=self.path, proposal=self.proposal, confirmation={
+            "confirm_code": self.proposal["confirm_code"] if code is None else code,
+            "confirmation_method": method, "user_message": message})
+
+    def test_thread_decision_without_code_is_recorded_and_verifies(self) -> None:
+        self.assertNotIn(self.proposal["confirm_code"], self.MESSAGE.upper())
+        entry = self.apply(self.MESSAGE)
+        self.assertEqual((entry["confirmation_method"], entry["confirm_code"], entry["user_message"]),
+                         ("PROJECT_THREAD_USER_DECISION", self.proposal["confirm_code"], self.MESSAGE))
+        self.assertEqual((entry["order_authority"], entry["quantity_authority"]), (False, "none"))
+        loaded = journal_module.load_journal(self.path)
+        self.assertEqual((loaded["status"], len(loaded["entries"])), ("OK", 1))
+
+    def test_missing_or_empty_fields_are_rejected(self) -> None:
+        for message in ("", "   ", None, "cmsg_TEST | user_TEST | 2026-10-27 15:27:32 KST",
+                        "cmsg_TEST | | 2026-10-27 15:27:32 KST | 기록", " | user_TEST | 2026-10-27 KST | 기록",
+                        "cmsg_TEST | user_TEST | 2026-10-27 KST |  "):
+            with self.subTest(message=message):
+                with self.assertRaisesRegex(journal_module.JournalError, "PROJECT_THREAD_MESSAGE_INVALID"):
+                    self.apply(message)
+        self.assertFalse(self.path.exists())
+
+    def test_wrong_code_is_still_rejected(self) -> None:
+        with self.assertRaisesRegex(journal_module.JournalError, "CONFIRM_CODE_MISMATCH"):
+            self.apply(self.MESSAGE, code="DEADBEEF")
+        self.assertFalse(self.path.exists())
+
+    def test_other_methods_still_need_the_code_in_the_message(self) -> None:
+        for method in ("COWORK_CHAT_USER_MESSAGE", "USER_TERMINAL"):
+            with self.subTest(method=method):
+                with self.assertRaisesRegex(journal_module.JournalError, "USER_CONFIRMATION_MESSAGE_REQUIRED"):
+                    self.apply(self.MESSAGE, method=method)
+        with self.assertRaisesRegex(journal_module.JournalError, "CONFIRMATION_METHOD_INVALID"):
+            self.apply(self.MESSAGE, method="AUTO_CORE")
+        self.assertFalse(self.path.exists())
+
+    def test_hand_edited_thread_entry_is_corrupt(self) -> None:
+        self.apply(self.MESSAGE)
+        text = self.path.read_text(encoding="utf-8")
+        for mutate, reason in (
+                (lambda entry: entry.update(user_message="cmsg_TEST | user_TEST | 기록"), "PROJECT_THREAD_MESSAGE_INVALID"),
+                (lambda entry: entry.update(confirmation_method="COWORK_CHAT_USER_MESSAGE"),
+                 "CONFIRM_CODE_NOT_IN_USER_MESSAGE")):
+            with self.subTest(reason=reason):
+                document = json.loads(text)
+                mutate(document["entries"][-1])
+                self.path.write_text(json.dumps(document), encoding="utf-8")
+                loaded = journal_module.load_journal(self.path)
+                self.assertEqual((loaded["status"], loaded["errors"]),
+                                 ("CORRUPT", [f"JOURNAL_ENTRY_INCONSISTENT:1:{reason}"]))
+
+    def test_cli_apply_with_thread_decision_and_verify(self) -> None:
+        proposal_path = self.tmp / "journal_proposal.json"
+        proposal_path.write_text(json.dumps(self.proposal), encoding="utf-8")
+
+        def run(*argv: str) -> tuple[int, str]:
+            buffer = io.StringIO()
+            with contextlib.redirect_stdout(buffer):
+                code = journal_module.main(list(argv))
+            return code, buffer.getvalue()
+
+        base = ("apply", "--proposal", str(proposal_path), "--confirm", self.proposal["confirm_code"],
+                "--confirmed-via", "PROJECT_THREAD_USER_DECISION", "--journal", str(self.path))
+        self.assertEqual(run(*base)[0], 2)  # the thread decision text is required
+        self.assertEqual(run(*base, "--user-message", "cmsg_TEST | user_TEST | 기록")[0], 2)
+        self.assertFalse(self.path.exists())
+        self.assertEqual(run(*base, "--user-message", self.MESSAGE)[0], 0)
+        code, output = run("verify", "--journal", str(self.path))
+        self.assertEqual((code, json.loads(output)["status"], json.loads(output)["entry_count"]), (0, "OK", 1))
+
+
```

## 7. fix round 1 (Judge PASS_WITH_FIX, 2026-10-27)

Changes (worktree only; CLAUDE.md untouched by this Builder - fix 2 was added by the project thread, hash fdc14b56... -> fcf6d25b...; .claude settings, real journal, policy/state untouched; no commit/push/merge):
1. `apply_proposal_entries`: PROJECT_THREAD_USER_DECISION now rejects any proposal whose entry_type is not in CARD_ENTRY_TYPES (`PROJECT_THREAD_ENTRY_TYPE_INVALID`).
2. `_entry_inconsistency`: same rule on load/verify (a hand-edited thread entry of another type is CORRUPT with `PROJECT_THREAD_ENTRY_TYPE_INVALID`).
3. `project_thread_message_valid`: field 2 must start with `user_`, field 3 must end with `KST` (after strip).
Tests: ProjectThreadDecisionTests setUp now uses a card proposal (`make_card` + `build_card_proposal`); added s5_activation rejection, bad account/time field cases, hand-edit cases (bad account, entry_type -> s5_activation).

### diff -U0 (round 1 only, against the round-0 worktree text)

```diff
diff --git a/manage-us-stock-strategy/scripts/portfolio_review_journal.py b/manage-us-stock-strategy/scripts/portfolio_review_journal.py
index 90cc8f4..5f5b319 100644
--- a/manage-us-stock-strategy/scripts/portfolio_review_journal.py
+++ b/manage-us-stock-strategy/scripts/portfolio_review_journal.py
@@ -187,0 +188,2 @@ def _entry_inconsistency(entry: dict[str, Any], decisions: dict[str, dict[str, A
+        if entry_type not in CARD_ENTRY_TYPES:
+            return "PROJECT_THREAD_ENTRY_TYPE_INVALID"
@@ -239 +241 @@ def project_thread_message_valid(message: Any) -> bool:
-    """journal-venue: "<message or card id> | <account id> | <KST time> | <verbatim text>", no empty field."""
+    """journal-venue: "<message or card id> | user_<account> | <time> KST | <verbatim text>", no empty field."""
@@ -242,2 +244,3 @@ def project_thread_message_valid(message: Any) -> bool:
-    fields = message.split("|", 3)
-    return len(fields) == 4 and all(field.strip() for field in fields)
+    fields = [field.strip() for field in message.split("|", 3)]
+    return (len(fields) == 4 and all(fields) and fields[1].startswith("user_")
+            and fields[2].endswith("KST"))
@@ -553,0 +557,2 @@ def apply_proposal_entries(*, journal_path: Path, proposal: dict[str, Any], conf
+        if proposal["entry_type"] not in CARD_ENTRY_TYPES:
+            raise JournalError("PROJECT_THREAD_ENTRY_TYPE_INVALID")
diff --git a/manage-us-stock-strategy/tests/test_portfolio_review_journal.py b/manage-us-stock-strategy/tests/test_portfolio_review_journal.py
index 56a3d90..a44f1be 100644
--- a/manage-us-stock-strategy/tests/test_portfolio_review_journal.py
+++ b/manage-us-stock-strategy/tests/test_portfolio_review_journal.py
@@ -409,4 +409,4 @@ class ProjectThreadDecisionTests(unittest.TestCase):
-        review = not_activated_review()
-        self.proposal = journal_module.build_proposal(
-            entry_type="s5_activation", payload=journal_module.activation_payload(review), review=review,
-            journal=journal_module.load_journal(self.path), now=NOW)
+        card, pack = make_card()
+        self.proposal = journal_module.build_card_proposal(
+            card=card, fact_pack=pack, journal=journal_module.load_journal(self.path), now=NOW)
+        self.count = len(self.proposal["payload"]["decisions"])
@@ -426 +426,22 @@ class ProjectThreadDecisionTests(unittest.TestCase):
-        self.assertEqual((loaded["status"], len(loaded["entries"])), ("OK", 1))
+        self.assertEqual((loaded["status"], len(loaded["entries"])), ("OK", self.count))
+        self.assertEqual({item["entry_type"] for item in loaded["entries"]}, {"card_decision"})
+
+    def test_non_card_proposal_is_rejected(self) -> None:
+        review = not_activated_review()
+        self.proposal = journal_module.build_proposal(
+            entry_type="s5_activation", payload=journal_module.activation_payload(review), review=review,
+            journal=journal_module.load_journal(self.path), now=NOW)
+        with self.assertRaisesRegex(journal_module.JournalError, "PROJECT_THREAD_ENTRY_TYPE_INVALID"):
+            self.apply(self.MESSAGE)
+        self.assertFalse(self.path.exists())
+
+    def test_bad_account_or_time_field_is_rejected(self) -> None:
+        for message in ("cmsg_TEST | TEST | 2026-10-27 15:27:32 KST | 기록",
+                        "cmsg_TEST | acct_TEST | 2026-10-27 15:27:32 KST | 기록",
+                        "cmsg_TEST | user_TEST | 2026-10-27 15:27:32 | 기록",
+                        "cmsg_TEST | user_TEST | 2026-10-27 15:27:32 UTC | 기록",
+                        "cmsg_TEST | 2026-10-27 15:27:32 KST | user_TEST | 기록"):
+            with self.subTest(message=message):
+                with self.assertRaisesRegex(journal_module.JournalError, "PROJECT_THREAD_MESSAGE_INVALID"):
+                    self.apply(message)
+        self.assertFalse(self.path.exists())
@@ -455,0 +477,3 @@ class ProjectThreadDecisionTests(unittest.TestCase):
+                (lambda entry: entry.update(user_message="cmsg_TEST | TEST | 2026-10-27 15:27:32 KST | 기록"),
+                 "PROJECT_THREAD_MESSAGE_INVALID"),
+                (lambda entry: entry.update(entry_type="s5_activation"), "PROJECT_THREAD_ENTRY_TYPE_INVALID"),
@@ -464 +488 @@ class ProjectThreadDecisionTests(unittest.TestCase):
-                                 ("CORRUPT", [f"JOURNAL_ENTRY_INCONSISTENT:1:{reason}"]))
+                                 ("CORRUPT", [f"JOURNAL_ENTRY_INCONSISTENT:{self.count}:{reason}"]))
@@ -483 +507 @@ class ProjectThreadDecisionTests(unittest.TestCase):
-        self.assertEqual((code, json.loads(output)["status"], json.loads(output)["entry_count"]), (0, "OK", 1))
+        self.assertEqual((code, json.loads(output)["status"], json.loads(output)["entry_count"]), (0, "OK", self.count))
```

### sha256 / CRLF (LF count == CRLF count, no bare CR)

| file | sha256 | LF | CRLF |
|---|---|---|---|
| manage-us-stock-strategy/scripts/portfolio_review_journal.py (ASCII only) | c29f9d87fd3d3762b0cfcc0807b1b5a846fee74bb04f6a01341c4ec216d6cb23 | 977 | 977 |
| manage-us-stock-strategy/tests/test_portfolio_review_journal.py | b5b1c6ed4c557e5bf4a501dd0848b1aca7b165274001f30e5026d696969bb14a | 511 | 511 |
| CLAUDE.md (Judge fix 2 sentence, lines 40-42, added by the project thread before this round; not touched by this Builder) | fcf6d25bc6e5888a133eedc7a4d039fe4821b5a86d02ae73e319d381100c27b2 | 138 | 138 |

### tests

- `python -m unittest discover -s tests -p "test_portfolio_review_journal.py"`: Ran 22 tests, OK
- `python -m unittest discover -s tests -p "test_decision_journal_cards.py"`: Ran 36 tests, OK
- `python scripts/validate_schema_contracts.py`: PASS, errors []
