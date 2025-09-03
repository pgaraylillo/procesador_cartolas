# scripts/performance_monitor.py
# !/usr/bin/env python3
"""Monitor de performance continuo"""

import time
import requests
import sqlite3
import json
from datetime import datetime


def monitor_performance():
    """Ejecutar checks de performance"""

    results = {
        'timestamp': datetime.now().isoformat(),
        'metrics': {}
    }

    # 1. Test API response time
    start = time.time()
    try:
        response = requests.get('http://localhost:8501/_stcore/health', timeout=10)
        api_time = time.time() - start
        results['metrics']['api_response_time'] = api_time
        results['metrics']['api_status'] = response.status_code
    except Exception as e:
        results['metrics']['api_error'] = str(e)

    # 2. Test database performance
    start = time.time()
    try:
        with sqlite3.connect('data/finance.db', timeout=5) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM transactions")
            count = cursor.fetchone()[0]
            db_time = time.time() - start
            results['metrics']['db_response_time'] = db_time
            results['metrics']['transaction_count'] = count
    except Exception as e:
        results['metrics']['db_error'] = str(e)

    # 3. Check disk usage
    import shutil
    total, used, free = shutil.disk_usage('.')
    results['metrics']['disk_usage_percent'] = (used / total) * 100

    # Log results
    print(json.dumps(results, indent=2))

    # Alerts si hay problemas
    if results['metrics'].get('api_response_time', 0) > 5:
        print("ALERT: API response time too high")

    if results['metrics'].get('db_response_time', 0) > 2:
        print("ALERT: Database response time too high")


if __name__ == '__main__':
    monitor_performance()