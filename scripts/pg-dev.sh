#!/usr/bin/env bash
# Dev PostgreSQL 17 + pgvector launcher for AI Workspace RAG.
#
# Usage:
#   scripts/pg-dev.sh start    # Start PG on port 5439, socket in /tmp/aiw-pg
#   scripts/pg-dev.sh stop     # Stop PG
#   scripts/pg-dev.sh status   # Show status
#   scripts/pg-dev.sh psql     # Open psql session
#
# The data directory is at ~/.aiw/pgdata (gitignored).

set -euo pipefail

PG_BUNDLE="${PG_BUNDLE:-/nix/store/cbxd8m06aymk3nb4w6i7fbkiix3lh3dg-postgresql-and-plugins-17.10}"

# Ensure PG bundle is available (rebuild if GC'd)
if [[ ! -d "${PG_BUNDLE}" ]]; then
    echo "Building PostgreSQL 17 + pgvector..."
    PG_BUNDLE=$(nix build --no-link --print-out-paths --impure --expr '
        let pkgs = import <nixpkgs> {}; in
        pkgs.postgresql_17.withPackages (p: [ p.pgvector ])
    ' 2>/dev/null)
    if [[ -z "${PG_BUNDLE}" ]]; then
        echo "ERROR: Could not build PostgreSQL + pgvector. Install nixpkgs first."
        exit 1
    fi
fi
DATA_DIR="${HOME}/.aiw/pgdata"
LOG_FILE="${HOME}/.aiw/pg.log"
SOCKET_DIR="/tmp/aiw-pg"
PORT=5439
DB_NAME="aiw_rag"

export PATH="${PG_BUNDLE}/bin:${PATH}"

init() {
    if [[ ! -d "${DATA_DIR}" ]]; then
        mkdir -p "${DATA_DIR}" "${SOCKET_DIR}"
        initdb -D "${DATA_DIR}" --locale=C --encoding=UTF8
        echo "PG data dir initialized at ${DATA_DIR}"
    fi
    # Always ensure socket dir exists
    mkdir -p "${SOCKET_DIR}"
}

start() {
    if status --quiet 2>/dev/null; then
        echo "PostgreSQL is already running (port ${PORT})"
        return 0
    fi
    init
    pg_ctl -D "${DATA_DIR}" \
        -o "-p ${PORT} -k ${SOCKET_DIR}" \
        -l "${LOG_FILE}" start
    sleep 2
    ensure_db
    ensure_extensions
    echo "PostgreSQL 17 + pgvector ready on port ${PORT}"
}

stop() {
    if status --quiet 2>/dev/null; then
        pg_ctl -D "${DATA_DIR}" stop
        echo "PostgreSQL stopped"
    else
        echo "PostgreSQL is not running"
    fi
}

status() {
    if pg_isready -h "${SOCKET_DIR}" -p "${PORT}" >/dev/null 2>&1; then
        if [[ "${1:-}" != "--quiet" ]]; then
            echo "PostgreSQL is running on port ${PORT}"
        fi
        return 0
    else
        if [[ "${1:-}" != "--quiet" ]]; then
            echo "PostgreSQL is not running"
        fi
        return 1
    fi
}

ensure_db() {
    if ! psql -h "${SOCKET_DIR}" -p "${PORT}" -d postgres -tAc \
        "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" 2>/dev/null | grep -q 1; then
        createdb -h "${SOCKET_DIR}" -p "${PORT}" "${DB_NAME}"
        echo "Created database: ${DB_NAME}"
    fi
}

ensure_extensions() {
    psql -h "${SOCKET_DIR}" -p "${PORT}" -d "${DB_NAME}" -c \
        "CREATE EXTENSION IF NOT EXISTS vector" >/dev/null 2>&1
    echo "pgvector extension ready"
}

psql_cmd() {
    exec psql -h "${SOCKET_DIR}" -p "${PORT}" -d "${DB_NAME}" "${@}"
}

case "${1:-}" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; sleep 1; start ;;
    status)  status ;;
    psql)    shift; psql_cmd "$@" ;;
    init)    init; ensure_extensions ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|psql|init}"
        exit 1
        ;;
esac
