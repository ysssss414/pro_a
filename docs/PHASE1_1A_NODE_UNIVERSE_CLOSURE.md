# Phase 1.1A AI Hardware Node Universe Closure

- Closure date: **2026-08-25**
- Branch: `phase1.1/ai-hardware-universe`
- Status: **COMPLETE**
- Scope: Node, alias, and approved structural `part_of` expansion only

## Objective

Close the Phase 1.1A AI Hardware expanded Node universe by reconciling the Sol Pro V2 staging candidates against the actual Production database, recording human decisions, qualifying a clean package on an isolated Production copy, and applying only that qualified package under a one-time explicit Production authorization.

Functional Relation validation and import are outside this closure and have not started.

## Sol Pro V2 staging input

- Package: `pro_a_ai_hardware_foundation_v2_final_20260818`
- Local staging source at review time: `D:\ej\材料\codex\get_knowledge\pro_a_v0_1\pro_a_ai_hardware_foundation_v2_final_20260818`
- Role: offline candidate input only
- Identity policy: exact canonical, exact alias, SQLite NOCASE, and Unicode NFKC/casefold checks only
- Prohibited identity mechanisms: embedding, semantic similarity, and fuzzy matching

The original staging package was never treated as a direct import payload. All Production-facing rows came from the later clean, human-approved, isolated-qualified package.

## Reconciliation summary

Actual-DB preflight evaluated **35** Node candidates against the Phase 1 frozen Production baseline.

| Disposition | Preflight | Final human decision |
|---|---:|---:|
| CREATE | 14 | 13 |
| REUSE | 5 | 5 |
| DEFER | 10 | 11 |
| REJECT | 2 | 2 |
| CROSS_DOMAIN_QUARANTINE | 4 | 4 |

- CREATE canonical collisions: **0**
- Alias collisions: **0**
- Primary Type conflicts: **0**
- All five REUSE candidates resolved uniquely to the same Production Node IDs used during isolated qualification.
- The clean package contained no DEFER, REJECT, or CROSS_DOMAIN_QUARANTINE Node and no functional Relation.

## Human adjudication summary

Human adjudication approved **13 CREATE** candidates and confirmed all **5 REUSE** decisions. `High-Frequency High-Speed Electronic Resin` moved from preflight CREATE to final DEFER. `Plate Heat Exchanger` and `Barium Titanate` remained DEFER under their explicit restrictions. Cross-domain and rejected candidates retained their preflight dispositions.

Alias decisions were also frozen:

- `Nickel Powder` permits `镍粉`; `MLCC镍粉` is prohibited.
- `Pump Laser` permits `泵浦激光器`; an alias identical to canonical name `Pump Laser` is prohibited.
- Other aliases that passed identity review were retained.

Only four structural Relations were approved. No usage-context relationship was converted into structural containment, and no additional `part_of` was inferred.

## Approved CREATE inventory

| Canonical name | Primary Type |
|---|---|
| PTFE Resin | Material |
| Spherical Silica Powder | Material |
| Quartz Glass Fabric | Material |
| Low-CTE Glass Fabric | Material |
| Electronic Glass Yarn | Material |
| Pump Laser | Product |
| Arrayed Waveguide Grating | Product |
| Gas Turbine | Equipment |
| Supercapacitor | Product |
| Tantalum Capacitor | Product |
| Nickel Powder | Material |
| MLCC Release Film | Material |
| MLCC Materials | Segment |

## Confirmed REUSE inventory

| Candidate | Type | Production Node ID | Resolved canonical name | Match |
|---|---|---|---|---|
| Hydrocarbon Resin | Material | `NODE_20260819_FC11C8E9` | Hydrocarbon Resin | EXACT_CANONICAL |
| Silica Powder | Material | `NODE_20260819_4B13EC49` | Silica Powder | EXACT_CANONICAL |
| Electronic Glass Fabric | Material | `NODE_20260814_36FDA0B6` | 电子布 | EXACT_ALIAS |
| Optical Circuit Switch | Product | `NODE_20260814_25C1F227` | OCS交换机 | EXACT_ALIAS |
| Thin-Film Lithium Niobate | Technology | `NODE_20260814_E67739ED` | 薄膜铌酸锂 | EXACT_ALIAS |

