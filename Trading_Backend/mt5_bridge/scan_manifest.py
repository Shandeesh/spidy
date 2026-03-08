
import re
import os

def scan_manifest():
    exe_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    print(f"Scanning {exe_path} for manifest...")
    
    try:
        with open(exe_path, "rb") as f:
            content = f.read()
            # Look for XML manifest patterns
            # dependentAssembly matches
            # <assemblyIdentity type="win32" name="Microsoft.VC80.CRT" ... />
            
            # Broad search for Microsoft.VC strings
            # Often UTF-16 encoded in binaries, so we scan for bytes
            
            # UTF-8/ASCII
            matches = re.findall(b'Microsoft\.VC[0-9]+\.[A-Za-z]+', content)
            for m in matches:
                print(f"Found (ASCII): {m.decode('utf-8', errors='ignore')}")
                
            # UTF-16 LE
            matches_wide = re.findall(b'M\x00i\x00c\x00r\x00o\x00s\x00o\x00f\x00t\x00\.\x00V\x00C\x00', content)
            if matches_wide:
                print("Found UTF-16 Microsoft.VC references (likely modern manifest).")
            
            # Check for VCRUNTIME140.dll
            if b'VCRUNTIME140.dll' in content or b'V\x00C\x00R\x00U\x00N\x00T\x00I\x00M\x00E\x001\x004\x000\x00.\x00d\x00l\x00l\x00' in content:
                print("Found VCRUNTIME140.dll reference (VS 2015+)")
                
    except Exception as e:
        print(f"Error reading file: {e}")

    # Check external manifest
    man = exe_path + ".manifest"
    if os.path.exists(man):
        print(f"Found external manifest: {man}")
        with open(man, "r", errors="ignore") as f:
            print(f.read()[:500])

if __name__ == "__main__":
    scan_manifest()
