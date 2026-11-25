from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StockPilot"
    debug: bool = False
    database_url: str = "sqlite:///./stockpilot.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
