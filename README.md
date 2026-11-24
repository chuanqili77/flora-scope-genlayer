# FloraScope

[Stable Studionet contract](https://explorer-studio.genlayer.com/address/0x24aB4f21d985548937a9b5f0Eb09219075416aaE) · [Deployment transaction](https://explorer-studio.genlayer.com/tx/0x35132df18a92123b516be95bee343e7015277c770537e369a5637fde72256152)

A plant checklist indexed by accepted GBIF taxon identifiers. A curator can
enroll a binomial written in the form `Genus species`. A historical synonym
and the accepted name resolve to the same slot, preventing the two labels from
inflating the species count. External users can recheck any active entry.

Validators independently query the [GBIF species match API](https://techdocs.gbif.org/en/openapi/v1/species#/Searching%20names/match). For this
checklist, only an exact, high-confidence Plantae species response with the
input canonical name is eligible. Accepted usages supply their usage key.
Synonyms supply their accepted usage key. Validators compare the normalized
key or the no-assignment result. HTTP failures abort without changing state.

| Call | Result |
| --- | --- |
| `enroll(name)` | Curator-only. Opens one ACTIVE entry for the agreed accepted key. |
| `review(key)` | Anyone can recheck an ACTIVE entry. If the accepted assignment changes or disappears, quarantine the entry under its original key. |
| `concept(key)` | Return the entry or an empty string. Use only ACTIVE entries in the current checklist. |

Quarantine is permanent. A changed taxonomy is reconciled by curating a new
accepted key. The contract preserves the original entry and never silently
moves it. This is a reconciliation of published taxonomy, not proof of a
physical specimen or acceptance by every taxonomic authority.

The [example](scenario.json) enrolls `Acacia dealbata`, then attempts to enroll
`Racosperma dealbatum` and reviews the accepted concept.

## Build and verify

Use Node.js 24 and Stable Studionet (chain ID 61999).

```sh
npm ci
python3 -B -m unittest discover -s tests -v
python3 -m pip install genvm-linter==0.11.0
genvm-lint check contracts/contract.py --json
npm run verify:live
```

The Python suite uses an in-memory SDK stub. The
[official lint result](evidence/genvm-lint.json) validates the declared SDK.
The [chain evidence](evidence/studionet.json) is independently checked by the
read-only verification command. It compares deployed source bytes, receipt
execution and finalized state.

In a separate working copy, `STUDIONET_FAUCET=1 npm run deploy` deploys a fresh
instance and exercises the exact calls in the scenario using a test wallet.
