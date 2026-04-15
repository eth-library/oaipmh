# Contributing

Thank you for your interest in contributing to `oaipmh`. Bug reports, feature proposals, and pull requests are welcome.

## Local development

Three setup paths are supported, in order of preference.

### Option A — Nix flake with direnv (recommended)

The repository ships a reproducible [Nix](https://nixos.org/) flake with [direnv](https://direnv.net/) integration. This provisions the correct Python, [`uv`](https://docs.astral.sh/uv/), and system dependencies automatically.

Activate the environment the first time you enter the repository:

```bash
direnv allow
```

Run the test suite:

```bash
uv run pytest
```

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

Create and activate a virtual environment:

```bash
python3 -m venv .venv
```

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

## Branch naming

Use a short, purpose-driven prefix that matches the commit type:

- `feat/<short-description>`
- `fix/<short-description>`
- `docs/<short-description>`
- `chore/<short-description>`
- `ci/<short-description>`
- `release/<version>` for release branches (for example `release/v3.0.0`).

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

1. Merge all release-bound changes into `main` through pull requests.
2. Tag the merge commit with `vX.Y.Z` and push the tag.
3. Create a draft GitHub Release against the tag, using the relevant `CHANGELOG.md` section as the release notes.
4. Review the draft release; when publishing it, the `publish.yml` workflow uploads the distribution to PyPI through [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC — no tokens stored in the repository).

The fork jumped directly from `2.5.2pre` (an unreleased development version under the upstream `pyoai` distribution name) to `3.0.0` because the PyPI distribution was renamed from `pyoai` to `oaipmh` and the minimum supported Python version was raised to 3.10 — both of which are breaking changes under SemVer.