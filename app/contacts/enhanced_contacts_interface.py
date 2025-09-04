# app/contacts/enhanced_contacts_interface.py - Interfaz mejorada para Streamlit
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List


def show_enhanced_transfer_upload(datastore):
    """Interfaz mejorada para cargar resúmenes de transferencia"""
    st.markdown("### 📤 Cargar Contactos desde Resumen de Transferencia")

    st.markdown("""
    **📋 Formatos soportados:**
    - ✅ **Resúmenes de transferencia del banco** (detección automática)
    - ✅ **Archivos Excel genéricos** con RUTs y nombres
    - ✅ **Archivos CSV** con datos de contactos

    **🎯 Características:**
    - 🔍 **Detección automática** del formato de resumen de transferencia
    - 🚫 **Evita duplicados** automáticamente
    - 📊 **Múltiples transferencias** a la misma persona se consolidan en un contacto
    - ✅ **Validación de RUTs** chilenos
    """)

    # File uploader
    uploaded_file = st.file_uploader(
        "📁 Seleccionar archivo de resumen de transferencia",
        type=['xlsx', 'xls', 'csv'],
        help="Archivo Excel o CSV con datos de transferencias del banco"
    )

    if uploaded_file is not None:
        try:
            with st.spinner("🔍 Analizando archivo..."):
                # Guardar archivo temporalmente
                temp_path = Path(f"uploads/{uploaded_file.name}")
                temp_path.parent.mkdir(exist_ok=True)

                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Usar el detector mejorado
                from .contacts_manager import ContactsManager
                enhanced_manager = ContactsManager(datastore)

                # Procesar archivo
                df_contacts, stats = enhanced_manager.load_contacts_from_excel(temp_path)

                # Mostrar resultados del análisis
                st.success("✅ Archivo procesado exitosamente")

                # Métricas del análisis
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("📊 Total filas", stats['total_rows'])

                with col2:
                    st.metric("✅ Contactos únicos", stats['valid_contacts'])

                with col3:
                    st.metric("🔄 Duplicados removidos", stats['duplicates_removed'])

                with col4:
                    st.metric("❌ RUTs inválidos", stats['invalid_ruts'])

                # Mostrar información de detección
                if stats.get('detected_as_transfer_summary', False):
                    confidence = stats.get('detection_confidence', 0)
                    st.info(f"🎯 **Resumen de transferencia detectado** (confianza: {confidence:.1%})")

                    col_det1, col_det2 = st.columns(2)
                    with col_det1:
                        st.success(f"📋 RUT: `{stats.get('rut_column_detected', 'N/A')}`")
                    with col_det2:
                        st.success(f"👤 Nombre: `{stats.get('name_column_detected', 'N/A')}`")
                else:
                    st.warning("⚠️ Formato genérico detectado (no es resumen de transferencia específico)")

                # Preview de contactos únicos
                if not df_contacts.empty:
                    st.markdown("#### 👥 Vista previa de contactos únicos")

                    # Preparar DataFrame para mostrar
                    preview_df = df_contacts[['rut', 'nombre', 'alias']].head(15).copy()
                    preview_df = preview_df.rename(columns={
                        'rut': 'RUT',
                        'nombre': 'Nombre Completo',
                        'alias': 'Alias'
                    })

                    # Mostrar información adicional si está disponible
                    if 'total_transferido' in df_contacts.columns:
                        preview_df['Total Transferido'] = df_contacts['total_transferido'].head(15).apply(
                            lambda x: f"${x:,.0f}".replace(',', '.') if pd.notna(x) else "N/A"
                        )

                    st.dataframe(preview_df, use_container_width=True, hide_index=True)

                    if len(df_contacts) > 15:
                        st.caption(f"Mostrando 15 de {len(df_contacts)} contactos únicos encontrados")

                    # Opciones de guardado
                    st.markdown("#### 💾 Opciones de guardado")

                    col_save1, col_save2, col_save3 = st.columns(3)

                    with col_save1:
                        overwrite_existing = st.checkbox(
                            "🔄 Actualizar contactos existentes",
                            value=False,
                            help="Si está marcado, actualizará contactos que ya existen en la base de datos"
                        )

                    with col_save2:
                        if st.button("💾 Guardar Contactos", type="primary"):
                            with st.spinner("💾 Guardando contactos únicos..."):
                                save_result = enhanced_manager.save_contacts_to_database(
                                    df_contacts,
                                    overwrite_existing=overwrite_existing
                                )

                                # Mostrar resultado detallado
                                show_save_results(save_result)

                    with col_save3:
                        # Botón de descarga
                        csv = df_contacts.to_csv(index=False)
                        st.download_button(
                            label="📥 Descargar CSV",
                            data=csv,
                            file_name=f"contactos_unicos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv"
                        )

                    # Análisis adicional
                    if len(df_contacts) > 0:
                        with st.expander("📊 Análisis detallado"):
                            show_contact_analysis(df_contacts, stats)

                else:
                    st.warning("⚠️ No se encontraron contactos válidos en el archivo")
                    st.markdown("**Posibles causas:**")
                    st.markdown("- Formato de archivo no reconocido")
                    st.markdown("- RUTs en formato incorrecto")
                    st.markdown("- Columnas de nombres vacías")

                # Limpiar archivo temporal
                temp_path.unlink(missing_ok=True)

        except Exception as e:
            st.error(f"❌ Error procesando archivo: {e}")

            with st.expander("🔍 Detalles del error"):
                import traceback
                st.code(traceback.format_exc())

                st.markdown("**💡 Sugerencias:**")
                st.markdown("- Verifica que el archivo no esté corrupto")
                st.markdown("- Asegúrate de que contenga columnas con RUTs y nombres")
                st.markdown("- Revisa que el formato sea Excel (.xlsx) o CSV")


