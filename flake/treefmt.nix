{ inputs, ... }:
{
  imports = [ inputs.treefmt-nix.flakeModule ];

  # Formatter coverage is `*.nix` only; YAML and Python formatting
  # are handled by other tools (`pre-commit` hooks, `ruff`).
  # `programs.nixfmt.package` is pinned to `nixfmt-rfc-style`
  # (RFC 166) explicitly: recent `treefmt-nix` defaults
  # `programs.nixfmt.enable = true` to that package, but older
  # `treefmt-nix` resolves to `nixfmt-classic`, so the explicit pin
  # makes the resolution stable across `treefmt-nix` versions.
  perSystem = { pkgs, ... }: {
    treefmt = {
      projectRootFile = "flake.nix";
      programs.nixfmt.enable = true;
      programs.nixfmt.package = pkgs.nixfmt-rfc-style;
    };
  };
}
