"""合并前检查：拦截放宽的安全断言、防御性写法和自写共用逻辑。

用法：
    uv run python scripts/check_merge_guard.py --base <rev> [--head <rev>] [--waivers <文件>]
    uv run python scripts/check_merge_guard.py --list-rules

--base 必填。--head 省略时检查 ``git merge-base <base> HEAD`` 到工作区（含未提交改动）
的 ``git diff -U0``。给了 --head 就检查 ``<base>...<head>``。范围内每个提交再额外检查
G1/G2，避免「先写入严格断言、再在同一范围内放宽」被净 diff 抵消。git 失败直接抛出。

指纹 = 规则 ID + 文件路径 + 去空白后的行内容的 sha1 前 12 位，不含行号。
有未豁免命中退出 1；无命中退出 0；豁免文件格式错误退出 2。

共用模块（规则排除或对照这些路径，不在别的文件再写一套）：

- ``src/crosserp/iam/scope.py``：AllStores / resolve_store_scope / apply_store_scope
- ``src/crosserp/api/metadata.py``：api_endpoint 的幂等归属
- ``src/crosserp/api/idempotency.py``：HTTP 幂等中间件
- ``src/crosserp/platform/idempotency.py``：调用身份隔离的幂等范围与回放
- ``src/crosserp/platform/factory.py``：make_action_dispatcher
- ``src/crosserp/platform/approval.py``：ApprovalSubmission
- ``src/crosserp/platform/audit.py``：AuditRecorder
- ``src/crosserp/audit/log.py``：AuditRecorder 使用的哈希链写入

规则：

- G1 安全断言删除或放宽（tests/）。删除行含 assert / pytest.raises / status_code，
  且该行或所在测试函数涉及权限、审批、审计、幂等、撤销、风险、密钥等安全词。
  同一 diff 的新增行里已有去空白后完全相同的行时，视为纯移动，不算。同一 hunk
  内只改写法、比较符未放宽、4xx 未改成 2xx、pytest.raises 仍在，不算。另计：
  tests/ 整文件删除；断言状态码从 4xx 改成 2xx；``==`` / ``is`` 改成 ``in`` /
  ``>=`` / ``<=`` 等放宽比较。
- G2 新增 skip/xfail（tests/）。新增 pytest.mark.skip、skipif、xfail、pytest.skip(、
  pytest.importorskip(，以及把已有 timeout 数值调大。注释里的同名文字不算。
- D1 带默认值的回退（src/ 新增行）。``.get(x, <默认>)``、``getattr(x, "y", <默认>)``、
  ``or {}`` / ``or []`` / ``or ""``。``session.get(模型, 主键)`` 不是字典回退。
- D2 静默吞错（src/ 新增行）。``except ...: pass``、看不到 raise 的 ``except Exception``、
  ``contextlib.suppress``、except 块里只 return / return None / 记日志。函数中新增
  ``if ... is None: return`` / ``if not ...: return``（无返回值，含 return None）。
- D3 兼容或可选开关（src/ 新增行）。新形参 ``: X | None = None``、``hasattr(``、
  把 isinstance 用作兼容回退（else 默认值，或判断 dict/list/str）。Alembic 的
  branch_labels / depends_on 和 ``isinstance(scope, AllStores)`` 不算。
- S1 自写店铺范围（src/ 新增行，排除 iam/scope.py）。出现 store_ids /
  allowed_store / StoreScope 的集合构造、对 store 列 ``.in_(``、按角色名或
  snapshot 判断店铺，且该文件没有引用 apply_store_scope / resolve_store_scope。
- S2 自写幂等（src/ 新增行，排除幂等中间件、platform/idempotency.py 和
  api/metadata.py）。出现自建回放、IdempotencyKey(、自行读取 Idempotency-Key。
  转发给执行器、``idempotency=`` 元数据、``find_action_replay`` 不算。
- S3 自建执行器或审批壳（src/ 新增行）。直接构造 ActionDispatcher(（排除
  factory.py）、``_Approval...(dict)`` 兼容壳、绕开 AuditRecorder 直接写审计表。
"""

