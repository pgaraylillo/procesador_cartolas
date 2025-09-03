# app/kame/kame_report.py
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


@dataclass
class KameIntegrator:
    """Integrador para reportes KAME ERP

    Permite cargar reportes de KAME y conciliar con transacciones bancarias
    para identificar gastos sin respaldo documental.
    """

    def load(self, path: str) -> pd.DataFrame:
        """Carga archivo KAME (Excel o CSV)"""
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Archivo KAME no encontrado: {path}")

        try:
            if path.suffix.lower() == '.csv':
                df = pd.read_csv(path, dtype=str)
            else:
                # Intentar cargar Excel, posiblemente con múltiples hojas
                df = pd.read_excel(path, dtype=str, sheet_name=0)

            # Normalizar headers
            df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]

            # Limpiar y procesar campos monetarios
            amount_fields = ['total', 'neto', 'iva', 'monto', 'valor']
            for field in amount_fields:
                if field in df.columns:
                    df[field] = self._clean_amount_column(df[field])

            # Limpiar fechas
            date_fields = ['fecha', 'date', 'fecha_documento']
            for field in date_fields:
                if field in df.columns:
                    df[field] = pd.to_datetime(df[field], errors='coerce')

            return df

        except Exception as e:
            raise ValueError(f"Error cargando archivo KAME: {str(e)}")

    def _clean_amount_column(self, series: pd.Series) -> pd.Series:
        """Limpia columna de montos en formato chileno"""
        return (series.astype(str)
                .str.replace(r'[^\d.,\-]', '', regex=True)  # Solo números, puntos, comas y guiones
                .str.replace('.', '', regex=False)  # Remover separadores de miles
                .str.replace(',', '.', regex=False)  # Coma decimal a punto
                .pipe(pd.to_numeric, errors='coerce'))

    def find_unbacked_expenses(self,
                               bank_df: pd.DataFrame,
                               kame_df: pd.DataFrame,
                               tolerance_days: int = 5,
                               tolerance_amount: float = 0.05) -> pd.DataFrame:
        """Encuentra gastos bancarios sin respaldo en KAME

        Args:
            bank_df: DataFrame con transacciones bancarias
            kame_df: DataFrame con documentos KAME
            tolerance_days: Tolerancia en días para matching de fechas
            tolerance_amount: Tolerancia porcentual para matching de montos (0.05 = 5%)
        """

        # Filtrar solo gastos (montos negativos)
        expenses = bank_df[bank_df['Monto'] < 0].copy() if 'Monto' in bank_df.columns else bank_df.copy()

        if expenses.empty:
            return pd.DataFrame()

        # Preparar datos para matching
        expenses = self._prepare_bank_data_for_matching(expenses)
        kame_df = self._prepare_kame_data_for_matching(kame_df)

        if kame_df.empty:
            return expenses  # Todos sin respaldo si no hay datos KAME

        # Realizar matching
        matched_indices = set()

        for expense_idx, expense_row in expenses.iterrows():
            if self._find_kame_match(expense_row, kame_df, tolerance_days, tolerance_amount):
                matched_indices.add(expense_idx)

        # Retornar gastos sin match
        unbacked = expenses.loc[~expenses.index.isin(matched_indices)]
        return unbacked

    def _prepare_bank_data_for_matching(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepara datos bancarios para matching"""
        df = df.copy()

        # Mapear columnas comunes
        column_mapping = {
            'Monto': 'amount',
            'Fecha': 'date',
            'Descripción': 'description'
        }

        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df[new_col] = df[old_col]

        # Asegurar que amount sea positivo para matching
        if 'amount' in df.columns:
            df['amount_abs'] = df['amount'].abs()

        # Convertir fechas
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')

        return df

    def _prepare_kame_data_for_matching(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepara datos KAME para matching"""
        df = df.copy()

        # Buscar columnas de monto (flexible)
        amount_cols = [col for col in df.columns if any(word in col for word in ['total', 'monto', 'valor', 'neto'])]

        if amount_cols:
            # Usar la primera columna de monto encontrada
            df['amount'] = df[amount_cols[0]]

        # Buscar columnas de fecha
        date_cols = [col for col in df.columns if any(word in col for word in ['fecha', 'date'])]

        if date_cols:
            df['date'] = pd.to_datetime(df[date_cols[0]], errors='coerce')

        # Limpiar datos nulos
        df = df.dropna(subset=[col for col in ['amount', 'date'] if col in df.columns])

        return df

    def _find_kame_match(self,
                         expense_row: pd.Series,
                         kame_df: pd.DataFrame,
                         tolerance_days: int = 5,
                         tolerance_amount: float = 0.05) -> bool:
        """Busca match individual entre gasto bancario y documentos KAME"""

        expense_amount = expense_row.get('amount_abs', 0)
        expense_date = expense_row.get('date')

        if pd.isna(expense_amount) or pd.isna(expense_date):
            return False

        for _, kame_row in kame_df.iterrows():
            kame_amount = kame_row.get('amount', 0)
            kame_date = kame_row.get('date')

            if pd.isna(kame_amount) or pd.isna(kame_date):
                continue

            # Matching por monto con tolerancia
            amount_diff = abs(expense_amount - kame_amount)
            amount_tolerance = expense_amount * tolerance_amount

            if amount_diff <= amount_tolerance:
                # Matching por fecha con tolerancia
                date_diff = abs((expense_date - kame_date).days)

                if date_diff <= tolerance_days:
                    return True

        return False

    def generate_reconciliation_report(self,
                                       bank_df: pd.DataFrame,
                                       kame_df: pd.DataFrame) -> Dict:
        """Genera reporte completo de conciliación"""

        unbacked_expenses = self.find_unbacked_expenses(bank_df, kame_df)

        total_expenses = len(bank_df[bank_df['Monto'] < 0]) if 'Monto' in bank_df.columns else 0
        backed_expenses = total_expenses - len(unbacked_expenses)

        unbacked_amount = unbacked_expenses['Monto'].sum() if 'Monto' in unbacked_expenses.columns else 0
        total_expenses_amount = bank_df[bank_df['Monto'] < 0]['Monto'].sum() if 'Monto' in bank_df.columns else 0

        backing_rate = (backed_expenses / total_expenses * 100) if total_expenses > 0 else 0

        report = {
            'summary': {
                'total_expenses': total_expenses,
                'backed_expenses': backed_expenses,
                'unbacked_expenses': len(unbacked_expenses),
                'backing_rate_percent': round(backing_rate, 1),
                'unbacked_amount': unbacked_amount,
                'total_expenses_amount': total_expenses_amount
            },
            'unbacked_transactions': unbacked_expenses.to_dict('records') if not unbacked_expenses.empty else [],
            'recommendations': self._generate_recommendations(unbacked_expenses),
            'kame_stats': {
                'total_documents': len(kame_df),
                'date_range': self._get_date_range(kame_df) if not kame_df.empty else None
            }
        }

        return report

    def _generate_recommendations(self, unbacked_expenses: pd.DataFrame) -> List[str]:
        """Genera recomendaciones basadas en gastos sin respaldo"""
        recommendations = []

        if unbacked_expenses.empty:
            recommendations.append("✅ Excelente: Todos los gastos tienen respaldo documental")
            return recommendations

        unbacked_count = len(unbacked_expenses)
        unbacked_amount = abs(unbacked_expenses['Monto'].sum()) if 'Monto' in unbacked_expenses.columns else 0

        if unbacked_count > 0:
            recommendations.append(f"⚠️ Se encontraron {unbacked_count} gastos sin respaldo")

            if unbacked_amount > 1000000:  # > 1M CLP
                recommendations.append("🔴 Alto riesgo: Monto sin respaldo supera $1.000.000")
            elif unbacked_amount > 500000:  # > 500k CLP
                recommendations.append("🟡 Riesgo medio: Monto sin respaldo supera $500.000")

            # Análisis por descripción común
            if 'Descripción' in unbacked_expenses.columns:
                common_patterns = self._find_common_patterns(unbacked_expenses['Descripción'])
                if common_patterns:
                    recommendations.append(f"💡 Patrones frecuentes sin respaldo: {', '.join(common_patterns[:3])}")

        return recommendations

    def _find_common_patterns(self, descriptions: pd.Series) -> List[str]:
        """Encuentra patrones comunes en descripciones"""
        patterns = {}

        for desc in descriptions.astype(str):
            # Extraer palabras clave (más de 3 caracteres)
            words = re.findall(r'\b\w{4,}\b', desc.upper())
            for word in words:
                patterns[word] = patterns.get(word, 0) + 1

        # Retornar patrones más frecuentes
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
        return [pattern for pattern, count in sorted_patterns if count >= 2]

    def _get_date_range(self, df: pd.DataFrame) -> Optional[Dict[str, str]]:
        """Obtiene rango de fechas del DataFrame"""
        date_cols = [col for col in df.columns if 'fecha' in col.lower() or 'date' in col.lower()]

        if not date_cols:
            return None

        try:
            dates = pd.to_datetime(df[date_cols[0]], errors='coerce').dropna()
            if not dates.empty:
                return {
                    'earliest': dates.min().strftime('%Y-%m-%d'),
                    'latest': dates.max().strftime('%Y-%m-%d')
                }
        except:
            pass

        return None