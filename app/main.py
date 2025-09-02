import streamlit as st
import pandas as pd
from pathlib import Path
from utils.io import read_statement_excel, ensure_dir
from bankstatements.santander import SantanderParser
from storage.datastore import DataStore
from ml.classifier import ExpenseClassifier
from kame.kame_report import KameIntegrator

st.set_page_config(page_title="Santander Finance App", page_icon="📊", layout="wide")

st.title("📊 Santander Finance App")
st.caption("Procesa cartolas, etiqueta gastos y cruza con Kame. Arquitectura modular y extensible.")

ds = DataStore(root=Path('data'))
parser = SantanderParser()
model = ExpenseClassifier()
kame = KameIntegrator()

with st.sidebar:
    st.header("Acciones")
    page = st.radio("Ir a:", ["1) Cargar cartola", "2) Etiquetar", "3) Entrenar IA", "4) Clasificar", "5) Cruzar con Kame"], index=0)
    st.markdown("---")
    st.caption("Proyecto OOP, listo para extender a nuevos bancos o ERPs.")

if page == "1) Cargar cartola":
    st.subheader("Cargar cartola Santander (Excel)")
    f = st.file_uploader("Sube la cartola .xlsx", type=["xlsx"])
    if f is not None:
        tmp_path = Path("uploads") / f.name
        ensure_dir(tmp_path.parent)
        with open(tmp_path, 'wb') as w:
            w.write(f.read())
        df_raw = read_statement_excel(tmp_path)
        df = parser.parse(df_raw)
        st.success(f"Cargadas {len(df)} transacciones.")
        st.dataframe(df.head(50))
        st.download_button("Descargar CSV normalizado", df.to_csv(index=False).encode('utf-8'), file_name="santander_normalizado.csv", mime="text/csv")

elif page == "2) Etiquetar":
    st.subheader("Etiquetar gastos (supervisado)")
    f = st.file_uploader("Sube CSV normalizado para etiquetar", type=["csv"])
    if f is not None:
        df = pd.read_csv(f)
        df = df.sort_values('date')
        # Select only expenses to label typically
        df_exp = df[df['amount'] < 0].copy().reset_index(drop=True)
        st.write("Selecciona una categoría para filas y guarda.")
        cat = st.text_input("Nueva categoría (escribe y presiona Enter para usarla)", value="Gasto General")
        edited = st.data_editor(df_exp.assign(category=""), num_rows="dynamic", use_container_width=True, key="editor")
        if st.button("Guardar etiquetas"):
            if 'category' not in edited.columns:
                st.error("Agrega la columna 'category' en el editor.")
            else:
                labeled = edited.dropna(subset=['category'])
                if len(labeled) == 0:
                    st.warning("No hay filas etiquetadas.")
                else:
                    ds.save_labeled(labeled)
                    st.success(f"Guardadas {len(labeled)} filas etiquetadas en data/{ds.labeled_file}")

elif page == "3) Entrenar IA":
    st.subheader("Entrenar clasificador de gastos")
    labeled = ds.load_labeled()
    if labeled.empty:
        st.info("Aún no hay datos etiquetados. Ve a 'Etiquetar'.")
    else:
        st.write(f"Registros etiquetados: {len(labeled)}")
        labeled = labeled.dropna(subset=['category'])
        model.fit(labeled, label_col='category')
        st.success("Modelo entrenado con éxito (LogisticRegression + TF-IDF)")
        # Simple report using train performance
        report = model.report(labeled, labeled['category'])
        st.text(report)

elif page == "4) Clasificar":
    st.subheader("Clasificar automáticamente nuevos movimientos")
    f = st.file_uploader("Sube CSV normalizado a clasificar", type=["csv"])
    if f is not None:
        df = pd.read_csv(f)
        labeled = ds.load_labeled()
        if labeled.empty:
            st.warning("Primero entrena el modelo en 'Entrenar IA'.") 
        else:
            model.fit(labeled, label_col='category')  # train (or load a persisted model in future)
            preds = model.predict(df)
            out = df.copy()
            out['predicted_category'] = preds
            st.dataframe(out.head(50))
            st.download_button("Descargar clasificados", out.to_csv(index=False).encode('utf-8'), file_name="clasificados.csv", mime="text/csv")    

elif page == "5) Cruzar con Kame":
    st.subheader("Cruzar gastos con reportes Kame (buscar sin respaldo)")
    f_bank = st.file_uploader("Sube CSV normalizado de banco", type=["csv"], key="bank_csv")
    f_kame = st.file_uploader("Sube reporte Kame (Excel o CSV)", type=["csv","xlsx"], key="kame_file")
    if f_bank is not None and f_kame is not None:
        bank_df = pd.read_csv(f_bank)
        # Save temp Kame file
        tmp_path = Path("uploads") / f_kame.name
        ensure_dir(tmp_path.parent)
        with open(tmp_path, 'wb') as w:
            w.write(f_kame.read())
        kame_df = kame.load(tmp_path)
        missing = kame.find_unbacked_expenses(bank_df, kame_df)
        st.write(f"Gastos sin respaldo tributario detectados: {len(missing)}")
        st.dataframe(missing.head(100))
        st.download_button("Descargar listado sin respaldo", missing.to_csv(index=False).encode('utf-8'), file_name="gastos_sin_respaldo.csv", mime="text/csv")    
