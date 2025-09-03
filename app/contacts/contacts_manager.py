# app/contacts/contacts_manager.py - Sistema completo de gestión de contactos
from __future__ import annotations
import pandas as pd
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import streamlit as st
import logging
from datetime import datetime


class ContactsManager:
    """Gestor completo de contactos con carga desde Excel y mejora de descripciones"""

    def __init__(self, datastore):
        self.datastore = datastore
        self.logger = logging.getLogger(__name__)

    def clean_rut(self, rut: str) -> str:
        """Limpia formato de RUT chileno"""
        if not rut or pd.isna(rut):
            return ""

        # Convertir a string y limpiar
        rut_clean = str(rut).strip().upper()

        # Remover puntos, guiones, espacios
        rut_clean = re.sub(r'[.\s-]', '', rut_clean)

        # Formato estándar: XXXXXXXX-X
        if len(rut_clean) >= 8:
            # Separar número del dígito verificador
            number = rut_clean[:-1]
            digit = rut_clean[-1]

            # Formatear como XX.XXX.XXX-X solo si es numérico (excepto el dígito verificador)
            if number.isdigit():
                return f"{int(number):,}".replace(',', '.') + f"-{digit}"
            else:
                return f"{number}-{digit}"

        return rut_clean

    def validate_rut(self, rut: str) -> bool:
        """Valida formato básico de RUT chileno"""
        if not rut:
            return False

        # Limpiar RUT
        rut_clean = re.sub(r'[.\s-]', '', str(rut).strip())

        # Debe tener al menos 8 caracteres (7 números + 1 dígito verificador)
        if len(rut_clean) < 8:
            return False

        # Los primeros caracteres deben ser números, el último puede ser número o K
        number_part = rut_clean[:-1]
        digit_part = rut_clean[-1].upper()

        if not number_part.isdigit():
            return False

        if digit_part not in '0123456789K':
            return False

        return True

    def load_contacts_from_excel(self, file_path: Union[str, Path]) -> Tuple[pd.DataFrame, Dict]:
        """Carga contactos desde archivo Excel del banco"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        try:
            # Intentar leer el archivo Excel
            df_raw = pd.read_excel(file_path, dtype=str)

            self.logger.info(f"Excel cargado: {len(df_raw)} filas, columnas: {list(df_raw.columns)}")

            # Detectar automáticamente columnas de RUT y nombre
            rut_col, name_col = self._detect_rut_and_name_columns(df_raw)

            if not rut_col or not name_col:
                raise ValueError("No se pudieron detectar columnas de RUT y nombre automáticamente")

            # Extraer y limpiar datos
            df_contacts = pd.DataFrame()
            df_contacts['rut_original'] = df_raw[rut_col].astype(str)
            df_contacts['nombre_original'] = df_raw[name_col].astype(str)

            # Limpiar RUTs
            df_contacts['rut'] = df_contacts['rut_original'].apply(self.clean_rut)
            df_contacts['nombre'] = df_contacts['nombre_original'].str.strip().str.title()

            # Filtrar RUTs válidos
            df_contacts['rut_valido'] = df_contacts['rut'].apply(self.validate_rut)
            df_valid = df_contacts[df_contacts['rut_valido'] & (df_contacts['nombre'] != '')].copy()

            # Remover duplicados por RUT
            df_unique = df_valid.drop_duplicates(subset=['rut'], keep='first')

            # Generar alias automático (primer nombre + primer apellido)
            df_unique['alias'] = df_unique['nombre'].apply(self._generate_alias)

            # Estadísticas de procesamiento
            stats = {
                'total_rows': len(df_raw),
                'valid_contacts': len(df_unique),
                'invalid_ruts': len(df_contacts) - len(df_valid),
                'duplicates_removed': len(df_valid) - len(df_unique),
                'rut_column_detected': rut_col,
                'name_column_detected': name_col,
                'sample_contacts': df_unique.head(3)[['rut', 'nombre', 'alias']].to_dict('records')
            }

            self.logger.info(
                f"Contactos procesados: {stats['valid_contacts']} válidos de {stats['total_rows']} totales")

            return df_unique, stats

        except Exception as e:
            self.logger.error(f"Error cargando contactos desde Excel: {e}")
            raise

    def _detect_rut_and_name_columns(self, df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
        """Detecta automáticamente las columnas de RUT y nombre"""
        rut_col = None
        name_col = None

        # Buscar columna de RUT
        rut_keywords = ['rut', 'identificacion', 'cedula', 'documento', 'id']
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in rut_keywords):
                # Verificar que la columna contenga datos que parezcan RUTs
                sample_data = df[col].dropna().astype(str).head(10)
                if self._looks_like_rut_column(sample_data):
                    rut_col = col
                    break

        # Buscar columna de nombre
        name_keywords = ['nombre', 'razon', 'social', 'cliente', 'beneficiario', 'destinatario']
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in name_keywords):
                # Verificar que la columna contenga texto que parezca nombres
                sample_data = df[col].dropna().astype(str).head(10)
                if self._looks_like_name_column(sample_data):
                    name_col = col
                    break

        return rut_col, name_col

    def _looks_like_rut_column(self, sample_data: pd.Series) -> bool:
        """Verifica si una muestra de datos parece contener RUTs"""
        if sample_data.empty:
            return False

        # Contar cuántas entradas parecen RUTs
        rut_like_count = 0
        for value in sample_data:
            # Buscar patrones que parezcan RUTs
            if re.search(r'\d{7,8}[-.]?[0-9kK]', str(value)):
                rut_like_count += 1

        # Si al menos el 60% parece RUT, es probable que sea la columna correcta
        return (rut_like_count / len(sample_data)) >= 0.6

    def _looks_like_name_column(self, sample_data: pd.Series) -> bool:
        """Verifica si una muestra de datos parece contener nombres"""
        if sample_data.empty:
            return False

        name_like_count = 0
        for value in sample_data:
            str_value = str(value).strip()
            # Buscar características de nombres: longitud, espacios, letras
            if (len(str_value) > 5 and
                    len(str_value) < 100 and
                    ' ' in str_value and
                    re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', str_value)):
                name_like_count += 1

        return (name_like_count / len(sample_data)) >= 0.7

    def _generate_alias(self, nombre_completo: str) -> str:
        """Genera un alias corto a partir del nombre completo"""
        if not nombre_completo or pd.isna(nombre_completo):
            return ""

        # Dividir en palabras y tomar las primeras 2-3
        palabras = str(nombre_completo).strip().split()

        if len(palabras) == 0:
            return ""
        elif len(palabras) == 1:
            return palabras[0][:15]  # Limitar longitud
        elif len(palabras) >= 2:
            # Primer nombre + primer apellido
            return f"{palabras[0]} {palabras[1]}"[:20]

    def save_contacts_to_database(self, df_contacts: pd.DataFrame, overwrite_existing: bool = False) -> Dict:
        """Guarda contactos en la base de datos"""
        if df_contacts.empty:
            return {'saved': 0, 'errors': 0, 'duplicates': 0}

        saved_count = 0
        error_count = 0
        duplicate_count = 0
        errors = []

        for _, row in df_contacts.iterrows():
            try:
                rut = row.get('rut', '')
                nombre = row.get('nombre', '')
                alias = row.get('alias', '')

                if not rut or not nombre:
                    error_count += 1
                    continue

                # Verificar si ya existe
                existing_contact = self.datastore.find_contact_by_rut(rut)

                if existing_contact and not overwrite_existing:
                    duplicate_count += 1
                    continue
                elif existing_contact and overwrite_existing:
                    # Actualizar contacto existente
                    if self.datastore.db.update_contact(rut, nombre, alias):
                        saved_count += 1
                    else:
                        error_count += 1
                else:
                    # Crear nuevo contacto
                    if self.datastore.add_contact(rut, nombre, alias, 'cliente'):
                        saved_count += 1
                    else:
                        error_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Error con {row.get('rut', 'RUT desconocido')}: {str(e)}")
                self.logger.error(f"Error guardando contacto: {e}")

        result = {
            'saved': saved_count,
            'errors': error_count,
            'duplicates': duplicate_count,
            'error_details': errors[:10]  # Máximo 10 errores detallados
        }

        self.logger.info(f"Contactos guardados: {saved_count}, errores: {error_count}, duplicados: {duplicate_count}")
        return result

    def enhance_transaction_descriptions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mejora las descripciones de transacciones reemplazando RUTs por nombres"""
        if df.empty or 'Descripción' not in df.columns:
            return df

        df_enhanced = df.copy()

        # Cargar todos los contactos
        try:
            contacts = self.datastore.get_contacts()
            if not contacts:
                self.logger.info("No hay contactos en la base de datos para mejorar descripciones")
                return df

            # Crear diccionario de RUT -> contacto para búsqueda rápida
            rut_to_contact = {}
            for contact in contacts:
                rut_clean = self.clean_rut(contact['rut'])
                rut_to_contact[rut_clean] = contact

            # Mejorar cada descripción
            enhanced_descriptions = []
            for desc in df_enhanced['Descripción']:
                enhanced_desc = self._enhance_single_description(str(desc), rut_to_contact)
                enhanced_descriptions.append(enhanced_desc)

            df_enhanced['Descripción'] = enhanced_descriptions

            # Agregar columna con descripción original si hubo cambios
            if any(orig != enh for orig, enh in zip(df['Descripción'], enhanced_descriptions)):
                df_enhanced['Descripción_Original'] = df['Descripción']

            return df_enhanced

        except Exception as e:
            self.logger.error(f"Error mejorando descripciones: {e}")
            return df

    def _enhance_single_description(self, description: str, rut_to_contact: Dict) -> str:
        """Mejora una descripción individual"""
        if not description or pd.isna(description):
            return description

        enhanced = description

        # Patrones para encontrar RUTs en descripciones
        rut_patterns = [
            r'\b(\d{1,2}\.?\d{3}\.?\d{3}[-.]?[0-9kK])\b',  # Formato completo
            r'\b(\d{7,8}[-.]?[0-9kK])\b',  # Formato sin puntos
        ]

        for pattern in rut_patterns:
            matches = re.finditer(pattern, description, re.IGNORECASE)

            for match in matches:
                rut_found = match.group(1)
                rut_clean = self.clean_rut(rut_found)

                # Buscar contacto
                contact = rut_to_contact.get(rut_clean)
                if contact:
                    alias = contact.get('alias', contact.get('name', ''))
                    if alias:
                        # Reemplazar patrón completo manteniendo contexto
                        if 'transf' in description.lower():
                            replacement = f"Transferencia a {alias}"
                        elif 'pago' in description.lower():
                            replacement = f"Pago a {alias}"
                        else:
                            replacement = f"{alias} ({rut_found})"

                        # Reemplazar toda la parte de la transferencia
                        enhanced = re.sub(
                            rf'.*{re.escape(rut_found)}.*',
                            replacement,
                            enhanced,
                            flags=re.IGNORECASE
                        )

        return enhanced

    def get_contacts_summary(self) -> Dict:
        """Obtiene resumen de contactos en la base de datos"""
        try:
            contacts = self.datastore.get_contacts()

            if not contacts:
                return {
                    'total_contacts': 0,
                    'by_type': {},
                    'recent_contacts': []
                }

            # Contar por tipo
            type_counts = {}
            for contact in contacts:
                contact_type = contact.get('contact_type', 'sin_tipo')
                type_counts[contact_type] = type_counts.get(contact_type, 0) + 1

            # Contactos recientes (últimos 5)
            recent_contacts = contacts[-5:] if len(contacts) >= 5 else contacts

            return {
                'total_contacts': len(contacts),
                'by_type': type_counts,
                'recent_contacts': [
                    {
                        'rut': c.get('rut', ''),
                        'name': c.get('name', ''),
                        'alias': c.get('alias', ''),
                        'type': c.get('contact_type', '')
                    } for c in recent_contacts
                ]
            }

        except Exception as e:
            self.logger.error(f"Error obteniendo resumen de contactos: {e}")
            return {'error': str(e)}

    def search_contacts(self, query: str) -> List[Dict]:
        """Busca contactos por RUT, nombre o alias"""
        if not query or len(query.strip()) < 2:
            return []

        try:
            contacts = self.datastore.get_contacts()
            query_lower = query.lower().strip()

            matching_contacts = []
            for contact in contacts:
                # Buscar en RUT, nombre y alias
                rut = str(contact.get('rut', '')).lower()
                name = str(contact.get('name', '')).lower()
                alias = str(contact.get('alias', '')).lower()

                if (query_lower in rut or
                        query_lower in name or
                        query_lower in alias):
                    matching_contacts.append(contact)

            return matching_contacts

        except Exception as e:
            self.logger.error(f"Error buscando contactos: {e}")
            return []


