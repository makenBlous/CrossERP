# 补齐批次 B 验收报告

日期：2026-11-10（Asia/Shanghai）

## 页面清单

本批完成 20 个页面（列表页与详情页共用 `src/views/gap-b/GapBPage.vue`，每个路由保留独立薄壳）：

- 供应链：S09 询价单、S10 询价比价、S11 采购合同、S12 合同详情、S13 供应商评估。
- 库存：I12 批次与效期、I13 补货建议、I14 调拨详情、I15 盘点详情。
- 业务链：D05 业务链追溯。
- 集成：INT01 领星/赛狐导入向导、INT02 平台同步、INT03 金蝶导出设置、INT04 ERPNext 账套、INT05 集成日志。
- 渠道与审批：W08 IM 审批卡片预览、SYS19 我的渠道绑定、SYS20 IM 审批设置、SYS25 通知渠道、SYS26 新增渠道。

页面数据均由 `src/api/gap-b.ts` 读取或提交，mock 服务只保留演示数据和确定性状态变化；没有改动后端。

## 流程结果

- 业务链搜索 `SO-2026-001`：显示客户/商机 → 订单 → SKU/采购/入库 → 头程/出库/发货 → 凭证，4 个断点均显示“已接通”。
- 领星/赛狐导入：上传 CSV → 列映射确认 → 导入完成。
- IM 审批：¥3,000 卡片可批准；金额超过 ¥50,000 的卡片只显示“去网页确认”；内容变化动作会标记为阻止操作。
- 补货：正常模式可点击“AI 起草”，AI 关闭时可点击“手动新建采购单”；两条路径都生成采购单草稿提示。
- 渠道绑定、调拨确认、盘点差异提交、同步任务、通知渠道测试均有页面动作和 mock 服务状态反馈。

## 复用情况

页面复用 `ListPage`、`DetailPage`、`FormPage`、`StatusChip`、`MoneyText`、Vuetify `VStepper`/`VCard`/`VTable`。没有新增通用 UI 组件；复用记录已追加到 `component-reuse-audit.md`。

## 检查与 Playwright

实际执行并通过：

```text
pnpm install --frozen-lockfile --prefer-offline
pnpm run typecheck
cmd /c "pnpm exec eslint . -c .eslintrc.cjs --ext .ts,.js,.cjs,.vue,.tsx,.jsx"
pnpm run build
```

Playwright 使用本机 Chrome 和 `http://127.0.0.1:4182`：`admin`、`operator`、`finance`、`auditor` 四个角色各打开 20 页，控制台错误均为 0；管理员截图 20 张保存在 `%TEMP%\cx-pw\gap-b\shots\`。流程脚本的正常模式和 `crosserp-ai-mode=off` 模式均无错误。

## 未完成与未核实

- 当前仍是静态前端和 mock 服务，真实 `/api/v1`、IM 回调签名服务端复核、ERPNext/金蝶连接尚未接入。
- 采购退货真实库存扣减、销售订单客户/商机字段、物流运单持久化等后端断点只在本批页面链路中展示，等待对应后端任务。
- ERPNext/Odoo 对照名称沿用设计文档中标注“未核实”的条目，未新增未经核实的平台字段。
