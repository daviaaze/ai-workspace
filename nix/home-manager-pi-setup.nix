{ config, lib, pkgs, ... }:

let
  inherit (lib) mkIf mkOption types;
  cfg = config.programs.pi-setup;
in {
  options.programs.pi-setup = {
    enable = mkOption {
      type = types.bool;
      default = false;
      description = "Enable deploying pi-setup assets to ~/.pi/agent/";
    };
  };

  config = mkIf cfg.enable {
    home.packages = [
      (pkgs.writeShellScriptBin "pi-setup-deploy" ''
        set -euo pipefail
        PI_DIR="''${PI_DIR:-$HOME/.pi/agent}"
        PI_SETUP_DIR="${../../../pi-setup}"
        exec "$PI_SETUP_DIR/deploy-pi-setup.sh" "$PI_SETUP_DIR"
      '')
    ];

    # Deploy on home-manager activation
    home.activation.piSetup = lib.hm.dag.entryAfter ["writeBoundary"] (
      pkgs.lib.optionalString cfg.enable ''
        $DRY_RUN_CMD ${pkgs.writeShellScript "activate-pi-setup" ''
          PI_DIR="$HOME/.pi/agent"
          PI_SETUP_DIR="${../../../pi-setup}"
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
        ''}
      ''
    );
  };
}
