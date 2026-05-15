{ pythonEntries, lib, ... }:
{
  perSystem =
    { pkgs, ... }:
    let
      mkShell =
        python:
        pkgs.mkShell {
          packages = [
            python
            pkgs.uv
            pkgs.pre-commit
          ];
          # `LD_LIBRARY_PATH` exposes `stdenv.cc.cc.lib` so dynamically-linked
          # wheels resolved by `uv` (e.g. those linking `libstdc++`) load
          # inside the devshell.
          LD_LIBRARY_PATH = lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib ];
          UV_PYTHON = "${python}/bin/python3";
          UV_PYTHON_DOWNLOADS = "never";
          UV_PYTHON_PREFERENCE = "only-system";
          # Install hooks directly from `.pre-commit-config.yaml`. The
          # `git rev-parse` guard skips installation when entered
          # outside a checkout (e.g. `nix develop github:…`).
          shellHook = ''
            if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
              pre-commit install --install-hooks >/dev/null
            fi
          '';
        };
      # Decorate each pythonEntries row with a resolved Python derivation.
      axis = map (e: e // { python = pkgs.${e.pythonAttr}; }) pythonEntries;
      # Build { py310 = mkShell python310; py311 = ...; } from the axis.
      byShell = lib.listToAttrs (
        map (e: {
          name = e.shell;
          value = mkShell e.python;
        }) axis
      );
      # The axis row marked `default = true` aliases `.#default`.
      defaultEntry = lib.findFirst (e: e.default or false) null axis;
    in
    {
      devShells = byShell // {
        default = mkShell defaultEntry.python;
      };
    };
}
