# Contributing to CrossERP

开发环境使用仓库内 `.venv`：

```bash
uv sync --all-extras
source .venv/bin/activate
```

本项目单人直接在 `main` 开发，不创建任务分支或工作树。一次只处理一个任务，先把任务状态改为 `doing`，测试和文档完成后改为 `review`。提交信息使用 Conventional Commits 并带任务号，例如 `test: add import regression coverage (T54)`。

提交前运行：

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest --cov=crosserp --cov-fail-under=80 -q
uv run pre-commit run --all-files
```

测试失败不能通过删除测试、跳过测试或使用 mock 冒充真实验收来解决。金额只能由确定性代码计算；写账必须审批；提交中不能放密钥或真实卖家数据。当前阶段不发布 PyPI、镜像或 GitHub Release。
