from app.config import Settings


def test_cors_allowed_origins_list_defaults_to_single_origin():
    settings = Settings(cors_allowed_origins="http://localhost:5173")
    assert settings.cors_allowed_origins_list == ["http://localhost:5173"]


def test_cors_allowed_origins_list_splits_and_trims_multiple_origins():
    settings = Settings(cors_allowed_origins="http://localhost:5173, https://example.com ,http://a.b")
    assert settings.cors_allowed_origins_list == [
        "http://localhost:5173",
        "https://example.com",
        "http://a.b",
    ]


def test_cors_allowed_origins_list_ignores_blank_entries():
    settings = Settings(cors_allowed_origins="http://localhost:5173,,  ,")
    assert settings.cors_allowed_origins_list == ["http://localhost:5173"]
