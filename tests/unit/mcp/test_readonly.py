from crosserp.agent import tools
from crosserp.mcp_server.server import registered_tools


def test_mcp_tools_are_readonly_agent_tools() -> None:
    registered = registered_tools()
    assert set(registered) == {
        "get_profit",
        "list_issues",
        "get_order",
        "get_settlement",
        "get_recon_summary",
        "get_approval_status",
        "get_voucher",
        "compare_profit",
        "search_rules_doc",
    }
    assert all(
        getattr(function, "__module__", "").startswith(tools.__name__)
        for function in registered.values()
    )
