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


def check_wheel(
    wheel: Path, bundle: Path, shell: str, interpreter: str, env: dict[str, str]
) -> None:
    """Install one wheel and run the smoke checks in a fresh environment."""
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
                str(wheel),
            ]
        )
        # Isolated Python ignores source-path and user-site leakage
        run([python, "-I", "check_installed_package.py", "manifest.json", shell])


def main() -> None:
    """Validate the bundle before testing each wheel with the requested shell."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("shell")
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    manifest = verify(bundle)
    if args.shell not in manifest["shells"]:
        raise ValueError(f"Unsupported Python shell: {args.shell}")
    interpreter = os.environ["UV_PYTHON"]
    env = consumer_environment()
    # Each wheel gets its own environment so one installation cannot mask another
    for wheel in bundle_wheels(bundle):
        check_wheel(wheel, bundle, args.shell, interpreter, env)


if __name__ == "__main__":
    main()
