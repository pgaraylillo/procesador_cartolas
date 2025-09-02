# --- bootstrap de ruta para que 'app' sea importable ---
import sys
from pathlib import Path
_THIS = Path(__file__).resolve()
PROJ_ROOT = _THIS.parent.parent  # .../santander_finance_app
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))
import streamlit as st
import pandas as pd
from pathlib import Path
import time
from app.utils.io import read_statement_excel, ensure_dir
from app.utils.schema import to_canonical, to_spanish
from app.bankstatements.santander import SantanderParser
from app.storage.datastore import DataStore
from app.ml.classifier import ExpenseClassifier
from app.kame.kame_report import KameIntegrator

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

# ------- 1) Cargar cartola -------
if page == "1) Cargar cartola":
    st.subheader("Cargar cartola Santander (Excel)")
    f = st.file_uploader("Sube la cartola .xlsx", type=["xlsx"])
    if f is not None:
        uploads_dir = ensure_dir("uploads")
        ts = time.strftime("%Y%m%d-%H%M%S")
        raw_path = uploads_dir / f"cartola_{ts}.xlsx"
        with open(raw_path, 'wb') as w:
            w.write(f.read())

        # Leer y parsear
        df_raw = read_statement_excel(raw_path)
        df_parsed_es = parser.parse(df_raw)  # devuelve headers en español

        # Guardar CSV procesado en uploads/
        csv_path = uploads_dir / f"cartola_{ts}.csv"
        df_parsed_es.to_csv(csv_path, index=False, encoding="utf-8")

        st.success(f"Procesadas {len(df_parsed_es)} transacciones. Guardado: {csv_path}")
        st.dataframe(df_parsed_es.head(50), use_container_width=True)
        st.download_button(
            "Descargar CSV normalizado (ES)",
            df_parsed_es.to_csv(index=False).encode('utf-8'),
            file_name=f"cartola_{ts}.csv",
            mime="text/csv",
        )

