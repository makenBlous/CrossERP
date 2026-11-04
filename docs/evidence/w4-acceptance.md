# W4 验收证据

| 项目 | 结果 | 证据 |
|---|---|---|
| 不审批不写出 | 通过 | `tests/guard/test_denials.py`，无 token、驳回、内容变化、重复使用均拒绝 |
| 审计哈希链 | 通过 | `crosserp audit verify`，`tests/integration/test_audit_chain.py` |
| app 账号不能改审计 | 通过 | T30 MySQL/PG `tests/integration/test_grants.py` |
| agent 账号只读 | 通过 | T30 `tests/integration/test_readonly_session.py` 和守卫测试 |
| 审计包离线校验 | 通过 | `tests/unit/test_offline_verify.py`、`tests/integration/test_audit_export.py`；CLI 导出后 verify-export 通过 |
| 凭证字段 | 未实现 | W6 才有凭证；本阶段用期间利润报表审批+导出代替 |
