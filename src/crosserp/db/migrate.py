"""程序化 Alembic。打包后不依赖当前工作目录。"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url


def ensure_database_directory(url_text: str) -> None:
    """SQLite 文件的父目录不存在时创建。其他数据库不建目录。"""
    sa_url = make_url(url_text)
    if sa_url.get_backend_name() != "sqlite":
        return
    database = sa_url.database
    if not database or database == ":memory:":
        return
    Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def make_alembic_config(url: str) -> Config:
    """指向包内迁移目录。并让 env.py 使用传入的连接串。"""
    package_dir = Path(__file__).resolve().parent
    cfg = Config(str(package_dir / "alembic.ini"))
    cfg.set_main_option("script_location", (package_dir / "migrations").as_posix())
    # ConfigParser 把 % 当插值。属性里保留原串给 env.py。
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    cfg.attributes["connection_url"] = url
    return cfg


def upgrade_head(url: str) -> None:
    """升级到最新迁移。重复执行无副作用。"""
    command.upgrade(make_alembic_config(url), "head")


def downgrade_base(url: str) -> None:
    """回退到空库。alembic_version 表可能还在。"""
    command.downgrade(make_alembic_config(url), "base")


def check_schema(url: str) -> None:
    """模型与当前库没有差异时通过。有差异则抛错。"""
    command.check(make_alembic_config(url))
