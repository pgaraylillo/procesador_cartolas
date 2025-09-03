# app/utils/exporters.py
import pandas as pd
from pathlib import Path
from datetime import datetime


class ReportExporter:
    """Exporta reportes en diferentes formatos"""

    @staticmethod
    def export_reconciliation_excel(
            bank_df: pd.DataFrame,
            kame_df: pd.DataFrame,
            unbacked_df: pd.DataFrame,
            output_path: Path
    ):
        """Exporta reporte de conciliación completo a Excel"""

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Resumen ejecutivo
            summary = {
                'Métrica': [
                    'Total Gastos Bancarios',
                    'Gastos Respaldados',
                    'Gastos Sin Respaldo',
                    '% Respaldo',
                    'Monto Sin Respaldo'
                ],
                'Valor': [
                    len(bank_df[bank_df['amount'] < 0]),
                    len(bank_df[bank_df['amount'] < 0]) - len(unbacked_df),
                    len(unbacked_df),
                    f"{((len(bank_df[bank_df['amount'] < 0]) - len(unbacked_df)) / len(bank_df[bank_df['amount'] < 0]) * 100):.1f}%",
                    f"${unbacked_df['amount'].sum():,.0f}" if len(unbacked_df) > 0 else "$0"
                ]
            }
            pd.DataFrame(summary).to_excel(writer, sheet_name='Resumen', index=False)

            # Gastos sin respaldo
            if len(unbacked_df) > 0:
                unbacked_export = unbacked_df.copy()
                if 'date' in unbacked_export.columns:
                    unbacked_export['date'] = pd.to_datetime(unbacked_export['date']).dt.strftime('%d/%m/%Y')
                unbacked_export.to_excel(writer, sheet_name='Sin Respaldo', index=False)

            # Datos KAME
            kame_df.to_excel(writer, sheet_name='Documentos KAME', index=False)

            # Gastos bancarios
            bank_expenses = bank_df[bank_df['amount'] < 0]
            bank_expenses.to_excel(writer, sheet_name='Gastos Bancarios', index=False)
