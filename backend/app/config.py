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
    catalog_path: str = "/app/catalog/catalog_dummy.json"

    # App
    session_secret_key: str = "dev-secret-key"
    session_cookie_secure: bool = False

    # DB
    database_path: str = "/app/data/sessions.db"


settings = Settings()
