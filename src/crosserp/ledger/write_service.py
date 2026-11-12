"""唯一的外部写出入口。"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.approval.payload import compute as compute_payload
from crosserp.approval.service import hash_token, mark_exported
from crosserp.approval.state import ApprovalState
from crosserp.audit.log import append
from crosserp.core.errors import CrossErpError
from crosserp.db.schema import Approval, ExportArtifact, Voucher
from crosserp.ledger.targets.base import LedgerTarget
from crosserp.vouchers.accounts import AccountMapping
from crosserp.vouchers.model import VoucherDraft, VoucherLineDraft
from crosserp.vouchers.service import save_draft

# 调整草稿使用示例科目占位编码。占位编码拒绝过账。本函数只写 state=draft。
_DRAFT_ACCOUNTS = {
    "fx_diff": AccountMapping("fx_diff", "待会计核实-汇兑差", "汇兑差", "either"),
    "platform_receivable": AccountMapping(
        "platform_receivable", "待会计核实-平台应收", "平台应收", "either"
    ),
}


class ApprovalRequired(CrossErpError):
    """写出前置审批不满足。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(message)


def write_issue_adjustment_draft(
    session: Session,
    *,
    issue_id: UUID,
    store_id: UUID,
    period: str,
    amount: Decimal,
    currency: str,
    created_by: str,
) -> Voucher:
    """由对账异常写一张借贷平衡的调整凭证草稿。不导出、不过账。"""
    if not isinstance(amount, Decimal):
        raise TypeError("调整金额必须是 Decimal")
    if amount == 0:
        raise ValueError("调整金额不能为零")
    magnitude = abs(amount)
    debit_account = _DRAFT_ACCOUNTS["fx_diff"]
    credit_account = _DRAFT_ACCOUNTS["platform_receivable"]
    if amount < 0:
        debit_account, credit_account = credit_account, debit_account
    source_ref = str(issue_id)
    summary = f"异常调整 {source_ref}"
    draft = VoucherDraft(
        id=None,
        store_id=store_id,
        period=period,
        source_type="issue",
        source_id=source_ref,
        currency=currency,
        inputs_hash=_digest(
            {"issueId": source_ref, "amount": str(amount), "currency": currency, "period": period}
        ),
        accounts_hash=_digest(
            {
                key: {
                    "code": item.code,
                    "name": item.name,
                    "direction": item.direction,
                }
                for key, item in _DRAFT_ACCOUNTS.items()
            }
        ),
        created_by=created_by,
        lines=(
            VoucherLineDraft(
                1,
                debit_account.key,
                debit_account.code,
                debit_account.name,
                magnitude,
                Decimal(0),
                summary,
                source_ref,
            ),
            VoucherLineDraft(
                2,
                credit_account.key,
                credit_account.code,
                credit_account.name,
                Decimal(0),
                magnitude,
                summary,
                source_ref,
            ),
        ),
    )
    return save_draft(session, draft)


