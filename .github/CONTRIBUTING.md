# Contributing to VeriTrace Desktop

Thank you for contributing to **VeriTrace Desktop**! This project is being engineered for the DataOps Innovation Hackathon (Problem Statement 2).

To maintain high code quality, architectural integrity, and developer velocity across parallel workstreams, all contributors must follow these guidelines.

---

## 1. Quick Onboarding Checklist

1. **Read the Architecture & Onboarding Guide:**
   Before writing any code, thoroughly read [dev/26_TEAM_DEVELOPMENT_AND_GITHUB_WORKFLOW.md](../dev/26_TEAM_DEVELOPMENT_AND_GITHUB_WORKFLOW.md). It is the authoritative guide for coding standards, shared contracts, and workstream responsibilities.
2. **Environment Setup:**
   Ensure you have installed **Python 3.11 (64-bit)**:
   ```powershell
   winget install Python.Python.3.11 --scope user
   py -3.11 -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -e .[all]
   ```
3. **Verify Setup:**
   Run the automated architectural validator:
   ```powershell
   python scripts/validation/check_architecture.py
   python scripts/development/run_desktop.py
   ```

---

## 2. Architectural Boundaries (Non-Negotiable)

VeriTrace follows a strict layered monolith architecture in `src/veritrace/`:
* `domain/` contains pure business logic and models. **NEVER import PySide6, SQLAlchemy, OpenCV, PyMuPDF, or external frameworks into `domain/`.**
* `gui/` interacts with the system exclusively through `application/services/`. **NEVER import `infrastructure/` or write raw SQL queries in `gui/`.**
* `capabilities/` modules are algorithmic engines. **NEVER manipulate Qt widgets in `capabilities/`.**
* These boundaries are strictly verified by `python scripts/validation/check_architecture.py`. Pull requests that violate boundaries will be blocked.

---

## 3. Git & Branching Process

1. **Work from `develop`:** Always branch your feature from the latest `develop` branch.
   ```powershell
   git checkout develop
   git pull origin develop
   git checkout -b feature/ws1-my-feature
   ```
2. **Commit Messages:** Follow Conventional Commits:
   * `feat(ws1): add bounding box overlay to document viewer`
   * `fix(ws5): correct baseline regression sigma calculation`
   * `docs: update shared contract specifications in dev/26`
3. **Open a Pull Request:** Use `.github/pull_request_template.md`. Link the relevant issue.
4. **Peer Review:** Every PR requires at least one approving peer review before merging.

---

## 4. Code Standards & Testing

* **Formatting & Linting:** We use **Ruff** (line length 100 characters). Format code before committing:
  ```powershell
  ruff format src/
  ruff check --fix src/
  ```
* **Testing:** Run unit tests:
  ```powershell
  pytest tests/unit/
  ```
* **Secrets:** Never commit `.env` files or API keys. Always use `.env.example`.
* **External Repositories:** Never touch or modify `UdyogPermit AI`.

---

## 5. Repository Documentation & Task Reporting Policy

To maintain a clean repository baseline and avoid documentation sprawl, all contributors and AI agents must adhere to the following documentation hierarchy:

1. **Permanent Technical Documentation (`dev/`, `docs/`, `README.md`):**
   * Living architectural specifications, domain models, interface contracts, and development plans.
   * Update these files when an architectural contract or implementation design changes.
2. **Decision Records & Progress Tracking:**
   * Record new or updated architectural decisions in `dev/12_DECISION_LOG.md`.
   * Update milestone and task completion in `dev/13_PROGRESS_TRACKER.md`.
3. **Execution Reports (Chat / PR Only — No Repository Files):**
   * **DO NOT commit separate `TASK_XX_COMPLETION_REPORT.md` files into the repository.**
   * Task execution details, validation logs, and audit summaries belong directly in the PR description or conversational interface.
   * Only create standalone report files if an explicit project deliverable requires it (e.g. user-facing investigative dossiers).

---

## 6. Getting Help & Escalation

If you encounter architectural ambiguities, contract mismatches, or blocking dependencies, open an **Architecture Task** issue or contact the Technical Project Manager.
