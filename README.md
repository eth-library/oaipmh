# oaipmh

[![PyPI version](https://img.shields.io/pypi/v/oaipmh)](https://pypi.org/project/oaipmh/)
[![Python versions](https://img.shields.io/pypi/pyversions/oaipmh)](https://pypi.org/project/oaipmh/)
[![CI](https://github.com/eth-library/oaipmh/actions/workflows/ci.yml/badge.svg)](https://github.com/eth-library/oaipmh/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue)](./LICENSE)

A Python library for working with [OAI-PMH version 2](https://www.openarchives.org/OAI/openarchivesprotocol.html) — harvest metadata from existing repositories using the client, or expose your own repository using the server. This is a maintained fork of [`infrae/pyoai`](https://github.com/infrae/pyoai).

## Installation

Install the latest release from PyPI:

```bash
pip install oaipmh
```

Requires Python 3.10 or newer.

## Quickstart

A minimal client that lists records from an OAI-PMH endpoint using the Dublin Core metadata prefix:

```python
from oaipmh.client import Client
from oaipmh.metadata import MetadataRegistry, oai_dc_reader

URL = "http://uni.edu/ir/oaipmh"

registry = MetadataRegistry()
registry.registerReader("oai_dc", oai_dc_reader)
client = Client(URL, registry)

for record in client.listRecords(metadataPrefix="oai_dc"):
    print(record)
```

## Migrating from pyoai

If you already depend on `pyoai`, migration is a dependency swap:

- Replace `pyoai` with `oaipmh` in your requirements (`pip install oaipmh`).
- Import paths are unchanged — `from oaipmh import ...` continues to work.
- The minimum supported Python version is 3.10.

No application code changes are required beyond the dependency rename. See [Why this fork](#why-this-fork) for background.

## Why this fork

`oaipmh` is a maintained fork of [`infrae/pyoai`](https://github.com/infrae/pyoai), which has received no substantive changes since March 2022. The public API and import path are unchanged; only the PyPI distribution name has changed, from `pyoai` to `oaipmh`, to distinguish the maintained release from the abandoned upstream package.

Maintenance since the fork has focused on bringing the codebase onto current Python infrastructure while preserving behaviour for existing consumers:

- Python 3.10+ baseline; legacy Python 2 compatibility code removed.
- Deprecated `datetime.utcnow()` replaced with timezone-aware alternatives.
- Modern packaging using [PEP 621](https://peps.python.org/pep-0621/) metadata and the [Hatchling](https://hatch.pypa.io/) build backend.
- CI pipeline rebuilt on [`uv`](https://docs.astral.sh/uv/), replacing the legacy `tox` configuration.
- Reproducible development environment via a [Nix](https://nixos.org/) flake and [direnv](https://direnv.net/).
- Test suite modernised and running green across Python 3.10 – 3.13.

## Scope

`oaipmh` is a maintained fork. Bug fixes and compatibility work are the primary focus; well-scoped feature proposals are welcome via GitHub Issues and Pull Requests. See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for guidelines.

## Contributing

Issues and pull requests are welcome. See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for local development setup, branch naming, commit conventions, and the release process.

## Support

Bug reports and questions are accepted via [GitHub Issues](https://github.com/eth-library/oaipmh/issues). Maintenance is best-effort with no formal SLA.

## Acknowledgements

We are grateful to the original [`infrae/pyoai`](https://github.com/infrae/pyoai) authors at Infrae and to the many community contributors who built and maintained this library over two decades; this fork would not exist without their work.

## License

Distributed under the BSD-3-Clause License.  
Copyright © 2026 ETH Zurich, Jaime Cardozo; ETH Library.  
Based on [`infrae/pyoai`](https://github.com/infrae/pyoai) by Infrae and community contributors.

See [`LICENSE`](./LICENSE) for the full license terms and [`CHANGELOG.md`](./CHANGELOG.md) for the release history.