# Development shell for AI Workspace
# Resolves binary dependencies (numpy, crewai) without reinstalling NixOS
{
  pkgs ? import <nixpkgs> {},
}:
let
  playwright-browsers = pkgs.playwright-driver.browsers;
in
pkgs.mkShell {
  name = "ai-workspace-dev";

  buildInputs = with pkgs; [
    python3
    python3Packages.playwright
    uv
    postgresql
    playwright-driver
    playwright-browsers
    chromium
    zlib
  ];

  # Fix numpy/crewai binary dependencies on NixOS
  LD_LIBRARY_PATH =
    "${pkgs.zlib}/lib:"
    + "${pkgs.stdenv.cc.cc.lib}/lib:"
    + "${pkgs.libglvnd}/lib:"
    + "${pkgs.xorg.libX11}/lib:"
    + "${pkgs.xorg.libXcomposite}/lib:"
    + "${pkgs.xorg.libXdamage}/lib:"
    + "${pkgs.xorg.libXext}/lib:"
    + "${pkgs.xorg.libXfixes}/lib:"
    + "${pkgs.xorg.libXrandr}/lib:"
    + "${pkgs.libxcb}/lib:"
    + "${pkgs.nss}/lib:"
    + "${pkgs.nspr}/lib:"
    + "${pkgs.cups}/lib:"
    + "${pkgs.dbus}/lib:"
    + "${pkgs.atk}/lib:"
    + "${pkgs.at-spi2-core}/lib:"
    + "${pkgs.at-spi2-atk}/lib:"
    + "${pkgs.gtk3}/lib:"
    + "${pkgs.pango}/lib:"
    + "${pkgs.cairo}/lib:"
    + "${pkgs.gdk-pixbuf}/lib:"
    + "${pkgs.freetype}/lib:";

  # Point Playwright to nix-provided browser binaries
  PLAYWRIGHT_BROWSERS_PATH = "${playwright-browsers}";
  PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = "1";

  shellHook = ''
    echo "🖥️  AI Workspace dev shell"
    echo "  Playwright browsers: ${playwright-browsers}"
    echo ""
    echo "  Setup:"
    echo "    pre-commit install          # Enable git hooks"
    echo "    createdb ai_workspace        # Create PostgreSQL DB"
    echo "    python3 -m venv .venv        # Create virtualenv"
    echo "    source .venv/bin/activate    # Activate"
    echo "    pip install -e .             # Install in dev mode"
    echo "    aiw init                     # Initialize DB tables"
    echo ""
    echo "  Test:"
    echo "    aiw models                   # List Ollama models"
    echo "    aiw search 'rust vs go'      # Deep research test"
    echo "    aiw tui                      # Terminal dashboard"
  '';
}
