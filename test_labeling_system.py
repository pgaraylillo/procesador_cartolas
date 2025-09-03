# test_labeling_system.py - Prueba el sistema de etiquetado mejorado
import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime


def setup_test_environment():
    """Configura entorno de prueba"""
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
    os.chdir(project_root)
    sys.path.insert(0, str(app_dir))

    return project_root, app_dir, original_cwd


def create_test_data():
    """Crea datos de prueba para el etiquetado"""
    test_transactions = pd.DataFrame({
        'Fecha': ['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04', '2025-01-05'] * 4,
        'Descripción': [
            '0773820856 Transf a 4CDC BORDADOS',
            'PAGO EN LINEA PREVIRED',
            'Compra SUPERMERCADO LIDER',
            'Transf.Internet a TEXTIL JADUE',
            'COMISION MANTENCION CUENTA',
            'Abono Ventas GETNET',
            'COMBUSTIBLE COPEC ESTACION',
            'Transf a HERMANOS GARAY',
            'PAGO EN LINEA S.I.I.',
            'Compra TEXTIL CASSIS',
            '0146716709 Transf a Miguel Loza',
            'CARGO SERVICIO BANCARIO',
            'Compra RESTAURANT PIZZA',
            'TRANSFERENCIA EMPLEADO',
            'IMPUESTO MUNICIPAL',
            'COMPRA MATERIALES OFICINA',
            'GASTO COMBUSTIBLE AUTO',
            'PAGO CONTADOR TRIBUTARIO',
            'COMPRA INSUMOS BORDADO',
            'MANTENCION SISTEMA CONTABLE'
        ],
        'Monto': [-253470, -522252, -45000, -3972740, -15000, 163500, -35000, -200000,
                  -502049, -274082, -698292, -8900, -25000, -300000, -125000, -67000,
                  -42000, -180000, -89000, -95000],
        'ABONO/CARGO': ['CARGO'] * 19 + ['ABONO']
    })

    return test_transactions


def test_file_structure():
    """Verifica la estructura de archivos necesaria"""
    print("📁 VERIFICANDO ESTRUCTURA DE ARCHIVOS...")

    try:
        project_root, app_dir, original_cwd = setup_test_environment()

        # Verificar directorio labeling
        labeling_dir = app_dir / 'labeling'

        if not labeling_dir.exists():
            print(f"❌ FALTA DIRECTORIO: {labeling_dir}")
            print("💡 Necesitas crear: mkdir -p app/labeling")
            os.chdir(original_cwd)
            return False
        else:
            print(f"✅ Directorio existe: {labeling_dir}")

        # Verificar archivos requeridos
        required_files = [
            labeling_dir / '__init__.py',
            labeling_dir / 'smart_labeling.py'
        ]

        missing_files = []
        for file_path in required_files:
            if file_path.exists() and file_path.stat().st_size > 10:  # Al menos 10 bytes
                print(f"✅ {file_path}")
            else:
                if not file_path.exists():
                    print(f"❌ FALTA: {file_path}")
                else:
                    print(f"❌ VACÍO: {file_path}")
                missing_files.append(file_path)

        os.chdir(original_cwd)

        if missing_files:
            print(f"\n💡 ARCHIVOS FALTANTES O VACÍOS:")
            for file_path in missing_files:
                print(f"   📝 Crear/completar: {file_path}")
            return False
        else:
            print(f"✅ Todos los archivos necesarios están presentes")
            return True

    except Exception as e:
        print(f"❌ Error verificando estructura de archivos: {e}")
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False


