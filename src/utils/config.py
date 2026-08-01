# src/utils/config.py
"""Centralized configuration and environment manager for AI Trading Floor."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass
class Settings:
    # LLM API Keys
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    
    # Groww Market API
    groww_api_token: str = os.getenv("GROWW_API_TOKEN", "")
    groww_base_url: str = os.getenv("GROWW_BASE_URL", "https://api.groww.in")

    # INDmoney / INDstocks Integration
    indmoney_mcp_url: str = os.getenv("INDMONEY_MCP_URL", "https://mcp.indmoney.com/mcp")
    indmoney_mcp_token: str = os.getenv("INDMONEY_MCP_TOKEN", "")

    # Moomoo / Futu OpenAPI Integration
    moomoo_host: str = os.getenv("MOOMOO_HOST", "127.0.0.1")
    moomoo_port: int = int(os.getenv("MOOMOO_PORT", "11111"))
    moomoo_env: str = os.getenv("MOOMOO_ENV", "SIMULATE")

    # Execution & Scheduling Settings
    run_every_n_minutes: int = int(os.getenv("RUN_EVERY_N_MINUTES", "60"))
    run_even_when_market_is_closed: bool = (
        os.getenv("RUN_EVEN_WHEN_MARKET_IS_CLOSED", "false").strip().lower() == "true"
    )
    use_many_models: bool = os.getenv("USE_MANY_MODELS", "false").strip().lower() == "true"

    # Push Notification Credentials
    pushover_user_key: str = os.getenv("PUSHOVER_USER_KEY", "")
    pushover_api_token: str = os.getenv("PUSHOVER_API_TOKEN", "")

    # Brave Web Search
    brave_api_key: str = os.getenv("BRAVE_API_KEY", "")

    def is_groww_configured(self) -> bool:
        return bool(self.groww_api_token)

    def is_indmoney_configured(self) -> bool:
        return bool(self.indmoney_mcp_token)

    def is_pushover_configured(self) -> bool:
        return bool(self.pushover_user_key and self.pushover_api_token)


# Global settings instance
settings = Settings()
