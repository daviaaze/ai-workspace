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

  meta = with lib; {
    description = "AI Workspace - Deep search, agent swarm, knowledge base, telemetry";
    license = licenses.mit;
    mainProgram = "aiw";
    platforms = platforms.linux;
  };
}
