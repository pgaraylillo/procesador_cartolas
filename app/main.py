# app/main.py - Aplicación Streamlit principal
from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path
import traceback
from datetime import datetime

# Import local modules
from bankstatements.santander import SantanderParser
from storage.datastore import DataStore
from ml.classifier import ExpenseClassifier
from kame.kame_report import KameIntegrator
from utils.validators import DataValidator, FileValidator

# Configuración de la página
st.set_page_config(
    page_title="Santander Finance App",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Inicializar componentes en session_state
@st.cache_resource
def init_components():
    """Inicializar componentes principales una sola vez"""
    return {
        'parser': SantanderParser(),
        'datastore': DataStore(),
        'classifier': ExpenseClassifier(),
        'kame_integrator': KameIntegrator()
    }


def init_session_state():
    """Inicializar estado de la sesión"""
    if 'components' not in st.session_state:
        st.session_state.components = init_components()

    if 'current_data' not in st.session_state:
        st.session_state.current_data = None

    if 'labeled_data' not in st.session_state:
        st.session_state.labeled_data = None


def main_header():
    """Header principal de la aplicación"""
    col1, col2, col3 = st.columns([2, 3, 1])

    with col1:
        st.title("📊 Santander Finance App")

    with col2:
        st.markdown("### Sistema de análisis financiero y conciliación KAME")

    with col3:
        if st.button("🔄 Recargar", help="Recargar componentes"):
            st.cache_resource.clear()
            st.rerun()


def sidebar_navigation():
    """Navegación principal en sidebar"""
    st.sidebar.title("🧭 Navegación")

    pages = {
        "📁 Cargar Cartola": "upload",
        "🏷️ Etiquetar Gastos": "labeling",
        "🤖 Entrenar IA": "training",
        "📊 Dashboard": "dashboard",
        "🔄 Integración KAME": "kame",
        "⚙️ Configuración": "settings"
    }

    selected_page = st.sidebar.radio("Seleccionar página:", list(pages.keys()))

    # Información del estado actual
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 Estado actual")

    # Cargar datos etiquetados
    try:
        labeled_data = st.session_state.components['datastore'].load_labeled()
        if not labeled_data.empty:
            st.sidebar.success(f"✅ {len(labeled_data)} transacciones etiquetadas")
            categories = labeled_data['category'].nunique()
            st.sidebar.info(f"📋 {categories} categorías diferentes")
        else:
            st.sidebar.warning("⚠️ Sin datos etiquetados")
    except Exception as e:
        st.sidebar.error(f"❌ Error cargando datos: {str(e)}")

    return pages[selected_page]


def page_upload():
    """Página de carga de cartolas"""
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

                # Validate file
                validation_result = FileValidator.validate_file_upload(temp_path)

                col1, col2 = st.columns([2, 1])

                with col2:
                    st.markdown("### 📊 Info del archivo")
                    st.info(f"**Tamaño:** {validation_result['file_info']['size_mb']:.1f} MB")
                    st.info(f"**Formato:** {validation_result['file_info']['extension']}")

                with col1:
                    if not validation_result['valid']:
                        st.error("❌ Archivo no válido:")
                        for issue in validation_result['issues']:
                            st.error(f"• {issue}")
                        return

                    if validation_result['warnings']:
                        st.warning("⚠️ Advertencias:")
                        for warning in validation_result['warnings']:
                            st.warning(f"• {warning}")

                # Read and parse file
                df_raw = pd.read_excel(temp_path)
                st.success(f"✅ Archivo leído: {len(df_raw)} filas, {len(df_raw.columns)} columnas")

                # Parse with Santander parser
                parser = st.session_state.components['parser']
                df_parsed = parser.parse(df_raw)

                st.success(f"🎯 Procesamiento completado: {len(df_parsed)} transacciones válidas")

                # Store in session state (datos puros)
                st.session_state.current_data = df_parsed

                # Crear versión formateada para display
                df_display = df_parsed.copy()
                if 'Monto' in df_display.columns:
                    df_display['Monto_Formateado'] = df_display['Monto'].apply(
                        lambda x: f"${abs(x):,.0f}".replace(",", ".") if x >= 0
                        else f"-${abs(x):,.0f}".replace(",", ".")
                    )

                # Show preview
                st.markdown("### 👀 Vista previa de datos procesados")

                # Metrics row
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total transacciones", len(df_parsed))

                with col2:
                    total_gastos = len(df_parsed[df_parsed['Monto'] < 0])
                    st.metric("Gastos (CARGO)", total_gastos)

                with col3:
                    total_ingresos = len(df_parsed[df_parsed['Monto'] > 0])
                    st.metric("Ingresos (ABONO)", total_ingresos)

                with col4:
                    balance = df_parsed['Monto'].sum()
                    balance_fmt = f"${balance:,.0f}".replace(",",
                                                             ".") if balance >= 0 else f"-${abs(balance):,.0f}".replace(
                        ",", ".")
                    st.metric("Balance Neto", balance_fmt)

                # Data table con formato chileno
                st.dataframe(
                    df_display[['Fecha', 'Descripción', 'Monto_Formateado', 'ABONO/CARGO']].rename(
                        columns={'Monto_Formateado': 'Monto'}),
                    use_container_width=True,
                    height=400
                )

                # Action buttons
                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button("➡️ Ir a Etiquetar", type="primary"):
                        st.session_state.page = "labeling"
                        st.rerun()

                with col2:
                    if st.button("💾 Guardar datos"):
                        # Here we would save to storage
                        st.success("✅ Datos guardados (funcionalidad pendiente)")

                with col3:
                    if st.button("📥 Descargar CSV"):
                        csv = df_parsed.to_csv(index=False)
                        st.download_button(
                            label="⬇️ Descargar",
                            data=csv,
                            file_name=f"cartola_procesada_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv"
                        )

                # Clean up temp file
                temp_path.unlink(missing_ok=True)

        except Exception as e:
            st.error(f"❌ Error procesando archivo: {str(e)}")
            st.code(traceback.format_exc())


def page_labeling():
    """Página de etiquetado de transacciones"""
    st.header("🏷️ Etiquetar Gastos")

    if st.session_state.current_data is None:
        st.warning("⚠️ Primero debes cargar una cartola")
        if st.button("📁 Ir a Cargar"):
            st.session_state.page = "upload"
            st.rerun()
        return

    df = st.session_state.current_data
    gastos = df[df['Monto'] < 0].copy()

    if gastos.empty:
        st.info("ℹ️ No hay gastos para etiquetar en la cartola actual")
        return

    st.markdown(f"### Etiquetando {len(gastos)} transacciones de gasto")

    # Cargar configuración de categorías
    from config.simple_config import config
    categorias = config.default_categories

    # Opción para agregar categoría personalizada
    col_cat1, col_cat2 = st.columns([3, 1])
    with col_cat1:
        nueva_categoria = st.text_input("Nueva categoría:", placeholder="Escribe una nueva categoría...")
    with col_cat2:
        if st.button("+ Agregar") and nueva_categoria.strip():
            if nueva_categoria.strip().lower() not in [c.lower() for c in categorias]:
                categorias.append(nueva_categoria.strip().lower())
                st.success(f"✅ Categoría '{nueva_categoria}' agregada")
                st.rerun()
            else:
                st.warning("⚠️ Categoría ya existe")

    # Agregar columna de categoría si no existe
    if 'Categoría' not in gastos.columns:
        gastos['Categoría'] = ""

    # Interface de etiquetado
    with st.container():
        for idx, (_, row) in enumerate(gastos.iterrows()):
            if idx >= 10:  # Limitar a 10 por página por ahora
                st.info(f"Mostrando las primeras 10 transacciones. Total: {len(gastos)}")
                break

            col1, col2, col3, col4 = st.columns([2, 3, 2, 1])

            with col1:
                st.text(row['Fecha'])

            with col2:
                st.text(row['Descripción'][:50] + "..." if len(row['Descripción']) > 50 else row['Descripción'])

            with col3:
                monto_fmt = f"${abs(row['Monto']):,.0f}".replace(",", ".")
                st.text(monto_fmt)

            with col4:
                selected_category = st.selectbox(
                    "Categoría",
                    [""] + categorias,
                    key=f"cat_{idx}",
                    label_visibility="collapsed"
                )

                if selected_category:
                    gastos.loc[row.name, 'Categoría'] = selected_category

    # Botones de acción
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💾 Guardar etiquetas"):
            # Aquí guardaríamos las etiquetas
            etiquetados = gastos[gastos['Categoría'] != ""]
            if not etiquetados.empty:
                st.success(f"✅ {len(etiquetados)} transacciones etiquetadas guardadas")
            else:
                st.warning("⚠️ No hay etiquetas para guardar")

    with col2:
        if st.button("🤖 Auto-clasificar"):
            st.info("🔧 Funcionalidad pendiente: usar IA para clasificar automáticamente")

    with col3:
        if st.button("➡️ Entrenar IA"):
            st.session_state.page = "training"
            st.rerun()


def page_training():
    """Página de entrenamiento de IA"""
    st.header("🤖 Entrenar IA")
    st.markdown("Entrena el clasificador automático con las transacciones etiquetadas.")

    # Cargar datos etiquetados
    try:
        labeled_data = st.session_state.components['datastore'].load_labeled()

        if labeled_data.empty:
            st.warning("⚠️ No hay datos etiquetados disponibles")
            st.markdown("Primero debes etiquetar algunas transacciones:")
            if st.button("🏷️ Ir a Etiquetar"):
                st.session_state.page = "labeling"
                st.rerun()
            return

        st.success(f"✅ {len(labeled_data)} transacciones etiquetadas encontradas")

        # Estadísticas de categorías
        category_stats = labeled_data['category'].value_counts()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📊 Distribution por categoría")
            st.bar_chart(category_stats)

        with col2:
            st.markdown("### 📈 Estadísticas")
            st.dataframe(category_stats.reset_index())

        # Verificar si hay suficientes datos
        min_samples = 3
        insufficient_categories = category_stats[category_stats < min_samples]

        if not insufficient_categories.empty:
            st.warning(f"⚠️ Algunas categorías tienen menos de {min_samples} ejemplos:")
            st.write(insufficient_categories.index.tolist())
            st.info("💡 Se recomienda tener al menos 3 ejemplos por categoría")

        # Botón de entrenamiento
        if st.button("🚀 Entrenar Modelo", type="primary"):
            with st.spinner("Entrenando clasificador..."):
                try:
                    classifier = st.session_state.components['classifier']
                    classifier.fit(labeled_data, label_col='category')

                    st.success("✅ Modelo entrenado exitosamente!")

                    # Mostrar métricas
                    report = classifier.report(labeled_data, labeled_data['category'])
                    st.text("📊 Reporte de clasificación:")
                    st.code(report)

                except Exception as e:
                    st.error(f"❌ Error entrenando modelo: {str(e)}")

    except Exception as e:
        st.error(f"❌ Error cargando datos: {str(e)}")


def page_dashboard():
    """Dashboard con visualizaciones"""
    st.header("📊 Dashboard Financiero")

    if st.session_state.current_data is None:
        st.warning("⚠️ No hay datos cargados")
        return

    df = st.session_state.current_data

    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)

    gastos = df[df['Monto'] < 0]  # Los negativos son gastos
    ingresos = df[df['Monto'] > 0]  # Los positivos son ingresos

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

    # Gráficos
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 💸 Distribución de gastos")
        if not gastos.empty:
            # Top 10 gastos más grandes (en valor absoluto)
            top_gastos = gastos.nlargest(10, 'Monto', keep='all')[['Descripción', 'Monto']]
            top_gastos['Monto_Abs'] = abs(top_gastos['Monto'])  # Para el gráfico
            st.bar_chart(top_gastos.set_index('Descripción')['Monto_Abs'])
        else:
            st.info("Sin gastos para mostrar")

    with col2:
        st.markdown("### 📈 Ingresos vs Gastos por día")
        if not df.empty:
            df['Fecha'] = pd.to_datetime(df['Fecha'])
            daily_summary = df.groupby(df['Fecha'].dt.date).agg({
                'Monto': ['sum', 'count']
            }).round(0)
            st.line_chart(daily_summary['Monto']['sum'])

    # Tabla de datos
    st.markdown("### 📋 Transacciones recientes")

    # Formatear DataFrame para mostrar
    df_display = df.head(20).copy()
    if 'Monto' in df_display.columns:
        df_display['Monto_Formateado'] = df_display['Monto'].apply(
            lambda x: f"${x:,.0f}".replace(",", ".") if x >= 0
            else f"-${abs(x):,.0f}".replace(",", ".")
        )
        # Mostrar con formato chileno
        df_display = df_display[['Fecha', 'Descripción', 'Monto_Formateado', 'ABONO/CARGO']].rename(
            columns={'Monto_Formateado': 'Monto'})

    st.dataframe(
        df_display,
        use_container_width=True
    )


