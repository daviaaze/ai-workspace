# Development shell for AI Workspace
# Resolves binary dependencies (numpy, crewai) without reinstalling NixOS
{
  pkgs ? import <nixpkgs> {},
}:
pkgs.mkShell {
  name = "ai-workspace-dev";

  buildInputs = with pkgs; [
    python3
    uv
    postgresql
  ];

  # Fix numpy/crewai binary dependencies on NixOS
  LD_LIBRARY_PATH = "${pkgs.stdenv.cc.cc.lib}/lib";

  shellHook = ''
    echo "🖥️  AI Workspace dev shell"
    echo ""
    echo "  Setup:"
    echo "    createdb ai_workspace        # Create PostgreSQL DB"
    echo "    python3 -m venv .venv        # Create virtualenv"
    echo "    source .venv/bin/activate    # Activate"
    echo "    pip install -e .             # Install in dev mode"
    echo "    aiw init                     # Initialize DB tables"
    echo ""
    echo "  Test:"
    echo "    aiw models                   # List Ollama models"
    echo "    aiw ask 'explain Nix flakes' # Quick chat test"
    echo "    aiw search 'rust vs go'      # Deep research test"
    echo "    aiw tui                      # Terminal dashboard"
  '';
}
