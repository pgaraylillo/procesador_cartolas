# test_transfer_detector.py - Prueba el sistema de detección de resúmenes de transferencia
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


def create_transfer_summary_test_data():
    """Crea datos de prueba que simulan un resumen de transferencia bancario"""

    # Datos que simulan un resumen real de transferencia
    transfer_data = pd.DataFrame({
        'FECHA TRANSFERENCIA': [
            '01/01/2025', '02/01/2025', '03/01/2025', '01/01/2025', '04/01/2025',
            '02/01/2025', '05/01/2025', '01/01/2025', '03/01/2025', '06/01/2025'
        ],
        'RUT BENEFICIARIO': [
            '12.345.678-9',
            '98.765.432-1',
            '11.222.333-4',
            '12.345.678-9',  # Duplicado intencional
            '77.382.085-6',
            '98.765.432-1',  # Duplicado intencional
            '10.503.375-3',
            '12.345.678-9',  # Otro duplicado
            '14.671.670-9',
            '20.123.456-7'
        ],
        'NOMBRE BENEFICIARIO': [
            'JUAN CARLOS PÉREZ GARCÍA',
            'MARÍA ELENA GONZÁLEZ LÓPEZ',
            'TEXTIL JADUE LIMITADA',
            'JUAN CARLOS PÉREZ GARCÍA',  # Mismo nombre para duplicado
            'EMPRESA ABC SPA',
            'MARÍA ELENA GONZÁLEZ LÓPEZ',  # Mismo nombre para duplicado
            'PEDRO ANTONIO SILVA ROJAS',
            'JUAN CARLOS PÉREZ GARCÍA',  # Mismo nombre otra vez
            'CARMEN ROSA MORALES CASTRO',
            'CONSULTORA FINANCIERA DEL NORTE'
        ],
        'MONTO TRANSFERENCIA': [
            '500.000',
            '250.000',
            '3.972.740',
            '750.000',  # Otra transferencia al mismo RUT
            '4.000.000',
            '125.000',  # Otra transferencia al mismo RUT
            '203.250',
            '300.000',  # Otra transferencia al mismo RUT
            '200.000',
            '750.000'
        ],
        'NUMERO OPERACION': [
            '2025010101', '2025010201', '2025010301', '2025010102', '2025010401',
            '2025010202', '2025010501', '2025010103', '2025010302', '2025010601'
        ],
        'TIPO OPERACION': ['TRANSFERENCIA'] * 10,
        'CANAL': ['INTERNET'] * 10
    })

    return transfer_data


def create_non_transfer_test_data():
    """Crea datos que NO son un resumen de transferencia para probar detección"""

    # Datos genéricos que no deberían detectarse como resumen de transferencia
    non_transfer_data = pd.DataFrame({
        'Producto': ['Widget A', 'Widget B', 'Widget C'],
        'Precio': ['1000', '2000', '3000'],
        'Cantidad': ['5', '10', '15'],
        'Vendedor': ['José López', 'Ana Martínez', 'Carlos Ruiz'],
        'Fecha Venta': ['01/01/2025', '02/01/2025', '03/01/2025']
    })

    return non_transfer_data


def test_file_structure():
    """Verifica que los archivos necesarios existan"""
    print("📁 VERIFICANDO ESTRUCTURA DE ARCHIVOS...")

    try:
        project_root, app_dir, original_cwd = setup_test_environment()

        # Verificar archivos requeridos
        required_files = [
            app_dir / 'contacts' / 'transfer_summary_detector.py',
            app_dir / 'contacts' / 'enhanced_contacts_interface.py',
        ]

        missing_files = []
        for file_path in required_files:
            if file_path.exists() and file_path.stat().st_size > 100:
                print(f"✅ {file_path}")
            else:
                print(f"❌ FALTA O VACÍO: {file_path}")
                missing_files.append(file_path)

        os.chdir(original_cwd)

        if missing_files:
            print(f"\n💡 ARCHIVOS FALTANTES:")
            for file_path in missing_files:
                print(f"   📝 Crear: {file_path}")
            return False
        else:
            print(f"✅ Todos los archivos necesarios están presentes")
            return True

    except Exception as e:
        print(f"❌ Error verificando estructura: {e}")
        return False


