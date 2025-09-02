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

        # Monto: miles '.' y coma decimal ','
        if "amount" in out.columns:
            amt = (out["amount"]
                   .str.replace("\u00a0", "", regex=False)
                   .str.replace(" ", "", regex=False)
                   .str.replace(".", "", regex=False)
                   .str.replace(",", ".", regex=False))
            out["amount"] = pd.to_numeric(amt, errors="coerce")

        # Signo + texto normalizado
        if "debit_credit" in out.columns:
            dc = out["debit_credit"].str.upper().str.strip()
            sign = dc.map({"CARGO": -1, "ABONO": 1, "C": -1, "A": 1}).fillna(1)
            out["amount"] = out["amount"] * sign
            out["debit_credit"] = dc.replace({"A": "ABONO", "C": "CARGO"})

        # Fecha
        if "date" in out.columns:
            out["date"] = pd.to_datetime(out["date"], errors="coerce", dayfirst=True).dt.strftime("%Y-%m-%d")

        # Renombrar a español y ordenar columnas
        out = out.rename(columns={
            "date": "Fecha",
            "description": "Descripción",
            "amount": "Monto",
            "debit_credit": "ABONO/CARGO",
        })[["Fecha", "Descripción", "Monto", "ABONO/CARGO"]]

        # --- 4) Filtros nucleares ---
        # 4.1) Eliminar resumen de saldos (filas sin abono/cargo válido)
        out = out[out["ABONO/CARGO"].isin(["ABONO", "CARGO"])]

        # 4.2) Deduplicación inteligente de COMISIONES:
        #      Si en el MISMO día y MISMA descripción existen dos o más filas que parecen comisiones,
        #      conserva la de mayor |Monto| y elimina las otras (esto remueve el duplicado del bloque "detalle de comisiones").
        comisiones_pat = r"(?i)\bcom\.?\s*manten|comisi[oó]n|gastos?\s+bancarios?|cargo[s]?\s+por\s+servicio|mantenci[oó]n"
        is_commission = out["Descripción"].str.contains(comisiones_pat, na=False)

        # Normaliza descripción para agrupar de forma robusta (minúscula y espacios comprimidos)
        desc_norm = (out["Descripción"]
                     .str.lower()
                     .str.replace(r"\s+", " ", regex=True)
                     .str.strip())
        out = out.assign(_is_comm=is_commission, _desc_norm=desc_norm, _abs=out["Monto"].abs())

        # Para grupos de comisiones: quedarnos con idx de mayor |Monto|
        keep_index = out.index.to_series()
        if out["_is_comm"].any():
            grp = out[out["_is_comm"]].groupby(["Fecha", "_desc_norm"], as_index=False)["_abs"].idxmax()
            idx_keep_comm = set(grp["_abs"].tolist())
            idx_all_comm = set(out[out["_is_comm"]].index.tolist())
            idx_drop_comm = idx_all_comm - idx_keep_comm
            keep_index = keep_index.drop(list(idx_drop_comm), errors="ignore")

        out = out.loc[keep_index].drop(columns=["_is_comm", "_desc_norm", "_abs"], errors="ignore")

        # 4.3) Quitar duplicados exactos (por seguridad)
        out = out.drop_duplicates(subset=["Fecha", "Descripción", "Monto", "ABONO/CARGO"], keep="first")

        # 4.4) Filtrar filas sin monto/fecha/descripcion
        out = out.dropna(subset=["Monto"])
        out = out[out["Fecha"].notna() & out["Descripción"].notna()]
        out = out[(out["Fecha"] != "") & (out["Descripción"] != "")]

        out = out.reset_index(drop=True)
        return out