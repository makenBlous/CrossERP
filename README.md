# CrossERP

CrossERP 是一个面向跨境电商卖家的 ERP：导入平台结算和业务文件，用确定性规则完成清洗、对账、异常分析和 SKU 利润，并在审批后生成凭证草稿或导出。AI 只读取已保存的数据，提供带引用的解释和建议，不计算金额，也不绕过审批写账。

当前版本是 0.5.0 内部里程碑，尚未发布到 PyPI、GHCR、Docker Hub 或公开 Release。

## 当前状态

- **已实现：** Python/FastAPI 后端已有导入、对账、利润、异常、凭证、审批、登录、安全日志、审计哈希链、只读 AI 工具和 MCP。
- **仅静态原型（前端 mock）：** frontend/ 使用 Vue 3、TypeScript、Vuetify 3、Vite 和本地 Vuexy v10.11.1 参考组件，页面与 service 仍是 mock。
- **仅设计：** Vue 前端目标 /api/v1 JSON 接口、本体实体动作目录和后续业务域。现有后端网页路由是 Jinja HTML，尚未提供 Vue JSON 接口。

正式环境以 MySQL 8.4 LTS 为主库；本机演示使用 SQLite，PostgreSQL 只作兼容回归或满足 08 第 11.3 节的替换条件。

## 已实现能力

- Amazon Settlement Flat File V2、Shopify Payments CSV 和 YAML 映射文件导入。
- 确定性对账、重复/失败导入处理、异常原因码、SKU 利润和 CSV/XLSX 报表。
- 审批状态机与 ledger/write_service.py 唯一写出口。
- 用户角色、Argon2 密码、会话、CSRF、防暴力登录锁定和 API token。
- 只追加的业务/安全审计链、审计导出和离线校验。
- 只读 AI、脱敏与提示注入防护、调用记录、预算告警、MCP stdio 服务和离线评测基线。

## 安全边界

1. 金额只由确定性代码使用 Money / Decimal 计算，金额采用万分位整数；LLM 不计算或修改金额。
2. 凭证、付款和调账等改账动作必须经过配置的审批和唯一写出口；制单人不能审批自己的单据。
3. agent 继承登录人的有效权限，只能少不能多；AI 不能执行代码。关闭 AI 后，人工流程仍可用。
4. 审计只追加，仓库不放密钥、密码、token 或真实卖家数据。

## 快速开始

~~~bash
uv sync --all-extras
uv run crosserp demo --check --no-browser
~~~

Windows PowerShell：

~~~powershell
uv sync --all-extras
uv run crosserp demo --check --no-browser
~~~

演示使用独立 SQLite 数据库和固定合成样本。需要创建本地应用库时：

~~~powershell
uv run crosserp init --admin-username admin --admin-password-stdin
uv run crosserp serve --host 127.0.0.1 --port 8000
~~~

浏览器打开 http://127.0.0.1:8000。不要把密码写进仓库或文档。Docker 和安装说明见 [docs/体验指南.md](docs/体验指南.md)。

## 文档

从 [docs/README.md](docs/README.md) 开始，再阅读 [AGENTS.md](AGENTS.md)、[docs/dev/开发规则.md](docs/dev/开发规则.md) 和 [docs/dev/测试与回归.md](docs/dev/测试与回归.md)。接口设计以 [docs/design/08-后端模块与API设计.md](docs/design/08-后端模块与API设计.md) 为准，前端接入方式见 [frontend/docs/README.md](frontend/docs/README.md)。

## 开发检查

~~~bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov=crosserp --cov-fail-under=80 -q
~~~

前端构建、数据库矩阵和推送门槛见 [docs/dev/测试与回归.md](docs/dev/测试与回归.md)。项目当前不做公开发布。
