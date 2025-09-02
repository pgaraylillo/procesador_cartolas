from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
from app.utils.schema import to_canonical  # <-- importa

@dataclass
class DataStore:
    root: Path = field(default_factory=lambda: Path('data'))
    labeled_file: str = 'labeled_transactions.csv'

    def __post_init__(self):
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_labeled(self, df: pd.DataFrame):
        # Asegura canónico
        df = to_canonical(df).copy()
        # columnas mínimas
        needed = ["date", "description", "amount", "category"]
        for c in needed:
            if c not in df.columns:
                raise ValueError(f"Falta columna requerida en etiquetas: {c}")
        path = self.root / self.labeled_file
        if path.exists():
            old = pd.read_csv(path)
            old = to_canonical(old)
            combined = pd.concat([old, df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["date","description","amount","category"])
            combined.to_csv(path, index=False)
        else:
            df.to_csv(path, index=False)

    def load_labeled(self) -> pd.DataFrame:
        path = self.root / self.labeled_file
        if path.exists():
            df = pd.read_csv(path)
            return to_canonical(df)
        return pd.DataFrame()