from crosserp.web.routes import ROUTE_PERMISSIONS


def test_business_routes_are_registered() -> None:
    assert {"/", "/imports", "/profit", "/issues", "/security-log", "/settings"} <= set(
        ROUTE_PERMISSIONS
    )
