# app/storage/datastore.py - VERSIÓN CORREGIDA
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import logging
import os
import tempfile


@dataclass
class DataStore:
    """DataStore robusto con manejo de errores mejorado"""
    root: Path = field(default_factory=lambda: Path('data'))

    def __post_init__(self):
        """Inicialización robusta con fallbacks reales"""
        self.root = Path(self.root)
        self.db = None

        # Configurar logging
        self._setup_logging()

        # Inicializar base de datos con fallbacks
        self._initialize_database()

        # Verificar que la inicialización fue exitosa
        if self.db is None:
            raise RuntimeError("❌ No se pudo inicializar la base de datos ni los fallbacks")

        self.logger.info(f"✅ DataStore inicializado exitosamente: {self.db.db_path}")

    def _setup_logging(self):
        """Configura logging para DataStore"""
        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _initialize_database(self):
        """Inicializa la base de datos con múltiples fallbacks"""
        # Estrategia 1: Ruta normal del proyecto
        primary_db_path = self._get_primary_db_path()
        if self._try_initialize_database(primary_db_path, "base de datos principal"):
            return

        # Estrategia 2: Directorio temporal del usuario
        temp_user_path = Path.home() / '.santander_finance' / 'finance_app.db'
        if self._try_initialize_database(temp_user_path, "directorio de usuario"):
            return

        # Estrategia 3: Directorio temporal del sistema
        system_temp_path = Path(tempfile.gettempdir()) / 'santander_finance_app.db'
        if self._try_initialize_database(system_temp_path, "directorio temporal"):
            return

        # Estrategia 4: Memoria (último recurso)
        if self._try_initialize_database(":memory:", "base de datos en memoria"):
            self.logger.warning("⚠️ Usando base de datos en memoria - los datos no se persistirán")
            return

        self.logger.error("❌ Todas las estrategias de inicialización fallaron")

    def _get_primary_db_path(self) -> Path:
        """Determina la ruta principal de la base de datos"""
        # Si root es relativo, buscar la raíz del proyecto
        if not self.root.is_absolute():
            project_root = self._find_project_root()
            return project_root / self.root / "finance_app.db"
        else:
            return self.root / "finance_app.db"

    def _find_project_root(self) -> Path:
        """Encuentra la raíz del proyecto de manera robusta"""
        current = Path.cwd()

        # Buscar hacia arriba hasta encontrar app/ o indicadores del proyecto
        for path in [current] + list(current.parents):
            # Indicadores de que estamos en la raíz del proyecto
            if any(path.exists() for path in [
                path / 'app' / 'main.py',
                path / 'requirements.txt',
                path / 'README.md'
            ]):
                return path

        # Fallback: directorio actual
        self.logger.warning(f"⚠️ No se encontró raíz del proyecto, usando: {current}")
        return current

    def _try_initialize_database(self, db_path, description: str) -> bool:
        """Intenta inicializar la base de datos en la ruta especificada"""
        try:
            # Importar aquí para evitar problemas de importación circular
            from database.db_manager import DatabaseManager

            # Si no es ":memory:", crear directorio padre
            if db_path != ":memory:":
                db_path = Path(db_path)
                db_path.parent.mkdir(parents=True, exist_ok=True)

            # Intentar crear/conectar a la base de datos
            self.db = DatabaseManager(str(db_path))

            # Verificar que la conexión funciona
            with self.db.get_connection() as conn:
                conn.execute("SELECT 1").fetchone()

            self.logger.info(f"✅ Base de datos inicializada: {description} -> {db_path}")
            return True

        except Exception as e:
            self.logger.warning(f"⚠️ Falló inicialización de {description}: {e}")
            return False

    def save_labeled(self, df: pd.DataFrame):
        """Guarda transacciones etiquetadas con manejo robusto de errores"""
        if self.db is None:
            raise RuntimeError("Base de datos no inicializada")

        try:
            self.logger.info(f"💾 Guardando {len(df)} transacciones...")

            if df.empty:
                self.logger.warning("⚠️ DataFrame vacío, no hay nada que guardar")
                return

            # Normalizar DataFrame con validación
            df_normalized = self._normalize_dataframe_safe(df)

            # Verificar columnas requeridas
            required_cols = ['date', 'description', 'amount', 'category']
            missing_cols = [col for col in required_cols if col not in df_normalized.columns]

            if missing_cols:
                raise ValueError(f"Faltan columnas requeridas: {missing_cols}")

            # Mejorar descripciones con nombres de contactos (opcional)
            df_normalized = self._enhance_descriptions_safe(df_normalized)

            # Guardar en base de datos
            self.db.save_labeled_transactions(df_normalized)
            self.logger.info("✅ Guardado exitoso en base de datos")

        except Exception as e:
            self.logger.error(f"❌ Error guardando transacciones: {e}")
            raise

    def load_labeled(self) -> pd.DataFrame:
        """Carga transacciones etiquetadas con fallbacks"""
        if self.db is None:
            self.logger.error("Base de datos no inicializada")
            return pd.DataFrame()

        try:
            df = self.db.get_labeled_transactions()
            return self._normalize_dataframe_safe(df) if not df.empty else pd.DataFrame()
        except Exception as e:
            self.logger.error(f"❌ Error cargando datos desde BD: {e}")
            return self._load_from_csv_fallback()

    def _load_from_csv_fallback(self) -> pd.DataFrame:
        """Carga datos desde CSV como fallback"""
        csv_path = self.root / 'labeled_transactions.csv'
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                return self._normalize_dataframe_safe(df)
            except Exception as e:
                self.logger.error(f"❌ Error cargando CSV fallback: {e}")
        return pd.DataFrame()

    def _normalize_dataframe_safe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza DataFrame de manera segura"""
        if df.empty:
            return df

        try:
            df = df.copy()

            # Mapeo básico y seguro de columnas
            simple_mapping = {
                'Fecha': 'date', 'fecha': 'date',
                'Descripción': 'description', 'descripcion': 'description', 'descripción': 'description',
                'Monto': 'amount', 'monto': 'amount',
                'Categoría': 'category', 'categoria': 'category', 'categoría': 'category',
                'ABONO/CARGO': 'debit_credit', 'abono/cargo': 'debit_credit'
            }

            # Solo renombrar columnas que existen
            rename_dict = {old: new for old, new in simple_mapping.items() if old in df.columns}
            if rename_dict:
                df = df.rename(columns=rename_dict)

            # Limpiar strings de manera segura
            string_columns = df.select_dtypes(include=['object']).columns
            for col in string_columns:
                try:
                    df[col] = df[col].astype(str).str.strip()
                except:
                    pass  # Continuar si hay problemas con una columna específica

            return df

        except Exception as e:
            self.logger.error(f"❌ Error normalizando DataFrame: {e}")
            return df  # Retornar original si falla la normalización

    def _enhance_descriptions_safe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mejora descripciones de manera segura (opcional)"""
        if 'description' not in df.columns:
            return df

        try:
            # Solo si tenemos DatabaseManager y funciona
            if hasattr(self.db, 'enhance_description_with_contacts'):
                if 'original_description' not in df.columns:
                    df['original_description'] = df['description'].copy()

                df['description'] = df['description'].apply(
                    self.db.enhance_description_with_contacts
                )
            return df
        except Exception as e:
            self.logger.warning(f"⚠️ No se pudieron mejorar descripciones: {e}")
            return df

    def get_financial_summary(self) -> dict:
        """Obtiene resumen financiero de manera segura"""
        try:
            if self.db is None:
                return {'error': 'Base de datos no disponible', 'total_transactions': 0}

            # Obtener estadísticas desde DB
            db_stats = self.db.get_statistics()
            labeled_data = self.load_labeled()

            if labeled_data.empty:
                return {
                    'total_transactions': 0,
                    'categories': db_stats.get('categories_count', 0),
                    'contacts': db_stats.get('contacts_count', 0),
                    'date_range': None
                }

            # Construir resumen básico
            summary = {
                'total_transactions': len(labeled_data),
                'categories': db_stats.get('categories_count', 0),
                'contacts': db_stats.get('contacts_count', 0),
                'category_distribution': db_stats.get('category_distribution', [])
            }

            # Agregar estadísticas adicionales si es posible
            if 'amount' in labeled_data.columns:
                try:
                    labeled_data['amount'] = pd.to_numeric(labeled_data['amount'], errors='coerce')
                    summary.update({
                        'total_expenses': len(labeled_data[labeled_data['amount'] < 0]),
                        'total_income': len(labeled_data[labeled_data['amount'] > 0]),
                        'amount_range': {
                            'min': labeled_data['amount'].min(),
                            'max': labeled_data['amount'].max(),
                            'mean': labeled_data['amount'].mean()
                        }
                    })
                except:
                    pass

            return summary

        except Exception as e:
            self.logger.error(f"❌ Error obteniendo resumen financiero: {e}")
            return {'error': str(e), 'total_transactions': 0}

    # === MÉTODOS PARA GESTIÓN DE CATEGORÍAS ===
    def get_categories(self) -> List[str]:
        """Obtiene categorías de manera segura"""
        try:
            if self.db:
                categories = self.db.get_categories(active_only=True)
                return [cat['name'] for cat in categories]
        except Exception as e:
            self.logger.error(f"❌ Error cargando categorías: {e}")

        # Fallback a categorías por defecto
        return ['bordados', 'contabilidad', 'servicios', 'combustible',
                'alimentacion', 'tecnologia', 'bancario', 'impuestos', 'otros']

    def add_category(self, name: str, description: str = None) -> bool:
        """Agrega nueva categoría de manera segura"""
        try:
            if self.db:
                return self.db.add_category(name, description)
        except Exception as e:
            self.logger.error(f"❌ Error agregando categoría: {e}")
        return False

    # === MÉTODOS PARA GESTIÓN DE CONTACTOS ===
    def get_contacts(self) -> List[Dict]:
        """Obtiene contactos de manera segura"""
        try:
            if self.db:
                return self.db.get_contacts(active_only=True)
        except Exception as e:
            self.logger.error(f"❌ Error cargando contactos: {e}")
        return []

    def add_contact(self, rut: str, name: str, alias: str = None, contact_type: str = 'proveedor') -> bool:
        """Agrega contacto de manera segura"""
        try:
            if self.db:
                return self.db.add_contact(rut, name, alias, contact_type)
        except Exception as e:
            self.logger.error(f"❌ Error agregando contacto: {e}")
        return False

    def is_ready(self) -> bool:
        """Verifica si el DataStore está listo para usar"""
        return self.db is not None

    def get_status(self) -> Dict:
        """Obtiene estado actual del DataStore"""
        return {
            'database_initialized': self.db is not None,
            'database_path': str(self.db.db_path) if self.db else None,
            'database_type': 'memory' if self.db and str(self.db.db_path) == ':memory:' else 'file',
            'ready': self.is_ready()
        }

    def save_raw_data(self, df: pd.DataFrame, filename: str = None):
        """Guarda datos sin procesar de manera segura"""
        try:
            if filename is None:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"raw_data_{timestamp}.csv"

            # Crear directorio si no existe
            self.root.mkdir(parents=True, exist_ok=True)
            path = self.root / filename

            df.to_csv(path, index=False)
            self.logger.info(f"✅ Datos guardados en: {path}")
            return str(path)
        except Exception as e:
            self.logger.error(f"❌ Error guardando datos raw: {e}")
            return None