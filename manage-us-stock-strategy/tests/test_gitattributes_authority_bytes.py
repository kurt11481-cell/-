"""Authority files read over raw bytes must stay out of CRLF conversion (gitattr-bytes, 2026-11-02)."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

RAW_BYTE_PATHS = (
    "workspace/research/provider-evidence/kiwoom/2026-10-07/"
    "835d4f46bb9e3532a79e32aca9a408f59861640b31dc04718cdb507f5f8e429c/"
    "session-aware-priority-acceptance-inactive-superseding-candidate.json",
    "workspace/policies/instrument_identity_activation.json",
    "workspace/policies/session_calendar_activation.json",
    "workspace/instrument-identity-authority/source-packets/"
    "0e12b7133fa91305a07e734a35fb042bd903b3b8f3b6a259669ad0cd2d82cd93/"
    "us-equity-instrument-identity-current-v1.sources.json",
)
PAST_CRLF_EVIDENCE_PATH = (
    "workspace/research/provider-evidence/kiwoom/2026-08-14/session-aware-priority-acceptance.json"
)


def text_attribute(path: str) -> str:
    completed = subprocess.run(
        ["git", "check-attr", "text", "--", path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    output = completed.stdout.strip()
    prefix = f"{path}: text: "
    if not output.startswith(prefix):
        raise AssertionError(f"unexpected git check-attr output: {output!r}")
    return output[len(prefix):]


class GitAttributesAuthorityBytesTests(unittest.TestCase):
    def test_raw_byte_authority_files_are_excluded_from_conversion(self) -> None:
        for path in RAW_BYTE_PATHS:
            with self.subTest(path=path):
                self.assertTrue((REPO_ROOT / path).is_file())
                self.assertEqual(text_attribute(path), "unset")

    def test_past_crlf_evidence_keeps_text_conversion(self) -> None:
        self.assertTrue((REPO_ROOT / PAST_CRLF_EVIDENCE_PATH).is_file())
        self.assertEqual(text_attribute(PAST_CRLF_EVIDENCE_PATH), "set")


if __name__ == "__main__":
    unittest.main()