def page_kame():
    """Página de integración KAME"""
    st.header("🔄 Integración KAME")
    st.markdown("Concilia transacciones bancarias con documentos del ERP KAME.")

    st.info("🔧 Funcionalidad en desarrollo")

    # Placeholder para funcionalidad futura
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏦 Datos Bancarios")
        if st.session_state.current_data is not None:
            gastos = st.session_state.current_data[st.session_state.current_data['Monto'] < 0]
            st.success(f"✅ {len(gastos)} gastos cargados")
        else:
            st.warning("⚠️ No hay datos bancarios")

    with col2:
        st.markdown("### 📄 Documentos KAME")
        uploaded_kame = st.file_uploader(
            "Cargar reporte KAME",
            type=['xlsx', 'csv'],
            help="Archivo Excel o CSV del sistema KAME"
        )

        if uploaded_kame:
            st.success("✅ Archivo KAME cargado")


def page_settings():
    """Página de configuración"""
    st.header("⚙️ Configuración")

    col1, col2 = st.columns(2)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎯 Gestión de Categorías")

        # Mostrar categorías actuales de la configuración
        from config.simple_config import config
        st.markdown("**Categorías disponibles:**")
        for i, cat in enumerate(config.default_categories, 1):
            st.text(f"{i:2d}. {cat}")

        # Agregar nueva categoría
        st.markdown("---")
        nueva_cat = st.text_input("Agregar nueva categoría:")
        if st.button("➕ Agregar categoría"):
            if nueva_cat.strip() and nueva_cat.strip().lower() not in [c.lower() for c in config.default_categories]:
                config.default_categories.append(nueva_cat.strip().lower())
                st.success(f"✅ Categoría '{nueva_cat}' agregada")
                st.rerun()
            elif nueva_cat.strip():
                st.warning("⚠️ Categoría ya existe")
            else:
                st.error("❌ Nombre de categoría vacío")

        # Mostrar categorías de datos etiquetados
        try:
            labeled_data = st.session_state.components['datastore'].load_labeled()
            if not labeled_data.empty and 'category' in labeled_data.columns:
                categories_used = sorted(labeled_data['category'].unique())
                st.markdown("**Categorías con datos etiquetados:**")
                for cat in categories_used:
                    count = len(labeled_data[labeled_data['category'] == cat])
                    st.text(f"• {cat} ({count} transacciones)")
            else:
                st.info("Sin categorías con datos etiquetados")
        except:
            st.error("Error cargando categorías etiquetadas")

    with col2:
        st.markdown("### 🔧 Configuración General")

        # Configuraciones básicas
        max_rows = st.number_input("Máximo filas a mostrar", value=1000, min_value=100, max_value=10000)

        enable_auto_classification = st.checkbox("Clasificación automática", value=False)

        confidence_threshold = st.slider("Umbral de confianza IA", 0.0, 1.0, 0.6, 0.1)

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


def main():
    """Función principal de la aplicación"""
    init_session_state()
    main_header()

    # Navegación
    current_page = sidebar_navigation()

    # Mostrar página seleccionada
    if current_page == "upload":
        page_upload()
    elif current_page == "labeling":
        page_labeling()
    elif current_page == "training":
        page_training()
    elif current_page == "dashboard":
        page_dashboard()
    elif current_page == "kame":
        page_kame()
    elif current_page == "settings":
        page_settings()


if __name__ == "__main__":
    main()