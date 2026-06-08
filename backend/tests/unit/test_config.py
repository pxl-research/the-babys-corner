from app.config import Settings, get_runtime_config_issues, get_startup_config_errors


def test_runtime_config_reports_missing_llm_provider():
    settings = Settings(
        _env_file=None,
        azure_openai_endpoint="",
        azure_openai_api_key="",
        openrouter_api_key="",
    )

    issues = get_runtime_config_issues(settings)

    assert any("No LLM provider configured" in issue for issue in issues)


def test_runtime_config_treats_whitespace_llm_values_as_missing():
    settings = Settings(
        _env_file=None,
        azure_openai_endpoint="   ",
        azure_openai_api_key="   ",
        openrouter_api_key="   ",
    )

    issues = get_runtime_config_issues(settings)

    assert any("No LLM provider configured" in issue for issue in issues)


def test_runtime_config_accepts_complete_azure_provider():
    settings = Settings(
        _env_file=None,
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="key",
        openrouter_api_key="",
    )

    assert get_runtime_config_issues(settings) == []


def test_runtime_config_accepts_openrouter_provider():
    settings = Settings(
        _env_file=None,
        azure_openai_endpoint="",
        azure_openai_api_key="",
        openrouter_api_key="key",
    )

    assert get_runtime_config_issues(settings) == []


def test_cors_origin_list_parses_and_trims():
    settings = Settings(_env_file=None, cors_origins=" https://a.com , http://localhost:5173 ,, ")
    assert settings.cors_origin_list == ["https://a.com", "http://localhost:5173"]


def test_startup_config_rejects_blank_production_auth_values():
    settings = Settings(
        _env_file=None,
        app_env="production",
        session_secret_key="",
        staff_admin_password="",
        pxl_admin_password="",
    )

    errors = get_startup_config_errors(settings)

    assert any("SESSION_SECRET_KEY" in error for error in errors)
    assert any("STAFF_ADMIN_PASSWORD" in error for error in errors)
    assert any("PXL_ADMIN_PASSWORD" in error for error in errors)


def test_startup_config_rejects_default_production_auth_values():
    settings = Settings(
        _env_file=None,
        app_env="production",
        session_secret_key="dev-secret-key",
        staff_admin_password="changeme",
        pxl_admin_password="changeme",
    )

    errors = get_startup_config_errors(settings)

    assert any("SESSION_SECRET_KEY" in error for error in errors)
    assert any("STAFF_ADMIN_PASSWORD" in error for error in errors)
    assert any("PXL_ADMIN_PASSWORD" in error for error in errors)


def test_startup_config_rejects_padded_default_auth_values():
    settings = Settings(
        _env_file=None,
        app_env=" production ",
        session_secret_key="dev-secret-key" + (" " * 32),
        staff_admin_password="changeme" + (" " * 12),
        pxl_admin_password="changeme" + (" " * 12),
    )

    errors = get_startup_config_errors(settings)

    assert any("SESSION_SECRET_KEY" in error for error in errors)
    assert any("STAFF_ADMIN_PASSWORD" in error for error in errors)
    assert any("PXL_ADMIN_PASSWORD" in error for error in errors)


def test_startup_config_rejects_insecure_production_cookie():
    settings = Settings(
        _env_file=None,
        app_env="production",
        session_secret_key="x" * 48,
        staff_admin_password="staff-" + ("x" * 24),
        pxl_admin_password="admin-" + ("x" * 24),
        session_cookie_secure=False,
    )

    errors = get_startup_config_errors(settings)

    assert any("SESSION_COOKIE_SECURE" in error for error in errors)


def test_startup_config_accepts_strong_production_auth_values():
    settings = Settings(
        _env_file=None,
        app_env="production",
        session_secret_key="x" * 48,
        staff_admin_password="staff-" + ("x" * 24),
        pxl_admin_password="admin-" + ("x" * 24),
        session_cookie_secure=True,
    )

    assert get_startup_config_errors(settings) == []
