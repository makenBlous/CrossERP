"""Deterministic reconciliation rule protocol and registry."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from crosserp.core.enums import IssueKind


@dataclass(frozen=True)
class RuleIssue:
    """A deterministic issue returned by a rule before persistence."""

    kind: IssueKind
    detail: dict[str, Any]


@dataclass(frozen=True)
class Matched:
    """The rule matched the group and selected order lines."""

    order_lines: tuple[Any, ...]
    rule_id: str
    diff: Decimal


@dataclass(frozen=True)
class Unmatched:
    """The rule rejected the group with one or more issue descriptions."""

    issues: tuple[RuleIssue, ...]


@dataclass(frozen=True)
class Pass:
    """The rule does not decide this group; continue with the next rule."""


type RuleResult = Matched | Unmatched | Pass


class Rule(Protocol):
    """Protocol implemented by each ordered reconciliation rule."""

    id: str
    version: str

    def applies(self, group: Any) -> bool:
        """Return whether this rule applies to the group."""

    def evaluate(self, ctx: Any, group: Any) -> RuleResult:
        """Evaluate the group without performing database writes."""


@dataclass(frozen=True)
class _Rule:
    id: str
    version: str
    predicate: Callable[[Any], bool]
    evaluator: Callable[[Any, Any], RuleResult]

    def applies(self, group: Any) -> bool:
        return bool(self.predicate(group))

    def evaluate(self, ctx: Any, group: Any) -> RuleResult:
        return self.evaluator(ctx, group)


def _platform(group: Any) -> str:
    return str(group.settlement.platform)


def _sku_mapped(ctx: Any, group: Any) -> RuleResult:
    key = group.key[1]
    if not key or key not in ctx.sku_values:
        return Unmatched((RuleIssue(IssueKind.SKU_UNMAPPED, {"sku": key}),))
    return Pass()


def _order_exists(ctx: Any, group: Any) -> RuleResult:
    if ctx.candidates:
        return Pass()
    kind = IssueKind.REFUND_WITHOUT_ORDER if ctx.all_refunds else IssueKind.NOT_IN_ERP
    return Unmatched((RuleIssue(kind, {}),))


def _currency(ctx: Any, group: Any) -> RuleResult:
    currencies = {order.currency for order in ctx.candidates}
    if any(group.settlement.currency != currency for currency in currencies):
        return Unmatched(
            (
                RuleIssue(
                    IssueKind.CURRENCY_MISMATCH,
                    {
                        "currency_settlement": group.settlement.currency,
                        "currency_order": sorted(currencies),
                    },
                ),
            )
        )
    return Pass()


def _qty(ctx: Any, group: Any) -> RuleResult:
    if ctx.settlement_qty != ctx.order_qty:
        return Unmatched(
            (
                RuleIssue(
                    IssueKind.QTY_MISMATCH,
                    {"qty_settlement": ctx.settlement_qty, "qty_order": ctx.order_qty},
                ),
            )
        )
    return Pass()


def _amount(ctx: Any, group: Any) -> RuleResult:
    if ctx.has_expected_amount and ctx.actual_amount != ctx.expected_amount:
        return Unmatched(
            (
                RuleIssue(
                    IssueKind.AMOUNT_MISMATCH,
                    {
                        "principal": str(ctx.actual_amount),
                        "item_price": str(ctx.expected_amount),
                        "diff": str(ctx.actual_amount - ctx.expected_amount),
                    },
                ),
            )
        )
    return Pass()


def _match(ctx: Any, group: Any) -> RuleResult:
    rule_id = "R06_order_id_sku" if _platform(group) == "amazon" else "R06_order_id"
    return Matched(tuple(ctx.candidates), rule_id, Decimal(0))


RULES = (
    _Rule("R01_sku_mapped", "1", lambda group: _platform(group) == "amazon", _sku_mapped),
    _Rule("R02_order_exists", "1", lambda group: True, _order_exists),
    _Rule("R03_currency", "1", lambda group: True, _currency),
    _Rule("R04_qty", "1", lambda group: _platform(group) == "amazon", _qty),
    _Rule("R05_amount", "1", lambda group: True, _amount),
    _Rule("R06_order_id_sku", "1", lambda group: True, _match),
)


def rule_set_version() -> str:
    """Hash all registered rule ids and versions in stable order."""
    payload = "\n".join(f"{rule.id}@{rule.version}" for rule in sorted(RULES, key=lambda r: r.id))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
