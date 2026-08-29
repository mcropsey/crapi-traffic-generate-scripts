#!/bin/bash
# Run all baseline scripts once per hour
# Logs to /var/log/crapi_baseline.log

LOG_FILE="/var/log/crapi_baseline.log"
BASELINE_DIR="/home/mcropsey/crapi-traffic/baseline"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

{
    echo "[$TIMESTAMP] Starting baseline training data generation..."
    cd "$BASELINE_DIR"

    for i in {01..15}; do
        SCRIPT=$(ls baseline_${i}_*.py 2>/dev/null)
        if [ -z "$SCRIPT" ]; then
            echo "[$TIMESTAMP] Baseline $i: Script not found"
            continue
        fi

        if timeout 20 python3 "$SCRIPT" > /dev/null 2>&1; then
            echo "[$TIMESTAMP] Baseline $i: SUCCESS"
        else
            echo "[$TIMESTAMP] Baseline $i: FAILED/TIMEOUT"
        fi
    done

    echo "[$TIMESTAMP] Baseline training run complete"
} >> "$LOG_FILE" 2>&1
