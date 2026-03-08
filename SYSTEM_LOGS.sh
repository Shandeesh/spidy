#!/bin/bash

# Configuration
LOG_FILE="Trading_Backend/mt5_bridge/system_logs.txt"
DOWNLOAD_DIR="logs_download"

# Ensure log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "Error: Log file not found at $LOG_FILE"
    exit 1
fi

# Function to show usage
usage() {
    echo "Usage: $0 [command] [args]"
    echo "Commands:"
    echo "  (no args)           Monitor logs (tail -f)"
    echo "  download date <YYYY-MM-DD>  Extract logs for a specific date"
    echo "  download systems    Extract System/Info/Error/Settings logs"
    echo "  download trade      Extract Trade/Signal/HFT/Scanner logs"
    echo "  download overall    Copy the full log file"
}

# Default behavior: tail -f
if [ -z "$1" ]; then
    echo "Monitoring logs... (Ctrl+C to exit)"
    tail -f "$LOG_FILE"
    exit 0
fi

# Command handling
COMMAND="$1"
SUBCOMMAND="$2"
ARG="$3"

mkdir -p "$DOWNLOAD_DIR"

if [ "$COMMAND" == "download" ]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    
    if [ "$SUBCOMMAND" == "date" ]; then
        if [ -z "$ARG" ]; then
            echo "Error: Date required (YYYY-MM-DD)"
            exit 1
        fi
        OUT_FILE="$DOWNLOAD_DIR/logs_date_${ARG}_${TIMESTAMP}.txt"
        grep "$ARG" "$LOG_FILE" > "$OUT_FILE"
        
        if [ -s "$OUT_FILE" ]; then
            echo "Saved date logs to $OUT_FILE"
        else
            echo "No logs found for date: $ARG"
            rm "$OUT_FILE"
        fi
        
    elif [ "$SUBCOMMAND" == "systems" ]; then
        OUT_FILE="$DOWNLOAD_DIR/logs_systems_${TIMESTAMP}.txt"
        grep -E "INFO|ERROR|WARNING|SETTINGS|COMMAND|SMART CONNECT|Process launched" "$LOG_FILE" > "$OUT_FILE"
        echo "Saved systems logs to $OUT_FILE"
        
    elif [ "$SUBCOMMAND" == "trade" ]; then
        OUT_FILE="$DOWNLOAD_DIR/logs_trade_${TIMESTAMP}.txt"
        grep -E "TRADE|SIGNAL|SUCCESS|CLOSING|HFT|SCANNER|SHIELD|SENTIMENT" "$LOG_FILE" > "$OUT_FILE"
        echo "Saved trade logs to $OUT_FILE"
        
    elif [ "$SUBCOMMAND" == "overall" ]; then
        OUT_FILE="$DOWNLOAD_DIR/logs_full_${TIMESTAMP}.txt"
        cp "$LOG_FILE" "$OUT_FILE"
        echo "Saved full log to $OUT_FILE"
        
    else
        usage
    fi
else
    usage
fi
