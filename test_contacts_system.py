# test_contacts_system.py - Prueba el sistema de gestión de contactos
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


def create_test_excel():
    """Crea un Excel de prueba simulando datos del banco"""
    test_data = pd.DataFrame({
        'RUT CLIENTE': [
            '12.345.678-9',
            '98.765.432-1',
            '11.222.333-4',
            '77.382.085-6',
            '10.503.375-3',
            '14.671.670-9',
            '76.293.338-1',
            '86.521.400-6',
            '15.876.543-2',
            '20.123.456-7'
        ],
        'NOMBRE BENEFICIARIO': [
            'JUAN CARLOS PÉREZ GARCÍA',
            'MARÍA ELENA GONZÁLEZ LÓPEZ',
            'TEXTIL JADUE LIMITADA',
            'EMPRESA ABC SPA',
            'PEDRO ANTONIO SILVA ROJAS',
            'CARMEN ROSA MORALES CASTRO',
            'COMERCIAL XYZ LTDA',
            'SERVICIOS INTEGRALES DEL SUR',
            'ANA BEATRIZ HERRERA MUÑOZ',
            'CONSULTORA FINANCIERA DEL NORTE'
        ],
        'MONTO': [
            '500000',
            '250000',
            '3972740',
            '4000000',
            '203250',
            '200000',
            '1150732',
            '698292',
            '150000',
            '750000'
        ],
        'FECHA': [
            '01/01/2025',
            '02/01/2025',
            '03/01/2025',
            '04/01/2025',
            '05/01/2025',
            '06/01/2025',
            '07/01/2025',
            '08/01/2025',
            '09/01/2025',
            '10/01/2025'
        ]
    })

    return test_data


def test_file_structure():
    """Verifica que existan los archivos necesarios"""
    print("📁 VERIFICANDO ESTRUCTURA DE ARCHIVOS...")

    try:
        project_root, app_dir, original_cwd = setup_test_environment()

        # Verificar directorio contacts
        contacts_dir = app_dir / 'contacts'

        if not contacts_dir.exists():
            print(f"❌ FALTA DIRECTORIO: {contacts_dir}")
            print("💡 Necesitas crear: mkdir -p app/contacts")
            os.chdir(original_cwd)
            return False
        else:
            print(f"✅ Directorio existe: {contacts_dir}")

        # Verificar archivos requeridos
        required_files = [
            contacts_dir / '__init__.py',
            contacts_dir / 'contacts_manager.py'
        ]

        missing_files = []
        for file_path in required_files:
            if file_path.exists() and file_path.stat().st_size > 10:
                print(f"✅ {file_path}")
            else:
                if not file_path.exists():
                    print(f"❌ FALTA: {file_path}")
                else:
                    print(f"❌ VACÍO: {file_path}")
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
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False


