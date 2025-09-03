# test_save_labels.py - Probar guardado de etiquetas independientemente
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime


def test_save_labels():
    """Prueba el guardado de etiquetas paso a paso"""

    print("🧪 PRUEBA DE GUARDADO DE ETIQUETAS")
    print("=" * 40)

    # Verificar desde dónde se ejecuta
    current_dir = Path.cwd()
    print(f"📁 Directorio actual: {current_dir}")

    # Buscar el directorio app
    if current_dir.name == 'app':
        # Si estamos en app/, subir un nivel
        project_root = current_dir.parent
        app_dir = current_dir
    elif (current_dir / 'app').exists():
        # Si estamos en la raíz del proyecto
        project_root = current_dir
        app_dir = current_dir / 'app'
    else:
        print("❌ No se puede encontrar el directorio app/")
        return

    print(f"📁 Raíz del proyecto: {project_root}")
    print(f"📁 Directorio app: {app_dir}")

    # Agregar app al path
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))

    print(f"🔧 Python path actualizado")

    # Cambiar al directorio del proyecto para paths relativos
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(project_root)
        print(f"📁 Cambiado a directorio: {Path.cwd()}")

        # Verificar que existe el directorio app y sus módulos
        required_modules = ['database', 'storage']
        for module in required_modules:
            module_path = app_dir / module
            if not module_path.exists():
                print(f"❌ Módulo faltante: {module_path}")
                return
            else:
                print(f"✅ Módulo encontrado: {module}")

        try:
            # 1. Importar componentes
            print("\n📦 Importando componentes...")
            from database.db_manager import DatabaseManager
            print("✅ DatabaseManager importado")

            from storage.datastore import DataStore
            print("✅ DataStore importado")

        except Exception as e:
            print(f"❌ Error en importación: {e}")
            import traceback
            traceback.print_exc()
            return

        try:
            # 2. Inicializar DataStore
            print("\n🔧 Inicializando DataStore...")
            ds = DataStore()
            print(f"✅ DataStore inicializado")

            # Verificar que tiene el atributo db
            if not hasattr(ds, 'db'):
                print(f"❌ DataStore no tiene atributo 'db'")
                print(f"🔍 Atributos disponibles: {dir(ds)}")
                return

            print(f"📁 Base de datos: {ds.db.db_path}")

        except Exception as e:
            print(f"❌ Error inicializando DataStore: {e}")
            import traceback
            traceback.print_exc()
            return

        # 3. Verificar BD existe y está accesible
        print(f"📁 Archivo existe: {ds.db.db_path.exists()}")

        # 4. Probar conexión básica
        print("\n🔌 Probando conexión...")
        try:
            with ds.db.get_connection() as conn:
                result = conn.execute("SELECT COUNT(*) FROM categories").fetchone()
                print(f"✅ Conexión exitosa - Categorías: {result[0]}")
        except Exception as e:
            print(f"❌ Error en conexión: {e}")
            return

        # 5. Crear datos de prueba
        print("\n📝 Creando datos de prueba...")
        test_data = pd.DataFrame({
            'date': ['2025-01-01', '2025-01-02'],
            'description': ['Gasto de prueba 1', 'Transf.Internet a 10.503.375-3'],
            'amount': [-1000, -2000],
            'category': ['test', 'test'],
            'debit_credit': ['CARGO', 'CARGO']
        })

        print(f"📊 Datos de prueba creados:")
        print(test_data.to_string())

        # 6. Guardar datos de prueba
        print(f"\n💾 Guardando datos de prueba...")
        try:
            ds.save_labeled(test_data)
            print("✅ Guardado completado (sin errores)")
        except Exception as e:
            print(f"❌ Error guardando: {e}")
            import traceback
            traceback.print_exc()
            return

        # 7. Verificar que se guardaron
        print(f"\n🔍 Verificando guardado...")
        try:
            loaded_data = ds.load_labeled()
            print(f"📊 Registros cargados: {len(loaded_data)}")

            if len(loaded_data) > 0:
                print("✅ ¡Datos encontrados en la BD!")
                print(f"📝 Últimas transacciones:")
                print(loaded_data.tail(3).to_string())

                # Verificar categorías
                if 'category' in loaded_data.columns:
                    categories = loaded_data['category'].value_counts()
                    print(f"\n📊 Categorías encontradas:")
                    for cat, count in categories.items():
                        print(f"   • {cat}: {count} transacciones")

            else:
                print("❌ No se encontraron datos en la BD")

                # Verificar directamente en la BD
                print("🔍 Verificando directamente en SQLite...")
                with ds.db.get_connection() as conn:
                    count = conn.execute("SELECT COUNT(*) FROM labeled_transactions").fetchone()[0]
                    print(f"📊 Registros en labeled_transactions: {count}")

                    if count > 0:
                        rows = conn.execute("SELECT * FROM labeled_transactions LIMIT 3").fetchall()
                        print("📝 Primeros registros:")
                        for row in rows:
                            print(f"   {row}")
        except Exception as e:
            print(f"❌ Error verificando: {e}")
            return

        # 8. Estadísticas finales
        print(f"\n📊 ESTADÍSTICAS FINALES:")
        try:
            summary = ds.get_financial_summary()
            for key, value in summary.items():
                if not isinstance(value, (list, dict)):
                    print(f"   {key}: {value}")
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {e}")

        print(f"\n✅ PRUEBA COMPLETADA EXITOSAMENTE")

    except Exception as e:
        print(f"\n❌ ERROR GENERAL EN LA PRUEBA: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Restaurar directorio original
        os.chdir(original_cwd)


def clean_test_data():
    """Limpia datos de prueba de la BD"""
    try:
        # Mismo setup que arriba para paths
        current_dir = Path.cwd()
        if current_dir.name == 'app':
            project_root = current_dir.parent
            app_dir = current_dir
        elif (current_dir / 'app').exists():
            project_root = current_dir
            app_dir = current_dir / 'app'
        else:
            print("❌ No se puede encontrar directorio app/")
            return

        import os
        original_cwd = Path.cwd()
        os.chdir(project_root)

        if str(app_dir) not in sys.path:
            sys.path.insert(0, str(app_dir))

        from storage.datastore import DataStore

        ds = DataStore()
        with ds.db.get_connection() as conn:
            # Eliminar transacciones de prueba
            deleted = conn.execute("DELETE FROM labeled_transactions WHERE category = 'test'").rowcount
            conn.commit()
            print(f"🧹 {deleted} transacciones de prueba eliminadas")

        os.chdir(original_cwd)

    except Exception as e:
        print(f"❌ Error limpiando datos de prueba: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Limpiar datos de prueba")
    args = parser.parse_args()

    if args.clean:
        clean_test_data()
    else:
        test_save_labels()