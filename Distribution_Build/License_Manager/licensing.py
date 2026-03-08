import hashlib
import hmac
import base64
import os
import platform
import subprocess

SECRET_SEED = b"SpidyAI_Secret_Core_2025"  # CHANGE THIS IN PRODUCTION

def get_hardware_id():
    """Generates a unique Hardware ID for the machine."""
    try:
        if platform.system() == "Windows":
            cmd = "wmic csproduct get uuid"
            uuid = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
            return uuid
        else:
            return "UNKNOWN_HWID"
    except Exception:
        return "FALLBACK_HWID"

def generate_key(hardware_id):
    """Generates an Activation Key for a given Hardware ID."""
    # Simple HMAC-SHA256 signature
    signature = hmac.new(SECRET_SEED, hardware_id.encode(), hashlib.sha256).digest()
    # Base32 encoding for readable keys (removing look-alike chars)
    key = base64.b32encode(signature).decode().strip("=")
    # Format as XXXX-XXXX-XXXX-XXXX
    formatted_key = "-".join([key[i:i+4] for i in range(0, 16, 4)])
    return formatted_key[:19] # Truncate to standard length

def validate_key(hardware_id, key_input):
    """Validates if the input key matches the Hardware ID."""
    expected_key = generate_key(hardware_id)
    # Normalize input
    key_input = key_input.strip().upper()
    return hmac.compare_digest(expected_key, key_input)

if __name__ == "__main__":
    print("=== Spidy AI License Manager ===")
    print("1. Generate Key for a Hardware ID")
    print("2. Validate a Key")
    choice = input("Select (1/2): ")
    
    if choice == "1":
        hwid = input("Enter User's Hardware ID: ")
        print(f"Activation Key: {generate_key(hwid)}")
    elif choice == "2":
        hwid = input("Enter Hardware ID: ")
        key = input("Enter Key: ")
        if validate_key(hwid, key):
            print("VALID LINE.")
        else:
            print("INVALID KEY.")
