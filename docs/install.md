# 安装

本文状态：**已实现安装路径 + 仅设计部署目标**。

## 本机演示

代码包要求 Python 3.12 或更高版本，使用 `uv` 安装依赖；默认数据库为 SQLite `~/.crosserp/data.db`。运行 `crosserp init` 后可启动现有 FastAPI/Jinja 网页。具体命令以 `README.md`、`pyproject.toml` 和 CLI 帮助为准。

## 正式环境目标

部署到内网服务器，使用 MySQL 8.4 LTS，单法人、不做多租户。FastAPI 与 agent worker 是两个进程；worker 采用独立 Python 环境嵌入 DeerFlow SDK。生产不需要 Docker，也不需要独立 DeerFlow 服务；仓库 Compose 仅可选。

## 安全

不把 `.env`、密钥、密码或真实卖家数据写进仓库。模型配置使用 OpenAI 兼容的 `baseUrl`、`apiKey`、`model`，密钥加密存储、不回显、不写日志。详见 [安全](security.md) 和 [08 第 10、11 章](design/08-后端模块与API设计.md)。
