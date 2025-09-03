# app/storage/datastore.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from database.db_manager import DatabaseManager


@dataclass
class DataStore:
    root: Path = field(default_factory=lambda: Path('data'))

    def __post_init__(self):
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

        # Inicializar gestor de base de datos
        try:
            self.db = DatabaseManager(str(self.root / "finance_app.db"))
            print(f"✅ DatabaseManager inicializado: {self.db.db_path}")
        except Exception as e:
            print(f"❌ Error inicializando DatabaseManager: {e}")
            # Crear fallback básico para evitar que la app se rompa
            import tempfile
            fallback_db = Path(tempfile.gettempdir()) / "finance_app_fallback.db"
            self.db = DatabaseManager(str(fallback_db))
            print(f"⚠️ Usando BD fallback: {fallback_db}")
            raise e

    def save_labeled(self, df: pd.DataFrame):
        """Guarda transacciones etiquetadas en base de datos"""
        try:
            print(f"🔍 Intentando guardar {len(df)} transacciones...")

            if df.empty:
                print("⚠️ DataFrame vacío, no hay nada que guardar")
                return

            # Normalizar DataFrame
            print("📝 Normalizando DataFrame...")
            df_normalized = self._normalize_dataframe(df)
            print(f"📊 Columnas después de normalizar: {list(df_normalized.columns)}")

            # Verificar columnas requeridas
            required_cols = ['date', 'description', 'amount', 'category']
            missing_cols = [col for col in required_cols if col not in df_normalized.columns]

            if missing_cols:
                raise ValueError(f"Faltan columnas requeridas: {missing_cols}")

            # Mejorar descripciones con nombres de contactos
            if 'description' in df_normalized.columns:
                print("🔄 Mejorando descripciones con contactos...")
                if 'original_description' not in df_normalized.columns:
                    df_normalized['original_description'] = df_normalized['description'].copy()

                try:
                    df_normalized['description'] = df_normalized['description'].apply(
                        self.db.enhance_description_with_contacts
                    )
                except Exception as e:
                    print(f"⚠️ Error mejorando descripciones: {e}")
                    # Continuar sin mejoras si hay error

            # Guardar en base de datos
            print("💾 Guardando en base de datos...")
            self.db.save_labeled_transactions(df_normalized)
            print("✅ Guardado exitoso en base de datos")

        except Exception as e:
            print(f"❌ Error guardando transacciones etiquetadas: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def load_labeled(self) -> pd.DataFrame:
        """Carga transacciones etiquetadas desde base de datos"""
        try:
            df = self.db.get_labeled_transactions()
            return self._normalize_dataframe(df) if not df.empty else pd.DataFrame()
        except Exception as e:
            print(f"Error loading labeled data from DB: {e}")
            # Fallback a archivo CSV si existe
            return self._load_from_csv_fallback()

    def _load_from_csv_fallback(self) -> pd.DataFrame:
        """Carga datos desde CSV como fallback"""
        csv_path = self.root / 'labeled_transactions.csv'
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                return self._normalize_dataframe(df)
            except Exception as e:
                print(f"Error loading CSV fallback: {e}")
        return pd.DataFrame()

    def save_raw_data(self, df: pd.DataFrame, filename: str = None):
        """Guarda datos sin procesar"""
        if filename is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"raw_data_{timestamp}.csv"

        path = self.root / filename
        df.to_csv(path, index=False)
        return str(path)

    def get_financial_summary(self) -> dict:
        """Obtiene resumen financiero desde base de datos"""
        try:
            # Obtener estadísticas desde DB
            db_stats = self.db.get_statistics()

            # Cargar datos etiquetados
            labeled_data = self.load_labeled()

            if labeled_data.empty:
                return {
                    'total_transactions': 0,
                    'categories': db_stats.get('categories_count', 0),
                    'contacts': db_stats.get('contacts_count', 0),
                    'date_range': None
                }

            # Convertir amount a numérico si es string
            if 'amount' in labeled_data.columns and labeled_data['amount'].dtype == 'object':
                labeled_data['amount'] = pd.to_numeric(labeled_data['amount'], errors='coerce')

            summary = {
                'total_transactions': len(labeled_data),
                'total_expenses': len(
                    labeled_data[labeled_data['amount'] < 0]) if 'amount' in labeled_data.columns else 0,
                'total_income': len(
                    labeled_data[labeled_data['amount'] > 0]) if 'amount' in labeled_data.columns else 0,
                'categories': db_stats.get('categories_count', 0),
                'contacts': db_stats.get('contacts_count', 0),
                'category_distribution': db_stats.get('category_distribution', [])
            }

            # Estadísticas de montos
            if 'amount' in labeled_data.columns and not labeled_data['amount'].isna().all():
                summary['amount_range'] = {
                    'min': labeled_data['amount'].min(),
                    'max': labeled_data['amount'].max(),
                    'mean': labeled_data['amount'].mean()
                }

            # Rango de fechas
            if 'date' in labeled_data.columns:
                try:
                    labeled_data['date'] = pd.to_datetime(labeled_data['date'])
                    summary['date_range'] = {
                        'earliest': labeled_data['date'].min().strftime('%Y-%m-%d'),
                        'latest': labeled_data['date'].max().strftime('%Y-%m-%d')
                    }
                except:
                    summary['date_range'] = None

            return summary

        except Exception as e:
            print(f"Error getting financial summary: {e}")
            return {'total_transactions': 0, 'error': str(e)}

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza DataFrame para consistencia interna"""
        if df.empty:
            return df

        df = df.copy()

        # Mapear headers comunes a formato estándar
        column_mapping = {
            'Fecha': 'date',
            'fecha': 'date',
            'Descripción': 'description',
            'descripcion': 'description',
            'descripción': 'description',
            'Monto': 'amount',
            'monto': 'amount',
            'Categoría': 'category',
            'categoria': 'category',
            'categoría': 'category',
            'ABONO/CARGO': 'debit_credit',
            'abono/cargo': 'debit_credit'
        }

        # Aplicar mapeo si las columnas existen
        rename_dict = {old: new for old, new in column_mapping.items() if old in df.columns}
        if rename_dict:
            df = df.rename(columns=rename_dict)

        # Limpiar strings
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        return df

    # === MÉTODOS PARA GESTIÓN DE CATEGORÍAS ===

    def get_categories(self) -> List[str]:
        """Obtiene lista de categorías desde base de datos"""
        try:
            categories = self.db.get_categories(active_only=True)
            return [cat['name'] for cat in categories]
        except Exception as e:
            print(f"Error loading categories: {e}")
            # Fallback a categorías por defecto
            return ['bordados', 'contabilidad', 'servicios', 'otros']

    def add_category(self, name: str, description: str = None) -> bool:
        """Agrega nueva categoría"""
        return self.db.add_category(name, description)

    # === MÉTODOS PARA GESTIÓN DE CONTACTOS ===

    def get_contacts(self) -> List[Dict]:
        """Obtiene lista de contactos"""
        return self.db.get_contacts(active_only=True)

    def add_contact(self, rut: str, name: str, alias: str = None, contact_type: str = 'proveedor') -> bool:
        """Agrega nuevo contacto"""
        return self.db.add_contact(rut, name, alias, contact_type)

    def find_contact_by_rut(self, rut: str) -> Optional[Dict]:
        """Busca contacto por RUT"""
        return self.db.find_contact_by_rut(rut)