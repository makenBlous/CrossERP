# U3 接入说明

> **历史记录：** 2026-11-11。本文保留当时结论；现行规范见 [前端开发规范](../前端开发规范.md) 和 [对接真实接口](../对接真实接口.md)。


本任务未修改公共路由、权限、会话、i18n、依赖和变更日志文件。

## 需要整合者确认

- 若产品要将 AI 关闭说明纳入统一多语言资源，请在 `src/plugins/i18n/ui.ts` 增加对应 `assistant.aiClosed`（中英文）键，并替换入口中的局部常量 `disabledReason`。
- `frontend/scripts/verify-u3.ts` 需要接入统一的前端检查流程；本任务先按任务要求提供独立的 `pnpm exec tsx scripts/verify-u3.ts` 命令。
- 本地历史缓存键为 `crosserp-chat-history:<userId>:assistant` 和 `crosserp-chat-history:<userId>:agent-center`。没有 `userId` 时不读也不写；API 返回的同 ID 消息优先，缓存只补充当前会话产生且标记为 `local` 的增量，不改变 API 权限检查、审批提交或服务端历史语义。

## 未改动的业务边界

消息发送仍走现有 agent adapter；建议卡仍只能通过 `submitAgentSuggestion` 进入审批；AI 关闭时浮动助手整体隐藏，人工页面和智能体中心显示禁用说明，智能体中心不能发送，发送按钮、附件和语音入口均禁用。
