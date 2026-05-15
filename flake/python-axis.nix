{ lib, ... }:
let
  # Single source of truth for the supported Python axis. Fields:
  #   version    — display only (job titles, error messages).
  #   shell      — devShell attribute name; CI invokes
  #                `nix develop .#${shell}` directly.
  #   pythonAttr — nixpkgs attribute resolving to the Python derivation,
  #                so future entries (pypy, RC builds, overlays) plug
  #                in by adding a row.
  #   default    — optional; the row with `default = true` is the
  #                one `default` aliases.
  pythonEntries = [
    {
      version = "3.10";
      shell = "py310";
      pythonAttr = "python310";
    }
    {
      version = "3.11";
      shell = "py311";
      pythonAttr = "python311";
    }
    {
      version = "3.12";
      shell = "py312";
      pythonAttr = "python312";
    }
    {
      version = "3.13";
      shell = "py313";
      pythonAttr = "python313";
    }
    {
      version = "3.14";
      shell = "py314";
      pythonAttr = "python314";
      default = true;
    }
  ];
in
{
  # Share the axis with sibling modules via `_module.args`.
  _module.args.pythonEntries = pythonEntries;

  # Flat list projected to `.#lib.pythonShells`.
  flake.lib.pythonShells = map (e: e.shell) pythonEntries;
}
