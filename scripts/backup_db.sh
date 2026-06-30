#!/usr/bin/env bash
set -euo pipefail

# Backup script for salon-manager PostgreSQL database.
# Usage:
#   ./scripts/backup_db.sh              # dev (Docker)
#   ./scripts/backup_db.sh --env prod   # prod (Docker)
#   ./scripts/backup_db.sh --keep 30    # keep last 30 backups (default: 10)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

ENV="dev"
KEEP=10

while [[ $# -gt 0 ]]; do
    case "$1" in
        --env) ENV="$2"; shift 2 ;;
        --keep) KEEP="$2"; shift 2 ;;
        *) echo "Nieznana opcja: $1"; exit 1 ;;
    esac
done

# Load env file
ENV_FILE="$ROOT_DIR/.env.$ENV"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "Błąd: nie znaleziono pliku $ENV_FILE"
    exit 1
fi

get_env_var() {
    grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2-
}

POSTGRES_USER=$(get_env_var POSTGRES_USER)
POSTGRES_DB=$(get_env_var POSTGRES_DB)
POSTGRES_PASSWORD=$(get_env_var POSTGRES_PASSWORD)

BACKUP_DIR="$ROOT_DIR/backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/salon_${ENV}_${TIMESTAMP}.sql.gz"

echo "Środowisko: $ENV"
echo "Baza danych: ${POSTGRES_DB:-salon}"
echo "Plik docelowy: $BACKUP_FILE"

COMPOSE_FILE="$ROOT_DIR/docker-compose.${ENV}.yml"
if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo "Błąd: nie znaleziono pliku $COMPOSE_FILE"
    exit 1
fi

if ! docker compose -f "$COMPOSE_FILE" ps --services --filter "status=running" 2>/dev/null | grep -q "^db$"; then
    echo "Błąd: kontener 'db' nie działa. Uruchom: docker compose -f docker-compose.${ENV}.yml up -d db"
    exit 1
fi

docker compose -f "$COMPOSE_FILE" exec -T db \
    pg_dump -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-salon}" \
    | gzip > "$BACKUP_FILE"

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "Backup gotowy: $BACKUP_FILE ($SIZE)"

# Remove old backups, keep last $KEEP files
OLD_COUNT=$(find "$BACKUP_DIR" -name "salon_${ENV}_*.sql.gz" | sort | wc -l | tr -d ' ')
if [[ "$OLD_COUNT" -gt "$KEEP" ]]; then
    REMOVE=$((OLD_COUNT - KEEP))
    find "$BACKUP_DIR" -name "salon_${ENV}_*.sql.gz" | sort | head -n "$REMOVE" | while read -r f; do
        echo "Usuwam stary backup: $(basename "$f")"
        rm "$f"
    done
fi

echo "Backupy zachowane: $(find "$BACKUP_DIR" -name "salon_${ENV}_*.sql.gz" | wc -l | tr -d ' ')/$KEEP"
