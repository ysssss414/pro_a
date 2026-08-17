# Relation Semantics — Working Specification

Status: **working specification, not frozen**

This document records the current intended meaning of Relation types and known ambiguity areas. It is deliberately separate from `REQUIREMENTS_FROZEN.md` so that R1 evidence can still refine ontology details before anything is frozen.

## General rules

- Relation direction is semantic, not textual order.
- A Relation Candidate must be supported by Relation-specific Evidence.
- Node co-occurrence, thematic relevance or ordinary Claim↔Node linkage is not sufficient Evidence for a Relation.
- If Evidence cannot determine endpoints, relation type or direction safely, conservative rejection is preferred.
- Relation scope is part of Proposal identity when it changes the meaning of the relationship.
- Entity / Product / Technology granularity should not be silently substituted merely because names are related.

## Current relation types

### `part_of`

Meaning: `from_node` is structurally contained in, belongs to, or is a component/subcategory of `to_node`.

Typical examples:

- EML `part_of` optical communication component universe, if the Node hierarchy has explicitly adopted that taxonomy.
- A Segment `part_of` an Industry.

Special rule: this is the only current Relation type allowed to exist without Relation-specific Evidence when created through the confirmed structural seed / hierarchy path.

Common confusion:

- “used in” is not automatically `part_of`.
- supplier/customer relationships are not `part_of`.

### `upstream_of`

Meaning: `from_node` is upstream of `to_node` in a value chain or dependency chain.

This is a structural economic / industrial-chain relation, not merely chronological precedence.

Common confusion:

- A company supplying a product does not automatically imply the company itself is globally `upstream_of` every application of that product.
- `supplies` is more specific when Evidence names an actual supply relationship.

### `supplies`

Working meaning: `from_node` supplies goods, materials, components, capacity or other deliverables to `to_node` within the stated scope.

Direction:

```text
supplier → recipient
```

Examples:

- “Beta supplies HBM to Alpha” → Beta `supplies` Alpha, subject to endpoint ontology and scope.
- “HBM is supplied to Alpha by Beta” has the same semantic direction.

Open ontology question for R1:

- When Evidence only says “Company A supplies Product X” without naming a recipient, should the graph represent `Company A → Product X` as `supplies`, use `produces`, or not create a `supplies` Relation at all?
- Product→Entity and Entity→Entity supply representations need empirical review before freezing endpoint compatibility.

### `produces`

Working meaning: `from_node` manufactures, fabricates or produces `to_node`.

Direction:

```text
producer → produced object
```

Examples:

- “Company A produces EML chips” → Company A `produces` EML, if both endpoints are valid Nodes and Evidence indicates actual production rather than research / validation / planned capability.

Insufficient Evidence examples:

- “Company A is developing EML” does not necessarily prove current `produces`.
- “Company A is validating EML” does not prove production.
- “Company A can potentially manufacture EML” may remain Judgment / capability Evidence rather than a formal current `produces` Relation.

### `uses`

Working meaning: `from_node` directly uses, adopts, integrates or depends on `to_node` as an input / component / technology within scope.

Direction:

```text
user / consuming object → used object
```

Examples:

- Rubin GPU `uses` HBM4.
- A specific product may `use` a technology or material.

Open granularity question for R1:

- Prefer the most Evidence-faithful endpoint: Product `uses` Material may be more precise than Company `uses` Material when Evidence explicitly concerns one product generation.
- Do not silently lift Product-level Evidence to an Entity-wide Relation.

### `applied_in`

Working meaning: `from_node` is applied in, deployed in or used in `to_node` as an application context.

Direction:

```text
technology / product / material → application context
```

Common confusion:

- `uses` often points from the consuming object to the input.
- `applied_in` points from the technology / product toward where it is applied.
- The two can represent inverse-looking language but are not assumed to be formal inverses unless the ontology later freezes that rule.

### `substitutes`

Working meaning: `from_node` can replace, displace or act as a substitute for `to_node` in a defined use case / scope.

Direction:

```text
substitute → incumbent / replaced object
```

Requirements:

- Evidence should indicate actual substitutability, not merely competition or similarity.
- Scope is often material because two products may substitute in one application but not generally.

### `regulated_by`

Meaning: `from_node` is governed, constrained or directly regulated by `to_node` where `to_node` is typically a Policy / Standard / regulatory regime.

Direction:

```text
regulated object → regulation / policy / standard
```

Common confusion:

- “Regulator X regulates Company Y” is textually regulator-first but semantically Company Y `regulated_by` X / the relevant policy regime, depending on Node modeling.

## Evidence sufficiency principles

Evidence should establish all material components of a Relation Candidate:

1. `from_node` identity;
2. `to_node` identity;
3. relation semantics;
4. direction, for directional relations;
5. material scope where omission would overgeneralize the claim.

If one of these is only inferred from broad context, the candidate should normally be rejected or marked for review rather than formalized.

## Directional language

Current implementation explicitly guards common active / passive forms for directional Relations, including `uses`, `supplies`, and `produces`.

Examples:

```text
Alpha uses Beta.
→ Alpha uses Beta

Alpha is used by Beta.
→ Beta uses Alpha

Alpha supplies Beta.
→ Alpha supplies Beta

Alpha is supplied by Beta.
→ Beta supplies Alpha

Alpha produces Beta.
→ Alpha produces Beta

Alpha is manufactured by Beta.
→ Beta produces Alpha
```

Complex Chinese passive constructions may be conservatively rejected when direction cannot be established safely by the current validator.

## Scope and identity

Scope must be preserved verbatim when it is legitimate business text.

Examples:

- `C1 stepping`
- `C2 stepping`
- `Rubin`
- `GB300`

Two otherwise identical Relation Candidates with materially different scope must not be silently merged.

## Questions to resolve using R1

R1 should provide evidence for, rather than pre-judge, the following ontology decisions:

1. Exact endpoint type compatibility for `supplies`.
2. Whether `produces` should always be Entity→Product / Material / Equipment or also permit other endpoint classes.
3. Preferred granularity when Company-level and Product-level endpoints are both available.
4. Whether any Relation pairs should be treated as explicit inverses.
5. Whether `upstream_of` should be created when a more specific Relation already captures the same fact.
6. Which scopes are identity-defining versus merely descriptive metadata.
7. How to represent planned / trial / qualification / mass-production states without overstating current Relations.

No answer to these questions becomes frozen until R1 / Gold Set review explicitly supports it.
