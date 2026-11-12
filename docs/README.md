# CrossERP 文档地图

本文是文档入口。先看状态，再按建议顺序阅读；实现与设计冲突时，以代码、测试和 [08 后端模块与 API 设计](design/08-后端模块与API设计.md) 的当前版本为准。

## 总览

- [README](../README.md)：项目定位、已实现能力和本地快速开始；已实现说明与静态前端边界已核对。
- [中文 README](../README.zh-CN.md)：面向使用者的中文概览；已实现说明与静态前端边界已核对。
- [体验指南](体验指南.md)：Windows 本机演示路径；只写可复制的用户操作，不替代开发规则。

## 设计方案

- [设计方案索引](design/README.md)：说明 00–08 的事实来源和优先级；仅设计/现状对照。
- [08 后端模块与 API 设计](design/08-后端模块与API设计.md)：v4 后端与 agent 的唯一接口依据；仅设计，接口尚待实现。
- [实体目录](design/08/ontology-entities.yaml)：实体、状态机和动作目录；由后端组维护。
- [OpenAPI 草案](design/08/openapi-draft.yaml)：Vue 前端目标 JSON 契约；由后端组维护。
- [页面接口对照](design/08/page-api-coverage.csv)：页面、实体动作与权限点的映射；由后端组维护。

## 后端

- [后端开发指南](backend/README.md)：包结构、动作执行器、权限、迁移和 MySQL 注意点；由后端组维护。
- [现有架构说明](architecture.md)：已实现模块的现状记录；与 08 的目标设计配套阅读。
- [数据库说明](database.md)：数据库连接和迁移现状；正式环境默认看 MySQL 规则。
- [安全说明](security.md)：已实现安全边界和运行时注意事项。

## 前端

- [前端文档索引](../frontend/docs/README.md)：Vue 3 / TypeScript / Vuetify 3 / Vite 静态原型的入口；当前仍是 mock。
- [前端开发规范](../frontend/docs/前端开发规范.md)：组件复用、权限显示和接口切换规则；由前端组维护。
- [对接真实接口](../frontend/docs/对接真实接口.md)：从 mock 切换到 `/api/v1` 的步骤；接口以 08 和 OpenAPI 为准。
- [组件复用审计](../frontend/docs/component-reuse-audit.md) 与 [最终审计](../frontend/docs/component-reuse-audit-final.md)：每批复用检查记录。

## 业务域

- [业务域索引](domains/README.md)：实体、动作、流程和业务口径的入口；由领域组维护。
- [财务](domains/财务.md)、[供应链](domains/供应链.md)、[智能体与权限](domains/智能体与权限.md)：按域说明边界和风险。
- [数据清洗、知识库与数字孪生](domains/数据清洗-知识库-数字孪生.md)：原件到实体及副本推演链路。
- [平台与外部对接](domains/平台与外部对接.md)：连接器、渠道和外部账套；平台接入顺序以 08 第 12 章为准。
- [人事、行政、客户、广告](domains/人事行政客户广告.md)：后期域的状态和启用边界。

## 开发任务

- [后端开发任务路线](tasks/README.md)：P0–P5 任务卡；以任务文件状态为准。
- [历史任务表](tasks/_archive/README.md)：T01–T56 的历史实施记录和验收状态。

## 开发规则

- [开发规则](dev/开发规则.md)：长期可执行清单，所有改动前必读。
- [测试与回归](dev/测试与回归.md)：仓库内检查、监督方脚本边界和推送门槛。
- [代理入口](../AGENTS.md)：代理阅读顺序、状态三分和硬规则。

## 历史与验收记录

- [变更日志](../CHANGELOG.md)：历史发布和验收记录，按规定不在文档刷新任务中改动。
- [证据目录](evidence/)：历史验收输出，只作为证据，不反向改变当前设计。
- [ADR](adr/)：已作出的架构决定；新决定优先补 ADR 和 08，再更新引用文档。
- [旧 AUTOPILOT 流程](AUTOPILOT.md)：历史自动开发提示，当前规则见 [开发规则](dev/开发规则.md)。
