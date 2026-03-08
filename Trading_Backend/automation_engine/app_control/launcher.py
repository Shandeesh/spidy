import sys
import os
import time

def open_app(app_name):
    """
    Basic automation to open apps. 
    In a real scenario, this would use AppPaths or specialized libraries.
    """
    app_name = app_name.lower()
    print(f"Attempting to launch: {app_name}")
    
    if "whatsapp" in app_name:
        # Windows 10/11 URI scheme
        os.system("start whatsapp:")
    elif "calculator" in app_name:
        os.system("calc")
    elif "notepad" in app_name:
        os.system("notepad")
    elif "instagram" in app_name:
        # Instagram PWA or browser
        os.system("start https://www.instagram.com")
    else:
        print(f"Unknown app: {app_name}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        open_app(command)
    else:
        print("No command provided.")
