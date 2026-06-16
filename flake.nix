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
    crawl4ai-flake = {
      url = "github:daviaaze/crawl4ai-flake";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = inputs @ {flake-parts, crawl4ai-flake, ...}:
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
        crawl4ai = crawl4ai-flake.packages.${system}.crawl4ai;
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
            plotly
            pandas
            crawl4ai
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
            crawl4ai
          ];

          doCheck = false;

          meta = with pkgs.lib; {
            description = "AI Workspace (full: includes Prefect scheduling)";
            license = licenses.mit;
            mainProgram = "aiw";
          };
        };

        # Pi setup deploy — symlinks pi-setup/ into ~/.pi/agent/
        packages.pi-setup-deploy = pkgs.writeShellScriptBin "pi-setup-deploy" ''
          set -euo pipefail
          PI_DIR="''${PI_DIR:-$HOME/.pi/agent}"
          PI_SETUP_DIR="${./pi-setup}"

          mkdir -p "$PI_DIR/skills" "$PI_DIR/rules" "$PI_DIR/prompts" "$PI_DIR/extensions"

          for skill_dir in "$PI_SETUP_DIR/skills"/*/; do
            name="$(basename "$skill_dir")"
            mkdir -p "$PI_DIR/skills/$name"
            for f in "$skill_dir"/*; do
              base="$(basename "$f")"
              ln -sf "$f" "$PI_DIR/skills/$name/$base"
            done
          done

          for rule in "$PI_SETUP_DIR/rules"/*.md; do
            ln -sf "$rule" "$PI_DIR/rules/$(basename "$rule")"
          done

          for prompt in "$PI_SETUP_DIR/prompts"/*.md; do
            ln -sf "$prompt" "$PI_DIR/prompts/$(basename "$prompt")"
          done

          for ext in "$PI_SETUP_DIR/extensions"/*.ts; do
            ln -sf "$ext" "$PI_DIR/extensions/$(basename "$ext")"
          done

          echo "Pi setup deployed to $PI_DIR"
        '';

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
