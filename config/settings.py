"""Centralised application configuration.

Settings are read from environment variables (and a local ``.env`` file if
present) via ``pydantic-settings``. Field names map to upper-case environment
variables, so ``openai_api_key`` reads ``OPENAI_API_KEY``. Secrets are never
hard-coded; ``.env.example`` documents every variable.

Use :func:`get_settings` to obtain a cached singleton.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = two levels up from this file (config/settings.py -> project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SAMPLE_DIR = PROJECT_ROOT / "data" / "sample"


class Settings(BaseSettings):
    """Typed application configuration with sensible defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- OpenAI / LLM ---------------------------------------------------- #
    openai_api_key: str | None = Field(default=None)
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_request_timeout: int = Field(default=60, ge=1)
    openai_max_retries: int = Field(default=3, ge=0)

    # --- Data provider --------------------------------------------------- #
    data_provider: str = Field(default="yfinance", description="'yfinance' or 'local'")
    request_timeout: int = Field(default=30, ge=1)
    default_currency: str = "USD"
    sample_data_dir: Path = DEFAULT_SAMPLE_DIR

    # --- Valuation defaults --------------------------------------------- #
    risk_free_rate: float = Field(default=0.04, ge=-0.05, le=0.25)
    equity_risk_premium: float = Field(default=0.055, gt=0.0, le=0.25)
    default_terminal_growth: float = Field(default=0.025, ge=-0.05, lt=0.20)
    default_tax_rate: float = Field(default=0.21, ge=0.0, le=1.0)
    forecast_years: int = Field(default=5, ge=1, le=20)

    # --- Monte Carlo ----------------------------------------------------- #
    monte_carlo_simulations: int = Field(default=10_000, ge=100, le=1_000_000)
    monte_carlo_seed: int = 42

    # --- RAG ------------------------------------------------------------- #
    rag_chunk_size: int = Field(default=1000, ge=100)
    rag_chunk_overlap: int = Field(default=150, ge=0)
    rag_top_k: int = Field(default=5, ge=1)

    # --- Logging --------------------------------------------------------- #
    log_level: str = "INFO"

    def has_openai(self) -> bool:
        """Whether an OpenAI API key is configured."""
        return bool(self.openai_api_key)

    @property
    def use_live_data(self) -> bool:
        """Whether the app should attempt live (yfinance) data retrieval."""
        return self.data_provider.strip().lower() == "yfinance"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
