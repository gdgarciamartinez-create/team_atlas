from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # lee .env y NO se queja por keys extra
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # app
    app_name: str = Field(default="atlas_gatillo_notifier", alias="APP_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    loop_seconds: int = Field(default=15, alias="LOOP_SECONDS")
    tz: str = Field(default="America/Santiago", alias="TZ")

    # telegram
    telegram_bot_token: str = Field(default="", alias="8422955778:AAFhUajt67-gyx5myJP9SCOxlUAIhKPGYzU")
    telegram_chat_id: str = Field(default="", alias="5372780169")

    # openai
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_timeout_s: int = Field(default=20, alias="OPENAI_TIMEOUT_S")
    ai_enabled: bool = Field(default=True, alias="AI_ENABLED")
    ai_ruleset_version: str = Field(default="v1", alias="AI_RULESET_VERSION")

    # riesgo
    account_size: float = Field(default=10000.0, alias="ACCOUNT_SIZE")
    risk_pct: float = Field(default=1.0, alias="RISK_PCT")

    # anti-spam
    alert_cooldown_min: int = Field(default=45, alias="ALERT_COOLDOWN_MIN")

    # atlas logic (Phase 4/5)
    atlas_mode: str = Field(default="winter", alias="ATLAS_MODE") # winter | summer
    tf_exec: str = Field(default="5m", alias="TF_EXEC")
    fib_key: float = Field(default=0.786, alias="FIB_KEY")
    gap_threshold: float = Field(default=0.0015, alias="GAP_THRESHOLD") # 0.15%
    max_trades_per_window: int = Field(default=1, alias="MAX_TRADES_PER_WINDOW")
    loop_seconds: int = Field(default=5, alias="LOOP_SECONDS")
    score_threshold: int = Field(default=70, alias="SCORE_THRESHOLD")

settings = Settings()
