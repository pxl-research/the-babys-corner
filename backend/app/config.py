from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment_nano: str = "gpt-5-nano"
    azure_openai_deployment_mini: str = "gpt-5-mini"
    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-chat-v4"

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    staff_email: str = ""

    # Auth
    staff_admin_username: str = "staff"
    staff_admin_password: str = "changeme"
    pxl_admin_username: str = "admin"
    pxl_admin_password: str = "changeme"

    # Catalog
    catalog_path: str = "/app/catalog/catalog.json"

    # App
    session_secret_key: str = "dev-secret-key"
    session_cookie_secure: bool = False
    # Comma-separated allowed CORS origins. Explicit origins are required because the
    # frontend sends credentialed requests (cookies), which forbid a "*" wildcard.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # DB
    database_path: str = "/app/data/sessions.db"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()


def get_runtime_config_issues(config: Settings = settings) -> list[str]:
    issues: list[str] = []
    azure_configured = bool(config.azure_openai_endpoint and config.azure_openai_api_key)
    openrouter_configured = bool(config.openrouter_api_key)

    if not azure_configured and not openrouter_configured:
        issues.append(
            "No LLM provider configured. Set AZURE_OPENAI_ENDPOINT + "
            "AZURE_OPENAI_API_KEY or OPENROUTER_API_KEY."
        )

    return issues
