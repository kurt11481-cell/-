#!/usr/bin/env python3
"""Intraday shadow replay, run once (docs/claude/system-evolution-2026-10-31.md 1-4 and 10, D3 exception 1).

MODELLED_ONLY, SHADOW NAV != ACTUAL NAV: display only, never an input to the core, state, reconciliation or
journal. Reads only the saved Kiwoom 30-minute pages and regular-session close histories pinned below by
sha256 (any other file is ignored, any mismatch stops the run). Never calls Kiwoom, never reads a clock,
writes only the --out file.

Rule, fixed before any result was seen (bars labelled by their START time in U.S. Eastern time):
- opening range = the 09:30 bar (high H, low L);
- long entry at the close of the first bar from 10:00 through the bar before the session's final regular bar
  (the history's bar_cntr_tm) whose close is above H; at most one trade per symbol per session;
- stop = (H + L) / 2 rounded down to the cent; risk = entry - stop; no trade when risk < 0.05% of the entry;
- target = entry + 2 x risk rounded half up to the cent;
- every later bar through the final bar, in this order: open <= stop -> exit at the open; open >= target ->
  exit at the target; low <= stop -> exit at the stop (also when the same bar reaches the target);
  high >= target -> exit at the target; no exit by then -> exit at the final bar's close;
- R = (exit - entry) / risk - c x (entry + exit) / risk, c = commission per side.
Verdict per symbol at c = 0.25%: PASS when trades >= 30 and the one-sided 97.5% lower bound of the mean R
(10,000 bootstrap means, seed 20261031, the 251st smallest) is above 0; FEE_CONDITIONAL when that fails but
the same test at c = 0.07% passes; otherwise FAIL. The 0% and 0.07% versions are for reference only.

usage: intraday_shadow_replay.py run --root <regular-session-closes folder> [--out result.json]
       intraday_shadow_replay.py selftest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from collections import Counter
from datetime import datetime, timedelta
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from pathlib import Path

SYMBOLS = ("SOXX", "SOXL")
DECISION_COST = Decimal("0.0025")
FEE_CONDITIONAL_COST = Decimal("0.0007")
COSTS = (Decimal("0"), FEE_CONDITIONAL_COST, DECISION_COST)
TARGET_R = Decimal("2")
MIN_RISK_FRACTION = Decimal("0.0005")
MIN_TRADES = 30
BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20261031
LOWER_INDEX = 250  # 0-based: the 251st smallest of 10,000 sorted means
RANGE_TIME = "093000"
CENT = Decimal("0.01")
STAMP_FORMAT = "%Y%m%d%H%M%S"

PINNED = {
    "history/SOXL.close-history.json": "a7bd7e143f7e6dbdb72145559c72a3138ce40a182cc7f75dc1da89043c26a045",
    "history/SOXX.close-history.json": "409185c4987301bac1d46b0c8aa1a20c4b42cb63a682a75760ec2254ca3ddb55",
    "pages/SOXL/soxl_30m_20260402_p3.json": "dc4d94b64557f3df3016e7e838b5170d70eba873b32bf64f94cf776e67bf6754",
    "pages/SOXL/soxl_30m_20260409_p3.json": "ee03f601fa770b4456814c605308f600d2245dc667ef11c0987da15b2c0c95a4",
    "pages/SOXL/soxl_30m_20260416_p3.json": "dd7c0065f9dffc9010586a4590093a1556a700e949f3a3de0b5432b80927423f",
    "pages/SOXL/soxl_30m_20260423_p3.json": "49c9f592509a85107b76535324f7cf9e584e22084b676fbbce8a5ca65b30b347",
    "pages/SOXL/soxl_30m_20260430_p3.json": "67df098a3e7b4cb546183ff820cfc5ced030339c2017c73be592246ee290dc44",
    "pages/SOXL/soxl_30m_20260507_p3.json": "6a78724e059093fe94105ed12c40bb0009b1ae44d349df5d70b8d40ec4b3666e",
    "pages/SOXL/soxl_30m_20260514_p3.json": "b39388c849486f7e2b8c1c2ba460afc9ed83b31eb99a553692901b17d0b857bd",
    "pages/SOXL/soxl_30m_20260521_p3.json": "643a61303f27a4c2ee0ba76cc0bbf28eb476c5450b82c3f24ecadfb04eb0f8d9",
    "pages/SOXL/soxl_30m_20260528_p3.json": "c186db5c12e1365c20800be066c028f4c339a4a2c029f34242a6f287052d0d1e",
    "pages/SOXL/soxl_30m_20260604_p3.json": "ee0d9408776e9fa56536ed2d830d0a058af544706e967844a93922d048bce0d3",
    "pages/SOXL/soxl_30m_20260611_p3.json": "bf019dd6442e66377ae3e19c6374337a579be1de67a275d772215c51a6f55346",
    "pages/SOXL/soxl_30m_20260618_p3.json": "6ab5da6c011272567adf35c0204fa2709ace4410916c266d9b3b0cec333e4f5c",
    "pages/SOXL/soxl_30m_20260625_p3.json": "947f36f9d84d8c3b62aada0deab7fd7c8b7e4e0a939459dd6839c2cc5a590dac",
    "pages/SOXL/soxl_30m_20260702_p3.json": "5f23b034f72d53781679abec3b44d91342ba3785164cd84ebf7dd5666eb6f405",
    "pages/SOXL/soxl_30m_20260709_p3.json": "5fe22a24f602cf22485ec2df641dfac44762328624a576db2080e460f4d39031",
    "pages/SOXL/soxl_30m_20260716_p3.json": "43b5e2929b5a994abf196d628f36ef24d84af5a64302c66ae9af3f5e23708620",
    "pages/SOXL/soxl_30m_20260723_p3.json": "ef2a3321fba862fc8eb5eb882777c5eb6425fccbaa41397006c156a0fcb2e5e2",
    "pages/SOXL/soxl_30m_20260730_p3.json": "6ed733df45720a24b1fab2c9aec33395224f982763cb7f8c2c00f8804163d39d",
    "pages/SOXL/soxl_30m_20260806_p3.json": "837e10625b538abc661b71f1c015fb28c64f515abf34182733bec3a301ad1c50",
    "pages/SOXL/soxl_30m_20260813_p3.json": "e22385f867d644d9b0ab4a15a7a7f3f0c7e8c1d1bfd1f61c277c986b3c4803f0",
    "pages/SOXL/soxl_30m_20260820_p3.json": "be177233a81203dfdac0ebc4c951bebc6b845c2c08abd866de30235ca2c07b1f",
    "pages/SOXL/soxl_30m_20260827_p3.json": "b9884d268289682ac0b42b5d5d766cd887ddcce60c3318dc1e059c0eecb936a3",
    "pages/SOXL/soxl_30m_20260903_p3.json": "9e1bc6768c84a508fbf911d4a90515c8e37828f371ee26a5af391b851ebf3689",
    "pages/SOXL/soxl_30m_20260910_p3.json": "d5d66e4bd8d68e867642bf2ca292d82d87956c3b1d985567aa2c1fabfd305e74",
    "pages/SOXL/soxl_30m_20260917_p3.json": "777321f26bac759bba229756b8cfadab7ed56656e662b43dc8b664b3bb08d8ae",
    "pages/SOXL/soxl_30m_20260924_p3.json": "69dd8d85c2bf23d9fc2e7bec08a04a87259cc3b38398ecbd5c54c1e58d807f99",
    "pages/SOXL/soxl_30m_20261001_p3.json": "58e366d9f919c174ddc1fcd7c72ca3a45f6d3d6eb78e47bdbe3e31b619b28a6e",
    "pages/SOXL/soxl_30m_20261002_p3.json": "50027ab4d82cd320a2e3f65485d14c98b8682c8f41b4f15ead715b8691bbe599",
    "pages/SOXL/soxl_30m_20261005_p3.json": "8adc7349f9d2dc9b05c6e33faf3f04fa72280f1453406caf47d41a37815f8f6b",
    "pages/SOXL/soxl_30m_20261006_p3.json": "1fa501093a2e1d60c713dc67f51288dad64451dd5cebeee9de367aac826f277b",
    "pages/SOXL/soxl_30m_20261007_p3.json": "c6f87800f73208d4a61922759299ef6d68f3bdc3bcafb859dbe6390d8ad0690c",
    "pages/SOXL/soxl_30m_20261008_p3.json": "c54a8df06f517fc1f56a3170fd9e83d36ab15550e0dcf41fd8680dc5006870e2",
    "pages/SOXL/soxl_30m_20261009_p3.json": "156594b134702e76edc0cf2394b27b9a41ebb9b5e539a7cde84031aa0ae0feef",
    "pages/SOXL/soxl_30m_20261013_p3.json": "c4563762ec929a8ce29346373a0e735600cc14f1c3d3c91908682d6a1ab982f8",
    "pages/SOXL/soxl_30m_20261014_p3.json": "99deceaca0a73d42d2543f51f48dc777dc11245140b86aecb296d75a2261fe95",
    "pages/SOXL/soxl_30m_20261015_p3.json": "c5bc978258a0e6b968574a828e32c1f026e2833c9d145558a8f92cbc17b37e3e",
    "pages/SOXL/soxl_30m_20261016_p3.json": "d396f022544ff99a2dc649a9fe06361adcfa73eee536c5fc361690b290d87cd5",
    "pages/SOXL/soxl_30m_20261017_p3.json": "6e1beb74f481b4a880a3267594e78d7255b8302e1fc248feb48f67b8ae242704",
    "pages/SOXL/soxl_30m_20261020_p3.json": "3c1de428a68ecdf98af2f2404a73df72eae097455a212412492d9d6f778e58ee",
    "pages/SOXL/soxl_30m_20261021_p3.json": "8f3881e0282d1cf51c2ae65d8ef15a58c05e66ec66cd6e6296d5d8eff6ce0102",
    "pages/SOXL/soxl_30m_20261022_p3.json": "66c6ba4c1b8538bbc02e03debe483872f04dabcf39092c3590f08b3b78e08d16",
    "pages/SOXL/soxl_30m_20261023_p3.json": "e3f69d699080411030dff1edb2b619da3d8769174183e8271874a621e114bd7e",
    "pages/SOXL/soxl_30m_20261024_p3.json": "918d99d1f3bc1d800c7eea5b4f5ba22729d2bc6af0604f4d2c3931bb51bbf0f7",
    "pages/SOXL/soxl_30m_20261027_p3.json": "92c9d5f5b4ff3bf892c328f8caba204586348b5a5ba3e45ddf126a9de4b3400d",
    "pages/SOXL/soxl_30m_20261028_p3.json": "1a615cda0e2bf9411ebae61706d0b9805646fd6acce76009dce406c71e191265",
    "pages/SOXL/soxl_30m_20261029_p3.json": "fe283e02e46c6cf78408d10b35eb6822f88ee5419c92bfa2150e5bf687a62616",
    "pages/SOXL/soxl_30m_20261030_p3.json": "c49f8f8be9866f7a0016b04d0259a021b2d730fbf6adf77e98b99397231cbc1f",
    "pages/SOXL/soxl_30m_20261031_p3.json": "36b7c89def68ed31af5412ca05ce23f973bfd1980d94374968d3c32e47c1741c",
    "pages/SOXX/soxx_30m_20260402_p3.json": "cc26b63cc34b7e39a47b9c22b7fbfc56e4266da8f46962ec1991f75bb6a388cb",
    "pages/SOXX/soxx_30m_20260409_p3.json": "0b5eac66c7ebf3bf8676ada205b61a37c4e58eec6c0a6304359c4c7d70844ab1",
    "pages/SOXX/soxx_30m_20260416_p3.json": "e112eccc1028d0fd68dd8568e306535f09c9fa0ad9070aff2402b0f50e9f8a10",
    "pages/SOXX/soxx_30m_20260423_p3.json": "49116659ba056f64f0430462da84e31edda6fab1d3034d4351b3f6a78dc1969a",
    "pages/SOXX/soxx_30m_20260430_p3.json": "d12adbd3118de4e60b2b44943ef0a29259547b573a609e0997273cc588cedf80",
    "pages/SOXX/soxx_30m_20260507_p3.json": "7f9f374de7f1feaf52b8fa1aa96db926fac1cba5856f3de2d9aa998bf728ebff",
    "pages/SOXX/soxx_30m_20260514_p3.json": "498e8ee371b6a28ba42da0a6a84c2de273ac89d20dd42327566980194dcf23a9",
    "pages/SOXX/soxx_30m_20260521_p3.json": "8686510051b60c37ade93612a1966a19c152e8db7e6e969a99471ee449ca95af",
    "pages/SOXX/soxx_30m_20260528_p3.json": "fe913ff24c715464b2a726f36fcd914e767f79bf069d11d7c5819af1fadcb923",
    "pages/SOXX/soxx_30m_20260604_p3.json": "de74cf072f8f089f5a6206d1988a25988097774e73c8efd3cfece87829f0ad05",
    "pages/SOXX/soxx_30m_20260611_p3.json": "f4f942dbf9f68daa6de8c3e63d27500d0cb21302b9b8ade0d6febb7031e906a6",
    "pages/SOXX/soxx_30m_20260618_p3.json": "3628f298e37247130c58e2b512bf06cebfa45fc0612df49f5b24f87a5de53311",
    "pages/SOXX/soxx_30m_20260625_p3.json": "697b6c5de42c40827549e65da65bf4f9f1a3f05b3193a3de4a56e383b2a46a7b",
    "pages/SOXX/soxx_30m_20260702_p3.json": "2aeff74092f237c98eed2aeacc0468f50b134ee2eddea5f50763d1cd6423411b",
    "pages/SOXX/soxx_30m_20260709_p3.json": "287d2d29f32f05eb1548b124226437f2d4bf9ca657dd0aa925db58beaca466ea",
    "pages/SOXX/soxx_30m_20260716_p3.json": "5b59372de6588518808f63f0ea44e605316ce039e5ba94c7ef09959970d5d213",
    "pages/SOXX/soxx_30m_20260723_p3.json": "231391a4c368cf8f85d2d2f8b1da469532a9f995b9717a3e401458a62fb71ff3",
    "pages/SOXX/soxx_30m_20260730_p3.json": "08980e2f2edfb9cf13d905a96c7788a44452163b9605c47fef9d15feee316290",
    "pages/SOXX/soxx_30m_20260806_p3.json": "34716db89436f16a21f869ca2502d1f56c3ac7c943681641bbb53e698eb96b5c",
    "pages/SOXX/soxx_30m_20260813_p3.json": "3dc1aab835c9952e1226b7c32af0a8685653fedc9748b63999a3cb2a07828307",
    "pages/SOXX/soxx_30m_20260820_p3.json": "a8ce3cc7fc3020d336138d8a0132e2dd3c48b5c6c8bb2ed629ec981b95fb7645",
    "pages/SOXX/soxx_30m_20260827_p3.json": "1483a837d7479cc10290a29233182defd2ecd780ded7e2d9403187ea1b851473",
    "pages/SOXX/soxx_30m_20260903_p3.json": "40bd0f726c34cff2b2068a6dd9360f36b7c7b23e949aa4fa271d7f6588a29fac",
    "pages/SOXX/soxx_30m_20260910_p3.json": "e8ca02d3cf67701625547e1f530e6e456474605cb30d96be93d8feea519dbe4f",
    "pages/SOXX/soxx_30m_20260917_p3.json": "ecb99bd8a61bd0d264e56db777416740c8f15ca1753772ad80ba9882230f8c61",
    "pages/SOXX/soxx_30m_20260924_p3.json": "b7ea88ddfc91241b5b1ec4fc8d54ae241782f5b626768e34e8346d6dbd01dcde",
    "pages/SOXX/soxx_30m_20261001_p3.json": "056f9db877c31899e4ea71b7b8f67b72fe009621ba5c2a6dace9bcb1313dea83",
    "pages/SOXX/soxx_30m_20261002_p3.json": "4f991b73c74b1bafd4e771d04ed40d12b05f570c7cd047b303e5ffba01b267a5",
    "pages/SOXX/soxx_30m_20261005_p3.json": "8aa9e957c8a2525965dd0e5f0297cb607ddb3bc0527435fee67d8e95fa833add",
    "pages/SOXX/soxx_30m_20261006_p3.json": "e92f451381b3ff79f5598b20cc84959353bff7f346482b44570094b3bb64e640",
    "pages/SOXX/soxx_30m_20261007_p3.json": "e2dbe5b594b72198084c5dd68469de9f8854b25cad59560fe560742f3798125e",
    "pages/SOXX/soxx_30m_20261008_p3.json": "aac4d73c0f8a9201d081e2c85a85ecf6af986cdfe14a68c55fde9a526c907b93",
    "pages/SOXX/soxx_30m_20261009_p3.json": "3afdca7967590145a2699208bea4cb221544d0d1cbb7b8967c37b7801a3e490d",
    "pages/SOXX/soxx_30m_20261013_p3.json": "b4f2fbd6b1fd0ddf9ba5bddce7317f3a2cb4d93c4e75827d872c880bc3a7e559",
    "pages/SOXX/soxx_30m_20261014_p3.json": "25033526974f28599bf351b9be8cc4c573f6129e81639a4e812855addb8ac771",
    "pages/SOXX/soxx_30m_20261015_p3.json": "f7f484cc044364457357f40c4ad6e8389f6b49f8062b442da1caa5d60a0c50c4",
    "pages/SOXX/soxx_30m_20261016_p3.json": "b768d66bd701b51ea657bded4a5e5533e3124e044a2478cf8b7530daa39cad8c",
    "pages/SOXX/soxx_30m_20261017_p3.json": "225c637e457d1e0a4e8476960a9c1fed6efd2e67b8476e705d66ae0ec4aeedfc",
    "pages/SOXX/soxx_30m_20261020_p3.json": "32fe35679b11b79684867db8e8f88e0769d58e3413e88e8e16e39a8301810928",
    "pages/SOXX/soxx_30m_20261021_p3.json": "e0ea5d75110e9ff768a20791948ff2a0878bd3dd9fbfd069dbc05185a39d25b4",
    "pages/SOXX/soxx_30m_20261022_p3.json": "fa0338deb3392b33452484f1ea70466a2aa9c2d20400822976a3a85d8f20560c",
    "pages/SOXX/soxx_30m_20261023_p3.json": "f14dcf2bd3cbbe9e62b755857dc209603e7f1b061bcef66625a07fde80d78f3b",
    "pages/SOXX/soxx_30m_20261024_p3.json": "992fd3fd3ada6d4905e2bd0eda6b7a85b7624603ae540778fb08f53f15770a45",
    "pages/SOXX/soxx_30m_20261027_p3.json": "772094d5ca2ae3c788898c975b177321202299dc98cc126a087785c23ba47cd4",
    "pages/SOXX/soxx_30m_20261028_p3.json": "284d5c959725356d91f0f9631b95c29ceabbfeb60776bf60787928a26889af52",
    "pages/SOXX/soxx_30m_20261029_p3.json": "4554c01875c51a3846b732532ec0bff36a993cd3e774693aacc06bd7f421c367",
    "pages/SOXX/soxx_30m_20261030_p3.json": "b79480245ff393328cea8d2fefd0bb2ebe1acdff6bd35e2608a5562fb9d790fc",
    "pages/SOXX/soxx_30m_20261031_p3.json": "62c21ddd867c163daeea79ac85b4dbb39326e3c8d0f1ce6ad075877333ea97ff",
}

class ReplayError(Exception):
    """Fail-closed input error."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_sha256() -> str:
    text = "".join(f"{digest}  {name}\n" for name, digest in sorted(PINNED.items()))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_inputs(root: Path) -> None:
    problems = []
    for name, digest in sorted(PINNED.items()):
        path = root / name
        if not path.is_file():
            problems.append(f"MISSING:{name}")
        elif file_sha256(path) != digest:
            problems.append(f"HASH_MISMATCH:{name}")
    if problems:
        raise ReplayError("INPUT_NOT_PINNED " + " ".join(problems[:5]))


