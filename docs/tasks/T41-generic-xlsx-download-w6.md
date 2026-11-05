# T41 通用 Excel 目标 `generic_xlsx` + 网页「下载凭证」+ W6 验收证据（⚠ 待 maken 确认）

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| doing | W6 | 1.5 天 | T40 | `main` |

## 目标
不用金蝶的人也能导出一份通用 Excel 凭证；财务在网页上批准凭证后能点「下载凭证」；没批准的凭证点下载（或直接访问下载地址）返回 403，且审计里有被拒记录。

## 背景
- 实施方案 8 W6 第 4、5 条与 W6 验收（「未审批调用导出返回 403；黄金样例导出的凭证借贷平衡」）。
- 仓库现状：审批 token 是一次性的，`approve()` 返回明文 token、库里只存 `token_hash`；CLI 流程是「approve 打印 token → export 带 token」。网页上让用户复制粘贴 token 不合理，见 Q1。
- `export_artifact` 已记录产物路径和哈希（T25/T27）。

## 范围
- `ledger/targets/generic_xlsx.py`：两张表「凭证头」「分录」，中文列名，固定格式；支持 `voucher`。
- 网页（`voucher.download` 权限，finance）：
  - `/vouchers` 列表与 `/vouchers/{id}` 详情（分录表、借贷合计、状态、审批记录）；operator 可在此「生成草稿」「提交审批」（调用 T39 service）。
  - 按 Q1 方案实现下载：`GET /vouchers/{id}/download?target=kingdee_xlsx|generic_xlsx`。
  - 未批准 / 已作废 / 数据已变 → 403 页面 + `audit_log` 拒绝记录（复用 `_record_denial`，`reason_code` 与 CLI 一致）+ `security_event(permission_denied)` 仅在缺权限时写（状态不对不算越权）。
- W6 证据 `docs/evidence/W6.md`：黄金样例凭证借贷平衡测试输出、两种格式文件截图位（待 maken 补）、403 测试输出、审计记录。
- 提交：`main`，`feat(web): add voucher download with approval gate (T41)`；证据 `docs: add W6 evidence (T41)`；测试不过不提交；不发布。

## 不做
- 不做邮件发送凭证；不做批量下载。

## 步骤
1. 先写测试：未批准 GET 下载 403 + 审计；批准后下载两种格式都成功且内容一致（同一凭证）；第二次下载（Q1-A 下）返回同一个已存文件、`export_artifact` 不新增；operator 下载 403；直接猜 URL 下载别的凭证 403。
2. 实现 → 证据。

## 涉及文件
`src/crosserp/ledger/targets/generic_xlsx.py` `src/crosserp/ledger/write_service.py`（注册） `src/crosserp/web/routes/vouchers.py` `src/crosserp/web/routes/approvals.py` `src/crosserp/web/routes/__init__.py` `src/crosserp/web/templates/{vouchers,voucher_detail}.html` `tests/web/test_voucher_download.py` `tests/web/test_permission_matrix.py`（只追加） `docs/evidence/W6.md` `docs/vouchers.md` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/web -k voucher -q` | passed |
| `uv run pytest -m db -q`（三库） | passed |
| `uv run crosserp check-golden` | 通过（原黄金样例不受影响） |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] `op1` 登录「凭证」页，生成并提交一张凭证。
- [ ] 还没批准时，`fin1` 点「下载凭证」：显示没有批准，不能下载。
- [ ] `fin1` 批准后再点下载：两种格式都能下，Excel 里借方合计 = 贷方合计。
- [ ] `aud1` 打开审计页：能看到那次被拒的下载和成功的下载。
- [ ] 补 `docs/evidence/W6.md` 的截图。

## 问题
- **Q1 ⚠ 待 maken 确认：网页上一次性 token 怎么用。** 选项：A 批准的同一个请求里，服务端立刻用刚生成的 token 调 `write_service.export` 生成两种格式文件并存为 `export_artifact`，token 当场消费；之后「下载」只是读取已存产物（需已批准且产物哈希匹配）（推荐：token 不出服务端，仍是一次性，红线不变）；B 批准后页面显示 token，用户粘贴到下载表单（麻烦、易泄露）；C 下载时用会话身份代替 token（会改变红线语义，不推荐）。
- **Q2 ⚠ 待 maken 确认：Q1-A 下，批准时生成哪些格式。** 选项：A 两种都生成（推荐；需要给 `write_service.export` 增加 `target_ids: list[str]`，一次校验、一次消费 token、生成多个产物，同一事务；单目标调用行为不变）；B 只生成 accounts 配置里指定的默认格式。

按推荐默认执行 Q1-A、Q2-A：批准后服务端一次生成两种格式并消费 token，网页下载只读取已保存产物。

## 完成记录
- 完成内容：新增通用双表 Excel 目标；唯一写出口支持一次审批生成多个目标并只消费一次 token；网页新增凭证列表/详情和两种格式下载；未批准、无文件、目标不匹配和越权下载均拒绝并记录审计；新增 W6 验收证据。
- 修改文件：`src/crosserp/ledger/targets/generic_xlsx.py`、`src/crosserp/ledger/write_service.py`、`src/crosserp/web/app.py`、`src/crosserp/web/routes/__init__.py`、`src/crosserp/web/templates/{vouchers,voucher_detail,index}.html`、`tests/web/test_voucher_download.py`、`docs/evidence/W6.md`、`docs/vouchers.md`、`CHANGELOG.md`。
- 测试结果：网页/凭证导出/守卫 15 passed；写出筛选 18 passed；全量 SQLite `.venv/bin/pytest -q --cov=crosserp --cov-fail-under=60` 为 246 passed、7 skipped，覆盖率 79.72%；MySQL 8.4 和 PostgreSQL 18 凭证导出各 1 passed；`.venv/bin/ruff check .`、`.venv/bin/mypy`、`.venv/bin/pre-commit run --all-files` 通过。
- 偏离计划：当前网页仍集中装配在 `web/app.py`，按现有项目结构实现；通用格式固定中文两表，金蝶格式继续使用 T40 的可配置模板。
