## Workflow

- Read-only actions don't need prior approval — status, log, branch listing, file reads, drafting.
- Mutating actions need a plan and explicit approval before running — file edits, commits, pushes, branch/ref/worktree deletion, rebases, merges.

## Project: OG-ETH

OG-ETH is an Ethiopia country calibration of the OG-Core overlapping-generations model of demographics and fiscal policy.

## Environment

- Package manager: [`uv`](https://docs.astral.sh/uv/). Install via your package manager (e.g. `brew install uv`) or `pip install uv`.
- Local virtualenv: `.venv` at the repo root, created by `uv sync --extra dev`.
- Run Python/pytest/etc. via `uv run <cmd>` (preferred — uses the project venv without activation) or activate first with `source .venv/bin/activate`.
- For docs/Jupyter Book work, also pass `--extra docs`: `uv sync --extra dev --extra docs`.

## Python formatting and linting

- Sequence: edit → format → test → stage → commit → push.
- Format + auto-fix: `make format` (runs `uvx ruff format .` + `uvx ruff check . --fix`).
- CI check (no changes): `make lint` (runs `uvx ruff format --check .` + `uvx ruff check .`).
- Ruff config lives in `pyproject.toml` under `[tool.ruff]`; matches OG-Core.
- Re-run tests after formatting — ruff can change line breaks that affect string literals and assertions.

## Testing

- Default suite (matches CI, skips the long example run): `uv run python -m pytest -m 'not local' -q` (or `make test`).
- Targeted (fast): `uv run python -m pytest tests/test_macro_params.py tests/test_calibrate.py tests/test_update_baseline.py -q`.
- Full example run (slow, ~35 min – 2 hr): `uv run python examples/run_og_eth.py`.

## Repo conventions

- `pyproject.toml` is the source of truth for dependencies, declared as floors (e.g. `ogcore>=…`). `uv.lock` is not committed (it is git-ignored), so `uv sync` resolves the latest compatible versions — including the latest released `ogcore`.
- The packaged JSON default parameters are the standard baseline input for offline/default runs.
- Calibration or data-source changes (macro parameters, demographics, earnings, industry I/O) should be validated with targeted tests and, where feasible, the relevant example flow.
