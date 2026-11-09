# 智能体接入与 DeerFlow 2.0

- 文档日期：2026-11-09（Asia/Shanghai）
- 本文只设计接入方式，不在本机安装或启动 DeerFlow

---

## 1. DeerFlow 2.0 是否存在（已核实）

maken 提到希望用「deerflow2.0」快速接入。网上公开材料可以确认：**DeerFlow 2.0 是真实发布的产品线**，不是口头说法。

| 事实 | 来源 |
|---|---|
| 仓库为字节跳动组织下的 `deer-flow`，主页 https://deerflow.tech | https://github.com/bytedance/deer-flow |
| 官方 README 标题为 “DeerFlow - 2.0”，并写明 2.0 是推倒重写，与 v1 不共用代码；原深度研究框架留在 `1.x` / `main-1.x` 分支 | https://github.com/bytedance/deer-flow/blob/main/README.md |
| GitHub Release `v2.0.0`，发布时间 2026-06-25T16:23:22Z，说明里同样写 ground-up rewrite，1.x 在 `main-1.x` | https://github.com/bytedance/deer-flow/releases/tag/v2.0.0 |
| 发布计划议题 #824 已关闭，维护者说明 2.0 已发布、当前开发在 `main` | https://github.com/bytedance/deer-flow/issues/824 |
| 许可证为 MIT | https://raw.githubusercontent.com/bytedance/deer-flow/main/LICENSE |
| 检索时仓库还有更新的 `v2.2.0`（发布页列出） | https://github.com/bytedance/deer-flow/releases |

实施前请 maken 决定是锁定 `v2.0.0`，还是采用更新的 2.x。本文按 2.0 这条产品线的官方架构来设计，**未在 maken 电脑上实际运行 DeerFlow**，因此「能否一次性联通」标为「未核实」。

---

## 2. DeerFlow 2.0 是什么（摘自官方文档）

官方把自己定位为开源的 **super agent harness**（超级智能体运行架）：由一个主导智能体调度子智能体、长期记忆和沙箱，并用可扩展的技能（skills）和工具来完成可能持续数分钟到数小时的任务。名称含义是 Deep Exploration and Efficient Research Flow。

架构文档（https://github.com/bytedance/deer-flow/blob/main/docs/ARCHITECTURE.md）描述的运行方式：

| 组成 | 官方说明 |
|---|---|
| 语言与运行时 | 后端 Python 3.12+，前端 Node.js 22+（README 徽章） |
| 编排 | 建立在 LangGraph 上；主导智能体通过中间件链调用模型 |
| 服务拓扑 | 一次启动通常有 Nginx（默认对外端口 2026）、Gateway API（内部 8001）、Next.js 前端（内部 3000）、可选的沙箱供给服务（8002） |
| 访问 | 官方建议浏览器打开 http://localhost:2026；开发也可用 `make dev` 或 Docker |
| 工具来源 | 内置工具、配置中的工具（如读文件、命令、联网搜索）、以及 MCP 工具，合并后给主导智能体使用 |
| 沙箱 | 抽象为 `SandboxProvider`；开发可用本机执行，生产建议 Docker 隔离 |
| 技能 | `skills/public`（随仓库）和 `skills/custom`（本地自定义）；用 `SKILL.md` 描述 |
| 记忆 | 有持久记忆；官方提供导入示例和设置页 |
| 模型配置 | 根目录 `config.yaml` 与环境变量；可在设置里登记模型。密钥写在 `.env`，不应当进 Git |
| 扩展配置 | `extensions_config.json` 管 MCP 服务器和技能，可在运行时通过 Gateway 修改 |
| 对外接口 | 一套兼容 LangGraph 的接口（`/api/langgraph/*`），一套 Gateway REST（模型、MCP、技能、上传等） |
| 嵌入式客户端 | `deerflow.client.DeerFlowClient`，供定时任务和程序化调用 |
| 即时通讯 | 飞书、Slack、Telegram、Discord、钉钉等可接到同一套智能体（README / 架构文档） |
| 安全提醒 | 官方强调默认绑定本机回环地址；Gateway 管理权限相当于代码执行能力，部署不当有风险 |

