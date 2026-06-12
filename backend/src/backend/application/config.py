from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    max_error_tolerance: int = 5
    ws_host: str = "0.0.0.0"
    ws_port: int = 6767
    ws_ping_interval: int = 20
    ws_ping_timeout: int = 20

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
