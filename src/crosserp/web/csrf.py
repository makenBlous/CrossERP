"""同步令牌 CSRF 校验。"""

from __future__ import annotations

import hashlib
import re
import secrets

# token_urlsafe(24) 是 24 字节的 base64url, 去掉填充后固定 32 个字符.
_LOGIN_CSRF_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32}$")


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def valid_pair(cookie: str | None, submitted: str | None) -> bool:
    if not cookie or not submitted:
        return False
    return secrets.compare_digest(token_hash(cookie), token_hash(submitted))


def login_form_token(existing: str | None) -> tuple[str, bool]:
    """返回登录表单要嵌入的令牌, 以及是否写入新 cookie.

    浏览器提交的是 HTML 里的值, 不是服务端刚生成且尚未进入本次请求的 cookie.
    已有合法令牌就复用, 刷新和多个标签页才能对上同一个 cookie.
    缺失或格式不对时签发新令牌. 调用方必须把同一个值写入 cookie 和表单.
    """
    if existing and _LOGIN_CSRF_PATTERN.fullmatch(existing):
        return existing, False
    return secrets.token_urlsafe(24), True
