# 合并前验收流程：自动检查 + 独立验收 agent

> 目的：拦住"知道规则但为了让测试通过而放松"的改动（删改安全断言、静默放行、兜底写法），并横向对比各模块是否一致使用共用函数。
> 适用：每个功能块合入 main 之前；合并任务（merge-*）在 `git merge` 之前执行。

## 1. 流程总览

```
开发 agent 提交（工作树 0 失败）
  → ① 自动检查 check_merge_guard（开发 agent 自己先跑；监督方复跑）
  → ② 独立验收 agent（另开只读 grok，不是写代码的那个）
  → ③ 监督方读 <块>-accept.txt：全部通过 → 写 <块>-ok.txt；有"不通过" → 写返工任务，回到开发
  → ④ 合并任务 merge-*：合并前再跑一次 ①，合并后全量回归
```

任何一步不通过都不能合并。验收 agent 的结论只能是"通过 / 不通过"，没有"有条件通过"；有条件的一律记为不通过并列出返工项。

## 2. ① 自动检查 `scripts/check_merge_guard.py`

```powershell
uv run python scripts/check_merge_guard.py --base <该块切出时的 main 提交> [--head <块的提交>] [--waivers <豁免文件>]
uv run python scripts/check_merge_guard.py --list-rules   # 打印全部规则
```

- 只看 diff 中新增和删除的行，命中即退出码 1；无命中 0。
- 拦截内容（规则 ID 以脚本 `--list-rules` 为准）：
  - **安全断言被删或放宽**（tests/ 下）：涉及权限、范围、审批、审计、幂等、撤销、风险档、密钥的 `assert`/`pytest.raises`/状态码断言被删除且没有原样移到别处；状态码从 4xx 改成 2xx；精确比较改成宽松比较；整份测试文件删除。
  - **新增 skip/xfail**、调大超时。
  - **防御性写法**（src/ 下新增）：`.get(x, 默认)`、`getattr(x, "y", 默认)`、`or {}`/`or []`、`except: pass`、吞异常、无返回值的静默早退、新增 `X | None = None` 可选参数、`hasattr`/兼容性 `isinstance`。
  - **自写共用逻辑**（src/ 下新增）：在 `iam/scope.py` 之外自建店铺集合或 `.in_()` 范围过滤、在幂等模块之外处理 `Idempotency-Key`/回放、在 `platform/factory.py` 之外直接构造 `ActionDispatcher(`、自建审批结果兼容壳、绕开 AuditRecorder 写审计。
- **豁免**：只有验收报告（`<块>-accept.txt`）"豁免"段里逐条写明的命中可以豁免。豁免文件每行 `指纹<TAB>理由`，理由必须说明为什么这不是放松（例如"断言改写为更严格的 ApprovalSubmission 字段比较，原断言见新文件第 N 行"）。指纹由脚本输出，不含行号。安全断言类命中原则上不豁免，只有"改得更严格"或"原样迁移"才可豁免。

## 3. ② 独立验收 agent

### 3.1 原则

- 另开一个 grok，**只读**：不改文件、不提交、不起服务、不跑会写库的命令（测试只在隔离库里跑，且可以不跑）。它不是开发这块的 agent，也不复用开发 agent 的会话。
- 输入：该块 diff、对应功能文件的验收标准、[rules.md](rules.md)、自动检查输出。
- 逐条判定功能文件"验收标准"里的每一项：通过 / 不通过 + 证据（文件:行 或测试名）。没有测试覆盖的条目判不通过。
- **横向对比**：把本块与 main 上同类模块对照，确认一致使用 [rules.md](rules.md) 第 3 节 的共用函数；列出本块里任何与其他模块不同的写法（范围过滤、幂等声明、执行器构造、审批结果读取、撤销登记、错误码）。
- **测试改动逐条核对**：diff 里每一处被删或被改的测试断言，判断是"更严 / 等价 / 放松"，放松一律不通过。
- 输出到 `%TEMP%\cx-pw\backend\<块>-accept.txt`（UTF-8），固定格式见 3.3。

### 3.2 启动方式

