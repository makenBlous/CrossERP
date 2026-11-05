from decimal import Decimal
from uuid import uuid4

from crosserp.db.schema import LlmCall
from crosserp.observability.stats import summarize


def test_stats_counts_and_percentiles() -> None:
    rows = [
        LlmCall(
            id=uuid4(),
            ts=None,
            user_id=None,
            username=None,
            channel="cli",
            model="m",
            prompt_version_id=uuid4(),
            input_tokens=1,
            output_tokens=2,
            latency_ms=value,
            cost_estimate=Decimal("0.1000"),
            currency="USD",
            status="ok",
            refusal_reason=None,
            question_text=None,
            answer_text=None,
            trace_id="x",
            request_id=None,
        )
        for value in (10, 20, 30)
    ]
    stats = summarize(rows)
    assert stats["calls"] == 3 and stats["cost"] == Decimal("0.3000") and stats["p50_ms"] == 20
