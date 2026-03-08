
import subprocess
import time
import os

def run_trace():
    folder = os.path.dirname(os.path.abspath(__file__))
    trace_file = os.path.join(folder, "sxstrace.etl")
    out_file = os.path.join(folder, "sxstrace.txt")
    exe_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"

    if os.path.exists(trace_file): os.remove(trace_file)
    if os.path.exists(out_file): os.remove(out_file)

    print("Starting sxstrace...")
    # Start tracing in background
    tracer = subprocess.Popen(["sxstrace", "Trace", f"-logfile:{trace_file}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)

    print(f"Launching {exe_path}...")
    try:
        # Launch MT5 (it will crash)
        subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
    except Exception as e:
        print(f"Launch error: {e}")

    time.sleep(3)

    print("Stopping tracer...")
    subprocess.run(["sxstrace", "StopTrace"], check=True)
    tracer.terminate()

    print("Parsing trace...")
    res = subprocess.run(["sxstrace", "Parse", f"-logfile:{trace_file}", f"-outfile:{out_file}"], capture_output=True, text=True)
    print(res.stdout)
    
    if os.path.exists(out_file):
        print(f"Trace parsed to {out_file}")
    else:
        print("Failed to create output file.")

if __name__ == "__main__":
    run_trace()
