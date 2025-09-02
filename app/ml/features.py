from __future__ import annotations
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

class TextFeaturizer:
    def __init__(self, max_features: int = 5000, ngram_range=(1,2)):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            strip_accents='unicode',
            lowercase=True
        )

    def fit_transform(self, texts: pd.Series):
        return self.vectorizer.fit_transform(texts.fillna(''))

    def transform(self, texts: pd.Series):
        return self.vectorizer.transform(texts.fillna(''))
