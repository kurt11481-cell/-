# Read-only diagnosis of ust21100 (US stock transaction history) return_code 2 seen by the auto-core bridge
# on 2026-10-13 (08:46 and 10:13 KST), while kiwoomcli returned 20 "no records" for the same period.
# Cowork, 2026-10-13. Run with the Kiwoom runtime python (same as the bridge worker). ASCII only.
# Calls ust21100 (/api/us/acnt, account inquiry) three times with three request bodies and prints only
# return_code, the return_msg with account-like numbers masked, the row count and the non-date body keys.
# No row content, no account label, no order route, no file written, no token reissue beyond normal reuse.
import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "manage-us-stock-strategy" / "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import kiwoom_runtime_bridge as rb  # noqa: E402
import kiwoom_account_readonly_bridge as ab  # noqa: E402

API_ID, PATH = ab.ACCOUNT_APIS["account_transaction_history_read"]
if (API_ID, PATH) != ("ust21100", "/api/us/acnt"):
    raise SystemExit("UNEXPECTED_ROUTE")
policy = json.loads((REPO / "workspace" / "policies" / "kiwoom-readonly-policy.json").read_text(encoding="utf-8"))
runtime = Path(policy["official_runtime_path"]).resolve()
os.chdir(runtime)
rb._load_env_without_echo(runtime / ".env")
session = rb._runtime_session(runtime, 0.5, 1, 1.0, set(), set(), 1, 0, 1, 1)
base = ab.request_body(ab.validate_request({"operation": "account_transaction_history_read",
                                             "params": {"strt_dt": "20261010", "end_dt": "20261013"}}))
variants = [
    ("A_bridge_body_as_is", dict(base)),
    ("B_krw_repl_skip_yn_N", dict(base, krw_repl_skip_yn="N")),
    ("C_tp_empty_krw_N", dict(base, tp="", krw_repl_skip_yn="N")),
]


def mask(text):
    text = re.sub(r"\d{2,}-\d{2,}-\d{1,}", "<ACNT>", text)
    return re.sub(r"\d{8,}", "<N>", text)


for name, body in variants:
    keys = {k: v for k, v in body.items() if k not in ("strt_dt", "end_dt")}
    try:
        session["pacer"]()
        response = session["client"].fetch_page(api_id=API_ID, path=PATH, body=body, cont_yn=None, next_key=None)
        payload = getattr(response, "body", None)
        if not isinstance(payload, dict):
            print(name, "NON_DICT_PAYLOAD", type(payload).__name__)
        else:
            rows = payload.get("result_list")
            print(name, "return_code=%r" % (payload.get("return_code"),),
                  "msg=" + mask(str(payload.get("return_msg"))),
                  "rows=%s" % (len(rows) if isinstance(rows, list) else None),
                  "body_keys=" + json.dumps(keys))
    except Exception as exc:  # print the type and a masked, short message only
        print(name, "EXCEPTION", type(exc).__name__, mask(str(exc))[:200], "body_keys=" + json.dumps(keys))
    time.sleep(1.0)
print("UST21100_DIAG_DONE")
