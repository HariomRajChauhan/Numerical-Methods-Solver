"""Application configuration loaded from environment / .env files."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. All values can be overridden via environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Numerical Methods Solver"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    debug: bool = False

    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    rate_limit_per_minute: int = 60

    # Safety limits enforced by the parser and solvers.
    solver_timeout_seconds: float = 10.0
    max_iterations_limit: int = 10_000
    max_matrix_size: int = 50

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list, stripped and empty-safe."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the cached global settings instance."""
    return Settings()
