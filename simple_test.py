# simple_test.py - Prueba básica que funciona desde cualquier directorio
import sys
from pathlib import Path


def find_project_root():
    """Encuentra la raíz del proyecto buscando app/"""
    current = Path.cwd()

    # Intentar encontrar desde directorio actual hacia arriba
    for parent in [current] + list(current.parents):
        if (parent / 'app').exists() and (parent / 'app' / 'main.py').exists():
            return parent, parent / 'app'

    # Si no encontramos, assumir que estamos en la raíz
    return current, current / 'app'


def main():
    print("🚀 TEST SIMPLE DE BASE DE DATOS")
    print("=" * 40)

    # 1. Encontrar directorios
    try:
        project_root, app_dir = find_project_root()
        print(f"📁 Raíz proyecto: {project_root}")
        print(f"📁 Directorio app: {app_dir}")

        if not app_dir.exists():
            print("❌ No se encontró directorio app/")
            return

    except Exception as e:
        print(f"❌ Error encontrando directorios: {e}")
        return

    # 2. Configurar paths y cambiar directorio
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(project_root)
        sys.path.insert(0, str(app_dir))

        print("✅ Paths configurados")

        # 3. Verificar estructura básica
        required_dirs = ['database', 'storage', 'bankstatements']
        for dir_name in required_dirs:
            dir_path = app_dir / dir_name
            if dir_path.exists():
                print(f"✅ {dir_name}/ encontrado")
            else:
                print(f"❌ {dir_name}/ faltante")

        # 4. Verificar base de datos
        db_path = project_root / 'data' / 'finance_app.db'
        print(f"\n📁 Base de datos: {db_path}")
        print(f"📁 Existe: {db_path.exists()}")

        if db_path.exists():
            # Probar conexión directa con sqlite3
            import sqlite3
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Listar tablas
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                print(f"📋 Tablas: {tables}")

                # Contar registros en cada tabla
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"   {table}: {count} registros")

                conn.close()
                print("✅ Conexión SQLite directa exitosa")

            except Exception as e:
                print(f"❌ Error con SQLite directo: {e}")

        # 5. Probar importación de módulos
        print(f"\n📦 Probando importaciones...")
        try:
            from database.db_manager import DatabaseManager
            print("✅ DatabaseManager importado")

            from storage.datastore import DataStore
            print("✅ DataStore importado")

            # 6. Crear instancia básica
            print(f"\n🔧 Inicializando DataStore...")
            ds = DataStore()

            if hasattr(ds, 'db'):
                print("✅ DataStore tiene atributo 'db'")
                print(f"📁 DB Path: {ds.db.db_path}")

                # Probar conexión
                with ds.db.get_connection() as conn:
                    result = conn.execute("SELECT COUNT(*) FROM categories").fetchone()
                    print(f"✅ Conexión BD exitosa - Categorías: {result[0]}")

                print("🎉 ¡TODO FUNCIONA CORRECTAMENTE!")

            else:
                print("❌ DataStore NO tiene atributo 'db'")
                print(f"🔍 Atributos de DataStore: {[attr for attr in dir(ds) if not attr.startswith('_')]}")

        except Exception as e:
            print(f"❌ Error en importaciones/inicialización: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Restaurar directorio original
        os.chdir(original_cwd)

    print(f"\n✅ Test completado")


if __name__ == "__main__":
    main()