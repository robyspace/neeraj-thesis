#!/bin/bash
# Final Comparison Script: ECMR vs C-MORL with Unified Metrics

echo "="
echo "ECMR vs C-MORL: Standardized Comparison"
echo "="
echo ""
echo "Configuration:"
echo "  - 24 hours simulation"
echo "  - 10 VMs per hour (240 total VMs)"
echo "  - Identical infrastructure (5 DCs, 3 server types)"
echo "  - Same carbon data (synchronized_dataset_2024.csv)"
echo ""

# Activate virtual environment
source venv/bin/activate

# Create output directory
mkdir -p final_comparison_results

# Kill any existing gateway
pkill -9 -f "Py4JGatewayEnhanced" 2>/dev/null || true
sleep 2

# Start fresh gateway
echo "Starting Java gateway..."
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > final_comparison_results/gateway.log 2>&1 &
GATEWAY_PID=$!
sleep 5

echo "Gateway started (PID: $GATEWAY_PID)"
echo ""

# Run ECMR
echo "="
echo "Step 1: Running ECMR Baseline"
echo "="
python ecmr_heterogeneous_integration.py \
  --data output/synchronized_dataset_2024.csv \
  --hours 24 \
  --vms-per-hour 10 \
  > final_comparison_results/ecmr_output.txt 2>&1

echo "✓ ECMR completed"
echo ""

# Restart gateway for C-MORL
echo "Restarting gateway for C-MORL..."
kill $GATEWAY_PID 2>/dev/null || true
sleep 3
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > final_comparison_results/gateway_cmorl.log 2>&1 &
GATEWAY_PID=$!
sleep 5

# Run C-MORL
echo "="
echo "Step 2: Running C-MORL"
echo "="
python train_cmorl.py \
  --simulation-hours 24 \
  --vms-per-hour 10 \
  --n-policies 3 \
  --timesteps 1000 \
  --n-extend 2 \
  --output-dir final_comparison_results/cmorl \
  --seed 42 \
  > final_comparison_results/cmorl_output.txt 2>&1

echo "✓ C-MORL completed"
echo ""

# Cleanup gateway
kill $GATEWAY_PID 2>/dev/null || true

echo "="
echo "✓ Comparison Complete!"
echo "="
echo ""
echo "Results saved to: final_comparison_results/"
echo "  - ecmr_output.txt"
echo "  - cmorl_output.txt"
echo "  - cmorl/final_results.json"
