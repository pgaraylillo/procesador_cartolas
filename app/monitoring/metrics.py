# app/monitoring/metrics.py
import time
from collections import defaultdict, deque
from typing import Dict, List
import threading
from datetime import datetime


class MetricsCollector:
    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)
        self.histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.gauges: Dict[str, float] = {}
        self.lock = threading.Lock()

    def increment_counter(self, name: str, value: int = 1):
        """Incrementar contador"""
        with self.lock:
            self.counters[name] += value

    def record_histogram(self, name: str, value: float):
        """Registrar valor en histograma"""
        with self.lock:
            self.histograms[name].append({
                'value': value,
                'timestamp': time.time()
            })

    def set_gauge(self, name: str, value: float):
        """Establecer valor de gauge"""
        with self.lock:
            self.gauges[name] = value

    def get_metrics(self) -> Dict:
        """Obtener todas las métricas"""
        with self.lock:
            metrics = {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histograms': {}
            }

            # Calcular estadísticas de histogramas
            for name, values in self.histograms.items():
                if values:
                    values_only = [item['value'] for item in values]
                    metrics['histograms'][name] = {
                        'count': len(values_only),
                        'avg': sum(values_only) / len(values_only),
                        'min': min(values_only),
                        'max': max(values_only),
                        'p95': self._percentile(values_only, 0.95),
                        'p99': self._percentile(values_only, 0.99)
                    }

            return metrics

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calcular percentil"""
        sorted_values = sorted(values)
        index = int(percentile * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]


# Instancia global
metrics = MetricsCollector()


def timed_operation(operation_name: str):
    """Decorator para medir tiempo de operaciones"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                metrics.increment_counter(f"{operation_name}_success")
                return result
            except Exception as e:
                metrics.increment_counter(f"{operation_name}_error")
                raise
            finally:
                duration = time.time() - start_time
                metrics.record_histogram(f"{operation_name}_duration", duration)

        return wrapper

    return decorator

    ## 10. EXTENSIONES FUTURAS
    # Ideas para desarrollo futuro:

    # 1. Soporte para múltiples bancos:
    #    - BancoEstado, BCI, Chile, etc.
    #    - Parser factory pattern

    # 2. Integración con APIs bancarias:
    #    - Open Banking APIs
    #    - Sincronización automática

    # 3. Machine Learning avanzado:
    #    - Detección de anomalías
    #    - Predicción de gastos
    #    - Clustering de comportamiento

    # 4. Dashboards avanzados:
    #    - Presupuestos y alertas
    #    - Análisis comparativo
    #    - Proyecciones financieras

    # 5. Integraciones adicionales:
    #    - Boletas electrónicas SII
    #    - Sistemas contables adicionales
    #    - APIs de proveedores