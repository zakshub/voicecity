# Development Setup

## Target environment
The first runtime target is the user's Linux desktop. Termux and Debian on the phone are the initial repository editing and agent workflow environment, not the assumed ML inference target.

## Requirements
- Git
- Python 3.11 or newer
- Python virtual environment
- Node.js only after a frontend framework is selected
- Laptop hardware inventory before installing an ML runtime

## Clone
```bash
git clone https://github.com/zakshub/voicecity.git
cd voicecity
```

## Python environment
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev,api]"
```

## Run scaffold API
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

Open http://127.0.0.1:8765/health and http://127.0.0.1:8765/docs.

These endpoints report scaffold status only. They do not clone a voice or generate speech.

## Tests
```bash
pytest
ruff check .
```

## Hardware inventory
```bash
uname -a
cat /etc/os-release
python3 --version
lscpu
free -h
df -h
lspci | grep -Ei 'vga|3d|display'
```

If NVIDIA tooling is installed:
```bash
nvidia-smi
```

Do not install CUDA, ROCm, PyTorch, model weights, or large audio dependencies until the selected candidate's requirements are known.

## Local data
Copy .env.example to .env only when needed. Local data and model directories must remain untracked.
