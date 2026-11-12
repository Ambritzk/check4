#!/bin/bash
# usage: sudo ./pingexp.sh <target_hostname_or_ip>
# sudo is needed for intervals below 0.2 s on most systems.

if [ -z "$1" ]; then
    echo "Usage: $0 <target_hostname_or_ip>"
    exit 1
fi

TARGET="$1"
OUTPUT_FILE="ping_data3.csv"
MAXTIME=9    # seconds per run, keeps every run under 10 s

SIZES=(64 256 512 1024 1400)                       # never above 1400
INTERVALS=(1.0 0.5 0.2 0.1 0.05 0.02 0.01 0.005)

[ "$EUID" -ne 0 ] && echo "Note: not root, intervals below 0.2 s will likely be refused."

echo "packet_size,interval,count,sent,received,req_rate_bps,reply_rate_bps,loss_pct" > "$OUTPUT_FILE"

for size in "${SIZES[@]}"; do
    for interval in "${INTERVALS[@]}"; do
        # count scales with interval so each run lasts about MAXTIME seconds
        count=$(awk -v i="$interval" -v t="$MAXTIME" 'BEGIN{c=int(t/i); if(c<1)c=1; print c}')

        echo "Testing -> size=${size} interval=${interval}s count=${count}"
        output=$(ping -c "$count" -s "$size" -i "$interval" -q "$TARGET" 2>&1)

        transmitted=$(echo "$output" | grep -oE '[0-9]+ packets transmitted' | awk '{print $1}')
        received=$(echo "$output" | grep -oE '[0-9]+ received' | awk '{print $1}')
        time_ms=$(echo "$output" | grep -oE 'time [0-9]+ms' | grep -oE '[0-9]+')

        if [ -z "$transmitted" ] || [ -z "$received" ]; then
            echo "  ping failed/refused: $(echo "$output" | head -n 1)"
            continue
        fi

        # Fallback if this ping doesn't report total time
        if [ -z "$time_ms" ] || [ "$time_ms" -eq 0 ]; then
            time_ms=$(awk -v n="$transmitted" -v i="$interval" 'BEGIN{printf "%d", (n-1)*i*1000}')
        fi
        [ "$time_ms" -eq 0 ] && { echo "  zero duration, skipping"; continue; }

        # On-wire size: payload + 8 ICMP + 20 IP header bytes
        awk -v s="$size" -v i="$interval" -v c="$count" -v tx="$transmitted" \
            -v rx="$received" -v ms="$time_ms" 'BEGIN{
            bits = (s + 28) * 8
            d    = ms / 1000
            printf "%d,%s,%d,%d,%d,%.0f,%.0f,%.1f\n", s, i, c, tx, rx,
                   tx*bits/d, rx*bits/d, 100*(tx-rx)/tx
        }' >> "$OUTPUT_FILE"

        sleep 1
    done
done

echo "Done. Data saved to $OUTPUT_FILE"