import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("API_TITLE", "VRP Solver API")
    APP_VERSION: str = os.getenv("API_VERSION", "1.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./vrp.db")
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]

    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

    MAP_PROVIDER: str = os.getenv("MAP_PROVIDER", "locationiq")
    LOCATIONIQ_API_KEY: str = os.getenv("LOCATIONIQ_API_KEY", "")
    GOONG_API_KEY: str = os.getenv("GOONG_API_KEY", "")

    JWT_SECRET: str = os.getenv("JWT_SECRET_KEY", "change-me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TEST_TOPIC: str = os.getenv("KAFKA_TEST_TOPIC", "api-test-events")
    ENABLE_KAFKA: bool = os.getenv("ENABLE_KAFKA", "false").lower() == "true"

    MAX_ROUTE_POINTS: int = int(os.getenv("MAX_ROUTE_POINTS", "200"))
    DEFAULT_AVG_SPEED_KMH: float = float(os.getenv("DEFAULT_AVG_SPEED_KMH", "35.0"))


settings = Settings()
