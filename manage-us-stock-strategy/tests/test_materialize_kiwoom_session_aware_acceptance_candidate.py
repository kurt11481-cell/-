from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
SCHEMAS = ROOT / "manage-us-stock-strategy" / "schemas"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from authority_artifact_io import canonical_json_bytes
from materialize_kiwoom_session_aware_acceptance_candidate import (
    AcceptanceCandidateMaterializationError,
    build_candidate_manifest,
    materialize_candidate,
)
from validate_kiwoom_session_aware_acceptance import validate_acceptance
from validate_kiwoom_session_aware_acceptance_candidate import (
    EXPECTED_PROVIDER_SCOPE,
    REQUIRED_IMPLEMENTATION_PATHS,
    validate_candidate_acceptance,
)
from validate_skill_deployment import normalized_text_sha256
from validation_common import file_hash, load_json


ACTIVE_MANIFEST = (
    ROOT
    / "workspace/research/provider-evidence/kiwoom/2026-08-26"
    / "session-aware-priority-acceptance-k2-signed-cur-prc-675a7ee-inactive-candidate.json"
)
ACTIVE_POLICY = ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json"
PROVIDER_SCOPE_POLICY = (
    ROOT
    / "workspace/research/provider-evidence/kiwoom/2026-08-28"
    / "kiwoom-session-aware-priority-policy-pgr-jpm-cme-v-inactive-superseding-candidate.json"
)
SOURCE_REGISTRY = ROOT / "workspace/policies/source_capabilities.json"
EVIDENCE_ROOT = ROOT / "workspace/research/provider-evidence/kiwoom"
GENERATED_AT = "2026-08-28T21:00:00+09:00"
BASE_COMMIT = "10569eee1d69b5d0d561165de363a0ba103d99ee"


