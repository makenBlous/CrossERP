# 登录、登出、当前用户、忘记/重置密码（P0-01-auth）

- **旧任务卡：** TASK-pf-auth（仓库外）
- **状态：** 已合入 main（b84385e–26ef0a5；幂等豁免 64b824b）
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

认证是所有接口的入口：统一会话、CSRF、会话时长、登出作废钩子。

## 范围：接口与迁移

`/auth/login`、`/auth/logout`、`/auth/me`、`/auth/forgot-password`、`/auth/reset-password`；路由文件 `src/crosserp/api/routers/auth.py`。

## 依赖

P0-01 底座。

## 必须复用的共用函数

`PermissionService`（/auth/me 的权限点、数据范围、字段策略都从 IAM 取，不取会话快照）；`api_endpoint(..., idempotency="none")`（登录、忘记/重置密码不参与幂等回放，带 Idempotency-Key 也不得返回 401）。

## 验收标准（逐条可测试）

1. 错误密码 5 次锁 15 分钟；会话 12h/空闲 2h 过期；停用账号不能登录且现有会话失效。
2. 写请求缺或错 `X-CSRF-Token` 被拒。
3. 登出后旧会话 401，且会话作废钩子被调用（作废该会话的委托、标记运行停止）。
4. `/auth/me` 返回有效权限点、数据范围、字段策略、AI 模式、本位币 CNY、时区，且与 PermissionService 一致。
5. 重置令牌只存哈希、一次性、过期失效。
6. 登录/忘记/重置密码带 Idempotency-Key 时不返回 401、不回放（有测试）。
7. AI principal 调这些 critical 接口被拒；登录成功/失败、登出、重置都进 security_event。
8. `check_merge_guard.py --base <切出点>` 0 命中，或命中已在验收报告中逐条豁免。
9. 独立验收报告 `<块>-accept.txt` 结论为"通过"，横向对比无不一致项。
10. rules.md 第 5 节全部检查 0 失败（SQLite 全量、MySQL `-m db`、双库迁移往返、ruff、mypy、文档链接、授权覆盖、API contract、密钥扫描）。

## 进度

已合入。

## 待定 / 需拍板

无。
