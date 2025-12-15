"""Application configuration settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    project_name: str = "Travel Website Backend"
    public_api_url: str = "http://localhost:8000"
    api_prefix: str = "/api"
    api_v1_prefix: str = "/v1"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./data/travel.db"
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 300  # 5 minutes default TTL
    media_storage_root: str = "storage/media"
    media_storage_backend: str = "local"
    media_storage_url_prefix: str = "/media"
    cors_allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # AI model configuration
    ai_model: str = "deepseek-chat"
    ai_api_base: str = "https://api.deepseek.com"
    ai_api_key: str = "sk-67c8b18677e64eddaa1d1db3a5f5134e"
    ai_provider: str = "DeepSeek"

    # XiaoHongShu spider configuration
    xhs_cookies: str = "abRequestId=b1783e6b-27ae-58a7-8d56-c92b2af7acd6; a1=199e0c807a1c47smhvf46uu0eer2fl3jkipqn57lk50000227898; webId=34c00c2f47e122e4d33bfb6e4b121cf6; gid=yjjd8SYJDfT0yjjd8SY8W32W0yS4WM6xhi4KU1T778ddFA28Ji1qVI888JJWYjY804i84SyW; web_session=040069b99a45e197305e7dd8283b4b4860f3fc; webBuild=5.0.6; xsecappid=xhs-pc-web; loadts=1765697685086; acw_tc=0ad529b117656976858006457ecdac90589919e39a36072e5c8006318af015; websectiga=29098a4cf41f76ee3f8db19051aaa60c0fc7c5e305572fec762da32d457d76ae; sec_poison_id=247cf612-2502-4f18-a4a9-694101d3201c; unread={%22ub%22:%226934e880000000001b0263cc%22%2C%22ue%22:%2269251281000000000d03de52%22%2C%22uc%22:25}"
    xhs_download_mode: str = "none"  # disable media downloads by default

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    """Load settings only once."""

    return Settings()


settings = get_settings()