# 规则说明沿用项目中文口径。
# ruff: noqa: RUF001, RUF002

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCOPE_MODULE = "src/crosserp/iam/scope.py"
METADATA_MODULE = "src/crosserp/api/metadata.py"
IDEMPOTENCY_MIDDLEWARE = "src/crosserp/api/idempotency.py"
IDEMPOTENCY_MODULE = "src/crosserp/platform/idempotency.py"
FACTORY_MODULE = "src/crosserp/platform/factory.py"
APPROVAL_MODULE = "src/crosserp/platform/approval.py"
AUDIT_MODULE = "src/crosserp/platform/audit.py"
AUDIT_LOG_MODULE = "src/crosserp/audit/log.py"

S2_EXCLUDED = frozenset({IDEMPOTENCY_MIDDLEWARE, IDEMPOTENCY_MODULE, METADATA_MODULE})
S3_AUDIT_EXCLUDED = frozenset({AUDIT_MODULE, AUDIT_LOG_MODULE})
MIGRATIONS_PREFIX = "src/crosserp/db/migrations/"

RULES: tuple[tuple[str, str], ...] = (
    (
        "G1",
        "删除含安全词的 assert/pytest.raises/status_code，或把 4xx 改成 2xx、把 == 放宽",
    ),
    ("G2", "新增 skip/xfail/importorskip，或调大 timeout 数值"),
    ("D1", '新增 .get/getattr 默认值，或 or {} / or [] / or "" 兜底'),
    ("D2", "新增 except pass、except Exception 不抛、suppress，或无返回值的 is None/not 早退"),
    ("D3", "新增可选形参 : X | None = None、hasattr，或 isinstance 兼容回退"),
    ("S1", "未引用 apply_store_scope/resolve_store_scope 就自写店铺范围"),
    ("S2", "在幂等中间件和 api/metadata.py 之外自写幂等回放"),
    ("S3", "直接构造 ActionDispatcher、自定义 _Approval 壳，或绕开 AuditRecorder 写审计表"),
)

