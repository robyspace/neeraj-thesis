#!/bin/bash
echo "=================================================="
echo "TESTING CAPACITY-AWARE C-MORL (STATE_DIM=137)"
echo "=================================================="
echo "Configuration:"
echo "  State dimensions: 137 (127 + 5 DC type + 5 DC capacity)"
echo "  Hours: 2"
echo "  VMs per hour: 5"
echo "  Total VMs per episode: 10"
echo "  Timesteps per policy: 1000"
echo "  Output: test_capacity_137"
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Create test directory
mkdir -p test_capacity_137

# Run quick C-MORL training
echo "Starting C-MORL training..."
python3 train_cmorl.py \
    --output-dir test_capacity_137 \
    --simulation-hours 2 \
    --vms-per-hour 5 \
    --n-policies 1 \
    --timesteps 1000 \
    --n-extend 0 \
    --seed 42

echo ""
echo "✓ Test complete"
echo "Check test_capacity_137/ for results"
