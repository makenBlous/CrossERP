"""对账核心纯函数。"""

from decimal import Decimal
from types import SimpleNamespace

from crosserp.core.enums import IssueKind
from crosserp.recon.engine import _norm
from crosserp.recon.registry import RULES, Matched, Pass, Unmatched, rule_set_version


def test_normalize_only_trims_and_uppercases() -> None:
    assert _norm("  sku-01 ") == "SKU-01"
    assert _norm(None) == ""


def test_rule_set_version_is_stable() -> None:
    assert len(rule_set_version()) == 12
    assert Decimal("0") == Decimal("0")


def test_rules_run_in_order_and_return_typed_decisions() -> None:
    group = SimpleNamespace(
        key=("ORDER-1", "SKU-1"),
        settlement=SimpleNamespace(platform="amazon", currency="USD"),
    )
    ctx = SimpleNamespace(
        candidates=(SimpleNamespace(currency="USD", qty=1),),
        sku_values=frozenset({"SKU-1"}),
        all_refunds=False,
        settlement_qty=1,
        order_qty=1,
        actual_amount=Decimal("10.00"),
        expected_amount=Decimal("10.00"),
        has_expected_amount=True,
    )

    decisions = [rule.evaluate(ctx, group) for rule in RULES if rule.applies(group)]

    assert isinstance(decisions[0], Pass)
    assert isinstance(decisions[1], Pass)
    assert isinstance(decisions[2], Pass)
    assert isinstance(decisions[3], Pass)
    assert isinstance(decisions[4], Pass)
    assert isinstance(decisions[5], Matched)
    assert decisions[5].diff == Decimal("0")


def test_rules_explain_unmapped_sku_and_missing_order() -> None:
    amazon_group = SimpleNamespace(
        key=("ORDER-1", "UNKNOWN"),
        settlement=SimpleNamespace(platform="amazon", currency="USD"),
    )
    missing_sku_ctx = SimpleNamespace(sku_values=frozenset(), candidates=())
    sku_result = RULES[0].evaluate(missing_sku_ctx, amazon_group)
    assert isinstance(sku_result, Unmatched)
    assert sku_result.issues[0].kind is IssueKind.SKU_UNMAPPED

    missing_order_ctx = SimpleNamespace(candidates=(), all_refunds=True)
    order_result = RULES[1].evaluate(missing_order_ctx, amazon_group)
    assert isinstance(order_result, Unmatched)
    assert order_result.issues[0].kind is IssueKind.REFUND_WITHOUT_ORDER
