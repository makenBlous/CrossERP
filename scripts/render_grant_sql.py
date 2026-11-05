"""用容器环境变量渲染未提交的授权脚本模板。"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: render_grant_sql.py <grant_pg.sql|grant_mysql.sql>", file=sys.stderr)
        return 2
    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    values = {
        "__OWNER_PASSWORD__": os.environ["CROSSERP_OWNER_PASSWORD"],
        "__APP_PASSWORD__": os.environ["CROSSERP_APP_PASSWORD"],
        "__AGENT_PASSWORD__": os.environ["CROSSERP_AGENT_PASSWORD"],
    }
    for placeholder, value in values.items():
        source = source.replace(placeholder, value)
    sys.stdout.write(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
