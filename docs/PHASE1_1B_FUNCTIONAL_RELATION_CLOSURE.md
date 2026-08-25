# Phase 1.1B AI Hardware Functional Relation Requalification Closure

- Closure date: **2026-08-25**
- Branch: `phase1.1/ai-hardware-universe`
- Status: **COMPLETE**
- Scope: evidence reconstruction, frozen-validator diagnosis, and human adjudication of the fixed 26-candidate functional Relation inventory

## Objective

Close Phase 1.1B by requalifying the existing Sol Pro V2 functional Relation candidates against the completed Phase 1.1A Node universe and the unchanged frozen Relation Evidence contract. The goal was to determine whether a safe import payload existed, not to force the creation of functional Relations.

This closure did not extract new candidates, change relation types or scopes, create formal Claims, weaken or bypass the validator, or write Production.

## Frozen candidate inventory

All **26** input candidates retained their original candidate ID, relation type, scope, and endpoints during automated processing. `R1F_0078` has a separately recorded human endpoint correction, but no candidate or Relation was automatically rewritten.

| Candidate | Frozen relation | B1 classification | Final disposition | Final basis |
|---|---|---|---|---|
| `R1F_0007` | `800V DC Power Distribution --applied_in--> Data Center Power Infrastructure` | RELATION_OVERSTATED | DEFER | Non-direct human defer |
| `R1F_0008` | `AI Accelerator --uses--> High Bandwidth Memory` | ENDPOINT_OR_GRANULARITY_REVIEW | DEFER | Non-direct human defer |
| `R1F_0018` | `AI Network Switch --uses--> Data Center Optical Transceiver` | NEEDS_HUMAN_INTERPRETATION | REJECT | `SOURCE_SUPPORTS_PHYSICAL_CONNECTION_NOT_USES` |
| `R1F_0032` | `AI Server PCB --uses--> High-Speed Low-Loss CCL` | ENDPOINT_OR_GRANULARITY_REVIEW | DEFER | Non-direct human defer |
| `R1F_0041` | `Co-Packaged Optics --uses--> External Laser Source` | RELATION_OVERSTATED | DEFER | Non-direct human defer |
| `R1F_0045` | `Coolant Distribution Unit --uses--> CDU Heat Exchanger` | DIRECT_AFTER_CONTEXT_EXPANSION | DEFER | `CONTRACT_CONSTRAINED_FALSE_NEGATIVE` |
| `R1F_0046` | `Coolant Distribution Unit --uses--> CDU Pump` | DIRECT_AFTER_CONTEXT_EXPANSION | DEFER | `CONTRACT_CONSTRAINED_FALSE_NEGATIVE` |
| `R1F_0053` | `Data Center Optical Transceiver --uses--> EML` | DIRECT_AFTER_CONTEXT_EXPANSION | DEFER | Claim context overstatement and frozen `uses` contract not satisfied |
| `R1F_0056` | `Data Center Optical Transceiver --uses--> Optical DSP` | RELATION_OVERSTATED | DEFER | Non-direct human defer |
| `R1F_0058` | `Data Center Optical Transceiver --uses--> Transimpedance Amplifier` | NEEDS_HUMAN_INTERPRETATION | DEFER | Non-direct human defer |
| `R1F_0071` | `Direct-to-Chip Liquid Cooling --uses--> Cold Plate` | ENDPOINT_OR_GRANULARITY_REVIEW | DEFER | Non-direct human defer |
| `R1F_0078` | `EML --uses--> InP Epitaxial Wafer` | ENDPOINT_OR_GRANULARITY_REVIEW | DEFER | Endpoint correction recorded; frozen `uses` contract not satisfied |
| `R1F_0089` | `High-Speed Low-Loss CCL --uses--> Low-Dk Glass Fabric` | DIRECT_AFTER_CONTEXT_EXPANSION | DEFER | `CONTRACT_CONSTRAINED_FALSE_NEGATIVE` |
| `R1F_0090` | `High-Speed Low-Loss CCL --uses--> Low-Profile Copper Foil` | NEEDS_HUMAN_INTERPRETATION | DEFER | Non-direct human defer |
| `R1F_0110` | `Near-Packaged Optics --applied_in--> AI Network Switch` | RELATION_OVERSTATED | DEFER | Non-direct human defer |
| `R1F_0132` | `Scale-Out Network --uses--> AI Network Switch` | DIRECT_AFTER_CONTEXT_EXPANSION | DEFER | `CONTRACT_CONSTRAINED_FALSE_NEGATIVE` |
| `R1F_0140` | `Silicon Photonics --applied_in--> Data Center Optical Transceiver` | RELATION_OVERSTATED | DEFER | Non-direct human defer |
| `AIH26F_0002` | `High-Speed Low-Loss CCL --uses--> Hydrocarbon Resin` | NEEDS_HUMAN_INTERPRETATION | DEFER | Non-direct human defer |
| `AIH26F_0004` | `High-Speed Low-Loss CCL --uses--> Silica Powder` | DIRECT_AFTER_CONTEXT_EXPANSION | DEFER | `CONTRACT_CONSTRAINED_FALSE_NEGATIVE` |
| `AIH26F_0005` | `High-Speed Low-Loss CCL --uses--> Spherical Silica Powder` | DIRECT_AFTER_CONTEXT_EXPANSION | DEFER | `CONTRACT_CONSTRAINED_FALSE_NEGATIVE` |
| `AIH26F_0006` | `High-Speed Low-Loss CCL --uses--> Quartz Glass Fabric` | NEEDS_HUMAN_INTERPRETATION | DEFER | Non-direct human defer |
| `AIH26F_0009` | `AI Cluster --uses--> Optical Circuit Switch` | DIRECT_AFTER_CONTEXT_EXPANSION | DEFER | `CONTRACT_CONSTRAINED_FALSE_NEGATIVE` |
| `AIH26F_0011` | `Data Center Optical Transceiver --uses--> Arrayed Waveguide Grating` | RELATION_OVERSTATED | DEFER | Non-direct human defer |
| `AIH26F_0014` | `AI Data Center --uses--> Gas Turbine` | DIRECT_AFTER_CONTEXT_EXPANSION | DEFER | `CONTRACT_CONSTRAINED_FALSE_NEGATIVE` |
| `AIH26F_0016` | `AI Server --uses--> Tantalum Capacitor` | DIRECT_AFTER_CONTEXT_EXPANSION | DEFER | `CONTRACT_CONSTRAINED_FALSE_NEGATIVE` |
| `AIH26F_0017` | `MLCC --uses--> Nickel Powder` | DIRECT_AFTER_CONTEXT_EXPANSION | DEFER | `CONTRACT_CONSTRAINED_FALSE_NEGATIVE` |

