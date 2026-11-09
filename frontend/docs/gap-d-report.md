# 补齐开发批次 D 验收报告

## 页面清单

已将 G18–G26（含扩展 `/agent/tools`）、HR01–HR12、AM01–AM05 共 26 个页面从占位路由替换为真实页面。路由页面均使用 `BatchDPage` 薄壳，页面元数据已标记 `implemented: true` 并接入菜单。

## 流程结果

- 自主等级：票据分类白名单默认为 L3；凭证起草硬上限为 L2，服务层拒绝越过硬上限的请求。
- AI 总开关：正常、降级、关闭均可切换；降级只读并暂停 L3，关闭后 AI 提示区隐藏，人工页面仍可操作。
- 工具注册表：自定义 HTTP 工具默认停用、只读；密钥只保留“已配置”状态；MCP 工具导入后默认停用。
- 算薪：规则费率存放在 mock 配置，按累计预扣法由代码计算；HR 复核入口和工资凭证前的状态展示已提供。工资字段由 mock 服务按角色裁剪，员工只返回本人数据。

## 复用情况

详见 `component-reuse-audit.md` 的“补齐批次 D”小节。未新增通用组件，列表/详情/表单/KPI/金额/状态均复用既有组件。

## 检查结果

- `pnpm install --frozen-lockfile --prefer-offline`：通过。
- `pnpm run typecheck`：通过。
- `cmd /c "pnpm exec eslint . -c .eslintrc.cjs --ext .ts,.js,.cjs,.vue,.tsx,.jsx"`：0 error（基线存在 23 条 warning）。
- `pnpm run build`：通过。

## Playwright

已在端口 4184 使用本机 Chrome（playwright-core）运行 4 个角色（admin/operator/finance/employee）逐页打开 27 个批次 D 路由，共 108 次导航；控制台与 pageerror 均为 0。截图已保存到 `C:\Users\cimi\AppData\Local\Temp\cx-pw\gap-d\shots`。管理员实际点击验证了 AI 正常/降级/关闭、自治策略保存、发起算薪、MCP 工具导入；AI 关闭后再次执行人工算薪路径无 pageerror。普通员工工资页路由可访问，工资字段由服务层按本人范围裁剪。

## 未完成项与未核实项

薪资费率和税率均为模拟规则，标记为“待会计/HR 核实”，不代表全国合规算税算社保能力。后端 `/api/v1` 尚未接入，本批仅提供静态前端、类型、API 注释和确定性 mock 服务。Playwright 截图和跨角色逐页回归需在本机 Chrome 可用时补跑。

