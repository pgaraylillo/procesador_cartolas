from __future__ import annotations
import pandas as pd
from pathlib import Path
from .schema import normalize_headers

def read_statement_excel(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    df = pd.read_excel(path, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    # Normalize headers
    mapping = normalize_headers(df.columns)
    df = df.rename(columns=mapping)
    # Strip whitespace
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()
    return df

def ensure_dir(p: str | Path) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p