def show_contacts_management_page(datastore):
    """Página principal de gestión de contactos"""
    st.header("👥 Gestión de Contactos")

    # Inicializar gestor de contactos
    contacts_manager = ContactsManager(datastore)

    # Tabs principales
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Lista de Contactos",
        "📤 Cargar desde Excel",
        "➕ Agregar Manual",
        "🔍 Buscar y Editar"
    ])

    with tab1:
        show_contacts_list(contacts_manager)

    with tab2:
        show_excel_upload(contacts_manager)

    with tab3:
        show_manual_contact_form(contacts_manager)

    with tab4:
        show_contact_search(contacts_manager)


def show_contacts_list(contacts_manager):
    """Muestra lista completa de contactos"""
    st.markdown("### 📋 Lista de Contactos")

    # Obtener resumen
    summary = contacts_manager.get_contacts_summary()

    if 'error' in summary:
        st.error(f"❌ Error cargando contactos: {summary['error']}")
        return

    if summary['total_contacts'] == 0:
        st.info("📝 No hay contactos registrados. Usa las otras tabs para agregar contactos.")
        return

    # Métricas
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("👥 Total Contactos", summary['total_contacts'])

    with col2:
        clientes = summary['by_type'].get('cliente', 0)
        st.metric("🏢 Clientes", clientes)

    with col3:
        proveedores = summary['by_type'].get('proveedor', 0)
        st.metric("📦 Proveedores", proveedores)

    # Lista completa de contactos
    try:
        contacts = contacts_manager.datastore.get_contacts()

        if contacts:
            # Convertir a DataFrame para mostrar mejor
            df_contacts = pd.DataFrame(contacts)

            # Seleccionar y renombrar columnas para display
            display_columns = ['rut', 'name', 'alias', 'contact_type']
            available_columns = [col for col in display_columns if col in df_contacts.columns]

            if available_columns:
                df_display = df_contacts[available_columns].copy()
                df_display = df_display.rename(columns={
                    'rut': 'RUT',
                    'name': 'Nombre Completo',
                    'alias': 'Alias',
                    'contact_type': 'Tipo'
                })

                # Filtros
                st.markdown("#### 🔍 Filtros")
                col_filter1, col_filter2 = st.columns(2)

                with col_filter1:
                    type_filter = st.selectbox(
                        "Filtrar por tipo:",
                        options=['Todos'] + list(summary['by_type'].keys()),
                        key="contact_type_filter"
                    )

                with col_filter2:
                    search_text = st.text_input(
                        "Buscar por nombre/RUT:",
                        placeholder="Escribe para filtrar...",
                        key="contact_search_filter"
                    )

                # Aplicar filtros
                df_filtered = df_display.copy()

                if type_filter != 'Todos':
                    df_filtered = df_filtered[df_filtered['Tipo'] == type_filter]

                if search_text:
                    mask = (
                            df_filtered['RUT'].str.contains(search_text, case=False, na=False) |
                            df_filtered['Nombre Completo'].str.contains(search_text, case=False, na=False) |
                            df_filtered['Alias'].str.contains(search_text, case=False, na=False)
                    )
                    df_filtered = df_filtered[mask]

                # Mostrar tabla
                st.markdown(f"#### 📊 Contactos ({len(df_filtered)} de {len(df_display)})")
                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True
                )

                # Botón de exportación
                if st.button("📥 Exportar contactos a CSV"):
                    csv = df_filtered.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Descargar CSV",
                        data=csv,
                        file_name=f"contactos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv"
                    )

    except Exception as e:
        st.error(f"❌ Error mostrando contactos: {e}")


