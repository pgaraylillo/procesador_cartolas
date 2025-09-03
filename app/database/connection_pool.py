# app/database/connection_pool.py
import sqlite3
import threading
from contextlib import contextmanager
from queue import Queue, Empty


class ConnectionPool:
    def __init__(self, database_path: str, max_connections: int = 10):
        self.database_path = database_path
        self.max_connections = max_connections
        self.pool = Queue(maxsize=max_connections)
        self.lock = threading.Lock()

        # Pre-crear conexiones
        for _ in range(max_connections):
            conn = self._create_connection()
            self.pool.put(conn)

    def _create_connection(self):
        conn = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
            timeout=30
        )
        # Configuraciones de performance
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA cache_size=10000;")
        return conn

    @contextmanager
    def get_connection(self):
        conn = None
        try:
            # Obtener conexión del pool
            conn = self.pool.get(timeout=10)
            yield conn
        except Empty:
            # Si no hay conexiones disponibles, crear una temporal
            conn = self._create_connection()
            yield conn
        finally:
            if conn and self.pool.qsize() < self.max_connections:
                self.pool.put(conn)
            elif conn:
                conn.close()