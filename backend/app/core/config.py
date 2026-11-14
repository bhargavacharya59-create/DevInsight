"""Application configuration using Pydantic Settings."""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./devinsight_dev.db"
    DATABASE_URL_SYNC: str = "sqlite:///./devinsight_dev.db"

    # Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # GitHub
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_REPO_OWNER: Optional[str] = None
    GITHUB_REPO_NAME: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: str = "devinsight-webhook-secret"

    # ShopSphere integration
    SHOPSPHERE_URL: str = "http://localhost:8001"
    SHOPSPHERE_METRICS_URL: str = "http://localhost:8001/metrics"
    # No built-in ingest secret: configure the same strong value in both apps.
    INGEST_API_KEY: Optional[str] = None

    # Monitoring
    MONITORING_MODE: str = "demo"

    # Prometheus
    PROMETHEUS_URL: str = "http://localhost:9090"

    # Loki
    LOKI_URL: str = "http://localhost:3100"

    # OpenTelemetry
    OTEL_COLLECTOR_URL: str = "http://localhost:4318"

    # Anomaly Detection
    ANOMALY_CONTAMINATION: float = 0.1
    ANOMALY_THRESHOLD: float = -0.3
    DETECTION_INTERVAL_SECONDS: int = 30

    # Demo
    DEMO_SCENARIO_AUTO_PROGRESS: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def is_demo_mode(self) -> bool:
        return self.MONITORING_MODE.lower() == "demo"

    @property
    def gemini_available(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def github_configured(self) -> bool:
        return bool(self.GITHUB_TOKEN and self.GITHUB_REPO_OWNER and self.GITHUB_REPO_NAME)


settings = Settings()
