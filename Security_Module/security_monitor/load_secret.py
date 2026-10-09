"""
Spidy AI — Secret Loader
Tries key_manager decryption first, falls back to environment variables.
"""
import os
import sys
import logging

logger = logging.getLogger("spidy.secrets")

_key_manager_imported = False

def load_secret(key_name: str, default: str = "") -> str:
    """
    Load a secret value. Priority: Encrypted .env key (via key_manager) > Environment Variable > Default.
    """
    global _key_manager_imported
    # Try key_manager first
    try:
        sec_storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secure_storage")
        if sec_storage_path not in sys.path:
            sys.path.insert(0, sec_storage_path)
        from key_manager import decrypt_key
        val = decrypt_key(key_name)
        if val:
            return val
    except Exception as e:
        logger.debug(f"key_manager decryption not available for {key_name}: {e}")

    # Fall back to environment variable
    return os.getenv(key_name, default)