def _digest(value: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def ledger_export_dir() -> Path:
    """写出文件的唯一目录。"""
    return Path.cwd() / "exports"


def export(
    session: Session,
    batch_id: str,
    target_id: str,
    approval_token: str | None,
) -> ExportArtifact:
    """验证审批、生成 XLSX、记录产物并消费一次性 token。"""
    return export_many(
        session,
        batch_id,
        approval_token,
        target_ids=[target_id],
    )[0]


def export_many(
    session: Session,
    batch_id: str,
    approval_token: str | None,
    *,
    target_ids: list[str],
) -> list[ExportArtifact]:
    """一次校验并消费审批 token, 生成多个格式的凭证产物。"""
    if not target_ids:
        raise ValueError("至少需要一个写出目标")
    approval: Approval | None = None
    approval_id: UUID | None = None
    reason: tuple[str, str] | None = None
    bind = session.get_bind()
    # 先用独立会话完成拒绝判断，避免 SQLite 读锁挡住拒绝审计。  # noqa: RUF003
    with Session(bind=bind) as validation:
        if approval_token:
            approval = validation.scalar(
                select(Approval).where(Approval.token_hash == hash_token(approval_token))
            )
        if approval is None:
            reason = ("MISSING_APPROVAL", "没有有效审批或审批 token 不正确")
        else:
            approval_id = approval.id
            if approval.target_type + ":" + approval.target_id != batch_id:
                reason = ("TARGET_MISMATCH", "审批对象与要导出的对象不一致")
            elif approval.used_at is not None:
                reason = ("TOKEN_USED", "审批已被使用，不能重复导出")  # noqa: RUF001
            elif approval.state not in {
                ApprovalState.APPROVED.value,
                "auto_effective",
                "initiator_confirmed",
            }:
                reason = ("NOT_APPROVED", "审批当前不是已批准状态")
            else:
                current_hash = _payload_hash(validation, approval.target_type, approval.target_id)
                if current_hash != approval.payload_hash:
                    reason = (
                        "PAYLOAD_CHANGED",
                        "审批后的报表内容已经变化，请重新申请审批",  # noqa: RUF001
                    )

    if reason is not None:
        _record_denial(session, batch_id, reason[1], approval_id)
        raise ApprovalRequired(reason[0], reason[1])
    assert approval_id is not None
    approval = session.get(Approval, approval_id)
    if approval is None:
        _record_denial(session, batch_id, "审批单在导出前消失", approval_id)
        raise ApprovalRequired("MISSING_APPROVAL", "审批单在导出前消失")
    targets = [_target(target_id) for target_id in target_ids]
    if any(approval.target_type not in target.supported_types for target in targets):
        _record_denial(session, batch_id, "TARGET_TYPE_MISMATCH", approval.id)
        raise ApprovalRequired("TARGET_TYPE_MISMATCH", "审批对象类型与写出目标不匹配")
    paths = [
        target.render(
            session,
            batch_id=batch_id,
            approval_id=str(approval.id),
            output_dir=ledger_export_dir(),
        )
        for target in targets
    ]
    now = datetime.now(UTC)
    artifacts: list[ExportArtifact] = []
    for target, path in zip(targets, paths, strict=True):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        artifact = ExportArtifact(
            id=uuid4(),
            approval_id=approval.id,
            target_id=target.id,
            file_path=str(path),
            ext_ref=None,
            sha256=digest,
            created_at=now,
        )
        session.add(artifact)
        session.flush()
        artifacts.append(artifact)
    approval.used_at = now
    mark_exported(session, approval, actor="system")
    for artifact, path, target in zip(artifacts, paths, targets, strict=True):
        append(
            session,
            "system",
            "ledger.export",
            "export_artifact",
            str(artifact.id),
            None,
            {
                "approval_id": str(approval.id),
                "target_id": target.id,
                "file_path": str(path),
                "sha256": artifact.sha256,
            },
            approval_id=approval.id,
            approver_id=None,
            self_approved=False,
        )
    return artifacts


def _record_denial(
    session: Session,
    batch_id: str,
    reason: str,
    approval_id: UUID | None,
) -> None:
    """在独立事务里写拒绝审计，避免外层回滚吞掉拒绝记录。"""  # noqa: RUF002
    bind = session.get_bind()
    with Session(bind=bind) as audit_session, audit_session.begin():
        append(
            audit_session,
            "system",
            "ledger.export_denied",
            "ledger_export",
            batch_id,
            None,
            {"approval_id": None if approval_id is None else str(approval_id)},
            reason=reason,
            approval_id=approval_id,
            self_approved=False,
        )


def _payload_hash(session: Session, target_type: str, target_id: str | None = None) -> str:
    if target_id is None:
        target_id = target_type
        target_type = "profit_report"
    try:
        return compute_payload(session, target_type, target_id)
    except LookupError as exc:
        raise ApprovalRequired("MISSING_REPORT", str(exc)) from exc
    except ValueError as exc:
        raise ApprovalRequired("INVALID_TARGET", str(exc)) from exc


def export_target_catalog() -> tuple[tuple[str, frozenset[str]], ...]:
    """列出写出目标 id 及其支持的审批对象类型。"""
    targets = (_target("xlsx"), _target("kingdee_xlsx"), _target("generic_xlsx"))
    return tuple((target.id, target.supported_types) for target in targets)


def _target(target_id: str) -> LedgerTarget:
    if target_id == "xlsx":
        from crosserp.ledger.targets.xlsx import XlsxLedgerTarget

        return XlsxLedgerTarget()
    if target_id == "kingdee_xlsx":
        from crosserp.ledger.targets.kingdee_xlsx import KingdeeXlsxTarget

        return KingdeeXlsxTarget()
    if target_id == "generic_xlsx":
        from crosserp.ledger.targets.generic_xlsx import GenericXlsxTarget

        return GenericXlsxTarget()
    raise ApprovalRequired("UNKNOWN_TARGET", f"不支持的写出目标 {target_id}")
