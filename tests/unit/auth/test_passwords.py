"""密码哈希单元测试。"""

from crosserp.auth.passwords import hash_password, needs_rehash, verify_password


def test_password_hash_is_not_plaintext_and_verifies() -> None:
    password = "A sufficiently long password"
    hashed = hash_password(password)
    assert hashed.startswith("$argon2id$")
    assert hashed != password
    assert verify_password(hashed, password)
    assert not verify_password(hashed, "a different password")
    assert not needs_rehash(hashed)


def test_same_password_uses_a_new_salt() -> None:
    assert hash_password("A sufficiently long password") != hash_password(
        "A sufficiently long password"
    )
