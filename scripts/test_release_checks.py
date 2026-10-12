"""Exercise release gates without publishing or contacting an index."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from check_distributions import sha256
from check_release import before_publish, check_pypi


@pytest.fixture
def publication():
    # A tiny simulated index exercises integrity checks without publishing anything
    project = {
        "name": "oaipmh",
        "version": "example",
        "requires-python": ">=3.11",
        "classifiers": [],
    }
    files = {"example.whl": b"wheel", "example.tar.gz": b"sdist"}
    manifest = {
        "project": project,
        "revision": "release-revision",
        "dirty": False,
        "files": {"release/" + name: sha256(data) for name, data in files.items()},
    }
    index = {
        "info": {
            "name": "oaipmh",
            "version": "example",
            "requires_python": ">=3.11",
            "classifiers": [],
            "description_content_type": "text/markdown",
            "description": "# Example",
        },
        "urls": [
            {
                "filename": name,
                "digests": {"sha256": sha256(data)},
                "url": "https://files.pythonhosted.org/" + name,
                "yanked": False,
                "requires_python": ">=3.11",
            }
            for name, data in files.items()
        ],
    }

    def read(url):
        if url.endswith("/json"):
            return json.dumps(index).encode()
        return files[url.rsplit("/", 1)[1]]

    return manifest, index, files, read


def test_accept_exact_published_files(publication):
    manifest, _, _, read = publication
    check_pypi(manifest, read)


@pytest.mark.parametrize(
    "mutation", ["bytes", "digest", "metadata", "missing", "yanked", "host", "extra"]
)
def test_reject_wrong_publication(publication, mutation):
    manifest, index, files, read = publication
    # Metadata and digest checks must not substitute for checking downloaded bytes
    if mutation == "bytes":
        files["example.whl"] = b"wrong artifact"
    elif mutation == "digest":
        index["urls"][0]["digests"]["sha256"] = "wrong"
    elif mutation == "metadata":
        index["info"]["requires_python"] = ">=3.10"
    elif mutation == "missing":
        index["urls"].pop()
    elif mutation == "host":
        index["urls"][0]["url"] = "https://example.org/example.whl"
    elif mutation == "extra":
        index["urls"].append({"filename": "unexpected.whl"})
    else:
        index["urls"][0]["yanked"] = True
    with pytest.raises(ValueError):
        check_pypi(manifest, read)


@pytest.mark.parametrize("mutation", [None, "dirty", "revision", "tag", "branch"])
def test_release_identity(publication, monkeypatch, mutation):
    manifest, _, _, _ = publication
    # Model the tag event while keeping the test independent of a live workflow
    monkeypatch.setenv("GITHUB_SHA", "release-revision")
    monkeypatch.setenv("GITHUB_REF_TYPE", "tag")
    monkeypatch.setenv("GITHUB_REF_NAME", "vexample")
    if mutation == "dirty":
        manifest["dirty"] = True
    elif mutation == "revision":
        manifest["revision"] = "other-revision"
    elif mutation == "tag":
        monkeypatch.setenv("GITHUB_REF_NAME", "vother")
    elif mutation == "branch":
        monkeypatch.setenv("GITHUB_REF_TYPE", "branch")
    if mutation:
        with pytest.raises(ValueError):
            before_publish(manifest)
    else:
        before_publish(manifest)


def test_optimized_python_rejects_dirty_release():
    # Publication safeguards must still run when Python disables assert statements
    result = subprocess.run(
        [
            sys.executable,
            "-O",
            "-c",
            "from check_release import before_publish; before_publish({'dirty': True})",
        ],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "ValueError: Publish only from a committed release revision" in result.stderr
