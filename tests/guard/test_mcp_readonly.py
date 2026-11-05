from crosserp.mcp_server.server import registered_tools


def test_mcp_has_no_write_tool() -> None:
    assert not set(registered_tools()) & {"export", "create", "update", "delete", "approve"}