_SECURITY_WORDS = (
    "permission",
    "forbidden",
    "denied",
    "404",
    "403",
    "401",
    "data_scope",
    "scope",
    "store",
    "approval",
    "awaiting",
    "initiator",
    "approver",
    "audit",
    "hash",
    "chain",
    "idempot",
    "idempotency-key",
    "replay",
    "undo",
    "revert",
    "risk",
    "critical",
    "high",
    "medium",
    "secret",
    "token",
    "logout",
)
_ASSERT_TOKEN = re.compile(r"\bassert\b|pytest\.raises\b|\bstatus_code\b")
_STATUS_CODE = re.compile(r"\b([1-5]\d{2})\b")
_GET_DEFAULT = re.compile(r"\.get\(\s*([^,)]+)\s*,\s*([^)]+)\)")
_GETATTR_DEFAULT = re.compile(r"\bgetattr\(\s*[^,]+,\s*[^,]+,\s*[^)]+\)")
_OR_EMPTY = re.compile(r"""\bor\s+(\{\}|\[\]|""|'')""")
_EXCEPT_PASS = re.compile(r"\bexcept\b[^:]*:\s*pass\s*(?:#.*)?$")
_EXCEPT_EXCEPTION = re.compile(r"\bexcept\s+Exception\b[^:]*:")
_EXCEPT_ANY = re.compile(r"\bexcept\b[^:]*:")
_SUPPRESS = re.compile(r"\bsuppress\s*\(")
_IF_NONE_RETURN = re.compile(r"\bif\s+.+\bis\s+None\b.*:\s*return(?:\s+None)?\s*(?:#.*)?$")
_IF_NOT_RETURN = re.compile(r"\bif\s+not\s+.+:\s*return(?:\s+None)?\s*(?:#.*)?$")
_IF_NONE = re.compile(r"\bif\s+.+\bis\s+None\b.*:\s*(?:#.*)?$")
_IF_NOT = re.compile(r"\bif\s+not\s+.+:\s*(?:#.*)?$")
_BARE_RETURN = re.compile(r"return(?:\s+None)?\s*(?:#.*)?$")
_OPTIONAL_NONE = re.compile(r":\s*[^=\n]+\|\s*None\s*=\s*None\b")
_HASATTR = re.compile(r"\bhasattr\s*\(")
_ISINSTANCE_FALLBACK = re.compile(
    r"\bisinstance\s*\([^)\n]*\)\s*else\s+|\bif\s+not\s+isinstance\s*\(|"
    r"\bisinstance\s*\(\s*[^,]+,\s*(?:dict|list|str|bytes|tuple)\b"
)
_ALL_STORES_DISPATCH = re.compile(r"\bisinstance\s*\(\s*[^,]+,\s*AllStores\b")
_S1_PATTERNS = (
    re.compile(r"\bstore_ids\b\s*=\s*(?:set|frozenset)\s*\("),
    re.compile(r"\bstore_ids\b\s*=\s*\{"),
    re.compile(r"\ballowed_store\w*\s*=\s*(?:set|frozenset)\s*\("),
    re.compile(r"\ballowed_store\w*\s*=\s*\{"),
    re.compile(r"\bStoreScope\s*\("),
    re.compile(r"\b\w*store\w*\.in_\s*\(", re.IGNORECASE),
    re.compile(r"\.in_\s*\(\s*(?:store_ids|allowed_store\w*|scope)\b"),
    re.compile(r"\b(?:role|roles)\b\s*(?:==|in\b).*\bstore\b", re.IGNORECASE),
    re.compile(r"\bsnapshot\b.*\bstore_ids?\b|\bstore_ids?\b.*\bsnapshot\b"),
)
_S2_CUSTOM = (
    re.compile(r"\bIdempotencyKey\s*\("),
    re.compile(r"\bdef\s+_?replay\w*\s*\("),
    re.compile(r"\._replay\s*\("),
    re.compile(r"""headers\s*\[\s*['"]Idempotency-Key['"]\s*\]"""),
)
_S2_BENIGN = re.compile(
    r"idempotency\s*=\s*['\"](?:dispatcher|http|none)['\"]|"
    r"alias\s*=\s*['\"]Idempotency-Key['\"]|"
    r"idempotency_key\s*=|"
    r"\bfind_action_replay\s*\("
)
_G2_PATTERNS = (
    re.compile(r"pytest\.mark\.skip\b"),
    re.compile(r"\bskipif\b"),
    re.compile(r"\bxfail\b"),
    re.compile(r"pytest\.skip\s*\("),
    re.compile(r"pytest\.importorskip\s*\("),
)
_TIMEOUT = re.compile(r"timeout(?:\s*=\s*|\s*\()\s*(\d+)", re.IGNORECASE)
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]+")
_LOG_CALL = re.compile(
    r"\b(?:log|logger|logging)\b.*\(|\.(?:debug|info|warning|error|exception|critical)\s*\("
)
_RAISE = re.compile(r"\braise\b")


@dataclass(frozen=True)
class DiffLine:
    number: int
    text: str
    function: str
    hunk: int


@dataclass
class FileDiff:
    path: str
    added: list[DiffLine]
    removed: list[DiffLine]
    deleted: bool = False


@dataclass(frozen=True)
class Hit:
    rule_id: str
    path: str
    line: int
    text: str
    fingerprint: str


def fingerprint(rule_id: str, path: str, text: str) -> str:
    """规则、路径和去空白行内容的 sha1 前 12 位。"""
    stripped = "".join(text.split())
    raw = f"{rule_id}{path}{stripped}".encode()
    return hashlib.sha1(raw).hexdigest()[:12]


def _utf8_stdio() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def _git(args: list[str], *, allow_diff: bool = False) -> str:
    env = os.environ.copy()
    env["GIT_PAGER"] = "cat"
    env["GIT_TERMINAL_PROMPT"] = "0"
    completed = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        stdin=subprocess.DEVNULL,
    )
    if completed.returncode != 0 and not (allow_diff and completed.returncode == 1):
        raise subprocess.CalledProcessError(
            completed.returncode, ["git", *args], completed.stdout, completed.stderr
        )
    return completed.stdout


def _has_security(text: str) -> bool:
    folded = text.casefold()
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", folded)
        for word in _SECURITY_WORDS
    )


