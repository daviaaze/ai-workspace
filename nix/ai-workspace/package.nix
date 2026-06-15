# Package definition for ai-workspace (Nix)
{
  lib,
  python3Packages,
}:
python3Packages.buildPythonPackage {
  pname = "ai-workspace";
  version = "0.1.0";
  src = ../..;

  pyproject = true;

  nativeBuildInputs = with python3Packages; [
    setuptools
  ];

  propagatedBuildInputs = with python3Packages; [
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
    # langtrace-python-sdk — not in nixpkgs yet, loaded via pip if needed
  ];

  doCheck = false;

  # Patch pyproject.toml to fix dependency names/constraints that differ
  # between the Python ecosystem and nixpkgs:
  # - crewai<1.0,>=0.80.0 → crewai (nixpkgs has 1.14.4, version constraint relaxed)
  # - mem0ai → removed (not in nixpkgs yet)
  # - psycopg2-binary → psycopg2 (nixpkgs naming)
  # - langtrace-python-sdk → removed (not in nixpkgs yet, loaded via pip if needed)
  prePatch = ''
    # Relax crewai constraint (nixpkgs has 1.x, project pins >=1.0)
    substituteInPlace pyproject.toml --replace-fail '"crewai[tools]>=1.0"' '"crewai"'
    # Remove mem0ai from dev deps (not in nixpkgs)
    substituteInPlace pyproject.toml --replace-fail '"mem0ai>=0.1.0",' '#'
    # Fix psycopg2-binary naming in optional postgres deps
    substituteInPlace pyproject.toml --replace-fail '"psycopg2-binary>=2.9.0",' '"psycopg2>=2.9.0",'
    # Remove langtrace from dev deps (not in nixpkgs)
    substituteInPlace pyproject.toml --replace-fail '"langtrace-python-sdk>=3.0.0",' '#'
  '';

  meta = with lib; {
    description = "AI Workspace - Deep search, agent swarm, knowledge base, telemetry";
    license = licenses.mit;
    mainProgram = "aiw";
    platforms = platforms.linux;
  };
}
