---
id: coreinput2-reference
title: "coreinput 1차 실행 최종 diff (attempt-2, Judge PASS) — coreinput2 Builder 참고용"
date: 2026-11-01
source: "workspace/outputs/dev-runs/coreinput/attempt-2/diff.patch (기준 커밋 9a7e16b, diff_hash 9874005c…dfd). coreinput은 병합하지 않음 — 사장 결정 카드 '문구 고친 뒤 병합'(2026-11-01 19:23 KST)으로 coreinput2가 대신함"
---

이 파일은 코드가 아니다. coreinput2-builder-prompt.md가 이 diff를 다시 만들되, 그 지시문 "이번에 다른 점"만 바꾸게 한다. 여기 적힌 docs/claude/coreinput-report.md는 coreinput2에서는 docs/claude/coreinput2-report.md로 쓴다.

````diff
diff --git a/manage-us-stock-strategy/scripts/auto_core_decide.py b/manage-us-stock-strategy/scripts/auto_core_decide.py
index 04b8a40..6d9c0ae 100644
--- a/manage-us-stock-strategy/scripts/auto_core_decide.py
+++ b/manage-us-stock-strategy/scripts/auto_core_decide.py
@@ -7,7 +7,9 @@
  3 inputs: 30-minute pages, close histories, corporate actions, calendar, card registry (F2), research record
    (F3; when today's is missing it is looked for every 5 minutes until 08:30 KST, then the run goes on without
    it: buys blocked), watchlist, alert policy, previous decision.json. The S7 review is run again with the
-   research record's earnings and the buy-target proposals (read-only output under <day>/s7/).
+   research record's earnings and the buy-target proposals (read-only output under <day>/s7/). An uncommitted or
+   missing docs/claude judgment input (coreinput, inputs.core_input_guard) blocks every buy and drops the redeployment
+   candidate: its reasons never enter a sell gate, but a sell can change (or lose its ticket) without the candidate.
  4 F6 outcome classification (read-only ust21150 order fills and ust21050 open orders only) of the tickets left
    unclassified by the latest record whose F6 ran (f6_ran); a record that ends before F6 or fails carries that
    record's ledger and tickets (carried_from) and commits nothing. A ticket is classified only after its
