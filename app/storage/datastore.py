# app/storage/datastore.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd


@dataclass
class DataStore:
    root: Path = field(default_factory=lambda: Path('data'))
    labeled_file: str = 'labeled_transactions.csv'

    def __post_init__(self):
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_labeled(self, df: pd.DataFrame):
        """Guarda transacciones etiquetadas"""
        # Asegurar que tenemos las columnas necesarias
        df = self._normalize_dataframe(df).copy()

        # Columnas mínimas requeridas
        required_cols = ["date", "description", "amount", "category"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Falta columna requerida: {col}")

        path = self.root / self.labeled_file

        if path.exists():
            # Combinar con datos existentes
            old_df = pd.read_csv(path)
            old_df = self._normalize_dataframe(old_df)
            combined = pd.concat([old_df, df], ignore_index=True)

            # Eliminar duplicados basado en campos clave
            combined = combined.drop_duplicates(
                subset=["date", "description", "amount", "category"],
                keep="last"
            )
            combined.to_csv(path, index=False)
        else:
            df.to_csv(path, index=False)

    def load_labeled(self) -> pd.DataFrame:
        """Carga transacciones etiquetadas"""
        path = self.root / self.labeled_file

        if path.exists():
            try:
                df = pd.read_csv(path)
                return self._normalize_dataframe(df)
            except Exception as e:
                print(f"Error loading labeled data: {e}")
                return pd.DataFrame()

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
        """Obtiene resumen financiero básico"""
        labeled_data = self.load_labeled()

        if labeled_data.empty:
            return {
                'total_transactions': 0,
                'categories': 0,
                'date_range': None
            }

        # Convertir amount a numérico si es string
        if labeled_data['amount'].dtype == 'object':
            labeled_data['amount'] = pd.to_numeric(labeled_data['amount'], errors='coerce')

        summary = {
            'total_transactions': len(labeled_data),
            'total_expenses': len(labeled_data[labeled_data['amount'] < 0]),
            'total_income': len(labeled_data[labeled_data['amount'] > 0]),
            'categories': labeled_data['category'].nunique(),
            'category_list': sorted(labeled_data['category'].unique()),
            'amount_range': {
                'min': labeled_data['amount'].min(),
                'max': labeled_data['amount'].max(),
                'mean': labeled_data['amount'].mean()
            }
        }

        # Rango de fechas
        try:
            labeled_data['date'] = pd.to_datetime(labeled_data['date'])
            summary['date_range'] = {
                'earliest': labeled_data['date'].min().strftime('%Y-%m-%d'),
                'latest': labeled_data['date'].max().strftime('%Y-%m-%d')
            }
        except:
            summary['date_range'] = None

        return summary

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