def show_save_results(save_result):
    """Muestra los resultados del guardado"""
    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        st.success(f"✅ Guardados: {save_result['saved']}")

    with col_r2:
        if save_result['duplicates'] > 0:
            st.warning(f"⚠️ Duplicados: {save_result['duplicates']}")

    with col_r3:
        if save_result['errors'] > 0:
            st.error(f"❌ Errores: {save_result['errors']}")

    # Total procesados
    total_processed = save_result['saved'] + save_result['errors'] + save_result['duplicates']
    st.info(f"📊 Total procesados: {total_processed}")

    # Detalles de errores si existen
    if save_result.get('error_details'):
        with st.expander("🔍 Detalles de errores"):
            for error in save_result['error_details']:
                st.error(error)


def show_contact_analysis(df_contacts: pd.DataFrame, stats: Dict):
    """Muestra análisis detallado de los contactos extraídos"""

    col_an1, col_an2 = st.columns(2)

    with col_an1:
        st.markdown("**📈 Estadísticas de procesamiento:**")
        st.write(f"• Total filas en archivo: {stats['total_rows']:,}")
        st.write(f"• Contactos únicos extraídos: {stats['valid_contacts']:,}")
        st.write(f"• Duplicados consolidados: {stats['duplicates_removed']:,}")
        st.write(f"• RUTs inválidos descartados: {stats['invalid_ruts']:,}")

        if stats.get('detection_confidence'):
            st.write(f"• Confianza de detección: {stats['detection_confidence']:.1%}")

    with col_an2:
        st.markdown("**🔍 Análisis de contenido:**")

        # Análisis de longitud de nombres
        if not df_contacts.empty and 'nombre' in df_contacts.columns:
            avg_name_length = df_contacts['nombre'].str.len().mean()
            st.write(f"• Longitud promedio de nombres: {avg_name_length:.0f} caracteres")

            # Tipos de contactos (personas vs empresas)
            empresas = df_contacts[df_contacts['nombre'].str.contains(
                r'\b(SPA|LTDA|LIMITADA|SOCIEDAD|CIA|EMPRESA|COMERCIAL)\b',
                case=False, na=False
            )]
            personas = len(df_contacts) - len(empresas)

            st.write(f"• Personas naturales: {personas:,}")
            st.write(f"• Empresas/Sociedades: {len(empresas):,}")

    # Mostrar muestra de datos originales si hay info de columnas
    if stats.get('rut_column_detected') and stats.get('name_column_detected'):
        st.markdown("**📋 Columnas detectadas automáticamente:**")
        col_det1, col_det2 = st.columns(2)

        with col_det1:
            st.code(f"RUT: '{stats['rut_column_detected']}'")

        with col_det2:
            st.code(f"NOMBRE: '{stats['name_column_detected']}'")