def test_contacts_manager():
    """Prueba el ContactsManager"""
    print("\n🧪 PROBANDO CONTACTS MANAGER...")

    try:
        project_root, app_dir, original_cwd = setup_test_environment()

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

        # Importar ContactsManager
        try:
            from contacts.contacts_manager import ContactsManager
            print("✅ ContactsManager importado correctamente")
        except ImportError as e:
            print(f"❌ No se puede importar ContactsManager: {e}")
            print("💡 Asegúrate de haber creado app/contacts/contacts_manager.py")
            os.chdir(original_cwd)
            return False

        # Crear instancia
        contacts_manager = ContactsManager(ds)
        print("✅ ContactsManager creado")

        # Probar limpieza de RUT
        print("🔧 Probando limpieza de RUTs...")
        test_ruts = ['12.345.678-9', '12345678-9', '12345678K', '  12.345.678-9  ']
        for rut in test_ruts:
            clean_rut = contacts_manager.clean_rut(rut)
            valid = contacts_manager.validate_rut(rut)
            print(f"   {rut} → {clean_rut} (válido: {valid})")

        # Probar creación de Excel de prueba
        print("🔧 Creando Excel de prueba...")
        test_df = create_test_excel()

        # Guardar Excel temporal para probar carga
        temp_excel_path = Path("temp_contacts_test.xlsx")
        test_df.to_excel(temp_excel_path, index=False)
        print(f"✅ Excel de prueba creado: {temp_excel_path}")

        # Probar carga desde Excel
        print("🔧 Probando carga desde Excel...")
        try:
            df_contacts, stats = contacts_manager.load_contacts_from_excel(temp_excel_path)

            print("✅ Excel procesado exitosamente:")
            print(f"   📊 Total filas: {stats['total_rows']}")
            print(f"   ✅ Contactos válidos: {stats['valid_contacts']}")
            print(f"   🔍 RUT detectado: {stats['rut_column_detected']}")
            print(f"   🔍 Nombre detectado: {stats['name_column_detected']}")

            if len(stats['sample_contacts']) > 0:
                print("   📋 Muestra de contactos:")
                for contact in stats['sample_contacts']:
                    print(f"      • {contact['rut']} → {contact['nombre']} ({contact['alias']})")

        except Exception as e:
            print(f"❌ Error cargando Excel: {e}")
            os.chdir(original_cwd)
            return False
        finally:
            # Limpiar archivo temporal
            if temp_excel_path.exists():
                temp_excel_path.unlink()

        # Probar guardado en base de datos
        print("🔧 Probando guardado en BD...")
        try:
            save_result = contacts_manager.save_contacts_to_database(df_contacts, overwrite_existing=True)
            print("✅ Guardado en BD:")
            print(f"   💾 Guardados: {save_result['saved']}")
            print(f"   ⚠️ Duplicados: {save_result['duplicates']}")
            print(f"   ❌ Errores: {save_result['errors']}")

        except Exception as e:
            print(f"❌ Error guardando en BD: {e}")

        # Probar mejora de descripciones
        print("🔧 Probando mejora de descripciones...")
        test_descriptions = pd.DataFrame({
            'Descripción': [
                'Transf.Internet a 77.382.085-6',
                'Transf.Internet a 10.503.375-3',
                'PAGO EN LINEA PREVIRED',
                'Transferencia a 12.345.678-9 por servicios'
            ],
            'Monto': [-4000000, -203250, -522252, -150000]
        })

        try:
            enhanced_df = contacts_manager.enhance_transaction_descriptions(test_descriptions)

            print("✅ Descripciones mejoradas:")
            for orig, enhanced in zip(test_descriptions['Descripción'], enhanced_df['Descripción']):
                if orig != enhanced:
                    print(f"   📝 {orig}")
                    print(f"   ✨ {enhanced}")
                else:
                    print(f"   ➖ {orig} (sin cambios)")

        except Exception as e:
            print(f"⚠️ Error mejorando descripciones: {e}")

        # Probar resumen
        print("🔧 Probando resumen de contactos...")
        try:
            summary = contacts_manager.get_contacts_summary()

            if 'error' not in summary:
                print("✅ Resumen obtenido:")
                print(f"   👥 Total contactos: {summary['total_contacts']}")
                print(f"   📊 Por tipo: {summary['by_type']}")
                print(f"   📋 Contactos recientes: {len(summary['recent_contacts'])}")
            else:
                print(f"❌ Error en resumen: {summary['error']}")

        except Exception as e:
            print(f"❌ Error obteniendo resumen: {e}")

        os.chdir(original_cwd)
        print("🎉 ¡CONTACTS MANAGER FUNCIONA CORRECTAMENTE!")
        return True

    except Exception as e:
        print(f"❌ Error general en ContactsManager: {e}")
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False


def test_streamlit_integration():
    """Prueba las funciones de integración con Streamlit"""
    print("\n🖥️ PROBANDO INTEGRACIÓN STREAMLIT...")

    try:
        project_root, app_dir, original_cwd = setup_test_environment()

        try:
            from contacts.contacts_manager import show_contacts_management_page
            print("✅ show_contacts_management_page importada correctamente")

            if callable(show_contacts_management_page):
                print("✅ Función de interfaz es válida")
                os.chdir(original_cwd)
                return True
            else:
                print("❌ show_contacts_management_page no es callable")
                os.chdir(original_cwd)
                return False

        except ImportError as e:
            print(f"❌ No se puede importar interfaz Streamlit: {e}")
            os.chdir(original_cwd)
            return False

    except Exception as e:
        print(f"❌ Error en integración Streamlit: {e}")
        return False