elif page == "2) Etiquetar":
    st.subheader("Etiquetar gastos (supervisado)")
    f = st.file_uploader("Sube CSV normalizado (ES) para etiquetar", type=["csv"])
    if f is not None:
        df_es = pd.read_csv(f)
        # 1) Llevar a canónico
        df = to_canonical(df_es).copy()

        # 2) Validaciones mínimas
        required = {"date", "description", "amount"}
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"Faltan columnas requeridas en el CSV: {missing}. "
                     f"Asegura que el CSV provenga del paso 'Cargar cartola'.")
            st.stop()

        # 3) Normalizaciones robustas
        # 3.1) date -> datetime
        df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)

        # 3.2) amount -> numeric (por si viene como string)
        #     OJO: los CSV guardados deberían venir con punto decimal, pero reforzamos:
        df["amount"] = (
            df["amount"]
            .astype(str)
            .str.replace("\u00a0", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)  # coma -> punto
        )
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

        # 3.3) Si hay debit_credit y todos los amounts son >= 0, aplicamos signo por ABONO/CARGO
        if "debit_credit" in df.columns:
            dc = df["debit_credit"].astype(str).str.upper().str.strip()
            if (df["amount"] >= 0).all():
                sign = dc.map({"CARGO": -1, "ABONO": 1}).fillna(1)
                df["amount"] = df["amount"] * sign
            # guardamos el texto normalizado (opcional)
            df["debit_credit"] = dc

        # 4) Drop filas inválidas y ordenar
        df = df.dropna(subset=["date", "description", "amount"])
        df = df.sort_values("date")

        # 5) Debug/preview
        st.caption(f"Registros totales: {len(df)} | Gastos (amount<0): {(df['amount']<0).sum()} | Ingresos (amount>0): {(df['amount']>0).sum()}")
        st.dataframe(to_spanish(df).head(20), use_container_width=True)

        st.caption(
            f"Total filas: {len(df)} | "
            f"Gastos (amount<0): {(df['amount'] < 0).sum()} | "
            f"Ingresos (amount>0): {(df['amount'] > 0).sum()} | "
            f"Con ABONO/CARGO: {'debit_credit' in df.columns}"
        )
        # 3.3) Forzar signo con ABONO/CARGO si existe
        if "debit_credit" in df.columns:
            dc = df["debit_credit"].astype(str).str.upper().str.strip()
            sign = dc.map({"CARGO": -1, "ABONO": 1}).fillna(1)
            # fuerza el signo con valor absoluto
            df["amount"] = df["amount"].abs() * sign
            df["debit_credit"] = dc

        # Debug/preview detallado
        st.caption(
            f"Total filas: {len(df)} | "
            f"Gastos (amount<0): {(df['amount'] < 0).sum()} | "
            f"Ingresos (amount>0): {(df['amount'] > 0).sum()}"
        )
        if "debit_credit" in df.columns:
            st.write("ABONO/CARGO (conteo):", df["debit_credit"].value_counts(dropna=False))

        # ¿Cuáles se descartarían por NaN?
        mask_nan = df["date"].isna() | df["description"].isna() | df["amount"].isna()
        n_nan = int(mask_nan.sum())
        if n_nan > 0:
            st.warning(f"Filas con NaN en date/description/amount: {n_nan}")
            st.dataframe(to_spanish(df[mask_nan]).head(10), use_container_width=True)


        # 6) Filtrar gastos para etiquetar
        df_exp = df[df["amount"] < 0].copy().reset_index(drop=True)
        df_exp_es = to_spanish(df_exp)
        df_exp_es["category"] = ""

        st.write("Asigna categorías y guarda:")
        edited = st.data_editor(
            df_exp_es,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_etiquetas",
        )

        if st.button("Guardar etiquetas"):
            if "category" not in edited.columns:
                st.error("Agrega la columna 'category' en el editor.")
            else:
                labeled_es = edited.dropna(subset=["category"])
                if labeled_es.empty:
                    st.warning("No hay filas etiquetadas.")
                else:
                    # Volver a canónico antes de guardar
                    labeled = to_canonical(labeled_es).copy()
                    labeled["date"] = pd.to_datetime(labeled["date"], errors="coerce").dt.strftime("%Y-%m-%d")
                    from app.storage.datastore import DataStore
                    ds = DataStore(root=Path('data'))
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
    f = st.file_uploader("Sube CSV normalizado (ES) a clasificar", type=["csv"])
    if f is not None:
        df_es = pd.read_csv(f)
        df = to_canonical(df_es)

        # Normalizaciones
        df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
        df["amount"] = (
            df["amount"].astype(str)
            .str.replace("\u00a0", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        if "debit_credit" in df.columns:
            dc = df["debit_credit"].astype(str).str.upper().str.strip()
            sign = dc.map({"CARGO": -1, "ABONO": 1}).fillna(1)
            df["amount"] = df["amount"].abs() * sign
            df["debit_credit"] = dc

        # Cargar etiquetas y entrenar
        labeled = ds.load_labeled()
        if labeled.empty:
            st.warning("Primero entrena el modelo en 'Entrenar IA'.")
        else:
            model.fit(labeled, label_col='category')
            preds = model.predict(df)
            out = df.copy()
            out['predicted_category'] = preds

            # Mostrar/descargar en español
            out_es = to_spanish(out).copy()
            out_es["Categoría (pred)"] = out["predicted_category"]
            st.dataframe(out_es.head(50), use_container_width=True)
            st.download_button(
                "Descargar clasificados (ES)",
                out_es.to_csv(index=False).encode('utf-8'),
                file_name="clasificados.csv",
                mime="text/csv",
            )

elif page == "5) Cruzar con Kame":
    st.subheader("Cruzar gastos con reportes Kame (buscar sin respaldo)")
    f_bank = st.file_uploader("Sube CSV normalizado de banco (ES)", type=["csv"], key="bank_csv")
    f_kame = st.file_uploader("Sube reporte Kame (Excel o CSV)", type=["csv","xlsx"], key="kame_file")
    if f_bank is not None and f_kame is not None:
        # Banco -> canónico + normalización de montos
        bank_es = pd.read_csv(f_bank)
        bank_df = to_canonical(bank_es).copy()
        bank_df["amount"] = (
            bank_df["amount"].astype(str)
            .str.replace("\u00a0", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        bank_df["amount"] = pd.to_numeric(bank_df["amount"], errors="coerce")

        # Guardar temporal Kame y cargar
        tmp_path = Path("uploads") / f_kame.name
        ensure_dir(tmp_path.parent)
        with open(tmp_path, 'wb') as w:
            w.write(f_kame.read())
        kame_df = kame.load(tmp_path)

        missing = kame.find_unbacked_expenses(bank_df, kame_df)
        st.write(f"Gastos sin respaldo tributario detectados: {len(missing)}")
        st.dataframe(missing.head(100), use_container_width=True)
        st.download_button(
            "Descargar listado sin respaldo",
            missing.to_csv(index=False).encode('utf-8'),
            file_name="gastos_sin_respaldo.csv",
            mime="text/csv",
        )
