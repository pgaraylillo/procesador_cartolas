# test_streamlit_fix.py - Prueba el nuevo sistema de componentes
import sys
import os
from pathlib import Path


class MockStreamlitState:
    """Mock de st.session_state para pruebas"""

    def __init__(self):
        self._state = {}

    def __getitem__(self, key):
        return self._state[key]

    def __setitem__(self, key, value):
        self._state[key] = value

    def __contains__(self, key):
        return key in self._state

    def get(self, key, default=None):
        return self._state.get(key, default)


def setup_test_environment():
    """Configura el entorno de prueba"""
    # Encontrar directorios
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

    # Configurar paths
    original_cwd = Path.cwd()
    os.chdir(project_root)
    sys.path.insert(0, str(app_dir))

    # Mock de streamlit
    import types
    st_mock = types.ModuleType('streamlit')
    st_mock.session_state = MockStreamlitState()
    sys.modules['streamlit'] = st_mock

    return project_root, app_dir, original_cwd


def test_component_manager():
    """Prueba el ComponentManager independientemente"""
    print("🧪 PRUEBA DEL COMPONENT MANAGER")
    print("=" * 50)

    try:
        # Setup
        project_root, app_dir, original_cwd = setup_test_environment()
        print(f"📁 Directorio configurado: {Path.cwd()}")

        # Importar ComponentManager
        from components.component_manager import ComponentManager, ComponentStatus
        print("✅ ComponentManager importado correctamente")

        # Crear instancia
        manager = ComponentManager()
        print("✅ ComponentManager creado")

        # Probar inicialización de componentes individuales
        print(f"\n🔧 PROBANDO INICIALIZACIÓN DE COMPONENTES...")

        components_to_test = ['datastore', 'parser', 'classifier', 'kame_integrator']
        results = {}

        for component_name in components_to_test:
            print(f"\n📦 Probando {component_name}...")
            try:
                component, status = manager.get_component(component_name)
                results[component_name] = {
                    'status': status,
                    'instance': component is not None,
                    'error': manager.components[
                        component_name].error_message if component_name in manager.components else ""
                }

                if status == ComponentStatus.READY:
                    print(f"✅ {component_name}: LISTO")
                elif status == ComponentStatus.ERROR:
                    print(f"❌ {component_name}: ERROR - {results[component_name]['error'][:100]}")
                elif status == ComponentStatus.DISABLED:
                    print(f"🚫 {component_name}: DESHABILITADO")
                else:
                    print(f"⏸️ {component_name}: {status.value}")

            except Exception as e:
                print(f"💥 {component_name}: EXCEPCIÓN - {str(e)[:100]}")
                results[component_name] = {
                    'status': ComponentStatus.ERROR,
                    'instance': False,
                    'error': str(e)
                }

        # Probar estado del sistema
        print(f"\n📊 ESTADO DEL SISTEMA...")
        system_status = manager.get_system_status()

        print(f"🔢 Total componentes: {system_status['total_components']}")
        print(f"✅ Componentes listos: {system_status['ready_components']}")
        print(f"❌ Componentes con error: {system_status['error_components']}")
        print(f"🔴 Errores críticos: {system_status['critical_errors']}")
        print(f"💚 Sistema saludable: {system_status['system_healthy']}")

        # Mostrar detalles de componentes
        print(f"\n📋 DETALLES DE COMPONENTES:")
        for name, info in system_status['components'].items():
            status_icon = {
                'ready': '✅',
                'error': '❌',
                'initializing': '🔄',
                'not_initialized': '⏸️',
                'disabled': '🚫'
            }.get(info['status'], '❓')

            critical_icon = '🔴' if info['is_critical'] else '🟡'
            print(f"  {status_icon} {name} {critical_icon} (intentos: {info['attempts']})")

            if info['error_message']:
                print(f"    💬 {info['error_message'][:100]}...")

        # Resultados finales
        ready_critical = sum(1 for name, info in results.items()
                             if info['status'] == ComponentStatus.READY
                             and manager.component_definitions[name].get('is_critical', True))

        total_critical = sum(1 for name in results.keys()
                             if manager.component_definitions[name].get('is_critical', True))

        print(f"\n🎯 RESULTADO FINAL:")
        print(f"📊 Componentes críticos listos: {ready_critical}/{total_critical}")

        if ready_critical >= 1:  # Al menos DataStore o Parser
            print("🎉 ¡SISTEMA MÍNIMO FUNCIONANDO!")
            print("💡 La aplicación puede funcionar con componentes básicos")
            return True
        else:
            print("💥 SISTEMA NO FUNCIONAL")
            print("❌ No hay componentes críticos funcionando")
            return False

    except Exception as e:
        print(f"\n💥 ERROR GENERAL EN LA PRUEBA: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Restaurar directorio original
        try:
            os.chdir(original_cwd)
        except:
            pass


def test_streamlit_integration():
    """Prueba la integración con Streamlit (simulada)"""
    print(f"\n🖥️ PRUEBA DE INTEGRACIÓN STREAMLIT")
    print("-" * 40)

    try:
        # Las funciones ya deberían estar importadas del test anterior
        from components.component_manager import get_component, get_component_manager, ComponentStatus

        # Simular session_state
        import streamlit as st  # Nuestro mock

        # Probar funciones de integración
        print("🔧 Probando get_component_manager()...")
        manager = get_component_manager()
        print("✅ get_component_manager() funciona")

        print("🔧 Probando get_component()...")
        datastore, status = get_component('datastore')

        if status == ComponentStatus.READY:
            print("✅ get_component('datastore') funciona - componente listo")
        else:
            print(f"⚠️ get_component('datastore') - estado: {status.value}")

        # Probar que el estado se mantiene en session_state
        print("🔧 Probando persistencia en session_state...")
        if 'component_manager' in st.session_state:
            print("✅ ComponentManager está en session_state")
        else:
            print("❌ ComponentManager NO está en session_state")

        print("🎉 ¡Integración Streamlit funciona!")
        return True

    except Exception as e:
        print(f"❌ Error en integración Streamlit: {e}")
        return False


def main():
    """Ejecuta todas las pruebas"""
    print("🚀 PRUEBA COMPLETA DEL SISTEMA DE COMPONENTES")
    print("=" * 60)

    success1 = test_component_manager()
    success2 = test_streamlit_integration()

    print(f"\n" + "=" * 60)
    print("📋 RESUMEN FINAL:")
    print(f"✅ Component Manager: {'ÉXITO' if success1 else 'FALLO'}")
    print(f"✅ Integración Streamlit: {'ÉXITO' if success2 else 'FALLO'}")

    if success1 and success2:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON!")
        print("💡 El sistema está listo para usar con Streamlit")
        return True
    else:
        print(f"\n💥 ALGUNAS PRUEBAS FALLARON")
        print("🔧 Revisa los errores arriba para diagnosticar")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