def load_bars(paths: list[Path]) -> dict[str, tuple[Decimal, Decimal, Decimal, Decimal]]:
    """Merge pages like regular_session_close_history.build_history, comparing all four prices."""
    bars: dict[str, tuple[Decimal, Decimal, Decimal, Decimal]] = {}
    for path in sorted(paths, key=lambda item: item.name):
        document = json.loads(path.read_bytes().decode("utf-8-sig"))
        if document.get("return_code") != 0:
            raise ReplayError(f"PAGE_RETURN_CODE:{path.name}")
        rows = document["result_list"]
        previous = None
        for row in rows:
            stamp = row["cntr_tm"]
            if len(stamp) != 14 or not stamp.isdigit() or row["bus_dt"] != stamp[:8]:
                raise ReplayError(f"PAGE_ROW_TIME_INVALID:{path.name}:{stamp}")
            if previous is not None and stamp >= previous:
                raise ReplayError(f"PAGE_ROW_ORDER_INVALID:{path.name}:{stamp}")
            previous = stamp
        # The newest bar of a file may still be forming; a bar counts only when a later bar exists.
        for row in rows[1:]:
            value = tuple(Decimal(row[key]) for key in ("open_pric", "high_pric", "low_pric", "cur_prc"))
            if min(value) <= 0:
                raise ReplayError(f"PAGE_ROW_PRICE_INVALID:{path.name}:{row['cntr_tm']}")
            known = bars.get(row["cntr_tm"])
            if known is not None and known != value:
                raise ReplayError(f"PAGE_ROWS_CONFLICT:{row['cntr_tm']}")
            bars[row["cntr_tm"]] = value
    return bars


