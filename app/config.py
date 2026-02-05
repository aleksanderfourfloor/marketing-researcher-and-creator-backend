import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Research App API")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")


settings = Settings()
