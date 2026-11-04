-- CrossERP PostgreSQL 18 权限模板。
-- 执行前把 __OWNER_PASSWORD__ / __APP_PASSWORD__ / __AGENT_PASSWORD__ 替换在临时文件里；不要提交替换后的文件。
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'crosserp_owner') THEN
    CREATE ROLE crosserp_owner LOGIN PASSWORD '__OWNER_PASSWORD__';
  ELSE
    ALTER ROLE crosserp_owner PASSWORD '__OWNER_PASSWORD__';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'crosserp_app') THEN
    CREATE ROLE crosserp_app LOGIN PASSWORD '__APP_PASSWORD__';
  ELSE
    ALTER ROLE crosserp_app PASSWORD '__APP_PASSWORD__';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'crosserp_agent') THEN
    CREATE ROLE crosserp_agent LOGIN PASSWORD '__AGENT_PASSWORD__';
  ELSE
    ALTER ROLE crosserp_agent PASSWORD '__AGENT_PASSWORD__';
  END IF;
END $$;

GRANT CONNECT ON DATABASE crosserp TO crosserp_app, crosserp_agent;
GRANT USAGE ON SCHEMA public TO crosserp_app, crosserp_agent;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO crosserp_owner;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO crosserp_owner;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO crosserp_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO crosserp_app;
REVOKE UPDATE, DELETE ON TABLE public.audit_log FROM crosserp_app;
GRANT SELECT, INSERT ON TABLE public.audit_log TO crosserp_app;
REVOKE UPDATE, DELETE ON TABLE public.audit_head FROM crosserp_app;
GRANT SELECT, UPDATE ON TABLE public.audit_head TO crosserp_app;
REVOKE UPDATE, DELETE ON TABLE public.audit_checkpoint, public.audit_export FROM crosserp_app;
GRANT SELECT, INSERT ON TABLE public.audit_checkpoint, public.audit_export TO crosserp_app;
REVOKE DELETE ON TABLE public.app_user, public.user_role, public.user_session, public.api_token, public.app_setting FROM crosserp_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.app_user, public.user_role, public.user_session, public.api_token, public.app_setting TO crosserp_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO crosserp_agent;
REVOKE SELECT ON TABLE public.app_user, public.user_session, public.api_token FROM crosserp_agent;

ALTER DEFAULT PRIVILEGES FOR ROLE crosserp_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO crosserp_app;
ALTER DEFAULT PRIVILEGES FOR ROLE crosserp_owner IN SCHEMA public
  GRANT SELECT ON TABLES TO crosserp_agent;
