# 前端文档索引

> **适用范围：** `frontend/` 文档。**状态：** 已实现的代码说明、仅静态原型（前端 mock）的验收记录和仅设计的接入约束分开维护。

## 规范（长期有效）

- [前端开发规范](./前端开发规范.md)：组件复用、页面目录、权限、金额、日期、审批、AI 安全和模型设置约束。
- [对接真实接口](./对接真实接口.md)：从 mock 切换到 08 / OpenAPI 契约的步骤、27 处契约调整和 P0–P5 切换顺序。

## 批次报告与审计记录（历史）

下列文件保留当时的验收结论。它们的开头已标注日期和“历史记录”；遇到现行规则时，以 [前端开发规范](./前端开发规范.md) 和 [对接真实接口](./对接真实接口.md) 为准。

| 文档 | 内容 |
|---|---|
| [batch0-foundation.md](./batch0-foundation.md) | 批次 0 的前端地基、类型和占位路由记录。 |
| [gap-a-report.md](./gap-a-report.md) | 批次 A 费用、财务和凭证原型验收。 |
| [gap-b-report.md](./gap-b-report.md) | 批次 B 供应链、库存、集成和渠道原型验收。 |
| [gap-c-report.md](./gap-c-report.md) | 批次 C 权限与页面访问复核。 |
| [gap-d-report.md](./gap-d-report.md) | 批次 D 智能体、HR 和行政原型验收。 |
| [gap-e-report.md](./gap-e-report.md) | 批次 E 知识库和新人上手原型验收。 |
| [ux/U1-integration.md](./ux/U1-integration.md)、[ux/U1-reuse.md](./ux/U1-reuse.md) | U1 页面头部、日历和组件复用记录。 |
| [ux/U2-integration.md](./ux/U2-integration.md)、[ux/U2-reuse.md](./ux/U2-reuse.md) | U2 工作台和引导接入记录。 |
| [ux/U3-integration.md](./ux/U3-integration.md)、[ux/U3-reuse.md](./ux/U3-reuse.md) | U3 聊天和助手接入记录。 |
| [component-reuse-audit.md](./component-reuse-audit.md)、[component-reuse-audit-final.md](./component-reuse-audit-final.md) | Vuexy / Vuetify 复用审计及整合后复核。 |
| [vuexy-sources-batch3.md](./vuexy-sources-batch3.md) | 第三批页面的 Vuexy 来源记录。 |

## 相关设计来源

- [前端页面设计](../../docs/design/01-前端页面设计.md)
- [后端模块与 API 设计（预定文件）](../../docs/design/08-后端模块与API设计.md)
- [OpenAPI 草案（预定文件）](../../docs/design/08/openapi-draft.yaml)
- [页面与 API 对照（预定文件）](../../docs/design/08/page-api-coverage.csv)

后 3 个链接由后端文档组提供；合入前端文档时允许预先引用，文件名以任务约定为准。
