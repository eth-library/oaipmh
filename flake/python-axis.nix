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
  #   packageSet — optional interpreter source; defaults to the base package set
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
    {
      version = "3.15";
      shell = "py315";
      pythonAttr = "python315";
      packageSet = "python315";
    }
  ];
  shellNames = map (e: e.shell) pythonEntries;
  defaultEntries = lib.filter (e: e.default or false) pythonEntries;
  checkedEntries =
    assert lib.assertMsg (
      builtins.length shellNames == builtins.length (lib.unique shellNames)
    ) "Python axis shell names must be unique";
    assert lib.assertMsg (
      builtins.length defaultEntries == 1
    ) "Python axis must have exactly one default row";
    pythonEntries;
in
{
  # Share the axis with sibling modules via `_module.args`.
  _module.args.pythonEntries = checkedEntries;

  # Flat list projected to `.#lib.pythonShells`.
  flake.lib.pythonShells = map (e: e.shell) checkedEntries;
}
