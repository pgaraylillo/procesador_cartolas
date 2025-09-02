# app/services/financial_service.py
from typing import List, Dict, Optional
from app.repositories.transaction_repository import TransactionRepository
from app.ml.classifier import ExpenseClassifier
from app.analytics.anomaly_detector import AnomalyDetector


class FinancialService:
    def __init__(self,
                 transaction_repo: TransactionRepository,
                 classifier: ExpenseClassifier,
                 anomaly_detector: AnomalyDetector):
        self.transaction_repo = transaction_repo
        self.classifier = classifier
        self.anomaly_detector = anomaly_detector

    def process_bank_statement(self, file_data: bytes, filename: str) -> Dict:
        """Procesar cartola completa"""

        # 1. Parse del archivo
        parsed_transactions = self._parse_statement(file_data, filename)

        # 2. Validar datos
        validation_result = self._validate_transactions(parsed_transactions)
        if not validation_result['valid']:
            raise ValueError(f"Invalid data: {validation_result['issues']}")

        # 3. Detectar duplicados
        unique_transactions = self._remove_duplicates(parsed_transactions)

        # 4. Guardar en base de datos
        saved_ids = []
        for transaction in unique_transactions:
            transaction_id = self.transaction_repo.save(transaction)
            saved_ids.append(transaction_id)

        # 5. Clasificar automáticamente si hay modelo entrenado
        if self.classifier.is_fitted:
            self._auto_classify_new_transactions(saved_ids)

        # 6. Detectar anomalías
        anomalies = self.anomaly_detector.detect_anomalies(unique_transactions)

        return {
            'processed_count': len(unique_transactions),
            'saved_ids': saved_ids,
            'anomalies_detected': len(anomalies),
            'validation_warnings': validation_result.get('warnings', [])
        }

    def get_financial_insights(self, year: int, month: int) -> Dict:
        """Generar insights financieros del mes"""

        # Obtener datos del mes
        transactions = self.transaction_repo.find_by_date_range(
            f"{year}-{month:02d}-01",
            f"{year}-{month:02d}-31"
        )

        if not transactions:
            return {'error': 'No data available for this period'}

        # Calcular métricas básicas
        expenses = [t for t in transactions if t['amount'] < 0]
        income = [t for t in transactions if t['amount'] > 0]

        insights = {
            'summary': {
                'total_transactions': len(transactions),
                'total_expenses': sum(t['amount'] for t in expenses),
                'total_income': sum(t['amount'] for t in income),
                'net_flow': sum(t['amount'] for t in transactions)
            },
            'categories': self._analyze_categories(expenses),
            'trends': self._analyze_trends(transactions),
            'recommendations': self._generate_recommendations(transactions)
        }

        return insights

    def reconcile_with_erp(self,
                           bank_transactions: List[Dict],
                           erp_documents: List[Dict]) -> Dict:
        """Conciliar transacciones bancarias con documentos ERP"""

        reconciliation_result = {
            'matched_transactions': [],
            'unmatched_bank': [],
            'unmatched_erp': [],
            'potential_matches': []
        }

        # Lógica de matching inteligente
        for bank_tx in bank_transactions:
            matches = self._find_erp_matches(bank_tx, erp_documents)

            if matches:
                reconciliation_result['matched_transactions'].append({
                    'bank_transaction': bank_tx,
                    'erp_matches': matches
                })
            else:
                reconciliation_result['unmatched_bank'].append(bank_tx)

        return reconciliation_result