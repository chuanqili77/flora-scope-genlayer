# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import re
from urllib.parse import quote
from genlayer import TreeMap, gl

MATCH = "https://api.gbif.org/v1/species/match?kingdom=Plantae&name="


def assignment(record: dict, name: str) -> int:
    if (record.get("kingdom") != "Plantae" or record.get("rank") != "SPECIES"
        or record.get("matchType") != "EXACT" or record.get("canonicalName") != name
        or record.get("confidence", 0) < 95):
        return 0
    status = record.get("status")
    key = record.get("usageKey") if status == "ACCEPTED" else record.get("acceptedUsageKey")
    if status not in ("ACCEPTED", "SYNONYM") or type(key) is not int or key <= 0:
        return 0
    return key


def agree(name: str) -> int:
    def observe() -> int:
        response = gl.nondet.web.get(MATCH + quote(name, safe=""))
        if response.status != 200 or not response.body or len(response.body) > 16384:
            raise gl.vm.UserError("GBIF match unavailable")
        return assignment(json.loads(response.body), name)

    return gl.eq_principle.strict_eq(observe)


class FloraScope(gl.Contract):
    curator: str
    concepts: TreeMap[str, str]

    def __init__(self):
        self.curator = str(gl.message.sender_address)

    @gl.public.write
    def enroll(self, name: str) -> int:
        if str(gl.message.sender_address) != self.curator:
            raise gl.vm.UserError("Only the curator can enroll taxa")
        if not re.fullmatch(r"[A-Z][a-z]{1,29} [a-z][a-z-]{1,39}", name):
            raise gl.vm.UserError("Provide a canonical plant binomial")
        key = agree(name)
        if not key:
            raise gl.vm.UserError("No exact plant species assignment")
        slot = str(key)
        if self.concepts.get(slot, ""):
            raise gl.vm.UserError("Accepted taxon already enrolled")
        self.concepts[slot] = json.dumps({
            "submitted_name": name, "accepted_key": key, "status": "ACTIVE",
        })
        return key

    @gl.public.write
    def review(self, key: int) -> str:
        slot = str(key)
        raw = self.concepts.get(slot, "")
        if not raw:
            raise gl.vm.UserError("Unknown concept")
        record = json.loads(raw)
        if record["status"] != "ACTIVE":
            raise gl.vm.UserError("Concept already quarantined")
        observed = agree(record["submitted_name"])
        if observed == key:
            return "ACTIVE"
        record["status"] = "QUARANTINED"
        record["observed_key"] = observed
        self.concepts[slot] = json.dumps(record)
        return "QUARANTINED"

    @gl.public.view
    def concept(self, key: int) -> str:
        return self.concepts.get(str(key), "")
