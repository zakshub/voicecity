# AGENTS.md — Operating Rules for `zakshub/voicecity`

> **Governance & Access Note:** This is a **public** repository. Public contributors and external tools should follow this `AGENTS.md`, `README.md`, and the files inside `docs/`. Internal maintainer governance and portfolio tracking follow the owner's **private** `zakshub/project-os` repository (`antigravity/OPERATING_INSTRUCTIONS.md`) and **private** `Zakshub Portfolio` board (owner access only).

---

## 1. Project Identity & Strict Boundaries
- **Purpose:** Original, local-first personal voice studio for Urdu, English, and mixed Urdu-English voice cloning and speech generation (`http://127.0.0.1:8765`).
- **Classification:** Active Substantial Product
- **Default Branch:** `main` (use short-lived feature branches + Pull Requests; never rewrite history)
- **Strict Privacy, Consent & Operating Constraints:**
  - **Local-first & private:** Never send user voice recordings or transcripts to external cloud APIs or telemetry services without explicit opt-in authorization.
  - **Loopback-only API binding:** Keep the local API strictly bound to `127.0.0.1` unless Zak separately approves a different host binding.
  - **Consent & anti-impersonation boundary:** VoiceCity is intended strictly for the user's own voice or a voice they are explicitly authorized to use. Never build features intended to impersonate another person without consent, bypass identity checks, or facilitate fraud (see [docs/PRIVACY_SECURITY.md](./docs/PRIVACY_SECURITY.md)).
  - **Honest verification:** Preserve the 5-Axis Verification discipline—keep hardware-dependent live speech and listening tests explicitly marked `SKIPPED` (`PENDING_LAPTOP_HARDWARE`) when running without target ML hardware. Never fabricate audio quality results.
  - **Licensing honesty:** Consult [docs/MODEL_LICENSING_REGISTER.md](./docs/MODEL_LICENSING_REGISTER.md) before adding or recommending voice models.
  - **No heavy weights in Git or CI:** Never commit recordings, generated audio, voice embeddings, model weights, `.env`, or credentials to Git, and do not install CUDA/PyTorch/model weights in lightweight CI runs.

## 2. Mandatory Reading Order
1. [README.md](./README.md) and [docs/ANTIGRAVITY_HANDOFF.md](./docs/ANTIGRAVITY_HANDOFF.md)
2. [docs/PRODUCT_REQUIREMENTS.md](./docs/PRODUCT_REQUIREMENTS.md) and [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
3. [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md), [docs/LINUX_MINT_GUIDE.md](./docs/LINUX_MINT_GUIDE.md), and [docs/PRIVACY_SECURITY.md](./docs/PRIVACY_SECURITY.md)
4. [docs/ROADMAP.md](./docs/ROADMAP.md), [docs/OPEN_DECISIONS.md](./docs/OPEN_DECISIONS.md), and [docs/ACCEPTANCE_CHECKLIST.md](./docs/ACCEPTANCE_CHECKLIST.md)
5. [docs/MODEL_EVALUATION.md](./docs/MODEL_EVALUATION.md) and [docs/MODEL_LICENSING_REGISTER.md](./docs/MODEL_LICENSING_REGISTER.md)

## 3. Verified Local Development & Test Commands
```bash
# Create virtual environment and install lightweight API + dev dependencies
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev,api]"

# Run local server (loopback 127.0.0.1 only)
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload

# Run automated test suite (required passing gate in CI)
pytest -q

# Check Ruff lint on files you modified (keep modified files Ruff-clean)
ruff check <modified-files>

# Full-repo Ruff lint (currently advisory in CI due to 77 pre-existing findings)
ruff check .
```

### Ruff Lint Policy (Pre-Existing Backlog)
- `ruff check .` currently reports **77 pre-existing lint findings** across existing source and test files, so the Ruff step in `.github/workflows/ci.yml` runs as **advisory (`continue-on-error: true`)** while `pytest -q` is the required passing gate.
- **Required rule for all changes:** Any Python file you add or modify **must** be Ruff-clean (`ruff check <modified-files>` passes with 0 errors), without performing unrelated repository-wide lint reformatting outside a dedicated lint-cleanup issue.

## 4. Design & Visual Intelligence
- **UX/UI changes (`frontend/`):** Consult canonical UX/UI intelligence (`zakshub/designer`, via your configured local intelligence workspace when available) and [docs/UX_DIRECTION.md](./docs/UX_DIRECTION.md) before modifying UI components (paying special attention to Urdu RTL readability).
- **Visual assets:** Consult canonical visual-production intelligence (`zakshub/studio`, under the Designer–Studio Contract) whenever artwork or photographic assets are required.

## 5. Verification & Safety Rules
- Never modify application logic solely for documentation or Project OS maintenance tasks.
- Always run `pytest -q` and `ruff check <modified-files>` (and report exact pass/skip/fail counts) before opening a Pull Request.
- Never claim completion without verified command output.
