# app/auth/rate_limiter.py
import time
from collections import defaultdict, deque
from typing import Dict, Tuple


class AdvancedRateLimiter:
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.limits = {
            'default': (100, 3600),  # 100 requests per hour
            'parse': (10, 600),  # 10 file uploads per 10 min
            'train': (5, 3600),  # 5 training sessions per hour
        }

    def is_allowed(self, key: str, endpoint: str = 'default') -> Tuple[bool, dict]:
        """Verificar si request está permitido"""
        now = time.time()
        limit_count, limit_window = self.limits.get(endpoint, self.limits['default'])

        # Limpiar requests antiguos
        while (self.requests[key] and
               now - self.requests[key][0] > limit_window):
            self.requests[key].popleft()

        # Verificar límite
        current_count = len(self.requests[key])

        if current_count >= limit_count:
            # Calcular tiempo hasta reset
            oldest_request = self.requests[key][0]
            reset_time = oldest_request + limit_window

            return False, {
                'error': 'Rate limit exceeded',
                'limit': limit_count,
                'remaining': 0,
                'reset_time': reset_time
            }

        # Agregar request actual
        self.requests[key].append(now)

        return True, {
            'limit': limit_count,
            'remaining': limit_count - current_count - 1,
            'reset_time': now + limit_window
        }