# Phase 4.2 scroll maintenance release — v0.5.1

Version **0.5.1** fixes desktop vertical scrolling across Phase 4.2 long-page
Workbench surfaces while preserving the classic three-column Explorer's
viewport-bound internal scrolling.

## Corrected surfaces

- Research Home and long Research routes
- Source Operations
- Durable Jobs
- Human View Proposals
- Changes & Impact
- Review

The classic Explorer retains its three-column desktop layout and independent
panel scrolling. This patch does not redesign navigation, typography or other
product layout.

## Qualification

The exact release candidate passed the complete frontend test suite, TypeScript
validation, the production frontend build and browser acceptance at 1920×1080
and 1366×768. Browser checks covered mouse-wheel and PageDown navigation,
reachable bottom content, usable headers, expected vertical scrollbars, absence
of unnecessary horizontal page scrolling and the Explorer's internal scroll
containers.

## Boundaries

This is a frontend-only maintenance release. It does not change knowledge
semantics, backend APIs, database schemas, provider contracts, Review, Current
View, Impact, Golden Path or Production behavior. It performs no Production
Apply and requires no live provider, cloud-model or local-model call.

Private browser evidence, local paths, databases, credentials and runtime
artifacts remain outside the public tracked tree.
