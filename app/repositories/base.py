# app/repositories/base.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class BaseRepository(ABC):
    @abstractmethod
    def find_by_id(self, id: int) -> Optional[Dict]:
        pass

    @abstractmethod
    def find_all(self) -> List[Dict]:
        pass

    @abstractmethod
    def save(self, data: Dict) -> int:
        pass

    @abstractmethod
    def update(self, id: int, data: Dict) -> bool:
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        pass