def show_transfer_summary_page(datastore):
    """Página principal mejorada para resúmenes de transferencia"""

    st.header("📤 Carga de Resúmenes de Transferencia")
    st.markdown("Sistema inteligente para extraer contactos únicos desde resúmenes bancarios")

    # Tabs principales
    tab1, tab2, tab3 = st.tabs([
        "📤 Cargar Resumen",
        "👥 Contactos Existentes",
        "📊 Estadísticas"
    ])

    with tab1:
        show_enhanced_transfer_upload(datastore)

    with tab2:
        # Usar la función existente del ContactsManager original
        try:
            from .contacts_manager import show_contacts_list
            from .transfer_summary_detector import ContactsManager

            enhanced_manager = ContactsManager(datastore)
            show_contacts_list(enhanced_manager)

        except ImportError:
            st.error("❌ Sistema de contactos no disponible completamente")

    with tab3:
        show_contacts_statistics(datastore)


def show_contacts_statistics(datastore):
    """Muestra estadísticas detalladas de contactos"""
    st.markdown("### 📊 Estadísticas de Contactos")

    try:
        # Obtener estadísticas desde el datastore
        contacts = datastore.get_contacts()

        if not contacts:
            st.info("📝 No hay contactos registrados aún")
            return

        df_contacts = pd.DataFrame(contacts)

        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("👥 Total Contactos", len(df_contacts))

        with col2:
            clientes = len(df_contacts[df_contacts['contact_type'] == 'cliente'])
            st.metric("🏢 Clientes", clientes)

        with col3:
            proveedores = len(df_contacts[df_contacts['contact_type'] == 'proveedor'])
            st.metric("📦 Proveedores", proveedores)

        with col4:
            # Contactos añadidos hoy (aproximado)
            today_contacts = 0  # Necesitaríamos fecha de creación para esto
            st.metric("📅 Hoy", today_contacts)

        # Distribución por tipo
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("#### 📊 Distribución por Tipo")
            type_counts = df_contacts['contact_type'].value_counts()
            st.bar_chart(type_counts)

        with col_chart2:
            st.markdown("#### 🏆 Top 10 Contactos")
            st.dataframe(
                df_contacts[['name', 'rut', 'contact_type']].head(10),
                use_container_width=True,
                hide_index=True
            )

        # Análisis de calidad
        with st.expander("🔍 Análisis de Calidad de Datos"):

            # Contactos sin alias
            sin_alias = len(df_contacts[df_contacts['alias'].isna() | (df_contacts['alias'] == '')])
            st.write(f"• Contactos sin alias: {sin_alias}")

            # Longitud promedio de nombres
            avg_name_length = df_contacts['name'].str.len().mean()
            st.write(f"• Longitud promedio de nombres: {avg_name_length:.1f} caracteres")

            # Empresas vs personas (estimado)
            empresas = df_contacts[df_contacts['name'].str.contains(
                r'\b(SPA|LTDA|LIMITADA|SOCIEDAD|CIA|EMPRESA|COMERCIAL)\b',
                case=False, na=False
            )]
            st.write(f"• Empresas detectadas: {len(empresas)} ({len(empresas) / len(df_contacts) * 100:.1f}%)")
            st.write(
                f"• Personas naturales: {len(df_contacts) - len(empresas)} ({(len(df_contacts) - len(empresas)) / len(df_contacts) * 100:.1f}%)")

    except Exception as e:
        st.error(f"❌ Error obteniendo estadísticas: {e}")
        with st.expander("🔍 Detalles del error"):
            import traceback
            st.code(traceback.format_exc())