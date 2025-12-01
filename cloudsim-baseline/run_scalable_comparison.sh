#!/bin/bash
# Scalable Comparison Script with Progress Monitoring
# Gradually scales up to avoid hangs

set -e  # Exit on error

echo "=================================================="
echo "SCALABLE ECMR vs C-MORL COMPARISON"
echo "=================================================="

# Activate virtual environment
source venv/bin/activate

# Configuration
HOURS=${1:-12}
VMS_PER_HOUR=${2:-10}
TIMESTEPS=${3:-10000}
OUTPUT_DIR=${4:-scalable_comparison}

TOTAL_VMS=$((HOURS * VMS_PER_HOUR))

echo "Configuration:"
echo "  Hours: $HOURS"
echo "  VMs per hour: $VMS_PER_HOUR"
echo "  Total VMs per episode: $TOTAL_VMS"
echo "  Timesteps per policy: $TIMESTEPS"
echo "  Output: $OUTPUT_DIR"
echo ""

# Check gateway
echo "Checking gateway..."
if ! pgrep -f "Py4JGatewayEnhanced" > /dev/null; then
    echo "⚠️  Gateway not running! Starting gateway..."
    pkill -9 -f "Py4JGatewayEnhanced" 2>/dev/null || true
    sleep 2

    # Start gateway with more memory for large simulations
    GATEWAY_MEMORY="8g"
    if [ $TOTAL_VMS -gt 100 ]; then
        GATEWAY_MEMORY="12g"
    fi

    java -Xmx${GATEWAY_MEMORY} -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
      com.ecmr.baseline.Py4JGatewayEnhanced > /Volumes/M4MiniDrv/cmorl_logs/gateway_comparison.log 2>&1 &

    echo "Started gateway with ${GATEWAY_MEMORY} memory"
    sleep 5
fi

echo "✓ Gateway is running"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run comparison with timeout and monitoring
echo "=================================================="
echo "Running comparison (this may take 30-60 minutes)..."
echo "=================================================="

# Run in background and monitor progress
python3 run_enhanced_comparison.py \
  --hours $HOURS \
  --vms-per-hour $VMS_PER_HOUR \
  --cmorl-timesteps $TIMESTEPS \
  --cmorl-policies 3 \
  --cmorl-extend 2 \
  --output-dir "$OUTPUT_DIR" \
  > "${OUTPUT_DIR}/comparison_output.log" 2>&1 &

COMPARISON_PID=$!

echo "Comparison running (PID: $COMPARISON_PID)"
echo "Progress log: ${OUTPUT_DIR}/comparison_output.log"
echo ""
echo "Monitor progress with:"
echo "  tail -f ${OUTPUT_DIR}/comparison_output.log"
echo ""

# Monitor progress
TIMEOUT=3600  # 1 hour timeout
ELAPSED=0
CHECK_INTERVAL=10

while kill -0 $COMPARISON_PID 2>/dev/null; do
    sleep $CHECK_INTERVAL
    ELAPSED=$((ELAPSED + CHECK_INTERVAL))

    # Print progress every minute
    if [ $((ELAPSED % 60)) -eq 0 ]; then
        echo "[$((ELAPSED / 60))m elapsed] Still running..."

        # Check if ECMR finished
        if [ -f "${OUTPUT_DIR}/ecmr/output.txt" ]; then
            if [ ! -f "${OUTPUT_DIR}/.ecmr_done" ]; then
                echo "  ✓ ECMR completed"
                touch "${OUTPUT_DIR}/.ecmr_done"
            fi
        fi

        # Check if C-MORL is training
        if [ -f "${OUTPUT_DIR}/cmorl/training_log.txt" ]; then
            EPISODES=$(grep -c "Episode.*Timesteps" "${OUTPUT_DIR}/cmorl/training_log.txt" 2>/dev/null || echo "0")
            if [ $EPISODES -gt 0 ]; then
                echo "  → C-MORL: ~$EPISODES episodes completed"
            fi
        fi
    fi

    # Check timeout
    if [ $ELAPSED -gt $TIMEOUT ]; then
        echo ""
        echo "⚠️  TIMEOUT! Comparison took longer than $((TIMEOUT / 60)) minutes"
        echo "  Killing process..."
        kill -9 $COMPARISON_PID 2>/dev/null || true
        echo "  Check logs: ${OUTPUT_DIR}/comparison_output.log"
        exit 1
    fi
done

# Wait for process to finish
wait $COMPARISON_PID
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "=================================================="
    echo "✓ COMPARISON COMPLETE!"
    echo "=================================================="
    echo ""
    echo "Generating visualizations..."
    python3 comparison_visualizer.py --results-dir "$OUTPUT_DIR"
    echo ""
    echo "Results saved to: $OUTPUT_DIR/"
    echo "  - Report: $OUTPUT_DIR/comparison_report.md"
    echo "  - Figures: $OUTPUT_DIR/figures/"
    echo ""
    echo "View report:"
    echo "  cat $OUTPUT_DIR/comparison_report.md"
else
    echo "=================================================="
    echo "❌ COMPARISON FAILED (exit code: $EXIT_CODE)"
    echo "=================================================="
    echo "Check logs: ${OUTPUT_DIR}/comparison_output.log"
    exit $EXIT_CODE
fi
