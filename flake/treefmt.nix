{ inputs, ... }:
{
  imports = [ inputs.treefmt-nix.flakeModule ];

  # `programs.nixfmt.package` is pinned to `nixfmt-rfc-style` (RFC 166)
  # explicitly: older `treefmt-nix` resolves `programs.nixfmt.enable =
  # true` to `nixfmt-classic`, so the pin keeps resolution stable.
  perSystem =
    { pkgs, ... }:
    {
      treefmt = {
        projectRootFile = "flake.nix";
        programs.nixfmt.enable = true;
        programs.nixfmt.package = pkgs.nixfmt-rfc-style;
      };
    };
}
