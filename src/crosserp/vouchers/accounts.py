"""读取和校验会计科目映射。科目编码由使用方填写, 仓库不编造真实编码。"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml  # type: ignore[import-untyped]

_REQUIRED_KEYS = frozenset(
    {
        "sales_revenue",
        "platform_fee",
        "ad_cost",
        "fx_diff",
        "platform_receivable",
    }
)


@dataclass(frozen=True)
class AccountMapping:
    key: str
    code: str
    name: str
    direction: str


@dataclass(frozen=True)
class AccountsConfig:
    accounts: dict[str, AccountMapping]
    content_hash: str

    def require(self, key: str) -> AccountMapping:
        try:
            return self.accounts[key]
        except KeyError as exc:
            raise ValueError(f"科目映射缺少 {key}") from exc


def default_accounts_path() -> Path:
    configured = os.environ.get("CROSSERP_ACCOUNTS_FILE", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".crosserp" / "accounts.yaml"


def load_accounts(path: Path | None = None) -> AccountsConfig:
    selected = path or default_accounts_path()
    if not selected.is_file():
        raise FileNotFoundError(
            f"找不到科目映射文件 {selected}。请复制 config/accounts.example.yaml 后填写。"
        )
    raw_bytes = selected.read_bytes()
    try:
        raw = yaml.safe_load(raw_bytes) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"科目映射 YAML 无法解析: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("accounts"), dict):
        raise ValueError("科目映射必须包含 accounts 对象")
    accounts: dict[str, AccountMapping] = {}
    for key, value in raw["accounts"].items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise ValueError("科目映射的 key 和配置必须是文本/对象")
        code = value.get("code")
        name = value.get("name")
        direction = value.get("direction")
        if not all(isinstance(item, str) and item.strip() for item in (code, name, direction)):
            raise ValueError(f"科目 {key} 的 code/name/direction 必填")
        code = cast(str, code)
        name = cast(str, name)
        direction = cast(str, direction)
        if code.startswith(("待填", "待会计核实")):
            raise ValueError(f"科目 {key} 的编码仍是待会计核实占位, 请填写实际科目表编码")
        if direction not in {"debit", "credit", "either"}:
            raise ValueError(f"科目 {key} 的 direction 必须是 debit/credit/either")
        accounts[key] = AccountMapping(key, code, name, direction)
    missing = sorted(_REQUIRED_KEYS - accounts.keys())
    if missing:
        raise ValueError(f"科目映射缺少: {', '.join(missing)}")
    return AccountsConfig(
        accounts=accounts,
        content_hash=hashlib.sha256(raw_bytes).hexdigest(),
    )
