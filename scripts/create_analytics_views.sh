#!/usr/bin/env bash
# Crée le schéma analytics (vues + droits) dans la base statistique.
# Utilisation : make views   (variables lues dans .env ; le compte doit pouvoir CRÉER des vues)
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a

: "${ADMIN_USER:?Définissez ADMIN_USER (compte autorisé à créer des vues, pas chatbot_ro)}"
export PGPASSWORD="${ADMIN_PASSWORD:?Définissez ADMIN_PASSWORD}"

for f in data/analytics/views/*.sql; do
  echo ">> $f"
  psql -h "${SRC_HOST:-localhost}" -p "${SRC_PORT:-5432}" -U "$ADMIN_USER" -d "${SRC_DB:-prod_mhm_ps}" \
       -v ON_ERROR_STOP=1 -f "$f"
done
echo "Vues créées. Lancez maintenant : make validate"
