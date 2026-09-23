# Import record — R2 pack + kernel (2026-09-10)

Source: `stallshark` bucket (R2, vault keys). Pristine copies kept in
`imports/`:
- `agi_bottleneck_intelligence_resource_pack_2026-09-10.zip` 53KB/36 files
- `postagi_worldstate_kernel_2026-09-10.zip` 107KB/46 files
Unpacked (flattened, single top level) to `imported/resource_pack/` and
`imported/postagi_kernel/` — MANIFEST.json sha256 verified 35/35 on 2026-09-10.
(Previously double-nested `imported/<x>/<x>/`; fixed, bridge + import_pack
paths updated.)

## Merged into live stores (dedupe keys noted)

- 22 frontier-lab events → `data/labs/commitments.json` (+20 new; 2
  watch-kinds routed to diggers/unknowns, not commitments). Dedupe: (lab,target).
- 11 diggers → `data/labs/diggers.json` (+9 new orgs at CLAIM; 7 proof-bars
  merged into existing Normal/Extropic entries). Dedupe: name substring.
- Kernel demo panel: stays vendored (`imported/postagi_kernel/.../data/`);
  `bneck2/kernel_bridge.py` loads it stdlib-side and declares the mapping.
  Native equivalents documented in `bridge.describe()`.

## Collectors: theirs vs ours

Pack collectors are ~300-600 byte stubs (URL builders). Ours
(`collectors/*.py`) are full fetch+parse with offline-tested parsers.
Kept ours; pack versions retained under `imported/` for reference.

## Schemas

Pack edge schema relations (REQUIRES/ENABLES/SUBSTITUTES/KILLED_BY/...)
are compatible with ours (DEPENDS_ON/CASCADE + PATENT_COVERED_BY/
REGULATED_BY). No migration needed; KILLED_BY maps to our kill_signals.

## Repo coverage: pack 60 vs local clones

Already had all S++ except pm-analysis (now cloned: `pm-analysis`).
New clones this round: `pm-analysis` (S++, MIT), `equibles` (market/filings),
`usaspending-mcp` (gov spending). Remaining 34 uncloned are mostly
pip-heavy infra (networkx, qlib, OpenBB, PyPSA, dowhy, river, tigramite,
cugraph — need package installs first) or A-tier tools queued in
`docs/RESOURCES.md`. Clone queue lives there; nothing silently dropped.
