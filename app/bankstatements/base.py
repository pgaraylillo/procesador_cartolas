from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd

class BankStatementParser(ABC):
    @abstractmethod
    def parse(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a normalized dataframe with columns:
        [date, description, amount, debit_credit, document_number, branch]."""
        pass
