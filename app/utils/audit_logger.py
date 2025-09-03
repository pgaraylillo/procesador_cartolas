# app/utils/audit_logger.py
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
import inspect


class AuditLogger:
    def __init__(self, log_file: str = 'logs/audit.log'):
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)

        # File handler para auditoría
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Formato JSON para auditoría
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def log_action(self,
                   action: str,
                   user_id: Optional[str] = None,
                   details: Dict[str, Any] = None,
                   sensitive: bool = False):
        """Log de acciones de usuario"""

        # Obtener información del frame actual
        frame = inspect.currentframe().f_back
        filename = frame.f_code.co_filename
        line_number = frame.f_lineno
        function_name = frame.f_code.co_name

        audit_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'user_id': user_id or 'anonymous',
            'source': {
                'file': filename.split('/')[-1],
                'function': function_name,
                'line': line_number
            },
            'details': details or {},
            'sensitive': sensitive
        }

        # No loggar datos sensibles en detalle si sensitive=True
        if sensitive:
            audit_record['details'] = {'_redacted': True}

        self.logger.info(json.dumps(audit_record))

    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log específico para eventos de seguridad"""
        self.log_action(
            action=f"SECURITY_{event_type}",
            details=details,
            sensitive=True
        )

    def log_data_access(self, table: str, operation: str, count: int):
        """Log de acceso a datos"""
        self.log_action(
            action="DATA_ACCESS",
            details={
                'table': table,
                'operation': operation,
                'record_count': count
            }
        )


# Uso global
audit = AuditLogger()


def audit_action(action: str):
    """Decorator para auditar acciones"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            audit.log_action(action, details={'function': func.__name__})
            return func(*args, **kwargs)

        return wrapper

    return decorator