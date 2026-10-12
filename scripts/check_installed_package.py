"""Exercise the installed distribution without access to the checkout."""

import hashlib
import json
import sys
from datetime import datetime
from email.parser import Parser
from importlib.metadata import Distribution, distribution, distributions
from io import BytesIO
from pathlib import Path

from lxml import etree

from oaipmh import client, metadata, server
from oaipmh.datestamp import datestamp_to_datetime


def check_installation(manifest: dict, shell: str) -> Distribution:
    """Check interpreter identity, installed metadata, and package file hashes."""
    project = manifest["project"]
    if sys.version_info[:2] != (int(shell[2]), int(shell[3:])):
        raise ValueError(sys.version)
    if sys.version_info.releaselevel != "final":
        raise ValueError(sys.version)
    prefix = Path(sys.prefix).resolve()
    if sys.prefix == sys.base_prefix:
        raise ValueError("A fresh virtual environment is required")
    dist = distribution(project["name"])
    if dist.metadata["Name"] != project["name"]:
        raise ValueError("Installed package name differs from project declaration")
    if dist.version != project["version"]:
        raise ValueError("Installed version differs from project declaration")
    if dist.metadata["Requires-Python"] != project["requires-python"]:
        raise ValueError(
            "Installed Python requirement differs from project declaration"
        )
    if sorted(dist.metadata.get_all("Classifier")) != sorted(project["classifiers"]):
        raise ValueError("Metadata classifiers differ from project declarations")
    wheel = Parser().parsestr(dist.read_text("WHEEL"))
    if wheel.get_all("Tag") != ["py3-none-any"]:
        raise ValueError("Wheel must be platform-independent Python 3")
    if wheel["Root-Is-Purelib"] != "true":
        raise ValueError("Wheel must use purelib")
    # Verify installed payload bytes as well as the distribution’s declared version
    for name, digest in manifest["wheel_files"].items():
        installed = Path(dist.locate_file(name)).resolve()
        if not installed.is_relative_to(prefix):
            raise ValueError(installed)
        if hashlib.sha256(installed.read_bytes()).hexdigest() != digest:
            raise ValueError(name)
    return dist


def check_behavior() -> None:
    """Exercise deterministic public operations without network access."""
    # Include the compiled dependency in the import-provenance check
    for module in (client, metadata, server, etree):
        location = Path(module.__file__).resolve()
        if not location.is_relative_to(Path(sys.prefix).resolve()):
            raise ValueError(location)
        print(f"{module.__name__}: {location}")
    if datestamp_to_datetime("2005-07-04T14:35:10Z") != datetime(
        2005, 7, 4, 14, 35, 10
    ):
        raise ValueError("Datestamp conversion returned an unexpected value")
    tree = etree.parse(BytesIO(b"<record><identifier>example</identifier></record>"))
    if etree.XPath("string(/record/identifier)")(tree) != "example":
        raise ValueError("XPath returned an unexpected identifier")
    # Exercise a public library operation using deterministic XML and no live endpoint
    registry = metadata.MetadataRegistry()
    registry.registerReader(
        "example",
        metadata.MetadataReader({"identifier": ("text", "string(identifier)")}),
    )
    record = registry.readMetadata("example", tree.getroot())
    if record.getMap() != {"identifier": "example"}:
        raise ValueError("Metadata reader returned an unexpected record")
    if type(record.getMap()["identifier"]) is not str:
        raise ValueError("Metadata reader must return a plain string")


def main() -> None:
    """Check the installed package, then report the consumer environment."""
    # Expected metadata travels with the exact validated distribution bundle
    manifest = json.loads(Path(sys.argv[1]).read_text())
    dist = check_installation(manifest, sys.argv[2])
    # An index installation must not be replaced by a local wheel or direct URL
    if (
        len(sys.argv) > 3
        and sys.argv[3] == "pypi"
        and dist.read_text("direct_url.json") is not None
    ):
        raise ValueError("Expected an installation from the package index")
    check_behavior()
    print(f"Interpreter: {sys.executable}\n{sys.version}")
    print(f"Requires-Python: {dist.metadata['Requires-Python']}")
    print(f"Installed artifact: {dist.read_text('direct_url.json')}")
    for installed in sorted(distributions(), key=lambda d: d.metadata["Name"]):
        print(f"{installed.metadata['Name']}=={installed.version}")
    print("Installed-wheel runtime, metadata, payload, and provenance checks passed")


if __name__ == "__main__":
    main()