def session_labels(date: str, final_label: str) -> list[str]:
    moment = datetime.strptime(date + RANGE_TIME, STAMP_FORMAT)
    end = datetime.strptime(final_label, STAMP_FORMAT)
    labels = []
    while moment <= end:
        labels.append(moment.strftime(STAMP_FORMAT))
        moment += timedelta(minutes=30)
    return labels


def replay_session(bars: dict, date: str, final_label: str) -> dict:
    labels = session_labels(date, final_label)
    if len(labels) < 3 or labels[-1] != final_label:
        return {"status": "CALENDAR_UNEXPECTED"}
    missing = [label for label in labels if label not in bars]
    if missing:
        return {"status": "INCOMPLETE", "missing": missing}
    _, high, low, _ = bars[labels[0]]
    stop = ((high + low) / 2).quantize(CENT, rounding=ROUND_FLOOR)
    entry_index = next((index for index in range(1, len(labels) - 1) if bars[labels[index]][3] > high), None)
    if entry_index is None:
        return {"status": "NO_ENTRY"}
    entry = bars[labels[entry_index]][3]
    risk = entry - stop
    if risk < MIN_RISK_FRACTION * entry:
        return {"status": "REFUSED_TIGHT"}
    target = (entry + TARGET_R * risk).quantize(CENT, rounding=ROUND_HALF_UP)
    exit_label = exit_price = reason = None
    for label in labels[entry_index + 1:]:
        bar_open, bar_high, bar_low, _ = bars[label]
        if bar_open <= stop:
            exit_price, reason = bar_open, "STOP_GAP"
        elif bar_open >= target:
            exit_price, reason = target, "TARGET_GAP"
        elif bar_low <= stop:
            exit_price, reason = stop, "STOP"
        elif bar_high >= target:
            exit_price, reason = target, "TARGET"
        if reason is not None:
            exit_label = label
            break
    if reason is None:
        exit_label, exit_price, reason = labels[-1], bars[labels[-1]][3], "CLOSE"
    return {"status": "TRADE", "range_high": high, "range_low": low, "entry_label": labels[entry_index],
            "entry": entry, "stop": stop, "target": target, "risk": risk, "exit_label": exit_label,
            "exit": exit_price, "reason": reason}


