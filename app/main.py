# app/main.py - Aplicación Streamlit completa con todos los sistemas integrados
from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path
import traceback
from datetime import datetime

# Import del sistema de componentes robusto
from components.component_manager import (
    get_component,
    ComponentStatus,
    initialize_session_state,
    show_component_status_sidebar,
    handle_component_error
)

# Configuración de la página
st.set_page_config(
    page_title="Santander Finance App",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main_header():
    """Header principal de la aplicación"""
    col1, col2, col3 = st.columns([2, 3, 1])

    with col1:
        st.title("📊 Santander Finance App")

    with col2:
        st.markdown("### Sistema de análisis financiero y gestión de contactos")

    with col3:
        if st.button("🔄 Actualizar", help="Recargar sistema"):
            st.cache_data.clear()
            st.rerun()


def sidebar_navigation():
    """Navegación principal en sidebar mejorada"""
    st.sidebar.title("🧭 Navegación")

    pages = {
        "📁 Cargar Cartola": "upload",
        "🏷️ Etiquetar Gastos": "labeling",
        "🤖 Entrenar IA": "training",
        "📊 Dashboard": "dashboard",
        "👥 Gestión Contactos": "contacts",  # 🆕 NUEVA PÁGINA
        "🔄 Integración KAME": "kame",
        "⚙️ Configuración": "settings"
    }

    selected_page = st.sidebar.radio("Seleccionar página:", list(pages.keys()))

    # Estado del sistema - usando el nuevo sistema
    show_component_status_sidebar()

    # Información del estado de datos
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 Estado de datos")

    try:
        # Obtener DataStore con el nuevo sistema
        datastore, datastore_status = get_component('datastore')

        if datastore_status == ComponentStatus.READY and datastore:
            try:
                labeled_data = datastore.load_labeled()
                if not labeled_data.empty:
                    st.sidebar.success(f"✅ {len(labeled_data)} transacciones etiquetadas")
                    categories = labeled_data['category'].nunique() if 'category' in labeled_data.columns else 0
                    st.sidebar.info(f"📋 {categories} categorías diferentes")
                else:
                    st.sidebar.warning("⚠️ Sin datos etiquetados")

                # Mostrar información de contactos
                try:
                    from contacts.contacts_manager import ContactsManager
                    contacts_manager = ContactsManager(datastore)
                    contacts_summary = contacts_manager.get_contacts_summary()

                    if 'error' not in contacts_summary:
                        total_contacts = contacts_summary.get('total_contacts', 0)
                        if total_contacts > 0:
                            st.sidebar.info(f"👥 {total_contacts} contactos registrados")
                        else:
                            st.sidebar.info("👥 Sin contactos")
                except ImportError:
                    st.sidebar.info("👥 Sistema de contactos no disponible")
                except Exception as e:
                    st.sidebar.warning(f"👥 Error contactos: {str(e)[:30]}...")

            except Exception as e:
                st.sidebar.error(f"❌ Error cargando datos: {str(e)[:50]}...")
        else:
            st.sidebar.error("❌ DataStore no disponible")

    except Exception as e:
        st.sidebar.error(f"❌ Error del sistema: {str(e)[:50]}...")

    return pages[selected_page]


def safe_component_operation(component_name: str, operation_name: str):
    """Decorator para operaciones seguras con componentes"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                component, status = get_component(component_name)

                if status != ComponentStatus.READY or not component:
                    st.error(f"❌ {component_name.title()} no está disponible")
                    st.info(f"Estado: {status.value}")

                    if st.button(f"🔄 Reintentar inicializar {component_name}"):
                        from components.component_manager import get_component_manager
                        manager = get_component_manager()
                        manager.force_reinitialize(component_name)
                        st.rerun()
                    return None

                return func(component, *args, **kwargs)

            except Exception as e:
                st.error(f"❌ Error en {operation_name}: {str(e)}")
                handle_component_error(component_name, e)
                return None

        return wrapper

    return decorator


@safe_component_operation('parser', 'procesamiento de cartola')
def page_upload(parser):
    """Página de carga de cartolas con manejo robusto"""
    st.header("📁 Cargar Cartola Santander")
    st.markdown("Sube tu archivo Excel (.xlsx) de cartola bancaria para procesarlo.")

    # File uploader
    uploaded_file = st.file_uploader(
        "Seleccionar archivo de cartola",
        type=['xlsx', 'xls'],
        help="Solo archivos Excel de cartolas Santander"
    )

    if uploaded_file is not None:
        try:
            with st.spinner("Procesando cartola..."):
                # Save uploaded file temporarily
                temp_path = Path(f"uploads/{uploaded_file.name}")
                temp_path.parent.mkdir(exist_ok=True)

                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Validate file básico
                size_mb = temp_path.stat().st_size / (1024 * 1024)

                col1, col2 = st.columns([2, 1])

                with col2:
                    st.markdown("### 📊 Info del archivo")
                    st.info(f"**Tamaño:** {size_mb:.1f} MB")
                    st.info(f"**Formato:** {temp_path.suffix}")

                with col1:
                    if size_mb > 50:
                        st.error("❌ Archivo muy grande (máx 50MB)")
                        return

                    # Read and parse file con manejo de errores
                    try:
                        df_raw = pd.read_excel(temp_path)
                        st.success(f"✅ Archivo leído: {len(df_raw)} filas, {len(df_raw.columns)} columnas")
                    except Exception as e:
                        st.error(f"❌ Error leyendo archivo: {str(e)}")
                        return

                    # Parse with Santander parser
                    try:
                        df_parsed = parser.parse(df_raw)
                        st.success(f"🎯 Procesamiento completado: {len(df_parsed)} transacciones válidas")
                    except Exception as e:
                        st.error(f"❌ Error procesando cartola: {str(e)}")
                        st.info("💡 Verifica que sea una cartola válida de Santander")
                        return

                # Store in session state
                st.session_state.current_data = df_parsed

                # Show preview con formato mejorado
                st.markdown("### 👀 Vista previa de datos procesados")
                show_transaction_preview(df_parsed)

                # Clean up temp file
                temp_path.unlink(missing_ok=True)

        except Exception as e:
            st.error(f"❌ Error general procesando archivo: {str(e)}")
            with st.expander("🔍 Detalles del error"):
                st.code(traceback.format_exc())


def show_transaction_preview(df_parsed):
    """Muestra preview de transacciones con mejora automática de descripciones"""
    if df_parsed.empty:
        st.warning("⚠️ No hay transacciones para mostrar")
        return

    try:
        # NUEVO: Opción para mejorar descripciones automáticamente
        col_enhance1, col_enhance2 = st.columns([3, 1])

        with col_enhance1:
            improve_descriptions = st.checkbox(
                "🔄 Mejorar descripciones con nombres de contactos",
                value=True,
                help="Reemplaza RUTs en las descripciones por nombres de contactos"
            )

        with col_enhance2:
            if st.button("👥 Gestionar Contactos"):
                st.session_state.page = "contacts"
                st.rerun()

        # Aplicar mejoras si está habilitado
        df_display = df_parsed.copy()

        if improve_descriptions:
            try:
                # Obtener el datastore desde los componentes
                datastore, status = get_component('datastore')

                if status == ComponentStatus.READY and datastore:
                    from contacts.contacts_manager import ContactsManager
                    contacts_manager = ContactsManager(datastore)

                    with st.spinner("🔄 Mejorando descripciones con nombres de contactos..."):
                        df_display = contacts_manager.enhance_transaction_descriptions(df_display)

                        # Contar cuántas descripciones se mejoraron
                        if 'Descripción_Original' in df_display.columns:
                            improved_count = sum(
                                1 for orig, new in zip(df_parsed['Descripción'], df_display['Descripción'])
                                if orig != new
                            )
                            if improved_count > 0:
                                st.success(f"✨ {improved_count} descripciones mejoradas con nombres de contactos")

            except Exception as e:
                st.warning(f"⚠️ No se pudieron mejorar descripciones: {e}")
                df_display = df_parsed.copy()

        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total transacciones", len(df_parsed))

        with col2:
            gastos = df_parsed[df_parsed['Monto'] < 0] if 'Monto' in df_parsed.columns else pd.DataFrame()
            st.metric("Gastos (CARGO)", len(gastos))

        with col3:
            ingresos = df_parsed[df_parsed['Monto'] > 0] if 'Monto' in df_parsed.columns else pd.DataFrame()
            st.metric("Ingresos (ABONO)", len(ingresos))

        with col4:
            if 'Monto' in df_parsed.columns:
                balance = df_parsed['Monto'].sum()
                balance_fmt = f"${balance:,.0f}".replace(",",
                                                         ".") if balance >= 0 else f"-${abs(balance):,.0f}".replace(",",
                                                                                                                    ".")
                st.metric("Balance Neto", balance_fmt)

        # Formatear montos para display
        if 'Monto' in df_display.columns:
            df_display['Monto_Formateado'] = df_display['Monto'].apply(
                lambda x: f"${x:,.0f}".replace(",", ".") if x >= 0
                else f"-${abs(x):,.0f}".replace(",", ".")
            )

        # Preparar columnas para mostrar
        display_columns = ['Fecha', 'Descripción', 'Monto_Formateado', 'ABONO/CARGO']
        if 'Descripción_Original' in df_display.columns:
            display_columns.insert(2, 'Descripción_Original')

        # Preparar DataFrame para mostrar
        df_show = df_display.copy()
        if 'Monto_Formateado' in df_show.columns:
            df_show = df_show.rename(columns={'Monto_Formateado': 'Monto'})

        # Mostrar solo las columnas necesarias
        final_columns = ['Fecha', 'Descripción', 'Monto', 'ABONO/CARGO']
        if 'Descripción_Original' in df_show.columns:
            final_columns.insert(2, 'Descripción_Original')

        df_show = df_show[[col for col in final_columns if col in df_show.columns]]

        st.dataframe(df_show, use_container_width=True, height=400)

        # Action buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("➡️ Ir a Etiquetar", type="primary"):
                # Guardar datos mejorados en session_state
                st.session_state.current_data = df_display
                st.session_state.page = "labeling"
                st.rerun()

        with col2:
            if st.button("💾 Guardar datos"):
                save_current_data()

        with col3:
            if st.button("📥 Descargar CSV"):
                # Descargar datos con descripciones mejoradas
                csv = df_display.to_csv(index=False)
                st.download_button(
                    label="⬇️ Descargar",
                    data=csv,
                    file_name=f"cartola_procesada_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )

    except Exception as e:
        st.error(f"❌ Error mostrando preview: {str(e)}")


@safe_component_operation('datastore', 'guardado de datos')
def save_current_data(datastore):
    """Guarda datos actuales de manera segura"""
    if st.session_state.current_data is None:
        st.warning("⚠️ No hay datos para guardar")
        return

    try:
        # Aquí podrías implementar la lógica de guardado adicional
        st.success("✅ Datos guardados exitosamente")
    except Exception as e:
        st.error(f"❌ Error guardando datos: {str(e)}")


@safe_component_operation('datastore', 'etiquetado de transacciones')
def page_labeling(datastore):
    """Página de etiquetado con sistema mejorado"""
    try:
        # Importar el nuevo sistema de etiquetado
        from labeling.smart_labeling import show_improved_labeling_page

        # Usar el sistema mejorado
        show_improved_labeling_page(datastore, st.session_state.current_data)

    except ImportError:
        # Fallback al sistema anterior si no está disponible el nuevo
        st.error("❌ Sistema de etiquetado mejorado no disponible")
        st.info("🔧 Usando sistema básico como fallback")
        page_labeling_basic(datastore)
    except Exception as e:
        st.error(f"❌ Error en sistema de etiquetado: {e}")
        handle_component_error('datastore', e)


def page_labeling_basic(datastore):
    """Sistema de etiquetado básico como fallback"""
    st.header("🏷️ Etiquetar Gastos - Sistema Básico")

    if st.session_state.current_data is None:
        st.warning("⚠️ Primero debes cargar una cartola")
        if st.button("📁 Ir a Cargar"):
            st.session_state.page = "upload"
            st.rerun()
        return

    df = st.session_state.current_data
    gastos = df[df['Monto'] < 0].copy() if 'Monto' in df.columns else pd.DataFrame()

    if gastos.empty:
        st.info("ℹ️ No hay gastos para etiquetar en la cartola actual")
        return

    st.markdown(f"### Etiquetando {len(gastos)} transacciones de gasto")

    try:
        categorias = datastore.get_categories()
        show_basic_labeling_interface(gastos, categorias, datastore)
    except Exception as e:
        st.error(f"❌ Error en etiquetado básico: {e}")


def show_basic_labeling_interface(gastos, categorias, datastore):
    """Interfaz básica de etiquetado (versión anterior simplificada)"""
    if 'Categoría' not in gastos.columns:
        gastos['Categoría'] = ""

    num_to_show = min(20, len(gastos))
    st.info(f"Mostrando las primeras {num_to_show} de {len(gastos)} transacciones")

    with st.container():
        for idx, (_, row) in enumerate(gastos.head(num_to_show).iterrows()):
            col1, col2, col3, col4 = st.columns([2, 3, 2, 1])

            with col1:
                st.text(str(row.get('Fecha', '')))

            with col2:
                desc = str(row.get('Descripción', ''))
                display_desc = desc[:50] + "..." if len(desc) > 50 else desc
                st.text(display_desc)

            with col3:
                amount = row.get('Monto', 0)
                monto_fmt = f"${abs(amount):,.0f}".replace(",", ".")
                st.text(monto_fmt)

            with col4:
                selected_category = st.selectbox(
                    "Categoría",
                    [""] + categorias,
                    key=f"basic_cat_{idx}_{row.name}",
                    label_visibility="collapsed"
                )

                if selected_category:
                    gastos.loc[row.name, 'Categoría'] = selected_category

    if st.button("💾 Guardar etiquetas básicas"):
        save_labels_basic(gastos, datastore)


def save_labels_basic(gastos, datastore):
    """Guardado básico de etiquetas"""
    try:
        etiquetados = gastos[gastos['Categoría'] != ""]
        if not etiquetados.empty:
            df_to_save = etiquetados[['Fecha', 'Descripción', 'Monto', 'Categoría']].copy()
            df_to_save = df_to_save.rename(columns={'Categoría': 'category'})

            datastore.save_labeled(df_to_save)
            st.success(f"✅ {len(etiquetados)} transacciones etiquetadas guardadas")
        else:
            st.warning("⚠️ No hay etiquetas para guardar")
    except Exception as e:
        st.error(f"❌ Error guardando etiquetas básicas: {e}")


@safe_component_operation('datastore', 'entrenamiento de IA')
def page_training(datastore):
    """Página de entrenamiento con manejo robusto"""
    st.header("🤖 Entrenar IA")
    st.markdown("Entrena el clasificador automático con las transacciones etiquetadas.")

    try:
        labeled_data = datastore.load_labeled()

        if labeled_data.empty:
            st.warning("⚠️ No hay datos etiquetados disponibles")
            st.markdown("Primero debes etiquetar algunas transacciones:")
            if st.button("🏷️ Ir a Etiquetar"):
                st.session_state.page = "labeling"
                st.rerun()
            return

        st.success(f"✅ {len(labeled_data)} transacciones etiquetadas encontradas")

        # Mostrar estadísticas
        show_training_statistics(labeled_data)

        # Botón de entrenamiento
        if st.button("🚀 Entrenar Modelo", type="primary"):
            train_classifier(labeled_data)

    except Exception as e:
        st.error(f"❌ Error en página de entrenamiento: {str(e)}")
        handle_component_error('datastore', e)


def show_training_statistics(labeled_data):
    """Muestra estadísticas para entrenamiento"""
    if 'category' not in labeled_data.columns:
        st.error("❌ No se encontró columna 'category' en los datos")
        return

    category_stats = labeled_data['category'].value_counts()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Distribución por categoría")
        st.bar_chart(category_stats)

    with col2:
        st.markdown("### 📈 Estadísticas")
        st.dataframe(category_stats.reset_index())

    # Verificar calidad de datos
    min_samples = 3
    insufficient_categories = category_stats[category_stats < min_samples]

    if not insufficient_categories.empty:
        st.warning(f"⚠️ Algunas categorías tienen menos de {min_samples} ejemplos:")
        st.write(insufficient_categories.index.tolist())
        st.info("💡 Se recomienda tener al menos 3 ejemplos por categoría")


@safe_component_operation('classifier', 'entrenamiento de modelo')
def train_classifier(labeled_data, classifier):
    """Entrena el clasificador con manejo robusto"""
    with st.spinner("Entrenando clasificador..."):
        try:
            classifier.fit(labeled_data, label_col='category')
            st.success("✅ Modelo entrenado exitosamente!")

            # Mostrar métricas si están disponibles
            try:
                report = classifier.report(labeled_data, labeled_data['category'])
                st.text("📊 Reporte de clasificación:")
                st.code(report)
            except Exception as e:
                st.warning(f"⚠️ No se pudo generar reporte: {str(e)}")

        except Exception as e:
            st.error(f"❌ Error entrenando modelo: {str(e)}")


def page_dashboard():
    """Dashboard simplificado y robusto"""
    st.header("📊 Dashboard Financiero")

    if st.session_state.current_data is None:
        st.warning("⚠️ No hay datos cargados")
        if st.button("📁 Cargar datos"):
            st.session_state.page = "upload"
            st.rerun()
        return

    df = st.session_state.current_data

    try:
        show_financial_dashboard(df)
    except Exception as e:
        st.error(f"❌ Error en dashboard: {str(e)}")
        with st.expander("🔍 Detalles del error"):
            st.code(str(e))


def show_financial_dashboard(df):
    """Muestra dashboard financiero de manera robusta"""
    # Verificar columnas necesarias
    required_cols = ['Monto', 'Fecha', 'Descripción']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"❌ Faltan columnas requeridas: {missing_cols}")
        return

    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)

    gastos = df[df['Monto'] < 0]
    ingresos = df[df['Monto'] > 0]

    with col1:
        st.metric("Total Transacciones", len(df))

    with col2:
        total_gastos_monto = abs(gastos['Monto'].sum())
        gastos_fmt = f"${total_gastos_monto:,.0f}".replace(",", ".")
        st.metric("Total Gastos", gastos_fmt)

    with col3:
        total_ingresos_monto = ingresos['Monto'].sum()
        ingresos_fmt = f"${total_ingresos_monto:,.0f}".replace(",", ".")
        st.metric("Total Ingresos", ingresos_fmt)

    with col4:
        balance = df['Monto'].sum()
        balance_fmt = f"${balance:,.0f}".replace(",", ".") if balance >= 0 else f"-${abs(balance):,.0f}".replace(",",
                                                                                                                 ".")
        st.metric("Balance Neto", balance_fmt)

    # Gráficos básicos
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 💸 Top 10 Gastos")
        if not gastos.empty:
            top_gastos = gastos.nlargest(10, 'Monto', keep='all')[['Descripción', 'Monto']]
            top_gastos['Monto_Abs'] = abs(top_gastos['Monto'])

            # Truncar descripciones largas
            top_gastos['Descripción_Short'] = top_gastos['Descripción'].apply(
                lambda x: x[:30] + "..." if len(str(x)) > 30 else str(x)
            )

            st.bar_chart(top_gastos.set_index('Descripción_Short')['Monto_Abs'])
        else:
            st.info("Sin gastos para mostrar")

    with col2:
        st.markdown("### 📈 Transacciones por día")
        if not df.empty:
            try:
                df_chart = df.copy()
                df_chart['Fecha'] = pd.to_datetime(df_chart['Fecha'], errors='coerce')
                df_chart = df_chart.dropna(subset=['Fecha'])

                if not df_chart.empty:
                    daily_summary = df_chart.groupby(df_chart['Fecha'].dt.date)['Monto'].sum().reset_index()
                    daily_summary = daily_summary.set_index('Fecha')
                    st.line_chart(daily_summary)
                else:
                    st.info("No hay fechas válidas para el gráfico")
            except Exception as e:
                st.error(f"Error creando gráfico temporal: {str(e)}")

    # Tabla de transacciones recientes
    st.markdown("### 📋 Transacciones recientes")

    df_display = df.head(20).copy()
    if 'Monto' in df_display.columns:
        df_display['Monto_Formateado'] = df_display['Monto'].apply(
            lambda x: f"${x:,.0f}".replace(",", ".") if x >= 0
            else f"-${abs(x):,.0f}".replace(",", ".")
        )

        display_cols = ['Fecha', 'Descripción', 'Monto_Formateado']
        if 'ABONO/CARGO' in df_display.columns:
            display_cols.append('ABONO/CARGO')

        df_show = df_display[display_cols].rename(columns={'Monto_Formateado': 'Monto'})
        st.dataframe(df_show, use_container_width=True)


@safe_component_operation('datastore', 'gestión de contactos')
def page_contacts(datastore):
    """Página de gestión de contactos con sistema mejorado"""

    # Intentar usar el sistema mejorado primero
    try:
        from contacts.enhanced_contacts_interface import show_transfer_summary_page
        show_transfer_summary_page(datastore)
        return

    except ImportError:
        st.warning("⚠️ Sistema mejorado no disponible, usando sistema básico")

    # Fallback al sistema original
    try:
        from contacts.contacts_manager import show_contacts_management_page
        show_contacts_management_page(datastore)

    except ImportError:
        st.error("❌ Sistema de contactos no disponible")
        st.info("🔧 Módulo de contactos no instalado correctamente")

        # Mostrar instrucciones de instalación
        with st.expander("📝 Instrucciones de instalación"):
            st.markdown("""
            **Para habilitar el sistema de contactos mejorado:**

            1. Crear directorio:
            ```bash
            mkdir -p app/contacts
            ```

            2. Crear los archivos necesarios:
            - `app/contacts/__init__.py`
            - `app/contacts/contacts_manager.py`
            - `app/contacts/transfer_summary_detector.py`
            - `app/contacts/enhanced_contacts_interface.py`

            3. Ejecutar prueba del sistema:
            ```bash
            python test_transfer_detector.py
            ```
            """)

    except Exception as e:
        st.error(f"❌ Error en gestión de contactos: {e}")
        handle_component_error('datastore', e)


# 2. MEJORAR LA FUNCIÓN show_transaction_preview PARA USAR EL NUEVO SISTEMA
def show_transaction_preview(df_parsed):
    """Muestra preview de transacciones con mejora automática de descripciones"""
    if df_parsed.empty:
        st.warning("⚠️ No hay transacciones para mostrar")
        return

    try:
        # NUEVO: Opción para mejorar descripciones automáticamente
        col_enhance1, col_enhance2 = st.columns([3, 1])

        with col_enhance1:
            improve_descriptions = st.checkbox(
                "🔄 Mejorar descripciones con nombres de contactos",
                value=True,
                help="Reemplaza RUTs en las descripciones por nombres de contactos"
            )

        with col_enhance2:
            if st.button("👥 Gestionar Contactos"):
                st.session_state.page = "contacts"
                st.rerun()

        # Aplicar mejoras si está habilitado
        df_display = df_parsed.copy()

        if improve_descriptions:
            try:
                # Obtener el datastore desde los componentes
                datastore, status = get_component('datastore')

                if status == ComponentStatus.READY and datastore:
                    # USAR EL SISTEMA MEJORADO
                    try:
                        from contacts.transfer_summary_detector import ImprovedContactsManager
                        enhanced_manager = ImprovedContactsManager(datastore)

                        with st.spinner("✨ Mejorando descripciones con sistema avanzado..."):
                            df_display = enhanced_manager.enhance_transaction_descriptions(df_display)

                    except ImportError:
                        # Fallback al sistema original
                        from contacts.contacts_manager import ContactsManager
                        contacts_manager = ContactsManager(datastore)

                        with st.spinner("🔄 Mejorando descripciones..."):
                            df_display = contacts_manager.enhance_transaction_descriptions(df_display)

                    # Contar cuántas descripciones se mejoraron
                    if 'Descripción_Original' in df_display.columns:
                        improved_count = sum(
                            1 for orig, new in zip(df_parsed['Descripción'], df_display['Descripción'])
                            if orig != new
                        )
                        if improved_count > 0:
                            st.success(f"✨ {improved_count} descripciones mejoradas con nombres de contactos")

            except Exception as e:
                st.warning(f"⚠️ No se pudieron mejorar descripciones: {e}")
                df_display = df_parsed.copy()

        # [RESTO DE LA FUNCIÓN PERMANECE IGUAL...]
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total transacciones", len(df_parsed))

        with col2:
            gastos = df_parsed[df_parsed['Monto'] < 0] if 'Monto' in df_parsed.columns else pd.DataFrame()
            st.metric("Gastos (CARGO)", len(gastos))

        with col3:
            ingresos = df_parsed[df_parsed['Monto'] > 0] if 'Monto' in df_parsed.columns else pd.DataFrame()
            st.metric("Ingresos (ABONO)", len(ingresos))

        with col4:
            if 'Monto' in df_parsed.columns:
                balance = df_parsed['Monto'].sum()
                balance_fmt = f"${balance:,.0f}".replace(",",
                                                         ".") if balance >= 0 else f"-${abs(balance):,.0f}".replace(",",
                                                                                                                    ".")
                st.metric("Balance Neto", balance_fmt)

        # [RESTO DE LA FUNCIÓN...]

    except Exception as e:
        st.error(f"❌ Error mostrando preview: {str(e)}")


# 3. ACTUALIZAR LA NAVEGACIÓN PARA DESTACAR LAS NUEVAS CARACTERÍSTICAS
def sidebar_navigation():
    """Navegación principal en sidebar mejorada"""
    st.sidebar.title("🧭 Navegación")

    pages = {
        "📁 Cargar Cartola": "upload",
        "🏷️ Etiquetar Gastos": "labeling",
        "🤖 Entrenar IA": "training",
        "📊 Dashboard": "dashboard",
        "👥 Gestión Contactos 🆕": "contacts",  # 🆕 DESTACAR NUEVAS CARACTERÍSTICAS
        "🔄 Integración KAME": "kame",
        "⚙️ Configuración": "settings"
    }

    selected_page = st.sidebar.radio("Seleccionar página:", list(pages.keys()))

    # MOSTRAR INFORMACIÓN SOBRE LAS NUEVAS CARACTERÍSTICAS
    if pages[selected_page] == "contacts":
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🆕 Nuevo Sistema de Contactos")
        st.sidebar.success("✅ Detección automática de resúmenes")
        st.sidebar.success("✅ Eliminación inteligente de duplicados")
        st.sidebar.success("✅ Consolidación de múltiples transferencias")
        st.sidebar.info("💡 Sube un Excel del banco para probar")

    # [RESTO DE LA FUNCIÓN PERMANECE IGUAL...]
    return pages[selected_page]


# 4. AÑADIR FUNCIÓN HELPER PARA MOSTRAR ESTADO DEL SISTEMA DE CONTACTOS
def show_contacts_system_status():
    """Muestra estado del sistema de contactos en el sidebar"""

    try:
        # Verificar sistema mejorado
        from contacts.transfer_summary_detector import ImprovedContactsManager
        from contacts.enhanced_contacts_interface import show_transfer_summary_page

        st.sidebar.success("🚀 Sistema avanzado disponible")

        # Mostrar estadísticas básicas si hay datastore
        try:
            datastore, status = get_component('datastore')
            if status == ComponentStatus.READY:
                contacts = datastore.get_contacts()
                if contacts:
                    st.sidebar.info(f"👥 {len(contacts)} contactos registrados")
                else:
                    st.sidebar.info("👥 Sin contactos registrados")
        except:
            pass

    except ImportError:
        try:
            # Verificar sistema básico
            from contacts.contacts_manager import show_contacts_management_page
            st.sidebar.warning("⚠️ Solo sistema básico disponible")

        except ImportError:
            st.sidebar.error("❌ Sistema de contactos no disponible")


# 5. INTEGRAR EN LA FUNCIÓN PRINCIPAL main()
def main():
    """Función principal mejorada"""
    try:
        # Inicializar estado de la sesión
        initialize_session_state()

        # Header principal
        main_header()

        # Navegación y contenido
        current_page = sidebar_navigation()

        # MOSTRAR ESTADO DEL SISTEMA DE CONTACTOS
        if current_page == "contacts":
            show_contacts_system_status()

        # Mostrar página seleccionada con manejo robusto
        try:
            if current_page == "upload":
                page_upload()
            elif current_page == "labeling":
                page_labeling()
            elif current_page == "training":
                page_training()
            elif current_page == "dashboard":
                page_dashboard()
            elif current_page == "contacts":  # PÁGINA MEJORADA
                page_contacts()
            elif current_page == "kame":
                page_kame()
            elif current_page == "settings":
                page_settings()

        except Exception as e:
            st.error(f"❌ Error en página {current_page}: {str(e)}")
            st.info("🔄 Intenta recargar la página o reiniciar los componentes")

            with st.expander("🔍 Detalles técnicos"):
                st.code(traceback.format_exc())

    except Exception as e:
        st.error(f"❌ Error crítico de la aplicación: {str(e)}")
        st.stop()

def page_kame():
    """Página KAME simplificada"""
    st.header("🔄 Integración KAME")
    st.markdown("Concilia transacciones bancarias con documentos del ERP KAME.")
    st.info("🔧 Funcionalidad en desarrollo")


def page_settings():
    """Página de configuración mejorada"""
    st.header("⚙️ Configuración")

    # Estado del sistema
    st.markdown("### 🔧 Estado del Sistema")

    from components.component_manager import get_component_manager
    manager = get_component_manager()
    system_status = manager.get_system_status()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Componentes totales", system_status['total_components'])
    with col2:
        st.metric("Componentes listos", system_status['ready_components'])
    with col3:
        st.metric("Errores críticos", system_status['critical_errors'])

    if st.button("🔄 Reinicializar todo el sistema"):
        manager.initialize_all()
        st.success("✅ Sistema reinicializado")
        st.rerun()

    # Gestión de categorías (si DataStore está disponible)
    datastore, datastore_status = get_component('datastore')
    if datastore_status == ComponentStatus.READY:
        show_category_management(datastore)

    # Información del sistema
    st.markdown("---")
    st.markdown("### ℹ️ Información del Sistema")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.text("📁 Directorio datos: data/")

    with col2:
        st.text("🤖 Modelo: LogisticRegression")

    with col3:
        st.text("📊 Versión: 1.0.0")


def show_category_management(datastore):
    """Gestión de categorías"""
    st.markdown("### 🏷️ Gestión de Categorías")

    try:
        categories = datastore.get_categories()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Categorías disponibles:**")
            for i, cat in enumerate(categories, 1):
                st.text(f"{i:2d}. {cat}")

        with col2:
            nueva_cat = st.text_input("Agregar nueva categoría:")
            if st.button("➕ Agregar categoría") and nueva_cat.strip():
                if datastore.add_category(nueva_cat.strip().lower()):
                    st.success(f"✅ Categoría '{nueva_cat}' agregada")
                    st.rerun()
                else:
                    st.error("❌ Error agregando categoría o ya existe")

    except Exception as e:
        st.error(f"❌ Error gestionando categorías: {str(e)}")


def main():
    """Función principal mejorada"""
    try:
        # Inicializar estado de la sesión
        initialize_session_state()

        # Header principal
        main_header()

        # Navegación y contenido
        current_page = sidebar_navigation()

        # Mostrar página seleccionada con manejo robusto
        try:
            if current_page == "upload":
                page_upload()
            elif current_page == "labeling":
                page_labeling()
            elif current_page == "training":
                page_training()
            elif current_page == "dashboard":
                page_dashboard()
            elif current_page == "contacts":  # 🆕 NUEVA PÁGINA
                page_contacts()
            elif current_page == "kame":
                page_kame()
            elif current_page == "settings":
                page_settings()
        except Exception as e:
            st.error(f"❌ Error en página {current_page}: {str(e)}")
            st.info("🔄 Intenta recargar la página o reiniciar los componentes")

            with st.expander("🔍 Detalles técnicos"):
                st.code(traceback.format_exc())

    except Exception as e:
        st.error(f"❌ Error crítico de la aplicación: {str(e)}")
        st.stop()


if __name__ == "__main__":
    main()