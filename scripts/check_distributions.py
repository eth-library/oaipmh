"""Build and inspect the distributions shared by CI and publication."""

import argparse
import hashlib
import json
import os
import subprocess
import tarfile
import tomllib
import zipfile
from email.message import Message
from email.parser import BytesParser
from pathlib import Path


def sha256(data: bytes) -> str:
    # One digest format ties the downloaded bundle to the tested bytes
    return hashlib.sha256(data).hexdigest()


def check_metadata(data: bytes, project: dict) -> Message:
    """Reject metadata that differs from the declared project requirements."""
    # Compare with project declarations, not with values read from the wheel itself
    metadata = BytesParser().parsebytes(data)
    for key, expected in (
        ("Name", project["name"]),
        ("Version", project["version"]),
        ("Requires-Python", project["requires-python"]),
    ):
        if metadata[key] != expected:
            raise ValueError(f"{key}: expected {expected!r}, found {metadata[key]!r}")
    if sorted(metadata.get_all("Classifier", [])) != sorted(project["classifiers"]):
        raise ValueError("Metadata classifiers differ from project declarations")
    runtime = [
        requirement
        for requirement in metadata.get_all("Requires-Dist", [])
        if "extra ==" not in requirement
    ]
    if runtime != project["dependencies"]:
        raise ValueError(f"Runtime dependencies differ from declarations: {runtime}")
    return metadata


def inspect_wheel(
    path: Path, project: dict, sources: dict[str, bytes]
) -> dict[str, str]:
    """Check wheel contents and return hashes of its installed files."""
    # Read members without extracting an archive into the checkout
    with zipfile.ZipFile(path) as archive:
        files = {n: archive.read(n) for n in archive.namelist() if not n.endswith("/")}
    info = f"{project['name']}-{project['version']}.dist-info/"
    check_metadata(files[info + "METADATA"], project)
    wheel = BytesParser().parsebytes(files[info + "WHEEL"])
    if wheel["Root-Is-Purelib"] != "true":
        raise ValueError(f"Unexpected wheel format in {path}: {wheel}")
    if wheel.get_all("Tag") != ["py3-none-any"]:
        raise ValueError(f"Unexpected wheel format in {path}: {wheel}")
    payload = {n: data for n, data in files.items() if n.startswith("oaipmh/")}
    # Exact membership detects missing modules and accidentally shipped test files
    if payload != sources:
        raise ValueError("Wheel library payload differs from source tree")
    if not all(name.startswith(("oaipmh/", info)) for name in files):
        raise ValueError(f"Unexpected wheel files: {sorted(files)}")
    if any("/tests/" in n or "__pycache__" in n for n in files):
        raise ValueError(f"Unexpected wheel files: {sorted(files)}")
    return {n: sha256(data) for n, data in files.items() if not n.endswith("/RECORD")}


def bundle_wheels(bundle: Path) -> tuple[Path, Path]:
    """Require one original wheel, one source archive, and one rebuilt wheel."""
    artifacts = []
    # Validate each role separately so a missing build cannot silently skip testing
    for directory, pattern in (
        ("release", "*.whl"),
        ("release", "*.tar.gz"),
        ("rebuilt", "*.whl"),
    ):
        matches = sorted((bundle / directory).glob(pattern))
        if len(matches) != 1:
            raise ValueError(
                f"Expected one {directory}/{pattern}, found {len(matches)}"
            )
        artifacts.append(matches[0])
    return artifacts[0], artifacts[2]


def verify(bundle: Path) -> dict:
    """Require a complete distribution bundle with matching file hashes."""
    manifest = json.loads((bundle / "manifest.json").read_text())
    # Extra artifacts must fail too; publication must not pick up a stale wheel
    actual = {str(p.relative_to(bundle)) for p in bundle.rglob("*") if p.is_file()}
    if actual != set(manifest["files"]) | {"manifest.json"}:
        raise ValueError(f"Bundle files differ from manifest: {sorted(actual)}")
    bundle_wheels(bundle)
    for name, digest in manifest["files"].items():
        if sha256((bundle / name).read_bytes()) != digest:
            raise ValueError(f"Artifact checksum mismatch: {name}")
    print(
        json.dumps(
            {k: manifest[k] for k in ("revision", "dirty", "shells", "files")}, indent=2
        )
    )
    return manifest


