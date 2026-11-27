# AGENTS.md — Operating Rules for `zakshub/voicecity`

> **Project Operating System:** This repository follows **[zakshub/project-os](https://github.com/zakshub/project-os)** (Private).  
> Follow all 14 steps of `zakshub/project-os/antigravity/OPERATING_INSTRUCTIONS.md` for every development task.

---

## 1. Project Identity & Strict Boundaries
- **Purpose:** Original, local-first personal voice studio for Urdu, English, and mixed Urdu-English voice cloning and speech generation (`http://127.0.0.1:8765`).
- **Classification:** Active Substantial Product
- **Default Branch:** `main` (use short-lived feature branches + Pull Requests; never rewrite history)
- **Strict Constraints:**
  - **Local-first & private:** Never send user voice recordings or transcripts to external cloud APIs or telemetry services without explicit authorization.
  - **Honest verification:** Preserve the 5-Axis Verification discipline—keep hardware-dependent live speech/listening tests explicitly marked `SKIPPED` (`PENDING_LAPTOP_HARDWARE`) when running without target ML hardware. Never fabricate audio quality results.
  - **Licensing honesty:** Consult [docs/MODEL_LICENSING_REGISTER.md](./docs/MODEL_LICENSING_REGISTER.md) before adding or recommending voice models.
  - **No heavy weights in Git or CI:** Never commit model weights, `.env`, or personal WAV recordings to Git, and do not install CUDA/PyTorch/model weights in lightweight CI runs.

## 2. Mandatory Reading Order
1. [README.md](./README.md)
2. [docs/PRODUCT_REQUIREMENTS.md](./docs/PRODUCT_REQUIREMENTS.md) and [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
3. [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md) and [docs/PRIVACY_SECURITY.md](./docs/PRIVACY_SECURITY.md)
4. [docs/ROADMAP.md](./docs/ROADMAP.md), [docs/OPEN_DECISIONS.md](./docs/OPEN_DECISIONS.md), and [docs/ACCEPTANCE_CHECKLIST.md](./docs/ACCEPTANCE_CHECKLIST.md)
5. [docs/MODEL_EVALUATION.md](./docs/MODEL_EVALUATION.md) and [docs/MODEL_LICENSING_REGISTER.md](./docs/MODEL_LICENSING_REGISTER.md)

## 3. Verified Local Development & Test Commands
```bash
# Create virtual environment and install API + dev dependencies
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev,api]"

# Run local server
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload

# Run automated tests & lint checks
pytest
ruff check .
```

## 4. Design & Visual Intelligence
- **UX/UI changes (`frontend/`):** Consult `/root/.intelligence/designer` (`zakshub/designer`) and [docs/UX_DIRECTION.md](./docs/UX_DIRECTION.md) before modifying UI components (pay special attention to Urdu RTL readability).
- **Visual assets:** Consult `/root/.intelligence/studio` (`zakshub/studio`) under the Designer–Studio Contract if artwork is required.

## 5. Verification & Safety Rules
- Never modify application logic solely for documentation or Project OS maintenance tasks.
- Always run `pytest` and `ruff check .` (and report actual pass/skip/fail counts) before opening a Pull Request.
- Never claim completion without verified command output.
