# app/utils/validators.py - Sistema de validación robusto
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import re
from datetime import datetime, date
from pathlib import Path
import hashlib


class DataValidator:
    """Validador completo de datos financieros"""

    @staticmethod
    def validate_rut(rut: str) -> Tuple[bool, str]:
        """Valida RUT chileno con mensaje de error detallado"""
        if not rut or pd.isna(rut):
            return False, "RUT vacío"

        rut_str = str(rut).strip().upper()

        # Remove formatting
        clean_rut = re.sub(r'[.\s]', '', rut_str)

        # Check basic format
        if not re.match(r'^\d{7,8}-[0-9K]$', clean_rut):
            return False, "Formato inválido (debe ser XXXXXXXX-X)"

        # Extract parts
        rut_number = clean_rut[:-2]
        dv = clean_rut[-1]

        # Calculate verification digit
        try:
            total = 0
            multiplier = 2

            for digit in reversed(rut_number):
                total += int(digit) * multiplier
                multiplier = 9 if multiplier == 7 else multiplier + 1

            remainder = total % 11
            expected_dv = 'K' if remainder == 10 else str(11 - remainder) if remainder > 1 else '0'

            if dv != expected_dv:
                return False, f"Dígito verificador incorrecto (esperado: {expected_dv})"

            return True, "RUT válido"

        except Exception as e:
            return False, f"Error validando RUT: {str(e)}"

    @staticmethod
    def validate_bank_transaction(row: pd.Series) -> Dict[str, Any]:
        """Valida una transacción bancaria individual"""
        issues = []
        warnings = []

        # Required fields
        required_fields = ['date', 'description', 'amount']
        for field in required_fields:
            if field not in row or pd.isna(row[field]) or str(row[field]).strip() == '':
                issues.append(f"Campo requerido vacío: {field}")

        # Date validation
        if 'date' in row and not pd.isna(row['date']):
            try:
                parsed_date = pd.to_datetime(row['date'])

                # Check if date is reasonable
                current_year = datetime.now().year
                if parsed_date.year < 2000 or parsed_date.year > current_year + 1:
                    warnings.append(f"Fecha inusual: {parsed_date.strftime('%Y')}")

                # Check if date is in future
                if parsed_date.date() > datetime.now().date():
                    warnings.append("Fecha en el futuro")

            except:
                issues.append("Fecha no parseable")

        # Amount validation
        if 'amount' in row and not pd.isna(row['amount']):
            try:
                amount = float(row['amount'])

                # Check for extreme values
                if abs(amount) > 1_000_000_000:  # 1 billion
                    warnings.append("Monto extremadamente alto")
                elif amount == 0:
                    warnings.append("Monto es cero")

            except:
                issues.append("Monto no numérico")

        # Description validation
        if 'description' in row and not pd.isna(row['description']):
            desc = str(row['description']).strip()
            if len(desc) < 3:
                warnings.append("Descripción muy corta")
            elif len(desc) > 200:
                warnings.append("Descripción muy larga")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }

    @staticmethod
    def validate_bank_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
        """Valida DataFrame completo de transacciones bancarias"""
        if df.empty:
            return {
                'valid': False,
                'issues': ['DataFrame vacío'],
                'warnings': [],
                'row_validations': [],
                'summary': {'total_rows': 0, 'valid_rows': 0, 'invalid_rows': 0}
            }

        overall_issues = []
        overall_warnings = []
        row_validations = []

        # Check required columns
        required_cols = ['date', 'description', 'amount']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            overall_issues.append(f"Columnas faltantes: {missing_cols}")

        # Check for completely empty columns
        empty_cols = [col for col in df.columns if df[col].isna().all()]
        if empty_cols:
            overall_warnings.append(f"Columnas completamente vacías: {empty_cols}")

        # Validate each row
        valid_rows = 0
        for idx, row in df.iterrows():
            row_validation = DataValidator.validate_bank_transaction(row)
            row_validation['row_index'] = idx
            row_validations.append(row_validation)

            if row_validation['valid']:
                valid_rows += 1

        # Duplicate detection
        if not missing_cols:  # Only if we have required columns
            potential_duplicates = DataValidator._find_potential_duplicates(df)
            if potential_duplicates:
                overall_warnings.append(f"Posibles duplicados encontrados: {len(potential_duplicates)} pares")

        # Data quality checks
        data_quality = DataValidator._analyze_data_quality(df)
        overall_warnings.extend(data_quality['warnings'])

        return {
            'valid': len(overall_issues) == 0,
            'issues': overall_issues,
            'warnings': overall_warnings,
            'row_validations': row_validations,
            'summary': {
                'total_rows': len(df),
                'valid_rows': valid_rows,
                'invalid_rows': len(df) - valid_rows,
                'completion_rate': f"{valid_rows / len(df) * 100:.1f}%" if len(df) > 0 else "0%"
            },
            'data_quality': data_quality
        }

    @staticmethod
    def validate_kame_document(row: pd.Series) -> Dict[str, Any]:
        """Valida documento KAME individual"""
        issues = []
        warnings = []

        # RUT validation if present
        if 'rut' in row and not pd.isna(row['rut']) and str(row['rut']).strip():
            is_valid, message = DataValidator.validate_rut(row['rut'])
            if not is_valid:
                issues.append(f"RUT inválido: {message}")

        # Amount validation
        amount_fields = ['total', 'neto', 'iva']
        for field in amount_fields:
            if field in row and not pd.isna(row[field]):
                try:
                    amount = float(row[field])
                    if amount < 0:
                        warnings.append(f"{field} negativo")
                    elif amount > 100_000_000:  # 100M CLP
                        warnings.append(f"{field} muy alto: ${amount:,.0f}")
                except:
                    issues.append(f"{field} no numérico")

        # Tax consistency check (if we have neto and iva)
        if all(field in row for field in ['neto', 'iva', 'total']):
            try:
                neto = float(row['neto']) if not pd.isna(row['neto']) else 0
                iva = float(row['iva']) if not pd.isna(row['iva']) else 0
                total = float(row['total']) if not pd.isna(row['total']) else 0

                expected_total = neto + iva
                if abs(total - expected_total) > 1:  # Allow 1 peso difference for rounding
                    warnings.append(f"Inconsistencia: Total={total} vs Neto+IVA={expected_total}")

            except:
                pass  # Skip if can't convert to numbers

        # Date validation if present
        if 'fecha' in row or 'date' in row:
            date_field = 'fecha' if 'fecha' in row else 'date'
            if not pd.isna(row[date_field]):
                try:
                    parsed_date = pd.to_datetime(row[date_field])
                    if parsed_date.year < 2000 or parsed_date.year > datetime.now().year + 1:
                        warnings.append(f"Fecha inusual: {parsed_date.strftime('%Y')}")
                except:
                    issues.append("Fecha no parseable")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }

    @staticmethod
    def validate_kame_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
        """Valida DataFrame completo de documentos KAME"""
        if df.empty:
            return {
                'valid': False,
                'issues': ['DataFrame KAME vacío'],
                'warnings': [],
                'summary': {'total_rows': 0, 'valid_rows': 0}
            }

        overall_issues = []
        overall_warnings = []
        row_validations = []

        # Expected columns (flexible)
        expected_cols = ['fecha', 'total', 'folio', 'rut']
        present_cols = [col for col in expected_cols if col in df.columns]
        missing_cols = [col for col in expected_cols if col not in df.columns]

        if len(present_cols) < 2:
            overall_issues.append("Muy pocas columnas reconocidas en KAME")

        if missing_cols:
            overall_warnings.append(f"Columnas KAME esperadas no encontradas: {missing_cols}")

        # Validate each row
        valid_rows = 0
        for idx, row in df.iterrows():
            row_validation = DataValidator.validate_kame_document(row)
            row_validation['row_index'] = idx
            row_validations.append(row_validation)

            if row_validation['valid']:
                valid_rows += 1

        return {
            'valid': len(overall_issues) == 0,
            'issues': overall_issues,
            'warnings': overall_warnings,
            'row_validations': row_validations,
            'summary': {
                'total_rows': len(df),
                'valid_rows': valid_rows,
                'invalid_rows': len(df) - valid_rows,
                'present_columns': present_cols,
                'missing_columns': missing_cols
            }
        }

    @staticmethod
    def validate_file_upload(file_path: Path, max_size_mb: int = 50) -> Dict[str, Any]:
        """Valida archivo subido"""
        issues = []
        warnings = []

        if not file_path.exists():
            return {
                'valid': False,
                'issues': ['Archivo no existe'],
                'warnings': []
            }

        # Size check
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            issues.append(f"Archivo muy grande: {size_mb:.1f}MB (máximo: {max_size_mb}MB)")
        elif size_mb > max_size_mb * 0.8:
            warnings.append(f"Archivo grande: {size_mb:.1f}MB")

        # Extension check
        allowed_extensions = ['.xlsx', '.xls', '.csv']
        if file_path.suffix.lower() not in allowed_extensions:
            issues.append(f"Extensión no soportada: {file_path.suffix}")

        # Try to read file
        try:
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, nrows=5)
            else:
                df = pd.read_excel(file_path, nrows=5)

            if df.empty:
                warnings.append("Archivo parece vacío")
            elif len(df.columns) < 3:
                warnings.append(f"Pocas columnas: {len(df.columns)}")

        except Exception as e:
            issues.append(f"Error leyendo archivo: {str(e)}")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'file_info': {
                'size_mb': size_mb,
                'extension': file_path.suffix,
                'name': file_path.name
            }
        }

    @staticmethod
    def _find_potential_duplicates(df: pd.DataFrame) -> List[Tuple[int, int]]:
        """Encuentra potenciales duplicados en transacciones"""
        if 'date' not in df.columns or 'amount' not in df.columns or 'description' not in df.columns:
            return []

        duplicates = []

        # Group by date and amount for faster comparison
        for group_key, group in df.groupby(['date', 'amount']):
            if len(group) > 1:
                # Check description similarity within group
                for i, row1 in group.iterrows():
                    for j, row2 in group.iterrows():
                        if i < j:  # Avoid duplicate pairs
                            desc1 = str(row1['description']).lower().strip()
                            desc2 = str(row2['description']).lower().strip()

                            # Simple similarity check
                            if desc1 == desc2 or (len(desc1) > 10 and desc1 in desc2) or (
                                    len(desc2) > 10 and desc2 in desc1):
                                duplicates.append((i, j))

        return duplicates

    @staticmethod
    def _analyze_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
        """Analiza calidad general de los datos"""
        warnings = []
        stats = {}

        if df.empty:
            return {'warnings': ['DataFrame vacío'], 'stats': stats}

        # Completeness analysis
        for col in df.columns:
            null_pct = df[col].isna().sum() / len(df) * 100
            stats[f'{col}_completeness'] = f"{100 - null_pct:.1f}%"

            if null_pct > 50:
                warnings.append(f"Columna {col} más de 50% vacía")
            elif null_pct > 20:
                warnings.append(f"Columna {col} tiene {null_pct:.1f}% valores faltantes")

        # Date range analysis
        if 'date' in df.columns:
            try:
                dates = pd.to_datetime(df['date'], errors='coerce')
                valid_dates = dates.dropna()

                if len(valid_dates) > 0:
                    date_range_days = (valid_dates.max() - valid_dates.min()).days
                    stats['date_range_days'] = date_range_days
                    stats['earliest_date'] = valid_dates.min().strftime('%Y-%m-%d')
                    stats['latest_date'] = valid_dates.max().strftime('%Y-%m-%d')

                    if date_range_days > 365 * 2:  # More than 2 years
                        warnings.append(f"Rango de fechas muy amplio: {date_range_days} días")
            except:
                warnings.append("Error analizando fechas")

        # Amount analysis
        if 'amount' in df.columns:
            try:
                amounts = pd.to_numeric(df['amount'], errors='coerce')
                valid_amounts = amounts.dropna()

                if len(valid_amounts) > 0:
                    stats['amount_range'] = f"${valid_amounts.min():,.0f} a ${valid_amounts.max():,.0f}"
                    stats['average_amount'] = f"${valid_amounts.mean():,.0f}"

                    # Check for suspiciously round numbers
                    round_numbers = valid_amounts[valid_amounts % 1000 == 0]
                    if len(round_numbers) / len(valid_amounts) > 0.3:
                        warnings.append("Muchos montos redondos (posibles estimaciones)")
            except:
                warnings.append("Error analizando montos")

        return {
            'warnings': warnings,
            'stats': stats
        }


