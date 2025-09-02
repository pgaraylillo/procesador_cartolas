# config/settings.py - Sistema de configuración centralizado
from __future__ import annotations
import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import logging


@dataclass
class DatabaseConfig:
    """Configuración de base de datos"""
    db_path: str = "data/finance.db"
    backup_retention_days: int = 30
    auto_backup: bool = True
    enable_wal: bool = True
    max_connections: int = 10


@dataclass
class MLConfig:
    """Configuración de Machine Learning"""
    test_size: float = 0.2
    cross_val_folds: int = 5
    max_features: int = 4000
    ngram_range: tuple = (1, 2)
    balance_classes: bool = True
    min_samples_per_category: int = 3
    confidence_threshold: float = 0.6
    model_path: str = "models/expense_classifier.pkl"


@dataclass
class KameConfig:
    """Configuración de integración KAME"""
    date_tolerance_days: int = 5
    amount_tolerance_pct: float = 0.05  # 5%
    enable_vendor_matching: bool = True
    vendor_similarity_threshold: float = 0.7
    supported_formats: List[str] = field(default_factory=lambda: ['.xlsx', '.xls', '.csv'])
    max_file_size_mb: int = 50


@dataclass
class UIConfig:
    """Configuración de interfaz de usuario"""
    page_title: str = "Santander Finance App"
    page_icon: str = "📊"
    layout: str = "wide"
    theme: str = "light"  # light, dark, auto
    sidebar_state: str = "expanded"
    currency_symbol: str = "$"
    date_format: str = "%d/%m/%Y"
    number_format: str = ",.0f"


@dataclass
class SecurityConfig:
    """Configuración de seguridad"""
    enable_auth: bool = False
    password_hash: Optional[str] = None
    session_timeout_minutes: int = 60
    max_file_size_mb: int = 100
    allowed_file_types: List[str] = field(default_factory=lambda: ['.xlsx', '.xls', '.csv'])
    enable_rate_limiting: bool = True


@dataclass
class LoggingConfig:
    """Configuración de logging"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/app.log"
    max_file_size_mb: int = 10
    backup_count: int = 5
    enable_console: bool = True


@dataclass
class AppConfig:
    """Configuración principal de la aplicación"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    ml: MLConfig = field(default_factory=MLConfig)
    kame: KameConfig = field(default_factory=KameConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Paths
    data_dir: str = "data"
    uploads_dir: str = "uploads"
    models_dir: str = "models"
    logs_dir: str = "logs"
    backups_dir: str = "backups"

    # Categories
    default_categories: List[str] = field(default_factory=lambda: [
        "Alimentación", "Combustible", "Servicios", "Transporte",
        "Salud", "Educación", "Entretenimiento", "Vestuario",
        "Hogar", "Tecnología", "Bancario", "Impuestos", "Otros"
    ])

    # Performance
    max_rows_display: int = 1000
    chunk_size: int = 1000
    enable_caching: bool = True
    cache_ttl_minutes: int = 30


class ConfigManager:
    """Gestor de configuración con carga desde archivo y variables de entorno"""

    def __init__(self, config_path: str = "config/app_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._setup_logging()

    def _load_config(self) -> AppConfig:
        """Carga configuración desde archivo y variables de entorno"""
        config = AppConfig()

        # Load from JSON file if exists
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    json_config = json.load(f)
                config = self._merge_config(config, json_config)
            except Exception as e:
                logging.warning(f"Could not load config file: {e}")

        # Override with environment variables
        config = self._load_env_overrides(config)

        # Create directories
        self._create_directories(config)

        return config

    def _merge_config(self, config: AppConfig, json_data: Dict[str, Any]) -> AppConfig:
        """Mezcla configuración JSON con configuración por defecto"""
        try:
            # Convert JSON to dataclass
            if 'database' in json_data:
                config.database = DatabaseConfig(**json_data['database'])
            if 'ml' in json_data:
                config.ml = MLConfig(**json_data['ml'])
            if 'kame' in json_data:
                config.kame = KameConfig(**json_data['kame'])
            if 'ui' in json_data:
                config.ui = UIConfig(**json_data['ui'])
            if 'security' in json_data:
                config.security = SecurityConfig(**json_data['security'])
            if 'logging' in json_data:
                config.logging = LoggingConfig(**json_data['logging'])

            # Simple fields
            for field_name in ['data_dir', 'uploads_dir', 'models_dir', 'logs_dir',
                               'backups_dir', 'default_categories', 'max_rows_display',
                               'chunk_size', 'enable_caching', 'cache_ttl_minutes']:
                if field_name in json_data:
                    setattr(config, field_name, json_data[field_name])

        except Exception as e:
            logging.warning(f"Error merging config: {e}")

        return config

    def _load_env_overrides(self, config: AppConfig) -> AppConfig:
        """Carga overrides desde variables de entorno"""
        env_mapping = {
            'DB_PATH': ('database', 'db_path'),
            'ML_TEST_SIZE': ('ml', 'test_size'),
            'ML_MAX_FEATURES': ('ml', 'max_features'),
            'KAME_DATE_TOLERANCE': ('kame', 'date_tolerance_days'),
            'KAME_AMOUNT_TOLERANCE': ('kame', 'amount_tolerance_pct'),
            'APP_PASSWORD': ('security', 'password_hash'),
            'LOG_LEVEL': ('logging', 'level'),
            'ENABLE_AUTH': ('security', 'enable_auth'),
        }

        for env_var, (section, field) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    section_obj = getattr(config, section)

                    # Type conversion
                    field_type = type(getattr(section_obj, field))
                    if field_type == bool:
                        value = value.lower() in ('true', '1', 'yes', 'on')
                    elif field_type == int:
                        value = int(value)
                    elif field_type == float:
                        value = float(value)

                    setattr(section_obj, field, value)
                except Exception as e:
                    logging.warning(f"Could not set {env_var}: {e}")

        return config

    def _create_directories(self, config: AppConfig):
        """Crea directorios necesarios"""
        directories = [
            config.data_dir,
            config.uploads_dir,
            config.models_dir,
            config.logs_dir,
            config.backups_dir,
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def _setup_logging(self):
        """Configura el sistema de logging"""
        log_config = self.config.logging

        # Create logs directory
        Path(log_config.file_path).parent.mkdir(parents=True, exist_ok=True)

        # Configure logging
        handlers = []

        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_config.file_path,
            maxBytes=log_config.max_file_size_mb * 1024 * 1024,
            backupCount=log_config.backup_count
        )
        file_handler.setFormatter(logging.Formatter(log_config.format))
        handlers.append(file_handler)

        # Console handler
        if log_config.enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(log_config.format))
            handlers.append(console_handler)

        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_config.level.upper()),
            handlers=handlers,
            format=log_config.format
        )

    def save_config(self):
        """Guarda configuración actual a archivo"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            config_dict = asdict(self.config)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Could not save config: {e}")

    def get_config(self) -> AppConfig:
        """Obtiene configuración actual"""
        return self.config

    def update_config(self, updates: Dict[str, Any]):
        """Actualiza configuración"""
        try:
            self.config = self._merge_config(self.config, updates)
            self.save_config()
        except Exception as e:
            logging.error(f"Could not update config: {e}")


# Global config instance
config_manager = ConfigManager()
config = config_manager.get_config()