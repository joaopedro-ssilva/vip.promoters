#!/bin/sh
# Backup do Postgres da stack do Docker Compose (formato custom do pg_dump, comprimido).
#
#   scripts/backup.sh                 # grava backups/vip-AAAAMMDD-HHMMSS.dump
#   scripts/backup.sh restaurar ARQ   # restaura ARQ por cima do banco atual (PERIGOSO)
#
# Em producao, prefira o backup automatico do Postgres gerenciado (Neon, RDS, Supabase...)
# e use este script como copia extra fora do provedor. Agende com cron, por exemplo:
#   15 3 * * * cd /srv/vip.promoters && scripts/backup.sh && find backups -mtime +14 -delete
# Os uploads (volume `uploads`) nao entram aqui: copie o volume ou use armazenamento de objetos.
set -eu
cd "$(dirname "$0")/.."
DB_USER="${POSTGRES_USER:-vip}"
DB_NAME="${POSTGRES_DB:-vip}"

if [ "${1:-}" = "restaurar" ]; then
  ARQ="${2:?informe o arquivo .dump}"
  echo "Restaurando $ARQ em $DB_NAME (o backend e o worker devem estar parados)..."
  docker compose exec -T db pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner < "$ARQ"
  echo "Restaurado. Rode 'docker compose run --rm migrate' para reaplicar o papel de aplicacao."
  exit 0
fi

mkdir -p backups
ARQ="backups/vip-$(date +%Y%m%d-%H%M%S).dump"
docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc > "$ARQ"
echo "Backup gravado em $ARQ ($(du -h "$ARQ" | cut -f1))"
