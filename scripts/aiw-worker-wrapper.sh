#!/usr/bin/env bash
# Wrapper for aiw worker — ensures nix libraries are available.
# Used by systemd --user service.

# Source nix profile for libraries
if [ -f /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh ]; then
    source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
fi

# Add user nix profile
export PATH="$HOME/.nix-profile/bin:$PATH"
export NIX_PROFILES="/nix/var/nix/profiles/default $HOME/.nix-profile"

# Enter a nix shell with the needed libraries and run the worker
exec nix-shell \
    -p python313 \
    -p python313Packages.pip \
    -p python313Packages.psycopg2 \
    -p python313Packages.numpy \
    -p stdenv.cc.cc-lib \
    -p openssl \
    --run "cd $HOME/Projects/ai-workspace && exec .venv/bin/aiw worker"
