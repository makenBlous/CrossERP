# CrossERP 数据库账号权限

生产环境建议用三个账号：`crosserp_owner` 只负责迁移，`crosserp_app` 运行应用，`crosserp_agent` 只读查询。仓库里的 SQL 是模板，密码占位符只能在本地临时文件中替换，不能提交替换后的文件。

MySQL 8.4 执行：

```bash
sed -e 's/__OWNER_PASSWORD__/临时密码1/g' \
    -e 's/__APP_PASSWORD__/临时密码2/g' \
    -e 's/__AGENT_PASSWORD__/临时密码3/g' \
    scripts/sql/grant_mysql.sql > /tmp/crosserp-grant.sql
mysql -h 127.0.0.1 -u root -p crosserp < /tmp/crosserp-grant.sql
```

PostgreSQL 18：

```bash
sed -e 's/__OWNER_PASSWORD__/临时密码1/g' \
    -e 's/__APP_PASSWORD__/临时密码2/g' \
    -e 's/__AGENT_PASSWORD__/临时密码3/g' \
    scripts/sql/grant_pg.sql > /tmp/crosserp-grant.sql
PGPASSWORD=管理员密码 psql -h 127.0.0.1 -U postgres -d crosserp -f /tmp/crosserp-grant.sql
```

配置应用和智能体：

```bash
export CROSSERP_DATABASE_URL='mysql+pymysql://crosserp_app:密码@127.0.0.1:3306/crosserp?charset=utf8mb4'
export CROSSERP_MIGRATE_DATABASE_URL='mysql+pymysql://crosserp_owner:密码@127.0.0.1:3306/crosserp?charset=utf8mb4'
export CROSSERP_AGENT_DATABASE_URL='mysql+pymysql://crosserp_agent:密码@127.0.0.1:3306/crosserp?charset=utf8mb4'
```

SQLite 没有账号权限。只读会话会用 `mode=ro` 打开文件，能防止应用代码误写，但不能提供 MySQL/PG 那种审计表权限隔离；生产请使用 MySQL 8.4 或 PostgreSQL 18。W5/T31 新建表后必须重跑授权脚本；MySQL 没有 PostgreSQL 的默认权限机制，新增迁移后必须重跑授权脚本。应用账号对 `app_user`、`user_role`、`user_session`、`api_token`、`app_setting` 只有 SELECT/INSERT/UPDATE，智能体账号不读取密码哈希、会话或 API token。
