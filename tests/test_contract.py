import json
import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

class UserError(Exception):
    pass

sdk = types.ModuleType("genlayer")
sdk.TreeMap = dict
sdk.u256 = int
sdk.gl = types.SimpleNamespace(
    Contract=object, vm=types.SimpleNamespace(UserError=UserError),
    message=types.SimpleNamespace(sender_address="lab"),
    public=types.SimpleNamespace(view=lambda fn: fn, write=lambda fn: fn),
    eq_principle=types.SimpleNamespace(strict_eq=lambda fn: fn()),
    nondet=types.SimpleNamespace(web=types.SimpleNamespace()),
)
with patch.dict(sys.modules, {"genlayer": sdk}):
    contract = runpy.run_path(str(Path(__file__).resolve().parents[1] / "contracts/contract.py"))


class CatalogTests(unittest.TestCase):
    def setUp(self):
        sdk.gl.message.sender_address = "lab"
        self.catalog = contract["FloraScope"]()
        self.catalog.concepts = {}

    def upstream(self, name, key, alias=False, kind="EXACT"):
        payload = {
            "kingdom": "Plantae", "rank": "SPECIES", "matchType": kind,
            "canonicalName": name, "confidence": 100,
            "status": "SYNONYM" if alias else "ACCEPTED", "usageKey": 70 if alias else key,
        }
        if alias:
            payload["acceptedUsageKey"] = key
        sdk.gl.nondet.web.get = lambda url: types.SimpleNamespace(
            status=200, body=json.dumps(payload).encode(),
        )

    def test_alias_cannot_create_a_second_active_entry(self):
        self.upstream("Acacia dealbata", 50)
        self.assertEqual(self.catalog.enroll("Acacia dealbata"), 50)
        self.upstream("Racosperma dealbatum", 50, alias=True)
        with self.assertRaisesRegex(UserError, "already enrolled"):
            self.catalog.enroll("Racosperma dealbatum")
        self.assertEqual(self.catalog.concept(70), "")

    def test_remapping_is_quarantined(self):
        self.upstream("Acacia dealbata", 50)
        self.catalog.enroll("Acacia dealbata")
        self.assertEqual(self.catalog.review(50), "ACTIVE")
        self.upstream("Acacia dealbata", 51)
        self.assertEqual(self.catalog.review(50), "QUARANTINED")
        self.assertEqual(json.loads(self.catalog.concept(50))["observed_key"], 51)
        with self.assertRaisesRegex(UserError, "already quarantined"):
            self.catalog.review(50)
        self.assertEqual(self.catalog.concept(51), "")

    def test_fuzzy_results_and_noncurator_cannot_write(self):
        self.upstream("Acacia dealbata", 50, kind="FUZZY")
        with self.assertRaisesRegex(UserError, "No exact"):
            self.catalog.enroll("Acacia dealbata")
        sdk.gl.message.sender_address = "stranger"
        with self.assertRaisesRegex(UserError, "Only the curator"):
            self.catalog.enroll("Acacia dealbata")
        self.assertEqual(self.catalog.concept(50), "")
