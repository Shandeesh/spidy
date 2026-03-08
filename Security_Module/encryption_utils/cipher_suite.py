import base64
import os
from cryptography.fernet import Fernet

class SpidyCipher:
    def __init__(self, key_path="secret.key"):
        self.key_path = key_path
        self.key = self._load_or_create_key()
        self.cipher_suite = Fernet(self.key)

    def _load_or_create_key(self):
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as key_file:
                return key_file.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_path, "wb") as key_file:
                key_file.write(key)
            return key

    def encrypt_data(self, data: str) -> str:
        """Encrypts string data."""
        return self.cipher_suite.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypts string data."""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()

if __name__ == "__main__":
    # Test
    cipher = SpidyCipher()
    secret = "Buy EURUSD @ 1.05"
    enc = cipher.encrypt_data(secret)
    print(f"Encrypted: {enc}")
    dec = cipher.decrypt_data(enc)
    print(f"Decrypted: {dec}")
