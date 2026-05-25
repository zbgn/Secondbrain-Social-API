from app.config import Settings


def test_settings_loads_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "SECRET_KEY=env-file-secret-with-at-least-32-bytes",
                "DATABASE_URL=postgresql+psycopg://user:pass@db:5432/app",
            ]
        )
    )
    monkeypatch.chdir(tmp_path)

    settings = Settings()

    assert settings.secret_key == "env-file-secret-with-at-least-32-bytes"
    assert settings.database_url == "postgresql+psycopg://user:pass@db:5432/app"
