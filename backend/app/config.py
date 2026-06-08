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
    app_env: str = "development"
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


_DEFAULT_SECRET_VALUES = {"", "dev-secret-key"}
_DEFAULT_PASSWORD_VALUES = {"", "changeme"}
_MIN_SECRET_LENGTH = 32
_MIN_PASSWORD_LENGTH = 12


def _is_production(config: Settings) -> bool:
    return config.app_env.strip().lower() in {"prod", "production"}


def get_startup_config_errors(config: Settings = settings) -> list[str]:
    if not _is_production(config):
        return []

    errors: list[str] = []
    session_secret_key = config.session_secret_key.strip()
    staff_admin_password = config.staff_admin_password.strip()
    pxl_admin_password = config.pxl_admin_password.strip()

    if session_secret_key in _DEFAULT_SECRET_VALUES or len(session_secret_key) < _MIN_SECRET_LENGTH:
        errors.append("SESSION_SECRET_KEY must be set to a strong production secret.")
    if (
        staff_admin_password in _DEFAULT_PASSWORD_VALUES
        or len(staff_admin_password) < _MIN_PASSWORD_LENGTH
    ):
        errors.append("STAFF_ADMIN_PASSWORD must be set to a strong production password.")
    if (
        pxl_admin_password in _DEFAULT_PASSWORD_VALUES
        or len(pxl_admin_password) < _MIN_PASSWORD_LENGTH
    ):
        errors.append("PXL_ADMIN_PASSWORD must be set to a strong production password.")
    if not config.session_cookie_secure:
        errors.append("SESSION_COOKIE_SECURE must be true in production.")
    return errors


def get_runtime_config_issues(config: Settings = settings) -> list[str]:
    issues: list[str] = []
    azure_configured = bool(
        config.azure_openai_endpoint.strip() and config.azure_openai_api_key.strip()
    )
    openrouter_configured = bool(config.openrouter_api_key.strip())

    if not azure_configured and not openrouter_configured:
        issues.append(
            "No LLM provider configured. Set AZURE_OPENAI_ENDPOINT + "
            "AZURE_OPENAI_API_KEY or OPENROUTER_API_KEY."
        )

    return issues
