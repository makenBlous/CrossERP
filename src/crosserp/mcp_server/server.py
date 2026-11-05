"""MCP 工具白名单注册。HTTP 传输由部署层按配置开启。"""

from crosserp.agent import tools

READONLY_TOOLS = {
    name: getattr(tools, name)
    for name in (
        "get_profit",
        "list_issues",
        "get_order",
        "get_settlement",
        "get_recon_summary",
        "get_approval_status",
        "get_voucher",
        "compare_profit",
        "search_rules_doc",
    )
}


def registered_tools() -> dict[str, object]:
    return dict(READONLY_TOOLS)


def create_server() -> object:
    """返回官方 MCP Server; 工具均来自只读白名单。"""
    from mcp.server.fastmcp import FastMCP  # type: ignore[attr-defined]

    server = FastMCP("CrossERP")
    for name, function in READONLY_TOOLS.items():
        server.tool(name=name, description="CrossERP 只读查询工具")(function)
    return server
