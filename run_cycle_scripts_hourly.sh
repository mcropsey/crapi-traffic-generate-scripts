#!/bin/bash
# Run all cycle scripts once per hour at bottom of the hour (30 minutes past)
# Logs to /var/log/crapi_cycle.log

LOG_FILE="/var/log/crapi_cycle.log"
CYCLE_DIR="/home/mcropsey/crapi-traffic"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

{
    echo "[$TIMESTAMP] Starting cycle scripts traffic generation..."
    cd "$CYCLE_DIR"

    CYCLE_SCRIPTS=(
        "crapi_mechanic_cycle.py"
        "crapi_location_cycle.py"
        "crapi_shop_cycle.py"
        "crapi_community_cycle.py"
        "crapi_dashboard_cycle.py"
        "crapi_coupon_cycle.py"
    )

    for script in "${CYCLE_SCRIPTS[@]}"; do
        if [ ! -f "$script" ]; then
            echo "[$TIMESTAMP] $script: NOT FOUND"
            continue
        fi

        if timeout 30 python3 "$script" > /dev/null 2>&1; then
            echo "[$TIMESTAMP] $script: SUCCESS"
        else
            echo "[$TIMESTAMP] $script: FAILED/TIMEOUT"
        fi
    done

    echo "[$TIMESTAMP] Cycle scripts run complete"
} >> "$LOG_FILE" 2>&1
