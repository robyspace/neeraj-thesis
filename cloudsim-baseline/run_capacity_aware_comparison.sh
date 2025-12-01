#!/bin/bash
echo "=================================================="
echo "CAPACITY-AWARE ECMR vs C-MORL COMPARISON"
echo "=================================================="
echo "Configuration:"
echo "  State dimensions: 137 (127 + 5 DC type + 5 DC capacity)"
echo "  Hours: 24"
echo "  VMs per hour: 10"
echo "  Total VMs per episode: 240"
echo "  C-MORL timesteps per policy: 20000"
echo "  Output: capacity_aware_comparison_24h"
echo ""

# Activate virtual environment
source venv/bin/activate

# Check gateway
echo "Checking gateway..."
if ! pgrep -f "Py4JGatewayEnhanced" > /dev/null; then
    echo "⚠️  Gateway not running! Please start gateway first."
    exit 1
fi
echo "✓ Gateway is running"
echo ""

# Run comparison
./run_scalable_comparison.sh 24 10 20000 capacity_aware_comparison_24h

echo ""
echo "=================================================="
echo "✓ CAPACITY-AWARE COMPARISON COMPLETE"
echo "=================================================="
