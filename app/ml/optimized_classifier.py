# app/ml/optimized_classifier.py
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
import joblib
from functools import lru_cache


class OptimizedExpenseClassifier:
    def __init__(self):
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                stop_words=self._get_spanish_stopwords(),
                min_df=2,
                max_df=0.95,
                token_pattern=r'\b[a-zA-Z]{2,}\b'  # Solo palabras de 2+ letras
            )),
            ('classifier', LogisticRegression(
                max_iter=1000,
                n_jobs=-1,
                random_state=42,
                solver='saga'  # Mejor para datasets grandes
            ))
        ])

        # Cache para predicciones recientes
        self._prediction_cache = {}
        self._cache_size = 1000

    @lru_cache(maxsize=128)
    def _get_spanish_stopwords(self):
        return frozenset([
            'de', 'la', 'el', 'en', 'y', 'a', 'que', 'por', 'con', 'del',
            'transf', 'transferencia', 'pago', 'compra', 'abono', 'cargo'
        ])

    def fit_optimized(self, df, target_col='category'):
        """Entrenamiento con grid search optimizado"""

        # Parámetros para optimizar
        param_grid = {
            'tfidf__max_features': [3000, 5000, 7000],
            'classifier__C': [0.1, 1.0, 10.0],
        }

        grid_search = GridSearchCV(
            self.pipeline,
            param_grid,
            cv=3,  # Reducir CV para velocidad
            n_jobs=-1,
            scoring='f1_weighted',
            verbose=1
        )

        X = df['description']
        y = df[target_col]

        grid_search.fit(X, y)
        self.pipeline = grid_search.best_estimator_

        return self

    def predict_with_cache(self, texts):
        """Predicción con cache para evitar re-cálculos"""
        results = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            text_hash = hash(text)
            if text_hash in self._prediction_cache:
                results.append(self._prediction_cache[text_hash])
            else:
                results.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Predecir solo textos no cacheados
        if uncached_texts:
            predictions = self.pipeline.predict(uncached_texts)

            # Actualizar cache y resultados
            for idx, pred in zip(uncached_indices, predictions):
                text_hash = hash(texts[idx])
                self._prediction_cache[text_hash] = pred
                results[idx] = pred

                # Limpiar cache si está muy grande
                if len(self._prediction_cache) > self._cache_size:
                    # Remover 20% de entradas más antiguas
                    items_to_remove = list(self._prediction_cache.items())[:200]
                    for key, _ in items_to_remove:
                        del self._prediction_cache[key]

        return results

    def save_model(self, path):
        """Guardar con compresión"""
        joblib.dump(self.pipeline, path, compress=3)