@@ -393,6 +395,7 @@ def decide(*, output_root: Path = AUTO_OUTPUT_ROOT, config_path: Path = core.CON
            watchlist_path: Path = inputs.WATCHLIST_PATH, docs_dir: Path = DOCS_DIR,
            explained_path: Path = compare_module.EXPLAINED_PATH, repo: Path = REPO_ROOT,
            registry_committed_check: Callable[[Path, Path], tuple[bool, str | None]] = inputs.registry_committed,
+           input_committed_check: Callable[[Path, Path], tuple[bool, str | None]] | None = None,
            calendar_loader: Callable[[datetime], dict[str, Any]] | None = None,
            score_runner: Callable[[Path], Any] | None = None,
            bars_loader: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
@@ -440,6 +443,7 @@ def decide(*, output_root: Path = AUTO_OUTPUT_ROOT, config_path: Path = core.CON
                     provenance_source=provenance_source, closes_root=closes_root, research_root=research_root,
                     registry_path=registry_path, watchlist_path=watchlist_path, docs_dir=docs_dir,
                     explained_path=explained_path, repo=repo, registry_committed_check=registry_committed_check,
+                    input_committed_check=registry_committed_check if input_committed_check is None else input_committed_check,
                     calendar_loader=calendar_loader, score_runner=score_runner, bars_loader=bars_loader,
                     previous=previous, carry=carry,
                     previous_all=previous_all, config_path=config_path, exceptions=exceptions)
@@ -506,8 +510,8 @@ def _run(*, decision: dict[str, Any], config: dict[str, Any], mode: str, provena
          paths: dict[str, Path], output_root: Path, output_directory: Path, day: str, now: datetime,
          clock: Callable[[], datetime], sleeper: Callable[[float], None], reader: Any, exposure_runner: Any,
          provenance_source: Any, closes_root: Path, research_root: Path, registry_path: Path, watchlist_path: Path,
-         docs_dir: Path, explained_path: Path, repo: Path, registry_committed_check: Any, calendar_loader: Any,
-         score_runner: Any, bars_loader: Any, previous: dict[str, Any] | None, carry: dict[str, Any],
+         docs_dir: Path, explained_path: Path, repo: Path, registry_committed_check: Any, input_committed_check: Any,
+         calendar_loader: Any, score_runner: Any, bars_loader: Any, previous: dict[str, Any] | None, carry: dict[str, Any],
          previous_all: list[tuple[str, Any]], config_path: Path,
          exceptions: list[tuple[str, str]]) -> dict[str, Any]:
     from run_portfolio_exposure_review import expected_completed_session, load_corporate_actions
@@ -528,6 +532,7 @@ def _run(*, decision: dict[str, Any], config: dict[str, Any], mode: str, provena
             and carry["evaluation_session"] == evaluation_session:
         return _no_new_session(decision=decision, carry=carry, previous=previous, previous_all=previous_all,
                                config=config, mode=mode, calendar=calendar, explained_path=explained_path,
+                               committed_check=input_committed_check, repo=repo,
                                output_root=output_root, output_directory=output_directory, day=day)
     journal_path = paths["journal"]
     from portfolio_review_journal import load_journal
@@ -561,6 +566,19 @@ def _run(*, decision: dict[str, Any], config: dict[str, Any], mode: str, provena
     registry = inputs.load_registry(registry_path, repo=repo, committed_check=registry_committed_check)
     watchlist = inputs.load_watchlist(watchlist_path)
     m6_docs = inputs.m6_documents(docs_dir)
+    recovery_text = (docs_dir / RECOVERY_GATE_DOC.name).read_text(encoding="utf-8") \
+        if (docs_dir / RECOVERY_GATE_DOC.name).is_file() else ""
+    # coreinput: checked right after the three documents are read, not after the research wait (up to 08:30), so an
+    # edit before the check is not missed by reading it later. A reason blocks buys only (never gates or card_check).
+    guard = inputs.core_input_guard(recovery_gate_path=docs_dir / RECOVERY_GATE_DOC.name, watchlist_path=watchlist_path,
+                                    docs_dir=docs_dir, repo=repo, committed_check=input_committed_check)
+    decision["inputs"]["core_input_guard"] = guard
+    previous_guard = ((previous or {}).get("inputs") or {}).get("core_input_guard") or {}
+    if guard["reasons"] and guard["reasons"] != previous_guard.get("reasons"):
+        exceptions.append(("CORE_INPUT_UNCOMMITTED",
+                           "\uc790\ub3d9 \ucf54\uc5b4 \uc785\ub825 \ubb38\uc11c \ubbf8\ucee4\ubc0b \u2014 \ub9e4\uc218 \uc8fc\ubb38\ud45c \ub9c9\ud798(\ub9e4\ub3c4 \uadf8\ub300\ub85c): "
+                           + ", ".join(reason.split(":", 1)[-1] for reason in guard["reasons"])
+                           + " \u2014 Cowork \ucee4\ubc0b \ud655\uc778"))
     wait = _wait_for_research(research_root, day, clock, sleeper)
     # The R-REC1 window (60 sessions to the evaluation session): damage facts and recorded sessions (r2 R2-4).
     window = [session for session in sessions if session <= evaluation_session][-rules.C["RREC_WINDOW_SESSIONS"]:]
@@ -641,8 +659,6 @@ def _run(*, decision: dict[str, Any], config: dict[str, Any], mode: str, provena
         attributed = tickets_module.attribute_orders(attributed, outcome_block["attributed"], day)
     decision.update(keys=keys, attributed_orders=attributed, f6_ran=True)
     # F1-F5 for the evaluation session (auto_core_replay runs the same function).
-    recovery_text = (docs_dir / RECOVERY_GATE_DOC.name).read_text(encoding="utf-8") \
-        if (docs_dir / RECOVERY_GATE_DOC.name).is_file() else ""
     seen: set[str] = set()
     for _day, item in previous_all:
         seen.update((item or {}).get("facts_seen") or [])
@@ -673,7 +689,8 @@ def _run(*, decision: dict[str, Any], config: dict[str, Any], mode: str, provena
         input_hashes={"registry": registry.get("sha256"),
                       "research_record": decision["inputs"]["research_record"]["sha256"],
                       "t1_result": decision["inputs"]["t1_result"]["sha256"]},
-        hold_range=True)  # close-confirm e: every ticket carries its hold range (priceCalc band, hold)
+        hold_range=True,  # close-confirm e: every ticket carries its hold range (priceCalc band, hold)
+        input_block=guard["reasons"])
     gate1 = session["gate1"]
     decision.update(symbols={symbol: _symbol_view(result) for symbol, result in session["symbols"].items()},
                     evidence=session["evidence"], buy_requirements=session["rows"], tickets=session["planned"]["tickets"],
@@ -687,7 +704,7 @@ def _run(*, decision: dict[str, Any], config: dict[str, Any], mode: str, provena
         decision["status"] = "HOLD"
     # F9 compare and the streak.
     block = compare_module.compare(decision, today_record.get("integrated_check_run"), registry["entries"], research_ok)
-    explained, explained_errors = compare_module.load_explained(explained_path)
+    explained, explained_errors = _committed_explained(explained_path, input_committed_check, repo)
     history = [(run_day, compare_module.streak_block(item)) for run_day, item in previous_all] + [(day, block)]
     block.update(streak=compare_module.streak(history, explained), required=int(config.get("decision_compare_days_required") or 5),
                  explained_errors=explained_errors)
@@ -804,9 +821,25 @@ def _rerun(decision: dict[str, Any], output_directory: Path, now: datetime) -> d
     return decision
 
 
+def _committed_explained(path: Path, committed_check: Callable[[Path, Path], tuple[bool, str | None]],
+                         repo: Path) -> tuple[list[dict[str, Any]], list[str]]:
+    """coreinput: load_explained, but an explanation file that is a symbolic link or not committed explains nothing
+    (EXPLAINED_FILE_UNCOMMITTED first in the errors). It only feeds the compare streak; no file stays as before."""
+    explained, errors = compare_module.load_explained(path)
+    target = Path(path)
+    if not target.is_file():
+        return explained, errors
+    try:
+        committed = not target.is_symlink() and committed_check(target, repo)[0]
+    except Exception:  # noqa: BLE001 - an unknown commit state is not a committed file
+        committed = False
+    return (explained, errors) if committed else ([], ["EXPLAINED_FILE_UNCOMMITTED"] + errors)
+
+
 def _no_new_session(*, decision: dict[str, Any], carry: dict[str, Any], previous: dict[str, Any] | None,
                     previous_all: list[tuple[str, Any]], config: dict[str, Any], mode: str, calendar: dict[str, Any],
-                    explained_path: Path, output_root: Path, output_directory: Path, day: str) -> dict[str, Any]:
+                    explained_path: Path, committed_check: Callable[[Path, Path], tuple[bool, str | None]], repo: Path,
+                    output_root: Path, output_directory: Path, day: str) -> dict[str, Any]:
     """r3 R3-3: the evaluation session is the ledger source's (the latest record with f6_ran true): no U.S.
     session has closed since (a holiday before this run). Nothing new is judged: status OK, no ticket, no journal
     entry, no push, no broker read. The source's keys, attributed orders (r4 R4-1) and unclassified tickets are
@@ -828,7 +861,7 @@ def _no_new_session(*, decision: dict[str, Any], carry: dict[str, Any], previous
         run_core["tickets"] = [item for item in run_core["tickets"] if item.get("id") in not_yet]
     orders = [copy.deepcopy(order) for order in dashboard.get("orders") or [] if order.get("id") in not_yet]
     block: dict[str, Any] = {"status": compare_module.NO_NEW_SESSION, "same_session_as": carry["carried_from"]}
-    explained, explained_errors = compare_module.load_explained(explained_path)
+    explained, explained_errors = _committed_explained(explained_path, committed_check, repo)
     history = [(run_day, compare_module.streak_block(item)) for run_day, item in previous_all] + [(day, block)]
     block.update(streak=compare_module.streak(history, explained),
                  required=int(config.get("decision_compare_days_required") or 5), explained_errors=explained_errors)
@@ -936,7 +969,7 @@ def evaluate_session(*, day: str, mode: str, issued_at: str, calendar: dict[str,
                      keys: dict[str, Any], gate0: list[str], gate1: list[str],
                      s7_runner: Callable[[list[dict[str, Any]]], dict[str, Any]],
                      research: dict[str, Any], input_hashes: dict[str, Any],
-                     hold_range: bool = False) -> dict[str, Any]:
+                     hold_range: bool = False, input_block: list[str] | None = None) -> dict[str, Any]:
     """F1 judgments, F4 requirements and gates, F5 tickets for one evaluation session.
 
     decide and auto_core_replay both call this (one implementation). bars are load_symbol outputs for every
@@ -950,6 +983,10 @@ def evaluate_session(*, day: str, mode: str, issued_at: str, calendar: dict[str,
     hold_range (close-confirm e, user decision 2026-10-20): decide passes True, so plan() gets ctx["hold_eval"]
     and every ticket its hold range (tickets_module.hold_range); False (the replay, the default) keeps the tickets
     as before.
+    input_block (coreinput): decide's core_input_guard reasons; any reason blocks every buy and drops the redeployment
+    candidate. The reasons never enter a sell gate, but without the candidate's columns the sell regret table can end in
+    REGRET_ZERO, LOT_ZERO or DEADBAND (no sell ticket that day), as on a day without a candidate.
+    None (the replay, the default) keeps the tickets as before.
     """
     sessions = sorted(calendar["sessions"])
     later = [item for item in sessions if item > evaluation_session]
@@ -1104,7 +1141,7 @@ def evaluate_session(*, day: str, mode: str, issued_at: str, calendar: dict[str,
         "policy_instruments": policy_instruments,
         "scenarios": scenario, "keys": keys, "model_for": model_for, "redeploy_ranked": redeploy_ranked,
         "input_hashes": {**input_hashes, "s7_review_id": review.get("review_id")},
-        "research_block": research["block"],
+        "research_block": research["block"], "input_block": list(input_block or []),
         # risk1r: evaluation-session EMA20 and ATR14 for the display-only 1R of a buy ticket.
         "indicators": {symbol: marks_of(item) for symbol, item in symbols_out.items()},
     }
diff --git a/manage-us-stock-strategy/scripts/auto_core_inputs.py b/manage-us-stock-strategy/scripts/auto_core_inputs.py
index a0d0d66..b4011bb 100644
--- a/manage-us-stock-strategy/scripts/auto_core_inputs.py
+++ b/manage-us-stock-strategy/scripts/auto_core_inputs.py
@@ -197,6 +197,59 @@ def m6_documents(docs_dir: Path) -> list[tuple[str, str]]:
             for path in sorted(Path(docs_dir).glob(M6_PREFIX + "*.md"))]
 
 
+def _guard_label(path: Path, repo: Path) -> str:
+    """Repository-relative posix path (the last part is not followed: a link keeps its own name), else the file name."""
+    try:
+        return (path.parent.resolve() / path.name).relative_to(Path(repo).resolve()).as_posix()
+    except ValueError:
+        return path.name
+
+
+def core_input_guard(*, recovery_gate_path: Path, watchlist_path: Path, docs_dir: Path, repo: Path,
+                     committed_check: Callable[[Path, Path], tuple[bool, str | None]]) -> dict[str, Any]:
+    """coreinput: decide's docs/claude judgment inputs must be the committed ones. Checked: the R-REC1 document, the
+    watchlist and every M6 document (the glob of m6_documents). {status OK|BLOCKED, reasons (sorted), checked, details
+    {path: why}, sha256 {path: hex}}. Reasons: CORE_INPUT_MISSING:<path> (R-REC1 only: a missing watchlist is already
+    load_watchlist's UNREADABLE), CORE_INPUT_UNCOMMITTED:<path> (a symbolic link, a failed committed_check or one that
+    raises), CORE_INPUT_GUARD_ERROR:<exception>. It never raises: a decide failure would take the sell tickets too. The
+    reasons block every buy and drop the redeployment candidate (plan()): they never enter a sell gate, but a sell can
+    change or lose its ticket without the candidate.
+    The card registry has its own check; card documents are pinned by its section
+    hashes."""
+    reasons: set[str] = set()
+    checked: list[str] = []
+    details: dict[str, str] = {}
+    digests: dict[str, str] = {}
+    try:
+        recovery = Path(recovery_gate_path)
+        for path in [recovery, Path(watchlist_path), *sorted(Path(docs_dir).glob(M6_PREFIX + "*.md"))]:
+            label = _guard_label(path, repo)
+            checked.append(label)
+            linked = path.is_symlink()  # registry_committed resolves a link, so it sees only the link's target
+            if not linked and not path.is_file():
+                if path == recovery:
+                    reasons.add(f"CORE_INPUT_MISSING:{label}")
+                continue
+            if linked:
+                why = "SYMLINK"
+            else:
+                try:
+                    committed, reason = committed_check(path, repo)
+                    why = None if committed else reason or "UNCOMMITTED"
+                except Exception as exc:  # noqa: BLE001 - an unknown commit state is not a committed file
+                    why = type(exc).__name__
+            if why is not None:
+                reasons.add(f"CORE_INPUT_UNCOMMITTED:{label}")
+                details[label] = why
+            if path.is_file():
+                digests[label] = hashlib.sha256(path.read_bytes()).hexdigest()
+    except Exception as exc:  # noqa: BLE001 - see the docstring: buys are blocked, decide goes on
+        return {"status": "BLOCKED", "reasons": [f"CORE_INPUT_GUARD_ERROR:{type(exc).__name__}"],
+                "checked": sorted(checked), "details": details, "sha256": digests}
+    return {"status": "BLOCKED" if reasons else "OK", "reasons": sorted(reasons), "checked": sorted(checked),
+            "details": details, "sha256": digests}
+
+
 # ---------------------------------------------------------------------------------------------
 # F3 research records
 # ---------------------------------------------------------------------------------------------
diff --git a/manage-us-stock-strategy/scripts/auto_core_tickets.py b/manage-us-stock-strategy/scripts/auto_core_tickets.py
index 277e197..f38dbde 100644
--- a/manage-us-stock-strategy/scripts/auto_core_tickets.py
+++ b/manage-us-stock-strategy/scripts/auto_core_tickets.py
@@ -737,6 +737,9 @@ def plan(ctx: dict[str, Any]) -> dict[str, Any]:
                    and ctx["evidence"][symbol]["sell"]["basis_met"]}
         ctx["redeploy_candidate"] = next((dict(item) for item in ctx["redeploy_ranked"]
                                           if item["symbol"] not in selling), None)
+    # coreinput: a candidate picked from unverified inputs does not reach the sell regret table (as if none passed).
+    if ctx.get("input_block"):
+        ctx["redeploy_candidate"] = None
 
     # Sells (circuit D5): a held symbol with an S7 reduce item or a card EXIT/TRIM target and sell evidence.
     for symbol in sorted(holdings):
@@ -816,8 +819,9 @@ def _plan_buy(ctx: dict[str, Any], row: dict[str, Any], add_symbols: set[str], g
                        else "S7_ADD_RECOMMENDATION"})
     # r2 R2-1: without an OK research record of the day every buy (index ETFs included) is blocked.
     research = [f"RESEARCH_RECORD_NOT_OK:{ctx['research_block']}"] if ctx["research_block"] is not None else []
-    reasons = list(global_reasons) + research + list((ctx["checks"].get(symbol) or {}).get("reasons") or []) + \
-        ctx["data_reasons"].get(symbol, [])
+    # coreinput: an uncommitted or missing docs/claude judgment input blocks every buy too.
+    reasons = list(global_reasons) + research + list(ctx.get("input_block") or []) + \
+        list((ctx["checks"].get(symbol) or {}).get("reasons") or []) + ctx["data_reasons"].get(symbol, [])
     return _buy_ticket(ctx, symbol, row, evidence, reasons, blocked)
 
 
diff --git a/docs/claude/coreinput-report.md b/docs/claude/coreinput-report.md
new file mode 100644
index 0000000..8a15444
--- /dev/null
+++ b/docs/claude/coreinput-report.md
@@ -0,0 +1,62 @@
+---
+id: coreinput-report
+title: "자동 코어 입력 문서 보호 — Builder 보고"
+date: 2026-11-01
+source: docs/claude/coreinput-builder-prompt.md
+---
+
+## 결과
+- 07:45 decide가 읽는 docs/claude 입력 4종이 미커밋·없음·링크·git 실패·가드 오류이면 매수 주문표를 막는다. 가드가 막은 날 재배치 후보가 빠지면 후보 없는 날과 같은 계산으로 REGRET_ZERO, LOT_ZERO, DEADBAND가 되어 그날 매도 주문표가 안 나올 수 있다.
+- 대상 테스트 `test_auto_core*`: 579건 실행, 실패 1건, 건너뜀 1건. 실패는 지시문에 적힌 기준선 실패 `RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches`(symbol='PLTR') 하나뿐이다.
+- 건너뜀 1건은 기존 skipUnless 테스트다(새 테스트 파일에는 skip 없음). 어느 테스트인지는 실행 출력에 나오지 않아 특정하지 못했다. 기준선과의 비교는 파이프라인 checks가 한다.
+- 스키마 감사 PASS. 전체 스위트는 지시문대로 돌리지 않았다.
+
+## 바뀐 줄
+| 파일:행 | 내용 |
+|---|---|
+| `manage-us-stock-strategy/scripts/auto_core_inputs.py:200-205` | `_guard_label` 새 함수(repo 상대 posix, repo 밖이면 파일 이름, 마지막 경로 조각은 링크를 따라가지 않음) |
+| `manage-us-stock-strategy/scripts/auto_core_inputs.py:208-252` | `core_input_guard` 새 함수 |
+| `manage-us-stock-strategy/scripts/auto_core_decide.py:10-12` | 모듈 설명 2줄 추가 |
+| `manage-us-stock-strategy/scripts/auto_core_decide.py:398, 446, 513` | `input_committed_check` 인자. None이면 `registry_committed_check` 사용 |
+| `manage-us-stock-strategy/scripts/auto_core_decide.py:535` | `_no_new_session`에 check·repo 전달 |
+| `manage-us-stock-strategy/scripts/auto_core_decide.py:569-582` | R-REC1 읽기를 m6_docs 바로 뒤로 이동, 가드 호출, `decision["inputs"]["core_input_guard"]`, 알림 |
+| `manage-us-stock-strategy/scripts/auto_core_decide.py:693` | `evaluate_session(..., input_block=guard["reasons"])` |
+| `manage-us-stock-strategy/scripts/auto_core_decide.py:707, 864` | 판정 대조 설명 두 곳을 `_committed_explained`로 묶음 |
+| `manage-us-stock-strategy/scripts/auto_core_decide.py:824-836` | `_committed_explained` 새 함수 |
+| `manage-us-stock-strategy/scripts/auto_core_decide.py:972, 986-989, 1144` | `input_block` 키워드, 설명, `ctx["input_block"]` |
+| `manage-us-stock-strategy/scripts/auto_core_tickets.py:740-742` | 기존 재배치 후보 대입 뒤에서 input_block이 있으면 `redeploy_candidate = None` |
+| `manage-us-stock-strategy/scripts/auto_core_tickets.py:822-824` | `_plan_buy` 사유에 research 사유 바로 뒤로 input_block 추가 |
+| `manage-us-stock-strategy/tests/test_auto_core_input_guard.py` | 새 파일, 29건(사례 a~k + 읽기 순서, 실제 매도 주문표 2건, 후보가 매도를 좌우하는 경우 1건 등) |
+
+기존 테스트·스키마·`m6_listed`·EV3 정규식·`registry_committed`·06:15 T1 파일은 바꾸지 않았다.
+
+## 가드 검사 목록과 사유 문자열
+검사 목록: `docs_dir / RECOVERY_GATE_DOC.name`, `watchlist_path`, `m6_documents`와 같은 glob(`M6_PREFIX + "*.md"`, 같은 정렬)의 파일 전부. `explained_path`는 가드 목록이 아니라 `_committed_explained`가 따로 검사한다(연속 일수 표시에만 쓰임, 매수를 막지 않음).
+
+| 문자열 | 언제 |
+|---|---|
+| `CORE_INPUT_MISSING:<경로>` | R-REC1 문서 없음 |
+| `CORE_INPUT_UNCOMMITTED:<경로>` | 미추적·수정됨, git 실패, check 예외, 심볼릭 링크. 왜 그런지는 `details[<경로>]`에 적힘(`REGISTRY_UNCOMMITTED`, `REGISTRY_GIT_UNAVAILABLE`, 예외 이름, `SYMLINK`) |
+| `CORE_INPUT_GUARD_ERROR:<예외 이름>` | 가드 안의 예상 못 한 예외. 이때 status BLOCKED이고 decide는 FAIL이 아니다 |
+| `EXPLAINED_FILE_UNCOMMITTED` | 설명 파일이 링크·미커밋·check 예외. `compare.explained_errors` 맨 앞, `explained = []` |
+| 알림 code `CORE_INPUT_UNCOMMITTED` | reasons가 직전 기록과 다를 때만 1건, push true |
+
+관심 명단 파일이 없을 때는 지시문대로 사유를 만들지 않는다. 파일이 없으면 비보유 종목만 빠지고 보유 종목 매수 경로는 남는다(`load_watchlist` UNREADABLE = 관심 종목 없음, `auto_core_inputs.py:148-157`, `auto_core_decide.py:601-607`). 문서가 새로 여는 관문은 없다.
+
+## 읽기·검사 순서
+registry 읽기 → watchlist 읽기 → M6 읽기 → R-REC1 읽기 → 가드(R-REC1, 관심 명단, M6 순서로 check) → 연구 기록 대기(최대 08:30) → 나머지. `test_guard_runs_before_the_research_wait`가 이 순서를 확인한다. 가드는 `_no_new_session` 분기 뒤에 있어서, 새 세션이 없는 날은 돌지 않는다. 그날은 주문표가 새로 나오지 않는다.
+
+## 반드시 적을 것
+- (a) 이 변경은 매수 관문을 조이기만 하고 완화하는 곳이 없다. 재배치 후보 None은 매도 regret 열·수량·swap_pair를 바꿀 수 있다. 가드가 막은 날 재배치 후보가 빠지면 후보 없는 날과 같은 계산으로 REGRET_ZERO, LOT_ZERO, DEADBAND가 되어 그날 매도 주문표가 안 나올 수 있다. 가드 사유 자체는 gate0·gate1·card_check·`_plan_sell` 사유에 들어가지 않는다. `test_candidate_issues_one_third_and_a_guard_block_ends_in_regret_zero`가 후보가 있으면 1/3 단계로 발행되고 input_block이 있으면 REGRET_ZERO로 발행되지 않으며 그 결과가 `redeploy_ranked=[]`와 같음을 고정한다. 코드는 지시문 C절대로 두었고, 이 동작의 수용 여부는 사장 병합 결정에서 판단한다.
+- (b) 커밋된 편집은 막지 못한다. `git update-index --assume-unchanged/--skip-worktree`도 막지 못한다.
+- (c) 병합 뒤 첫 새 세션 판정에서 `inputs.core_input_guard.status` OK 확인이 필요하다.
+- 주문·권한 줄: 표지 없음.
+
+## 남은 위험
+1. 정상 작업도 막힐 수 있다: 23:30 문서 자동 커밋 뒤부터 07:45 사이에 관심 명단이나 M6 문서를 고치고 커밋하지 않으면 그날 매수가 막히고 push가 온다. 의도한 동작이다. 저장소의 .py·.ps1에는 `watchlist-registry.json`을 고치는 코드가 없었으나, 예약 작업의 LLM 프롬프트가 쓰는 시점은 살피지 않았다(확인 필요).
+2. 알림이 한 번 더 올 수 있다: 직전 기록이 가드까지 가지 못한 날(새 세션 없음, T1 없음 등 조기 종료)이면 `inputs.core_input_guard`가 없어, 같은 사유가 이어져도 다음 날 다시 push된다. 놓치는 쪽이 아니라 더 알리는 쪽이다.
+3. 같은 날 재실행: `decision_identity_hash`는 inputs 전체를 쓰므로 `core_input_guard`도 해시에 든다. 기록 모드에서 병합 전 기록이 있는 날 병합 후 재실행하거나, 같은 날 입력 문서를 바꾼 뒤 재실행하면 기존 `_rerun` 경로(HOLD, 주문표 없음)로 간다. 막히는 쪽으로 동작하며, 그 경로는 바꾸지 않았다.
+4. 문서가 UTF-8로 깨진 경우: R-REC1 또는 M6 본문 읽기 예외는 지금처럼 decide FAIL이 된다(매도 주문표도 없음). 읽기 시점만 F6 앞으로 옮겨졌을 뿐 결과는 같고, 기존 동작이라 바꾸지 않았다. 가드는 읽기 뒤에 돌기 때문에 이 경우를 잡지 못한다.
+5. 읽기와 가드 사이의 아주 짧은 틈에 생긴 편집은 놓칠 수 있다(가드의 sha256은 가드 시점 값이다).
+6. 새 테스트 파일은 LF다. 다른 테스트 파일은 CRLF다. 고친 기존 파일 3개는 줄 수와 CRLF 줄 수가 같아 CRLF가 유지됐다(382, 1322, 1308줄).
+7. 알림 한 줄의 "매도 그대로"는 지시문 B절의 문구라 바꾸지 않았다(수정 지시 범위 밖). 가드 때문에 매도 주문표가 안 나오는 날에는 이 문구가 실제와 맞지 않는다. `auto_core_decide.py:572` 주석의 "blocks buys only"도 같은 이유로 두었다.
diff --git a/manage-us-stock-strategy/tests/test_auto_core_input_guard.py b/manage-us-stock-strategy/tests/test_auto_core_input_guard.py
new file mode 100644
index 0000000..3038987
--- /dev/null
+++ b/manage-us-stock-strategy/tests/test_auto_core_input_guard.py
@@ -0,0 +1,385 @@
+"""coreinput: decide's docs/claude judgment inputs (R-REC1 document, M6 documents, watchlist, compare explanations).
+
+An uncommitted, missing or linked input blocks every buy ticket and drops the redeployment candidate. Its reasons never
+enter a sell gate, but without the candidate a sell can change or lose its ticket (CandidateCarriesTheSellTests). decide
+never fails because of it and the push comes once per change. All inputs are synthetic (TEST_ONLY); no network, no
+Kiwoom.
+"""
+
+from __future__ import annotations
+
+import copy
+import sys
+import unittest
+from decimal import Decimal
+from pathlib import Path
+from unittest import mock
+
+TESTS = Path(__file__).resolve().parent
+sys.path.insert(0, str(TESTS))
+
+import test_auto_core_decide as decide_fixture  # noqa: E402
+import test_auto_core_tickets as tickets_tests  # noqa: E402
+
+decide_module = decide_fixture.decide_module
+inputs = decide_fixture.inputs
+tk = tickets_tests.tk
+helpers = tickets_tests.helpers
+Env = decide_fixture.Env
+write_json = decide_fixture.write_json
+DAYS = tickets_tests.DAYS
+
+RECOVERY = "recovery-gate-R-REC1-2026-10-09.md"
+M6 = "m6-relative-comparison-7stock-TEST.md"
+WATCHLIST = "watchlist-registry.json"
+REGISTRY = "card-evidence-registry.json"
+EXPLAINED = "explained.json"
+RECOVERY_LABEL = "docs/claude/" + RECOVERY
+PREVIOUS_DAY = "2026-10-01"
+
+
+def committed(path, repo):
+    return True, None
+
+
+def uncommitted(*names, reason="REGISTRY_UNCOMMITTED"):
+    """A committed check that fails for the given file names only."""
+    return lambda path, repo: (False, reason) if Path(path).name in names else (True, None)
+
+
+def buys(decision):
+    return [ticket for ticket in decision["tickets"] if ticket["side"] == "buy"]
+
+
+def blocked_buy_reasons(decision, symbol="MU"):
+    return [reason for item in decision["blocked"] if item["symbol"] == symbol and item["side"] == "buy"
+            for reason in item["reasons"]]
+
+
+def guard_of(decision):
+    return decision["inputs"]["core_input_guard"]
+
+
+class BuyCase(unittest.TestCase):
+    """The setting that gives one MU buy ticket when nothing blocks it."""
+
+    def setUp(self):
+        self.env = Env(holdings={"SOXL": 10})
+        self.addCleanup(self.env.close)
+        self.env.write_good_news()
+
+    def assert_buy_blocked(self, decision, reason):
+        self.assertIn(decision["status"], ("OK", "HOLD"), decision["reasons"])
+        self.assertEqual(buys(decision), [])
+        self.assertIn(reason, guard_of(decision)["reasons"])
+        self.assertEqual(guard_of(decision)["status"], "BLOCKED")
+        self.assertIn(reason, blocked_buy_reasons(decision))
+        self.assertEqual(decide_fixture.validate_instance(decision, decide_module.DECISION_SCHEMA), [])
+
+
+class AllCommittedTests(BuyCase):
+    def test_a_all_committed_changes_nothing(self):
+        plain = self.env.run()
+        checked = self.env.run(input_committed_check=committed)
+        self.assertEqual(len(buys(plain)), 1, plain["blocked"])
+        guard = guard_of(checked)
+        self.assertEqual((guard["status"], guard["reasons"], guard["details"]), ("OK", [], {}))
+        self.assertEqual(checked["tickets"], plain["tickets"])
+        self.assertEqual(checked["blocked"], plain["blocked"])
+        self.assertEqual(checked["reasons"], plain["reasons"])
+        self.assertFalse(any(alert["code"] == "CORE_INPUT_UNCOMMITTED" for alert in checked["alerts"]))
+
+    def test_a_guard_lists_every_input_with_its_hash(self):
+        guard = guard_of(self.env.run(input_committed_check=committed))
+        expected = ["docs/claude/" + name for name in (RECOVERY, M6, WATCHLIST)]
+        self.assertEqual(guard["checked"], sorted(expected))
+        self.assertEqual(sorted(guard["sha256"]), sorted(expected))
+        self.assertTrue(all(len(value) == 64 for value in guard["sha256"].values()))
+
+
+class BlockedInputTests(BuyCase):
+    def test_b_uncommitted_recovery_document_blocks_buys(self):
+        decision = self.env.run(input_committed_check=uncommitted(RECOVERY))
+        reason = f"CORE_INPUT_UNCOMMITTED:{RECOVERY_LABEL}"
+        self.assert_buy_blocked(decision, reason)
+        self.assertEqual(guard_of(decision)["details"], {RECOVERY_LABEL: "REGISTRY_UNCOMMITTED"})
+
+    def test_c_missing_recovery_document_blocks_buys(self):
+        (self.env.docs / RECOVERY).unlink()
+        decision = self.env.run(input_committed_check=committed)
+        self.assert_buy_blocked(decision, f"CORE_INPUT_MISSING:{RECOVERY_LABEL}")
+        self.assertNotIn(RECOVERY_LABEL, guard_of(decision)["sha256"])
+
+    def test_d_new_uncommitted_m6_file_blocks_buys(self):
+        name = "m6-relative-comparison-7stock-NEW.md"
+        (self.env.docs / name).write_text("MU", encoding="utf-8")
+        decision = self.env.run(input_committed_check=uncommitted(name))
+        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:docs/claude/{name}")
+
+    def test_d_existing_uncommitted_m6_file_blocks_buys(self):
+        decision = self.env.run(input_committed_check=uncommitted(M6))
+        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:docs/claude/{M6}")
+
+    def test_e_uncommitted_watchlist_blocks_buys(self):
+        decision = self.env.run(input_committed_check=uncommitted(WATCHLIST))
+        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:docs/claude/{WATCHLIST}")
+
+    def test_e_missing_watchlist_makes_no_guard_reason(self):
+        self.env.watchlist.unlink()
+        decision = self.env.run(input_committed_check=committed)
+        self.assertEqual(decision["inputs"]["watchlist"]["status"], "UNREADABLE")
+        self.assertEqual(guard_of(decision)["reasons"], [])
+        self.assertEqual(buys(decision), [])
+
+    def test_f_git_failure_blocks_buys_with_its_reason(self):
+        decision = self.env.run(input_committed_check=uncommitted(RECOVERY, reason="REGISTRY_GIT_UNAVAILABLE"))
+        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:{RECOVERY_LABEL}")
+        self.assertEqual(guard_of(decision)["details"][RECOVERY_LABEL], "REGISTRY_GIT_UNAVAILABLE")
+
+    def test_f_committed_check_exception_blocks_buys(self):
+        def raises(path, repo):
+            if Path(path).name == RECOVERY:
+                raise RuntimeError("TEST_ONLY")
+            return True, None
+
+        decision = self.env.run(input_committed_check=raises)
+        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:{RECOVERY_LABEL}")
+        self.assertEqual(guard_of(decision)["details"][RECOVERY_LABEL], "RuntimeError")
+
+    def test_f_unexpected_guard_error_blocks_buys_and_decide_does_not_fail(self):
+        original = Path.glob
+        seen = []
+
+        def second_m6_glob_fails(path, pattern, *args, **kwargs):  # the first one is m6_documents, the second the guard
+            if pattern.startswith(inputs.M6_PREFIX):
+                seen.append(pattern)
+                if len(seen) == 2:
+                    raise OSError("TEST_ONLY")
+            return original(path, pattern, *args, **kwargs)
+
+        with mock.patch.object(Path, "glob", second_m6_glob_fails):
+            decision = self.env.run(input_committed_check=committed)
+        self.assertEqual(len(seen), 2)
+        self.assertNotEqual(decision["status"], "FAIL", decision["reasons"])
+        self.assert_buy_blocked(decision, "CORE_INPUT_GUARD_ERROR:OSError")
+
+    def test_g_symbolic_link_blocks_buys_even_when_its_target_is_committed(self):
+        with mock.patch.object(Path, "is_symlink", lambda path: path.name == RECOVERY):
+            decision = self.env.run(input_committed_check=committed)
+        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:{RECOVERY_LABEL}")
+        self.assertEqual(guard_of(decision)["details"], {RECOVERY_LABEL: "SYMLINK"})
+
+    def test_k_registry_check_is_used_when_no_input_check_is_given(self):
+        decision = self.env.run(registry_committed_check=uncommitted(RECOVERY))
+        self.assertTrue(decision["inputs"]["registry"]["committed"])
+        self.assert_buy_blocked(decision, f"CORE_INPUT_UNCOMMITTED:{RECOVERY_LABEL}")
+
+    def test_guard_reason_stays_out_of_the_gates_and_the_decision_reasons(self):
+        decision = self.env.run(input_committed_check=uncommitted(RECOVERY))
+        self.assertEqual([reason for reason in decision["reasons"] if reason.startswith("CORE_INPUT")], [])
+
+    def test_guard_runs_before_the_research_wait(self):
+        order = []
+        original = decide_module._wait_for_research
+
+        def wait(*args):
+            order.append("wait")
+            return original(*args)
+
+        def check(path, repo):
+            order.append(Path(path).name)
+            return True, None
+
+        with mock.patch.object(decide_module, "_wait_for_research", wait):
+            self.env.run(input_committed_check=check)
+        self.assertEqual(order[:3], [RECOVERY, WATCHLIST, M6])
+        self.assertEqual(order[3], "wait")
+
+
+class ExplainedFileTests(BuyCase):
+    def explained_path(self):
+        path = self.env.root / EXPLAINED
+        write_json(path, {"schema_version": "redesign-t2-compare-explained-1.0", "items": []})
+        return path
+
+    def test_h_uncommitted_explanation_only_changes_the_compare_block(self):
+        base = self.env.run(input_committed_check=committed)
+        self.explained_path()
+        decision = self.env.run(input_committed_check=uncommitted(EXPLAINED))
+        self.assertEqual(decision["compare"]["explained_errors"], ["EXPLAINED_FILE_UNCOMMITTED"])
+        self.assertEqual(decision["tickets"], base["tickets"])
+        self.assertEqual(decision["blocked"], base["blocked"])
+        self.assertEqual(guard_of(decision)["reasons"], [])
+
+    def test_h_committed_or_absent_explanation_stays_as_before(self):
+        self.assertEqual(self.env.run(input_committed_check=uncommitted(EXPLAINED))["compare"]["explained_errors"], [])
+        self.explained_path()
+        self.assertEqual(self.env.run(input_committed_check=committed)["compare"]["explained_errors"], [])
+
+    def test_h_uncommitted_explanation_explains_nothing_and_keeps_the_load_errors(self):
+        (self.env.root / EXPLAINED).write_text("{broken", encoding="utf-8")
+        decision = self.env.run(input_committed_check=uncommitted(EXPLAINED))
+        self.assertEqual(decision["compare"]["explained_errors"],
+                         ["EXPLAINED_FILE_UNCOMMITTED", "EXPLAINED_FILE_UNREADABLE"])
+
+    def test_h_link_or_check_exception_counts_as_uncommitted(self):
+        path = self.explained_path()
+        with mock.patch.object(Path, "is_symlink", lambda item: item.name == EXPLAINED):
+            self.assertEqual(decide_module._committed_explained(path, committed, self.env.root),
+                             ([], ["EXPLAINED_FILE_UNCOMMITTED"]))
+
+        def raises(item, repo):
+            raise RuntimeError("TEST_ONLY")
+
+        self.assertEqual(decide_module._committed_explained(path, raises, self.env.root),
+                         ([], ["EXPLAINED_FILE_UNCOMMITTED"]))
+
+    def test_h_no_new_session_day_uses_the_same_check(self):
+        self.explained_path()
+        first = self.env.run(input_committed_check=committed)
+        first.update(run_day_kst=PREVIOUS_DAY, f6_ran=True)  # the same evaluation session: nothing new today
+        (self.env.output / PREVIOUS_DAY).mkdir()
+        write_json(self.env.output / PREVIOUS_DAY / "decision.json", first)
+        decision = self.env.run(input_committed_check=uncommitted(EXPLAINED))
+        self.assertTrue(decision["no_new_session"])
+        self.assertEqual(decision["compare"]["explained_errors"], ["EXPLAINED_FILE_UNCOMMITTED"])
+
+
+class AlertTests(BuyCase):
+    LINE = ("자동 코어 입력 문서 미커밋 — 매수 주문표 막힘(매도 그대로): "
+            f"{RECOVERY_LABEL} — Cowork 커밋 확인")
+
+    def setUp(self):
+        super().setUp()
+        self.base = self.env.run(input_committed_check=committed)
+        (self.env.output / PREVIOUS_DAY).mkdir()
+
+    def alerts_after(self, previous_reasons):
+        record = decide_fixture._as_of(copy.deepcopy(self.base), PREVIOUS_DAY)  # an earlier session: a new one today
+        record["inputs"]["core_input_guard"]["reasons"] = previous_reasons
+        write_json(self.env.output / PREVIOUS_DAY / "decision.json", record)
+        decision = self.env.run(input_committed_check=uncommitted(RECOVERY))
+        self.assertFalse(decision["no_new_session"])
+        self.assertEqual(buys(decision), [])
+        return [alert for alert in decision["alerts"] if alert["code"] == "CORE_INPUT_UNCOMMITTED"]
+
+    def test_i_first_day_pushes_once(self):
+        self.assertEqual(self.alerts_after([]),
+                         [{"code": "CORE_INPUT_UNCOMMITTED", "line": self.LINE, "push": True}])
+
+    def test_i_same_reasons_as_the_previous_record_do_not_push(self):
+        self.assertEqual(self.alerts_after([f"CORE_INPUT_UNCOMMITTED:{RECOVERY_LABEL}"]), [])
+
+    def test_i_changed_reasons_push_again(self):
+        alerts = self.alerts_after(["CORE_INPUT_UNCOMMITTED:docs/claude/other.md"])
+        self.assertEqual([alert["push"] for alert in alerts], [True])
+
+
+def plan_ctx(ranked, **extra):
+    return {"symbols": {}, "checks": {"A": {"entry": {"card_action": "EXIT"}}, "B": {"entry": {"card_action": "HOLD"}}},
+            "review": {}, "s7": {}, "holdings": {"A": 10, "B": 5}, "equity": Decimal("10000"), "weights": {},
+            "closes": {}, "sigmas": {}, "config": {}, "gate0": {"ok": False, "reasons": ["G0_TEST"]},
+            "gate1": {"ok": True, "reasons": []}, "buy_rows": [], "data_reasons": {}, "run_day": "2026-10-10",
+            "evidence": {symbol: {"sell": {"basis_met": True, "r_max": "1/3"}} for symbol in ("A", "B")},
+            "redeploy_ranked": ranked, **extra}
+
+
+def sell_results(planned):
+    return ([ticket for ticket in planned["tickets"] if ticket["side"] == "sell"],
+            [item for item in planned["blocked"] if item["side"] == "sell"])
+
+
+class RedeployCandidateTests(unittest.TestCase):
+    RANKED = [{"symbol": "A", "up": 0.1, "down": -0.1}, {"symbol": "B", "up": 0.2, "down": -0.2}]
+
+    def test_j_input_block_drops_the_candidate_and_leaves_the_sells_as_without_candidates(self):
+        blocked = plan_ctx(self.RANKED, input_block=["CORE_INPUT_UNCOMMITTED:x"])
+        planned = tk.plan(blocked)
+        self.assertIsNone(blocked["redeploy_candidate"])
+        self.assertEqual(sell_results(planned), sell_results(tk.plan(plan_ctx([]))))
+
+    def test_j_without_input_block_the_candidate_stays(self):
+        for extra in ({}, {"input_block": []}):
+            ctx = plan_ctx(self.RANKED, **extra)
+            tk.plan(ctx)
+            self.assertEqual(ctx["redeploy_candidate"], self.RANKED[1])
+
+    def test_j_replay_without_a_ranking_gets_no_candidate_key_unless_blocked(self):
+        ctx = plan_ctx(None)
+        tk.plan(ctx)
+        self.assertNotIn("redeploy_candidate", ctx)
+
+    def test_j_a_real_sell_ticket_is_the_one_issued_without_a_candidate(self):
+        def scenario():
+            item = tickets_tests.Scenario(holdings={"SOXL": 400}, cash="3000")
+            item.bars["SOXL"] = helpers.bars("SOXL", DAYS, tickets_tests.falling_soxl())
+            return item
+
+        original = decide_module.evaluate_session
+
+        def with_block(**kwargs):
+            return original(**kwargs, input_block=["CORE_INPUT_UNCOMMITTED:x"])
+
+        with mock.patch.object(decide_module, "redeploy_ranking", return_value=[]):
+            without_candidates = scenario().run()
+        with mock.patch.object(decide_module, "evaluate_session", side_effect=with_block):
+            blocked = scenario().run()
+        sells = tickets_tests.tickets_of(blocked, "SOXL", "sell")
+        self.assertEqual(len(sells), 1, blocked["planned"]["blocked"])
+        self.assertEqual(sell_results(blocked["planned"]), sell_results(without_candidates["planned"]))
+        self.assertEqual(sells[0]["regret"]["columns"], ["up:cash", "down:cash"])
+
+
+class CandidateCarriesTheSellTests(unittest.TestCase):
+    """The candidate's columns can be what issues a sell: without them (a guard block or a day without a candidate)
+    the same numbers choose step 0, so that day has no sell ticket."""
+
+    CANDIDATE = {"symbol": "MU", "up": 0.6, "down": -0.01}
+
+    def result(self, ranked, input_block=()):
+        scenario = tickets_tests.Scenario(holdings={"SOXL": 400}, cash="3000")
+        scenario.bars["SOXL"] = helpers.bars("SOXL", DAYS, tickets_tests.falling_soxl())
+        original = tk.plan
+
+        def shaped(ctx):
+            ctx["scenarios"]["SOXL"].update(up=0.3, down=-0.01)
+            ctx["evidence"]["SOXL"]["sell"]["r_max"] = "1/3"
+            ctx.update(redeploy_ranked=ranked, input_block=list(input_block))
+            return original(ctx)
+
+        with mock.patch.object(tk, "plan", shaped):
+            return scenario.run()
+
+    def test_candidate_issues_one_third_and_a_guard_block_ends_in_regret_zero(self):
+        issued = self.result([self.CANDIDATE])
+        sells = tickets_tests.tickets_of(issued, "SOXL", "sell")
+        self.assertEqual(len(sells), 1, issued["planned"]["blocked"])
+        self.assertEqual(sells[0]["regret"]["chosen"], "1/3")
+        self.assertEqual(sells[0]["regret"]["columns"], ["up:cash", "down:cash", "up:MU", "down:MU"])
+        guarded = self.result([self.CANDIDATE], input_block=["CORE_INPUT_UNCOMMITTED:x"])
+        self.assertEqual(tickets_tests.tickets_of(guarded, "SOXL", "sell"), [])
+        self.assertEqual(tickets_tests.blocked_reasons(guarded, "SOXL", "sell"), ["REGRET_ZERO"])
+        self.assertEqual(sell_results(guarded["planned"]), sell_results(self.result([])["planned"]))
+
+
+class SellThroughDecideTests(unittest.TestCase):
+    def env(self):
+        env = Env(holdings={"SOXL": 400}, cash="3000", soxl_closes=tickets_tests.falling_soxl())
+        self.addCleanup(env.close)
+        return env
+
+    def test_guard_block_leaves_the_sell_ticket_with_its_hold_range(self):
+        decision = self.env().run(input_committed_check=uncommitted(RECOVERY, M6, WATCHLIST))
+        self.assertEqual(guard_of(decision)["status"], "BLOCKED")
+        sells = [ticket for ticket in decision["tickets"] if ticket["side"] == "sell"]
+        self.assertEqual(len(sells), 1, decision["blocked"])
+        self.assertEqual(sells[0]["priceCalc"]["hold"]["status"], "ok")
+        self.assertEqual(sells[0]["regret"]["columns"], ["up:cash", "down:cash"])
+        self.assertEqual(buys(decision), [])
+        plain = self.env().run()
+        self.assertEqual([(ticket["ticker"], ticket["side"]) for ticket in plain["tickets"] if ticket["side"] == "sell"],
+                         [(sells[0]["ticker"], "sell")])
+
+
+if __name__ == "__main__":
+    unittest.main()
````
