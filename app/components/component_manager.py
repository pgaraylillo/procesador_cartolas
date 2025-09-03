# app/components/component_manager.py - Sistema robusto de gestión de componentes
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, Tuple
from enum import Enum
import streamlit as st
import logging
import traceback
from datetime import datetime


class ComponentStatus(Enum):
    """Estados posibles de un componente"""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ComponentInfo:
    """Información de un componente"""
    name: str
    status: ComponentStatus = ComponentStatus.NOT_INITIALIZED
    instance: Any = None
    error_message: str = ""
    last_check: Optional[datetime] = None
    initialization_attempts: int = 0
    max_attempts: int = 3
    is_critical: bool = True


class ComponentManager:
    """Gestor robusto de componentes para Streamlit"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.components: Dict[str, ComponentInfo] = {}
        self._setup_component_definitions()

    def _setup_component_definitions(self):
        """Define los componentes y sus configuraciones"""
        self.component_definitions = {
            'datastore': {
                'factory': self._create_datastore,
                'health_check': self._check_datastore_health,
                'is_critical': True,
                'max_attempts': 5
            },
            'parser': {
                'factory': self._create_parser,
                'health_check': self._check_parser_health,
                'is_critical': True,
                'max_attempts': 3
            },
            'classifier': {
                'factory': self._create_classifier,
                'health_check': self._check_classifier_health,
                'is_critical': False,
                'max_attempts': 3
            },
            'kame_integrator': {
                'factory': self._create_kame_integrator,
                'health_check': self._check_kame_health,
                'is_critical': False,
                'max_attempts': 3
            }
        }

    def get_component(self, name: str, auto_initialize: bool = True) -> Tuple[Any, ComponentStatus]:
        """Obtiene un componente, inicializándolo si es necesario"""

        # Si no existe, crear info del componente
        if name not in self.components:
            definition = self.component_definitions.get(name)
            if not definition:
                return None, ComponentStatus.ERROR

            self.components[name] = ComponentInfo(
                name=name,
                is_critical=definition.get('is_critical', True),
                max_attempts=definition.get('max_attempts', 3)
            )

        component_info = self.components[name]

        # Si está listo y funcionando, retornarlo
        if component_info.status == ComponentStatus.READY and component_info.instance:
            # Verificar salud periódicamente
            if self._should_check_health(component_info):
                if not self._check_component_health(name):
                    component_info.status = ComponentStatus.ERROR
                    component_info.instance = None

        # Si no está listo y se solicita inicialización automática
        if component_info.status != ComponentStatus.READY and auto_initialize:
            self._initialize_component(name)

        return component_info.instance, component_info.status

    def _initialize_component(self, name: str):
        """Inicializa un componente específico"""
        component_info = self.components[name]
        definition = self.component_definitions.get(name)

        if not definition:
            component_info.status = ComponentStatus.ERROR
            component_info.error_message = f"Definición no encontrada para {name}"
            return

        # Verificar límite de intentos
        if component_info.initialization_attempts >= component_info.max_attempts:
            component_info.status = ComponentStatus.DISABLED
            component_info.error_message = f"Máximo de intentos alcanzado ({component_info.max_attempts})"
            self.logger.error(f"❌ Componente {name} deshabilitado por exceder intentos")
            return

        component_info.status = ComponentStatus.INITIALIZING
        component_info.initialization_attempts += 1
        component_info.last_check = datetime.now()

        try:
            self.logger.info(f"🔧 Inicializando componente: {name}")

            # Crear instancia
            factory = definition['factory']
            instance = factory()

            # Verificar salud
            health_check = definition.get('health_check')
            if health_check and not health_check(instance):
                raise Exception(f"Health check falló para {name}")

            # Éxito
            component_info.instance = instance
            component_info.status = ComponentStatus.READY
            component_info.error_message = ""

            self.logger.info(f"✅ Componente {name} inicializado exitosamente")

        except Exception as e:
            component_info.status = ComponentStatus.ERROR
            component_info.error_message = str(e)
            component_info.instance = None

            self.logger.error(f"❌ Error inicializando {name}: {e}")

            # Log completo para componentes críticos
            if component_info.is_critical:
                self.logger.error(f"Stack trace para {name}: {traceback.format_exc()}")

    def _should_check_health(self, component_info: ComponentInfo) -> bool:
        """Determina si es momento de verificar la salud del componente"""
        if not component_info.last_check:
            return True

        # Verificar cada 5 minutos
        time_since_check = datetime.now() - component_info.last_check
        return time_since_check.total_seconds() > 300

    def _check_component_health(self, name: str) -> bool:
        """Verifica la salud de un componente"""
        component_info = self.components[name]
        definition = self.component_definitions.get(name)

        if not definition or not component_info.instance:
            return False

        try:
            health_check = definition.get('health_check')
            if health_check:
                result = health_check(component_info.instance)
                component_info.last_check = datetime.now()
                return result
            return True
        except Exception as e:
            self.logger.warning(f"⚠️ Health check falló para {name}: {e}")
            return False

    def force_reinitialize(self, name: str):
        """Fuerza la reinicialización de un componente"""
        if name in self.components:
            component_info = self.components[name]
            component_info.status = ComponentStatus.NOT_INITIALIZED
            component_info.instance = None
            component_info.initialization_attempts = 0
            component_info.error_message = ""

        self._initialize_component(name)

    def get_system_status(self) -> Dict:
        """Obtiene estado completo del sistema"""
        status = {
            'total_components': len(self.components),
            'ready_components': 0,
            'error_components': 0,
            'critical_errors': 0,
            'components': {}
        }

        for name, info in self.components.items():
            status['components'][name] = {
                'status': info.status.value,
                'is_critical': info.is_critical,
                'error_message': info.error_message,
                'attempts': info.initialization_attempts,
                'last_check': info.last_check.isoformat() if info.last_check else None
            }

            if info.status == ComponentStatus.READY:
                status['ready_components'] += 1
            elif info.status == ComponentStatus.ERROR:
                status['error_components'] += 1
                if info.is_critical:
                    status['critical_errors'] += 1

        status['system_healthy'] = status['critical_errors'] == 0
        return status

    def initialize_all(self):
        """Inicializa todos los componentes"""
        self.logger.info("🚀 Inicializando todos los componentes...")

        for name in self.component_definitions.keys():
            self._initialize_component(name)

    # === FACTORIES DE COMPONENTES ===

    def _create_datastore(self):
        """Crea instancia de DataStore"""
        from storage.datastore import DataStore
        return DataStore()

    def _create_parser(self):
        """Crea instancia de SantanderParser"""
        from bankstatements.santander import SantanderParser
        return SantanderParser()

    def _create_classifier(self):
        """Crea instancia de ExpenseClassifier"""
        from ml.classifier import ExpenseClassifier
        return ExpenseClassifier()

    def _create_kame_integrator(self):
        """Crea instancia de KameIntegrator"""
        from kame.kame_report import KameIntegrator
        return KameIntegrator()

    # === HEALTH CHECKS ===

    def _check_datastore_health(self, datastore) -> bool:
        """Verifica salud del DataStore"""
        try:
            return datastore.is_ready() if hasattr(datastore, 'is_ready') else True
        except:
            return False

    def _check_parser_health(self, parser) -> bool:
        """Verifica salud del Parser"""
        try:
            # Test básico con DataFrame vacío
            import pandas as pd
            test_df = pd.DataFrame()
            return hasattr(parser, 'parse')
        except:
            return False

    def _check_classifier_health(self, classifier) -> bool:
        """Verifica salud del Classifier"""
        try:
            return hasattr(classifier, 'fit') and hasattr(classifier, 'predict')
        except:
            return False

    def _check_kame_health(self, kame) -> bool:
        """Verifica salud del KameIntegrator"""
        try:
            return hasattr(kame, 'load')
        except:
            return False


# === INTEGRACIÓN CON STREAMLIT ===

def get_component_manager() -> ComponentManager:
    """Obtiene o crea el ComponentManager global"""
    if 'component_manager' not in st.session_state:
        st.session_state.component_manager = ComponentManager()
    return st.session_state.component_manager


def get_component(name: str, auto_initialize: bool = True) -> Tuple[Any, ComponentStatus]:
    """Función helper para obtener componentes desde Streamlit"""
    manager = get_component_manager()
    return manager.get_component(name, auto_initialize)


def show_component_status_sidebar():
    """Muestra estado de componentes en sidebar"""
    manager = get_component_manager()
    status = manager.get_system_status()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 Estado del Sistema")

    # Indicador general
    if status['system_healthy']:
        st.sidebar.success("✅ Sistema funcionando")
    else:
        st.sidebar.error(f"❌ {status['critical_errors']} errores críticos")

    # Detalles de componentes
    with st.sidebar.expander("📊 Detalles de componentes"):
        for name, info in status['components'].items():
            status_icon = {
                'ready': '✅',
                'error': '❌',
                'initializing': '🔄',
                'not_initialized': '⏸️',
                'disabled': '🚫'
            }.get(info['status'], '❓')

            critical_icon = '🔴' if info['is_critical'] else '🟡'

            st.markdown(f"{status_icon} **{name}** {critical_icon}")
            if info['error_message']:
                st.caption(f"Error: {info['error_message'][:50]}...")
            if info['attempts'] > 1:
                st.caption(f"Intentos: {info['attempts']}")

    # Botón de reinicio
    if st.sidebar.button("🔄 Reiniciar Componentes"):
        manager.initialize_all()
        st.rerun()


def initialize_session_state():
    """Inicializa el estado de la sesión de manera robusta"""
    # Solo inicializar datos básicos, no componentes pesados
    if 'current_data' not in st.session_state:
        st.session_state.current_data = None

    if 'labeled_data' not in st.session_state:
        st.session_state.labeled_data = None

    if 'page' not in st.session_state:
        st.session_state.page = 'upload'

    # Los componentes se inicializan bajo demanda
    manager = get_component_manager()

    # Solo inicializar componentes críticos automáticamente
    critical_components = ['datastore', 'parser']
    for component_name in critical_components:
        manager.get_component(component_name, auto_initialize=True)


def handle_component_error(component_name: str, error: Exception, fallback_fn: Callable = None):
    """Maneja errores de componentes graciosamente"""
    st.error(f"❌ Error en {component_name}: {str(error)}")

    manager = get_component_manager()

    col1, col2 = st.columns(2)

    with col1:
        if st.button(f"🔄 Reintentar {component_name}"):
            manager.force_reinitialize(component_name)
            st.rerun()

    with col2:
        if fallback_fn and st.button("🛠️ Usar modo simplificado"):
            fallback_fn()

    # Mostrar detalles técnicos en expander
    with st.expander("🔍 Detalles técnicos"):
        st.code(str(error))

        component_info = manager.components.get(component_name)
        if component_info:
            st.json({
                'status': component_info.status.value,
                'attempts': component_info.initialization_attempts,
                'is_critical': component_info.is_critical,
                'last_check': component_info.last_check.isoformat() if component_info.last_check else None
            })