# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Chain re-raised exceptions with `raise ... from` in `client.py`,
  `server.py`, and `datestamp.py` so tracebacks show the original cause
  ([Ruff `B904`](https://docs.astral.sh/ruff/rules/raise-without-from-inside-except/) /
  [PEP 3134](https://peps.python.org/pep-3134/)).
- Build the published wheel inside the project's Nix flake devShell
  (`publish.yml`). Pure-Python source semantics unchanged; published
  artifact bytes may differ across releases due to build-toolchain
  provenance.
- Centralise CI cache wiring behind composite Actions in
  `.github/actions/`; `test` and `build` now also cache
  `~/.cache/uv`.

## [3.1.0] — 2026-04-23

### Added

- Python 3.14 support. Added to the `pyproject.toml` trove classifiers and
  to the CI matrix; the test suite runs green on CPython 3.10 – 3.14.

### Security

- GitHub Actions in `ci.yml` and `publish.yml` pinned to full commit SHAs
  instead of mutable tags.

## [3.0.1] — 2026-04-15

### Fixed

- Embed `README.md` as the project's long description on PyPI. The PEP 621
  `readme` field was missing from `pyproject.toml`, so the `oaipmh 3.0.0`
  page on PyPI showed an empty body. No code or API changes; this is a
  packaging-metadata-only fix.

## [3.0.0] — 2026-04-15

First release under the `oaipmh` distribution name on PyPI. This release marks the
maintenance fork from [`infrae/pyoai`](https://github.com/infrae/pyoai) and brings the
codebase onto modern Python packaging and tooling. The public API and the
`from oaipmh import ...` import path are unchanged.

### Breaking Changes

- Renamed PyPI distribution from `pyoai` to `oaipmh`. Existing consumers must update
  their dependency declarations; no application code changes are required.
- Minimum supported Python version raised to 3.10. Python 2 and Python 3.9 and earlier
  are no longer supported.
- Removed the `six` dependency; the package now relies exclusively on native Python 3
  APIs.

### Added

- PEP 621 metadata in `pyproject.toml` with [Hatchling](https://hatch.pypa.io/) as the
  build backend.
- `uv.lock` for reproducible dependency resolution.
- [`uv`](https://docs.astral.sh/uv/)-based GitHub Actions CI covering Python 3.10 – 3.13.
- GitHub Actions workflow (`publish.yml`) for automated PyPI publishing via
  [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC; no
  long-lived tokens stored in the repository).
- Reproducible development environment via a [Nix](https://nixos.org/) flake and
  [`direnv`](https://direnv.net/) integration.
- `pytest` configuration replacing the legacy `runtests.sh` entry point.
- `CONTRIBUTING.md` with development setup, commit conventions, and the release process.
- `CHANGELOG.md` (this file), superseding `HISTORY.txt`.
- `ETH Library — Data Science and Research Support <dsr@library.ethz.ch>` maintainer
  entry alongside the existing Jaime Cardozo entry.

### Changed

- Build backend migrated from legacy `setup.py` / `setup.cfg` to Hatchling via
  `pyproject.toml`.
- Development status classifier raised from `4 - Beta` to `5 - Production/Stable`.
- Version jumped from `2.5.2pre` to `3.0.0` to reflect the breaking distribution rename
  and the Python version floor.
- README rewritten and expanded; converted from reStructuredText (`README.rst`) to
  Markdown (`README.md`).
- License file renamed from `LICENSE.txt` to `LICENSE` and prepended with an ETH Zurich
  copyright notice alongside the original Infrae notice.
- Wheel and sdist contents scoped via explicit `tool.hatch.build` include/exclude
  lists, so consumers no longer receive test fixtures or local development files.
- Bare imports inside the package converted to relative imports.

### Fixed

- Replaced deprecated `datetime.utcnow()` with timezone-aware
  `datetime.now(timezone.utc)` equivalents (Python 3.12+ deprecation).
- Replaced `lxml.etree.XPath.evaluate()` calls with direct callable syntax for
  compatibility with `lxml` 5.x.
- Replaced `unicode()` with `str()` for Python 3 compatibility.
- Replaced `pkg_resources` with `importlib.metadata` for distribution version lookup.
- Replaced removed unittest assertion aliases dropped in Python 3.12.
- Removed the `unittest.makeSuite` helper, which was dropped in Python 3.13.
- Renamed the internal test helper `TestError` to `FakeRequestError` to avoid pytest's
  `PytestCollectionWarning` on classes prefixed with `Test`.

### Removed

- Python 2 compatibility shims across the package and tests.
- `six` dependency.
- Legacy packaging files: `setup.py`, `setup.cfg`, `tox.ini`, `MANIFEST.in`, and
  `.travis.yml`.
- `runtests.sh` (replaced by `pytest`).
- Non-functional Python 2 data generation scripts.
- Outdated `doc/` directory.
- Legacy Mercurial files.
- `HISTORY.txt` (content migrated to this file).

---

## [2.5.1] — 2022-03-08

### Added

- Customizable client retry policy.
- Python 3.8 compatibility.

### Fixed

- Do not resume `ListRecord` requests when no result was returned.

## [2.5.0] — 2017-07-03

### Added

- Python 3 compatibility.
- Travis CI support and badges.

## [2.4.5] — 2015-12-23

### Added

- Client switch to force harvesting using HTTP GET.
- Unofficial `GetMetadata` verb in server and client. `GetMetadata` is identical to
  `GetRecord` but returns only the first element below the `oai:metadata` element,
  without the OAI envelope.

## [2.4.4] — 2010-09-30

### Changed

- Updated contact info.
- Migrated code from Subversion to Mercurial.

## [2.4.3] — 2010-08-19

### Fixed

- Convert `lxml.etree._ElementUnicodeResult` and `ElementStringResult` to normal `str`
  and `unicode` objects to prevent errors when these objects are pickled.

## [2.4.2] — 2010-05-03

### Fixed

- `oai_dc` and `dc` namespace declarations are now declared on the child of the
  metadata element rather than the document root, per the OAI-PMH specification.

## [2.4.1] — 2009-11-16

### Fixed

- When a date (not a datetime) is specified for the `until` parameter, default to
  `23:59:59` instead of `00:00:00`.

## [2.4] — 2009-05-04

### Added

- Support for description elements in OAI `Identify` headers, with a `toolkit`
  description included by default.

## [2.3.1] — 2009-04-24

### Fixed

- Raise the correct error when `from` and `until` parameters have different
  granularities.

## [2.3] — 2009-04-23

### Changed

- Use `buildout` to create the testrunner and environment, replacing the `test.py`
  script.

### Fixed

- Handle invalid `dateTime` formats correctly: the server now responds with a
  `BadArgument` XML error instead of a Python traceback.

## [2.2.1] — 2008-04-04

### Added

- XML declaration to server output.
- Pretty-printed XML output.
- Server resumption tokens now work with POST requests.

### Fixed

- Compatibility with `lxml` 2.0.
- Handle `503` responses from the server correctly in client code.

## [2.2] — 2006-11-20

### Added

- `BatchingServer`, implementing the `IBatchingOAI` interface. Similar to `IOAI` but
  with `cursor` and `batch_size` arguments on each method, enabling efficient batching
  OAI servers on top of relational databases.
- Ability to explicitly pass `None` as the `from` or `until` parameter for an OAI-PMH
  client.
- Extra `nsmap` argument on `Server` and `BatchingServer` to customise the namespace
  prefix to URI mappings used in server output.

### Fixed

- Output encoding bug: output is now correctly encoded as UTF-8.

## [2.1.5] — 2006-09-18

### Fixed

- Compatibility with `lxml` 1.1.

## [2.1.4] — 2006-06-16

### Changed

- Distribute as an egg.

## [2.1.3] — 2006-05-01

### Added

- Infrastructure to handle non-XML-compliant OAI-PMH feeds; an `XMLSyntaxError` is now
  raised in those cases.
- `tolerant_datestamp_to_datetime`, a more permissive alternative to
  `datestamp_to_datetime` for handling malformed datestamps.

### Changed

- Split datestamp handling into a separate `datestamp` module.

## [2.0] — 2006-01-26

### Added

- Support for day-only granularity (`YYYY-MM-DD`) in the client. Calling
  `updateGranularity` checks with the server (via `identify()`) which granularity it
  supports; if the server only supports day-level granularity, the client restricts
  outgoing timestamps to `YYYY-MM-DD`.

## [2.0b1] — 2005-11-21

### Added

- Framework for implementing OAI-PMH-compliant servers.
- Extended testing infrastructure.

### Changed

- Package structure is now an `oaipmh` namespace package; client functionality moved
  to `oaipmh.client`.
- Refactored `oaipmh.py` to share code between the client and server.
- Switched from the `libxml2` Python wrappers to the `lxml` binding.
- `listRecords`, `listIdentifiers`, and `listSets` now return iterators instead of
  lists (previously hacked via `__getitem__`). Existing call sites can wrap the result
  in `list()` if needed.

## [1.0.1]

### Fixed

- Typo in `oaipmh.py`.

## [1.0]

### Added

- `encoding` parameter to the `serialize` call, fixing a Unicode bug.

## [0.7.4]

### Fixed

- Harvested records with `<header status="deleted">` are no longer stored in the
  catalog. Previously they could be treated as normal records even though they merely
  indicate that the metadata set is no longer on the OAI service.

## [0.7]

Initial public release.
