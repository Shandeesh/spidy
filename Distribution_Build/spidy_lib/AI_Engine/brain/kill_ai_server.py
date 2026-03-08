import psutil
import sys

def kill_port(port):
    print(f"Checking port {port}...")
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for con in proc.connections(kind='inet'):
                    if con.laddr.port == port:
                        print(f"Found process on {port}: PID {proc.info['pid']}")
                        proc.kill()
                        print(f"Killed PID {proc.info['pid']}...")
                        return
            except (psutil.AccessDenied, psutil.ZombieProcess):
                continue
        print(f"No process found on port {port}.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    kill_port(5001)
