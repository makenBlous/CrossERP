# 补齐开发批次 D 验收报告

## 页面清单

已将 G18–G26（含扩展 `/agent/tools`）、HR01–HR12、AM01–AM05 共 26 个页面从占位路由替换为真实页面。路由页面均使用 `BatchDPage` 薄壳，页面元数据已标记 `implemented: true` 并接入菜单。

## 流程结果

- 自主等级：票据分类白名单默认为 L3；凭证起草硬上限为 L2，服务层拒绝越过硬上限的请求。
- AI 总开关：正常、降级、关闭均可切换；降级只读并暂停 L3，关闭后 AI 提示区隐藏，人工页面仍可操作。
- 工具注册表：自定义 HTTP 工具默认停用、只读；密钥只保留“已配置”状态；MCP 工具导入后默认停用。
- 算薪：规则费率存放在 mock 配置，按累计预扣法由代码计算；HR 复核入口和工资凭证前的状态展示已提供。工资字段由 mock 服务按 userId 绑定和有效权限裁剪，员工只返回本人数据。
- 权限契约：D 服务层调用 C 的有效权限计算，不复制范围判断。员工档案和工资条按稳定 `userId` 裁剪；请假一审使用 `leave_application:approve_manager` 加部门/直属主管范围，人事二审使用 `leave_application:approve_hr`；薪资人事复核使用 `salary_slip:review`，财务审批使用 `salary_slip:approve`。

## 复用情况

详见 `component-reuse-audit.md` 的“补齐批次 D”小节。未新增通用组件，列表/详情/表单/KPI/金额/状态均复用既有组件。

## 检查结果

- `pnpm install --frozen-lockfile --prefer-offline`：通过。
- `pnpm run typecheck`：通过。
- `cmd /c "pnpm exec eslint . -c .eslintrc.cjs --ext .ts,.js,.cjs,.vue,.tsx,.jsx"`：0 error（基线存在 23 条 warning）。
- `pnpm run build`：通过。
- `pnpm exec tsx scripts/verify-gap-d-security.ts`：全部通过，覆盖财务脱敏、本人档案/工资条、请假部门范围、AI 拒写和工具权限。
- 批次 D 独立断言 `xd.ts`：0 FAIL；批次 C `xperm.ts`：0 FAIL。`xperm2.ts` 依赖当前工作树不存在的 `@/mocks/services/scoped-reads` 和 `gap-c`，按原命令运行时无法加载，未伪造通过结果。

## Playwright

初次验收在端口 4184 使用本机 Chrome（playwright-core）运行 4 个角色（admin/operator/finance/employee）逐页打开 27 个批次 D 路由，共 108 次导航；控制台与 pageerror 均为 0，截图目录保存了 27 张管理员页面截图。补充工具/票据流程后再次运行同样的 108 次导航，控制台与 pageerror 仍为 0；另实际点击了票据收件和工具启用动作，均无错误。管理员实际点击验证了 AI 正常/降级/关闭、自治策略保存、发起算薪、MCP 工具导入；AI 关闭后再次执行人工算薪路径无 pageerror。普通员工工资页路由可访问，工资字段由服务层按本人范围裁剪。

## 未完成项与未核实项

薪资费率和税率均为模拟规则，标记为“待会计/HR 核实”，不代表全国合规算税算社保能力。后端 `/api/v1` 尚未接入，本批仅提供静态前端、类型、API 注释和确定性 mock 服务。Playwright 截图和跨角色逐页回归需在本机 Chrome 可用时补跑。



## 批次 D 最新补齐记录（2026-11-10）

本轮适配批次 C 最终权限契约；D 的员工、薪资 mock 读接口使用稳定 `userId ↔ employeeId` 绑定，敏感字段通过 `fieldAccess` 裁剪。新增统一服务层权限断言、状态检查、幂等和审计；AI 写入直接拒绝，只允许起草。

本轮补充 `demo-other-employee`、`demo-ops-manager`、`demo-fin-manager` 的员工档案和部门主管绑定，验证同部门员工只能看到本人档案和工资条；请假审批拒绝跨部门主管及缺少部门/绑定的审批人；工资条复核和审批不能由同一 userId 完成，发布仍需审批后且只允许一次。薪资、个税、社保继续标注“模拟规则，待人事/会计核实”。

已补齐模拟写操作：资产领用/归还、合同状态编辑、员工入离职状态流转、请假提交与主管→人事审批、考勤/合同模拟导入登记、HTTP 工具默认停用只读/密钥已配置状态/频率上限/启停/测试调用、MCP 登记与工具导入默认停用、社保个税规则与专项扣除保存、算薪→HR 复核→财务审批→工资条发布。薪资和规则均标注“模拟规则，待人事/会计核实”。

`pnpm exec tsx scripts/verify-gap-d-security.ts`：全部通过。页面请假、算薪、复核、审批、发布按钮按服务层对应权限键禁用；本轮未启动预览服务器或浏览器。

## 批次 D 修复记录（2026-11-10）

资产归还后状态回到“可领用”，归还审计保留；D 审计事件新增稳定 `actorId`，通用审计列表和导出也带出操作者 ID，旧缓存记录显示“旧记录未留 ID”。`scripts/check-gap-d-asset-audit.ts` 覆盖领用→归还→再次领用、重复归还拒绝及 D 写操作审计身份。
