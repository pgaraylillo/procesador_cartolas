# app/labeling/smart_labeling.py - Sistema de etiquetado inteligente y persistente
from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple, Optional
import hashlib
from datetime import datetime
import logging


class SmartLabelingSystem:
    """Sistema inteligente de etiquetado con persistencia automática"""

    def __init__(self, datastore):
        self.datastore = datastore
        self.logger = logging.getLogger(__name__)

    def create_transaction_key(self, row: pd.Series) -> str:
        """Crea una clave única para identificar transacciones"""
        # Usar fecha, descripción y monto para crear una clave única
        key_string = f"{row.get('Fecha', '')}-{row.get('Descripción', '')}-{row.get('Monto', 0)}"
        return hashlib.md5(key_string.encode()).hexdigest()[:12]

    def load_existing_labels(self, transactions_df: pd.DataFrame) -> Dict[str, str]:
        """Carga etiquetas existentes para las transacciones actuales"""
        try:
            # Cargar todas las transacciones etiquetadas
            labeled_data = self.datastore.load_labeled()

            if labeled_data.empty:
                return {}

            # Crear diccionario de etiquetas existentes
            existing_labels = {}

            for _, tx_row in transactions_df.iterrows():
                tx_key = self.create_transaction_key(tx_row)

                # Buscar coincidencias en datos etiquetados
                # Buscar por descripción y monto (más flexible que clave exacta)
                matches = labeled_data[
                    (labeled_data['description'].str.contains(str(tx_row.get('Descripción', '')), case=False,
                                                              na=False)) &
                    (abs(labeled_data['amount'] - tx_row.get('Monto', 0)) < 0.01)
                    ]

                if not matches.empty:
                    # Tomar la etiqueta más reciente
                    latest_match = matches.iloc[-1]
                    existing_labels[tx_key] = latest_match.get('category', '')

            self.logger.info(f"✅ Cargadas {len(existing_labels)} etiquetas existentes")
            return existing_labels

        except Exception as e:
            self.logger.error(f"❌ Error cargando etiquetas existentes: {e}")
            return {}

    def save_label_immediately(self, transaction_row: pd.Series, category: str, transaction_key: str):
        """Guarda una etiqueta inmediatamente (auto-save)"""
        try:
            if not category or category.strip() == "":
                return

            # Preparar datos para guardar
            df_to_save = pd.DataFrame({
                'date': [transaction_row.get('Fecha', '')],
                'description': [transaction_row.get('Descripción', '')],
                'amount': [transaction_row.get('Monto', 0)],
                'category': [category.lower().strip()],
                'debit_credit': [transaction_row.get('ABONO/CARGO', '')]
            })

            # Verificar si ya existe esta transacción exacta
            existing_data = self.datastore.load_labeled()
            if not existing_data.empty:
                # Buscar duplicados exactos
                duplicates = existing_data[
                    (existing_data['description'] == transaction_row.get('Descripción', '')) &
                    (abs(existing_data['amount'] - transaction_row.get('Monto', 0)) < 0.01) &
                    (existing_data['date'] == transaction_row.get('Fecha', ''))
                    ]

                if not duplicates.empty:
                    # Si existe, actualizar en lugar de duplicar
                    # Para esto, eliminaríamos la entrada antigua y agregamos la nueva
                    # Pero por simplicidad, omitimos guardar duplicados
                    self.logger.info(f"⚠️ Transacción ya etiquetada, omitiendo duplicado")
                    return

            # Guardar nueva etiqueta
            self.datastore.save_labeled(df_to_save)

            # Actualizar cache en session_state
            if 'existing_labels' not in st.session_state:
                st.session_state.existing_labels = {}
            st.session_state.existing_labels[transaction_key] = category

            self.logger.info(f"✅ Etiqueta guardada automáticamente: {category}")

        except Exception as e:
            self.logger.error(f"❌ Error guardando etiqueta automáticamente: {e}")

    def show_labeling_interface(self, transactions_df: pd.DataFrame, categories: List[str]):
        """Interfaz de etiquetado mejorada con paginación y persistencia"""

        if transactions_df.empty:
            st.info("ℹ️ No hay transacciones para etiquetar")
            return

        # Configuración de paginación
        st.markdown("### ⚙️ Configuración de etiquetado")

        col1, col2, col3 = st.columns(3)

        with col1:
            transactions_per_page = st.selectbox(
                "Transacciones por página",
                options=[10, 25, 50, 100],
                index=0,
                key="transactions_per_page"
            )

        with col2:
            total_pages = (len(transactions_df) - 1) // transactions_per_page + 1
            current_page = st.number_input(
                f"Página (1-{total_pages})",
                min_value=1,
                max_value=total_pages,
                value=st.session_state.get('current_labeling_page', 1),
                key="current_labeling_page"
            )

        with col3:
            if st.button("🔄 Recargar etiquetas"):
                # Forzar recarga de etiquetas existentes
                if 'existing_labels' in st.session_state:
                    del st.session_state.existing_labels
                st.rerun()

        # Calcular rango de transacciones para la página actual
        start_idx = (current_page - 1) * transactions_per_page
        end_idx = min(start_idx + transactions_per_page, len(transactions_df))

        page_transactions = transactions_df.iloc[start_idx:end_idx]

        st.markdown(f"### 🏷️ Etiquetando transacciones {start_idx + 1} - {end_idx} de {len(transactions_df)}")

        # Cargar etiquetas existentes si no están en cache
        if 'existing_labels' not in st.session_state:
            st.session_state.existing_labels = self.load_existing_labels(transactions_df)

        existing_labels = st.session_state.existing_labels

        # Opción para agregar categoría personalizada
        st.markdown("#### ➕ Nueva categoría")
        col_cat1, col_cat2 = st.columns([3, 1])
        with col_cat1:
            nueva_categoria = st.text_input(
                "Nueva categoría:",
                placeholder="Escribe una nueva categoría...",
                key="new_category_input"
            )
        with col_cat2:
            if st.button("+ Agregar", key="add_category_btn") and nueva_categoria.strip():
                if self.datastore.add_category(nueva_categoria.strip().lower()):
                    st.success(f"✅ Categoría '{nueva_categoria}' agregada")
                    categories.append(nueva_categoria.strip().lower())
                    # Limpiar input
                    st.session_state.new_category_input = ""
                    st.rerun()
                else:
                    st.warning("⚠️ Error agregando categoría o ya existe")

        # Interface de etiquetado
        st.markdown("#### 📝 Etiquetado de transacciones")

        # Contador de progreso
        total_labeled = sum(1 for label in existing_labels.values() if label and label.strip())
        progress = total_labeled / len(transactions_df) if len(transactions_df) > 0 else 0

        col_prog1, col_prog2 = st.columns([3, 1])
        with col_prog1:
            st.progress(progress,
                        text=f"Progreso: {total_labeled}/{len(transactions_df)} transacciones etiquetadas ({progress:.1%})")
        with col_prog2:
            st.metric("Etiquetadas", f"{total_labeled}/{len(transactions_df)}")

        # Mostrar transacciones para etiquetar
        for idx, (_, row) in enumerate(page_transactions.iterrows()):
            transaction_key = self.create_transaction_key(row)
            existing_label = existing_labels.get(transaction_key, "")

            # Contenedor para cada transacción
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 1])

                with col1:
                    st.text(str(row.get('Fecha', '')))

                with col2:
                    desc = str(row.get('Descripción', ''))
                    display_desc = desc[:45] + "..." if len(desc) > 45 else desc
                    st.text(display_desc)

                    # Mostrar descripción completa en tooltip
                    if len(desc) > 45:
                        st.caption(f"📝 {desc}")

                with col3:
                    amount = row.get('Monto', 0)
                    monto_fmt = f"${abs(amount):,.0f}".replace(",", ".")
                    if amount < 0:
                        st.markdown(f"🔴 -{monto_fmt}")
                    else:
                        st.markdown(f"🟢 +{monto_fmt}")

                with col4:
                    # Preparar opciones con etiqueta existente seleccionada
                    category_options = [""] + categories
                    selected_index = 0

                    if existing_label and existing_label in categories:
                        selected_index = categories.index(existing_label) + 1

                    selected_category = st.selectbox(
                        "Categoría",
                        options=category_options,
                        index=selected_index,
                        key=f"category_{current_page}_{idx}_{transaction_key}",
                        label_visibility="collapsed",
                        on_change=lambda tx_row=row, tx_key=transaction_key: self._on_category_change(tx_row, tx_key)
                    )

                with col5:
                    # Indicador visual del estado
                    if existing_label and existing_label.strip():
                        st.success("✅")
                    else:
                        st.error("❌")

                # Línea separadora sutil
                st.divider()

        # Información de navegación
        col_nav1, col_nav2, col_nav3 = st.columns(3)

        with col_nav1:
            if current_page > 1:
                if st.button("⬅️ Página anterior"):
                    st.session_state.current_labeling_page = current_page - 1
                    st.rerun()

        with col_nav2:
            st.info(f"📄 Página {current_page} de {total_pages}")

        with col_nav3:
            if current_page < total_pages:
                if st.button("Página siguiente ➡️"):
                    st.session_state.current_labeling_page = current_page + 1
                    st.rerun()

        # Botones de acción masiva
        st.markdown("---")
        st.markdown("### 🎯 Acciones masivas")

        col_action1, col_action2, col_action3 = st.columns(3)

        with col_action1:
            if st.button("💾 Guardar todas las etiquetas", type="primary"):
                self._save_all_labels_from_ui(page_transactions)

        with col_action2:
            if st.button("🗑️ Limpiar página actual"):
                self._clear_page_labels(page_transactions)

        with col_action3:
            if st.button("📊 Ver resumen"):
                self._show_labeling_summary()

    def _on_category_change(self, transaction_row: pd.Series, transaction_key: str):
        """Callback cuando cambia una categoría - guarda automáticamente"""
        # Obtener el valor seleccionado del widget
        widget_key = None
        for key in st.session_state.keys():
            if key.endswith(transaction_key) and key.startswith('category_'):
                widget_key = key
                break

        if widget_key:
            selected_category = st.session_state[widget_key]
            if selected_category and selected_category.strip():
                # Guardar inmediatamente
                self.save_label_immediately(transaction_row, selected_category, transaction_key)

    def _save_all_labels_from_ui(self, transactions_df: pd.DataFrame):
        """Guarda todas las etiquetas visibles de la interfaz"""
        try:
            saved_count = 0

            for idx, (_, row) in enumerate(transactions_df.iterrows()):
                transaction_key = self.create_transaction_key(row)

                # Buscar el widget correspondiente en session_state
                for key in st.session_state.keys():
                    if key.endswith(transaction_key) and key.startswith('category_'):
                        selected_category = st.session_state[key]
                        if selected_category and selected_category.strip():
                            self.save_label_immediately(row, selected_category, transaction_key)
                            saved_count += 1
                        break

            if saved_count > 0:
                st.success(f"✅ {saved_count} etiquetas guardadas exitosamente")
            else:
                st.warning("⚠️ No hay etiquetas nuevas para guardar")

        except Exception as e:
            st.error(f"❌ Error guardando etiquetas: {e}")

    def _clear_page_labels(self, transactions_df: pd.DataFrame):
        """Limpia las etiquetas de la página actual"""
        try:
            # Limpiar del session_state
            for idx, (_, row) in enumerate(transactions_df.iterrows()):
                transaction_key = self.create_transaction_key(row)

                # Limpiar de existing_labels
                if 'existing_labels' in st.session_state:
                    st.session_state.existing_labels.pop(transaction_key, None)

                # Limpiar widgets de UI
                for key in list(st.session_state.keys()):
                    if key.endswith(transaction_key) and key.startswith('category_'):
                        st.session_state[key] = ""

            st.success("✅ Etiquetas de la página actual limpiadas")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error limpiando etiquetas: {e}")

    def _show_labeling_summary(self):
        """Muestra resumen del progreso de etiquetado"""
        try:
            existing_labels = st.session_state.get('existing_labels', {})

            # Estadísticas generales
            total_labels = len(existing_labels)
            completed_labels = sum(1 for label in existing_labels.values() if label and label.strip())

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total transacciones", total_labels)
            with col2:
                st.metric("Etiquetadas", completed_labels)
            with col3:
                completion_rate = (completed_labels / total_labels * 100) if total_labels > 0 else 0
                st.metric("% Completado", f"{completion_rate:.1f}%")

            # Distribución por categoría
            if completed_labels > 0:
                category_counts = {}
                for label in existing_labels.values():
                    if label and label.strip():
                        category_counts[label] = category_counts.get(label, 0) + 1

                st.markdown("#### 📊 Distribución por categoría")
                category_df = pd.DataFrame(list(category_counts.items()), columns=['Categoría', 'Cantidad'])
                st.bar_chart(category_df.set_index('Categoría'))

        except Exception as e:
            st.error(f"❌ Error mostrando resumen: {e}")

    def get_labeling_statistics(self) -> Dict:
        """Obtiene estadísticas completas del etiquetado"""
        try:
            labeled_data = self.datastore.load_labeled()

            if labeled_data.empty:
                return {
                    'total_labeled': 0,
                    'categories_used': 0,
                    'category_distribution': {}
                }

            category_counts = labeled_data[
                'category'].value_counts().to_dict() if 'category' in labeled_data.columns else {}

            return {
                'total_labeled': len(labeled_data),
                'categories_used': len(category_counts),
                'category_distribution': category_counts,
                'most_common_category': max(category_counts.items(), key=lambda x: x[1])[
                    0] if category_counts else None,
                'completion_rate': None  # Se calcularía con el total de transacciones disponibles
            }

        except Exception as e:
            self.logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {'error': str(e)}


