# Upload.md Action-Oriented Runbook Design

## Intent & Why
`Upload.md` serves as the onboarding and operational guide for developers looking to package independent microservices and mount them into the `hf-backend` gateway. Previously, the document mixed high-level architecture narratives and diagrams with operational instructions. This redesign refocuses `Upload.md` into an actionable, step-by-step Standard Operating Procedure (SOP) runbook that guides a developer through the exact commands, code templates, file modifications, and git releases needed to deploy their service.

## Goals & Non-Goals
### Goals
- Structure `Upload.md` strictly into two sequential phases:
  - **Phase 1: Upstream Subproject Setup (In the service repository)**
  - **Phase 2: Gateway Integration (In `hf-backend`)**
- Detail exact file paths, directory reorganizations (preventing root namespace collisions with `main.py`), and required code additions (`pyproject.toml`, FastAPI `router.py`, `warmup()`, `/health`).
- Provide concrete git commands for releasing SemVer tags (`git tag -a v1.0.0 ...`).
- Provide concrete CLI steps for `requirements.in`, `uv pip compile`, `registry.py`, pytest test execution, and deployment verification.
- Keep currently mounted projects strictly to `heartflow` and `semantic`.

### Non-Goals
- Adding new microservices or changing `registry.py` at this time.
- Modifying gateway core proxy/forwarding architecture.

## Approaches Considered
- **Approach 1 (Selected)**: Pure Action-Oriented Runbook (Direct Step-by-Step SOP). Strips out high-level theoretical prose and presents numbered checklist steps with copy-paste code snippets.
- **Approach 2**: Hybrid Runbook with Storage/Stateful Appendices. Rejected in favor of Approach 1 to maximize developer speed and clarity.
