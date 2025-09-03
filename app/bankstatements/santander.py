# app/bankstatements/santander.py
from __future__ import annotations
import pandas as pd
from .base import BankStatementParser


class SantanderParser(BankStatementParser):
    def parse(self, df: pd.DataFrame) -> pd.DataFrame:
        # --- 1) Detectar encabezado real (busca 'MONTO' y 'DESCRIP') ---
        df_nohdr = df.copy()
        df_nohdr.columns = range(len(df_nohdr.columns))
        header_idx = None
        for i in range(min(50, len(df_nohdr))):
            row = df_nohdr.iloc[i].astype(str).str.strip().str.lower()
            if row.str.contains("monto").any() and row.str.contains("descrip").any():
                header_idx = i
                break

        if header_idx is None:
            working = df.copy()
        else:
            headers = df_nohdr.iloc[header_idx].astype(str).str.strip().tolist()
            working = df_nohdr.iloc[header_idx + 1:].reset_index(drop=True).copy()
            working.columns = headers

        # --- 2) Normalizar nombres internos ---
        mapping = {
            "monto": "amount",
            "descripción movimiento": "description",
            "descripcion movimiento": "description",
            "fecha": "date",
            "n° documento": "document_number",
            "n°  documento": "document_number",
            "n° documento ": "document_number",
            "sucursal": "branch",
            "cargo/abono": "debit_credit",
        }
        working.columns = [mapping.get(str(c).strip().lower(), str(c).strip().lower()) for c in working.columns]

        # --- 3) Mantener columnas necesarias y limpiar ---
        cols = [c for c in ["date", "description", "amount", "debit_credit"] if c in working.columns]
        out = working[cols].copy()

        for c in out.columns:
            out[c] = out[c].astype(str).str.strip()

        # --- 4) Limpiar y convertir montos (formato chileno: miles con '.' y decimal con ',') ---
        if "amount" in out.columns:
            # Limpiar espacios no-break y espacios normales
            amt = (out["amount"]
                   .str.replace("\u00a0", "", regex=False)  # Espacio no-break
                   .str.replace(" ", "", regex=False)  # Espacios normales
                   .str.replace(".", "", regex=False)  # Quitar separadores de miles
                   .str.replace(",", ".", regex=False))  # Coma decimal a punto

            # Convertir a numérico
            out["amount"] = pd.to_numeric(amt, errors="coerce")

        # --- 5) Aplicar signos CORRECTOS y normalizar texto ---
        if "debit_credit" in out.columns and "amount" in out.columns:
            # Limpiar y normalizar la columna CARGO/ABONO
            dc = out["debit_credit"].str.upper().str.strip()
            dc = dc.replace({"A": "ABONO", "C": "CARGO"})

            # Aplicar signos: CARGO = negativo (-), ABONO = positivo (+)
            sign_mapping = {"CARGO": -1, "ABONO": 1}
            signs = dc.map(sign_mapping).fillna(1)  # Default a positivo si no se reconoce

            # CRÍTICO: Aplicar signos a los montos
            out["amount"] = out["amount"].abs() * signs  # abs() por seguridad, luego aplicar signo correcto
            out["debit_credit"] = dc

        # --- 6) Procesar fechas ---
        if "date" in out.columns:
            out["date"] = pd.to_datetime(out["date"], errors="coerce", dayfirst=True)
            # Convertir a string en formato ISO para consistencia
            out["date"] = out["date"].dt.strftime("%Y-%m-%d")

        # --- 7) Filtros de limpieza ---

        # 7.1) Eliminar filas sin tipo ABONO/CARGO válido
        if "debit_credit" in out.columns:
            out = out[out["debit_credit"].isin(["ABONO", "CARGO"])]

        # 7.2) Deduplicación inteligente de COMISIONES
        if len(out) > 0:
            comisiones_pat = r"(?i)\bcom\.?\s*manten|comisi[oó]n|gastos?\s+bancarios?|cargo[s]?\s+por\s+servicio|mantenci[oó]n"
            is_commission = out["description"].str.contains(comisiones_pat, na=False)

            if is_commission.any():
                # Normalizar descripción para agrupar
                desc_norm = (out["description"]
                             .str.lower()
                             .str.replace(r"\s+", " ", regex=True)
                             .str.strip())
                out = out.assign(_is_comm=is_commission, _desc_norm=desc_norm, _abs=out["amount"].abs())

                # Para grupos de comisiones: mantener solo la de mayor |Monto|
                keep_index = out.index.to_series()
                grp = out[out["_is_comm"]].groupby(["date", "_desc_norm"], as_index=False)["_abs"].idxmax()
                idx_keep_comm = set(grp["_abs"].tolist()) if len(grp) > 0 else set()
                idx_all_comm = set(out[out["_is_comm"]].index.tolist())
                idx_drop_comm = idx_all_comm - idx_keep_comm

                if idx_drop_comm:
                    keep_index = keep_index.drop(list(idx_drop_comm), errors="ignore")

                out = out.loc[keep_index].drop(columns=["_is_comm", "_desc_norm", "_abs"], errors="ignore")

        # 7.3) Eliminar duplicados exactos
        duplicate_cols = ["date", "description", "amount", "debit_credit"]
        available_cols = [col for col in duplicate_cols if col in out.columns]
        if available_cols:
            out = out.drop_duplicates(subset=available_cols, keep="first")

        # 7.4) Filtrar filas con datos esenciales faltantes
        out = out.dropna(subset=["amount"])
        if "date" in out.columns:
            out = out[out["date"].notna() & (out["date"] != "")]
        if "description" in out.columns:
            out = out[out["description"].notna() & (out["description"] != "")]

        # --- 8) Renombrar a español y formatear para presentación ---
        column_rename = {
            "date": "Fecha",
            "description": "Descripción",
            "amount": "Monto",
            "debit_credit": "ABONO/CARGO",
        }

        out = out.rename(columns=column_rename)

        # Ordenar columnas
        final_cols = ["Fecha", "Descripción", "Monto", "ABONO/CARGO"]
        out = out[[col for col in final_cols if col in out.columns]]

        out = out.reset_index(drop=True)
        return out

    def format_for_display(self, df: pd.DataFrame) -> pd.DataFrame:
        """Formatea DataFrame para mostrar en interfaz con formato chileno"""
        if df.empty:
            return df

        display_df = df.copy()

        # Formatear montos con separadores de miles chilenos
        if 'Monto' in display_df.columns:
            display_df['Monto_Formateado'] = display_df['Monto'].apply(self._format_chilean_currency)

        return display_df

    def _format_chilean_currency(self, amount) -> str:
        """Formatea monto en formato chileno: $123.456 o -$123.456"""
        try:
            amount = float(amount)
            if amount < 0:
                return f"-${abs(amount):,.0f}".replace(",", ".")
            else:
                return f"${amount:,.0f}".replace(",", ".")
        except:
            return str(amount)