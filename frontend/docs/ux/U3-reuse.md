# U3 聊天组件复用核对

> **历史记录：** 2026-11-11。本文保留当时结论；现行规范见 [前端开发规范](../前端开发规范.md) 和 [对接真实接口](../对接真实接口.md)。


## 复用的 Vuexy / 项目能力

- `VNavigationDrawer`、`VLayout`、`VMain`、`VAvatar`、`VBtn`、`VAlert`、`VCard`：继续使用 Vuexy/Vuetify 的布局、状态和审批卡片能力。
- `vue3-perfect-scrollbar`：仅用于智能体中心的会话列表；消息主区使用原生滚动容器，保证输入区固定且高度可控。
- `useResponsiveLeftSidebar`：保留 Vuexy 的窄屏会话列表抽屉行为。
- 现有 `createAgentAdapter`、`fetchChat`、`submitAgentSuggestion`、`recordAgentQuestion` 和 `recordSuggestionStep`：数据读取、权限检查、审批提交和历史接口语义不变。

## 新增组件

- `src/components/chat/ChatThread.vue`：两个入口共用的滚动消息区、状态行和固定输入区编排。
- `src/views/apps/chat/ChatLog.vue`：两个入口共用的消息分组、气泡、头像和安全 Markdown 文本渲染；通过 `v-text` 渲染文本节点，避免 HTML 注入。
- `src/views/apps/chat/ChatMessageForm.vue`：两个入口共用的多行自动增高输入、附件缩略名、Enter/Shift+Enter/Esc 和语音/发送操作。
- `src/components/chat/ChatMessage.vue`、`ChatComposer.vue`：仅保留旧引用的薄适配层，不再重复绘制气泡或输入区。
- `src/components/chat/ChatStatusLine.vue`：加载中、失败重试、取消和已取消提示。
- `src/components/chat/useChatHistory.ts`：按稳定 `session.userId` 和入口隔离的本地增量缓存；API 返回的历史按消息 ID 优先，只有带 `local: true` 的当前会话新增消息才会补充到结果中。

这些复用点让浮动窗和智能体中心共享消息与输入 UI，同时保留各入口自己的数据上下文、权限门禁和审批卡片。没有稳定 `userId` 时不会读取或写入历史缓存；用户身份变化时会重新加载对应身份的会话。