MCP 文档（https://deerflow.tech/en/docs/harness/mcp）说明：只要对方实现 MCP，就可以在几乎不改 DeerFlow 内核的情况下加工具。配置示例使用 `extensions_config.json` 的 `mcpServers` 项，支持 `command`、`args`、`enabled`、`env`；也支持 HTTP 类型以及按用户注入凭证。配置变更后按文件修改时间使缓存失效，不必总是重启。工具太多时可以打开 `tool_search`，让智能体按需发现工具。

自定义工具和沙箱还可以写在 `config.yaml` 的 `tools.use` / `sandbox.use` 里（https://deerflow.tech/en/docs/harness/customization）。对 CrossERP 来说，**优先走 MCP**，这样不必把业务代码嵌进 DeerFlow，也不用 fork DeerFlow。

---

## 3. 和 CrossERP 现有智能体如何分工

CrossERP 现在已经有：

- 只读工具和引用/数字校验（`docs/agent.md`、`src/crosserp/agent/`）
- 网页 `/ask`
- `crosserp mcp serve`（默认标准输入输出，HTTP 默认关闭，`docs/mcp.md`）
- 每次调用写入 `llm_call` / `llm_tool_call`，并有预算和评测表
- 模型配置：`CROSSERP_MODEL_BASE_URL`、`CROSSERP_MODEL`、`CROSSERP_API_KEY`，密钥不进仓库

这些与 ADR 0002 一致：AI 只解释和问答，不算钱。

DeerFlow 更擅长：长时间任务、子智能体分工、沙箱里看文件、技能包、定时任务。它不应该取代 CrossERP 的财务计算，也不应该自己写金蝶凭证。

建议的分工：

| 事情 | 谁负责 |
|---|---|
| 对账、利润、凭证金额、借贷平衡 | CrossERP 确定性代码 |
| 批准后写账和导出 | CrossERP `ledger.write_service` |
| 简单的带出处问答（「上月哪个货最亏」） | 可继续用 CrossERP 现有问答，便于沿用 20 题评测 |
| 需要多步研究、读上传文件、定时解读的任务 | DeerFlow 编排，过程中调用 CrossERP 的 MCP 工具取数 |
| 智能体是谁、能用哪些工具、会话和费用 | CrossERP 存档，便于权限和审计 |
| 模型密钥 | 各自放在本机环境，都不进仓库 |

两个问答入口可以并存：日常卖家用 CrossERP 智能体中心；需要看沙箱产物或调试技能时，管理员可以打开本机 DeerFlow 工作台。是否对卖家隐藏 DeerFlow 界面，请 maken 决定（总览第 11 节）。

---

## 4. 推荐连接方式

```text
卖家浏览器
    │  登录 CrossERP（现有会话）
    ▼
CrossERP 智能体中心
    │  ① 短问答：走现有 agent 运行时，结果写 llm_call
    │  ② 长任务：由 CrossERP 作为客户端调用 DeerFlow Gateway
    ▼
DeerFlow（单独部署在本机或内网，默认 127.0.0.1:2026）
    │  只通过 MCP 访问业务
    ▼
CrossERP MCP 服务
    │  用 API Token 识别是谁、有哪些角色、能看哪些店铺
    ▼
只读查询 或 生成「待审批」建议
    │
    ▼
人在 CrossERP 审批中心确认后，才可能写账
```

### 4.1 CrossERP 把业务能力暴露成工具

现有只读工具保持不变，并继续同时注册给网页问答和 MCP：

- `get_profit`
- `list_issues`
- `get_order`
- `get_settlement`
- `get_recon_summary`
- `get_approval_status`
- `get_voucher`
- `compare_profit`
- `search_rules_doc`

以后按模块增加只读工具（例如查 SKU、查库存、查客户），必须：带记录编号以便引用、数字来自数据库已有结果、加入评测或接线测试、记入 `llm_tool_call`。

「建议类」工具（原实施方案 6.5 已点名，可在接入时补齐）：

- `propose_column_mapping`
- `propose_fee_category`
- `propose_issue_note`