def show_excel_upload(contacts_manager):
    """Interfaz para cargar contactos desde Excel"""
    st.markdown("### 📤 Cargar Contactos desde Excel")

    st.markdown("""
    **📝 Instrucciones:**
    1. Sube el archivo Excel que te entrega el banco con los detalles de transferencias
    2. El sistema detectará automáticamente las columnas de RUT y nombre
    3. Los contactos válidos se procesarán y guardarán en la base de datos
    """)

    # File uploader
    uploaded_file = st.file_uploader(
        "Seleccionar archivo Excel",
        type=['xlsx', 'xls'],
        help="Archivo Excel del banco con RUTs y nombres"
    )

    if uploaded_file is not None:
        try:
            with st.spinner("Procesando archivo Excel..."):
                # Guardar archivo temporalmente
                temp_path = Path(f"uploads/{uploaded_file.name}")
                temp_path.parent.mkdir(exist_ok=True)

                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Procesar contactos
                df_contacts, stats = contacts_manager.load_contacts_from_excel(temp_path)

                # Mostrar estadísticas de procesamiento
                st.success(f"✅ Archivo procesado exitosamente")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("📊 Total filas", stats['total_rows'])

                with col2:
                    st.metric("✅ Contactos válidos", stats['valid_contacts'])

                with col3:
                    st.metric("❌ RUTs inválidos", stats['invalid_ruts'])

                with col4:
                    st.metric("🔄 Duplicados", stats['duplicates_removed'])

                # Mostrar detalles de detección
                st.info(
                    f"🔍 Columnas detectadas: RUT = '{stats['rut_column_detected']}', Nombre = '{stats['name_column_detected']}'")

                # Preview de contactos
                if not df_contacts.empty:
                    st.markdown("#### 👀 Vista previa de contactos")

                    preview_df = df_contacts[['rut', 'nombre', 'alias']].head(10).copy()
                    preview_df = preview_df.rename(columns={
                        'rut': 'RUT',
                        'nombre': 'Nombre',
                        'alias': 'Alias'
                    })

                    st.dataframe(preview_df, use_container_width=True, hide_index=True)

                    # Opciones de guardado
                    st.markdown("#### 💾 Guardar en base de datos")

                    col_save1, col_save2 = st.columns(2)

                    with col_save1:
                        overwrite_existing = st.checkbox(
                            "Sobrescribir contactos existentes",
                            value=False,
                            help="Si está marcado, actualizará contactos que ya existen"
                        )

                    with col_save2:
                        if st.button("💾 Guardar contactos", type="primary"):
                            with st.spinner("Guardando contactos..."):
                                save_result = contacts_manager.save_contacts_to_database(
                                    df_contacts,
                                    overwrite_existing=overwrite_existing
                                )

                                # Mostrar resultado
                                col_r1, col_r2, col_r3 = st.columns(3)

                                with col_r1:
                                    st.success(f"✅ Guardados: {save_result['saved']}")

                                with col_r2:
                                    if save_result['duplicates'] > 0:
                                        st.warning(f"⚠️ Duplicados: {save_result['duplicates']}")

                                with col_r3:
                                    if save_result['errors'] > 0:
                                        st.error(f"❌ Errores: {save_result['errors']}")

                                if save_result['error_details']:
                                    with st.expander("🔍 Detalles de errores"):
                                        for error in save_result['error_details']:
                                            st.error(error)

                # Limpiar archivo temporal
                temp_path.unlink(missing_ok=True)

        except Exception as e:
            st.error(f"❌ Error procesando archivo: {e}")

            with st.expander("🔍 Detalles del error"):
                import traceback
                st.code(traceback.format_exc())