Inventory closure totals:

- Input functional candidates: **26**
- DEFER: **25**
- REJECT: **1**
- ACCEPT: **0**
- Functional Relations to import: **0**

## Evidence reconstruction result

Phase 1.1B.1 relocated each original source/evidence pointer and expanded only within a continuous, source-local paragraph, adjacent paragraph, table row/header, bullet block, or section-local span. It did not use document-level co-occurrence or outside knowledge as Relation evidence.

| B1 classification | Count |
|---|---:|
| DIRECT_AFTER_CONTEXT_EXPANSION | 11 |
| NEEDS_HUMAN_INTERPRETATION | 5 |
| INSUFFICIENT_EVIDENCE | 0 |
| RELATION_OVERSTATED | 6 |
| ENDPOINT_OR_GRANULARITY_REVIEW | 4 |

All 26 candidate endpoints resolved exactly against the Phase 1.1A Production Node/alias universe. B1 generated 11 draft Claim candidates for the direct group only; it created no formal Claim and wrote no database.

## Direct validation and validator rejection forensics

Phase 1.1B.2 classified 10 of the 11 direct draft Claim candidates as `CLAIM_CANDIDATE_PASS` and one, `R1F_0053`, as `CLAIM_CANDIDATE_REVIEW`. The 10 passing drafts were then submitted to the unchanged frozen Relation analyzer; all 10 returned `VALIDATOR_REJECT`.

Phase 1.1B.2A reproduced the exact validator results:

| Frozen rejection class | Count |
|---|---:|
| ENDPOINT_UNSUPPORTED | 8 |
| SEMANTIC_SUPPORT_INSUFFICIENT | 2 |
| DIRECTION_UNSUPPORTED | 0 |
| REVERSED_DIRECTION | 0 |
| NEGATED | 0 |
| OTHER | 0 |

