from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./supply_chain_warroom.db"
    anthropic_api_key: str = ""
    frontend_url: str = "http://localhost:5173"
    environment: str = "development"

    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8"}


settings = Settings()