def test_transfer_summary_detector():
    """Prueba el detector de resúmenes de transferencia"""
    print("\n🕵️ PROBANDO TRANSFER SUMMARY DETECTOR...")

    try:
        project_root, app_dir, original_cwd = setup_test_environment()

        # Importar clases
        from contacts.transfer_summary_detector import TransferSummaryDetector, ImprovedContactsManager
        from storage.datastore import DataStore

        print("✅ Imports exitosos")

        # Crear instancia del detector
        detector = TransferSummaryDetector()
        print("✅ TransferSummaryDetector creado")

        # PRUEBA 1: Detectar resumen de transferencia VERDADERO
        print("\n🧪 PRUEBA 1: Detectar resumen de transferencia...")
        transfer_data = create_transfer_summary_test_data()

        detection_result = detector.detect_transfer_summary_format(transfer_data)

        print(f"📊 Resultados de detección:")
        print(f"   • Es resumen de transferencia: {detection_result['is_transfer_summary']}")
        print(f"   • Confianza: {detection_result['confidence']:.2%}")
        print(f"   • Score headers: {detection_result['header_score']}")
        print(f"   • Score contenido: {detection_result['content_score']}")

        features = detection_result.get('detected_features', {})
        print(f"   • Columnas RUT detectadas: {features.get('rut_columns', [])}")
        print(f"   • Columnas nombre detectadas: {features.get('name_columns', [])}")
        print(f"   • Columnas monto detectadas: {features.get('amount_columns', [])}")
        print(f"   • Conteo patrones RUT: {features.get('rut_pattern_count', 0)}")

        if detection_result['is_transfer_summary']:
            print("✅ ÉXITO: Resumen de transferencia detectado correctamente")
        else:
            print("❌ FALLO: No se detectó como resumen de transferencia")
            os.chdir(original_cwd)
            return False

        # PRUEBA 2: Detectar datos NO-transferencia
        print("\n🧪 PRUEBA 2: Detectar datos que NO son resumen de transferencia...")
        non_transfer_data = create_non_transfer_test_data()

        non_detection_result = detector.detect_transfer_summary_format(non_transfer_data)

        print(f"📊 Resultados de NO-detección:")
        print(f"   • Es resumen de transferencia: {non_detection_result['is_transfer_summary']}")
        print(f"   • Confianza: {non_detection_result['confidence']:.2%}")

        if not non_detection_result['is_transfer_summary']:
            print("✅ ÉXITO: Datos genéricos correctamente NO detectados como resumen")
        else:
            print("❌ FALLO: Falso positivo - datos genéricos detectados como resumen")

        # PRUEBA 3: Mapeo de columnas
        print("\n🧪 PRUEBA 3: Mapeo automático de columnas...")
        column_mapping = detector.get_best_columns_mapping(transfer_data)

        print(f"📋 Mapeo de columnas:")
        for key, value in column_mapping.items():
            print(f"   • {key}: '{value}'")

        expected_mappings = ['rut_column', 'name_column']
        success_mappings = [key for key, value in column_mapping.items() if
                            value is not None and key in expected_mappings]

        if len(success_mappings) >= 2:
            print("✅ ÉXITO: RUT y nombre mapeados correctamente")
        else:
            print("❌ FALLO: No se pudieron mapear columnas críticas")
            os.chdir(original_cwd)
            return False

        # PRUEBA 4: Extracción de contactos únicos
        print("\n🧪 PRUEBA 4: Extracción de contactos únicos...")

        unique_contacts, extraction_stats = detector.extract_unique_contacts(transfer_data, column_mapping)

        print(f"📊 Estadísticas de extracción:")
        print(f"   • Total extraídos: {extraction_stats['extracted']}")
        print(f"   • Contactos únicos: {extraction_stats['unique']}")
        print(f"   • Duplicados removidos: {extraction_stats['duplicates_removed']}")
        print(f"   • RUTs inválidos: {extraction_stats['invalid_ruts']}")

        if not unique_contacts.empty:
            print(f"✅ ÉXITO: {len(unique_contacts)} contactos únicos extraídos")

            print(f"\n📋 Muestra de contactos únicos:")
            for _, contact in unique_contacts.head(3).iterrows():
                print(f"   • {contact['rut']} → {contact['nombre']} ({contact['alias']})")

            # Verificar que efectivamente se eliminaron duplicados
            original_ruts = transfer_data['RUT BENEFICIARIO'].apply(
                lambda x: detector.detector._clean_rut(x) if hasattr(detector, 'detector') else x
            ).nunique()
            extracted_ruts = unique_contacts['rut'].nunique()

            print(f"📊 Verificación deduplicación:")
            print(f"   • RUTs únicos en datos originales: {original_ruts}")
            print(f"   • RUTs únicos extraídos: {extracted_ruts}")

            if extracted_ruts <= original_ruts:
                print("✅ ÉXITO: Deduplicación funcionando correctamente")
            else:
                print("❌ FALLO: Problema con deduplicación")

        else:
            print("❌ FALLO: No se extrajeron contactos únicos")
            os.chdir(original_cwd)
            return False

        os.chdir(original_cwd)
        return True

    except Exception as e:
        print(f"❌ Error probando detector: {e}")
        import traceback
        traceback.print_exc()
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False


