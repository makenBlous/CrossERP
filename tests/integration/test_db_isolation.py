from __future__ import annotations

import os
from pathlib import Path


def test_default_test_database_url_does_not_point_to_home() -> None:
    home_database = str(Path.home() / ".crosserp")
    assert home_database not in os.environ["CROSSERP_DATABASE_URL"]
    assert home_database not in os.environ["CROSSERP_MIGRATE_DATABASE_URL"]
