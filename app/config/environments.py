# config/environments.py
import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class BaseConfig:
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite:///data/finance.db"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    MAX_FILE_SIZE_MB: int = 100

@dataclass
class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_URL: str = "sqlite:///data/finance_dev.db"

@dataclass
class TestConfig(BaseConfig):
    TESTING: bool = True
    DATABASE_URL: str = "sqlite:///:memory:"
    SECRET_KEY: str = "test-secret-key"

@dataclass
class ProductionConfig(BaseConfig):
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/finance_prod.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY")  # Debe estar definida
    SENTRY_DSN: str = os.getenv("SENTRY_DSN")  # Para error tracking

config_map = {
    'development': DevelopmentConfig,
    'testing': TestConfig,
    'production': ProductionConfig
}

def get_config() -> BaseConfig:
    env = os.getenv('APP_ENV', 'development')
    config_class = config_map.get(env, DevelopmentConfig)
    return config_class()