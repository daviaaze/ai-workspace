{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "career-ops-mvp";
  buildInputs = [
    (pkgs.python311.withPackages (ps: with ps; [
      jobspy
      click
      jinja2
      pyyaml
      imaplib2
      beautifulsoup4
      requests
      lxml
      rich
    ]))
    pkgs.yt-dlp
  ];
  shellHook = ''
    echo "CareerOps MVP shell — Python 3.11 + JobSpy"
    export PYTHONPATH="/home/daviaaze/Projects/pessoal/ai-workspace/career-ops/src:$PYTHONPATH"
    export CAREER_OPS_HOME="/home/daviaaze/Projects/pessoal/ai-workspace/career-ops"
  '';
}
