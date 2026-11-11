# CrossERP 贡献指南

## 开始前

先读 [AGENTS.md](AGENTS.md)、[docs/README.md](docs/README.md) 和 [docs/dev/开发规则.md](docs/dev/开发规则.md)，再确认任务范围、事实来源和当前状态。接口、实体动作、风险和审批规则以 [08 后端模块与 API 设计](docs/design/08-后端模块与API设计.md) 及其 OpenAPI / YAML 附件为准。

## 工作方式

使用分离头工作树：

~~~powershell
git worktree add --detach <worktree-path> main
~~~

不创建任务分支，不覆盖其他工作树中的用户改动。一次只处理一个明确范围；完成后把提交整合到 main，工作树干净且已合入时再移除。不要打 tag、发 Release、强制推送、reset 或改写历史。

## 提交前检查

~~~powershell
uv sync --locked --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov=crosserp --cov-fail-under=80 -q
uv run pre-commit run --all-files
~~~

前端和数据库矩阵检查见 [docs/dev/测试与回归.md](docs/dev/测试与回归.md)。推送前必须所有检查 exit=0、0 个 FAIL、0 个 ESLint error、密钥扫描 0 命中。

## 改动边界

- 不删除、跳过或放宽测试和断言；保留不认识的用户改动。
- 金额只由确定性代码计算。审批按 [08 v4 第 4.6、12.1 节](docs/design/08-后端模块与API设计.md) 的目标规则处理：agent 发起的改账动作最多到草稿或待审；人提交的单据按审批人解析，配置了审批人必须审且不能自批，未配置或解析不到可用账号时直接生效并留痕。现有代码仍按 [ADR 0001](docs/adr/0001-single-write-path.md) 的唯一写账出口执行「不通过审批不写账」。
- agent 权限不超过登录人，不能自批，不能执行代码；AI 关闭后人工流程仍可用。
- 不读或提交 CrossERP演示密码.txt、任何 .env、密钥、token 或真实卖家数据；示例只用占位符。
- 同一事实只在一个权威文档写死。先改 08 / OpenAPI / 实体目录，再改引用它的说明。

提交信息使用中文 Conventional Commits，例如：

~~~text
docs(指南): 更新文档入口与回归门槛
~~~
