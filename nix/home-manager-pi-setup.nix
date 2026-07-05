{ config, lib, pkgs, ... }:

let
  inherit (lib) mkIf mkOption types;
  cfg = config.programs.pi-setup;
  piSetupDir = ../../../pi-setup;
  deployScript = pkgs.writeShellScript "activate-pi-setup" ''
    set -euo pipefail
    PI_DIR="$HOME/.pi/agent"
    exec "${piSetupDir}/deploy.sh"
  '';
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
      deployScript
    ];

    # Deploy on home-manager activation via canonical deploy.sh
    home.activation.piSetup = lib.hm.dag.entryAfter ["writeBoundary"] (
      pkgs.lib.optionalString cfg.enable ''
        $DRY_RUN_CMD ${deployScript}
      ''
    );
  };
}
