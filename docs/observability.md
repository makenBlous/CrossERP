# AI 调用记录

T44 将提示词版本和调用元数据保存到 `prompt_version`、`llm_call`、`llm_tool_call`。
费用是按 `~/.crosserp/model_prices.yaml` 中每百万 token 价格用 Decimal 估算，未配置价格时为空；这是估算值，不是供应商账单。