这些工具的唯一副作用是在 CrossERP 创建待审批或待确认记录，**绝不直接改映射生效值、绝不调用 ledger**。

MCP 进程用调用方提供的 Token 运行，权限不超过该用户本身。管理员可以再给某个智能体收紧工具白名单（见数据模型中的授权表）。

现有 MCP 默认是标准输入输出。DeerFlow 官方示例也支持用 `command` + `args` 拉起这类服务。HTTP/SSE 形式更适合「DeerFlow 与 CrossERP 不在同一台机器」的情况；CrossERP 文档写明 HTTP 默认关闭，若要打开必须显式配置，并继续要求 Token，不得把服务暴露到公网而不加保护。

DeerFlow 侧配置形状（示例，实施时按所选版本的字段名核对官方文档；密钥用环境变量替换）：

```json
{
  "mcpServers": {
    "crosserp": {
      "command": "crosserp",
      "args": ["mcp", "serve"],
      "enabled": true,
      "env": {
        "CROSSERP_API_TOKEN": "$CROSSERP_API_TOKEN"
      }
    }
  }
}
```

若改用 HTTP MCP，则使用官方文档中的 `type: "http"` 与 `user_auth` / `headers_from_context`，按 DeerFlow 用户分别注入该用户在 CrossERP 的 Token，避免所有人共用一个管理员令牌。

### 4.2 DeerFlow 单独运行

- 不把 DeerFlow 源码复制进 CrossERP 仓库。
- 按官方文档用 Docker 或 `make setup` + `make dev` 安装；Windows 上官方 README 写明本地开发脚本以 Git Bash 为准，原生 PowerShell 不受支持。这与 maken 的环境有关，实施时需单独验证（「未核实」）。
- CrossERP 只保存：本机可访问的地址、是否启用、用于调用 Gateway 的服务凭证引用（不把密钥写入 Git，界面不明文回显）。
- 官方安全说明要求默认监听本机回环地址。CrossERP 的接入页应提示：不要在未做访问控制时把 DeerFlow 的 2026 端口暴露到公网。

### 4.3 审批、审计、LLM 监控如何接住

1. **写操作**：DeerFlow 无论经过 MCP 还是其它方式，都只能打到 CrossERP 的工具。工具层拒绝一切直接写账。需要改业务时只生成审批单，人在网页上点批准。
2. **业务审计**：智能体发起的查询和提交，`actor_type` 记为智能体，并记下是哪一个用户授权、哪一次运行。与现有 `audit_log` 字段兼容。
3. **LLM 监控**：
   - CrossERP 自己的问答继续写 `llm_call`；
   - 经过 CrossERP 转发到 DeerFlow 的任务，由 CrossERP 在发起和结束时各记一笔运行档案，并把能拿到的 token / 费用写入 `agent_run` 和/或 `llm_call`；
   - 若 DeerFlow 还连了 Langfuse 等外部追踪，那是可选项，不能代替 CrossERP 本地表（现有设计默认监控不依赖外部服务）。
4. **密钥**：`CROSSERP_API_KEY` 与 DeerFlow 的模型密钥可以是同一家模型商，也可以分开，但都必须留在本机。CrossERP 不得在日志、审计 JSON、前端页面里写出密钥。

### 4.4 技能包

DeerFlow 的技能是带 `SKILL.md` 的目录。可以为 CrossERP 编写若干说明型技能（例如「如何解释一笔对账异常」「提问时必须引用工具结果」），放在 DeerFlow 本地的 `skills/custom`，不要把密钥写进技能文件。技能只指导模型怎么调用 MCP 工具，不在技能里做金额计算。

---

## 5. CrossERP 里需要预留的智能体档案

这些是给页面做增删改查用的，详细字段见 `04-数据模型.md`。原则：DeerFlow 负责「跑起来」，CrossERP 负责「谁允许跑、跑了什么、花了多少、能不能复盘」。

