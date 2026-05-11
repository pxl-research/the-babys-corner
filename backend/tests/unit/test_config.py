from app.config import Settings, get_runtime_config_issues


def test_runtime_config_reports_missing_llm_provider():
    settings = Settings(
        _env_file=None,
        azure_openai_endpoint="",
        azure_openai_api_key="",
        openrouter_api_key="",
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
