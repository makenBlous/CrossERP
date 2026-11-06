# 安全模型

## 权限与会话

网页默认只监听 `127.0.0.1`。对外监听必须放在 HTTPS 反向代理后，并设置 `CROSSERP_COOKIE_SECURE=1`。用户密码只保存 Argon2id 哈希；会话 token 只保存哈希，cookie 使用 HttpOnly、SameSite=Lax 和 CSRF token。连续 5 次失败会锁定账号 15 分钟，可用配置项调整。

角色权限由 `crosserp.auth.permissions` 的固定矩阵决定：`admin` 管理用户和设置，`operator` 处理导入与异常，`finance` 管理审批和凭证，`auditor` 查看审计，`viewer` 只能查看报表。无权限访问会写入独立 `security_event` 链。

## 写账与审计

审批状态和凭证导出由服务层控制。只有已经批准的对象才能经过 `ledger/write_service.py` 导出；其他模块不直接调用 ledger target。业务 `audit_log` 和安全 `security_event` 都是只追加哈希链，支持导出和离线校验。

## API token 与只读 AI

API token 只保存 SHA-256，不保存原文；吊销后不能再次使用。AI 工具通过只读账号查询数据库，工具结果带表、行 ID 和字段引用。MCP 默认只启用 stdio，HTTP 传输由部署层显式配置。

发送给模型前，买家姓名、手机号、邮箱、身份证号和地址字段会替换成带编号的占位符；金额、订单号和 SKU 保持原值以便引用。工具自由文本会包在转义后的 `<data>` 标签中，标签内内容只当数据处理。

AI 问答正文默认保留 90 天，可用 `CROSSERP_AI_RETENTION_TEXT_DAYS` 调整；清理通过 `crosserp ai purge-text` 手工执行并写业务审计。

仓库不接受真实密钥和未脱敏卖家数据。漏洞请按 [SECURITY.md](../SECURITY.md) 的内部方式报告。
