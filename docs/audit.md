# 审计导出与保留规则

`audit_log` 是只追加哈希链。每条记录包含操作者、时间、动作、对象、改前/改后、审批关联、原因、请求 id 和前一条哈希。业务审计默认永不自动删除。

导出审计包：

```bash
crosserp audit export --from 2026-11-01 --to 2026-12-31 --format jsonl --out audit.zip --as maken
crosserp audit verify-export audit.zip
```

包内有数据文件、`manifest.json` 和 `VERIFY.md`。`verify-export` 只用 Python 标准库读取 zip，不连接数据库。篡改数据文件、manifest 或文件摘要都会失败。

写入 `audit_checkpoint` 只记录当前链尾锚点，不会删除任何数据：

```bash
crosserp audit checkpoint --reason "月度离线归档前留锚点"
```

以后如果要清理登录日志或模型原文，必须先写检查点；本版本不提供任何删除命令。会计档案的法定保管期限尚未核实，请先向会计确认后再配置。

T33 配置读取 `CROSSERP_AUDIT_RETENTION_BUSINESS` 和 `CROSSERP_AUDIT_RETENTION_SECURITY_DAYS`；业务审计默认 `never`，安全事件默认 180 天。配置只影响后续 T34/T45 的清理策略，不会自动删除现有记录。
