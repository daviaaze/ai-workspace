# OmniRoute NixOS Setup

## Overview

OmniRoute (`diegosouzapw/omniroute:main-web`) runs as a Docker container on
**dvision-homelab** with the web profile (Chromium/Playwright for web-cookie
providers). Pi on the thinkbook connects to it remotely via Tailscale.

## URLs

| Service     | URL                                                |
|-------------|----------------------------------------------------|
| Dashboard   | https://omniroute.dvision-homelab.daviaaze.com      |
| API (v1)    | https://omniroute.dvision-homelab.daviaaze.com/v1   |
| Direct (TS) | http://dvision-homelab:20128/v1                     |

## Files

- **Nix service:** `hosts/dvision-homelab/services/omniroute.nix`
- **Service registry:** `hosts/dvision-homelab/services/default.nix`
- **Traefik routing:** `hosts/dvision-homelab/services/web-servers.nix`
- **Homepage widget:** `hosts/dvision-homelab/services/homepage-dashboard.nix`
- **Pi provider:** `~/.pi/agent/models.json` (provider: `omniroute`)
- **Pi settings:** `~/.pi/agent/settings.json` (enabledModels: `omniroute/auto*`)

## First-Time Setup

### 1. Generate secrets

```bash
# Generate JWT secret
openssl rand -base64 48

# Generate API key encryption secret
openssl rand -hex 32

# Pick a strong initial password for the dashboard
# (e.g., use a password manager generated one)
```

### 2. Add to sops

```bash
cd /home/daviaaze/nixfiles
sops secrets/secrets.yaml
```

Add these keys:

```yaml
omniroute_jwt_secret: <base64 from step 1>
omniroute_api_key_secret: <hex from step 1>
omniroute_initial_password: <your-password>
```

### 3. Deploy

```bash
nixos-rebuild switch --flake .#dvision-homelab
```

### 4. Access dashboard

Open https://omniroute.dvision-homelab.daviaaze.com
Login with the `INITIAL_PASSWORD`, then change it immediately in
Dashboard → Settings → Security.

### 5. Configure providers in OmniRoute

From the dashboard, add the providers you want to use. Good starting options:

- **Ollama** → `http://dvision-homelab:11434` (local models)
- **Claude Code (OAuth)** → built-in support
- **Codex (OpenAI)** → built-in support
- **Any API key providers** you have (OpenAI, Anthropic, Groq, etc.)

## Pi Usage

Pi is configured with the `omniroute` provider and these models:

| Model ID           | Description                     |
|--------------------|---------------------------------|
| `omniroute/auto`   | Balanced (sticky to last good)  |
| `omniroute/auto/cheap` | Cheapest per token          |
| `omniroute/auto/fast` | Lowest latency              |
| `omniroute/auto/coding` | Quality-first for code     |
| `omniroute/auto/offline` | Most quota remaining      |
| `omniroute/auto/smart` | Quality + 10% exploration  |

To use OmniRoute as default, set in settings.json:

```json
{
  "defaultProvider": "omniroute",
  "defaultModel": "omniroute/auto"
}
```

## Maintenance

- Container auto-pulls `:main-web` on restart (`--pull=always`)
- Persistent data lives in `/var/lib/omniroute/` on the homelab
- Logs: `docker logs omniroute`

## Troubleshooting

1. **Container not starting**: Check `docker logs omniroute`
2. **sops secrets not found**: Run `sops secrets/secrets.yaml` to verify keys exist
3. **pi can't reach OmniRoute**: Check Tailscale connectivity between hosts
   - `tailscale status` on thinkbook
   - `curl http://dvision-homelab:20128/v1/models` from thinkbook
4. **Traefik cert issues**: Check `docker logs traefik` for ACME errors
