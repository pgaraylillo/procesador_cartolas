from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

@dataclass
class KameIntegrator:
    """Integrate Kame ERP exports (Excel/CSV) to match bank transactions.
    Expected columns include: RUT, Folio, Fecha, Neto, IVA, Total, Proveedor/Cliente, etc.
    """
    def load(self, path: str) -> pd.DataFrame:
        if path.lower().endswith('.csv'):
            df = pd.read_csv(path, dtype=str)
        else:
            df = pd.read_excel(path, dtype=str)
        # Normalize headers
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        # Create key columns for matching if available
        if 'total' in df.columns:
            df['total'] = (df['total']
                           .astype(str)
                           .str.replace('.', '', regex=False)
                           .str.replace(',', '.', regex=False))
        return df

    def find_unbacked_expenses(self, bank_df: pd.DataFrame, kame_df: pd.DataFrame) -> pd.DataFrame:
        """Identify negative amounts (expenses) without a matching doc in Kame by fuzzy amount/date/desc logic."""
        expenses = bank_df[bank_df['amount'] < 0].copy()
        # Round amounts to two decimals for matching
        expenses['abs_amount'] = expenses['amount'].abs().round(2)
        # Kame total as float
        if 'total' in kame_df.columns:
            kame_df = kame_df.copy()
            kame_df['total_float'] = pd.to_numeric(kame_df['total'], errors='coerce')
            kame_df['total_float'] = kame_df['total_float'].round(2)
        else:
            kame_df['total_float'] = float('nan')

        # Simple left-anti merge on amount; can later add date window and vendor string match
        merged = expenses.merge(
            kame_df[['total_float']],
            left_on='abs_amount', right_on='total_float', how='left', indicator=True
        )
        unbacked = merged[merged['_merge'] == 'left_only'].drop(columns=['total_float','_merge'])
        return unbacked
