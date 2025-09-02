# Santander Finance App

App modular (Streamlit + sklearn) para procesar cartolas de Banco Santander, etiquetar gastos, entrenar un clasificador supervisado y cruzar con reportes de Kame ERP.

## Estructura
```
app/
  bankstatements/
    base.py
    santander.py
  kame/
    kame_report.py
  ml/
    classifier.py
    features.py
  storage/
    datastore.py
  utils/
    io.py
    schema.py
  main.py
requirements.txt
README.md
```

## Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar
```bash
streamlit run app/main.py
```

## Flujo
1. **Cargar cartola** (.xlsx) => obtiene CSV normalizado (date, description, amount, debit_credit, document_number, branch).
2. **Etiquetar** gastos manualmente (column `category`).
3. **Entrenar IA** con las etiquetas (LogisticRegression + TF-IDF).
4. **Clasificar** nuevos movimientos.
5. **Cruzar con Kame**: subir reporte Kame (Excel/CSV) para detectar gastos sin respaldo.

## Git
```bash
git init
git add .
git commit -m "feat: bootstrap OOP Streamlit app for Santander + Kame"
```

## Nota
Se generó un CSV de muestra (primeras 50 filas) desde tu archivo subido para pruebas rápidas:
/mnt/data/santander_finance_app/sample_santander.csv
Columnas detectadas: ['Cartolas históricas de Cuentas Corrientes', 'Cartolas históricas de Cuentas Corrientes.1', 'Cartolas históricas de Cuentas Corrientes.2', 'Cartolas históricas de Cuentas Corrientes.3', 'Cartolas históricas de Cuentas Corrientes.4', 'Cartolas históricas de Cuentas Corrientes.5', 'Cartolas históricas de Cuentas Corrientes.6', 'Cartolas históricas de Cuentas Corrientes.7']
Filas: 109
Errores (si hubo): None
