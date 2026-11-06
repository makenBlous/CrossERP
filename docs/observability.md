# AI 调用记录

T44 将提示词版本和调用元数据保存到 `prompt_version`、`llm_call`、`llm_tool_call`。
费用是按 `~/.crosserp/model_prices.yaml` 中每百万 token 价格用 Decimal 估算，未配置价格时为空；这是估算值，不是供应商账单。

## 记录内容

每次调用记录模型、渠道、提示词版本、输入/输出 token、延迟、状态、拒答原因、脱敏后的问题和答案、trace/request ID。工具调用记录工具名、参数摘要、结果行数、延迟和状态。正文默认保留 90 天，清理命令会写审计记录。

## 预算与告警

`crosserp ai budget set` 配置金额或 token 上限；预算优先使用金额，未配置价格时退回 token 上限。达到告警比例会生成 `llm_alert`，超过硬上限拒绝调用，管理员也不绕过预算。监控页只展示调用量、费用估算、拒答率和慢调用。

## 评测

离线评测不调用真实模型：

```bash
uv run crosserp eval run --model test
uv run crosserp eval compare --baseline tests/eval/baseline.json
```

真实模型评测只允许手动触发，API key 由部署者通过 GitHub secret 或本地环境变量提供。
