
import os

files = ["bridge.err", "bridge.log"]

for filename in files:
    print(f"--- CONTENT OF {filename} ---")
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-16") as f:
                print(f.read())
        except Exception as e:
            # Try utf-8 just in case
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    print(f.read())
            except Exception as e2:
                 print(f"Error reading {filename}: {e}")
    else:
        print("File not found.")
    print("\n-------------------------------\n")