The forensic comparison found that B1's evidence assessment was semantic, while the frozen analyzer independently requires exact Production canonical/alias forms for both endpoints plus a recognized semantic marker and safe direction representation in the relevant statement and evidence excerpt. A deterministic scan of continuous one-, two-, and three-unit source windows found no validator-compatible source span for any of the 10 candidates.

There was no `TRUE_SEMANTIC_REJECTION` and no `TRUE_DIRECTION_REJECTION`. The failure mode is recorded as a representation/contract mismatch, not authorization to change the validator. `VALIDATOR_CHANGE_REQUIRED` remained **false**.

## Contract-constrained false negatives

The 10 `CLAIM_CANDIDATE_PASS` plus `VALIDATOR_REJECT` candidates have final disposition **DEFER** with reason code `CONTRACT_CONSTRAINED_FALSE_NEGATIVE`.

Their expanded contexts support the candidate semantics, but no continuous, exact, source-faithful span satisfies the frozen dual-endpoint and semantic lexical contract. Because Phase 1.1B neither weakens the validator nor permits manual bypass, none can become an imported Relation. They are deferred rather than rejected because the forensics found no true semantic or direction rejection.

## Human adjudication

The remaining adjudication is frozen as follows:

- The 13 `NON_DIRECT_DEFER_RECOMMENDED` candidates remain **DEFER**.
- `R1F_0053` remains **DEFER**. Its source says that EML is a core optical chip in 800G/1.6T optical modules, but the draft Claim added short-reach and AI-data-center context, and the evidence does not directly satisfy the frozen `uses` semantic contract. No Relation is created.
- `R1F_0018` is **REJECT** with reason `SOURCE_SUPPORTS_PHYSICAL_CONNECTION_NOT_USES`. The rejection applies only to the proposed `AI Network Switch --uses--> Data Center Optical Transceiver` candidate; it does not mark the source's physical-connection fact as false.
- `R1F_0078` records the source-faithful endpoint correction from InP Epitaxial Wafer to **InP Substrate** (`NODE_20260817_51A6EB8B`), but its final Relation disposition is **DEFER**. The evidence says that EML places higher requirements on InP substrate; it does not pass the frozen `uses` semantic contract. No `EML --uses--> InP Substrate` Relation is generated, and the candidate is not converted to `depends_on` or any other relation type.

## Frozen contracts and write result

- Frozen validator changed: **no**
- Manual validator bypass: **no**
- Formal Claims created: **0**
- Functional Relations accepted: **0**
- Functional Relations written to Production: **0**
- Current View writes: **0**

The supporting read-only artifacts remain under:

- `workspace/phase1_1b_functional_relation_requalification_20260825/b1_evidence_reconstruction/`
- `workspace/phase1_1b_functional_relation_requalification_20260825/b2_direct_validation/`
- `workspace/phase1_1b_functional_relation_requalification_20260825/b2a_validator_forensics/`

## Production baseline unchanged

The Production database remained read-only throughout Phase 1.1B and was rechecked at closure:

| Metric | Value |
|---|---:|
| Nodes | 293 |
| Aliases | 737 |
| Node Relations | 181 |
| Current `part_of` | 174 |

- Production SHA-256: `8a4247b9da2c3d6f288f8a8af8519f33673bc45b5a4327a57c50436d39dd50b4`
- SQLite integrity check: **ok**
- Foreign-key violations: **0**
- Functional Relation writes: **0**

The Phase 1.1A Production import receipt remains at `workspace/phase1_1_ai_hardware_production_import_20260825/PRODUCTION_IMPORT_RECEIPT.json`.

## Acceptance decision

Phase 1.1B's objective was requalification, not forced Relation generation. The completed Phase 1.1A Node identity universe is sufficient to resolve every endpoint in the 26-candidate inventory, but the available source materials cannot form a safe functional Relation import payload under the frozen Evidence contract.

This is part of the known Phase 1 Relation Evidence / Generation backlog. It does not block completion of the Phase 1.1 AI Hardware Node Universe.

`PHASE1_1A_NODE_UNIVERSE_COMPLETE = true`

`PHASE1_1B_FUNCTIONAL_REQUALIFICATION_COMPLETE = true`

`PHASE1_1_FUNCTIONAL_RELATION_IMPORT_COUNT = 0`

`PHASE1_1_COMPLETE = true`

`PRODUCTION_WRITE_AUTHORIZED = false`
