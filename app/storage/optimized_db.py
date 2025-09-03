# app/storage/optimized_db.py
import sqlite3


class OptimizedDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self.setup_performance_settings()

    def setup_performance_settings(self):
        with sqlite3.connect(self.db_path) as conn:
            # WAL mode para mejor concurrencia
            conn.execute("PRAGMA journal_mode=WAL;")

            # Aumentar cache (en páginas de 4KB)
            conn.execute("PRAGMA cache_size=10000;")  # 40MB cache

            # Optimizar para velocidad vs durabilidad
            conn.execute("PRAGMA synchronous=NORMAL;")

            # Timeout más largo para escrituras
            conn.execute("PRAGMA busy_timeout=30000;")  # 30 segundos

            # Usar memoria para temp tables
            conn.execute("PRAGMA temp_store=MEMORY;")

            # Optimizar query planner
            conn.execute("PRAGMA optimize;")

# -- Índices compuestos para consultas comunes
# CREATE INDEX IF NOT EXISTS idx_transactions_date_amount ON transactions(date DESC, amount);
# CREATE INDEX IF NOT EXISTS idx_transactions_category_date ON transactions(category, date DESC);
# CREATE INDEX IF NOT EXISTS idx_transactions_description_fts ON transactions(description);
#
# -- Índice parcial para gastos
# CREATE INDEX IF NOT EXISTS idx_expenses_only ON transactions(date, amount) WHERE amount < 0;
#
# -- Estadísticas actualizadas
# ANALYZE;