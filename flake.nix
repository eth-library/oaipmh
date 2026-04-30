{
  description = "Nix flakes development environment for oaipmh";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

      mkShell = pkgs: python: pkgs.mkShell {
        packages = [
          python
          pkgs.uv
          pkgs.pre-commit
        ];
        LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
          pkgs.stdenv.cc.cc.lib
        ];
        UV_PYTHON = "${python}/bin/python3";
        UV_PYTHON_DOWNLOADS = "never";
        UV_PYTHON_PREFERENCE = "only-system";
      };
    in
    {
      devShells = forAllSystems (pkgs: {
        py310   = mkShell pkgs pkgs.python310;
        py311   = mkShell pkgs pkgs.python311;
        py312   = mkShell pkgs pkgs.python312;
        py313   = mkShell pkgs pkgs.python313;
        py314   = mkShell pkgs pkgs.python314;
        default = mkShell pkgs pkgs.python314;
      });
    };
}