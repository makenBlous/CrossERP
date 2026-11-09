# 补齐批次 E 验收报告

日期：2026-11-10（Asia/Shanghai）

## 页面

已实现 12/12 个页面：K01 `/kb`、K02 `/kb/docs/:id`、K03 `/kb/spaces/:id`、K04 `/kb/docs/:id/edit`、K05 `/kb/review`、K06 `/kb/qa`、K07 `/kb/expiring`、K08 `/kb/index`、K09 `/kb/access-log`、HR13 `/hr/employees/:id/files`、ON01 `/onboarding`、ON02 `/onboarding/admin`。旧 `/agent/knowledge` 和 `/agent/knowledge/:id` 已跳转到新知识库地址。

## 流程结果

- 发布流程：已用真实点击新建文档、保存草稿、提交审核、财务角色批准，并可查看版本历史。
- AI 建议沉淀：已从已解决工单生成建议问答，进入审核队列，批准后显示在沉淀问答页。
- 空间权限：已切换空间为仅财务可见；运营搜索结果被过滤，AI 引用范围同步受限。
- 个人档案：员工本人/人事可访问，其他角色由服务层拒绝；敏感文件下载后写入访问日志。
- 检索问答：报销问题返回制度文档版本与段落出处；重建索引后仍返回同一版本引用。
- 到期提醒：证书种子设置为 20 天内到期，在到期提醒页显示。
- 新人上手：采购模板显示清单，问答带出处，「带我去做」可打开采购页面；管理员可编辑清单。
- AI 关闭：切换 `crosserp-ai-mode=off` 后主要页面仍可打开，AI 页面问答区和全局助手入口隐藏。

## 检查命令

- `pnpm install --frozen-lockfile --prefer-offline`：通过。
- `pnpm run typecheck`：通过。
- `pnpm exec eslint . -c .eslintrc.cjs --ext .ts,.js,.cjs,.vue,.tsx,.jsx`：0 error（仓库已有 23 条 warning）。
- `pnpm run build`：通过。
- Playwright：使用本机 Chrome、`BASE=http://127.0.0.1:4185`，12 个页面按角色打开且控制台错误为 0；流程脚本最终 `errors: []`。截图保存在 `C:\Users\cimi\AppData\Local\Temp\cx-pw\gap-e\shots\`。

## 复用与边界

页面复用 `ListPage`、`DetailPage`、`FormPage`、`StatusChip`、`PermissionGate`、`KpiCard` 和全局 `AssistantDrawer`；专属版本表、访问日志和检索结果使用 Vuetify `VTable`/`VList`。新增类型、API、mock 和页面均在批次 E 文件中，未改后端。为满足 AI 总开关关闭时隐藏全局助手，`AssistantDrawer` 增加了读取 `ai-mode` 的显示条件。

## 未核实项

ERPNext `frappe/wiki`、Odoo `knowledge`/`website_slides` 的具体功能仍按设计文档标注为「未核实」；本批只实现静态前端和确定性 mock，真实后端接口、真实文件存储、向量检索和通知渠道待后续接入。
