"""layer-audit-1125: apply the approved CLAUDE.md / AGENTS.md wording to one checkout (byte level, CRLF kept).

Usage: python layer-audit-1125-apply.py <checkout root>
Checks the before hashes, writes the two files, checks the after hashes. Any mismatch: exit 2, nothing written.
Wording: docs/claude/layer-audit-1125-builder-prompt.md. No order, Kiwoom, policy, state or journal access.
"""
import hashlib
import pathlib
import sys

BEFORE = {
    "CLAUDE.md": "48464bb4e5f462707ff0a7a42840c8affb61c48b18183332731f6efe0a8569da",
    "AGENTS.md": "621c139f6042ffbe8c6999eafe195170568d0ecd76b59f9e3027da542bbb9149",
}
AFTER = {
    "CLAUDE.md": "cd0868ce97165d4c605c9e558b023b85ef9dcc0575ab5000797eaae5093ad63c",
    "AGENTS.md": "c07e509436fff943054a90f58c8f7f7bde3caddc77c953eab71de43a44ecf718",
}

PREC = (b"Precedence (summary of constitution section 1 items 1-4; the last two places follow project instructions "
        b"section 2; adds no authority): the user's latest explicit safety/authority approval, given in the venue and "
        b"form this file requires > verified Production Runtime / Authority Constitution > "
        b"docs/claude/constitution-v1.5.0.md > approved policy > this file > project instructions. Project "
        b"instructions win only on session operations (model, effort, response style, report procedure), never on "
        b"the order ban, Hard safety, authority/limit class or approval venue. Nothing in this file widens the "
        b"constitution.")
OLD_109 = b"- Production authority: workspace/policies/integrated_identity_session_activation.json\r"
NEW_109 = (b"- Instrument identity/calendar authority (activation; holds no order or quantity authority): "
           b"workspace/policies/integrated_identity_session_activation.json\r")
ADD_132 = (" Premise B0 suspended since 2026-11-01 06:43 KST (user decision card '\ud6a8\ub825 \uc815\uc9c0'); the "
           "status line and the prompt-block rule in this item stay; record: "
           "docs/claude/market-scenario-27h1-2026-10-09.md section 6 and docs/claude/active-decisions.md.").encode("utf-8")
C1 = (b"- Constitution (docs/claude/constitution-v*.md; protected by tools/dev_pipeline/authority-paths.txt): pointer "
      b"only, sets no venue here. Changed only as a new version file (never overwrite) after the user's own typed "
      b"confirmation; commit only by the user's .\\tools\\commit-docs.ps1 -ApproveProtected. Precedent: 1.4.0 "
      b"docs/claude/top-guideline-review-2026-11-01.md sections 10-11; 1.5.0 "
      b"docs/claude/ops-linkage-guideline-2026-11-07.md section 12.\r")
C2 = (b"- Scheduled tasks (create/change/delete): pointer only, sets no rule here; the venue and steps stay in project "
      b"instructions section 4 (scheduled-task change); guide docs/claude/approval-venue-table-2026-10-25.md row 7, "
      b"including the limits that approval cannot lift.\r")
AG = (b"This file is for Codex; CLAUDE.md Hard safety and Kiwoom query rules bind Codex too, and where this file "
      b"differs CLAUDE.md wins.\r")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(root):
    root = pathlib.Path(root)
    raw = {n: (root / n).read_bytes() for n in BEFORE}
    for n, h in BEFORE.items():
        if sha(raw[n]) != h:
            print("LAYER_AUDIT_STOP before hash differs:", n, sha(raw[n]))
            return 2
    L = raw["CLAUDE.md"].split(b"\n")
    if L[108] != OLD_109 or not L[99].startswith(b"- Kiwoom acceptance pin") or L[8] != b"\r":
        print("LAYER_AUDIT_STOP anchor lines differ")
        return 2
    if not L[131].startswith(b"- Scenario guideline SCN-27H1"):
        print("LAYER_AUDIT_STOP line 132 differs")
        return 2
    N = list(L)
    N[131] = L[131][:-1] + ADD_132 + b"\r"
    N[108] = NEW_109
    N = N[:99] + [C1, C2] + N[99:]
    N = N[:9] + [PREC + b"\r", b"\r"] + N[9:]
    new_claude = b"\n".join(N)
    A = raw["AGENTS.md"].split(b"\n")
    new_agents = b"\n".join(A[:1] + [b"\r", AG] + A[1:])
    out = {"CLAUDE.md": new_claude, "AGENTS.md": new_agents}
    for n, h in AFTER.items():
        if sha(out[n]) != h:
            print("LAYER_AUDIT_STOP after hash differs:", n, sha(out[n]))
            return 2
    for n, b in out.items():
        (root / n).write_bytes(b)
    for n, h in AFTER.items():
        print("OK", n, sha((root / n).read_bytes()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