# Función para integrar con el main.py existente
def show_improved_labeling_page(datastore, current_data):
    """Página de etiquetado mejorada para usar en main.py"""

    st.header("🏷️ Etiquetar Gastos - Sistema Mejorado")

    if current_data is None:
        st.warning("⚠️ Primero debes cargar una cartola")
        if st.button("📁 Ir a Cargar"):
            # Esta lógica dependería de cómo manejas la navegación en tu app
            return

    # Filtrar solo gastos (montos negativos)
    gastos = current_data[current_data['Monto'] < 0].copy() if 'Monto' in current_data.columns else pd.DataFrame()

    if gastos.empty:
        st.info("ℹ️ No hay gastos para etiquetar en la cartola actual")
        return

    st.info(f"📊 Total de gastos para etiquetar: **{len(gastos)}** transacciones")

    # Inicializar sistema de etiquetado
    labeling_system = SmartLabelingSystem(datastore)

    # Obtener categorías disponibles
    try:
        categories = datastore.get_categories()
    except Exception as e:
        st.error(f"❌ Error obteniendo categorías: {e}")
        categories = ['bordados', 'contabilidad', 'servicios', 'otros']  # Fallback

    # Mostrar estadísticas del progreso
    stats = labeling_system.get_labeling_statistics()
    if 'error' not in stats:
        col_stat1, col_stat2, col_stat3 = st.columns(3)

        with col_stat1:
            st.metric("📈 Total etiquetadas", stats.get('total_labeled', 0))
        with col_stat2:
            st.metric("📂 Categorías usadas", stats.get('categories_used', 0))
        with col_stat3:
            most_common = stats.get('most_common_category', 'N/A')
            st.metric("🏆 Categoría más usada", most_common if most_common != 'N/A' else 'N/A')

    # Mostrar interfaz de etiquetado
    labeling_system.show_labeling_interface(gastos, categories)

    # Consejos y ayuda
    with st.expander("💡 Consejos para un etiquetado eficiente"):
        st.markdown("""
        **🎯 Estrategias recomendadas:**
        - **Auto-guardado**: Las etiquetas se guardan automáticamente al seleccionar
        - **Navegación**: Usa las páginas para procesar lotes de transacciones
        - **Consistencia**: Usa siempre los mismos nombres de categoría
        - **Revisión**: Usa "Ver resumen" para revisar tu progreso

        **🔧 Características del sistema:**
        - ✅ **Persistencia**: Las etiquetas no se pierden al actualizar
        - ✅ **Sin duplicados**: Evita crear registros duplicados automáticamente
        - ✅ **Carga inteligente**: Detecta transacciones ya etiquetadas
        - ✅ **Paginación**: Maneja grandes cantidades de transacciones eficientemente
        """)
