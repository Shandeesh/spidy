
import winreg

def check_vc_redist():
    print("Checking installed VC++ Redistributables...")
    try:
        key_path = r"SOFTWARE\Microsoft\VisualStudio"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            print("Accessing VisualStudio registry key...")
            # This is a rough check, sophisticated check requires iterating uninstall keys
    except Exception as e:
        print(f"Registry access failed: {e}")

if __name__ == "__main__":
    check_vc_redist()