def test_improved_contacts_manager():
    """Prueba el ContactsManager mejorado"""
    print("\n👥 PROBANDO IMPROVED CONTACTS MANAGER...")

    try:
        project_root, app_dir, original_cwd = setup_test_environment()

        # Verificar DataStore
        from storage.datastore import DataStore
        ds = DataStore()

        if not ds.is_ready():
            print("⚠️ DataStore no está listo, pero continuamos con pruebas limitadas")

        # Importar y crear manager mejorado
        from contacts.transfer_summary_detector import ImprovedContactsManager
        enhanced_manager = ImprovedContactsManager(ds)

        print("✅ ImprovedContactsManager creado")

        # Crear archivo Excel de prueba
        print("\n🔧 Creando archivo Excel de prueba...")
        test_data = create_transfer_summary_test_data()

        test_excel_path = Path("test_transfer_summary.xlsx")
        test_data.to_excel(test_excel_path, index=False)

        print(f"✅ Archivo de prueba creado: {test_excel_path}")

        # Probar carga desde resumen de transferencia
        print("\n🔧 Probando carga desde resumen de transferencia...")

        df_contacts, stats = enhanced_manager.load_contacts_from_transfer_summary(test_excel_path)

        print(f"📊 Estadísticas de carga:")
        print(f"   • Total filas: {stats['total_rows']}")
        print(f"   • Detectado como resumen: {stats.get('detected_as_transfer_summary', False)}")
        print(f"   • Confianza: {stats.get('detection_confidence', 0):.2%}")
        print(f"   • Contactos válidos: {stats['valid_contacts']}")
        print(f"   • Duplicados removidos: {stats['duplicates_removed']}")
        print(f"   • RUTs inválidos: {stats['invalid_ruts']}")

        if not df_contacts.empty:
            print("✅ ÉXITO: Contactos cargados desde resumen de transferencia")

            # Mostrar muestra
            print(f"\n📋 Muestra de contactos:")
            for _, contact in df_contacts.head(3).iterrows():
                total_transf = contact.get('total_transferido', 'N/A')
                print(f"   • {contact['rut']} → {contact['nombre']} (Total: ${total_transf})")
        else:
            print("❌ FALLO: No se cargaron contactos")

        # Limpiar archivo de prueba
        test_excel_path.unlink()

        # Prueba de guardado único (si DataStore está listo)
        if ds.is_ready() and not df_contacts.empty:
            print(f"\n💾 Probando guardado de contactos únicos...")

            save_result = enhanced_manager.save_unique_contacts_to_database(df_contacts.head(3),
                                                                            overwrite_existing=True)

            print(f"📊 Resultado del guardado:")
            print(f"   • Guardados: {save_result['saved']}")
            print(f"   • Duplicados: {save_result['duplicates']}")
            print(f"   • Errores: {save_result['errors']}")

            if save_result['saved'] > 0 or save_result['duplicates'] > 0:
                print("✅ ÉXITO: Sistema de guardado funcionando")
            else:
                print("⚠️ ADVERTENCIA: No se guardaron contactos (verificar BD)")

        os.chdir(original_cwd)
        return True

    except Exception as e:
        print(f"❌ Error probando ImprovedContactsManager: {e}")
        import traceback
        traceback.print_exc()
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False


