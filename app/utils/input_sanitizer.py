# app/utils/input_sanitizer.py
import re
from typing import Any, Union
import pandas as pd


class InputSanitizer:

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitizar nombres de archivo"""
        # Remover caracteres peligrosos
        clean_name = re.sub(r'[^\w\s.-]', '', filename)

        # Evitar path traversal
        clean_name = clean_name.replace('..', '').replace('/', '').replace('\\', '')

        # Limitar longitud
        clean_name = clean_name[:100]

        return clean_name

    @staticmethod
    def validate_amount(amount: Any) -> float:
        """Validar y sanitizar montos"""
        try:
            # Convertir a float
            if isinstance(amount, str):
                # Limpiar formato
                clean_amount = re.sub(r'[^\d.,-]', '', amount)
                clean_amount = clean_amount.replace(',', '.')
                amount = float(clean_amount)
            else:
                amount = float(amount)

            # Validar rango razonable
            if abs(amount) > 1e12:  # 1 trillion
                raise ValueError("Amount too large")

            return amount

        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def sanitize_sql_input(text: str) -> str:
        """Prevenir SQL injection (aunque usemos ORM)"""
        if not isinstance(text, str):
            return str(text)

        # Escapar caracteres peligrosos
        dangerous_chars = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']

        for char in dangerous_chars:
            text = text.replace(char, '')

        return text[:1000]  # Limitar longitud

    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Validar y limpiar DataFrame completo"""
        if df.empty:
            raise ValueError("DataFrame is empty")

        if len(df) > 10000:
            raise ValueError("DataFrame too large (max 10,000 rows)")

        # Sanitizar columnas de texto
        text_columns = df.select_dtypes(include=['object']).columns

        for col in text_columns:
            df[col] = df[col].astype(str).apply(
                lambda x: InputSanitizer.sanitize_sql_input(x)
            )

        return df