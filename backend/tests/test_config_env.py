"""Portable dotenv loading and secret representation regression tests."""
from app.core.config import BACKEND_DIR, ENV_FILES, Settings


def test_default_env_locations_are_absolute():
    assert ENV_FILES == (BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env")
    assert all(path.is_absolute() for path in ENV_FILES)


def test_training_pending_exits_before_loading_model(monkeypatch):
    import sys
    import pytest
    from app.core.config import settings
    from app.workers.vision import main
    monkeypatch.setattr(settings, "CV_MODEL_PATH", "")
    monkeypatch.setattr(sys, "argv", ["vision", "--camera-id", "not-used"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_dotenv_precedence_and_secret_masking(tmp_path, monkeypatch):
    root_env = tmp_path / "root.env"
    backend_env = tmp_path / "backend.env"
    root_env.write_text("API_PORT=8101\nOPENAI_API_KEY=local-test-key\n", encoding="utf-8")
    backend_env.write_text("API_PORT=8102\n", encoding="utf-8")
    monkeypatch.delenv("API_PORT", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = Settings(_env_file=(root_env, backend_env))
    assert config.API_PORT == 8102
    assert config.OPENAI_API_KEY.get_secret_value() == "local-test-key"
    assert "local-test-key" not in repr(config)
    monkeypatch.setenv("API_PORT", "8103")
    assert Settings(_env_file=(root_env, backend_env)).API_PORT == 8103