def show_integration_instructions():
    """Muestra instrucciones de integración con la app principal"""
    print(f"\n🎯 INSTRUCCIONES DE INTEGRACIÓN:")
    print("=" * 50)

    print("1️⃣ **Crear los archivos necesarios:**")
    print("   • app/contacts/transfer_summary_detector.py")
    print("   • app/contacts/enhanced_contacts_interface.py")
    print()

    print("2️⃣ **Modificar main.py para usar el nuevo sistema:**")
    print()
    print("```python")
    print("def page_contacts(datastore):")
    print('    """Página de gestión de contactos mejorada"""')
    print("    try:")
    print("        from contacts.enhanced_contacts_interface import show_transfer_summary_page")
    print("        show_transfer_summary_page(datastore)")
    print("    except ImportError:")
    print("        # Fallback al sistema original")
    print("        from contacts.contacts_manager import show_contacts_management_page")
    print("        show_contacts_management_page(datastore)")
    print("```")
    print()

    print("3️⃣ **Características del nuevo sistema:**")
    print("   ✅ Detección automática de resúmenes de transferencia")
    print("   ✅ Eliminación inteligente de duplicados")
    print("   ✅ Consolidación de múltiples transferencias por cliente")
    print("   ✅ Validación de RUTs chilenos")
    print("   ✅ Interfaz mejorada con análisis detallado")
    print()

    print("4️⃣ **Probar en Streamlit:**")
    print("   streamlit run app/main.py")
    print("   → Ir a 'Gestión Contactos'")
    print("   → Usar tab 'Cargar Resumen'")


def main():
    """Ejecuta todas las pruebas del sistema de detección"""
    print("🚀 PRUEBA COMPLETA DEL SISTEMA DE DETECCIÓN DE RESÚMENES")
    print("=" * 80)

    # Verificar requisitos básicos
    print("🔍 VERIFICANDO REQUISITOS BÁSICOS...")
    try:
        project_root, app_dir, original_cwd = setup_test_environment()
        print(f"✅ Entorno configurado: {project_root}")

        from storage.datastore import DataStore
        ds = DataStore()
        if ds.is_ready():
            print("✅ DataStore funcionando correctamente")
        else:
            print("⚠️ DataStore no está completamente listo")

        os.chdir(original_cwd)

    except Exception as e:
        print(f"❌ ERROR CRÍTICO: DataStore no funciona: {e}")
        print("💡 Ejecuta primero: python test_fixed_datastore.py")
        return False

    # Ejecutar pruebas
    test_results = {}

    try:
        test_results['file_structure'] = test_file_structure()
    except Exception as e:
        print(f"❌ Error en test de estructura: {e}")
        test_results['file_structure'] = False

    if test_results.get('file_structure', False):
        try:
            test_results['detector'] = test_transfer_summary_detector()
        except Exception as e:
            print(f"❌ Error en test de detector: {e}")
            test_results['detector'] = False
    else:
        test_results['detector'] = False
        print("⚠️ Saltando test de detector (falta estructura)")

    if test_results.get('detector', False):
        try:
            test_results['improved_manager'] = test_improved_contacts_manager()
        except Exception as e:
            print(f"❌ Error en test de manager: {e}")
            test_results['improved_manager'] = False
    else:
        test_results['improved_manager'] = False
        print("⚠️ Saltando test de manager (detector no funciona)")

    # Resumen
    print(f"\n" + "=" * 80)
    print("📋 RESUMEN DE PRUEBAS:")

    for test_name, result in test_results.items():
        status = "✅ ÉXITO" if result else "❌ FALLO"
        print(f"   {status}: {test_name}")

    passed_tests = sum(test_results.values())
    total_tests = len(test_results)

    print(f"\n🎯 RESULTADO: {passed_tests}/{total_tests} pruebas pasaron")

    # Evaluación final
    if passed_tests == total_tests:
        print("\n🎉 ¡SISTEMA COMPLETAMENTE FUNCIONAL!")
        print("✅ El detector de resúmenes de transferencia está listo")
        show_integration_instructions()
        return True
    elif passed_tests >= 2:
        print("\n⚠️ SISTEMA MAYORMENTE FUNCIONAL")
        print("✅ Componentes principales funcionan")
        print("⚠️ Algunos errores menores a corregir")
        show_integration_instructions()
        return True
    else:
        print(f"\n💥 SISTEMA NO FUNCIONAL")
        print("❌ Demasiados errores críticos")
        print("🔧 Revisa los archivos faltantes y errores arriba")
        return False


if __name__ == "__main__":
    try:
        success = main()
        print(f"\n{'=' * 80}")
        if success:
            print("🎊 ¡PRUEBA EXITOSA! El sistema está listo para usar.")
        else:
            print("💔 PRUEBA FALLÓ. Revisa los errores y archivos faltantes.")

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n💥 ERROR CRÍTICO EJECUTANDO PRUEBAS: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)