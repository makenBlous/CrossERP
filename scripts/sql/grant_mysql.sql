-- CrossERP MySQL 8.4 权限模板。
-- 执行前把 __OWNER_PASSWORD__ / __APP_PASSWORD__ / __AGENT_PASSWORD__ 替换在临时文件里；不要提交替换后的文件。
CREATE USER IF NOT EXISTS 'crosserp_owner'@'%' IDENTIFIED BY '__OWNER_PASSWORD__';
CREATE USER IF NOT EXISTS 'crosserp_app'@'%' IDENTIFIED BY '__APP_PASSWORD__';
CREATE USER IF NOT EXISTS 'crosserp_agent'@'%' IDENTIFIED BY '__AGENT_PASSWORD__';

GRANT ALL PRIVILEGES ON crosserp.* TO 'crosserp_owner'@'%';
REVOKE ALL PRIVILEGES ON crosserp.* FROM 'crosserp_app'@'%';
-- MySQL 没有从 database 级授权中单独撤回某张表的 UPDATE。
-- 因此应用账号对业务表逐表授权，新增迁移后把新业务表补到这里并重跑脚本。
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.approval TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.export_artifact TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.fee TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.fee_reference TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.fx_rate TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.import_batch TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.issue TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.match TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.order_line TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.profit_snapshot TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.raw_row TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.recon_run TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.settlement TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.settlement_line TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.sku TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.sku_cost TO 'crosserp_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON crosserp.store TO 'crosserp_app'@'%';
GRANT SELECT, INSERT ON crosserp.audit_log TO 'crosserp_app'@'%';
GRANT SELECT, UPDATE ON crosserp.audit_head TO 'crosserp_app'@'%';
GRANT SELECT ON crosserp.* TO 'crosserp_agent'@'%';

-- security_event / audit_checkpoint / audit_export 在 W5/T31 创建。
-- 建表后重跑本文件，并按同样原则给 app SELECT/INSERT、agent SELECT。
FLUSH PRIVILEGES;
