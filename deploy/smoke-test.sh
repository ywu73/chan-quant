#!/usr/bin/env sh
set -eu

base_url="${CHAN_QUANT_SMOKE_BASE_URL:-http://127.0.0.1:8080}"
username="${CHAN_QUANT_BASIC_AUTH_USER:?set CHAN_QUANT_BASIC_AUTH_USER}"
password="${CHAN_QUANT_BASIC_AUTH_PASSWORD:?set CHAN_QUANT_BASIC_AUTH_PASSWORD}"

unauthenticated_status="$(curl --silent --output /dev/null --write-out '%{http_code}' "${base_url}/")"
test "${unauthenticated_status}" = "401"

for path in / /search /compare /indices /methodology; do
  body="$(curl --fail --silent --show-error --user "${username}:${password}" "${base_url}${path}")"
  printf '%s' "${body}" | grep --quiet 'name="chan-quant-app"'
done

curl --fail --silent --show-error --user "${username}:${password}" \
  "${base_url}/healthz" | grep --quiet '"status":"alive"'
curl --fail --silent --show-error --user "${username}:${password}" \
  "${base_url}/readyz" | grep --quiet '"status":"ready"'
curl --fail --silent --show-error --user "${username}:${password}" \
  "${base_url}/version" | grep --quiet '"release_sha"'

refresh_status="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --user "${username}:${password}" \
  "${base_url}/api/v1/market-breadth?market=CN_A_SH_SZ_V1&refresh=true")"
test "${refresh_status}" = "403"

printf '%s\n' "container smoke checks passed"
