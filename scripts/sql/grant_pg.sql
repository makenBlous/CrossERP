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
GRANT SELECT ON TABLE public.alembic_version TO crosserp_app;
-- 显式列出业务表，授权覆盖守卫可在新增迁移时提醒补充。
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.approval, public.api_token,
  public.app_setting, public.app_user, public.audit_checkpoint, public.audit_export,
  public.audit_head, public.audit_log, public.eval_run, public.export_artifact,
  public.fee, public.fee_reference, public.fx_rate, public.import_batch, public.issue,
  public.llm_alert, public.llm_budget, public.llm_call, public.llm_tool_call,
  public.idempotency_key, public.match, public.order_line, public.profit_snapshot, public.prompt_version,
  public.raw_row, public.recon_run, public.security_event, public.settlement,
  public.settlement_line, public.sku, public.sku_cost, public.store, public.user_role,
  public.password_reset_token, public.file_object, public.job, public.document_link, public.delegation,
  public.user_session, public.voucher, public.voucher_line TO crosserp_app;
  public.user_session, public.voucher, public.voucher_line, public.entity_version,
  public.action_execution, public.entity_event TO crosserp_app;
  public.user_session, public.voucher, public.voucher_line, public.iam_role,
  public.iam_permission_override, public.iam_temporary_grant, public.iam_field_policy,
  public.iam_data_scope_rule, public.iam_access_review, public.iam_sod_rule,
  public.iam_module_switch, public.iam_dictionary, public.iam_role_permission,
  public.iam_role_inheritance, public.iam_system_setting TO crosserp_app;
  public.user_session, public.voucher, public.voucher_line, public.approval_type,
  public.workflow_rule, public.audit_alert, public.retention_policy, public.audit_archive_run,
  public.cleansing_issue, public.mapping_rule, public.cleansing_issue_transfer TO crosserp_app;
REVOKE UPDATE, DELETE ON TABLE public.audit_log FROM crosserp_app;
GRANT SELECT, INSERT ON TABLE public.audit_log TO crosserp_app;
REVOKE UPDATE, DELETE ON TABLE public.audit_head FROM crosserp_app;
GRANT SELECT, UPDATE ON TABLE public.audit_head TO crosserp_app;
REVOKE UPDATE, DELETE ON TABLE public.audit_checkpoint, public.audit_export FROM crosserp_app;
GRANT SELECT, INSERT ON TABLE public.audit_checkpoint, public.audit_export TO crosserp_app;
GRANT SELECT, INSERT ON TABLE public.eval_run TO crosserp_app;
REVOKE UPDATE, DELETE ON TABLE public.security_event FROM crosserp_app;
GRANT SELECT, INSERT ON TABLE public.security_event TO crosserp_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.voucher, public.voucher_line,
  public.prompt_version, public.llm_call, public.llm_tool_call, public.llm_budget,
  public.llm_alert TO crosserp_app;
REVOKE DELETE ON TABLE public.app_user, public.user_role, public.user_session, public.api_token, public.app_setting FROM crosserp_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.app_user, public.user_role, public.user_session, public.api_token, public.app_setting TO crosserp_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO crosserp_agent;
GRANT SELECT ON TABLE public.approval, public.api_token, public.app_setting, public.app_user,
  public.audit_checkpoint, public.audit_export, public.audit_head, public.audit_log,
  public.eval_run, public.export_artifact, public.fee, public.fee_reference, public.fx_rate,
  public.import_batch, public.idempotency_key, public.issue, public.llm_alert, public.llm_budget, public.llm_call,
  public.llm_tool_call, public.match, public.order_line, public.profit_snapshot,
  public.prompt_version, public.raw_row, public.recon_run, public.security_event,
  public.settlement, public.settlement_line, public.sku, public.sku_cost, public.store,
  public.password_reset_token, public.file_object, public.job, public.document_link, public.delegation,
  public.user_role, public.user_session, public.voucher, public.voucher_line TO crosserp_agent;
  public.user_role, public.user_session, public.voucher, public.voucher_line,
  public.entity_version, public.action_execution, public.entity_event TO crosserp_agent;
  public.iam_role, public.iam_permission_override, public.iam_temporary_grant,
  public.iam_field_policy, public.iam_data_scope_rule, public.iam_access_review,
  public.iam_sod_rule, public.iam_module_switch, public.iam_dictionary,
  public.iam_role_permission, public.iam_role_inheritance, public.iam_system_setting TO crosserp_agent;
GRANT SELECT ON TABLE public.approval_type, public.workflow_rule, public.audit_alert,
  public.retention_policy, public.audit_archive_run, public.cleansing_issue,
  public.mapping_rule, public.cleansing_issue_transfer TO crosserp_agent;
REVOKE SELECT ON TABLE public.app_user, public.user_session, public.api_token FROM crosserp_agent;
GRANT SELECT ON TABLE public.eval_run, public.voucher, public.voucher_line,
  public.prompt_version, public.llm_call, public.llm_tool_call, public.llm_budget,
  public.llm_alert TO crosserp_agent;

ALTER DEFAULT PRIVILEGES FOR ROLE crosserp_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO crosserp_app;
ALTER DEFAULT PRIVILEGES FOR ROLE crosserp_owner IN SCHEMA public
  GRANT SELECT ON TABLES TO crosserp_agent;