def _is_comment(text: str) -> bool:
    return text.lstrip().startswith("#")


def _indent(text: str) -> int:
    return len(text) - len(text.lstrip(" "))


def _summary(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) <= 80:
        return compact
    return compact[:77] + "..."


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in _IDENT.findall(text)}


def _overlap(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    if not left_tokens:
        return 0.0
    return len(left_tokens & _tokens(right)) / len(left_tokens)


def _status_codes(text: str) -> list[int]:
    return [int(match) for match in _STATUS_CODE.findall(text)]


def _weakened(removed: str, added: str) -> bool:
    if _overlap(removed, added) < 0.45:
        return False
    removed_codes = _status_codes(removed)
    added_codes = _status_codes(added)
    if any(400 <= code <= 499 for code in removed_codes) and any(
        200 <= code <= 299 for code in added_codes
    ):
        return True
    removed_ops = _operators(removed)
    added_ops = _operators(added)
    strict = {"==", "is"}
    loose = {"in", ">=", "<=", ">", "<", "!="}
    if removed_ops & strict and added_ops & loose and not (added_ops & strict):
        return True
    return "is None" in removed and "is None" not in added and "is not None" not in added


def _operators(text: str) -> set[str]:
    padded = f" {text} "
    found: set[str] = set()
    for operator in ("==", "!=", ">=", "<=", " is not ", " is ", " not in ", " in ", ">", "<"):
        if operator in padded:
            found.add(operator.strip())
    return found


def _join_logical(lines: list[DiffLine]) -> list[tuple[DiffLine, str]]:
    """把同一 hunk 里括号未闭合的连续删除/新增行合成一条逻辑行。"""
    grouped: list[tuple[DiffLine, str]] = []
    index = 0
    while index < len(lines):
        first = lines[index]
        parts = [first.text]
        balance = first.text.count("(") - first.text.count(")")
        cursor = index
        while balance > 0 and cursor + 1 < len(lines):
            nxt = lines[cursor + 1]
            if nxt.hunk != first.hunk or nxt.number != lines[cursor].number + 1:
                break
            parts.append(nxt.text)
            balance += nxt.text.count("(") - nxt.text.count(")")
            cursor += 1
        grouped.append((first, " ".join(part.strip() for part in parts)))
        index = cursor + 1
    return grouped


def _parse_diff(text: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    current: FileDiff | None = None
    old_line = 0
    new_line = 0
    function = ""
    hunk = -1
    for raw in text.splitlines():
        if raw.startswith("diff --git "):
            current = FileDiff(path="", added=[], removed=[])
            files.append(current)
            hunk = -1
            continue
        if current is None:
            continue
        if raw.startswith("deleted file mode"):
            current.deleted = True
            continue
        if raw.startswith("--- a/"):
            current.path = current.path or raw[6:]
            continue
        if raw.startswith("+++ b/"):
            current.path = raw[6:]
            continue
        if raw.startswith("@@"):
            match = _HUNK.match(raw)
            if match is None:
                raise ValueError(f"无法解析 diff hunk: {raw}")
            old_line = int(match.group(1))
            new_line = int(match.group(3))
            function = match.group(5).strip()
            hunk += 1
            continue
        if raw.startswith("+"):
            current.added.append(DiffLine(new_line, raw[1:], function, hunk))
            new_line += 1
            continue
        if raw.startswith("-"):
            current.removed.append(DiffLine(old_line, raw[1:], function, hunk))
            old_line += 1
            continue
        if raw.startswith("\\"):
            continue
    return [item for item in files if item.path]


def _g1_candidate(text: str, function: str) -> bool:
    if not _ASSERT_TOKEN.search(text):
        return False
    if _has_security(text):
        return True
    if not _has_security(function):
        return False
    return bool(
        "pytest.raises" in text
        or re.search(r"\bstatus_code\b", text)
        or re.search(r"\bErrorCode\b", text)
        or re.search(r"\b40[13]\b|\b404\b", text)
    )


def _is_rewrite(removed: str, added: list[str]) -> bool:
    assertions = [line for line in added if _ASSERT_TOKEN.search(line)]
    for line in assertions:
        if _weakened(removed, line):
            continue
        if "pytest.raises" in removed and "pytest.raises" not in line:
            continue
        if _overlap(removed, line) >= 0.6:
            return True
    return False


def _hits_g1(file_diff: FileDiff, moved: set[str]) -> list[Hit]:
    if not file_diff.path.startswith("tests/"):
        return []
    hits: list[Hit] = []
    if file_diff.deleted:
        hits.append(_hit("G1", file_diff.path, 1, "整文件删除"))
    added_by_hunk: dict[int, list[str]] = {}
    for line in file_diff.added:
        added_by_hunk.setdefault(line.hunk, []).append(line.text)
    for origin, text in _join_logical(file_diff.removed):
        if _is_comment(text):
            continue
        stripped = "".join(text.split())
        if stripped in moved:
            continue
        added = added_by_hunk.get(origin.hunk, [])
        security_deletion = _g1_candidate(text, origin.function) and not _is_rewrite(text, added)
        weakened = any(_ASSERT_TOKEN.search(line) and _weakened(text, line) for line in added)
        if security_deletion or weakened:
            hits.append(_hit("G1", file_diff.path, origin.number, text))
    return hits


def _hits_g2(file_diff: FileDiff) -> list[Hit]:
    if not file_diff.path.startswith("tests/"):
        return []
    hits: list[Hit] = []
    removed_timeouts: dict[int, list[int]] = {}
    for line in file_diff.removed:
        numbers = [int(match) for match in _TIMEOUT.findall(line.text)]
        if numbers:
            removed_timeouts.setdefault(line.hunk, []).extend(numbers)
    for line in file_diff.added:
        if _is_comment(line.text):
            continue
        if any(pattern.search(line.text) for pattern in _G2_PATTERNS):
            hits.append(_hit("G2", file_diff.path, line.number, line.text))
        added_timeouts = [int(match) for match in _TIMEOUT.findall(line.text)]
        previous = removed_timeouts.get(line.hunk, [])
        if added_timeouts and previous and max(added_timeouts) > max(previous):
            hits.append(_hit("G2", file_diff.path, line.number, line.text))
    return hits


def _session_get(text: str, start: int) -> bool:
    prefix = text[:start].rstrip()
    return bool(re.search(r"(?:^|[^\w])session$", prefix))


def _hits_d1(file_diff: FileDiff) -> list[Hit]:
    if not file_diff.path.startswith("src/"):
        return []
    hits: list[Hit] = []
    for line in file_diff.added:
        if _is_comment(line.text):
            continue
        matched = False
        for match in _GET_DEFAULT.finditer(line.text):
            if not _session_get(line.text, match.start()):
                matched = True
        if _GETATTR_DEFAULT.search(line.text) or _OR_EMPTY.search(line.text):
            matched = True
        if matched:
            hits.append(_hit("D1", file_diff.path, line.number, line.text))
    return hits


def _following_body(lines: list[DiffLine], index: int) -> list[DiffLine]:
    head = lines[index]
    body: list[DiffLine] = []
    expected = head.number + 1
    base_indent = _indent(head.text)
    for nxt in lines[index + 1 :]:
        if nxt.hunk != head.hunk or nxt.number != expected or _indent(nxt.text) <= base_indent:
            break
        body.append(nxt)
        expected += 1
    return body


def _swallow_body(body: list[str]) -> bool:
    statements = [line.strip() for line in body if line.strip() and not _is_comment(line)]
    if not statements:
        return False
    return all(
        item == "pass" or re.fullmatch(r"return(?:\s+None)?", item) or _LOG_CALL.search(item)
        for item in statements
    )


def _hits_d2(file_diff: FileDiff) -> list[Hit]:
    if not file_diff.path.startswith("src/"):
        return []
    hits: list[Hit] = []
    lines = file_diff.added
    for index, line in enumerate(lines):
        if _is_comment(line.text):
            continue
        text = line.text.strip()
        body = _following_body(lines, index)
        body_text = [item.text for item in body]
        if _EXCEPT_PASS.search(text) or _SUPPRESS.search(line.text):
            hits.append(_hit("D2", file_diff.path, line.number, line.text))
            continue
        if (
            _EXCEPT_EXCEPTION.search(text)
            and body
            and not any(_RAISE.search(item) for item in body_text)
        ):
            hits.append(_hit("D2", file_diff.path, line.number, line.text))
            continue
        if _EXCEPT_ANY.search(text) and body and _swallow_body(body_text):
            hits.append(_hit("D2", file_diff.path, line.number, line.text))
            continue
        if _IF_NONE_RETURN.search(text) or _IF_NOT_RETURN.search(text):
            hits.append(_hit("D2", file_diff.path, line.number, line.text))
            continue
        if (_IF_NONE.search(text) or _IF_NOT.search(text)) and body:
            next_text = body[0].text.strip()
            if _BARE_RETURN.fullmatch(next_text):
                hits.append(_hit("D2", file_diff.path, line.number, line.text))
    return hits


def _hits_d3(file_diff: FileDiff) -> list[Hit]:
    if not file_diff.path.startswith("src/"):
        return []
    hits: list[Hit] = []
    for line in file_diff.added:
        if _is_comment(line.text):
            continue
        optional = _OPTIONAL_NONE.search(line.text)
        if optional and file_diff.path.startswith(MIGRATIONS_PREFIX):
            optional = None
        isinstance_hit = _ISINSTANCE_FALLBACK.search(line.text) and not _ALL_STORES_DISPATCH.search(
            line.text
        )
        if optional or _HASATTR.search(line.text) or isinstance_hit:
            hits.append(_hit("D3", file_diff.path, line.number, line.text))
    return hits


def _file_text(path: str, rev: str | None) -> str:
    if rev is None:
        return Path(path).read_text(encoding="utf-8")
    return _git(["show", f"{rev}:{path}"])


def _hits_s1(file_diff: FileDiff, rev: str | None) -> list[Hit]:
    if not file_diff.path.startswith("src/") or file_diff.path == SCOPE_MODULE:
        return []
    matched = [
        line
        for line in file_diff.added
        if not _is_comment(line.text) and any(pattern.search(line.text) for pattern in _S1_PATTERNS)
    ]
    if not matched:
        return []
    source = _file_text(file_diff.path, rev)
    if "apply_store_scope" in source or "resolve_store_scope" in source:
        return []
    return [_hit("S1", file_diff.path, line.number, line.text) for line in matched]


def _s2_custom(text: str) -> bool:
    if _S2_BENIGN.search(text):
        return False
    if any(pattern.search(text) for pattern in _S2_CUSTOM):
        return True
    return (
        "idempotency" in text.casefold() and re.search(r"\bdef\s+\w*idempotency", text) is not None
    )


def _hits_s2(file_diff: FileDiff) -> list[Hit]:
    if not file_diff.path.startswith("src/") or file_diff.path in S2_EXCLUDED:
        return []
    return [
        _hit("S2", file_diff.path, line.number, line.text)
        for line in file_diff.added
        if not _is_comment(line.text) and _s2_custom(line.text)
    ]


def _hits_s3(file_diff: FileDiff) -> list[Hit]:
    if not file_diff.path.startswith("src/"):
        return []
    hits: list[Hit] = []
    for line in file_diff.added:
        if _is_comment(line.text):
            continue
        dispatcher = "ActionDispatcher(" in line.text and file_diff.path != FACTORY_MODULE
        approval_shell = bool(re.search(r"\b_Approval\w*\s*\(\s*(?:\{|dict\s*\()", line.text))
        audit_write = file_diff.path not in S3_AUDIT_EXCLUDED and bool(
            re.search(r"\bAuditLog\s*\(", line.text)
        )
        if dispatcher or approval_shell or audit_write:
            hits.append(_hit("S3", file_diff.path, line.number, line.text))
    return hits


def _hit(rule_id: str, path: str, line: int, text: str) -> Hit:
    return Hit(rule_id, path, line, text, fingerprint(rule_id, path, text))


def _scan(files: list[FileDiff], rev: str | None, *, tests_only: bool) -> list[Hit]:
    moved = {"".join(line.text.split()) for file_diff in files for line in file_diff.added}
    hits: list[Hit] = []
    for file_diff in files:
        hits.extend(_hits_g1(file_diff, moved))
        hits.extend(_hits_g2(file_diff))
        if tests_only:
            continue
        hits.extend(_hits_d1(file_diff))
        hits.extend(_hits_d2(file_diff))
        hits.extend(_hits_d3(file_diff))
        hits.extend(_hits_s1(file_diff, rev))
        hits.extend(_hits_s2(file_diff))
        hits.extend(_hits_s3(file_diff))
    return hits


def _untracked_diffs() -> list[FileDiff]:
    names = [line for line in _git(["ls-files", "-o", "--exclude-standard"]).splitlines() if line]
    files: list[FileDiff] = []
    for name in names:
        files.extend(
            _parse_diff(
                _git(["diff", "--no-index", "-U0", "--", "/dev/null", name], allow_diff=True)
            )
        )
    return files


def _collect(base: str, head: str | None) -> list[Hit]:
    if head is None:
        merge_base = _git(["merge-base", base, "HEAD"]).strip()
        net = _parse_diff(_git(["diff", "-U0", merge_base]))
        net.extend(_untracked_diffs())
        end = "HEAD"
    else:
        merge_base = _git(["merge-base", base, head]).strip()
        net = _parse_diff(_git(["diff", "-U0", f"{base}...{head}"]))
        end = head
    hits = _scan(net, head, tests_only=False)
    commits = [
        line
        for line in _git(["rev-list", "--reverse", f"{merge_base}..{end}"]).splitlines()
        if line
    ]
    for commit in commits:
        parent = _git(["rev-parse", f"{commit}~1"]).strip()
        commit_diff = _parse_diff(_git(["diff", "-U0", parent, commit]))
        hits.extend(_scan(commit_diff, commit, tests_only=True))
    unique: dict[str, Hit] = {}
    for hit in hits:
        unique.setdefault(hit.fingerprint, hit)
    return sorted(
        unique.values(), key=lambda item: (item.rule_id, item.path, item.line, item.fingerprint)
    )


def _load_waivers(path: str) -> dict[str, str]:
    waivers: dict[str, str] = {}
    for line_number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        if "\t" not in raw:
            print(f"豁免文件第 {line_number} 行缺少制表符: {raw}", file=sys.stderr)
            raise SystemExit(2)
        digest, reason = raw.split("\t", 1)
        if len(reason.strip()) < 8:
            print(f"豁免文件第 {line_number} 行理由不足 8 个字符", file=sys.stderr)
            raise SystemExit(2)
        waivers[digest.strip()] = reason.strip()
    return waivers


def _print_rules() -> None:
    for rule_id, description in RULES:
        print(f"{rule_id}  {description}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="合并前检查安全断言、防御性写法和自写共用逻辑。")
    parser.add_argument("--base", help="比较基点。除 --list-rules 外必填")
    parser.add_argument("--head", help="比较终点。省略时检查 merge-base 到工作区")
    parser.add_argument("--waivers", help="豁免文件，每行 指纹<TAB>理由")
    parser.add_argument("--list-rules", action="store_true", help="打印规则 ID 与说明")
    return parser


def main(argv: list[str] | None = None) -> int:
    _utf8_stdio()
    args = _parser().parse_args(argv)
    if args.list_rules:
        _print_rules()
        return 0
    if not args.base:
        raise ValueError("缺少必填参数 --base")
    waivers = _load_waivers(args.waivers) if args.waivers else {}
    unwaived = 0
    for hit in _collect(args.base, args.head):
        reason = waivers.get(hit.fingerprint)
        summary = _summary(hit.text)
        location = f"{hit.path}:{hit.line}"
        if reason is None:
            unwaived += 1
            print(f"{hit.rule_id}  {location}  {summary}  {hit.fingerprint}")
        else:
            print(f"豁免 {hit.rule_id}  {location}  {summary}  {hit.fingerprint}  {reason}")
    return 1 if unwaived else 0


if __name__ == "__main__":
    raise SystemExit(main())
