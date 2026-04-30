{
  description = "Nix flakes development environment for oaipmh";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
  };

  outputs = { self, nixpkgs }:
    let
      lib = nixpkgs.lib;
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = f: lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

      # Single source of truth for the supported Python axis. Each
      # entry is plain data — no string parsing, no encoding rules.
      # Fields:
      #   version    — semantic version string, used for human-
      #                facing display only (job titles, error
      #                messages).
      #   shell      — the devShell attribute name. CI invokes
      #                `nix develop .#${shell}` directly; no
      #                derivation, no transformation.
      #   pythonAttr — the nixpkgs attribute that resolves to the
      #                Python derivation. Decouples the version
      #                axis from nixpkgs naming conventions, so
      #                future entries (pypy variants, RC builds,
      #                overlays) plug in by adding a row.
      #   default    — optional boolean; the row with `default =
      #                true` is the one `default` aliases.
      # Adding or removing a supported version is a one-line list
      # edit; CI follows automatically via `pythonShells` below.
      pythonEntries = [
        { version = "3.10"; shell = "py310"; pythonAttr = "python310"; }
        { version = "3.11"; shell = "py311"; pythonAttr = "python311"; }
        { version = "3.12"; shell = "py312"; pythonAttr = "python312"; }
        { version = "3.13"; shell = "py313"; pythonAttr = "python313"; }
        { version = "3.14"; shell = "py314"; pythonAttr = "python314"; default = true; }
      ];

      # Flat list of devShell attribute names. This is the only
      # CI-facing surface — see the workflow file and the
      # CI-as-pure-executor rule.
      pythonShells = map (e: e.shell) pythonEntries;

      mkShell = pkgs: python: pkgs.mkShell {
        packages = [
          python
          pkgs.uv
          pkgs.pre-commit
        ];
        LD_LIBRARY_PATH = lib.makeLibraryPath [
          pkgs.stdenv.cc.cc.lib
        ];
        UV_PYTHON = "${python}/bin/python3";
        UV_PYTHON_DOWNLOADS = "never";
        UV_PYTHON_PREFERENCE = "only-system";
        shellHook = ''
          # Surface pre-commit install failures and core.hooksPath conflicts.
          # Zero output on the healthy path; enforcement lives in CI.
          if git rev-parse --git-dir >/dev/null 2>&1; then
            hooks_path="$(git config --get core.hooksPath 2>/dev/null || true)"
            if [ -n "$hooks_path" ]; then
              echo "flake shellHook: warning — git core.hooksPath='$hooks_path'; pre-commit hooks may not fire as expected. Run 'git config --unset core.hooksPath' to restore default routing." >&2
            fi
            if ! out="$(pre-commit install --install-hooks 2>&1)"; then
              echo "flake shellHook: pre-commit install failed:" >&2
              printf '%s\n' "$out" >&2
            fi
          fi
        '';
      };

      # Per-system: extend each entry with the actual Python
      # derivation. The `pkgs.${e.pythonAttr}` lookup is the only
      # site where data crosses from the version axis into nixpkgs.
      mkAxisFor = pkgs:
        map (e: e // { python = pkgs.${e.pythonAttr}; }) pythonEntries;

      mkShellsFor = pkgs:
        let
          axis = mkAxisFor pkgs;
          pythonByShell = lib.listToAttrs (map (e: {
            name  = e.shell;
            value = mkShell pkgs e.python;
          }) axis);
          defaultEntry = lib.findFirst (e: e.default or false) null axis;
        in
          pythonByShell // { default = mkShell pkgs defaultEntry.python; };
    in
    {
      # Exported so CI can consume the execution targets directly.
      # CI never reads `pythonEntries` and never reconstructs shell
      # names from versions.
      inherit pythonShells;

      devShells = forAllSystems mkShellsFor;
    };
}
