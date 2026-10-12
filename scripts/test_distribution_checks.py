"""Regression tests for distribution-validation failures."""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from check_distributions import check_metadata, inspect_wheel, sha256, verify


@pytest.mark.parametrize(
    "field,value",
    [("Name", "wrong"), ("Version", "wrong"), ("Requires-Python", ">=3.10")],
)
def test_reject_wrong_identity(field, value):
    project = {
        "name": "oaipmh",
        "version": "example",
        "requires-python": ">=3.11",
        "classifiers": [],
        "dependencies": ["lxml"],
    }
    # Change one identity field while leaving the remaining metadata valid
    metadata = {
        "Name": "oaipmh",
        "Version": "example",
        "Requires-Python": ">=3.11",
        "Requires-Dist": "lxml",
    }
    metadata[field] = value
    raw = "\n".join(f"{k}: {v}" for k, v in metadata.items()).encode()
    with pytest.raises(ValueError):
        check_metadata(raw, project)


@pytest.mark.parametrize("mutation", ["changed", "extra", "missing"])
def test_reject_changed_bundle(tmp_path, mutation):
    # Begin with all three roles so each mutation tests its intended failure
    names = ("release/package.whl", "release/package.tar.gz", "rebuilt/package.whl")
    for name in names:
        path = tmp_path / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"original")
    wheel = tmp_path / names[0]
    (tmp_path / "manifest.json").write_text(
        json.dumps({"files": {name: sha256(b"original") for name in names}})
    )
    # Corruption, missing files, and unexpected files must all fail closed
    if mutation == "changed":
        wheel.write_bytes(b"modified")
    elif mutation == "extra":
        (tmp_path / "unexpected.whl").write_bytes(b"extra")
    else:
        wheel.unlink()
    with pytest.raises(ValueError):
        verify(tmp_path)


def test_reject_missing_library_module(tmp_path):
    project = {
        "name": "oaipmh",
        "version": "example",
        "requires-python": ">=3.11",
        "classifiers": [],
        "dependencies": ["lxml"],
    }
    wheel = tmp_path / "example.whl"
    # Valid metadata must not hide an absent library module
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "oaipmh-example.dist-info/METADATA",
            "Name: oaipmh\nVersion: example\n"
            "Requires-Python: >=3.11\nRequires-Dist: lxml\n",
        )
        archive.writestr(
            "oaipmh-example.dist-info/WHEEL",
            "Root-Is-Purelib: true\nTag: py3-none-any\n",
        )
    with pytest.raises(ValueError, match="payload"):
        inspect_wheel(wheel, project, {"oaipmh/client.py": b"missing"})


@pytest.mark.parametrize("missing", ["all", "original", "source", "rebuilt"])
def test_reject_incomplete_bundle(tmp_path, missing):
    # A consistent manifest must still contain every required artifact role
    names = {
        "original": "release/package.whl",
        "source": "release/package.tar.gz",
        "rebuilt": "rebuilt/package.whl",
    }
    files = {}
    for role, name in names.items():
        if missing in ("all", role):
            continue
        path = tmp_path / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"original")
        files[name] = sha256(b"original")
    (tmp_path / "manifest.json").write_text(json.dumps({"files": files}))
    with pytest.raises(ValueError, match="Expected one"):
        verify(tmp_path)


def test_optimized_python_rejects_invalid_metadata():
    # Execute the real helper with optimization, which previously removed its checks
    script = (
        "from check_distributions import check_metadata; "
        'check_metadata(b"Name: wrong", '
        '{"name": "oaipmh", "version": "example", "requires-python": ">=3.11"})'
    )
    result = subprocess.run(
        [sys.executable, "-O", "-c", script],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "ValueError: Name:" in result.stderr
