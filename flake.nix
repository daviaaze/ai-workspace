{
  description = "AI Workspace - Deep search, agent swarm, knowledge base, task automation";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts = {
      url = "github:hercules-ci/flake-parts";
      inputs.nixpkgs-lib.follows = "nixpkgs";
    };
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = inputs @ {flake-parts, ...}:
    flake-parts.lib.mkFlake {inherit inputs;} {
      imports = [
        inputs.treefmt-nix.flakeModule
      ];

      systems = ["x86_64-linux" "aarch64-linux"];

      perSystem = {
        config,
        pkgs,
        system,
        ...
      }: let
        pythonPkgs = pkgs.python3Packages;
      in {
        # Development shell
        devShells.default = pkgs.mkShell {
          name = "ai-workspace-dev";
          buildInputs = with pkgs; [
            python3
            uv
            postgresql
          ];
          shellHook = ''
            echo "🖥️  AI Workspace dev shell"
            echo "  ./scripts/bootstrap.sh  - Start all background services"
            echo "  aiw search <query>      - Deep research"
            echo "  aiw ask <question>       - Quick chat"
            echo "  aiw sync status          - Multi-PC sync status"
          '';
        };

        # Bootstrap script
        packages.bootstrap = pkgs.writeShellScriptBin "aiw-bootstrap" (
          builtins.readFile ./scripts/bootstrap.sh
        );

        # Package
        packages.ai-workspace = pythonPkgs.buildPythonPackage {
          pname = "ai-workspace";
          version = "0.1.0";
          src = ./.;
          pyproject = true;

          nativeBuildInputs = with pythonPkgs; [
            setuptools
          ];

          propagatedBuildInputs = with pythonPkgs; [
            typer
            rich
            httpx
            openai
            ollama
            pydantic
            pydantic-settings
            pyyaml
            python-dotenv
            beautifulsoup4
            lxml
            psycopg2
            pgvector
            crewai
            huey
            sentence-transformers
            streamlit
          ];

          # Don't run tests yet
          doCheck = false;

          meta = with pkgs.lib; {
            description = "AI Workspace - Deep search, agent swarm, knowledge base";
            license = licenses.mit;
            mainProgram = "aiw";
          };
        };

        packages.default = config.packages.ai-workspace;

        # Optional: prefect package (heavier)
        packages.ai-workspace-full = pythonPkgs.buildPythonPackage {
          pname = "ai-workspace-full";
          version = "0.1.0";
          src = ./.;
          pyproject = true;

          nativeBuildInputs = with pythonPkgs; [
            setuptools
          ];

          propagatedBuildInputs = with pythonPkgs; [
            typer
            rich
            httpx
            openai
            ollama
            pydantic
            pydantic-settings
            pyyaml
            python-dotenv
            beautifulsoup4
            lxml
            psycopg2
            pgvector
            crewai
            huey
            sentence-transformers
            prefect
          ];

          doCheck = false;

          meta = with pkgs.lib; {
            description = "AI Workspace (full: includes Prefect scheduling)";
            license = licenses.mit;
            mainProgram = "aiw";
          };
        };

        # Formatter
        treefmt = {
          projectRootFile = "flake.nix";
          programs = {
            alejandra.enable = true;
            ruff-format.enable = true;
          };
        };
      };
    };
}
