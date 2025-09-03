# debug_datastore.py - Script para diagnosticar problemas de guardado
import sys
from pathlib import Path
import pandas as pd

# Agregar el path de la app
app_path = Path(__file__).parent / 'app'
sys.path.insert(0, str(app_path))


def test_datastore():
    print("🔍 Diagnosticando DataStore...")

    try:
        # Intentar importar DatabaseManager
        from database.db_manager import DatabaseManager
        print("✅ DatabaseManager importado correctamente")
    except Exception as e:
        print(f"❌ Error importando DatabaseManager: {e}")
        return

    try:
        # Intentar importar DataStore
        from storage.datastore import DataStore
        print("✅ DataStore importado correctamente")
    except Exception as e:
        print(f"❌ Error importando DataStore: {e}")
        return

    try:
        # Crear instancia de DataStore
        ds = DataStore()
        print("✅ DataStore inicializado")
        print(f"📁 Base de datos: {ds.db.db_path}")
        print(f"📁 Existe: {ds.db.db_path.exists()}")

        # Verificar conexión a BD
        with ds.db.get_connection() as conn:
            result = conn.execute("SELECT COUNT(*) FROM categories").fetchone()
            print(f"✅ Conexión BD exitosa - Categorías: {result[0]}")

    except Exception as e:
        print(f"❌ Error inicializando DataStore: {e}")
        import traceback
        traceback.print_exc()
        return

    # Probar guardado de datos de prueba
    print("\n🧪 Probando guardado de datos de prueba...")

    test_data = pd.DataFrame({
        'date': ['2025-01-01'],
        'description': ['Test transaction'],
        'amount': [-1000],
        'category': ['test']
    })

    try:
        ds.save_labeled(test_data)
        print("✅ Guardado de prueba exitoso")

        # Verificar que se guardó
        loaded = ds.load_labeled()
        print(f"📊 Registros en BD: {len(loaded)}")

        if len(loaded) > 0:
            print("✅ Datos cargados correctamente desde BD")
            print(f"📝 Últimas 3 transacciones:")
            print(loaded.tail(3)[['date', 'description', 'category']])
        else:
            print("⚠️ No se encontraron datos en la BD")

    except Exception as e:
        print(f"❌ Error en guardado de prueba: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_datastore()