1. 监督方在 `%TEMP%\cx-pw\backend\` 准备输入：
   ```powershell
   $B="$env:TEMP\cx-pw\backend"; $K="<块名>"; $BASE="<切出时 main 提交>"; $HEAD="<块提交>"
   git -C D:\make\write\work\CrossERP diff --stat $BASE $HEAD | Out-File -Encoding UTF8 "$B\$K-accept-diffstat.txt"
   git -C D:\make\write\work\CrossERP diff $BASE $HEAD | Out-File -Encoding UTF8 "$B\$K-accept.diff"
   uv run python scripts/check_merge_guard.py --base $BASE --head $HEAD | Out-File -Encoding UTF8 "$B\$K-guard.txt"
   ```
   （在块的工作树里执行 check_merge_guard；退出码 1 不影响后续验收，结果交给验收 agent。）
2. 按 3.4 的模板写 `%TEMP%\cx-pw\backend\TASK-accept-<块名>.md`。
3. 用同一个启动脚本启动只读 grok，工作目录指向**该块的工作树**（只读使用）：
   ```powershell
   & "$env:TEMP\cx-pw\backend\start_task_grok.ps1" -Task accept-<块名> -Dir D:\make\write\work\CrossERP-wt\<块树名> -Rules "docs/tasks/rules.md, docs/tasks/acceptance.md"
   ```
   启动脚本把 grok 的最终输出写到 `accept-<块名>-last.txt`；验收报告本体由 grok 写到 `<块名>-accept.txt`。
4. 验收结束后在块工作树里跑 `git status --short`，必须没有新改动；有改动说明验收 agent 越权，报告作废并重跑。

### 3.3 报告格式（`<块>-accept.txt`）

```
# 验收：<块名>   基线 <BASE>   提交 <HEAD>   时间 <北京时间>
## 结论：通过 | 不通过
## 一、验收标准逐条
| # | 验收条目（照抄功能文件） | 判定 | 证据（文件:行 / 测试名） |
## 二、自动检查命中
| 指纹 | 规则 | 文件:行 | 判定（放松/防御性/误报） | 说明 |
## 三、测试断言改动逐条
| 文件:行 | 改动前 | 改动后 | 更严/等价/放松 |
## 四、横向对比共用函数
| 能力 | 本块写法 | main 上同类模块写法 | 是否一致 |
## 五、豁免（只列确认不是放松的自动检查命中；每行：指纹<TAB>理由）
## 六、返工项（不通过时必填，逐条可执行）
```

### 3.4 验收任务模板（复制到 `TASK-accept-<块名>.md`，替换尖括号）

```markdown
# 任务 accept-<块名>：独立验收（只读）

你是独立验收员，不是开发者。**只读**：不得修改、新建或删除仓库内任何文件，不得 git add/commit/stash/checkout/reset，不得起服务，不得读 `.env`、`CrossERP演示密码.txt`、任何密钥，不得碰 `~/.crosserp`。唯一允许写的文件是 `%TEMP%\cx-pw\backend\<块名>-accept.txt`。

## 输入
- 本工作树：D:\make\write\work\CrossERP-wt\<块树名>（只读）
- 规则：docs/tasks/rules.md、docs/tasks/acceptance.md
- 功能文件：docs/tasks/<pX>/<功能文件>.md（"验收标准"一节逐条判定）
- diff：%TEMP%\cx-pw\backend\<块名>-accept.diff（基线 <BASE>，提交 <HEAD>）；统计 <块名>-accept-diffstat.txt
- 自动检查结果：%TEMP%\cx-pw\backend\<块名>-guard.txt
- 横向对比参照（main 上已合入的同类模块）：<例如 src/crosserp/api/routers/catalog_listings.py、catalog_skus.py>

## 要做
1. 逐条判定功能文件的每条验收标准：通过/不通过，附文件:行或测试名。没有测试覆盖的判不通过。
2. 逐条判定 guard 命中：放松 / 防御性 / 误报。只有"误报"或"改得更严 / 原样迁移"才能进豁免段，并写理由。
3. 逐条列出 diff 中被删或被改的测试断言，判定更严/等价/放松。放松即不通过。
4. 横向对比：店铺范围、其他数据范围、字段权限、执行器构造、幂等声明（api_endpoint 的 idempotency）、审批结果读取（ApprovalSubmission）、审计、撤销登记、错误码与状态码，本块是否与参照模块一致使用 rules.md 第 3 节的共用函数；不一致逐条列出。
5. 检查 rules.md 第 4 节的防御性写法（guard 可能漏掉的也要找）。
6. 如需运行测试，只能带隔离库：`$env:CROSSERP_DATABASE_URL="sqlite:///C:/Users/cimi/AppData/Local/Temp/cx-pw/backend/db/accept-<块名>.db"`（MIGRATE 同值），只跑与本块相关的测试。
7. 按 docs/tasks/acceptance.md 3.3 的格式写 %TEMP%\cx-pw\backend\<块名>-accept.txt。结论只能是"通过"或"不通过"。

最后用中文打印结论和返工项摘要。
```

## 4. ③ 监督方处理

- 结论"通过"且第二节每条命中都已判定、豁免段理由充分 → 用豁免段生成 `%TEMP%\cx-pw\backend\<块>-waivers.txt`，复跑 `check_merge_guard --waivers` 退出码 0 → 写 `<块>-ok.txt`，更新功能文件的"进度"和 [README](README.md) 进度表。
- 结论"不通过" → 按"返工项"写返工任务（在原工作树新提交），返工后重新走 ①②。
- 监督方仍要抽查验收报告：至少核对"测试断言改动"一节与 diff 一致。
- 合入 main 后更新 [`docs/PROJECT_MEMORY.md`](../PROJECT_MEMORY.md)（当前状态、新增决策；见该文件「更新规则」）。

## 5. ④ 合并任务里的接入

合并任务卡（merge-*）在每块 `git merge` 之前加两步：
1. 确认 `<块>-ok.txt` 和 `<块>-accept.txt` 存在且结论为"通过"。
2. 在主工作区对该块提交跑 `check_merge_guard --base <合并前 main> --head <块提交> --waivers <块>-waivers.txt`，退出码 0 才合并。合并时解决冲突产生的新改动，合并后再对 `<合并前 main>..HEAD` 跑一次；新命中要么修掉，要么走一次补充验收。
3. 合入后更新 [`docs/PROJECT_MEMORY.md`](../PROJECT_MEMORY.md)。可与功能文件进度放在同一提交，或紧接着再提交一次。