def trade_r(trade: dict, cost: Decimal) -> float:
    entry, exit_price, risk = trade["entry"], trade["exit"], trade["risk"]
    return float((exit_price - entry) / risk - cost * (entry + exit_price) / risk)


def bootstrap_lower(values_by_cost: dict[Decimal, list[float]]) -> dict[Decimal, float]:
    """Same resampled sessions for every cost; seed restarts for each symbol."""
    count = len(next(iter(values_by_cost.values())))
    generator = random.Random(BOOTSTRAP_SEED)
    means: dict[Decimal, list[float]] = {cost: [] for cost in values_by_cost}
    for _ in range(BOOTSTRAP_SAMPLES):
        picks = [generator.randrange(count) for _ in range(count)]
        for cost, values in values_by_cost.items():
            means[cost].append(sum(values[index] for index in picks) / count)
    return {cost: sorted(values)[LOWER_INDEX] for cost, values in means.items()}


def passes(trade_count: int, lower: float) -> bool:
    return trade_count >= MIN_TRADES and lower > 0


def summarize(trades: list[dict]) -> dict:
    summary: dict = {"trades": len(trades), "exits": dict(sorted(Counter(t["reason"] for t in trades).items()))}
    if not trades:
        summary["verdict"] = "FAIL"
        summary["verdict_reason"] = "NO_TRADES"
        return summary
    values = {cost: [trade_r(trade, cost) for trade in trades] for cost in COSTS}
    lower = bootstrap_lower(values)
    summary["by_cost"] = {
        f"{cost * 100:.2f}%": {"mean_r": round(statistics.fmean(values[cost]), 4),
                               "median_r": round(statistics.median(values[cost]), 4),
                               "lower_97_5": round(lower[cost], 4),
                               "share_r_above_0": round(sum(v > 0 for v in values[cost]) / len(trades), 4)}
        for cost in COSTS}
    gross = values[Decimal("0")]
    summary["mean_risk_pct_of_entry"] = round(statistics.fmean(float(t["risk"] / t["entry"] * 100) for t in trades), 4)
    summary["mean_gross_r"] = round(statistics.fmean(gross), 4)
    if passes(len(trades), lower[DECISION_COST]):
        summary["verdict"] = "PASS"
    elif passes(len(trades), lower[FEE_CONDITIONAL_COST]):
        summary["verdict"] = "FEE_CONDITIONAL"
    else:
        summary["verdict"] = "FAIL"
        summary["verdict_reason"] = "TOO_FEW_TRADES" if len(trades) < MIN_TRADES else "LOWER_BOUND_NOT_ABOVE_0"
    return summary


