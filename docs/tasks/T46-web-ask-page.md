# T46 网页 AI 问答页：引用可点开到原始行 + 审计

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W7 | 1 天 | T45 | `main` |

## 目标
在网页「问一问」里提问，得到带引用的中文回答；点引用能打开对应的利润行/异常/订单原始行；每次提问在业务审计里有记录。

## 背景
- 实施方案 8 W7 第 6 条与 W7 验收（「10 个常见问题能回答且引用可点；编造数字被拦截」）。
- 权限 `ai.ask`（T35）；原始行页面已在 T37 做好（`/issues/{id}`），本任务补 `/rows/{table}/{id}` 通用只读查看（只允许白名单表：`profit_snapshot`、`order_line`、`settlement_line`、`raw_row`、`issue`、`voucher`、`voucher_line`、`approval`），权限按 T37 Q2 结论。

## 范围
- `/ask`：输入框（≤ 500 字）+ 结果区（HTMX，显示「正在查询…」），回答中 `[^n]` 渲染为链接到 `/rows/...`；被拒时显示原因（「回答中的数字 X 没有来源，已拦截」）。
- 审计：`audit_log(action="ai.ask", target_type="llm_call", target_id=llm_call.id)`，`after_json` 只放 `{question_sha256, answer_sha256, refused, citations_count}`，不放正文（正文在 `llm_call`，按 T45 保留期清理，审计链不受影响）。
- 速率限制：每用户每分钟 ≤ 6 次（内存计数，单进程；可配置）。
- 提交：`main`，`feat(web): add ask page with clickable citations (T46)`；测试不过不提交；不发布。

## 不做
- 不做多轮对话、不做历史记录页（监控页 T48 可看）。

## 步骤
1. 先写测试（`FunctionModel`）：正常回答引用链接可打开且 200；编造数字 → 页面显示拦截；auditor 访问 `/ask` 403；`/rows/app_user/...` 404（不在白名单）；审计行不含正文。
2. 实现。

## 涉及文件
`src/crosserp/web/routes/{ask,rows}.py` `src/crosserp/web/routes/__init__.py` `src/crosserp/web/templates/{ask,row_detail}.html` `tests/web/test_ask_page.py` `tests/web/test_rows_whitelist.py` `tests/web/test_permission_matrix.py`（只追加） `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/web -k "ask or rows" -q` | passed |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 配好模型环境变量后 `serve`，用 `op1` 登录「问一问」，问「demo 店铺上个月哪个 SKU 亏钱最多？」。
- [ ] 点回答里的 [1]：打开的就是那一行数据。
- [ ] 用 `aud1` 打开审计页：能看到这次提问的记录（只有摘要，没有全文）。

## 问题
- 无新的待确认项（原始行可见范围沿用 T37 Q2）。

## 完成记录
- 完成内容：新增 `/ask` 页面和 POST 问答入口，接入 AI 权限、500 字限制、每用户每分钟 6 次内存限流；新增白名单 `/rows/{table}/{id}` 只读原始行页；问答摘要写入 `audit_log`，不写正文；未配置模型时显示中文提示。
- 修改文件：`src/crosserp/web/app.py`、`src/crosserp/web/routes/__init__.py`、`src/crosserp/web/templates/{ask,row_detail,index}.html`、`tests/web/test_ask_page.py`、`tests/web/test_rows_whitelist.py`、`CHANGELOG.md`。
- 测试结果：`.venv/bin/pytest tests/web -k "ask or rows" -q` 为 2 passed；全量 SQLite `.venv/bin/pytest -q --cov=crosserp --cov-fail-under=60` 为 261 passed、7 skipped，覆盖率 79.19%；`.venv/bin/ruff check .`、`.venv/bin/mypy`、`.venv/bin/pre-commit run --all-files` 通过。
