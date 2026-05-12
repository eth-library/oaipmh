{ pythonEntries, lib, ... }:
{
  # `LD_LIBRARY_PATH` exposes `stdenv.cc.cc.lib` so dynamically-linked
  # wheels resolved by `uv` (e.g. those linking `libstdc++`) load
  # inside the devshell. `shellHook` inherits from
  # `git-hooks-nix.installationScript` (handles hook installation
  # plus `core.hooksPath` conflict surfacing).
  perSystem =
    { config, pkgs, ... }:
    let
      mkShell =
        python:
        pkgs.mkShell {
          packages = [
            python
            pkgs.uv
            pkgs.pre-commit
          ];
          LD_LIBRARY_PATH = lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib ];
          UV_PYTHON = "${python}/bin/python3";
          UV_PYTHON_DOWNLOADS = "never";
          UV_PYTHON_PREFERENCE = "only-system";
          shellHook = config.pre-commit.installationScript;
        };
      axis = map (e: e // { python = pkgs.${e.pythonAttr}; }) pythonEntries;
      byShell = lib.listToAttrs (
        map (e: {
          name = e.shell;
          value = mkShell e.python;
        }) axis
      );
      defaultEntry = lib.findFirst (e: e.default or false) null axis;
    in
    {
      devShells = byShell // {
        default = mkShell defaultEntry.python;
      };
    };
}