| 档案 | 页面 | 说明 |
|---|---|---|
| 智能体定义 | `/agent/definitions` | 名称、职责说明、是否启用、默认模型名（不含密钥）、对应 DeerFlow 中的智能体名 |
| 工具与授权 | `/agent/tools` | 工具目录 + 某智能体/某角色可用哪些工具；写类工具固定为「只建建议」 |
| 店铺范围 | 智能体详情里的页签 | 可选限制某个智能体只能查某些店铺 |
| 会话 | `/agent/threads`、对话页 | 本地会话编号；若走 DeerFlow，保存对方的 thread id |
| 消息 | 对话页 | 问、答、引用；长文本遵守现有 MEDIUMTEXT 规则 |
| 运行与步骤 | `/agent/runs` | 一次运行的状态、耗时、步骤、工具名、脱敏后的参数 |
| 任务 | `/agent/tasks` | 定时或手动长任务，对应 DeerFlow scheduled tasks 的本地登记 |
| 知识库与文档 | `/agent/knowledge` | 规则和手册；检索仍以可追溯的文档段落为准 |
| 记忆指针 | 智能体详情或运行详情 | 不强制把 DeerFlow 记忆全文搬过来，可只存外部引用 |
| 提示词版本 | `/agent/prompts` | 已有 `prompt_version`，补页面和维护接口 |
| 评测 | `/agent/evals` | 已有 `eval_run` 和问题集，换模型或换提示词要能重跑 |
| 用量与预算 | `/agent/usage` | 已有 `llm_call`、`llm_budget`、`llm_alert` |
| DeerFlow 连接 | `/agent/deerflow` | 地址、启用状态、最近一次连通检查 |

接口前缀建议：

- `GET/POST /api/v1/agent/definitions`
- `GET/PATCH /api/v1/agent/definitions/{id}`
- `GET/PUT /api/v1/agent/definitions/{id}/tools`
- `GET/POST /api/v1/agent/threads` ，`POST /api/v1/agent/threads/{id}/messages`
- `GET /api/v1/agent/runs` ，`GET /api/v1/agent/runs/{id}`
- `GET/POST /api/v1/agent/tasks`
- `GET/POST /api/v1/agent/knowledge-bases` 及文档上传
- `GET/POST /api/v1/agent/evals`
- `GET/POST /api/v1/agent/deerflow/test-connection`
- 现有问答可映射为 `POST /api/v1/agent/ask`，内部仍走数字校验

所有写接口记审计。密钥类字段只写本机安全存储，接口返回一律脱敏。

---

## 6. 接入步骤（实施时，不是现在）

1. 保持现有只读工具和 `/ask` 可用，避免卖家正在用的问答中断。
2. 补齐智能体定义、运行、任务等表（只追加）。
3. 给 MCP 增加 Token 与智能体授权校验的测试。
4. 在隔离环境按官方文档启动 DeerFlow，在 `extensions_config.json` 登记 CrossERP。
5. 先验证只读问题（利润、异常）能返回带出处的答案。
6. 再验证「建议类」工具只会生成待审批记录。
7. 把 DeerFlow 运行的用量回写到监控页。
8. 用现有 20 题评测回归；DeerFlow 路径若无法完全复用原评测，需标明哪些题仍以 CrossERP 内置问答为准。

---

## 7. 明确不做的事

- 不让 DeerFlow 直接连接业务数据库。
- 不在 DeerFlow 技能或提示词里要求模型自己加总金额。
- 不把模型密钥、平台 Token、数据库密码写进仓库或设计文档的示例真值。
- 不把 DeerFlow 管理入口暴露成「谁都能改 MCP 配置」——官方已提示 Gateway 管理权限接近代码执行。
- 不在 v1.0 之前把智能体写成可以自动批准凭证。

---

## 8. 未能核实

- 在 maken 的 Windows 环境用官方推荐的 Git Bash / Docker 启动 DeerFlow 是否顺利。
- DeerFlow 当前 2.x 小版本与 CrossERP 现有 MCP SDK 是否需要额外适配字段名（官方 MCP 示例写 `mcpServers`，部分 API 文档又提到 `/api/mcp/config`，实施时以选定版本的文档为准）。
- DeerFlow 的 token 用量回写接口稳定字段（发行说明提到默认打开 token 追踪，但本次未对着某一版 OpenAPI 逐项核对）。
- 是否使用官方提到的 RAGFlow 等外部知识检索；默认不依赖。
