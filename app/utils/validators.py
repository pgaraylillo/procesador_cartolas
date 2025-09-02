# app/utils/validators.py - Validadores simplificados y prácticos
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import re
from datetime import datetime


class DataValidator:
    """Validador básico para datos financieros"""

    @staticmethod
    def validate_bank_dataframe(df: pd.DataFrame) -> Dict:
        """Valida DataFrame de transacciones bancarias"""
        if df.empty:
            return {
                'valid': False,
                'issues': ['DataFrame vacío'],
                'warnings': [],
                'summary': {'total_rows': 0, 'valid_rows': 0}
            }

        issues = []
        warnings = []

        # Verificar columnas esperadas
        expected_cols = ['Fecha', 'Descripción', 'Monto']
        missing_cols = [col for col in expected_cols if col not in df.columns]

        if missing_cols:
            issues.append(f"Columnas faltantes: {missing_cols}")

        # Verificar datos válidos
        valid_rows = 0
        for _, row in df.iterrows():
            row_valid = True

            # Verificar fecha
            if 'Fecha' in df.columns:
                try:
                    pd.to_datetime(row['Fecha'])
                except:
                    row_valid = False

            # Verificar monto
            if 'Monto' in df.columns:
                try:
                    float(row['Monto'])
                except:
                    row_valid = False

            # Verificar descripción
            if 'Descripción' in df.columns:
                if pd.isna(row['Descripción']) or str(row['Descripción']).strip() == '':
                    row_valid = False

            if row_valid:
                valid_rows += 1

        # Warnings por calidad de datos
        if valid_rows < len(df) * 0.9:
            warnings.append(f"Calidad de datos baja: solo {valid_rows}/{len(df)} filas válidas")

        # Verificar duplicados potenciales
        if not missing_cols and len(df) > len(df.drop_duplicates(subset=expected_cols)):
            warnings.append("Posibles transacciones duplicadas detectadas")

        return {
            'valid': len(issues) == 0 and valid_rows > 0,
            'issues': issues,
            'warnings': warnings,
            'summary': {
                'total_rows': len(df),
                'valid_rows': valid_rows,
                'completion_rate': f"{valid_rows / len(df) * 100:.1f}%"
            }
        }

    @staticmethod
    def validate_kame_dataframe(df: pd.DataFrame) -> Dict:
        """Valida DataFrame de documentos KAME"""
        if df.empty:
            return {
                'valid': False,
                'issues': ['DataFrame KAME vacío'],
                'warnings': []
            }

        issues = []
        warnings = []

        # Buscar columnas relevantes (flexible)
        amount_cols = [col for col in df.columns if
                       any(word in col.lower() for word in ['total', 'monto', 'valor', 'neto'])]
        date_cols = [col for col in df.columns if any(word in col.lower() for word in ['fecha', 'date'])]

        if not amount_cols:
            warnings.append("No se encontraron columnas de monto reconocibles")

        if not date_cols:
            warnings.append("No se encontraron columnas de fecha reconocibles")

        # Verificar calidad de datos en columnas encontradas
        valid_rows = 0
        for _, row in df.iterrows():
            row_valid = True

            # Verificar montos
            if amount_cols:
                try:
                    amount_val = row[amount_cols[0]]
                    if pd.notna(amount_val):
                        float(str(amount_val).replace('.', '').replace(',', '.'))
                except:
                    row_valid = False

            # Verificar fechas
            if date_cols:
                try:
                    pd.to_datetime(row[date_cols[0]])
                except:
                    row_valid = False

            if row_valid:
                valid_rows += 1

        if valid_rows < len(df) * 0.8:
            warnings.append(f"Calidad de datos KAME baja: {valid_rows}/{len(df)} filas válidas")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'summary': {
                'total_rows': len(df),
                'valid_rows': valid_rows,
                'amount_columns': amount_cols[:3],  # Mostrar hasta 3
                'date_columns': date_cols[:3]
            }
        }

    @staticmethod
    def validate_labeled_data(df: pd.DataFrame) -> Dict:
        """Valida datos etiquetados para ML"""
        if df.empty:
            return {
                'valid': False,
                'issues': ['Sin datos etiquetados'],
                'suggestions': ['Etiqueta algunas transacciones primero']
            }

        issues = []
        warnings = []
        suggestions = []

        # Verificar columnas necesarias para ML
        required_ml_cols = ['description', 'category']
        missing_ml_cols = [col for col in required_ml_cols if col not in df.columns]

        if missing_ml_cols:
            issues.append(f"Faltan columnas para ML: {missing_ml_cols}")

        if 'category' in df.columns:
            # Análisis de categorías
            category_counts = df['category'].value_counts()

            # Categorías con muy pocos ejemplos
            few_examples = category_counts[category_counts < 3]
            if len(few_examples) > 0:
                warnings.append(f"Categorías con pocos ejemplos (< 3): {list(few_examples.index)}")
                suggestions.append("Agrega más ejemplos a categorías con pocos datos")

            # Balance de clases
            if category_counts.max() > category_counts.min() * 10:
                warnings.append("Desbalance significativo entre categorías")
                suggestions.append("Intenta balancear mejor las categorías")

        # Calidad de descripciones
        if 'description' in df.columns:
            short_descriptions = df[df['description'].str.len() < 10]
            if len(short_descriptions) > len(df) * 0.2:
                warnings.append("Muchas descripciones muy cortas")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'suggestions': suggestions,
            'ml_ready': len(issues) == 0 and len(df) >= 10,
            'category_stats': category_counts.to_dict() if 'category' in df.columns else {}
        }


