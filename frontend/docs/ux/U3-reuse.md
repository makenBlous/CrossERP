# U3 聊天组件复用核对

## 复用的 Vuexy / 项目能力

- `VNavigationDrawer`、`VLayout`、`VMain`、`VAvatar`、`VBtn`、`VAlert`、`VCard`：继续使用 Vuexy/Vuetify 的布局、状态和审批卡片能力。
- `vue3-perfect-scrollbar`：仅用于智能体中心的会话列表；消息主区使用原生滚动容器，保证输入区固定且高度可控。
- `useResponsiveLeftSidebar`：保留 Vuexy 的窄屏会话列表抽屉行为。
- 现有 `createAgentAdapter`、`fetchChat`、`submitAgentSuggestion`、`recordAgentQuestion` 和 `recordSuggestionStep`：数据读取、权限检查、审批提交和历史接口语义不变。

## 新增组件

- `src/components/chat/ChatThread.vue`：两个入口共用的滚动消息区、状态行和固定输入区编排。
- `src/components/chat/ChatMessage.vue`：品牌色用户消息、浅灰助手消息、头像、Markdown 文本、列表和代码块展示。
- `src/components/chat/ChatComposer.vue`：多行自动增高输入、附件缩略名、Enter/Shift+Enter/Esc 和语音/发送操作。
- `src/components/chat/ChatStatusLine.vue`：加载中、失败重试、取消和已取消提示。
- `src/components/chat/useChatHistory.ts`：按入口隔离的本地增量缓存；API 返回的历史优先合并，刷新后保留本地新增消息。

新增这些组件是为了让浮动窗和智能体中心共享视觉层次与交互行为，同时保留各入口自己的数据上下文、权限门禁和审批卡片。
