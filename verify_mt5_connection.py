import sys
import os
import yaml
import MetaTrader5 as mt5

def load_settings():
    yaml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "spidy_ai", "config", "settings.yaml"))
    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            return config.get("mt5", {})
    return {}

def test_connection():
    print("===================================================")
    print("      SPIDY MT5 CONNECTION DIAGNOSTIC UTILITY")
    print("===================================================\n")
    
    settings = load_settings()
    login = int(settings.get("login", 0))
    password = settings.get("password", "")
    server = settings.get("server", "MetaQuotes-Demo")
    exe_path = settings.get("path", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    
    print(f"Configured Credentials:")
    print(f"  - Login ID : {login if login > 0 else '0 (Use active running terminal)'}")
    print(f"  - Server   : {server}")
    print(f"  - Path     : {exe_path}")
    print(f"  - Password : {'[PROVIDED]' if password else '[NOT PROVIDED]'}\n")
    
    if not os.path.exists(exe_path):
        print(f"[ERROR] MetaTrader 5 executable not found at: {exe_path}")
        print("Please verify the 'path' setting in spidy_ai/config/settings.yaml")
        return
        
    print("Attempting to initialize MetaTrader 5...")
    
    # Try initialization
    if login > 0:
        success = mt5.initialize(path=exe_path, login=login, password=password, server=server)
    else:
        success = mt5.initialize(path=exe_path)
        
    if success:
        print("[SUCCESS] MetaTrader 5 initialized and connected!")
        terminal_info = mt5.terminal_info()
        account_info = mt5.account_info()
        
        if terminal_info:
            print("\nTerminal Information:")
            print(f"  - Connected     : {terminal_info.connected}")
            print(f"  - Trade Allowed : {terminal_info.trade_allowed}")
            print(f"  - Company       : {terminal_info.company}")
            
        if account_info:
            print("\nAccount Information:")
            print(f"  - Account ID    : {account_info.login}")
            print(f"  - Server Name   : {account_info.server}")
            print(f"  - Balance       : {account_info.balance} {account_info.currency}")
            print(f"  - Equity        : {account_info.equity} {account_info.currency}")
            print(f"  - Profit        : {account_info.profit} {account_info.currency}")
        else:
            print("\n[WARN] WARNING: Not logged in to an active trade account.")
            print("Please open your MT5 application and ensure you are logged into a valid demo/live account.")
            
        mt5.shutdown()
    else:
        err = mt5.last_error()
        print(f"\n[FAILED] Connection initialization failed.")
        print(f"  - Error Code : {err[0]}")
        print(f"  - Error Msg  : {err[1]}")
        
        if err[0] == -6:
            print("\n[SUGGESTION] This is an Authorization Failure.")
            print("This means the account login details in settings.yaml are incorrect or the demo account has expired.")
            print("To resolve this:")
            print("  1. Open the MetaTrader 5 desktop application manually.")
            print("  2. Go to File -> Open an Account, search for 'MetaQuotes', and register a new free Demo Account.")
            print("  3. Ensure the MT5 terminal is fully logged in and shows 'Connected' at the bottom right.")
            print("  4. Once connected, run this script again or update settings.yaml with your new credentials.")

if __name__ == "__main__":
    test_connection()