def show_manual_contact_form(contacts_manager):
    """Formulario para agregar contactos manualmente"""
    st.markdown("### ➕ Agregar Contacto Manual")

    with st.form("add_contact_form"):
        col1, col2 = st.columns(2)

        with col1:
            rut_input = st.text_input(
                "RUT *",
                placeholder="12.345.678-9",
                help="RUT con o sin puntos y guión"
            )

            nombre_input = st.text_input(
                "Nombre Completo *",
                placeholder="Juan Pérez García",
                help="Nombre completo de la persona o empresa"
            )

        with col2:
            alias_input = st.text_input(
                "Alias",
                placeholder="Juan P.",
                help="Nombre corto para mostrar en transacciones (opcional)"
            )

            tipo_input = st.selectbox(
                "Tipo de Contacto",
                options=['cliente', 'proveedor', 'empleado', 'otro'],
                index=0
            )

        submitted = st.form_submit_button("➕ Agregar Contacto", type="primary")

        if submitted:
            # Validaciones
            errors = []

            if not rut_input.strip():
                errors.append("RUT es obligatorio")
            elif not contacts_manager.validate_rut(rut_input):
                errors.append("RUT no tiene formato válido")

            if not nombre_input.strip():
                errors.append("Nombre es obligatorio")

            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                try:
                    # Limpiar datos
                    rut_clean = contacts_manager.clean_rut(rut_input)
                    nombre_clean = nombre_input.strip().title()
                    alias_clean = alias_input.strip() if alias_input.strip() else contacts_manager._generate_alias(
                        nombre_clean)

                    # Verificar si ya existe
                    existing = contacts_manager.datastore.find_contact_by_rut(rut_clean)

                    if existing:
                        st.warning(f"⚠️ Ya existe un contacto con RUT {rut_clean}: {existing.get('name', '')}")

                        if st.button("🔄 Actualizar contacto existente"):
                            if contacts_manager.datastore.db.update_contact(rut_clean, nombre_clean, alias_clean):
                                st.success("✅ Contacto actualizado exitosamente")
                                st.rerun()
                            else:
                                st.error("❌ Error actualizando contacto")
                    else:
                        # Crear nuevo contacto
                        if contacts_manager.datastore.add_contact(rut_clean, nombre_clean, alias_clean, tipo_input):
                            st.success(f"✅ Contacto agregado: {alias_clean} ({rut_clean})")
                            st.rerun()
                        else:
                            st.error("❌ Error guardando contacto")

                except Exception as e:
                    st.error(f"❌ Error procesando contacto: {e}")


