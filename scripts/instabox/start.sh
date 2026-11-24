#!/bin/sh
set -eu

cd "$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
test -f .env.instabox || {
  echo "Missing .env.instabox. Restore the deployment configuration first." >&2
  exit 1
}

docker compose -f docker-compose.instabox.yml up -d --wait --wait-timeout 120
instabox-port publish 8180 --name 'BookPath AI'
