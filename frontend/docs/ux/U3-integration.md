# U3 接入说明

本任务未修改公共路由、权限、会话、i18n、依赖和变更日志文件。

## 需要整合者确认

- 若产品要将“AI 已关闭，页面仍可按人工路径操作。”纳入统一多语言资源，请在 `src/plugins/i18n/ui.ts` 增加对应 `assistant.aiClosed`（中英文）键，并替换两个入口中的局部常量 `disabledReason`。
- `frontend/scripts/verify-u3.ts` 需要接入统一的前端检查流程；本任务先按任务要求提供独立的 `pnpm exec tsx scripts/verify-u3.ts` 命令。
- 本地历史缓存键为 `crosserp-chat-history:assistant-<route>` 和 `crosserp-chat-history:agent-center`。它只合并当前 actor 已经通过 API 返回或当前页面产生的消息，不改变 API 权限检查、审批提交或服务端历史语义。

## 未改动的业务边界

消息发送仍走现有 agent adapter；建议卡仍只能通过 `submitAgentSuggestion` 进入审批；AI 关闭时发送按钮、附件和语音入口均禁用，人工页面入口保留。
