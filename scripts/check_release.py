"""Validate release identity, the Python boundary, and published artifacts."""

import argparse
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

from check_distributions import sha256, verify
from check_installation import consumer_environment


def before_publish(manifest: dict) -> None:
    """Require the bundle to match the committed release tag being published."""
    # Uncommitted local validation bundles can never pass the publication gate
    if manifest["dirty"]:
        raise ValueError("Publish only from a committed release revision")
    if manifest["revision"] != os.environ["GITHUB_SHA"]:
        raise ValueError("Bundle revision differs from the release revision")
    if os.environ["GITHUB_REF_TYPE"] != "tag":
        raise ValueError("Publication requires a tag event")
    if os.environ["GITHUB_REF_NAME"] != "v" + manifest["project"]["version"]:
        raise ValueError("Release tag differs from the package version")
    print("Release tag, package version, artifact revision, and checksums agree")


def python_floor(bundle: Path, manifest: dict) -> None:
    """Check installer target compatibility without executing the dropped Python."""
    if manifest["project"]["requires-python"] != ">=3.11":
        raise ValueError("This boundary check requires a Python 3.11 minimum")
    (wheel,) = (bundle / "release").glob("*.whl")
    env = consumer_environment()
    # Simulate installer targets; this does not retain an unsupported interpreter
    with tempfile.TemporaryDirectory(prefix="oaipmh-boundary-") as directory:
        subprocess.run(
            [
                "uv",
                "venv",
                "--no-project",
                "--no-config",
                "--python",
                os.environ["UV_PYTHON"],
                ".venv",
            ],
            cwd=directory,
            env=env,
            check=True,
        )
        for target, accepted in [("3.11", True), ("3.10", False)]:
            result = subprocess.run(
                [
                    "uv",
                    "pip",
                    "install",
                    "--no-config",
                    "--python",
                    ".venv/bin/python",
                    "--python-version",
                    target,
                    "--dry-run",
                    "--no-deps",
                    str(wheel),
                ],
                cwd=directory,
                env=env,
                text=True,
                capture_output=True,
            )
            output = result.stdout + result.stderr
            print(output)
            if (result.returncode == 0) != accepted:
                raise ValueError(
                    f"Unexpected installer result for Python {target}: {output}"
                )
            if not accepted and (">=3.11" not in output or "3.10" not in output):
                raise ValueError(
                    f"Installer did not report the Python boundary: {output}"
                )
    print("Installer target check: accept Python 3.11 and reject Python 3.10")


def read_url(url: str) -> bytes:
    """Read one index response or artifact with a bounded network timeout."""
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def check_pypi(manifest: dict, read: Callable[[str], bytes] = read_url) -> None:
    """Compare the exact published release with the validated local artifacts."""
    project = manifest["project"]
    url = f"https://pypi.org/pypi/{project['name']}/{project['version']}/json"
    # Query the exact release, not the project’s potentially newer latest version
    data = json.loads(read(url))
    info = data["info"]
    if info["name"] != project["name"]:
        raise ValueError("Published package name differs")
    if info["version"] != project["version"]:
        raise ValueError("Published package version differs")
    if info["requires_python"] != project["requires-python"]:
        raise ValueError("Published Python requirement differs")
    if sorted(info["classifiers"]) != sorted(project["classifiers"]):
        raise ValueError("Published classifiers differ")
    if info["description_content_type"] != "text/markdown":
        raise ValueError("Published README must be Markdown")
    if not info["description"].strip():
        raise ValueError("Missing published README")
    # Only original release files are uploaded; the rebuilt wheel is test evidence
    expected = {
        Path(n).name: h
        for n, h in manifest["files"].items()
        if n.startswith("release/")
    }
    published = {item["filename"]: item for item in data["urls"]}
    if set(published) != set(expected):
        raise ValueError("Published artifact names differ from the validated bundle")
    for name, digest in expected.items():
        item = published[name]
        if item["yanked"]:
            raise ValueError(f"Published artifact is yanked: {name}")
        if item["requires_python"] != project["requires-python"]:
            raise ValueError(f"Artifact Python requirement differs: {name}")
        if item["digests"]["sha256"] != digest:
            raise ValueError(f"Published artifact checksum differs: {name}")
        # Accept artifact downloads only from PyPI’s HTTPS file host
        parsed = urllib.parse.urlsplit(item["url"])
        if parsed.scheme != "https" or parsed.hostname != "files.pythonhosted.org":
            raise ValueError(f"Unexpected artifact download URL: {item['url']}")
        if sha256(read(item["url"])) != digest:
            raise ValueError(f"Downloaded artifact checksum differs: {name}")
        print(f"Production PyPI artifact verified: {name} sha256:{digest}")


def wait_for_pypi(manifest: dict) -> None:
    """Retry briefly while the new release propagates through the index."""
    # Allow bounded index propagation after upload, then report any remaining failure
    for attempt in range(6):
        try:
            check_pypi(manifest)
            return
        except (urllib.error.URLError, ValueError):
            if attempt == 5:
                raise
            time.sleep(10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("before-publish", "python-floor", "pypi"))
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    manifest = verify(bundle)
    if args.command == "python-floor":
        python_floor(bundle, manifest)
    elif args.command == "before-publish":
        before_publish(manifest)
    else:
        wait_for_pypi(manifest)