No REUSE decision was based on semantic similarity or fuzzy matching.

## Approved structural Relations

Exactly these four current structural Relations were added:

1. `Spherical Silica Powder --part_of--> Silica Powder`
2. `Pump Laser --part_of--> Optical Components`
3. `Arrayed Waveguide Grating --part_of--> Optical Components`
4. `MLCC Release Film --part_of--> MLCC Materials`

In particular, `Nickel Powder --part_of--> MLCC Materials` was not added. Quartz Glass Fabric, Low-CTE Glass Fabric, and Electronic Glass Yarn were not placed under PCB Materials solely because of PCB usage, and Gas Turbine was not placed under Facility Power Equipment solely because of AIDC usage.

## Deferred, rejected, and quarantine policy

These dispositions remain outside the Phase 1.1A payload and Production delta:

- DEFER (11): High-Frequency High-Speed Electronic Resin; Solid Oxide Fuel Cell; Polyphenylene Ether Resin; BMI Resin; ITLA; Optical Fiber Preform; Micro Thermoelectric Cooler; Gas Engine; Barium Titanate; Diamond Thermal Material; Plate Heat Exchanger.
- REJECT (2): CXL Controller; CXL Switch.
- CROSS_DOMAIN_QUARANTINE (4): Glass Core Substrate; Through-Glass Via; CoWoP Packaging; NAND Flash.

Policy constraints:

- DEFER requires a later explicit evidence/type/identity decision; approval of a neighboring Node does not restore a deferred candidate.
- Plate Heat Exchanger must not be aliased or reused as CDU Heat Exchanger and has no approved structural Relation.
- Barium Titanate remains deferred even though MLCC Materials was approved.
- CXL Controller and CXL Switch remain rejected because the V2 package supplied no valid audited Node Evidence; coverage mentions do not restore them.
- Cross-domain quarantine candidates must not be merged back into the AI Hardware universe without a separate domain review.

## Production import and receipt

The clean package was applied atomically after the Production precondition, schema, identity resolution, collisions, types, endpoints, and sidecar state were revalidated.

- Receipt: `workspace/phase1_1_ai_hardware_production_import_20260825/PRODUCTION_IMPORT_RECEIPT.json`
- Production path: `D:\ej\材料\codex\get_knowledge\pro_a_v0_1\workspace\pro_a.db`
- Pre-SHA-256: `8bce2b47df971e527de3552ca0415160868b258c0fcd4a8f6d2f20f40a60541c`
- Post-SHA-256: `8a4247b9da2c3d6f288f8a8af8519f33673bc45b5a4327a57c50436d39dd50b4`
- Atomic apply: **PASS**
- SQLite/FK and package integrity checks: **PASS**
- Idempotent Production rerun: **PASS** with 0 new Nodes, 0 new aliases, 0 new Relations, and unchanged post-SHA
- Exact rollback contract on isolated post-state copy: **PASS**
- Functional Relations written: **0**
- Current View delta: **0**

No workspace database, Production backup, isolated copy, or other large workspace artifact is part of this Git closure.

## Final Production counts

| Metric | Pre-import | Post-import |
|---|---:|---:|
| Nodes | 280 | 293 |
| Aliases | 706 | 737 |
| Node Relations | 177 | 181 |
| Current `part_of` | 170 | 174 |

## Acceptance decision

Phase 1.1A meets its Node-universe acceptance contract: the final human-approved inventory is resolved, the exact clean package is present in Production, all immediate integrity gates passed, the rerun is idempotent, the rollback contract is byte-exact, and no functional Relation was written.

`PHASE1_1A_NODE_UNIVERSE_COMPLETE = true`

`PHASE1_1B_FUNCTIONAL_RELATIONS_STARTED = false`

`PHASE1_1B_READY = true`

This closure does not authorize any additional Production write.
