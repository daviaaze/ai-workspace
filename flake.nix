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
        
        # browser-use SDK (lightweight, only needs httpx + pydantic)
        browser-use-sdk = pythonPkgs.buildPythonPackage rec {
          pname = "browser-use-sdk";
          version = "3.8.4";
          format = "pyproject";
          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/1e/5b/9f52925c3dc1bc651a67031c3d456ce39731fbca870be55b3fedd5555498/browser_use_sdk-3.8.4.tar.gz";
            hash = "sha256-nbq8iXHmdsjEVLh3uocUKnzrw5wrTCiI/xatO+0UEvY=";
          };
          propagatedBuildInputs = with pythonPkgs; [ pydantic httpx ];
          nativeBuildInputs = with pythonPkgs; [ hatchling ];
          doCheck = false;
        };

        # browser-use — uses nixpkgs playwright + chromium (no pip binaries)
        browser-use = pythonPkgs.buildPythonPackage rec {
          pname = "browser-use";
          version = "0.9.7";
          format = "pyproject";
          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/a2/b5/c8cc6255373d3f7bb20d50068cbf8ebbb8e01dcd12d081019a8ea60d692a/browser_use-0.9.7.tar.gz";
            hash = "sha256-ASaCA9GESw9TB4hxxa9FEFcymAjs+KybQ/qt9FIgHaE=";
          };
          # Remove strict version pins and optional deps that aren't in nixpkgs
          postPatch = ''
            substituteInPlace pyproject.toml \
              --replace-fail 'aiohttp==3.12.15' 'aiohttp' \
              --replace-fail 'httpx>=0.28.1' 'httpx'
          '';
          propagatedBuildInputs = with pythonPkgs; [
            aiohttp
            httpx
            openai
            pydantic
            playwright
            python-dotenv
            rich
            screeninfo
            grpcio
            protobuf
            websockets
            browser-use-sdk
          ];
          nativeBuildInputs = with pythonPkgs; [ hatchling ];
          # Optional deps not in nixpkgs — removed from dependency checking
          pythonRemoveDeps = [
            "anthropic" "authlib" "bubus" "cdp-use" "click" "cloudpickle"
            "google-api-core" "google-api-python-client" "google-auth-oauthlib"
            "google-auth" "google-genai" "groq" "inquirerpy" "markdownify"
            "mcp" "ollama" "pillow" "portalocker" "posthog" "psutil"
            "pyotp" "pypdf" "python-docx" "reportlab" "requests" "uuid7"
          ];
          doCheck = false;
        };

        # Small missing deps for browser-use
        uuid7 = pythonPkgs.buildPythonPackage rec {
          pname = "uuid7";
          version = "0.1.0";
          format = "pyproject";
          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/5c/19/7472bd526591e2192926247109dbf78692e709d3e56775792fec877a7720/uuid7-0.1.0.tar.gz";
            hash = "sha256-jFeqMu50VtPMaMlcRTC8VxZG3vrAGJXPxzVFRJiUpjw=";
          };
          nativeBuildInputs = with pythonPkgs; [ setuptools ];
          doCheck = false;
        };

        cdp-use = pythonPkgs.buildPythonPackage rec {
          pname = "cdp-use";
          version = "1.4.5";
          format = "pyproject";
          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/f7/7a/c549417e8c5e4dface6d5d828cd7dc72502dcea33a99f5324abf5a853ce9/cdp_use-1.4.5.tar.gz";
            hash = "sha256-DaOjLfRjNqA/9aIrxrxELNfS8tUKEY/UhW8p039tJqA=";
          };
          propagatedBuildInputs = with pythonPkgs; [ httpx websockets ];
          pythonRemoveDeps = [ "typing-extensions" ];
          nativeBuildInputs = with pythonPkgs; [ hatchling ];
          doCheck = false;
        };

        bubus = pythonPkgs.buildPythonPackage rec {
          pname = "bubus";
          version = "1.5.6";
          format = "pyproject";
          src = pkgs.fetchPypi {
            inherit pname version;
            hash = "sha256-GlRW8KV26GYTp71m6BmJG2d3eDILbikQlOM5sNnfLg0=";
          };
          propagatedBuildInputs = with pythonPkgs; [
            pydantic portalocker uuid7
          ];
          pythonRemoveDeps = [ "aiofiles" "anyio" "typing-extensions" ];
          nativeBuildInputs = with pythonPkgs; [ hatchling ];
          doCheck = false;
        };
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
            playwright
            browser-use
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

        packages.browser-use-sdk = browser-use-sdk;
        packages.browser-use = browser-use;
        packages.uuid7 = uuid7;
        packages.cdp-use = cdp-use;
        packages.bubus = bubus;

        # Full Python environment with all packages (for testing imports)
        packages.python-with-packages = pythonPkgs.python.withPackages (ps:
          [ ps.python-dotenv ps.aiohttp ps.httpx ps.openai ps.pydantic
            ps.pydantic-settings ps.playwright ps.rich ps.screeninfo
            ps.grpcio ps.protobuf ps.websockets ps.psutil ps.pillow
            ps.portalocker ps.requests ps.cloudpickle ps.inquirerpy
            ps.markdownify ps.pyotp ps.pypdf ps.python-docx ps.reportlab
            ps.posthog ps.anthropic
            browser-use-sdk cdp-use bubus uuid7 browser-use
          ]
        );

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
