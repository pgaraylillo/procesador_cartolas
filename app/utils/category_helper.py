# app/utils/category_helper.py - Asistente inteligente de categorización
import re
from typing import Dict, List, Optional
import pandas as pd
from collections import Counter


class CategoryHelper:
    """Asistente para sugerir categorías basado en descripción de transacciones"""

    def __init__(self):
        # Patrones de palabras clave por categoría
        self.category_patterns = {
            'bordados': [
                'bordado', 'textil', 'tela', 'hilo', 'aguja', 'maquina', 'costura',
                '4cdc bordados', 'bordados'
            ],
            'contabilidad': [
                'contabilidad', 'contador', 'contable', 'tributario', 'declaracion',
                'impuesto', 'iva', 'renta', 'sii', 'tesoreria', 'previred',
                'honorarios', 'asesor'
            ],
            'servicios': [
                'servicio', 'mantencion', 'reparacion', 'instalacion', 'consultoria',
                'asesoria', 'auditoria', 'capacitacion', 'entrenamiento'
            ],
            'combustible': [
                'combustible', 'bencina', 'petroleo', 'gasolina', 'diesel',
                'copec', 'shell', 'esso', 'petrobras', 'estacion'
            ],
            'alimentacion': [
                'almuerzo', 'desayuno', 'cena', 'restaurant', 'comida',
                'supermercado', 'unimarc', 'lider', 'jumbo', 'santa isabel'
            ],
            'tecnologia': [
                'computador', 'notebook', 'software', 'licencia', 'microsoft',
                'google', 'amazon', 'hosting', 'dominio', 'internet', 'wifi'
            ],
            'bancario': [
                'comision', 'mantencion', 'cargo', 'interes', 'cuota',
                'banco', 'santander', 'bci', 'estado', 'chile', 'scotia'
            ],
            'impuestos': [
                'impuesto', 'contribucion', 'patente', 'municipal', 'sii',
                'tesoreria', 'multa', 'tag', 'transito'
            ]
        }

    def suggest_category(self, description: str) -> Optional[str]:
        """Sugiere una categoría basada en la descripción"""
        if not description:
            return None

        desc_clean = self._clean_description(description)

        # Buscar coincidencias
        category_scores = {}

        for category, patterns in self.category_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.lower() in desc_clean:
                    # Dar más peso a coincidencias exactas
                    if pattern.lower() == desc_clean:
                        score += 10
                    # Peso normal a coincidencias parciales
                    else:
                        score += 1

            if score > 0:
                category_scores[category] = score

        # Retornar categoría con mayor puntuación
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            return best_category[0]

        return None

    def get_category_suggestions_for_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Obtiene sugerencias de categorías para un DataFrame completo"""
        if df.empty or 'Descripción' not in df.columns:
            return df

        df = df.copy()
        df['Categoria_Sugerida'] = df['Descripción'].apply(self.suggest_category)
        df['Tiene_Sugerencia'] = df['Categoria_Sugerida'].notna()

        return df

    def _clean_description(self, description: str) -> str:
        """Limpia descripción para mejor matching"""
        if pd.isna(description):
            return ""

        # Convertir a minúsculas
        clean = str(description).lower()

        # Remover caracteres especiales y números al inicio
        clean = re.sub(r'^[\d\s\-\.]+', '', clean)

        # Remover espacios extra
        clean = re.sub(r'\s+', ' ', clean).strip()

        return clean

    def analyze_unlabeled_transactions(self, df: pd.DataFrame) -> Dict:
        """Analiza transacciones sin etiquetar y da estadísticas de sugerencias"""
        if df.empty:
            return {'total': 0, 'with_suggestions': 0, 'suggestions_by_category': {}}

        df_with_suggestions = self.get_category_suggestions_for_batch(df)

        total_transactions = len(df_with_suggestions)
        with_suggestions = len(df_with_suggestions[df_with_suggestions['Tiene_Sugerencia']])

        suggestions_counter = Counter(df_with_suggestions['Categoria_Sugerida'].dropna())

        return {
            'total_transactions': total_transactions,
            'with_suggestions': with_suggestions,
            'without_suggestions': total_transactions - with_suggestions,
            'suggestion_rate': f"{with_suggestions / total_transactions * 100:.1f}%" if total_transactions > 0 else "0%",
            'suggestions_by_category': dict(suggestions_counter),
            'top_suggested_categories': suggestions_counter.most_common(5)
        }

    def add_category_pattern(self, category: str, patterns: List[str]):
        """Agrega nuevos patrones para una categoría"""
        if category not in self.category_patterns:
            self.category_patterns[category] = []

        self.category_patterns[category].extend([p.lower() for p in patterns])
        # Remover duplicados
        self.category_patterns[category] = list(set(self.category_patterns[category]))

    def get_frequent_descriptions(self, df: pd.DataFrame, min_frequency: int = 2) -> List[tuple]:
        """Obtiene descripciones frecuentes que podrían necesitar categorización"""
        if df.empty or 'Descripción' not in df.columns:
            return []

        # Limpiar y contar descripciones
        descriptions_clean = df['Descripción'].apply(self._clean_description)
        description_counts = descriptions_clean.value_counts()

        # Filtrar por frecuencia mínima
        frequent = description_counts[description_counts >= min_frequency]

        return [(desc, count) for desc, count in frequent.items() if desc.strip()]