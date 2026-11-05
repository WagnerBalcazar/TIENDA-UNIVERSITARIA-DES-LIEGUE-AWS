#!/usr/bin/env bash
set -euo pipefail

command -v aws >/dev/null || { echo "Instala y configura AWS CLI primero." >&2; exit 1; }

read -r -s -p "Contraseña PostgreSQL (alfanumérica): " DB_PASSWORD
printf '\n'
read -r -s -p "Clave secreta Stripe (test o live): " STRIPE_SECRET
printf '\n'
DJANGO_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')"

put_parameter() {
  aws ssm put-parameter --name "$1" --type SecureString --value "$2" --overwrite >/dev/null
}

put_parameter /tienda/prod/database-password "$DB_PASSWORD"
put_parameter /tienda/prod/django-secret-key "$DJANGO_SECRET"
put_parameter /tienda/prod/stripe-secret-key "$STRIPE_SECRET"
unset DB_PASSWORD DJANGO_SECRET STRIPE_SECRET
echo "Parámetros SecureString guardados en SSM."
