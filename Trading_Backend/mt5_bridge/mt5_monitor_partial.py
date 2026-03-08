
# --- MONITOR MT5 PROCESS (Fix for Zombie Relaunch) ---
async def monitor_mt5_process():
    """
    Periodically checks if 'terminal64.exe' is actually running.
    If not, updates mt5_state["connected"] = False.
    This prevents other modules (like Watchdog) from trying to 'initialize' (relaunch) it.
    """
    print("INFO: MT5 Process Monitor Started.")
    while True:
        try:
            # Simple check using tasklist (lightweight enough for 5s interval)
            # using tasklist is safer than psutil if not installed
            # Check if terminal64.exe is in the output of tasklist
            proc = await asyncio.create_subprocess_shell(
                'tasklist /FI "IMAGENAME eq terminal64.exe" /NH',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode('utf-8', errors='ignore')
            
            is_running = "terminal64.exe" in output
            
            if not is_running:
                if mt5_state.get("connected", False):
                    print("⚠️ MONITOR: MT5 Process gone! Setting connected = False.")
                    mt5_state["connected"] = False
            else:
                # Optional: If running but state is False, we could auto-reconnect?
                # For now, let's just respect the running state.
                pass
                
        except Exception as e:
            print(f"Monitor Error: {e}")
            
        await asyncio.sleep(5)
