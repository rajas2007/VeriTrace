---
name: Architecture / Contract Task
about: Propose or track an architectural decision, shared contract change, or boundary refinement
title: '[ARCH]: '
labels: ['architecture']
assignees: ''
---

## Objective & Problem Statement
Describe the architectural ambiguity, contract requirement, or design decision that needs resolution.

## Impacted Architectural Layers
- [ ] `src/veritrace/domain/` (Business Rules, Core Models)
- [ ] `src/veritrace/application/` (Application Services, DTOs)
- [ ] `src/veritrace/capabilities/` (Forensic Capability Engines)
- [ ] `src/veritrace/gui/` (Presentation & Widgets)
- [ ] `src/veritrace/infrastructure/` (Database, Adapters, Storage)
- [ ] `src/veritrace/workers/` (Concurrency, Checkpoints)

## Proposed Architectural Change
Detailed description of the interface, schema change, or decision.

## Related ADR & Planning Documents
- **Decision Record:** (e.g. `dev/12_DECISION_LOG.md` ADR-028)
- **Planning Spec:** (e.g. `dev/26_TEAM_DEVELOPMENT_AND_GITHUB_WORKFLOW.md`)

## Backward Compatibility & Cross-Team Impact
Will this break existing mocks, database schemas, or downstream workstreams? How will downstream teams adapt?

## Verification Criteria
- [ ] Architectural boundary check passes: `python scripts/validation/check_architecture.py`
- [ ] Updated in `dev/12_DECISION_LOG.md`
- [ ] Updated in `dev/26_TEAM_DEVELOPMENT_AND_GITHUB_WORKFLOW.md`
