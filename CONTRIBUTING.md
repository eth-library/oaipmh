# Contributing

Thank you for your interest in contributing to `oaipmh`. Bug reports, feature proposals, and pull requests are welcome.

## Local development

Three setup paths are supported, in order of preference.

### Option A — Nix flake (recommended)

The repository ships a reproducible [Nix](https://nixos.org/) flake providing Python, [`uv`](https://docs.astral.sh/uv/), and system dependencies.

With [direnv](https://direnv.net/) — the shell auto-loads on `cd`:

```bash
direnv allow
```

Without direnv — manual entry per shell session:

```bash
nix develop
```

Run the test suite:

```bash
uv run pytest
```

The `default` shell aliases the newest supported Python. To use a specific version's shell instead, name it explicitly:

```bash
nix develop .#py311
```

See `flake.nix` for the list of available shells.

### Option B — `uv` only

If you have [`uv`](https://docs.astral.sh/uv/) installed directly and prefer not to use Nix.

Synchronise dependencies from `uv.lock`:

```bash
uv sync
```

Run the test suite:

```bash
uv run pytest
```

### Option C — plain `pip` and `venv`

Standard Python tooling works with no additional prerequisites beyond a Python 3.10+ interpreter.

Create the virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install the package in editable mode together with the test dependencies:

```bash
pip install -e ".[test]"
```

Run the test suite:

```bash
pytest
```

## CI

CI runs on every push and pull request. Two parallel tracks:

```
lint                  (independent)
matrix ──▶ test       (test: needs: matrix; fans out per devShell)
```

- **Lint track** (`lint` job, independent) — runs `pre-commit run --all-files` over the repository. Same Ruff and hygiene hooks that run on every local commit.
- **Test track** (`matrix` → `test`) — `matrix` evaluates `nix eval --json .#pythonShells` and exposes the devShell-name list as a job output; `test` depends on it (`needs: matrix`) and fans out one row per devShell with `fail-fast: false` so a regression on one row doesn't mask others. Adding or removing a Python version is a one-line edit to `pythonEntries` in `flake.nix`; CI follows automatically.

All three jobs run inside Nix devShells declared in `flake.nix`. CI's Python interpreter, `uv`, and `pre-commit` come from that file — the same source contributors use locally. Both `lint` and the `test` rows cache the Nix store between runs (`nix-community/cache-nix-action`); the `matrix` job is `nix eval`-only and skips caching for now.

## Style

The repository uses [Ruff](https://docs.astral.sh/ruff/) for linting, wired up via [pre-commit](https://pre-commit.com/) so the same checks run locally and in CI.

If you use the Nix flake (Option A), pre-commit hooks are installed automatically when you enter the dev shell.

Otherwise, install pre-commit:

```bash
uv tool install pre-commit
```

Then install the hooks:

```bash
pre-commit install
```

From then on, `git commit` runs Ruff (with `--fix`) plus a small set of standard hygiene hooks (trailing-whitespace, end-of-file-fixer, YAML/TOML syntax checks, merge-conflict marker detection, large-file guard) on the files you touch. To run everything against the whole tree on demand:

```bash
pre-commit run --all-files
```

CI enforces the same hook set in the `lint` job of `.github/workflows/ci.yml`. Contributors who commit before running `pre-commit install` will see the failure surface in CI rather than locally.

The repository also ships a `.git-blame-ignore-revs` file. When a future bulk-format pass lands as a single commit, its SHA is appended to this file so `git blame --ignore-revs-file=.git-blame-ignore-revs` (or `git config blame.ignoreRevsFile .git-blame-ignore-revs`) skips past it and surfaces the original author of each line.

## Commit conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/). Common prefixes used in this repository:

- `feat:` — a new feature.
- `fix:` — a bug fix.
- `docs:` — documentation-only changes.
- `refactor:` — a code change that neither fixes a bug nor adds a feature.
- `test:` — adding or correcting tests.
- `build:` — changes to the build system or packaging.
- `ci:` — changes to CI configuration.
- `chore:` — maintenance tasks that don't fit the categories above.

Keep commits atomic: one logical change per commit, with a clear message that explains the *why* rather than restating the diff.

## Branching strategy

This project follows a [trunk-based development](https://trunkbaseddevelopment.com/) model. All work lands on `main` through short-lived topic branches (typically merged within a few days). Long-lived branches — including release branches — are avoided because they drift from `main`, accumulate merge conflicts, and fragment CI signal.

Use a short, purpose-driven prefix that matches the commit type: `feat/`, `fix/`, `docs/`, `chore/`, `ci/`.

A `release/<version>` branch is only appropriate for exceptional, coordinated releases that cannot land as a single short-lived branch (for example, the initial `release/v3.0.0` that carried the fork takeover from `pyoai` to `oaipmh`). The default path for a release is a tag on `main`, not a release branch.

The [Releases](#releases) section below picks up from here and walks through the tag-and-publish flow.

## Pull requests

External contributors should [fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo) `eth-library/oaipmh` on GitHub, push changes to a branch on their fork, and open a pull request from that branch. Maintainers with push access to `eth-library/oaipmh` may open branches directly on the repository.

- Target the `main` branch of `eth-library/oaipmh`.
- Keep the PR focused on a single topic; open separate PRs for unrelated changes.
- Ensure the test suite passes locally (`uv run pytest`) before opening the PR.
- CI must be green before a PR can be merged.
- Provide enough context in the description for a reviewer to understand the motivation, the approach, and any trade-offs.

## Releases

Releases follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The release process is:

1. Merge release-bound changes into `main` as individual short-lived topic branches. Do not open a long-lived release branch; cut the release from `main` once the desired commits have landed.
2. Tag the merge commit with `vX.Y.Z` and push the tag.
3. Create a draft GitHub Release against the tag, using the relevant `CHANGELOG.md` section as the release notes.
4. Review the draft release; when publishing it, the `publish.yml` workflow uploads the distribution to PyPI through [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC — no tokens stored in the repository).

The fork jumped directly from `2.5.2pre` (an unreleased development version under the upstream `pyoai` distribution name) to `3.0.0` because the PyPI distribution was renamed from `pyoai` to `oaipmh` and the minimum supported Python version was raised to 3.10 — both of which are breaking changes under SemVer.
