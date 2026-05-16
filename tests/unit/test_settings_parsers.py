import pytest

from backend.config import settings as settings_module


@pytest.mark.unit
def test_get_bool_parses_true_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STAGE0_BOOL_FLAG", "true")
    assert settings_module._get_bool("STAGE0_BOOL_FLAG", False) is True


@pytest.mark.unit
def test_get_int_falls_back_to_default_for_invalid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STAGE0_INT_FLAG", "not-an-int")
    assert settings_module._get_int("STAGE0_INT_FLAG", 42) == 42