class KiwoomAcceptanceCandidateMaterializationTest(unittest.TestCase):
    def build(self):
        return build_candidate_manifest(
            active_manifest_path=ACTIVE_MANIFEST,
            active_priority_policy_path=ACTIVE_POLICY,
            provider_scope_policy_path=PROVIDER_SCOPE_POLICY,
            source_registry_path=SOURCE_REGISTRY,
            repo_root=ROOT,
            generated_at=GENERATED_AT,
            repository_base_commit=BASE_COMMIT,
        )

    def validate(self, manifest: dict, path: Path, policy: dict | None = None) -> list[str]:
        return validate_candidate_acceptance(
            manifest=manifest,
            manifest_path=path,
            manifest_schema=SCHEMAS / "kiwoom-session-aware-acceptance-manifest.schema.json",
            provider_scope_policy=policy or load_json(PROVIDER_SCOPE_POLICY),
            provider_scope_policy_path=PROVIDER_SCOPE_POLICY,
            priority_schema=SCHEMAS / "kiwoom-session-aware-priority-policy.schema.json",
            source_registry=load_json(SOURCE_REGISTRY),
            source_registry_path=SOURCE_REGISTRY,
            source_schema=SCHEMAS / "source-capability.schema.json",
            repo_root=ROOT,
        )

    def write_temp_manifest(self, manifest: dict, directory: str) -> Path:
        path = Path(directory) / "candidate.json"
        path.write_bytes(canonical_json_bytes(manifest))
        return path

    def test_01_candidate_is_exact_inactive_fifteen_symbol_authority(self):
        manifest, _, _ = self.build()
        contract = manifest["provider_scope_contract"]
        self.assertEqual(15, contract["count"])
        self.assertEqual(list(EXPECTED_PROVIDER_SCOPE), contract["symbols"])
        self.assertEqual("INACTIVE_SUPERSEDING_CANDIDATE", manifest["candidate_status"])
        self.assertFalse(manifest["activation_performed"])
        self.assertFalse(manifest["order_authority"])
        self.assertEqual("none", manifest["quantity_authority"])
        self.assertIsNone(manifest["execution_quantity"])

    def test_02_candidate_binds_exact_provider_scope_raw_sha(self):
        manifest, _, _ = self.build()
        expected = "9604570d9fa1b21095bd03b2c3ca7aee4cd1ba12308ea3fff8c2829342befa29"
        self.assertEqual(expected, file_hash(PROVIDER_SCOPE_POLICY))
        self.assertEqual(expected, manifest["provider_scope_contract"]["provider_scope_policy_raw_sha256"])
        self.assertEqual(expected, manifest["authority_bindings"]["provider_scope_policy"]["raw_sha256"])

    def test_03_same_inputs_materialize_same_bytes_and_id(self):
        first = self.build()
        second = self.build()
        self.assertEqual(first[1:], second[1:])
        self.assertEqual(first[2], hashlib.sha256(first[1]).hexdigest())

    def test_03a_implementation_bindings_use_production_normalized_text_hash(self):
        manifest, _, _ = self.build()
        self.assertEqual(set(REQUIRED_IMPLEMENTATION_PATHS), set(manifest["implementation_hashes"]))
        for relative in REQUIRED_IMPLEMENTATION_PATHS:
            with self.subTest(relative=relative):
                self.assertEqual(
                    normalized_text_sha256(ROOT / relative).lower(),
                    manifest["implementation_hashes"][relative],
                )

    def test_03b_crlf_lf_and_bom_share_the_production_hash(self):
        with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
            temp_root = Path(directory)
            lf = temp_root / "lf.txt"
            crlf = temp_root / "crlf.txt"
            bom_crlf = temp_root / "bom-crlf.txt"
            lf.write_bytes(b"alpha\nbeta\n")
            crlf.write_bytes(b"alpha\r\nbeta\r\n")
            bom_crlf.write_bytes(b"\xef\xbb\xbfalpha\r\nbeta\r\n")
            self.assertNotEqual(file_hash(lf), file_hash(crlf))
            self.assertNotEqual(file_hash(crlf), file_hash(bom_crlf))
            self.assertEqual(normalized_text_sha256(lf), normalized_text_sha256(crlf))
            self.assertEqual(normalized_text_sha256(lf), normalized_text_sha256(bom_crlf))

    def test_04_new_acceptance_id_differs_from_active(self):
        manifest, _, candidate_sha = self.build()
        active_sha = "2994192ec8e370607f60661758a69777b150d510fe841d759c936b24fea0e295"
        self.assertEqual(active_sha, file_hash(ACTIVE_MANIFEST))
        self.assertEqual(active_sha, manifest["supersedes_acceptance_sha256"])
        self.assertNotEqual(active_sha, candidate_sha)

    def test_05_materialized_candidate_passes_binding_validator(self):
        with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
            result = materialize_candidate(
                active_manifest_path=ACTIVE_MANIFEST,
                active_priority_policy_path=ACTIVE_POLICY,
                provider_scope_policy_path=PROVIDER_SCOPE_POLICY,
                source_registry_path=SOURCE_REGISTRY,
                repo_root=ROOT,
                output_root=Path(directory),
                generated_at=GENERATED_AT,
                repository_base_commit=BASE_COMMIT,
            )
            candidate_path = Path(result["candidate_path"])
            self.assertEqual(result["candidate_raw_sha256"], file_hash(candidate_path))
            self.assertEqual(result["candidate_raw_sha256"], candidate_path.parent.name)
            self.assertEqual([], self.validate(load_json(candidate_path), candidate_path))

    def test_06_duplicate_scope_fails_closed(self):
        manifest, _, _ = self.build()
        policy = load_json(PROVIDER_SCOPE_POLICY)
        policy["provider_scopes"].append(deepcopy(policy["provider_scopes"][0]))
        with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
            path = self.write_temp_manifest(manifest, directory)
            errors = self.validate(manifest, path, policy)
        self.assertTrue(any("duplicate provider scope" in error for error in errors))

    def test_07_malformed_scope_fails_closed(self):
        manifest, _, _ = self.build()
        policy = load_json(PROVIDER_SCOPE_POLICY)
        policy["provider_scopes"].append("malformed")
        with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
            path = self.write_temp_manifest(manifest, directory)
            errors = self.validate(manifest, path, policy)
        self.assertTrue(any("provider scope malformed" in error for error in errors))

    def test_08_excluded_symbols_fail_closed(self):
        for excluded in ("BRK.B", "BRKb", "COST"):
            with self.subTest(excluded=excluded):
                manifest, _, _ = self.build()
                policy = load_json(PROVIDER_SCOPE_POLICY)
                policy["provider_scopes"][-1]["ticker"] = excluded
                with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
                    path = self.write_temp_manifest(manifest, directory)
                    errors = self.validate(manifest, path, policy)
                self.assertTrue(errors)

    def test_09_raw_binding_mismatch_fails_closed(self):
        manifest, _, _ = self.build()
        manifest["authority_bindings"]["source_registry"]["raw_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
            path = self.write_temp_manifest(manifest, directory)
            errors = self.validate(manifest, path)
        self.assertIn("candidate binding raw hash mismatch: source_registry", errors)

    def test_09a_raw_only_implementation_binding_fails_production_contract(self):
        manifest, _, _ = self.build()
        relative = next(
            relative
            for relative in REQUIRED_IMPLEMENTATION_PATHS
            if file_hash(ROOT / relative) != normalized_text_sha256(ROOT / relative).lower()
        )
        manifest["implementation_hashes"][relative] = file_hash(ROOT / relative)
        with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
            path = self.write_temp_manifest(manifest, directory)
            errors = self.validate(manifest, path)
        self.assertIn(f"implementation hash mismatch: {relative}", errors)

    def test_09b_candidate_projects_cleanly_through_production_validator(self):
        manifest, _, _ = self.build()
        projected_policy = load_json(PROVIDER_SCOPE_POLICY)
        projected_registry = load_json(SOURCE_REGISTRY)
        with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
            path = self.write_temp_manifest(manifest, directory)
            projected_acceptance_sha = normalized_text_sha256(path).lower()
            projected_policy["acceptance_evidence"][
                "session_aware_acceptance_manifest_sha256"
            ] = projected_acceptance_sha
            for scope in projected_policy["provider_scopes"]:
                scope["acceptance_artifact_hash"] = projected_acceptance_sha
            kiwoom = next(
                row
                for row in projected_registry["providers"]
                if row.get("provider") == "kiwoom_rest"
            )
            kiwoom["acceptance_artifact_sha256"] = projected_acceptance_sha
            errors = validate_acceptance(
                manifest=manifest,
                manifest_path=path,
                manifest_schema=SCHEMAS / "kiwoom-session-aware-acceptance-manifest.schema.json",
                priority_policy=projected_policy,
                priority_schema=SCHEMAS / "kiwoom-session-aware-priority-policy.schema.json",
                source_registry=projected_registry,
                source_schema=SCHEMAS / "source-capability.schema.json",
                repo_root=ROOT,
            )
        self.assertEqual(16, len(manifest["implementation_hashes"]))
        self.assertEqual([], errors)

    def test_10_current_active_acceptance_remains_officially_valid(self):
        errors = validate_acceptance(
            manifest=load_json(ACTIVE_MANIFEST),
            manifest_path=ACTIVE_MANIFEST,
            manifest_schema=SCHEMAS / "kiwoom-session-aware-acceptance-manifest.schema.json",
            priority_policy=load_json(ACTIVE_POLICY),
            priority_schema=SCHEMAS / "kiwoom-session-aware-priority-policy.schema.json",
            source_registry=load_json(SOURCE_REGISTRY),
            source_schema=SCHEMAS / "source-capability.schema.json",
            repo_root=ROOT,
        )
        self.assertEqual([], errors)

    def test_11_output_outside_canonical_root_is_denied(self):
        with self.assertRaises(AcceptanceCandidateMaterializationError):
            materialize_candidate(
                active_manifest_path=ACTIVE_MANIFEST,
                active_priority_policy_path=ACTIVE_POLICY,
                provider_scope_policy_path=PROVIDER_SCOPE_POLICY,
                source_registry_path=SOURCE_REGISTRY,
                repo_root=ROOT,
                output_root=ROOT / "manage-us-stock-strategy/tests",
                generated_at=GENERATED_AT,
                repository_base_commit=BASE_COMMIT,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
