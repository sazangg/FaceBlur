# Contributing

Thanks for considering contributing!

## Setup
1. Create a virtual environment and install dev dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
2. Copy `.env.example` to `.env` and set values.

## Running checks
- Format: `black .`
- Lint: `ruff check .`
- Types: `mypy .`
- Tests: `pytest`

## Guidelines
- Keep changes focused and small.
- Add tests for new behavior when possible.
- Update docs if behavior or configuration changes.
