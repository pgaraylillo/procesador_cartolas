from __future__ import annotations
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.metrics import classification_report
from .features import TextFeaturizer

class ExpenseClassifier:
    def __init__(self):
        self.text_featurizer = TextFeaturizer(max_features=4000, ngram_range=(1,2))
        # We can extend with numeric features later (amount, day-of-week, etc.)
        self.model = LogisticRegression(max_iter=200, n_jobs=None)

    def fit(self, df: pd.DataFrame, label_col: str = 'category'):
        X_text = self.text_featurizer.fit_transform(df['description'])
        self.model.fit(X_text, df[label_col])
        return self

    def predict(self, df: pd.DataFrame):
        X_text = self.text_featurizer.transform(df['description'])
        return self.model.predict(X_text)

    def predict_proba(self, df: pd.DataFrame):
        X_text = self.text_featurizer.transform(df['description'])
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X_text)
        return None

    def report(self, df: pd.DataFrame, true_labels: pd.Series):
        preds = self.predict(df)
        return classification_report(true_labels, preds, zero_division=0)
