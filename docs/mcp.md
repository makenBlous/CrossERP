# MCP 只读服务

`crosserp mcp serve` 默认使用 stdio，只注册 T42 的只读查询工具；HTTP 传输默认关闭，避免未配置时暴露服务。

API token 在网页「我的 API Token」创建，明文只显示一次；用户停用或 token 吊销后立即失效。不要把 token 提交到仓库或公开配置。
