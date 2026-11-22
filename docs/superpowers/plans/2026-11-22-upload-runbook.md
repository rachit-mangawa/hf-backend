# Upload.md Action-Oriented Runbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform `Upload.md` into an actionable, execution-oriented runbook that instructs developers on modifying their service repos, structuring packages, cutting Git release tags, and mounting routes into `hf-backend`.

**Architecture:** The document is split into two chronological phases: Upstream Subproject Setup (namespacing, `pyproject.toml`, `router.py`, `warmup()`, release tags) and Gateway Integration (`requirements.in`, `uv pip compile`, `registry.py`, pytest test execution). High-level theoretical essays are replaced with structured, copy-pasteable checklists.

**Tech Stack:** Markdown, FastAPI, Python setuptools/pyproject.toml, Git SemVer, pytest, uv/pip-tools.

**Spec:** `docs/superpowers/specs/2026-11-22-upload-runbook-design.md`

## Global Constraints
- Preserve existing gateway registrations (`/heartflow` and `/semantic` only).
- Keep all code snippets in `Upload.md` syntactically valid and copy-paste ready.
- Do not introduce breaking changes to `registry.py` or existing tests.

## Review Focus
- Check that all paths and file structure examples in `Upload.md` cleanly isolate subproject namespaces to prevent `main.py` collisions.
- Check that the git tag release instructions include `--tags` so remote CI builds detect the new version.
- Check that `uv pip compile` commands specify the required platform flags (`--python-platform linux`).
- Verify existing gateway tests pass cleanly before and after the update.

---

### Task 1: Rewrite Upload.md into the Action-Oriented Runbook

**Files:**
- Modify: `Upload.md`
- Test: `tests/test_host.py`

**Interfaces:**
- Consumes: Existing subproject contract conventions from `hf-backend`.
- Produces: A self-contained, copy-pasteable SOP document in `Upload.md`.

- [ ] **Step 1: Draft the complete action runbook structure in `Upload.md`**
  Restructure `Upload.md` into:
  - Header: Purpose & Quick Checklist.
  - Phase 1: Upstream Subproject Setup (Step-by-step: namespaced layout `backend/<service>_backend/`, `pyproject.toml`, `router.py` with relative routes & `/health`, `warmup()`, and git tagging `git tag -a v1.0.0 -m "Release v1.0.0" && git push origin --tags`).
  - Phase 2: Host Gateway Integration (Step-by-step: `requirements.in`, `uv pip compile`, `registry.py`, local `pytest`, and push to `main`).
  - Phase 3: Post-Deployment Verification & UI Auto-Mounting (Checking live health, developer status console, and auto-generated Swagger UI on GitHub Pages).
  - Common Pitfalls & Solutions (Cheatsheet table: missing packaging metadata, namespace collision, timeout).

- [ ] **Step 2: Verify `Upload.md` markdown formatting and links**
  Ensure all internal references, code blocks, and markdown links are valid.

- [ ] **Step 3: Run existing gateway tests to ensure zero regressions**
  Run: `pytest tests/test_host.py -v`
  Expected: All host tests pass.

- [ ] **Step 4: Commit changes to Git**
  ```bash
  git add Upload.md docs/superpowers/
  git commit -m "docs: rewrite Upload.md as action-oriented developer runbook"
  ```