def inspect_sdist(
    sdist: Path, root: Path, project: dict, sources: dict[str, bytes]
) -> None:
    """Check the source archive against the intended checkout files."""
    with tarfile.open(sdist) as archive:
        members = {
            m.name.split("/", 1)[1]: archive.extractfile(m).read()
            for m in archive.getmembers()
            if m.isfile()
        }
    # An allowlist catches nested checkouts and private development files
    expected = {"src/" + n: data for n, data in sources.items()}
    for name in (
        ".gitignore",
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
    ):
        expected[name] = (root / name).read_bytes()
    if set(members) != set(expected) | {"PKG-INFO"}:
        raise ValueError(f"Unexpected source archive files: {sorted(members)}")
    if not all(members[name] == data for name, data in expected.items()):
        raise ValueError("Incomplete sdist")
    check_metadata(members["PKG-INFO"], project)


def build(bundle: Path) -> None:
    """Build both wheel variants and record the inspected artifact bundle."""
    root = Path.cwd().resolve()
    if bundle.exists():
        raise ValueError(f"Choose a new output directory: {bundle}")
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    shells = json.loads(
        subprocess.check_output(["nix", "eval", "--json", ".#lib.pythonShells"])
    )
    # Keep advertised support and the CI shell matrix in agreement
    classifiers = [f"Programming Language :: Python :: {s[2]}.{s[3:]}" for s in shells]
    advertised = [
        c
        for c in project["classifiers"]
        if c.startswith("Programming Language :: Python :: 3.")
    ]
    if sorted(classifiers) != sorted(advertised):
        raise ValueError((classifiers, advertised))
    if project["requires-python"] != f">={shells[0][2]}.{shells[0][3:]}":
        raise ValueError(project)
    # The current library has only top-level modules; changes must update this inventory
    sources = {
        str(p.relative_to(root / "src")): p.read_bytes()
        for p in (root / "src/oaipmh").glob("*.py")
    }
    # Keep upload candidates separate from the wheel rebuilt only for validation
    release = bundle / "release"
    subprocess.run(
        ["uv", "build", "--sdist", "--wheel", "--out-dir", str(release)], check=True
    )
    (wheel,) = release.glob("*.whl")
    (sdist,) = release.glob("*.tar.gz")
    wheel_files = inspect_wheel(wheel, project, sources)
    inspect_sdist(sdist, root, project, sources)
    # Building from the archive proves its completeness independently of the checkout
    rebuilt = bundle / "rebuilt"
    subprocess.run(
        ["uv", "build", str(sdist), "--wheel", "--out-dir", str(rebuilt)], check=True
    )
    (rebuilt_wheel,) = rebuilt.glob("*.whl")
    inspect_wheel(rebuilt_wheel, project, sources)
    # uv creates output-directory ignore files; they are not release artifacts
    for directory in (release, rebuilt):
        (directory / ".gitignore").unlink(missing_ok=True)
    # Dirty local snapshots are useful evidence but are rejected by the upload gate
    manifest = {
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "dirty": bool(subprocess.check_output(["git", "diff", "HEAD", "--", "."])),
        "project": project,
        "shells": shells,
        "wheel_files": wheel_files,
        "files": {
            str(p.relative_to(bundle)): sha256(p.read_bytes())
            for p in bundle.rglob("*")
            if p.is_file()
        },
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as stream:
            stream.write(f"shells={json.dumps(shells)}\n")
    verify(bundle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    {"build": build, "verify": verify}[args.command](args.bundle.resolve())
