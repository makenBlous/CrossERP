#!/bin/sh
set -eu

attempt=1
while :; do
    if printf '%s\n%s\n' "$CROSSERP_ADMIN_PASSWORD" "$CROSSERP_ADMIN_PASSWORD" \
        | crosserp init --admin-username "$CROSSERP_ADMIN_USERNAME" --admin-password-stdin; then
        break
    fi
    if [ "$attempt" -ge 30 ]; then
        echo "数据库未能在 30 次尝试内就绪" >&2
        exit 1
    fi
    attempt=$((attempt + 1))
    sleep 2
done

case "$CROSSERP_DATABASE_URL" in
    postgresql+psycopg://*)
        python /app/scripts/render_grant_sql.py /app/scripts/sql/grant_pg.sql \
            | PGPASSWORD="$POSTGRES_PASSWORD" psql --host=postgres --port=5432 \
                --username="${POSTGRES_USER:-postgres}" --dbname="${POSTGRES_DB:-crosserp}" \
                -v ON_ERROR_STOP=1
        ;;
    mysql+pymysql://*)
        python /app/scripts/render_grant_sql.py /app/scripts/sql/grant_mysql.sql \
            | mysql --protocol=tcp --host=mysql --user=root --password="$MYSQL_ROOT_PASSWORD" crosserp
        ;;
    sqlite:///*)
        : # SQLite 没有账号权限脚本。
        ;;
    *)
        echo "不支持的 CROSSERP_DATABASE_URL: $CROSSERP_DATABASE_URL" >&2
        exit 1
        ;;
esac