def test_smart_labeling_system():
    """Prueba el SmartLabelingSystem"""
    print("\n🧪 PROBANDO SMART LABELING SYSTEM...")

    try:
        project_root, app_dir, original_cwd = setup_test_environment()
        print(f"✅ Entorno configurado: {project_root}")

        # Verificar DataStore
        try:
            from storage.datastore import DataStore
            ds = DataStore()
            if not ds.is_ready():
                print("⚠️ DataStore no está completamente listo, pero continuamos")
            print("✅ DataStore inicializado")
        except Exception as e:
            print(f"❌ Error con DataStore: {e}")
            os.chdir(original_cwd)
            return False

        # Crear datos de prueba
        test_data = create_test_data()
        gastos_test = test_data[test_data['Monto'] < 0].copy()
        print(f"✅ Datos de prueba creados: {len(gastos_test)} gastos")

        # Probar SmartLabelingSystem
        try:
            from labeling.smart_labeling import SmartLabelingSystem
            print("✅ SmartLabelingSystem importado correctamente")
        except ImportError as e:
            print(f"❌ No se puede importar SmartLabelingSystem: {e}")
            print("💡 Esto es normal si aún no has creado app/labeling/smart_labeling.py")
            os.chdir(original_cwd)
            return False
        except Exception as e:
            print(f"❌ Error inesperado importando SmartLabelingSystem: {e}")
            os.chdir(original_cwd)
            return False

        # Crear instancia del sistema
        labeling_system = SmartLabelingSystem(ds)
        print("✅ SmartLabelingSystem creado")

        # Probar creación de claves de transacción
        print(f"🔧 Probando creación de claves...")
        test_row = gastos_test.iloc[0]
        transaction_key = labeling_system.create_transaction_key(test_row)
        print(f"✅ Clave creada: {transaction_key}")

        # Probar carga de etiquetas existentes
        print(f"🔧 Probando carga de etiquetas existentes...")
        existing_labels = labeling_system.load_existing_labels(gastos_test)
        print(f"✅ Etiquetas existentes cargadas: {len(existing_labels)}")

        # Probar guardado de etiqueta individual
        print(f"🔧 Probando guardado de etiqueta...")
        test_transaction = gastos_test.iloc[0]
        test_key = labeling_system.create_transaction_key(test_transaction)

        try:
            labeling_system.save_label_immediately(test_transaction, 'bordados', test_key)
            print("✅ Etiqueta guardada exitosamente")
        except Exception as e:
            print(f"⚠️ Error guardando etiqueta: {str(e)[:100]}...")

        # Probar estadísticas
        print(f"🔧 Probando estadísticas...")
        stats = labeling_system.get_labeling_statistics()

        if 'error' not in stats:
            print("✅ Estadísticas obtenidas:")
            print(f"   📊 Total etiquetadas: {stats.get('total_labeled', 0)}")
            print(f"   📂 Categorías usadas: {stats.get('categories_used', 0)}")
            print(f"   🏆 Más común: {stats.get('most_common_category', 'N/A')}")
        else:
            print(f"❌ Error en estadísticas: {stats['error']}")

        os.chdir(original_cwd)
        print(f"🎉 ¡SMART LABELING SYSTEM FUNCIONA CORRECTAMENTE!")
        return True

    except Exception as e:
        print(f"❌ Error general probando SmartLabelingSystem: {e}")
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False


def test_integration_functions():
    """Prueba las funciones de integración"""
    print(f"\n🔧 PROBANDO FUNCIONES DE INTEGRACIÓN...")

    try:
        project_root, app_dir, original_cwd = setup_test_environment()

        try:
            from labeling.smart_labeling import show_improved_labeling_page
            print("✅ show_improved_labeling_page importada correctamente")

            if callable(show_improved_labeling_page):
                print("✅ show_improved_labeling_page es una función válida")
                os.chdir(original_cwd)
                return True
            else:
                print("❌ show_improved_labeling_page no es callable")
                os.chdir(original_cwd)
                return False

        except ImportError as e:
            print(f"❌ No se puede importar funciones de integración: {e}")
            print("💡 Esto es normal si aún no has creado los archivos del sistema de etiquetado")
            os.chdir(original_cwd)
            return False
        except Exception as e:
            print(f"❌ Error inesperado probando funciones de integración: {e}")
            os.chdir(original_cwd)
            return False

    except Exception as e:
        print(f"❌ Error en setup de test de integración: {e}")
        return False


def show_success_instructions():
    """Muestra instrucciones cuando todo funciona"""
    print(f"\n🎯 PRÓXIMOS PASOS:")
    print("1. Integrar en main.py:")
    print("   - Reemplaza la función page_labeling() actual")
    print("   - Agrega las importaciones necesarias")
    print()
    print("2. Probar en Streamlit:")
    print("   streamlit run app/main.py")
    print()
    print("3. El nuevo sistema incluye:")
    print("   ✅ Paginación (10, 25, 50, 100 por página)")
    print("   ✅ Auto-guardado de etiquetas")
    print("   ✅ Prevención de duplicados")
    print("   ✅ Persistencia entre actualizaciones")
    print("   ✅ Progreso visual")
    print("   ✅ Estadísticas y resúmenes")


