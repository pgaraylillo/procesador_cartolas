# app/utils/cache.py
import streamlit as st
import hashlib
import pickle
from functools import wraps


def smart_cache(func):
    """Cache personalizado con invalidación inteligente"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Crear key única
        cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"

        # Verificar si está en cache
        if cache_key in st.session_state:
            return st.session_state[cache_key]

        # Ejecutar función
        result = func(*args, **kwargs)

        # Guardar en cache
        st.session_state[cache_key] = result

        return result

    return wrapper


# Uso
@smart_cache
def expensive_ml_operation(data):
    # Operación costosa
    return result