"""文件识别。低分和并列都要求用 --type 指定。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from crosserp.connectors.base import FileConnector, SourceKind
from crosserp.connectors.registry import CONNECTOR_GROUP, detect, load_connectors
from crosserp.core.errors import UnknownFileTypeError
from crosserp.core.models import CanonicalRecord, ColumnMapping, RawRow
from tests.fixtures.fake_connector import FakeCsvConnector


class _Connector:
    def __init__(self, connector_id: str, score: float) -> None:
        self.id = connector_id
        self.kind: SourceKind = "orders"
        self.version = "0"
        self._score = score

    def sniff(self, path: Path) -> float:
        del path
        return self._score

    def read(self, path: Path, mapping: ColumnMapping | None = None) -> Iterator[RawRow]:
        del path, mapping
        return iter(())

    def normalize(self, row: RawRow) -> list[CanonicalRecord]:
        del row
        return []


def test_fake_connector_matches_protocol() -> None:
    assert isinstance(FakeCsvConnector(), FileConnector)


def test_unique_high_score_wins(tmp_path: Path) -> None:
    path = tmp_path / "a.csv"
    path.write_text("x\n", encoding="utf-8")
    found = detect(path, [_Connector("low", 0.2), _Connector("high", 0.9)])
    assert found.id == "high"


def test_score_at_threshold_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "a.csv"
    path.write_text("x\n", encoding="utf-8")
    found = detect(path, [_Connector("edge", 0.5)])
    assert found.id == "edge"


def test_low_score_asks_for_type(tmp_path: Path) -> None:
    path = tmp_path / "a.csv"
    path.write_text("x\n", encoding="utf-8")
    with pytest.raises(UnknownFileTypeError, match="--type"):
        detect(path, [_Connector("low", 0.49)])


def test_tie_asks_for_type(tmp_path: Path) -> None:
    path = tmp_path / "a.csv"
    path.write_text("x\n", encoding="utf-8")
    with pytest.raises(UnknownFileTypeError, match="--type") as caught:
        detect(path, [_Connector("left", 0.9), _Connector("right", 0.9)])
    assert "left" in str(caught.value)
    assert "right" in str(caught.value)


def test_tie_below_threshold_still_fails(tmp_path: Path) -> None:
    path = tmp_path / "a.csv"
    path.write_text("x\n", encoding="utf-8")
    with pytest.raises(UnknownFileTypeError, match="--type"):
        detect(path, [_Connector("left", 0.2), _Connector("right", 0.2)])


class _Registered:
    id = "high"
    kind: SourceKind = "orders"
    version = "0"

    def sniff(self, path: Path) -> float:
        del path
        return 0.9

    def read(self, path: Path, mapping: ColumnMapping | None = None) -> Iterator[RawRow]:
        del path, mapping
        return iter(())

    def normalize(self, row: RawRow) -> list[CanonicalRecord]:
        del row
        return []


def test_load_connectors_reads_entry_point_group(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []

    class _Entry:
        name = "high"

        def load(self) -> type[_Registered]:
            return _Registered

    def _fake_entry_points(*, group: str) -> tuple[_Entry, ...]:
        captured.append(group)
        return (_Entry(),)

    monkeypatch.setattr("crosserp.connectors.registry.entry_points", _fake_entry_points)
    found = load_connectors()
    assert captured == [CONNECTOR_GROUP]
    assert [item.id for item in found] == ["high"]


def test_load_connectors_rejects_non_connector(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Entry:
        name = "bad"

        def load(self) -> type[object]:
            return object

    monkeypatch.setattr(
        "crosserp.connectors.registry.entry_points",
        lambda *, group: (_Entry(),),
    )
    with pytest.raises(TypeError, match="FileConnector"):
        load_connectors()
