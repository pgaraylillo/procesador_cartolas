# app/config/simple_config.py - Configuración básica funcional
from pathlib import Path
from dataclasses import dataclass
from typing import List


@dataclass
class AppConfig:
    """Configuración simple de la aplicación"""

    # Directorios
    data_dir: str = "data"
    uploads_dir: str = "uploads"
    models_dir: str = "models"
    logs_dir: str = "logs"

    # Archivos
    labeled_data_file: str = "labeled_transactions.csv"
    model_file: str = "expense_classifier.pkl"

    # ML Settings
    test_size: float = 0.2
    max_features: int = 4000
    ngram_range: tuple = (1, 2)
    min_samples_per_category: int = 3
    confidence_threshold: float = 0.6

    # UI Settings
    max_rows_display: int = 1000
    currency_symbol: str = "$"
    date_format: str = "%d/%m/%Y"

    # Categories
    default_categories: List[str] = None

    def __post_init__(self):
        if self.default_categories is None:
            self.default_categories = [
                "bordados",
                "contabilidad",
                "servicios",
                "combustible",
                "alimentacion",
                "tecnologia",
                "bancario",
                "impuestos",
                "otros"
            ]

        # Crear directorios
        self.create_directories()

    def create_directories(self):
        """Crea los directorios necesarios"""
        directories = [
            self.data_dir,
            self.uploads_dir,
            self.models_dir,
            self.logs_dir
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def get_data_path(self) -> Path:
        return Path(self.data_dir)

    def get_uploads_path(self) -> Path:
        return Path(self.uploads_dir)

    def get_models_path(self) -> Path:
        return Path(self.models_dir)

    def get_labeled_data_path(self) -> Path:
        return self.get_data_path() / self.labeled_data_file

    def get_model_path(self) -> Path:
        return self.get_models_path() / self.model_file


# Instancia global de configuración
config = AppConfig()