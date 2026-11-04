"""Argon2 密码哈希。原文密码永不落库。"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_HASHER = PasswordHasher()


def hash_password(plain: str) -> str:
    """使用 Argon2id 哈希密码。"""
    if not isinstance(plain, str):
        raise TypeError("密码必须是字符串")
    return _HASHER.hash(plain)


def verify_password(password_hash: str, plain: str) -> bool:
    """验证密码; 错误哈希也按验证失败处理。"""
    try:
        return _HASHER.verify(password_hash, plain)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """判断是否需要按当前 Argon2 参数重新哈希。"""
    try:
        return _HASHER.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True