def run(root: Path) -> dict:
    verify_inputs(root)
    result = {"artifact": "intraday-shadow-replay", "label": "MODELLED_ONLY", "shadow_nav_is_actual_nav": False,
              "script_sha256": file_sha256(Path(__file__)), "inputs_manifest_sha256": manifest_sha256(),
              "decision_cost_per_side": str(DECISION_COST), "target_r": str(TARGET_R), "symbols": {}}
    for symbol in SYMBOLS:
        pages = [root / name for name in PINNED if name.startswith(f"pages/{symbol}/")]
        bars = load_bars(pages)
        history = json.loads((root / f"history/{symbol}.close-history.json").read_bytes().decode("utf-8-sig"))
        sessions = history["sessions"]
        if history["symbol"] != symbol or len(sessions) != history["session_count"]:
            raise ReplayError(f"HISTORY_INVALID:{symbol}")
        statuses: Counter = Counter()
        trades = []
        for session in sessions:
            date = session["session_date"].replace("-", "")
            final_label = session["bar_cntr_tm"]
            final_bar = bars.get(final_label)
            if final_label[:8] != date or final_bar is None or final_bar[3] != Decimal(session["close"]):
                raise ReplayError(f"HISTORY_CLOSE_MISMATCH:{symbol}:{date}")
            outcome = replay_session(bars, date, final_label)
            statuses[outcome["status"]] += 1
            if outcome["status"] == "TRADE":
                trades.append({"session_date": session["session_date"], **outcome})
        summary = summarize(trades)
        summary["sessions"] = len(sessions)
        summary["session_status"] = dict(sorted(statuses.items()))
        summary["first_session"], summary["last_session"] = sessions[0]["session_date"], sessions[-1]["session_date"]
        summary["trade_list"] = [{key: (str(value) if isinstance(value, Decimal) else value)
                                  for key, value in trade.items()} for trade in trades]
        result["symbols"][symbol] = summary
    return result