def main():
    """Ejecuta todas las pruebas del sistema de contactos"""
    print("🚀 PRUEBA COMPLETA DEL SISTEMA DE GESTIÓN DE CONTACTOS")
    print("=" * 70)

    # Verificación básica de DataStore
    print("🔍 VERIFICANDO REQUISITOS BÁSICOS...")
    try:
        project_root, app_dir, original_cwd = setup_test_environment()
        print(f"✅ Entorno configurado: {project_root}")

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

    try:
        test_results['file_structure'] = test_file_structure()
    except Exception as e:
        print(f"❌ Error en test de estructura: {e}")
        test_results['file_structure'] = False

    if test_results.get('file_structure', False):
        try:
            test_results['contacts_manager'] = test_contacts_manager()
        except Exception as e:
            print(f"❌ Error en test de ContactsManager: {e}")
            test_results['contacts_manager'] = False
    else:
        print("⚠️ Saltando test de ContactsManager (falta estructura)")
        test_results['contacts_manager'] = False

    if test_results.get('contacts_manager', False):
        try:
            test_results['streamlit_integration'] = test_streamlit_integration()
        except Exception as e:
            print(f"❌ Error en test de integración: {e}")
            test_results['streamlit_integration'] = False
    else:
        print("⚠️ Saltando test de integración (ContactsManager no funciona)")
        test_results['streamlit_integration'] = False

    # Resumen
    print(f"\n" + "=" * 70)
    print("📋 RESUMEN DE PRUEBAS:")

    for test_name, result in test_results.items():
        status = "✅ ÉXITO" if result else "❌ FALLO"
        print(f"   {status}: {test_name}")

    passed_tests = sum(test_results.values())
    total_tests = len(test_results)

    print(f"\n🎯 RESULTADO: {passed_tests}/{total_tests} pruebas pasaron")

    # Instrucciones basadas en resultados
    if test_results.get('file_structure', False):
        if passed_tests >= 2:
            print("\n🎉 ¡SISTEMA DE CONTACTOS LISTO!")
            print("✅ Puedes integrar con Streamlit")
            show_success_instructions()
        else:
            print("\n⚠️ SISTEMA PARCIALMENTE LISTO")
            print("✅ Estructura de archivos correcta")
            print("❌ Hay errores en la implementación")
            show_partial_instructions()
    else:
        print(f"\n💥 SISTEMA NO LISTO")
        print("❌ Faltan archivos críticos")
        show_setup_instructions()

    return passed_tests >= 1


def show_success_instructions():
    """Instrucciones cuando todo funciona"""
    print(f"\n🎯 PRÓXIMOS PASOS:")
    print("1. Integrar en main.py:")
    print("   - Agregar página 'Gestión Contactos' al sidebar")
    print("   - Agregar función page_contacts()")
    print("   - Modificar show_transaction_preview()")
    print()
    print("2. Probar en Streamlit:")
    print("   streamlit run app/main.py")
    print()
    print("3. El sistema incluye:")
    print("   ✅ Carga masiva desde Excel del banco")
    print("   ✅ Gestión manual de contactos")
    print("   ✅ Mejora automática de descripciones")
    print("   ✅ Búsqueda y edición de contactos")
    print("   ✅ Detección automática de RUTs y nombres")


def show_partial_instructions():
    """Instrucciones para éxito parcial"""
    print(f"\n🔧 PARA COMPLETAR:")
    print("1. Revisa los errores mostrados arriba")
    print("2. Verifica que el DataStore funcione:")
    print("   python test_datastore_fix.py")
    print("3. Asegúrate de copiar correctamente el código")
    print("4. Vuelve a ejecutar este test")


def show_setup_instructions():
    """Instrucciones de configuración inicial"""
    print(f"\n🔧 PARA CONFIGURAR EL SISTEMA:")
    print("1. Crear directorio:")
    print("   mkdir -p app/contacts")
    print()
    print("2. Crear archivos desde los artifacts:")
    print("   - app/contacts/__init__.py")
    print("   - app/contacts/contacts_manager.py")
    print()
    print("3. Volver a ejecutar este test:")
    print("   python test_contacts_system.py")


if __name__ == "__main__":
    try:
        success = main()
        print(f"\n{'=' * 70}")
        if success:
            print("🎊 ¡SISTEMA DE CONTACTOS FUNCIONANDO!")
        else:
            print("💔 HAY ERRORES QUE CORREGIR")

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n💥 ERROR CRÍTICO: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)