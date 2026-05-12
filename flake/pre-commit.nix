{ inputs, ... }:
{
  imports = [ inputs.git-hooks-nix.flakeModule ];

  # `installationScript` is the only `git-hooks-nix` surface this
  # repo consumes — `flake/devshells.nix` reads
  # `config.pre-commit.installationScript` as its `shellHook`.
  # Hook *definitions* live in `.pre-commit-config.yaml` so non-Nix
  # contributors can edit them without touching Nix module schemas;
  # `perSystem.pre-commit.settings.hooks` is left empty for that
  # reason.
  perSystem = _: { pre-commit.settings.hooks = { }; };
}
