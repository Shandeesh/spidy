"""
Secure Key Manager — encrypts/decrypts API keys using cipher_suite.py.
Usage (CLI):
    python key_manager.py encrypt SPIDY_API_KEY my_plain_secret
    python key_manager.py decrypt SPIDY_API_KEY
    python key_manager.py rotate SPIDY_API_KEY new_plain_secret
"""
import os
import sys
import argparse

# Path to cipher_suite.py
_HERE    = os.path.dirname(os.path.abspath(__file__))
_SEC_DIR = os.path.abspath(os.path.join(_HERE, "../encryption_utils"))
_ENV     = os.path.abspath(os.path.join(_HERE, "../../../Shared_Data/configs/.env"))
_KEY_F   = os.path.abspath(os.path.join(_HERE, "../../../Shared_Data/configs/secret.key"))

if _SEC_DIR not in sys.path:
    sys.path.insert(0, _SEC_DIR)

from cipher_suite import SpidyCipher


def _get_cipher() -> SpidyCipher:
    return SpidyCipher(key_path=_KEY_F)


def encrypt_key(env_var: str, plaintext: str) -> str:
    """
    Encrypts `plaintext` and writes the encrypted value into the .env file
    under `env_var`. Returns the encrypted token.
    """
    cipher = _get_cipher()
    token  = cipher.encrypt_data(plaintext)

    lines = []
    replaced = False
    if os.path.exists(_ENV):
        with open(_ENV, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith(f"{env_var}="):
                lines[i] = f"{env_var}={token}\n"
                replaced = True
                break

    if not replaced:
        lines.append(f"{env_var}={token}\n")

    with open(_ENV, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"[KeyManager] {env_var} encrypted and written to .env")
    return token


def decrypt_key(env_var: str) -> str:
    """
    Reads `env_var` from the .env file and decrypts its value.
    Returns the plaintext string.
    """
    if not os.path.exists(_ENV):
        raise FileNotFoundError(f".env not found at {_ENV}")

    raw = None
    with open(_ENV, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith(f"{env_var}="):
                raw = line.split("=", 1)[1].strip()
                break

    if raw is None:
        raise KeyError(f"{env_var} not found in .env")

    if len(raw) < 100:
        # Looks like plaintext already
        return raw

    cipher = _get_cipher()
    return cipher.decrypt_data(raw)


def rotate_key(env_var: str, new_plaintext: str) -> str:
    """Encrypts a new value and overwrites the previous one in .env."""
    return encrypt_key(env_var, new_plaintext)


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spidy Secure Key Manager")
    sub    = parser.add_subparsers(dest="cmd")

    enc = sub.add_parser("encrypt", help="Encrypt a key and save to .env")
    enc.add_argument("env_var",   help="Environment variable name, e.g. SPIDY_API_KEY")
    enc.add_argument("plaintext", help="Plain-text value to encrypt")

    dec = sub.add_parser("decrypt", help="Read and decrypt a key from .env")
    dec.add_argument("env_var",   help="Environment variable name")

    rot = sub.add_parser("rotate",  help="Rotate (re-encrypt) a key in .env")
    rot.add_argument("env_var",    help="Environment variable name")
    rot.add_argument("plaintext",  help="New plain-text value")

    args = parser.parse_args()

    if args.cmd == "encrypt":
        token = encrypt_key(args.env_var, args.plaintext)
        print(f"Encrypted token ({len(token)} chars) written to .env")
    elif args.cmd == "decrypt":
        value = decrypt_key(args.env_var)
        print(f"{args.env_var} = {value}")
    elif args.cmd == "rotate":
        token = rotate_key(args.env_var, args.plaintext)
        print(f"Rotated. New token written to .env")
    else:
        parser.print_help()