def _bars(rows: dict[str, tuple]) -> dict:
    return {key: tuple(Decimal(str(value)) for value in values) for key, values in rows.items()}


def selftest() -> None:
    date, final = "20990105", "20990105153000"
    labels = session_labels(date, final)
    assert len(labels) == 13 and labels[0].endswith("093000") and labels[-1] == final

    def day(changes: dict[int, tuple]) -> dict:
        rows = {label: (100.5, 100.8, 100.2, 100.5) for label in labels}   # quiet day inside the range
        rows[labels[0]] = (100, 101, 99, 100)                          # range 99..101, stop 100.00
        for index, values in changes.items():
            rows[labels[index]] = values
        return _bars(rows)

    assert replay_session(day({}), date, final)["status"] == "NO_ENTRY"
    # Entry at the 10:00 bar close 102 (risk 2, target 106), target reached at 11:00.
    trade = replay_session(day({1: (100, 102.2, 100.5, 102), 3: (103, 106.5, 102.5, 106)}), date, final)
    assert (trade["entry"], trade["stop"], trade["target"], trade["reason"], trade["exit"]) == (
        Decimal("102"), Decimal("100.00"), Decimal("106.00"), "TARGET", Decimal("106.00")), trade
    assert abs(trade_r(trade, Decimal("0")) - 2.0) < 1e-12
    assert abs(trade_r(trade, Decimal("0.0025")) - (2.0 - 0.0025 * 208 / 2)) < 1e-12
    # One bar touches both the stop and the target: stop.
    trade = replay_session(day({1: (100, 102.2, 100.5, 102), 3: (102, 107, 99.9, 103)}), date, final)
    assert trade["reason"] == "STOP" and trade["exit"] == Decimal("100.00")
    # Gap below the stop: exit at the open; gap above the target: exit at the target.
    trade = replay_session(day({1: (100, 102.2, 100.5, 102), 2: (98, 99, 97, 98.5)}), date, final)
    assert trade["reason"] == "STOP_GAP" and trade["exit"] == Decimal("98")
    trade = replay_session(day({1: (100, 102.2, 100.5, 102), 2: (107, 108, 106.5, 107.5)}), date, final)
    assert trade["reason"] == "TARGET_GAP" and trade["exit"] == Decimal("106.00")
    # Entry at the 15:00 bar, no exit level reached: exit at the final bar's close.
    trade = replay_session(day({11: (100.5, 101.6, 100.4, 101.5), 12: (101.5, 101.8, 101.0, 101.2)}), date, final)
    assert trade["entry_label"].endswith("150000") and trade["reason"] == "CLOSE" and trade["exit"] == Decimal("101.2")
    # A breakout only in the final bar is not an entry.
    assert replay_session(day({12: (100.5, 102, 100.4, 101.8)}), date, final)["status"] == "NO_ENTRY"
    # Stop rounds down to the cent, target rounds half up.
    rows = {label: (100, 100.004, 99.996, 100) for label in labels}
    rows[labels[0]] = (100, 100.005, 99.99, 100)                       # mid 99.9975 -> stop 99.99
    rows[labels[1]] = (100, 100.02, 100, 100.015)                      # entry 100.015, risk 0.025 -> 0.025% < 0.05%
    assert replay_session(_bars(rows), date, final)["status"] == "REFUSED_TIGHT"
    rows[labels[1]] = (100, 100.1, 100, 100.075)                       # risk 0.085, target 100.245 -> 100.25
    trade = replay_session(_bars(rows), date, final)
    assert trade["stop"] == Decimal("99.99") and trade["target"] == Decimal("100.25"), trade
    # A missing regular bar makes the session incomplete.
    incomplete = day({})
    del incomplete[labels[5]]
    assert replay_session(incomplete, date, final)["status"] == "INCOMPLETE"
    # Bootstrap: deterministic, and a constant sample has that constant as its bound.
    first = bootstrap_lower({Decimal("0"): [0.5, -1.0, 2.0, -1.0, 0.25] * 8})
    assert first == bootstrap_lower({Decimal("0"): [0.5, -1.0, 2.0, -1.0, 0.25] * 8})
    assert bootstrap_lower({Decimal("0"): [0.3] * 40})[Decimal("0")] == 0.3
    assert passes(30, 0.01) and not passes(29, 0.5) and not passes(40, 0.0)
    print("SELFTEST OK")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--root", required=True, type=Path)
    run_parser.add_argument("--out", type=Path)
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        selftest()
        return 0
    try:
        result = run(args.root)
    except ReplayError as error:
        print(f"STOP {error}", file=sys.stderr)
        return 2
    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    for symbol, summary in result["symbols"].items():
        costs = " | ".join(f"{name} mean {item['mean_r']} lower {item['lower_97_5']}"
                           for name, item in summary.get("by_cost", {}).items())
        print(f"{symbol}: {summary['verdict']} trades {summary['trades']} exits {summary['exits']} | {costs}")
    print(f"script_sha256 {result['script_sha256']} inputs_manifest_sha256 {result['inputs_manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
