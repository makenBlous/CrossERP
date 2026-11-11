# DocumentLink 平台底座接口实现计划

> **面向 AI 代理的工作者：** 需要遵循测试驱动开发与完成前验证要求。

**目标：** 将 DocumentLink 的 links 与 chain 查询拆到独立自动发现路由，按契约返回分页和链路，并按调用人数据范围过滤。

**架构：** 新建 `documents.py` 仅负责 DocumentLink 查询，复用 `platform.py` 的身份、数据库和分页辅助函数。平台路由删除两条旧函数，保持其他路由及公共辅助区不变。链查询先筛选调用人可见边，再对可见子图遍历并对环路去重。

**技术栈：** FastAPI、SQLAlchemy 2、Pydantic 2、pytest、SQLite/MySQL。

---

### 任务 1：补充 DocumentLink API 失败测试

**文件：**
- 创建：`tests/api/test_pf_docs.py`
- 参考：`tests/api/conftest.py`、`tests/api/test_platform_endpoints.py`

- [ ] 建立可见/不可见单据和链路，验证 links 分页、数据范围过滤、未登录 401、无权/不存在链节点 404。
- [ ] 验证 chain 返回完整可见链、隐藏节点不泄露、环路去重。
- [ ] 运行测试确认因路由/过滤缺失而失败。

### 任务 2：拆出 documents 路由并实现最小契约

**文件：**
- 创建：`src/crosserp/api/routers/documents.py`
- 修改：`src/crosserp/api/routers/platform.py`（仅删除两条 DocumentLink 路由及其模型导入）

- [ ] 使用 Pydantic `PageParams` 查询参数和现有 metadata，声明契约中的 permission/riskTier/entity/action。
- [ ] 复用 `_principal_db`、`_page`；对链接端点按可见文档集合过滤；chain 对可见图遍历并去重，目标不存在或不可见统一 404。
- [ ] 运行专用测试并保持 ruff/mypy 通过。

### 任务 3：完整验证与提交

**文件：**
- 修改：仅实现与测试文件及计划文件

- [ ] 运行 ruff format/check、mypy、全量 pytest、文档链接、授权覆盖、SQLite 迁移往返、MySQL db 标记测试（若实例可用）。
- [ ] 检查密钥扫描与 git diff，按要求用 UTF-8 文件执行 `git commit -F`。

审查补充：links 采用 OpenAPI 的 q/sort 与 pageSize 默认 20，排序稳定；两个端点显式调用统一 `_require`，并在过滤边后遍历可见无向子图，环路按 link id 去重。测试覆盖路由自动发现、元数据、分页字段、查询过滤、权限/范围 404 和隐藏节点不泄露。

边界约定：无 `storeIds` 或含 `all` 的范围为全可见；受限范围从允许的 Store 节点开始，空 `storeIds` 只产生空可见子图；每条边两端都必须属于可见节点，先过滤边再无向遍历，孤立的非 Store 边在受限范围下不可见。链查询同样按可见根判断，未登录 links/chain 都返回 401。
