# app/auth/security.py
import hashlib
import secrets
import hmac


class SecureAuth:
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_hex(32)

    def hash_password(self, password: str) -> str:
        """Hash seguro de contraseñas"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100k iteraciones
        )
        return f"{salt}:{password_hash.hex()}"

    def verify_password(self, password: str, hash_with_salt: str) -> bool:
        """Verificar contraseña"""
        try:
            salt, password_hash = hash_with_salt.split(':')
            calculated_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return hmac.compare_digest(
                password_hash,
                calculated_hash.hex()
            )
        except ValueError:
            return False

    def generate_api_key(self, length: int = 64) -> str:
        """Generar API key criptográficamente segura"""
        return secrets.token_urlsafe(length)