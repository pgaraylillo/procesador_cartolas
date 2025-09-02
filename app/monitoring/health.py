# app/monitoring/health.py
import sqlite3
import requests
import psutil
from typing import Dict, List, Callable
import time


class HealthChecker:
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.register_default_checks()

    def register_check(self, name: str, check_func: Callable):
        """Registrar un health check personalizado"""
        self.checks[name] = check_func

    def register_default_checks(self):
        """Registrar checks por defecto"""
        self.register_check('database', self._check_database)
        self.register_check('memory', self._check_memory)
        self.register_check('disk', self._check_disk)
        self.register_check('cpu', self._check_cpu)

    def run_all_checks(self) -> Dict:
        """Ejecutar todos los health checks"""
        results = {
            'timestamp': time.time(),
            'status': 'healthy',
            'checks': {}
        }

        for name, check_func in self.checks.items():
            try:
                check_result = check_func()
                results['checks'][name] = {
                    'status': 'pass',
                    **check_result
                }
            except Exception as e:
                results['checks'][name] = {
                    'status': 'fail',
                    'error': str(e)
                }
                results['status'] = 'unhealthy'

        return results

    def _check_database(self) -> Dict:
        """Verificar conexión a base de datos"""
        try:
            with sqlite3.connect('data/finance.db', timeout=5) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM transactions")
                count = cursor.fetchone()[0]

                return {
                    'transaction_count': count,
                    'response_time_ms': 0  # Se podría medir
                }
        except Exception as e:
            raise Exception(f"Database check failed: {e}")

    def _check_memory(self) -> Dict:
        """Verificar uso de memoria"""
        memory = psutil.virtual_memory()

        if memory.percent > 90:
            raise Exception(f"Memory usage too high: {memory.percent}%")

        return {
            'used_percent': memory.percent,
            'available_gb': memory.available / (1024 ** 3)
        }

    def _check_disk(self) -> Dict:
        """Verificar espacio en disco"""
        disk = psutil.disk_usage('.')
        used_percent = (disk.used / disk.total) * 100

        if used_percent > 85:
            raise Exception(f"Disk usage too high: {used_percent:.1f}%")

        return {
            'used_percent': used_percent,
            'free_gb': disk.free / (1024 ** 3)
        }

    def _check_cpu(self) -> Dict:
        """Verificar uso de CPU"""
        cpu_percent = psutil.cpu_percent(interval=1)

        if cpu_percent > 95:
            raise Exception(f"CPU usage too high: {cpu_percent}%")

        return {
            'used_percent': cpu_percent,
            'count': psutil.cpu_count()
        }


# Endpoint para health check
health_checker = HealthChecker()


def get_health_status():
    return health_checker.run_all_checks()