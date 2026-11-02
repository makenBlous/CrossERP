"""连接器协议。具体平台解析不在这里。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from crosserp.core.models import (
    CanonicalRecord,
    ColumnMapping,
    Credentials,
    RawRow,
    SyncWindow,
)

SourceKind = Literal["settlement", "payout", "orders", "costs", "fees", "ads"]


@runtime_checkable
class FileConnector(Protocol):
    """文件导入器。read 保留原始行号。normalize 是纯函数。"""

    id: str
    kind: SourceKind
    version: str

    def sniff(self, path: Path) -> float:
        """返回 0 到 1 的识别分。"""

    def read(self, path: Path, mapping: ColumnMapping | None = None) -> Iterator[RawRow]:
        """按表头名读行。未知列留在 payload。文本只当数据。"""

    def normalize(self, row: RawRow) -> list[CanonicalRecord]:
        """把一行变成标准记录。不要写数据库。"""


@runtime_checkable
class ApiConnector(Protocol):
    """只读拉取。v0.1 不实现。"""

    id: str
    kind: SourceKind

    def pull(self, window: SyncWindow, creds: Credentials) -> Iterator[RawRow]:
        """按时间窗只读拉取。不要把凭证写入日志。"""


class VoucherBatch:
    """v0.5 凭证批次。此处只占位。"""


class Artifact:
    """v0.5 生成文件。此处只占位。"""


class ApprovalToken:
    """v0.5 审批令牌。此处只占位。"""


class PushResult:
    """v0.5 推送结果。此处只占位。"""


class LedgerTarget(Protocol):
    """v0.5 由 ledger.write_service 使用。本任务不实现。"""

    id: str

    def render(self, batch: VoucherBatch) -> Artifact:
        """生成文件。不产生外部副作用。"""

    def push(self, batch: VoucherBatch, approval: ApprovalToken) -> PushResult:
        """外部副作用。只能由写账服务调用。"""
