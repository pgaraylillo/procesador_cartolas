from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd

@dataclass
class DataStore:
    root: Path = field(default_factory=lambda: Path('data'))
    labeled_file: str = 'labeled_transactions.csv'

    def __post_init__(self):
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_labeled(self, df: pd.DataFrame):
        path = self.root / self.labeled_file
        if path.exists():
            old = pd.read_csv(path)
            combined = pd.concat([old, df], ignore_index=True).drop_duplicates(subset=['date','description','amount'])
            combined.to_csv(path, index=False)
        else:
            df.to_csv(path, index=False)

    def load_labeled(self) -> pd.DataFrame:
        path = self.root / self.labeled_file
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame()
