# 凭证与写账

本文状态：**凭证和审批已实现；扩展实体动作仅设计**。

现有 `vouchers/` 生成凭证草稿，`approval/` 管理 `draft → pending → approved/rejected → exported`，`ledger/write_service.py` 是唯一写账/导出出口。它检查批准状态、内容哈希和一次性令牌；其他模块不得直接导入 `ledger.targets`。金额由确定性代码计算，AI 只能解释、建议或生成草稿。

目标设计增加实体动作投射、按流程配置解析审批人和 `awaiting_initiator`。配置了审批人必须审批；没有可用审批人时，人发起的单据直接生效并留痕，AI 发起的钱账或高风险动作须由本人确认。审批不设金额上限。金额统一 `Money.amountMinor` 万分位整数；会计科目和税务口径是演示默认值，真实使用前需核实。

详见 [ADR 0001](adr/0001-single-write-path.md)、[ADR 0009](adr/0009-approval-resolution.md) 和 [08 第 4.6、7、8 章](design/08-后端模块与API设计.md)。
