from decimal import Decimal
from pathlib import Path

from crosserp.observability.prices import estimate_cost


def test_price_uses_decimal_and_rounds_four_places(tmp_path: Path) -> None:
    path = tmp_path / "prices.yaml"
    path.write_text(
        "models:\n  m:\n    input_per_million: '1.25'\n    output_per_million: '2.50'\n",
        encoding="utf-8",
    )
    assert estimate_cost("m", 1000, 2000, path) == Decimal("0.0063")
    assert estimate_cost("missing", 1, 1, path) is None
