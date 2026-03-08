import os
import subprocess
import re
import sys

def kill_port_8000():
    print("Checking port 8000...")
    try:
        # Run netstat
        output = subprocess.check_output("netstat -ano", shell=True).decode()
        lines = output.splitlines()
        pid = None
        for line in lines:
            if ":8000" in line and "LISTENING" in line:
                parts = line.split()
                pid = parts[-1] 
                print(f"Found process on 8000: PID {pid}")
                break
        
        if pid:
            print(f"Killing PID {pid}...")
            os.system(f"taskkill /F /PID {pid}")
            print("Killed.")
        else:
            print("No process found on port 8000.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    kill_port_8000()
