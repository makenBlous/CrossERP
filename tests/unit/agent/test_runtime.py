import pytest

from crosserp.agent.runtime import ask, prompt_version


def test_missing_model_configuration_is_chinese_error(monkeypatch) -> None:
    for key in ("CROSSERP_MODEL_BASE_URL", "CROSSERP_MODEL", "CROSSERP_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(RuntimeError, match="CROSSERP_MODEL_BASE_URL"):
        ask("测试")


def test_prompt_version_is_content_addressed() -> None:
    assert prompt_version().startswith("system_v1.md:")
