"""Schema 1.2 Kiwoom Acceptance candidate materialization (I4 R6).

The pre-R6 version of this module pinned the one-time 08-26 -> 08-28
11 -> 15 symbol transition (active manifest 2994..., provider scope 9604...).
That state can no longer exist, so each property is re-expressed against the
current active authority found through the policy binding. Drift tests use a
synthetic predecessor written inside the evidence root, so they hold both
before and after a later activation.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
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
    policy_acceptance_binding,
    resolve_active_manifest,
)
from validate_kiwoom_session_aware_acceptance import validate_acceptance
from validate_kiwoom_session_aware_acceptance_candidate import (
    IMPLEMENTATION_DRIFT_PREFIX,
    PIN_SCOPE_RELATIVE_PATH,
    allowed_drift_for,
    normalized_sha256,
    ordered_policy_symbols,
    predecessor_implementation_drift,
    validate_candidate_acceptance,
)
from validate_skill_deployment import normalized_text_sha256
from validation_common import file_hash, load_json


ACTIVE_POLICY = ROOT / "workspace/policies/kiwoom-session-aware-priority-policy.json"
SOURCE_REGISTRY = ROOT / "workspace/policies/source_capabilities.json"
PIN_SCOPE = ROOT / PIN_SCOPE_RELATIVE_PATH
EVIDENCE_ROOT = ROOT / "workspace/research/provider-evidence/kiwoom"
MANIFEST_SCHEMA = SCHEMAS / "kiwoom-session-aware-acceptance-manifest.schema.json"
PRIORITY_SCHEMA = SCHEMAS / "kiwoom-session-aware-priority-policy.schema.json"
SOURCE_SCHEMA = SCHEMAS / "source-capability.schema.json"
GENERATED_AT = "2026-10-05T21:00:00+09:00"
BASE_COMMIT = "5dd739fd04e9b1852eb6712537a8e5fa72db9dbd"


def write_canonical(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))
    return path


class KiwoomAcceptanceCandidateMaterializationTest(unittest.TestCase):
    def build(self, **overrides):
        arguments = dict(
            active_priority_policy_path=ACTIVE_POLICY,
            provider_scope_policy_path=ACTIVE_POLICY,
            source_registry_path=SOURCE_REGISTRY,
            repo_root=ROOT,
            generated_at=GENERATED_AT,
            repository_base_commit=BASE_COMMIT,
        )
        arguments.update(overrides)
        return build_candidate_manifest(**arguments)

    def validate(self, manifest: dict, path: Path, policy: dict | None = None, **overrides) -> list[str]:
        arguments = dict(
            manifest=manifest,
            manifest_path=path,
            manifest_schema=MANIFEST_SCHEMA,
            provider_scope_policy=policy or load_json(ACTIVE_POLICY),
            provider_scope_policy_path=ACTIVE_POLICY,
            priority_schema=PRIORITY_SCHEMA,
            source_registry=load_json(SOURCE_REGISTRY),
            source_registry_path=SOURCE_REGISTRY,
            source_schema=SOURCE_SCHEMA,
            repo_root=ROOT,
        )
        arguments.update(overrides)
        return validate_candidate_acceptance(**arguments)

    def write_temp_manifest(self, manifest: dict, directory: str) -> Path:
        return write_canonical(Path(directory) / "candidate.json", manifest)

    def active_binding(self) -> str:
        return policy_acceptance_binding(load_json(ACTIVE_POLICY))

    # -- old test_01: exact inactive scope, no authority -------------------------------
    def test_01_candidate_is_exact_inactive_scope_from_active_policy(self):
        manifest, _, _ = self.build()
        expected = list(ordered_policy_symbols(load_json(ACTIVE_POLICY)))
        scope = manifest["candidate_governance"]["provider_scope"]
        self.assertEqual(expected, scope["symbols"])
        self.assertEqual(len(expected), scope["count"])
        self.assertEqual(15, len(expected))
        self.assertEqual("1.2", manifest["schema_version"])
        self.assertEqual("INACTIVE_SUPERSEDING_CANDIDATE", manifest["candidate_status"])
        self.assertFalse(manifest["activation_performed"])
        self.assertFalse(manifest["order_authority"])
        self.assertFalse(scope["order_authority"])
        self.assertEqual("none", manifest["quantity_authority"])
        self.assertIsNone(manifest["execution_quantity"])
        self.assertNotIn("authority_bindings", manifest)
        self.assertNotIn("provider_scope_contract", manifest)

    # -- old test_02: exact provider scope binding ------------------------------------
    def test_02_candidate_binds_provider_scope_by_normalized_hash(self):
        manifest, _, _ = self.build()
        governance = manifest["candidate_governance"]
        expected = normalized_sha256(ACTIVE_POLICY)
        self.assertEqual("NORMALIZED_TEXT_SHA256", governance["hash_mode"])
        self.assertEqual(expected, governance["provider_scope"]["provider_scope_policy_sha256"])
        self.assertEqual(expected, governance["authority_bindings"]["provider_scope_policy"]["sha256"])
        self.assertEqual("workspace/policies/kiwoom-session-aware-priority-policy.json",
                         governance["authority_bindings"]["provider_scope_policy"]["repository_path"])

    def test_03_same_inputs_materialize_same_bytes_and_id(self):
        first = self.build()
        second = self.build()
        self.assertEqual(first[1:], second[1:])
        self.assertEqual(first[2], hashlib.sha256(first[1]).hexdigest())

    # -- old test_03a: implementation bindings, now from the pin scope ------------------
    def test_03a_implementation_bindings_follow_the_pinned_scope(self):
        manifest, _, _ = self.build()
        pin_scope = load_json(PIN_SCOPE)
        self.assertEqual(set(pin_scope["required_implementation_paths"]), set(manifest["implementation_hashes"]))
        self.assertIn(PIN_SCOPE_RELATIVE_PATH, manifest["implementation_hashes"])
        for relative in pin_scope["required_implementation_paths"]:
            with self.subTest(relative=relative):
                self.assertEqual(normalized_text_sha256(ROOT / relative).lower(),
                                 manifest["implementation_hashes"][relative])
        for released in ("manage-us-stock-strategy/scripts/run_manual_portfolio_analysis.py",
                         "manage-us-stock-strategy/tests/test_manual_portfolio_analysis.py",
                         "manage-us-stock-strategy/scripts/materialize_kiwoom_session_aware_acceptance_candidate.py"):
            self.assertNotIn(released, manifest["implementation_hashes"])
        binding = manifest["candidate_governance"]["pin_scope"]
        self.assertEqual(PIN_SCOPE_RELATIVE_PATH, binding["repository_path"])
        self.assertEqual(pin_scope["pin_scope_id"], binding["pin_scope_id"])

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

    # -- old test_04: supersedes the active ID, now read from the policy ---------------
    def test_04_new_acceptance_id_differs_from_active_found_through_policy(self):
        manifest, _, candidate_sha = self.build()
        active_sha = self.active_binding()
        active_path = resolve_active_manifest(active_sha, EVIDENCE_ROOT)
        self.assertEqual(active_sha, normalized_sha256(active_path))
        self.assertEqual(active_sha, manifest["supersedes_acceptance_sha256"])
        self.assertEqual(active_sha, manifest["candidate_governance"]["authority_bindings"][
            "active_acceptance_manifest"]["sha256"])
        self.assertNotEqual(active_sha, candidate_sha)

    def test_05_materialized_candidate_passes_binding_validator(self):
        with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
            result = materialize_candidate(
                active_priority_policy_path=ACTIVE_POLICY,
                provider_scope_policy_path=ACTIVE_POLICY,
                source_registry_path=SOURCE_REGISTRY,
                repo_root=ROOT,
                output_root=Path(directory),
                generated_at=GENERATED_AT,
                repository_base_commit=BASE_COMMIT,
            )
            candidate_path = Path(result["candidate_path"])
            self.assertEqual(result["candidate_raw_sha256"], file_hash(candidate_path))
            self.assertEqual(result["candidate_raw_sha256"], normalized_sha256(candidate_path))
            self.assertEqual(result["candidate_raw_sha256"], candidate_path.parent.name)
            self.assertEqual([], self.validate(load_json(candidate_path), candidate_path))
            self.assertFalse(result["activation_performed"])
            self.assertFalse(result["order_authority"])

    def test_06_duplicate_scope_fails_closed(self):
        manifest, _, _ = self.build()
        policy = load_json(ACTIVE_POLICY)
        policy["provider_scopes"].append(deepcopy(policy["provider_scopes"][0]))
        with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
            path = self.write_temp_manifest(manifest, directory)
            errors = self.validate(manifest, path, policy)
        self.assertTrue(any("duplicate provider scope" in error for error in errors))

    def test_07_malformed_scope_fails_closed(self):
        manifest, _, _ = self.build()
        policy = load_json(ACTIVE_POLICY)
        policy["provider_scopes"].append("malformed")
        with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
            path = self.write_temp_manifest(manifest, directory)
            errors = self.validate(manifest, path, policy)
        self.assertTrue(any("provider scope malformed" in error for error in errors))

    def test_08_excluded_symbols_fail_closed(self):
        for excluded in ("BRK.B", "BRKb", "COST"):
            with self.subTest(excluded=excluded):
                manifest, _, _ = self.build()
                policy = load_json(ACTIVE_POLICY)
                policy["provider_scopes"][-1]["ticker"] = excluded
                with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
                    path = self.write_temp_manifest(manifest, directory)
                    errors = self.validate(manifest, path, policy)
                self.assertTrue(errors)

    # -- old test_09: authority binding mismatch, now on the normalized binding ----------
    def test_09_authority_binding_mismatch_fails_closed(self):
        manifest, _, _ = self.build()
        manifest["candidate_governance"]["authority_bindings"]["source_registry"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
            path = self.write_temp_manifest(manifest, directory)
            errors = self.validate(manifest, path)
        self.assertIn("candidate binding normalized hash mismatch: source_registry", errors)

    def test_09a_raw_crlf_implementation_binding_fails_production_contract(self):
        manifest, _, _ = self.build()
        relative = "manage-us-stock-strategy/scripts/kiwoom_runtime_bridge.py"
        text = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
        crlf_raw = hashlib.sha256(text.replace(b"\n", b"\r\n")).hexdigest()
        self.assertNotEqual(crlf_raw, manifest["implementation_hashes"][relative])
        manifest["implementation_hashes"][relative] = crlf_raw
        with tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT) as directory:
            path = self.write_temp_manifest(manifest, directory)
            errors = self.validate(manifest, path)
        self.assertIn(f"implementation hash mismatch: {relative}", errors)

    def test_09b_candidate_projects_cleanly_through_production_validator(self):
        manifest, _, _ = self.build()
        projected_policy = load_json(ACTIVE_POLICY)
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
                manifest_schema=MANIFEST_SCHEMA,
                priority_policy=projected_policy,
                priority_schema=PRIORITY_SCHEMA,
                source_registry=projected_registry,
                source_schema=SOURCE_SCHEMA,
                repo_root=ROOT,
            )
        self.assertEqual(len(load_json(PIN_SCOPE)["required_implementation_paths"]),
                         len(manifest["implementation_hashes"]))
        self.assertEqual([], errors)

    # -- old test_10: the active acceptance is valid except explicitly allowed drift -----
    def test_10_active_acceptance_is_valid_except_allowed_drift(self):
        active_sha = self.active_binding()
        active_path = resolve_active_manifest(active_sha, EVIDENCE_ROOT)
        active = load_json(active_path)
        errors = validate_acceptance(
            manifest=active,
            manifest_path=active_path,
            manifest_schema=MANIFEST_SCHEMA,
            priority_policy=load_json(ACTIVE_POLICY),
            priority_schema=PRIORITY_SCHEMA,
            source_registry=load_json(SOURCE_REGISTRY),
            source_schema=SOURCE_SCHEMA,
            repo_root=ROOT,
        )
        allowed = allowed_drift_for(load_json(PIN_SCOPE), active_sha)
        self.assertEqual([], [error for error in errors
                              if error not in {IMPLEMENTATION_DRIFT_PREFIX + path for path in allowed}])
        drift, drift_errors = predecessor_implementation_drift(active, ROOT)
        self.assertEqual([], drift_errors)
        self.assertEqual(sorted(IMPLEMENTATION_DRIFT_PREFIX + item["repository_path"] for item in drift),
                         sorted(errors))
        manifest, _, _ = self.build()
        self.assertEqual(drift, manifest["candidate_governance"]["predecessor_implementation_drift"])

    def test_11_output_outside_canonical_root_is_denied(self):
        with self.assertRaises(AcceptanceCandidateMaterializationError):
            materialize_candidate(
                active_priority_policy_path=ACTIVE_POLICY,
                provider_scope_policy_path=ACTIVE_POLICY,
                source_registry_path=SOURCE_REGISTRY,
                repo_root=ROOT,
                output_root=ROOT / "manage-us-stock-strategy/tests",
                generated_at=GENERATED_AT,
                repository_base_commit=BASE_COMMIT,
            )


class SyntheticPredecessorDriftTest(unittest.TestCase):
    """New R6 negatives: only allowed implementation drift on the bound predecessor may pass."""

    DRIFT_PATH = "manage-us-stock-strategy/scripts/kiwoom_runtime_bridge.py"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=EVIDENCE_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        active_sha = policy_acceptance_binding(load_json(ACTIVE_POLICY))
        predecessor = load_json(resolve_active_manifest(active_sha, EVIDENCE_ROOT))
        hashes = {}
        for relative in predecessor["implementation_hashes"]:
            hashes[relative] = normalized_sha256(ROOT / relative)
        hashes[self.DRIFT_PATH] = "0" * 64  # one simulated predecessor drift
        predecessor["implementation_hashes"] = hashes
        self.predecessor_path = write_canonical(self.root / "predecessor" / "acceptance.json", predecessor)
        self.predecessor_sha = normalized_sha256(self.predecessor_path)
        self.policy = load_json(ACTIVE_POLICY)
        self.policy["acceptance_evidence"]["session_aware_acceptance_manifest_sha256"] = self.predecessor_sha
        for scope in self.policy["provider_scopes"]:
            scope["acceptance_artifact_hash"] = self.predecessor_sha
        self.registry = load_json(SOURCE_REGISTRY)
        next(row for row in self.registry["providers"]
             if row.get("provider") == "kiwoom_rest")["acceptance_artifact_sha256"] = self.predecessor_sha
        self.pin = load_json(PIN_SCOPE)
        self.pin["allowed_drift_predecessor_sha256"] = self.predecessor_sha
        self.pin["allowed_predecessor_drift"] = [self.DRIFT_PATH]

    def write_inputs(self):
        return (write_canonical(self.root / "policy.json", self.policy),
                write_canonical(self.root / "registry.json", self.registry),
                write_canonical(self.root / "pin-scope.json", self.pin))

    def build(self, provider_scope_policy_path=None):
        policy_path, registry_path, pin_path = self.write_inputs()
        return build_candidate_manifest(
            active_priority_policy_path=policy_path,
            provider_scope_policy_path=provider_scope_policy_path or policy_path,
            source_registry_path=registry_path,
            repo_root=ROOT,
            generated_at=GENERATED_AT,
            repository_base_commit=BASE_COMMIT,
            pin_scope_path=pin_path,
            evidence_root=self.root,
        ), (policy_path, registry_path, pin_path)

    def validate(self, manifest, paths):
        policy_path, registry_path, pin_path = paths
        candidate_path = write_canonical(self.root / "candidate" / "candidate.json", manifest)
        return validate_candidate_acceptance(
            manifest=manifest, manifest_path=candidate_path, manifest_schema=MANIFEST_SCHEMA,
            provider_scope_policy=load_json(policy_path), provider_scope_policy_path=policy_path,
            priority_schema=PRIORITY_SCHEMA, source_registry=load_json(registry_path),
            source_registry_path=registry_path, source_schema=SOURCE_SCHEMA, repo_root=ROOT,
            pin_scope_path=pin_path,
        )

    def test_12_allowed_drift_is_recorded_and_validates(self):
        (manifest, _, _), paths = self.build()
        drift = manifest["candidate_governance"]["predecessor_implementation_drift"]
        self.assertEqual([{"repository_path": self.DRIFT_PATH, "pinned_sha256": "0" * 64,
                           "current_sha256": normalized_sha256(ROOT / self.DRIFT_PATH)}], drift)
        self.assertEqual(self.predecessor_sha, manifest["supersedes_acceptance_sha256"])
        self.assertEqual([], self.validate(manifest, paths))

    def test_13_drift_outside_the_allowed_list_fails_closed(self):
        self.pin["allowed_predecessor_drift"] = []
        with self.assertRaisesRegex(AcceptanceCandidateMaterializationError, "beyond allowed drift"):
            self.build()

    def test_14_allowance_bound_to_another_predecessor_excuses_nothing(self):
        self.pin["allowed_drift_predecessor_sha256"] = "1" * 64
        with self.assertRaisesRegex(AcceptanceCandidateMaterializationError, "beyond allowed drift"):
            self.build()

    def test_15_non_drift_active_error_fails_closed(self):
        self.policy["transition_status"] = "KIWOOM_PRIMARY_TRANSITION_BLOCKED"
        with self.assertRaisesRegex(AcceptanceCandidateMaterializationError, "beyond allowed drift"):
            self.build()

    def test_16_reordered_or_changed_scope_fails_closed(self):
        reordered = deepcopy(self.policy)
        reordered["provider_scopes"].reverse()
        path = write_canonical(self.root / "reordered.json", reordered)
        with self.assertRaisesRegex(AcceptanceCandidateMaterializationError, "active ordered scope"):
            self.build(provider_scope_policy_path=path)

    def test_17_split_policy_or_registry_binding_fails_closed(self):
        self.policy["provider_scopes"][0]["acceptance_artifact_hash"] = "2" * 64
        with self.assertRaisesRegex(AcceptanceCandidateMaterializationError, "binding split"):
            self.build()
        self.setUp()
        next(row for row in self.registry["providers"]
             if row.get("provider") == "kiwoom_rest")["acceptance_artifact_sha256"] = "2" * 64
        with self.assertRaisesRegex(AcceptanceCandidateMaterializationError, "source registry"):
            self.build()

    def test_18_pin_scope_must_pin_itself(self):
        self.pin["required_implementation_paths"].remove(PIN_SCOPE_RELATIVE_PATH)
        with self.assertRaisesRegex(AcceptanceCandidateMaterializationError, "pin scope invalid"):
            self.build()

    def test_19_validator_rejects_tampered_drift_record_and_legacy_blocks(self):
        (manifest, _, _), paths = self.build()
        tampered = deepcopy(manifest)
        tampered["candidate_governance"]["predecessor_implementation_drift"] = []
        self.assertIn("candidate predecessor drift record mismatch", self.validate(tampered, paths))
        legacy = deepcopy(manifest)
        legacy["authority_bindings"] = {}
        self.assertTrue(any("legacy raw binding block" in error for error in self.validate(legacy, paths)))
        shrunk = deepcopy(manifest)
        shrunk["implementation_hashes"].pop(PIN_SCOPE_RELATIVE_PATH)
        self.assertIn("candidate required implementation path set mismatch", self.validate(shrunk, paths))
        widened = deepcopy(manifest)
        widened["candidate_governance"]["provider_scope"]["symbols"].append("COST")
        widened["candidate_governance"]["provider_scope"]["count"] += 1
        self.assertIn("candidate provider scope contract symbols mismatch", self.validate(widened, paths))
        authority = deepcopy(manifest)
        authority["quantity_authority"] = "full"
        self.assertTrue(self.validate(authority, paths))

    def test_20_validator_rejects_unallowed_drift_even_with_a_matching_record(self):
        (manifest, _, _), paths = self.build()
        self.pin["allowed_predecessor_drift"] = []
        write_canonical(self.root / "pin-scope.json", self.pin)
        manifest["candidate_governance"]["pin_scope"]["sha256"] = normalized_sha256(self.root / "pin-scope.json")
        errors = self.validate(manifest, paths)
        self.assertIn(f"predecessor drift not allowed: {self.DRIFT_PATH}", errors)
        self.assertTrue(any(error.startswith("active Acceptance invalid beyond allowed drift") for error in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
