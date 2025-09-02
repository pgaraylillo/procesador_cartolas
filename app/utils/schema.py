from typing import Dict
import pandas as pd

# Mapeo a nombres canónicos internos
CANONICAL_SCHEMA = {
    # español -> canónico
    "monto": "amount",
    "descripción movimiento": "description",
    "descripcion movimiento": "description",
    "fecha": "date",
    "n° documento": "document_number",
    "n°  documento": "document_number",
    "n° documento ": "document_number",
    "sucursal": "branch",
    "cargo/abono": "debit_credit",
    # headers en español finales del parser:
    "descripción": "description",
    "abono/cargo": "debit_credit",
}

# Para convertir de canónico a español (cuando exportes/descargues)
SPANISH_HEADERS = {
    "date": "Fecha",
    "description": "Descripción",
    "amount": "Monto",
    "debit_credit": "ABONO/CARGO",
}

def normalize_headers(cols) -> Dict[str, str]:
    """Mapea headers variados hacia formato canónico."""
    mapping = {}
    for c in cols:
        key = str(c).strip().lower()
        mapping[c] = CANONICAL_SCHEMA.get(key, key.replace(" ", "_"))
    return mapping

def to_canonical(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte DataFrame con headers en español o variados a canónicos."""
    if df is None or df.empty:
        return df
    rename_map = normalize_headers(df.columns)
    out = df.rename(columns=rename_map).copy()
    # normalización tipográfica
    for c in out.columns:
        if out[c].dtype == object:
            out[c] = out[c].astype(str).str.strip()
    return out

def to_spanish(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte DataFrame canónico a headers en español en el orden correcto."""
    if df is None or df.empty:
        return df
    out = df.rename(columns=SPANISH_HEADERS)
    cols = ["Fecha", "Descripción", "Monto", "ABONO/CARGO"]
    cols = [c for c in cols if c in out.columns]
    return out[cols]