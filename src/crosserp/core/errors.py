"""领域错误。"""

from __future__ import annotations


class CrossErpError(Exception):
    """CrossERP 业务错误基类。"""


class CurrencyMismatchError(CrossErpError):
    """不同币种不能直接加减。"""

    def __init__(self, left: str, right: str) -> None:
        self.left = left
        self.right = right
        super().__init__(f"币种不一致。{left} 与 {right} 不能直接加减")


class AmountParseError(CrossErpError):
    """金额字符串无法解析。`text` 是调用方传入的原文。"""

    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__(f"无法解析金额 {text!r}")


class PrecisionError(CrossErpError):
    """小数位数或数值范围超出允许精度。T04 的 Money4 / FxRate 使用。"""


class DatabaseConfigError(CrossErpError):
    """数据库配置不满足启动要求。消息用中文说明怎么改。"""


class UnknownFileTypeError(CrossErpError):
    """自动识别失败。提示用 --type 指定连接器。"""

    def __init__(self, path: str, detail: str) -> None:
        self.path = path
        self.detail = detail
        super().__init__(f"无法识别文件 {path}。{detail}请用 --type 指定连接器。")


class DuplicateImportError(CrossErpError):
    """同一 sha256 已经有导入批次。"""

    def __init__(self, file_sha256: str, imported_at: str, status: str) -> None:
        self.file_sha256 = file_sha256
        self.imported_at = imported_at
        self.status = status
        super().__init__(f"文件已成功导入过。首次成功时间 {imported_at}。sha256 {file_sha256}")


class FileUnreadableError(CrossErpError):
    """计算 sha256 之前无法打开文件。此时不写批次。"""


class RowParseError(CrossErpError):
    """单行解析失败。导入器写入 PARSE_ERROR 后继续下一行。"""

    def __init__(
        self,
        row_no: int,
        message: str,
        raw: dict[str, str] | str | None = None,
    ) -> None:
        self.row_no = row_no
        self.raw = raw
        super().__init__(message)
