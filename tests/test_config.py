from app.config import get_settings


def test_default_database_url_is_sqlite_posix_path(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()

    try:
        settings = get_settings()
        assert settings.database_url.startswith("sqlite:///")
        assert "\\" not in settings.database_url
        assert settings.database_url.endswith("/data/eto_zhe_helper.db")
    finally:
        get_settings.cache_clear()
