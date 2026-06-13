# Module: ai-workspace
# Adds AI Workspace to NixOS/home-manager with:
# - aiw CLI tool (Huey-based scheduling + Langtrace telemetry)
# - Systemd service for the Huey worker (runs periodic tasks)
# - PostgreSQL integration (optional)
# - Obsidian integration (optional)

{
  config,
  lib,
  pkgs,
  ...
}:
with lib; let
  cfg = config.features.ai-workspace;
  
  aiwPackage = pkgs.callPackage ./package.nix {};
in {
  options.features.ai-workspace = {
    enable = mkEnableOption "AI Workspace - deep search, agent swarm, knowledge base";

    database = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Enable PostgreSQL database for knowledge storage";
      };
      url = mkOption {
        type = types.str;
        default = "postgresql:///ai_workspace";
        description = "Database connection URL";
      };
    };

    obsidian = {
      enable = mkEnableOption "Obsidian vault integration";
      vaultPath = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "Path to Obsidian vault";
      };
    };

    telemetry = {
      enable = mkEnableOption "Langtrace telemetry for agent tracing";
    };

    # Periodic schedules (built into Huey worker)
    worker = {
      enable = mkEnableOption "Huey worker (runs periodic tasks)";
    };
  };

  config = mkIf cfg.enable {
    # Install AI Workspace package
    environment.systemPackages = [aiwPackage];

    # Environment variable for database
    environment.variables.AIW_DB_URL = mkIf cfg.database.enable cfg.database.url;

    # Obsidian vault path
    environment.variables.AIW_OBSIDIAN_VAULT = mkIf (cfg.obsidian.enable && cfg.obsidian.vaultPath != null)
      cfg.obsidian.vaultPath;

    # PostgreSQL integration
    services.postgresql = mkIf cfg.database.enable {
      enable = mkDefault true;
      ensureDatabases = ["ai_workspace"];
      ensureUsers = [{
        name = "ai_workspace";
        ensureDBOwnership = true;
      }];
      extensions = ps: [ps.pgvector];
    };

    # Systemd service: Huey worker (processes periodic tasks + enqueued jobs)
    systemd.services.aiw-worker = mkIf cfg.worker.enable {
      description = "AI Workspace - Huey Task Worker";
      after = ["network.target" "postgresql.service"];
      wants = ["postgresql.service"];
      wantedBy = ["multi-user.target"];

      script = ''
        exec ${aiwPackage}/bin/aiw worker
      '';

      serviceConfig = {
        Type = "simple";
        User = "daviaaze";
        Restart = "on-failure";
        RestartSec = "10s";
        Environment = [
          "AIW_DB_URL=${cfg.database.url}"
        ] ++ lib.optional (cfg.obsidian.vaultPath != null) 
          "AIW_OBSIDIAN_VAULT=${cfg.obsidian.vaultPath}";

        # Logging
        StandardOutput = "journal";
        StandardError = "journal";
      };
    };

    # Shell aliases for convenience (via fish/bash)
    programs.fish.shellAliases = mkIf (config.programs.fish.enable or false) {
      aiw-s = "aiw search";
      aiw-a = "aiw ask";
      aiw-t = "aiw task list";
      aiw-ta = "aiw task add";
      aiw-due = "aiw task due";
      aiw-w = "aiw worker";
      aiw-telem = "aiw telemetry";
    };
  };
}
