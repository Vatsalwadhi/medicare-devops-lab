#!/usr/bin/env bash
# Creates the medicare-secrets Secret once, with random values. Nothing secret is stored in Git.
set -euo pipefail
NS=medicare
if kubectl -n "$NS" get secret medicare-secrets >/dev/null 2>&1; then
  echo "Secret medicare-secrets already exists - keeping it"; exit 0
fi
DB_USER=medicare
DB_PASSWORD=$(openssl rand -hex 16)
PHI_KEY=$(python3 -c 'import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode())')
kubectl -n "$NS" create secret generic medicare-secrets \
  --from-literal=DB_USER="$DB_USER" \
  --from-literal=DB_PASSWORD="$DB_PASSWORD" \
  --from-literal=DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@postgres:5432/medicare" \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=PHI_ENCRYPTION_KEY="$PHI_KEY" \
  --from-literal=ADMIN_PASSWORD="Adm-$(openssl rand -hex 6)!A" \
  --from-literal=DOCTOR_PASSWORD="Doc-$(openssl rand -hex 6)!D"
echo "Secret medicare-secrets created"
