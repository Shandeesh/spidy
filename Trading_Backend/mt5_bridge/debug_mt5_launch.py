import subprocess
import os
import sys

exe_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
work_dir = os.path.dirname(exe_path)

print(f"Attempting to launch: {exe_path}")
print(f"Working Directory: {work_dir}")

try:
    # Try launching with subprocess and specific CWD
    process = subprocess.Popen(
        [exe_path], 
        cwd=work_dir,
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    print(f"Launch Successful? PID: {process.pid}")
    print("Waiting 5 seconds to see if it crashes immediately...")
    try:
        process.wait(timeout=5)
        print(f"Process exited with code: {process.returncode}")
    except subprocess.TimeoutExpired:
        print("Process is still running (Good sign).")
        
except Exception as e:
    print(f"Launch Failed: {e}")
