"""按表头名读 csv / xlsx。未知列留在 payload。不解析金额。"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from python_calamine import CalamineSheet, CalamineWorkbook, WorksheetNotFound

from crosserp.connectors.generic_mapped.mapping import MappingError, MappingSpec


@dataclass(frozen=True)
class Table:
    """一张表。行号是文件里的 1 起行号。"""

    headers: list[str]
    rows: list[tuple[int, dict[str, str]]]


def read_table(path: Path, spec: MappingSpec) -> Table:
    """读 csv 或 xlsx。其他扩展名整批失败。"""
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        grid = _read_csv(path, spec.encoding)
    elif suffix == ".xlsx":
        grid = _read_xlsx(path, spec.sheet)
    else:
        raise MappingError(f"只支持 .csv 和 .xlsx。当前是 {path.name}。")
    return _cut(grid, spec, path.name)


def _read_csv(path: Path, encoding: str) -> list[list[str]]:
    try:
        text = path.read_text(encoding=encoding)
    except UnicodeError as exc:
        raise MappingError(
            f"文件无法按 {encoding} 解码。领星/赛狐导出编码未核实。"
            f"若是 GB18030。请把 YAML 的 encoding 改成 gb18030。{exc}"
        ) from exc
    except OSError as exc:
        raise MappingError(f"无法读取文件 {path.name}。{exc}") from exc
    reader = csv.reader(io.StringIO(text, newline=""))
    return [list(row) for row in reader]


def _read_xlsx(path: Path, sheet: int | str | None) -> list[list[str]]:
    try:
        workbook = CalamineWorkbook.from_path(str(path))
    except OSError as exc:
        raise MappingError(f"无法读取文件 {path.name}。{exc}") from exc
    except Exception as exc:
        raise MappingError(f"无法读取 Excel {path.name}。{exc}") from exc
    try:
        names = list(workbook.sheet_names)
        if not names:
            raise MappingError(f"{path.name} 没有工作表。")
        try:
            chosen = _select_sheet(workbook, sheet, names)
        except WorksheetNotFound as exc:
            shown = "、".join(names)
            raise MappingError(f"找不到工作表 {sheet}。文件里的工作表是 {shown}。") from exc
        except IndexError as exc:
            shown = "、".join(names)
            raise MappingError(f"工作表序号 {sheet} 超出范围。文件里的工作表是 {shown}。") from exc
        # 保留空行。这样 header_row 对得上 Excel 行号。
        raw_rows = chosen.to_python(skip_empty_area=False)
    finally:
        workbook.close()
    grid: list[list[str]] = []
    for raw in raw_rows:
        if not isinstance(raw, list | tuple):
            raise MappingError(f"{path.name} 的工作表行不是列表。")
        grid.append([_cell_text(cell) for cell in raw])
    return grid


def _select_sheet(
    workbook: CalamineWorkbook, sheet: int | str | None, names: list[str]
) -> CalamineSheet:
    if sheet is None or sheet == 0 or sheet == "0":
        return workbook.get_sheet_by_index(0)
    if isinstance(sheet, int):
        return workbook.get_sheet_by_index(sheet)
    if sheet.isdigit() and sheet not in names:
        return workbook.get_sheet_by_index(int(sheet))
    return workbook.get_sheet_by_name(sheet)


def _cell_text(value: object) -> str:
    """单元格转文本。float 不能当金额来源。"""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, float):
        raise MappingError(
            "Excel 单元格是数值而不是文本。金额不能从 float 读取。请把该列设成文本。"
        )
    raise MappingError(f"无法把单元格转成文本。类型 {type(value).__name__}。")


def _cut(grid: list[list[str]], spec: MappingSpec, file_name: str) -> Table:
    header_index = spec.header_row - 1
    if header_index < 0 or header_index >= len(grid):
        raise MappingError(
            f"{file_name} 没有第 {spec.header_row} 行表头。文件只有 {len(grid)} 行。"
        )
    headers = _headers(grid[header_index], file_name)
    data_start = header_index + 1 + spec.skip_rows
    if spec.skip_rows and data_start > len(grid):
        raise MappingError(
            f"{file_name} 在表头后还要跳过 {spec.skip_rows} 行。但文件没有那么多行。"
        )
    rows: list[tuple[int, dict[str, str]]] = []
    for index, raw in enumerate(grid[data_start:], start=data_start + 1):
        if _blank(raw):
            continue
        if len(raw) > len(headers):
            raise MappingError(
                f"第 {index} 行有 {len(raw)} 列。表头只有 {len(headers)} 列。"
                "多出来的单元格没有表头名。不能丢也不能猜。"
            )
        padded = raw + [""] * (len(headers) - len(raw))
        rows.append((index, dict(zip(headers, padded, strict=True))))
    return Table(headers=headers, rows=rows)


def _headers(raw: list[str], file_name: str) -> list[str]:
    headers = [cell.strip() for cell in raw]
    while headers and headers[-1] == "":
        headers.pop()
    if not headers or any(header == "" for header in headers):
        raise MappingError(f"{file_name} 的表头有空列名。不能按位置猜测。")
    seen: set[str] = set()
    duplicated: list[str] = []
    for header in headers:
        if header in seen and header not in duplicated:
            duplicated.append(header)
        seen.add(header)
    if duplicated:
        names = "、".join(duplicated)
        raise MappingError(f"{file_name} 的表头重复。{names}。不能猜测该用哪一列。")
    return headers


def _blank(raw: list[str]) -> bool:
    return all(cell.strip() == "" for cell in raw)
