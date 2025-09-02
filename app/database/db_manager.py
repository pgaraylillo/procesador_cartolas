# app/database/db_manager.py
import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re
from contextlib import contextmanager


class DatabaseManager:
    """Gestor de base de datos SQLite para la aplicación"""

    def __init__(self, db_path: str = "data/finance_app.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def init_database(self):
        """Inicializa las tablas de la base de datos"""
        with self.get_connection() as conn:
            # Tabla de categorías personalizadas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    color TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)

            # Tabla de contactos/RUTs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rut TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    alias TEXT,
                    contact_type TEXT DEFAULT 'proveedor',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)

            # Tabla de transacciones etiquetadas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS labeled_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    original_description TEXT,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    debit_credit TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabla de configuraciones de la app
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Índices para rendimiento
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON labeled_transactions(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_category ON labeled_transactions(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_contacts_rut ON contacts(rut)")

            conn.commit()

        # Insertar categorías por defecto si no existen
        self.insert_default_categories()
        self.insert_sample_contacts()

    @contextmanager
    def get_connection(self):
        """Context manager para conexiones a la base de datos"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
        try:
            yield conn
        finally:
            conn.close()

    def insert_default_categories(self):
        """Inserta categorías por defecto si no existen"""
        default_categories = [
            ('bordados', 'Gastos relacionados con textiles, hilos, máquinas de bordar'),
            ('contabilidad', 'Honorarios contables, Previred, SII, servicios tributarios'),
            ('servicios', 'Mantención, reparaciones, consultorías generales'),
            ('combustible', 'Bencina, petróleo, gastos de combustible'),
            ('alimentacion', 'Comida, restaurantes, supermercados'),
            ('tecnologia', 'Software, hardware, servicios digitales'),
            ('bancario', 'Comisiones, mantención de cuentas, servicios bancarios'),
            ('impuestos', 'Impuestos, contribuciones, patentes'),
            ('otros', 'Gastos que no encajan en otras categorías')
        ]

        with self.get_connection() as conn:
            for name, description in default_categories:
                conn.execute("""
                    INSERT OR IGNORE INTO categories (name, description) 
                    VALUES (?, ?)
                """, (name, description))
            conn.commit()

    def insert_sample_contacts(self):
        """Inserta algunos contactos de ejemplo"""
        sample_contacts = [
            ('10.503.375-3', 'Juan Pérez', 'Juan', 'proveedor'),
            ('14.671.670-9', 'María González', 'María', 'empleado'),
            ('76.293.338-1', 'Empresa ABC SPA', 'ABC', 'proveedor'),
            ('86.521.400-6', 'Servicios XYZ Ltda.', 'XYZ', 'proveedor')
        ]

        with self.get_connection() as conn:
            for rut, name, alias, contact_type in sample_contacts:
                conn.execute("""
                    INSERT OR IGNORE INTO contacts (rut, name, alias, contact_type) 
                    VALUES (?, ?, ?, ?)
                """, (rut, name, alias, contact_type))
            conn.commit()

    # === GESTIÓN DE CATEGORÍAS ===

    def get_categories(self, active_only: bool = True) -> List[Dict]:
        """Obtiene todas las categorías"""
        with self.get_connection() as conn:
            query = "SELECT * FROM categories"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY name"

            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]

    def add_category(self, name: str, description: str = None) -> bool:
        """Agrega una nueva categoría"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO categories (name, description) 
                    VALUES (?, ?)
                """, (name.lower().strip(), description))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Categoría ya existe

    def delete_category(self, name: str) -> bool:
        """Marca una categoría como inactiva"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE categories SET is_active = 0 
                WHERE name = ?
            """, (name,))
            conn.commit()
            return cursor.rowcount > 0

    # === GESTIÓN DE CONTACTOS ===

    def get_contacts(self, active_only: bool = True) -> List[Dict]:
        """Obtiene todos los contactos"""
        with self.get_connection() as conn:
            query = "SELECT * FROM contacts"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY name"

            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]

    def add_contact(self, rut: str, name: str, alias: str = None, contact_type: str = 'proveedor') -> bool:
        """Agrega un nuevo contacto"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO contacts (rut, name, alias, contact_type) 
                    VALUES (?, ?, ?, ?)
                """, (self._clean_rut(rut), name.strip(), alias, contact_type))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # RUT ya existe

    def find_contact_by_rut(self, rut: str) -> Optional[Dict]:
        """Busca un contacto por RUT"""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM contacts 
                WHERE rut = ? AND is_active = 1
            """, (self._clean_rut(rut),)).fetchone()

            return dict(row) if row else None

    def update_contact(self, rut: str, name: str = None, alias: str = None) -> bool:
        """Actualiza información de contacto"""
        with self.get_connection() as conn:
            if name:
                conn.execute("""
                    UPDATE contacts 
                    SET name = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE rut = ?
                """, (name, self._clean_rut(rut)))

            if alias:
                conn.execute("""
                    UPDATE contacts 
                    SET alias = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE rut = ?
                """, (alias, self._clean_rut(rut)))

            conn.commit()
            return True

    # === GESTIÓN DE TRANSACCIONES ETIQUETADAS ===

    def save_labeled_transactions(self, df: pd.DataFrame):
        """Guarda transacciones etiquetadas"""
        if df.empty:
            return

        with self.get_connection() as conn:
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO labeled_transactions 
                    (date, description, original_description, amount, category, debit_credit)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    row.get('date', ''),
                    row.get('description', ''),
                    row.get('original_description', row.get('description', '')),
                    row.get('amount', 0),
                    row.get('category', ''),
                    row.get('debit_credit', '')
                ))
            conn.commit()

    def get_labeled_transactions(self) -> pd.DataFrame:
        """Obtiene todas las transacciones etiquetadas"""
        with self.get_connection() as conn:
            query = """
                SELECT date, description, original_description, amount, category, debit_credit
                FROM labeled_transactions 
                ORDER BY date DESC
            """
            return pd.read_sql_query(query, conn)

    # === UTILIDADES ===

    def _clean_rut(self, rut: str) -> str:
        """Limpia formato de RUT"""
        if not rut:
            return ""

        # Remover puntos y guiones
        clean = re.sub(r'[.\s-]', '', str(rut))

        # Formato estándar: XXXXXXXX-X
        if len(clean) >= 8:
            return f"{clean[:-1]}-{clean[-1].upper()}"

        return clean

    def enhance_description_with_contacts(self, description: str) -> str:
        """Mejora descripción reemplazando RUTs por nombres"""
        if not description:
            return description

        # Buscar patrones de RUT en la descripción
        rut_pattern = r'\b(\d{7,8}[-.]?\w)\b'
        ruts_found = re.findall(rut_pattern, description)

        enhanced_description = description

        for rut in ruts_found:
            contact = self.find_contact_by_rut(rut)
            if contact:
                # Usar alias si existe, sino el nombre completo
                display_name = contact['alias'] if contact['alias'] else contact['name']

                # Reemplazar RUT por nombre en la descripción
                enhanced_description = enhanced_description.replace(
                    rut,
                    f"{display_name} ({rut})"
                )

        return enhanced_description

    def get_statistics(self) -> Dict:
        """Obtiene estadísticas generales"""
        with self.get_connection() as conn:
            stats = {}

            # Categorías
            stats['categories_count'] = conn.execute(
                "SELECT COUNT(*) FROM categories WHERE is_active = 1"
            ).fetchone()[0]

            # Contactos
            stats['contacts_count'] = conn.execute(
                "SELECT COUNT(*) FROM contacts WHERE is_active = 1"
            ).fetchone()[0]

            # Transacciones etiquetadas
            stats['labeled_transactions_count'] = conn.execute(
                "SELECT COUNT(*) FROM labeled_transactions"
            ).fetchone()[0]

            # Distribución por categoría
            category_dist = conn.execute("""
                SELECT category, COUNT(*) as count
                FROM labeled_transactions 
                GROUP BY category 
                ORDER BY count DESC
            """).fetchall()

            stats['category_distribution'] = [dict(row) for row in category_dist]

            return stats