class FileValidator:
    """Validador específico de archivos"""

    @staticmethod
    def validate_excel_structure(file_path: Path) -> Dict[str, Any]:
        """Valida estructura específica de Excel bancario"""
        try:
            # Read first few rows to detect structure
            df = pd.read_excel(file_path, nrows=50)

            issues = []
            suggestions = []

            # Look for common Santander patterns
            santander_patterns = ['cartola', 'monto', 'descripción', 'fecha', 'cargo', 'abono']

            found_patterns = 0
            for pattern in santander_patterns:
                if any(pattern.lower() in str(col).lower() for col in df.columns):
                    found_patterns += 1
                if df.astype(str).apply(lambda x: x.str.lower().str.contains(pattern, na=False)).any().any():
                    found_patterns += 1

            if found_patterns < 3:
                suggestions.append("Archivo podría no ser una cartola de Santander válida")

            # Check for merged cells or complex formatting
            if len(df.columns) > 20:
                suggestions.append("Archivo tiene muchas columnas - podría tener formato complejo")

            # Check for completely empty rows
            empty_rows = df.isna().all(axis=1).sum()
            if empty_rows > len(df) * 0.5:
                issues.append("Más del 50% de las filas están vacías")

            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'suggestions': suggestions,
                'santander_score': found_patterns,
                'structure_info': {
                    'total_rows': len(df),
                    'total_columns': len(df.columns),
                    'empty_rows': empty_rows
                }
            }

        except Exception as e:
            return {
                'valid': False,
                'issues': [f"Error leyendo Excel: {str(e)}"],
                'suggestions': ["Verifica que el archivo no esté corrupto o protegido"],
                'santander_score': 0
            }

    @staticmethod
    def get_file_hash(file_path: Path) -> str:
        """Genera hash único para archivo"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
