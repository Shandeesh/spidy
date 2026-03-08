
import win32evtlog
import win32evtlogutil
import win32con

def read_sxs_errors():
    server = 'localhost'
    log_type = 'Application'
    hand = win32evtlog.OpenEventLog(server, log_type)
    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
    total = 0
    
    print("Scanning Application Event Log for SideBySide errors...")
    
    events = win32evtlog.ReadEventLog(hand, flags, 0)
    while events:
        for event in events:
            if event.SourceName == "SideBySide":
                print(f"Found Error: {event.TimeGenerated}")
                # Get the message
                try:
                    data = event.StringInserts
                    with open("c:/Users/Shandeesh R P/spidy/Trading_Backend/mt5_bridge/event_log_dump.txt", "a", encoding="utf-8") as f:
                        f.write(f"--- Event Time: {event.TimeGenerated} ---\n")
                        if data:
                            for i, line in enumerate(data):
                                f.write(f"Insert[{i}]: {line}\n")
                        else:
                            f.write("(No message data)\n")
                        f.write("\n")
                except Exception as e:
                    print(f"Error writing: {e}")
                
                total += 1
                if total >= 5:
                    return

        events = win32evtlog.ReadEventLog(hand, flags, 0)

if __name__ == "__main__":
    try:
        read_sxs_errors()
    except ImportError:
        print("win32evtlog not found. Please install pywin32.")
    except Exception as e:
        print(f"Failed: {e}")