class FileValidator:
    """Validador de archivos subidos"""

    @staticmethod
    def validate_file_upload(file_path: Path, max_size_mb: int = 50) -> Dict:
        """Valida archivo subido básicamente"""
        if not file_path.exists():
            return {
                'valid': False,
                'issues': ['Archivo no existe'],
                'warnings': []
            }

        issues = []
        warnings = []

        # Verificar tamaño
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            issues.append(f"Archivo muy grande: {size_mb:.1f}MB (máximo: {max_size_mb}MB)")
        elif size_mb > max_size_mb * 0.8:
            warnings.append(f"Archivo grande: {size_mb:.1f}MB")

        # Verificar extensión
        allowed_extensions = ['.xlsx', '.xls', '.csv']
        if file_path.suffix.lower() not in allowed_extensions:
            issues.append(f"Extensión no soportada: {file_path.suffix}")

        # Intentar leer archivo
        try:
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, nrows=5)
            else:
                df = pd.read_excel(file_path, nrows=5)

            if df.empty:
                warnings.append("Archivo parece estar vacío")
            elif len(df.columns) < 3:
                warnings.append(f"Pocas columnas detectadas: {len(df.columns)}")

        except Exception as e:
            issues.append(f"Error leyendo archivo: {str(e)[:100]}")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'file_info': {
                'size_mb': round(size_mb, 1),
                'extension': file_path.suffix,
                'name': file_path.name
            }
        }

    @staticmethod
    def validate_santander_format(df: pd.DataFrame) -> Dict:
        """Valida si el archivo parece ser una cartola Santander"""
        santander_indicators = [
            'cartola', 'monto', 'descripción', 'fecha', 'cargo', 'abono', 'santander'
        ]

        score = 0

        # Buscar indicadores en headers
        headers_text = ' '.join([str(col).lower() for col in df.columns])
        for indicator in santander_indicators:
            if indicator in headers_text:
                score += 1

        # Buscar indicadores en contenido (primeras filas)
        if len(df) > 0:
            content_text = ' '.join([str(val).lower() for val in df.iloc[:10].values.flatten() if pd.notna(val)])
            for indicator in santander_indicators:
                if indicator in content_text:
                    score += 0.5

        is_santander = score >= 2
        confidence = min(score / len(santander_indicators), 1.0)

        return {
            'is_santander_format': is_santander,
            'confidence': confidence,
            'score': score,
            'suggestions': [
                "Verifica que sea una cartola de Santander válida" if not is_santander else "Formato Santander detectado correctamente"
            ]
        }