def show_contact_search(contacts_manager):
    """Interfaz de búsqueda y edición de contactos"""
    st.markdown("### 🔍 Buscar y Editar Contactos")

    # Búsqueda
    search_query = st.text_input(
        "Buscar contacto:",
        placeholder="Escribe RUT, nombre o alias...",
        key="contact_search_query"
    )

    if search_query and len(search_query.strip()) >= 2:
        matching_contacts = contacts_manager.search_contacts(search_query)

        if matching_contacts:
            st.success(f"✅ {len(matching_contacts)} contacto(s) encontrado(s)")

            # Mostrar cada contacto con opción de editar
            for contact in matching_contacts:
                with st.expander(f"👤 {contact.get('name', '')} ({contact.get('rut', '')})"):

                    col1, col2 = st.columns(2)

                    with col1:
                        st.text_input(
                            "RUT",
                            value=contact.get('rut', ''),
                            disabled=True,
                            key=f"edit_rut_{contact.get('id', '')}"
                        )

                        new_name = st.text_input(
                            "Nombre",
                            value=contact.get('name', ''),
                            key=f"edit_name_{contact.get('id', '')}"
                        )

                    with col2:
                        new_alias = st.text_input(
                            "Alias",
                            value=contact.get('alias', ''),
                            key=f"edit_alias_{contact.get('id', '')}"
                        )

                        new_type = st.selectbox(
                            "Tipo",
                            options=['cliente', 'proveedor', 'empleado', 'otro'],
                            index=['cliente', 'proveedor', 'empleado', 'otro'].index(
                                contact.get('contact_type', 'cliente')
                            ),
                            key=f"edit_type_{contact.get('id', '')}"
                        )

                    col_btn1, col_btn2 = st.columns(2)

                    with col_btn1:
                        if st.button(f"💾 Actualizar", key=f"update_{contact.get('id', '')}"):
                            try:
                                rut = contact.get('rut', '')
                                if contacts_manager.datastore.db.update_contact(rut, new_name, new_alias):
                                    st.success("✅ Contacto actualizado")
                                    st.rerun()
                                else:
                                    st.error("❌ Error actualizando")
                            except Exception as e:
                                st.error(f"❌ Error: {e}")

                    with col_btn2:
                        if st.button(f"🗑️ Eliminar", key=f"delete_{contact.get('id', '')}"):
                            # Aquí implementarías la lógica de eliminación
                            st.warning("⚠️ Función de eliminación pendiente")
        else:
            st.info("🔍 No se encontraron contactos con esa búsqueda")

    elif search_query:
        st.info("✏️ Escribe al menos 2 caracteres para buscar")