# 凭证草稿

T39 只生成数据库中的凭证草稿，不向金蝶或其他外部系统写出。科目编码来自
`CROSSERP_ACCOUNTS_FILE` 指向的 YAML；没有设置时读取 `~/.crosserp/accounts.yaml`。
可以复制 `config/accounts.example.yaml` 后填写实际科目编码。示例中的编码均标为「待会计核实」，不能直接生成凭证。

当前支持按店铺月份生成：

```bash
cp config/accounts.example.yaml ~/.crosserp/accounts.yaml
# 编辑 ~/.crosserp/accounts.yaml，替换所有「待会计核实」编码
.venv/bin/crosserp voucher draft --store <店铺名> --period 2026-10 --by month --as maken
.venv/bin/crosserp voucher list
.venv/bin/crosserp voucher show <凭证 UUID>
.venv/bin/crosserp voucher submit <凭证 UUID> --as maken
```

每条分录只能有借方或贷方；保存前用 Decimal 检查借贷合计，任何不平衡的草稿都会被拒绝。
凭证审批哈希包含输入哈希、科目文件哈希和规范化分录，科目文件修改后旧审批会失效。
