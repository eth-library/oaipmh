"""Install each built wheel in a fresh environment outside the checkout."""

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from check_distributions import bundle_wheels, verify


def consumer_environment() -> dict[str, str]:
    """Keep consumer dependency resolution independent of the development shell."""
    # Remove interpreter and resolver settings inherited from the development shell
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("PYTHON", "UV_"))
        and k not in ("VIRTUAL_ENV", "CONDA_PREFIX")
    }
    env["UV_PYTHON_DOWNLOADS"] = "never"
    return env


def check_target(
    target: Path | str,
    bundle: Path,
    shell: str,
    interpreter: str,
    env: dict[str, str],
    *,
    from_pypi: bool = False,
) -> None:
    """Install an artifact or index requirement in a fresh consumer environment."""
    with tempfile.TemporaryDirectory(prefix="oaipmh-consumer-") as directory:
        outside = Path(directory).resolve()
        if outside.is_relative_to(Path.cwd().resolve()):
            raise ValueError(f"Consumer directory is inside the checkout: {outside}")
        # Copy only the smoke runner; package imports must come from the environment
        shutil.copyfile(
            Path(__file__).with_name("check_installed_package.py"),
            outside / "check_installed_package.py",
        )
        shutil.copyfile(bundle / "manifest.json", outside / "manifest.json")

        # Run consumer commands from the isolated temporary directory
        def run(command: list[str]) -> None:
            subprocess.run(command, cwd=outside, env=env, check=True)

        run(
            [
                "uv",
                "venv",
                "--no-project",
                "--no-config",
                "--python",
                interpreter,
                ".venv",
            ]
        )
        # Resolve runtime dependencies normally, without consulting the project lock
        python = str(outside / ".venv/bin/python")
        run(
            [
                "uv",
                "pip",
                "install",
                "--no-config",
                "--python",
                python,
                "--verbose",
                # Bypass cached artifacts when checking the production index
                *(
                    ["--no-cache", "--default-index", "https://pypi.org/simple"]
                    if from_pypi
                    else []
                ),
                str(target),
            ]
        )
        # Isolated Python ignores source-path and user-site leakage
        run(
            [
                python,
                "-I",
                "check_installed_package.py",
                "manifest.json",
                shell,
                *(["pypi"] if from_pypi else []),
            ]
        )


def main() -> None:
    """Validate the bundle before testing each wheel with the requested shell."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("shell")
    parser.add_argument(
        "--pypi",
        action="store_true",
        help="Install the exact version from production PyPI",
    )
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    manifest = verify(bundle)
    if args.shell not in manifest["shells"]:
        raise ValueError(f"Unsupported Python shell: {args.shell}")
    interpreter = os.environ["UV_PYTHON"]
    env = consumer_environment()
    project = manifest["project"]
    # Production mode resolves an index requirement instead of a local artifact path
    targets = (
        [f"{project['name']}=={project['version']}"]
        if args.pypi
        else bundle_wheels(bundle)
    )
    # Each target gets its own environment so one installation cannot mask another
    for target in targets:
        check_target(target, bundle, args.shell, interpreter, env, from_pypi=args.pypi)


if __name__ == "__main__":
    main()
