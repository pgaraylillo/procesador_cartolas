from typing import Dict

CANONICAL_SCHEMA = {
    "monto": "amount",
    "descripción movimiento": "description",
    "descripcion movimiento": "description",
    "fecha": "date",
    "n° documento": "document_number",
    "n° documento.1": "document_number",
    "n°  documento": "document_number",
    "sucursal": "branch",
    "cargo/abono": "debit_credit",
    "cargo": "debit_credit",  # fallback
    "abono": "debit_credit",  # fallback
}

NORMALIZED_TYPES = {
    "amount": float,
    "description": str,
    "date": str,  # parse later
    "document_number": str,
    "branch": str,
    "debit_credit": str,  # 'CARGO'/'ABONO'
}

def normalize_headers(cols) -> Dict[str, str]:
    """Return a mapping from original header to canonical header where possible."""
    mapping = {}
    for c in cols:
        key = str(c).strip().lower()
        mapping[c] = CANONICAL_SCHEMA.get(key, key.replace(" ", "_"))
    return mapping