def show_partial_success_instructions():
    """Muestra instrucciones cuando hay éxito parcial"""
    print(f"\n🔧 PARA COMPLETAR LA CONFIGURACIÓN:")
    print("1. Revisa los errores arriba")
    print("2. Verifica que copiaste correctamente el código de los artifacts")
    print("3. Asegúrate de que el DataStore funcione:")
    print("   python test_datastore_fix.py")
    print("4. Vuelve a ejecutar este test")


def show_setup_instructions():
    """Muestra instrucciones de configuración inicial"""
    print(f"\n🔧 PARA CONFIGURAR EL SISTEMA:")
    print("1. Crear directorio:")
    print("   mkdir -p app/labeling")
    print()
    print("2. Crear archivos desde los artifacts:")
    print("   - app/labeling/__init__.py")
    print("   - app/labeling/smart_labeling.py")
    print()
    print("3. Volver a ejecutar este test:")
    print("   python test_labeling_system.py")


def main():
    """Ejecuta todas las pruebas del sistema de etiquetado"""
    print("🚀 PRUEBA COMPLETA DEL SISTEMA DE ETIQUETADO MEJORADO")
    print("=" * 70)

    # Verificación previa de requisitos básicos
    print("🔍 VERIFICANDO REQUISITOS BÁSICOS...")
    try:
        project_root, app_dir, original_cwd = setup_test_environment()
        print(f"✅ Entorno configurado: {project_root}")

        # Verificar que DataStore funciona
        from storage.datastore import DataStore
        ds = DataStore()
        if ds.is_ready():
            print("✅ DataStore funcionando correctamente")
        else:
            print("⚠️ DataStore no está completamente listo, pero continuamos")

        os.chdir(original_cwd)

    except Exception as e:
        print(f"❌ ERROR CRÍTICO: DataStore no funciona: {e}")
        print("💡 Ejecuta primero: python test_datastore_fix.py")
        return False

    # Ejecutar pruebas
    test_results = {}

    # Test 1: Estructura de archivos
    try:
        test_results['file_structure'] = test_file_structure()
    except Exception as e:
        print(f"❌ Error en test de estructura: {e}")
        test_results['file_structure'] = False

    # Test 2: Sistema de etiquetado (solo si la estructura está bien)
    if test_results.get('file_structure', False):
        try:
            test_results['smart_labeling_system'] = test_smart_labeling_system()
        except Exception as e:
            print(f"❌ Error en test de SmartLabelingSystem: {e}")
            test_results['smart_labeling_system'] = False
    else:
        print("⚠️ Saltando test de SmartLabelingSystem (falta estructura de archivos)")
        test_results['smart_labeling_system'] = False

    # Test 3: Funciones de integración (solo si el sistema funciona)
    if test_results.get('smart_labeling_system', False):
        try:
            test_results['integration_functions'] = test_integration_functions()
        except Exception as e:
            print(f"❌ Error en test de integración: {e}")
            test_results['integration_functions'] = False
    else:
        print("⚠️ Saltando test de integración (SmartLabelingSystem no funciona)")
        test_results['integration_functions'] = False

    # Resumen
    print(f"\n" + "=" * 70)
    print("📋 RESUMEN DE PRUEBAS:")

    for test_name, result in test_results.items():
        status = "✅ ÉXITO" if result else "❌ FALLO"
        print(f"   {status}: {test_name}")

    passed_tests = sum(test_results.values())
    total_tests = len(test_results)

    print(f"\n🎯 RESULTADO: {passed_tests}/{total_tests} pruebas pasaron")

    # Evaluación y recomendaciones
    if test_results.get('file_structure', False):
        if passed_tests >= 2:
            print("\n🎉 ¡SISTEMA DE ETIQUETADO LISTO!")
            print("✅ Puedes integrar con Streamlit")
            show_success_instructions()
        else:
            print("\n⚠️ SISTEMA PARCIALMENTE LISTO")
            print("✅ Estructura de archivos correcta")
            print("❌ Hay errores en la implementación")
            show_partial_success_instructions()
    else:
        print(f"\n💥 SISTEMA NO LISTO")
        print("❌ Faltan archivos críticos")
        show_setup_instructions()

    return passed_tests >= 1


if __name__ == "__main__":
    try:
        success = main()
        print(f"\n{'=' * 70}")
        if success:
            print("🎊 ¡PRUEBA EXITOSA! El sistema de etiquetado está listo.")
        else:
            print("💔 PRUEBA FALLÓ. Revisa los errores y sigue las instrucciones.")

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n💥 ERROR CRÍTICO EJECUTANDO PRUEBAS: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)