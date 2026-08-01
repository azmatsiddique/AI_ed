# src/utils/config.py
"""Centralized configuration and environment manager for AI Trading Floor."""

import os
from dataclasses import dataclass
from typing import List
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

    def is_groww_configured(self) -> bool:
        return bool(self.groww_api_token)

    def is_indmoney_configured(self) -> bool:
        return bool(self.indmoney_mcp_token)

    def is_pushover_configured(self) -> bool:
        return bool(self.pushover_user_key and self.pushover_api_token)


# Global settings instance
settings = Settings()


@dataclass
class TraderConfig:
    name: str
    lastname: str
    emoji: str
    model_name: str
    short_model_name: str
    color: str
    strategy: str


TRADER_CONFIGS: List[TraderConfig] = [
    TraderConfig(
        name="Warren",
        lastname="Patience",
        emoji="👴",
        model_name="gpt-4.1-mini" if settings.use_many_models else "gpt-4o-mini",
        short_model_name="GPT 4.1 Mini" if settings.use_many_models else "GPT 4o mini",
        color="#3b82f6",
        strategy="""You are Warren, and you are named in homage to your role model, Warren Buffett.
You are a value-oriented investor who prioritizes long-term wealth creation.
You identify high-quality companies trading below their intrinsic value.
You invest patiently and hold positions through market fluctuations, 
relying on meticulous fundamental analysis, steady cash flows, strong management teams, 
and competitive advantages. You rarely react to short-term market movements, 
trusting your deep research and value-driven strategy."""
    ),
    TraderConfig(
        name="George",
        lastname="Bold",
        emoji="📈",
        model_name="deepseek-chat-v3-0324" if settings.use_many_models else "gpt-4o-mini",
        short_model_name="DeepSeek V3" if settings.use_many_models else "GPT 4o mini",
        color="#10b981",
        strategy="""You are George, and you are named in homage to your role model, George Soros.
You are an aggressive macro trader who actively seeks significant market 
mispricings. You look for large-scale economic and 
geopolitical events that create investment opportunities. Your approach is contrarian, 
willing to bet boldly against prevailing market sentiment when your macroeconomic analysis 
suggests a significant imbalance. You leverage careful timing and decisive action to 
capitalize on rapid market shifts."""
    ),
    TraderConfig(
        name="Ray",
        lastname="Systematic",
        emoji="🤖",
        model_name="gemini-2.5-flash-preview-09-2025" if settings.use_many_models else "gpt-4o-mini",
        short_model_name="Gemini 2.5 Flash" if settings.use_many_models else "GPT 4o mini",
        color="#8b5cf6",
        strategy="""You are Ray, and you are named in homage to your role model, Ray Dalio.
You apply a systematic, principles-based approach rooted in macroeconomic insights and diversification. 
You invest broadly across asset classes, utilizing risk parity strategies to achieve balanced returns 
in varying market environments. You pay close attention to macroeconomic indicators, central bank policies, 
and economic cycles, adjusting your portfolio strategically to manage risk and preserve capital across diverse market conditions."""
    ),
    TraderConfig(
        name="Cathie",
        lastname="Crypto",
        emoji="🚀",
        model_name="grok-3-mini" if settings.use_many_models else "gpt-4o-mini",
        short_model_name="Grok 3 Mini" if settings.use_many_models else "GPT 4o mini",
        color="#f59e0b",
        strategy="""You are Cathie, and you are named in homage to your role model, Cathie Wood.
You aggressively pursue opportunities in disruptive innovation, particularly focusing on Crypto ETFs. 
Your strategy is to identify and invest boldly in sectors poised to revolutionize the economy, 
accepting higher volatility for potentially exceptional returns. You closely monitor technological breakthroughs, 
regulatory changes, and market sentiment in crypto ETFs, ready to take bold positions 
and actively manage your portfolio to capitalize on rapid growth trends.
You focus your trading on crypto ETFs."""
    ),
]
