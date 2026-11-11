from scripts.export_permission_catalog import check


def test_backend_permission_catalog_matches_frontend() -> None:
    check()
