import os
from dotenv import load_dotenv

load_dotenv()

class Settings:

    APP_NAME = "VRP Optimizer API"

    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///./vrp.db"
    )

    # Google Maps
    GOOGLE_MAPS_API_KEY = os.getenv(
        "GOOGLE_MAPS_API_KEY",
        ""
    )

    # JWT
    JWT_SECRET = os.getenv(
        "JWT_SECRET",
        "secret"
    )

    # giới hạn số điểm route
    MAX_ROUTE_POINTS = 200


settings = Settings()