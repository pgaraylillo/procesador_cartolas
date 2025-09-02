# app/utils/data_cleaner.py - Limpieza automática de datos
import pandas as pd
from typing import Dict, Any, Tuple


class DataCleaner:
    """Limpiador automático de datos con reglas configurables"""

    @staticmethod
    def clean_bank_dataframe(df: pd.DataFrame, aggressive: bool = False) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Limpia DataFrame bancario automáticamente"""
        if df.empty:
            return df, {'operations': [], 'rows_removed': 0, 'rows_modified': 0}

        original_rows = len(df)
        operations = []
        rows_modified = 0

        df_clean = df.copy()

        # 1. Remove completely empty rows
        empty_mask = df_clean.isna().all(axis=1)
        empty_count = empty_mask.sum()
        if empty_count > 0:
            df_clean = df_clean[~empty_mask]
            operations.append(f"Removed {empty_count} completely empty rows")

        # 2. Clean amount column
        if 'amount' in df_clean.columns:
            before_count = df_clean['amount'].notna().sum()

            # Handle Chilean number format
            df_clean['amount'] = (df_clean['amount']
                                  .astype(str)
                                  .str.replace('.', '', regex=False)  # Remove thousands separator
                                  .str.replace(',', '.', regex=False)  # Decimal separator
                                  .str.replace('$', '', regex=False)
                                  .str.replace(' ', '', regex=False))

            df_clean['amount'] = pd.to_numeric(df_clean['amount'], errors='coerce')

            after_count = df_clean['amount'].notna().sum()
            if before_count != after_count:
                operations.append(f"Cleaned amount column: {before_count} -> {after_count} valid values")
                rows_modified += before_count - after_count

        # 3. Clean date column
        if 'date' in df_clean.columns:
            before_count = df_clean['date'].notna().sum()
            df_clean['date'] = pd.to_datetime(df_clean['date'], errors='coerce', dayfirst=True)
            after_count = df_clean['date'].notna().sum()

            if before_count != after_count:
                operations.append(f"Cleaned date column: {before_count} -> {after_count} valid dates")
                rows_modified += before_count - after_count

        # 4. Clean description column
        if 'description' in df_clean.columns:
            # Trim whitespace and remove multiple spaces
            df_clean['description'] = (df_clean['description']
                                       .astype(str)
                                       .str.strip()
                                       .str.replace(r'\s+', ' ', regex=True))

            # Remove very short descriptions if aggressive
            if aggressive:
                short_desc_mask = df_clean['description'].str.len() < 3
                short_count = short_desc_mask.sum()
                if short_count > 0:
                    df_clean = df_clean[~short_desc_mask]
                    operations.append(f"Removed {short_count} rows with very short descriptions")

        # 5. Remove duplicates if aggressive
        if aggressive:
            duplicate_cols = ['date', 'description', 'amount']
            available_cols = [col for col in duplicate_cols if col in df_clean.columns]

            if len(available_cols) >= 2:
                before_dupe_count = len(df_clean)
                df_clean = df_clean.drop_duplicates(subset=available_cols, keep='first')
                after_dupe_count = len(df_clean)

                if before_dupe_count != after_dupe_count:
                    operations.append(f"Removed {before_dupe_count - after_dupe_count} duplicate transactions")

        # 6. Filter by valid required fields
        required_fields = ['date', 'amount', 'description']
        available_required = [field for field in required_fields if field in df_clean.columns]

        if available_required:
            before_filter = len(df_clean)
            df_clean = df_clean.dropna(subset=available_required)
            after_filter = len(df_clean)

            if before_filter != after_filter:
                operations.append(f"Removed {before_filter - after_filter} rows with missing required data")

        final_rows = len(df_clean)

        return df_clean, {
            'operations': operations,
            'rows_removed': original_rows - final_rows,
            'rows_modified': rows_modified,
            'original_rows': original_rows,
            'final_rows': final_rows,
            'cleanup_rate': f"{((original_rows - final_rows) / original_rows * 100):.1f}%" if original_rows > 0 else "0%"
        }