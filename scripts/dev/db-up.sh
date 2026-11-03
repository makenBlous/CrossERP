#!/usr/bin/env bash
set -euo pipefail

mysql_name="crosserp-mysql"
postgres_name="crosserp-postgres"

start_container() {
  local name="$1"
  shift
  if docker container inspect "$name" >/dev/null 2>&1; then
    docker start "$name" >/dev/null
  else
    docker run -d --name "$name" "$@"
  fi
}

start_container "$mysql_name" \
  -p 13306:3306 \
  -e MYSQL_ROOT_PASSWORD=dev \
  -e MYSQL_DATABASE=crosserp \
  mysql:8.4 \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_0900_ai_ci

start_container "$postgres_name" \
  -p 15432:5432 \
  -e POSTGRES_PASSWORD=dev \
  -e POSTGRES_DB=crosserp \
  postgres:18

echo "MySQL 8.4: 127.0.0.1:13306 (root/dev)"
echo "PostgreSQL 18: 127.0.0.1:15432 (postgres/dev)"
