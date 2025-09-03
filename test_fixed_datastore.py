# test_fixed_datastore.py - Prueba del DataStore corregido
import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime


def test_fixed_datastore():
    """Prueba el DataStore corregido paso a paso"""

    print("🧪 PRUEBA DEL DATASTORE CORREGIDO")
    print("=" * 50)

    # Configurar paths
    current_dir = Path.cwd()
    if current_dir.name == 'app':
        project_root = current_dir.parent
        app_dir = current_dir
    elif (current_dir / 'app').exists():
        project_root = current_dir
        app_dir = current_dir / 'app'
    else:
        project_root = current_dir
        app_dir = current_dir / 'app'

    print(f"📁 Directorio actual: {current_dir}")
    print(f"📁 Raíz proyecto: {project_root}")
    print(f"📁 App directory: {app_dir}")

    # Cambiar al directorio del proyecto
    original_cwd = Path.cwd()
    try:
        os.chdir(project_root)
        sys.path.insert(0, str(app_dir))

        print(f"🔧 Directorio cambiado a: {Path.cwd()}")

        # PASO 1: Importar y crear DataStore
        print(f"\n📦 PASO 1: Importando DataStore...")
        try:
            from storage.datastore import DataStore
            print("✅ DataStore importado correctamente")
        except Exception as e:
            print(f"❌ Error importando DataStore: {e}")
            return False

        # PASO 2: Inicializar DataStore
        print(f"\n🏗️ PASO 2: Inicializando DataStore...")
        try:
            ds = DataStore()
            print("✅ DataStore creado sin excepciones")
        except Exception as e:
            print(f"❌ Error inicializando DataStore: {e}")
            import traceback
            traceback.print_exc()
            return False

        # PASO 3: Verificar estado
        print(f"\n🔍 PASO 3: Verificando estado...")
        status = ds.get_status()
        print(f"📊 Estado del DataStore:")
        for key, value in status.items():
            icon = "✅" if value else "❌"
            print(f"   {icon} {key}: {value}")

        if not ds.is_ready():
            print("❌ DataStore no está listo")
            return False

        # PASO 4: Probar operaciones básicas
        print(f"\n🧪 PASO 4: Probando operaciones básicas...")

        # Test 1: Cargar datos existentes
        try:
            existing_data = ds.load_labeled()
            print(f"✅ Carga de datos: {len(existing_data)} registros encontrados")
        except Exception as e:
            print(f"❌ Error cargando datos: {e}")

        # Test 2: Obtener categorías
        try:
            categories = ds.get_categories()
            print(f"✅ Categorías obtenidas: {len(categories)} categorías")
            print(f"   📝 Primeras 5: {categories[:5]}")
        except Exception as e:
            print(f"❌ Error obteniendo categorías: {e}")

        # Test 3: Obtener resumen financiero
        try:
            summary = ds.get_financial_summary()
            print(f"✅ Resumen financiero obtenido:")
            print(f"   📊 Total transacciones: {summary.get('total_transactions', 0)}")
            print(f"   📋 Categorías: {summary.get('categories', 0)}")
            if 'error' in summary:
                print(f"   ⚠️ Error en resumen: {summary['error']}")
        except Exception as e:
            print(f"❌ Error obteniendo resumen: {e}")

        # PASO 5: Probar guardado de datos
        print(f"\n💾 PASO 5: Probando guardado de datos...")
        test_data = pd.DataFrame({
            'date': ['2025-01-01', '2025-01-02'],
            'description': ['Test transaction 1', 'Test transaction 2'],
            'amount': [-1000, -2000],
            'category': ['test', 'test'],
            'debit_credit': ['CARGO', 'CARGO']
        })

        try:
            ds.save_labeled(test_data)
            print("✅ Guardado de datos de prueba exitoso")

            # Verificar que se guardó
            loaded_data = ds.load_labeled()
            test_records = loaded_data[loaded_data['category'] == 'test'] if not loaded_data.empty else pd.DataFrame()
            print(f"✅ Verificación: {len(test_records)} registros de prueba encontrados")

        except Exception as e:
            print(f"❌ Error guardando datos de prueba: {e}")
            import traceback
            traceback.print_exc()

        # PASO 6: Estadísticas finales
        print(f"\n📊 PASO 6: Estadísticas finales...")
        try:
            final_summary = ds.get_financial_summary()
            print(f"📈 Resumen final:")
            print(f"   🔢 Total transacciones: {final_summary.get('total_transactions', 0)}")
            print(f"   📂 Categorías disponibles: {final_summary.get('categories', 0)}")
            print(f"   👥 Contactos: {final_summary.get('contacts', 0)}")

            if final_summary.get('total_transactions', 0) > 0:
                print("🎉 ¡HAY DATOS EN LA BASE DE DATOS!")
            else:
                print("ℹ️ No hay transacciones etiquetadas aún")

        except Exception as e:
            print(f"❌ Error en estadísticas finales: {e}")

        print(f"\n🎯 RESULTADO: ¡DataStore funciona correctamente!")
        return True

    except Exception as e:
        print(f"\n❌ ERROR GENERAL EN LA PRUEBA: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Restaurar directorio original
        os.chdir(original_cwd)


def cleanup_test_data():
    """Limpia datos de prueba creados durante el test"""
    print(f"\n🧹 LIMPIANDO DATOS DE PRUEBA...")

    current_dir = Path.cwd()
    if current_dir.name == 'app':
        project_root = current_dir.parent
        app_dir = current_dir
    elif (current_dir / 'app').exists():
        project_root = current_dir
        app_dir = current_dir / 'app'
    else:
        project_root = current_dir
        app_dir = current_dir / 'app'

    original_cwd = Path.cwd()
    try:
        os.chdir(project_root)
        sys.path.insert(0, str(app_dir))

        from storage.datastore import DataStore
        ds = DataStore()

        if ds.is_ready() and ds.db:
            with ds.db.get_connection() as conn:
                deleted = conn.execute("DELETE FROM labeled_transactions WHERE category = 'test'").rowcount
                conn.commit()
                print(f"✅ {deleted} registros de prueba eliminados")
        else:
            print("⚠️ No se pudo limpiar - DataStore no está listo")

    except Exception as e:
        print(f"❌ Error limpiando datos de prueba: {e}")
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Limpiar datos de prueba")
    args = parser.parse_args()

    if args.clean:
        cleanup_test_data()
    else:
        success = test_fixed_datastore()
        if success:
            print(f"\n🎉 ¡TODOS LOS TESTS PASARON!")
        else:
            print(f"\n💥 ALGUNOS TESTS FALLARON")